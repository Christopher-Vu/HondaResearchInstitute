"""Visible agent that also records Step 3 replay inputs and per-layer residual-stream means (PRD 12.1).

Every model step logs both waypoint heads plus, for each decoder layer, the block output mean-pooled
over all tokens and over the driving-query tokens, the vision bridge (InternVL's `mlp1` projector)
output mean-pooled over tiles and tokens, and the hero's ground-truth `state` (PRD 9.2 probe targets,
read from CARLA just before the model runs). Collisions are logged with the step they happened
after. Every Nth step (SIMLINGO_CAPTURE_EVERY) also saves the exact preprocessed model input, so
`replay_capture.py` can rerun the frame offline. SIMLINGO_TOKEN_LAYERS (comma-separated decoder layers) adds
every driving-query token at those layers, unpooled, in float16: the per-token SAE's input (PRD 12.2).
SIMLINGO_CHASE_EVERY=N saves every Nth simulator frame from a third-person camera behind the car, for
figures; the policy never sees it. SIMLINGO_PROFILE=1 writes capture/profile.jsonl: per step, the wall seconds
spent outside the agent (simulator tick and evaluator), reading world state, preparing the model input, in the
forward pass (GPU synchronised), in the capture hook, and after the model.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import carla
import torch
from replay_capture import decoder, driving_query_count, move
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from torch import nn
from visible_agent import VisibleAgent
from world_state import WorldStateReader, vector_length

CPU = torch.device("cpu")


def get_entry_point() -> str:
    return "CaptureAgent"


def vision_bridge(model: nn.Module) -> nn.Module:
    """InternVL's projector from vision features into the language model's token space."""
    bridges = [module for name, module in model.named_modules() if name.endswith("mlp1")]
    if len(bridges) != 1:
        raise RuntimeError(f"Expected one mlp1 vision bridge, found {len(bridges)}")
    return bridges[0]


class CaptureAgent(VisibleAgent):
    def setup(self, path_to_conf_file: str, route_index: Any = None) -> None:
        self.records: list[dict[str, Any]] = []
        self.collisions: list[dict[str, Any]] = []
        self.collision_sensor: Any = None
        self.chase_camera: Any = None
        self.world_state: WorldStateReader | None = None
        self.pending_state: dict[str, Any] = {}
        self.profile: Any = None
        self.marks: dict[str, float] = {}
        super().setup(path_to_conf_file, route_index)
        # Upstream rewrites metric_info.json every step: ~0.26 s on Savio's scratch (40265241), about a third of a
        # step. Only Bench2Drive's efficiency/smoothness tools read it, so write it once, at the end, instead.
        self.metric_path = self.save_path_metric
        self.save_path_metric: Any = None
        self.capture_every = int(os.environ.get("SIMLINGO_CAPTURE_EVERY", "10"))
        self.token_layers = [int(layer) for layer in os.environ.get("SIMLINGO_TOKEN_LAYERS", "").split(",") if layer]
        self.capture_dir = self.evidence / "capture"
        (self.capture_dir / "inputs").mkdir(parents=True, exist_ok=True)
        self.layer_outputs: dict[int, torch.Tensor] = {}
        if os.environ.get("SIMLINGO_PROFILE"):
            self.profile = (self.capture_dir / "profile.jsonl").open("w")
            self._time_method("control_pid")
            self._time_method("get_metric_info")
        self.bridge_outputs: list[torch.Tensor] = []
        self.driving_tokens = driving_query_count(self.model)
        for index, layer in enumerate(decoder(self.model).layers):
            layer.register_forward_hook(self._layer_hook(index))
        vision_bridge(self.model).register_forward_hook(self._bridge_hook)
        self.model.register_forward_pre_hook(self._input_hook)
        self.model.register_forward_hook(self._output_hook)
        knockout = os.environ.get("SIMLINGO_ABLATE")
        if knockout:  # docs/steps/04-layer-site-ablation.md, Part C
            from ablate_replay import install
            spec = json.loads(knockout)
            install(self.model, spec["site"], int(spec["layer"]), Path(spec["means"]))

    def run_step(self, input_data: Any, timestamp: float, sensors: Any = None) -> Any:
        self._mark("entered")
        if self.world_state is None:
            self._attach_to_hero()
        self.pending_state = self._read_state()
        self._mark("state_read")
        control = super().run_step(input_data, timestamp, sensors)
        self._mark("left")
        self._write_profile()
        return control

    def _mark(self, name: str, synchronise: bool = False) -> None:
        if self.profile is None:
            return
        if synchronise and torch.cuda.is_available():
            torch.cuda.synchronize()
        self.marks[name] = time.monotonic()

    def _time_method(self, name: str) -> None:
        """Time an upstream method inside after_model; its remainder is mostly the per-step metric_info.json dump."""
        method = getattr(self, name)

        def timed(*args: Any, **kwargs: Any) -> Any:
            self._mark(f"{name}_started")
            result = method(*args, **kwargs)
            self._mark(f"{name}_done")
            return result
        setattr(self, name, timed)

    def _write_profile(self) -> None:
        if self.profile is None:
            return
        marks = self.marks
        spans = {"world_state": ("entered", "state_read"), "model_input": ("state_read", "forward_started"),
                 "forward": ("forward_started", "forward_done"), "capture_hook": ("forward_done", "hook_done"),
                 "after_model": ("hook_done", "left"), "control_pid": ("control_pid_started", "control_pid_done"),
                 "get_metric_info": ("get_metric_info_started", "get_metric_info_done"),
                 "metric_dump": ("get_metric_info_done", "left")}
        row = {"step": self.step, **{name: round(marks[end] - marks[start], 5)
                                     for name, (start, end) in spans.items() if start in marks and end in marks}}
        if "previous_left" in marks:
            row["outside_agent"] = round(marks["entered"] - marks["previous_left"], 5)
        self.profile.write(json.dumps(row) + "\n")
        self.marks = {"previous_left": marks["left"]}

    def _attach_to_hero(self) -> None:
        hero = CarlaDataProvider.get_hero_actor()
        if hero is None:
            raise RuntimeError("No hero vehicle to read state from")
        world = CarlaDataProvider.get_world()
        self.world_state = WorldStateReader(hero, world, CarlaDataProvider.get_map(), self.config.camera_pos_0[2])
        blueprint = world.get_blueprint_library().find("sensor.other.collision")
        self.collision_sensor = world.spawn_actor(blueprint, carla.Transform(), attach_to=hero)
        self.collision_sensor.listen(self._collision_hook)
        chase_every = int(os.environ.get("SIMLINGO_CHASE_EVERY", "0"))
        if chase_every:
            camera = world.get_blueprint_library().find("sensor.camera.rgb")
            for name, value in {"image_size_x": "1920", "image_size_y": "1080", "fov": "90"}.items():
                camera.set_attribute(name, value)
            behind = carla.Transform(carla.Location(x=-8.0, z=4.0), carla.Rotation(pitch=-15.0))
            self.chase_camera = world.spawn_actor(camera, behind, attach_to=hero)
            chase_dir = self.evidence / "chase"
            chase_dir.mkdir(exist_ok=True)
            self.chase_camera.listen(lambda image: image.frame % chase_every == 0
                                     and image.save_to_disk(str(chase_dir / f"{image.frame:08d}.png")))

    def _read_state(self) -> dict[str, Any]:
        assert self.world_state is not None
        try:
            return self.world_state.read()
        except Exception as error:
            return {"error": f"{type(error).__name__}: {error}"}

    def _collision_hook(self, event: Any) -> None:
        self.collisions.append({
            "step": self.step, "frame": event.frame, "other": event.other_actor.type_id,
            "intensity": vector_length(event.normal_impulse),
        })

    def _bridge_hook(self, _module: nn.Module, _inputs: Any, output: torch.Tensor) -> None:
        self.bridge_outputs.append(output.detach().float().mean(dim=tuple(range(output.dim() - 1))))

    def _layer_hook(self, index: int) -> Any:
        def hook(_module: nn.Module, _inputs: Any, output: Any) -> None:
            self.layer_outputs[index] = output[0] if isinstance(output, tuple) else output
        return hook

    def _input_hook(self, _module: nn.Module, inputs: tuple[Any, ...]) -> None:
        self.layer_outputs.clear()
        self.bridge_outputs.clear()
        if self.step % self.capture_every == 0:
            torch.save(move(inputs[0], CPU), self.capture_dir / "inputs" / f"{self.step:06d}.pt")
        self._mark("forward_started", synchronise=True)

    def _output_hook(self, _module: nn.Module, _inputs: Any, output: Any) -> None:
        self._mark("forward_done", synchronise=True)
        speed_wps, route, _language = output
        stacked = torch.stack([self.layer_outputs[index][0] for index in sorted(self.layer_outputs)])
        self.records.append({
            "step": self.step, "sequence_length": int(stacked.shape[1]), "driving_tokens": self.driving_tokens,
            "speed_wps": move(speed_wps.float(), CPU), "route": move(route.float(), CPU),
            "layer_mean": move(stacked.float().mean(dim=1), CPU),
            "layer_driving_mean": move(stacked[:, -self.driving_tokens:].float().mean(dim=1), CPU),
            "vision_bridge_mean": move(torch.stack(self.bridge_outputs).mean(dim=0), CPU),
            "state": self.pending_state,
        })
        if self.token_layers:
            self.records[-1]["driving_query_tokens"] = move(
                stacked[self.token_layers, -self.driving_tokens:].to(torch.float16), CPU)
        if len(self.records) % 200 == 0:
            self._flush()
        self._mark("hook_done")

    def _flush(self) -> None:
        torch.save({"capture_every": self.capture_every, "token_layers": self.token_layers,
                    "dtype": str(self.dtype), "device": str(self.device),
                    "records": self.records, "collisions": list(self.collisions)}, self.capture_dir / "steps.pt")

    def destroy(self, results: Any = None) -> None:
        if self.collision_sensor is not None and self.collision_sensor.is_alive:
            self.collision_sensor.stop()
            self.collision_sensor.destroy()
        if self.chase_camera is not None and self.chase_camera.is_alive:
            self.chase_camera.stop()
            self.chase_camera.destroy()
        if self.records:
            self._flush()
        if self.profile is not None:
            self.profile.close()
        if getattr(self, "metric_path", None) is not None and getattr(self, "metric_info", None):
            with open(f"{self.metric_path}/metric_info.json", "w") as outfile:
                json.dump(self.metric_info, outfile, indent=4)
        super().destroy(results)
