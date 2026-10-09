"""Visible agent that also records Step 3 replay inputs and per-layer residual-stream means (PRD 12.1).

Every model step logs both waypoint heads plus, for each decoder layer, the block output mean-pooled
over all tokens and over the driving-query tokens, the vision bridge (InternVL's `mlp1` projector)
output mean-pooled over tiles and tokens, and the hero's ground-truth `state` (PRD 9.2 probe targets,
read from CARLA just before the model runs). Collisions are logged with the step they happened
after. Every Nth step (SIMLINGO_CAPTURE_EVERY) also saves the exact preprocessed model input, so
`replay_capture.py` can rerun the frame offline.
"""
from __future__ import annotations

import os
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
        self.world_state: WorldStateReader | None = None
        self.pending_state: dict[str, Any] = {}
        super().setup(path_to_conf_file, route_index)
        self.capture_every = int(os.environ.get("SIMLINGO_CAPTURE_EVERY", "10"))
        self.capture_dir = self.evidence / "capture"
        (self.capture_dir / "inputs").mkdir(parents=True, exist_ok=True)
        self.layer_outputs: dict[int, torch.Tensor] = {}
        self.bridge_outputs: list[torch.Tensor] = []
        self.driving_tokens = driving_query_count(self.model)
        for index, layer in enumerate(decoder(self.model).layers):
            layer.register_forward_hook(self._layer_hook(index))
        vision_bridge(self.model).register_forward_hook(self._bridge_hook)
        self.model.register_forward_pre_hook(self._input_hook)
        self.model.register_forward_hook(self._output_hook)

    def run_step(self, input_data: Any, timestamp: float, sensors: Any = None) -> Any:
        if self.world_state is None:
            self._attach_to_hero()
        self.pending_state = self._read_state()
        return super().run_step(input_data, timestamp, sensors)

    def _attach_to_hero(self) -> None:
        hero = CarlaDataProvider.get_hero_actor()
        if hero is None:
            raise RuntimeError("No hero vehicle to read state from")
        world = CarlaDataProvider.get_world()
        self.world_state = WorldStateReader(hero, world, CarlaDataProvider.get_map(), self.config.camera_pos_0[2])
        blueprint = world.get_blueprint_library().find("sensor.other.collision")
        self.collision_sensor = world.spawn_actor(blueprint, carla.Transform(), attach_to=hero)
        self.collision_sensor.listen(self._collision_hook)

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

    def _output_hook(self, _module: nn.Module, _inputs: Any, output: Any) -> None:
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
        if len(self.records) % 200 == 0:
            self._flush()

    def _flush(self) -> None:
        torch.save({"capture_every": self.capture_every, "dtype": str(self.dtype), "device": str(self.device),
                    "records": self.records, "collisions": list(self.collisions)}, self.capture_dir / "steps.pt")

    def destroy(self, results: Any = None) -> None:
        if self.collision_sensor is not None and self.collision_sensor.is_alive:
            self.collision_sensor.stop()
            self.collision_sensor.destroy()
        if self.records:
            self._flush()
        super().destroy(results)
