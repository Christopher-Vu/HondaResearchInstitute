"""TransFuser++ (Fail2Drive's `team_code/sensor_agent.py`) with the harness's records, for the Fail2Drive track's
second policy (docs/prd-fail2drive.md, F6).

Writes what SimLingo's capture agent writes, in the same layout, so scoring and `export_activations.py` read it
unchanged:
- `controls.jsonl`: one row per step.
- `capture/steps.pt`: per model step, the hero's ground-truth `state`, and these activation sites:
  - `layer_mean`: each decoder (`join`) layer's output, mean-pooled over every query token of every `join` call that
    step (waypoint and checkpoint queries).
  - `layer_driving_mean`: the same layer outputs from the step's last `join` call only. That call is the checkpoint
    query, whose outputs the direct controller acts on.
  - `vision_bridge_mean`: the backbone's fused feature grid, mean-pooled over its spatial cells. This is where camera
    and LiDAR meet before the decoder.
  - Collisions are logged with the step they happened after.

No per-token or replay-input capture.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import carla
import numpy as np
import torch
from sensor_agent import SensorAgent
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from torch import nn
from world_state import WorldStateReader, vector_length

CPU = torch.device("cpu")
FLUSH_EVERY = 200


def get_entry_point() -> str:
    return "TfppCaptureAgent"


def first_tensor(output: Any) -> torch.Tensor:
    """Decoder layers and `join` return a tensor, or (tensor, attention) when built with attention."""
    return output[0] if isinstance(output, tuple) else output


class TfppCaptureAgent(SensorAgent):
    def setup(self, path_to_conf_file: str, route_index: Any = None, traffic_manager: Any = None) -> None:
        self.trace = None
        self.records: list[dict[str, Any]] = []
        self.collisions: list[dict[str, Any]] = []
        self.collision_sensor: Any = None
        self.world_state: WorldStateReader | None = None
        self.pending_state: dict[str, Any] = {}
        super().setup(path_to_conf_file, route_index, traffic_manager)
        if self.model_count != 1:
            raise RuntimeError(f"Expected one TransFuser++ model, found {self.model_count}")
        self.evidence = Path(os.environ["SIMLINGO_EVIDENCE"])
        self.capture_every = int(os.environ.get("SIMLINGO_CAPTURE_EVERY", "0"))
        self.capture_dir = self.evidence / "capture"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.trace = (self.evidence / "controls.jsonl").open("w")
        net = self.nets[0]
        if not hasattr(net, "join") or not hasattr(net.join, "layers"):
            raise RuntimeError("This TransFuser++ config has no transformer decoder join to capture")
        self.join_calls: list[list[torch.Tensor]] = []
        self.layer_outputs: list[torch.Tensor] = []
        self.fused: torch.Tensor | None = None
        self.forwarded = False
        for layer in net.join.layers:
            layer.register_forward_hook(self._layer_hook)
        net.join.register_forward_pre_hook(self._join_started)
        net.join.register_forward_hook(self._join_done)
        net.backbone.register_forward_hook(self._backbone_hook)
        # sensor_agent.py calls `net.forward(...)` directly, which skips module hooks on the net itself (smoke run
        # 40951567 recorded no model step), so the forward method is wrapped instead. Submodules are called normally.
        forward = net.forward

        def captured_forward(*args: Any, **kwargs: Any) -> Any:
            self._forward_started()
            output = forward(*args, **kwargs)
            self._forward_done()
            return output
        net.forward = captured_forward

    def run_step(self, input_data: Any, timestamp: float, sensors: Any = None) -> Any:
        if self.world_state is None:
            self._attach_to_hero()
        self.pending_state = self._read_state()
        self.forwarded = False
        started = time.monotonic()
        control = super().run_step(input_data, timestamp, sensors)
        record = {
            "step": self.step, "simulation_seconds": timestamp, "wall_step_seconds": time.monotonic() - started,
            "speed_metres_per_second": float(input_data["speed"][1]["speed"]),
            "throttle": float(control.throttle), "steer": float(control.steer), "brake": float(control.brake),
            "model_inference": self.forwarded,
        }
        if not all(np.isfinite(record[key]) for key in ("throttle", "steer", "brake")):
            raise RuntimeError("TransFuser++ returned non-finite vehicle controls")
        assert self.trace is not None
        self.trace.write(json.dumps(record) + "\n")
        self.trace.flush()
        print(f"TransFuser++ step {self.step}: speed={record['speed_metres_per_second']:.2f} "
              f"throttle={control.throttle:.3f} steer={control.steer:.3f} brake={control.brake:.3f}", flush=True)
        return control

    def _attach_to_hero(self) -> None:
        hero = CarlaDataProvider.get_hero_actor()
        if hero is None:
            raise RuntimeError("No hero vehicle to read state from")
        world = CarlaDataProvider.get_world()
        self.world_state = WorldStateReader(hero, world, CarlaDataProvider.get_map(), self.config.camera_pos[2])
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
        self.collisions.append({"step": self.step, "frame": event.frame, "other": event.other_actor.type_id,
                                "intensity": vector_length(event.normal_impulse)})

    def _forward_started(self) -> None:
        self.join_calls.clear()
        self.fused = None

    def _backbone_hook(self, _module: nn.Module, _inputs: Any, output: Any) -> None:
        # transFuser and bev_encoder backbones return (bev grid, fused features, image grid); aim returns two.
        fused = output[1] if len(output) == 3 else output[0]
        fused = fused.detach().float()
        # torch reads mean(dim=()) as every dim, so a flat (batch, channels) output is taken as it is.
        self.fused = (fused.mean(dim=tuple(range(2, fused.dim()))) if fused.dim() > 2 else fused)[0]

    def _join_started(self, _module: nn.Module, _inputs: Any) -> None:
        self.layer_outputs = []

    def _layer_hook(self, _module: nn.Module, _inputs: Any, output: Any) -> None:
        self.layer_outputs.append(first_tensor(output).detach().float()[0])

    def _join_done(self, _module: nn.Module, _inputs: Any, _output: Any) -> None:
        self.join_calls.append(self.layer_outputs)

    def _forward_done(self) -> None:
        self.forwarded = True
        if not self.join_calls or self.fused is None:
            raise RuntimeError("TransFuser++ ran without its decoder or backbone hooks firing")
        layers = len(self.join_calls[0])
        every_query = torch.stack([torch.cat([call[index] for call in self.join_calls]).mean(dim=0)
                                   for index in range(layers)])
        driving = torch.stack([output.mean(dim=0) for output in self.join_calls[-1]])
        self.records.append({"step": self.step, "layer_mean": every_query.to(CPU),
                             "layer_driving_mean": driving.to(CPU), "vision_bridge_mean": self.fused.to(CPU),
                             "state": self.pending_state})
        if len(self.records) % FLUSH_EVERY == 0:
            self._flush()

    def _flush(self) -> None:
        torch.save({"capture_every": self.capture_every, "token_layers": [], "dtype": "float32",
                    "device": str(self.device), "records": self.records, "collisions": list(self.collisions)},
                   self.capture_dir / "steps.pt")

    def get_metric_info(self) -> dict[str, Any]:
        """Fail2Drive's base agent has no metric record; Bench2Drive's evaluator asks for one."""
        upstream = getattr(super(), "get_metric_info", None)
        return upstream() if upstream is not None else {}

    def destroy(self, results: Any = None) -> None:
        if self.collision_sensor is not None and self.collision_sensor.is_alive:
            self.collision_sensor.stop()
            self.collision_sensor.destroy()
        if self.records:
            self._flush()
        if self.trace is not None:
            self.trace.close()
        super().destroy(results)
