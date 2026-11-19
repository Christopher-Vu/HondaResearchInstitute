"""UniAD-Base (Bench2DriveZoo's `team_code/uniad_b2d_agent.py`) with the harness's records, for the Fail2Drive
track's third policy (docs/prd-discovery-sprint.md §7).

Writes TransFuser++'s layout (adapters/tfpp/tfpp_agent.py), so `export_activations.py` and the sprint's
`cache_pool.py` read it unchanged:
- `controls.jsonl`: one row per step.
- `capture/steps.pt`: per model step (UniAD runs on every step), the hero's ground-truth `state`, and:
  - `layer_mean`: every layer in STAGES, in data-flow order (the capture's `layer_names`), each mean-pooled over all
    its tokens, queries or BEV cells, averaged over its calls that step. A layer with no queries that step (motion or
    occupancy with no tracked agent) records zeros, and `layer_fired` says which layers ran.
  - `layer_driving_mean`: the planning head's decoder layers on the ego plan query, the query the controller follows.
  - `vision_bridge_mean`: the FPN image features, mean over cameras, cells and levels: the camera features before
    BEVFormer lifts them to the BEV grid.
  - Collisions are logged with the step they happened after.
- `capture/frames/<step>.jpg`: the front camera, FRAME_WIDTH px wide, every FRAME_EVERY steps (the export's default
  stride, so every exported row has a frame).

- `capture/unpooled/<step>.pt` every UNPOOLED_EVERY steps (off with HRI_UNPOOLED=0), for the unpooled-activation
  experiment (docs/research/experiments/f2d-unpooled/protocol.md), all float16 and nothing averaged over space:
  `fpn` the coarsest FPN level per camera (cameras, C, H, W); `bev` the last BEV-encoder layer's grid, 4x4
  average-pooled to (C, 50, 50); `track` the last track-decoder layer's queries; `plan` every planning layer's output.
- `capture/cams/<step>_<camera>.jpg`: all six cameras, CAM_WIDTH px wide, every CAMS_EVERY steps (image-model rows).
Both are read-only hooks and file writes: they do not change what the model sees or does.

The upstream agent's top-down `bev` camera is dropped: it is only read for its debug saves, and rendering it costs time.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import carla
import cv2
import numpy as np
import torch
from Bench2DriveZoo.team_code import uniad_b2d_agent
from Bench2DriveZoo.team_code.uniad_b2d_agent import UniadAgent
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from torch import nn
from world_state import WorldStateReader, vector_length

CPU = torch.device("cpu")
FLUSH_EVERY = 200
FRAME_EVERY = 5
FRAME_WIDTH = 256
CAMERA_HEIGHT = 1.60  # CAM_FRONT's z in the upstream sensor list
HIDDEN = 256
UNPOOLED_EVERY, CAMS_EVERY, CAM_WIDTH, BEV_POOL = 20, 10, 800, 4
CAMERAS = ("CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT", "CAM_BACK", "CAM_BACK_LEFT", "CAM_BACK_RIGHT")
# (stage, module path of its layer list), in the order data flows through the model.
STAGES = (
    ("bev_encoder", "pts_bbox_head.transformer.encoder.layers"),
    ("track_decoder", "pts_bbox_head.transformer.decoder.layers"),
    ("seg_encoder", "seg_head.transformer.encoder.layers"),
    ("seg_decoder", "seg_head.transformer.decoder.layers"),
    ("motion_decoder", "motion_head.motionformer.bev_interaction_layers"),
    ("occ_decoder", "occ_head.transformer_decoder.layers"),
    ("planning", "planning_head.attn_module.layers"),
)
DRIVING_STAGE = "planning"


def get_entry_point() -> str:
    return "UniadCaptureAgent"


def channel_mean(output: Any) -> torch.Tensor | None:
    """Mean over every axis but the last (channels); the batch is always 1. None when the layer saw no queries."""
    values = (output[0] if isinstance(output, (tuple, list)) else output).detach().float()
    if values.shape[-1] != HIDDEN:
        raise RuntimeError(f"Expected {HIDDEN} channels last, got shape {tuple(values.shape)}")
    return values.reshape(-1, HIDDEN).mean(dim=0) if values.numel() else None


class UniadCaptureAgent(UniadAgent):
    def setup(self, path_to_conf_file: str) -> None:
        self.trace = None
        self.records: list[dict[str, Any]] = []
        self.collisions: list[dict[str, Any]] = []
        self.collision_sensor: Any = None
        self.world_state: WorldStateReader | None = None
        self.pending_state: dict[str, Any] = {}
        # Upstream joins 'Bench2DriveZoo/...' to the working directory for its anchors and plugin, and names its
        # save folder from `now` unless IS_BENCH2DRIVE is set. It reads that flag at import, so the environment variable
        # is too late here; set the module global instead.
        uniad_b2d_agent.IS_BENCH2DRIVE = "1"
        here = os.getcwd()
        os.chdir(os.environ["UNIAD_ZOO_PARENT"])
        try:
            super().setup(path_to_conf_file)
        finally:
            os.chdir(here)
        self.evidence = Path(os.environ["SIMLINGO_EVIDENCE"])
        self.capture_every = int(os.environ.get("SIMLINGO_CAPTURE_EVERY", "0"))
        self.capture_dir = self.evidence / "capture"
        (self.capture_dir / "frames").mkdir(parents=True, exist_ok=True)
        self.trace = (self.evidence / "controls.jsonl").open("w")
        self.layer_names: list[str] = []
        self.calls: dict[int, list[torch.Tensor]] = {}
        self.vision: torch.Tensor | None = None
        self.forwarded = False
        self.unpooled = os.environ.get("HRI_UNPOOLED", "1") != "0"
        self.raw: dict[str, Any] = {}
        for folder in ("unpooled", "cams"):
            (self.capture_dir / folder).mkdir(exist_ok=True)
        for stage, path in STAGES:
            for index, layer in enumerate(self.model.get_submodule(path)):
                layer.register_forward_hook(self._layer_hook(len(self.layer_names)))
                self.layer_names.append(f"{stage}.{index}")
        self.driving = [i for i, name in enumerate(self.layer_names) if name.startswith(DRIVING_STAGE + ".")]
        self.keep_raw = {self.layer_names.index(name): key for name, key in (
            (max(n for n in self.layer_names if n.startswith("bev_encoder.")), "bev"),
            (max(n for n in self.layer_names if n.startswith("track_decoder.")), "track"))}
        self.keep_raw.update({i: f"plan.{self.layer_names[i].split('.')[1]}" for i in self.driving})
        self.model.img_neck.register_forward_hook(self._neck_hook)
        self.model.register_forward_pre_hook(self._forward_started)
        self.model.register_forward_hook(self._forward_done)

    def sensors(self) -> list[dict[str, Any]]:
        return [sensor for sensor in super().sensors() if sensor["id"] != "bev"]

    def tick(self, input_data: Any) -> dict[str, Any]:
        input_data.setdefault("bev", (0, np.zeros((1, 1, 3), np.uint8)))
        return super().tick(input_data)

    def run_step(self, input_data: Any, timestamp: float) -> Any:
        if self.world_state is None:
            self._attach_to_hero()
        self.pending_state = self._read_state()
        self.forwarded = False
        started = time.monotonic()
        control = super().run_step(input_data, timestamp)
        speed = float(input_data["SPEED"][1]["speed"])
        record = {
            "step": self.step, "simulation_seconds": timestamp, "wall_step_seconds": time.monotonic() - started,
            "speed_metres_per_second": speed, "throttle": float(control.throttle), "steer": float(control.steer),
            "brake": float(control.brake), "model_inference": self.forwarded,
        }
        if not all(np.isfinite(record[key]) for key in ("throttle", "steer", "brake")):
            raise RuntimeError("UniAD returned non-finite vehicle controls")
        if self.step % FRAME_EVERY == 0:
            self._save_frame(input_data["CAM_FRONT"][1])
        if self.unpooled and self.step % CAMS_EVERY == 0:
            try:
                self._save_cams(input_data)
            except Exception as error:
                print(f"camera capture failed at step {self.step}: {type(error).__name__}: {error}", flush=True)
        assert self.trace is not None
        self.trace.write(json.dumps(record) + "\n")
        self.trace.flush()
        print(f"UniAD step {self.step}: speed={speed:.2f} throttle={control.throttle:.3f} "
              f"steer={control.steer:.3f} brake={control.brake:.3f}", flush=True)
        return control

    def _save_frame(self, bgra: np.ndarray) -> None:
        height = round(bgra.shape[0] * FRAME_WIDTH / bgra.shape[1])
        small = cv2.resize(bgra[:, :, :3], (FRAME_WIDTH, height), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(self.capture_dir / "frames" / f"{self.step:06d}.jpg"), small, [cv2.IMWRITE_JPEG_QUALITY, 90])

    def _save_cams(self, input_data: Any) -> None:
        for camera in CAMERAS:
            bgra = input_data[camera][1]
            height = round(bgra.shape[0] * CAM_WIDTH / bgra.shape[1])
            small = cv2.resize(bgra[:, :, :3], (CAM_WIDTH, height), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(self.capture_dir / "cams" / f"{self.step:06d}_{camera}.jpg"), small,
                        [cv2.IMWRITE_JPEG_QUALITY, 90])

    def _capturing(self) -> bool:
        return self.unpooled and self.step % UNPOOLED_EVERY == 0

    def _save_unpooled(self) -> None:
        saved: dict[str, Any] = {}
        for key, value in self.raw.items():
            tensor = (value[0] if isinstance(value, (tuple, list)) else value).detach()
            if key == "bev":  # batch 1: (1, cells, C) or (cells, 1, C), cells a square grid
                grid = tensor.reshape(-1, HIDDEN)
                side = int(round(grid.shape[0] ** 0.5))
                if side * side != grid.shape[0] or side % 50:
                    raise RuntimeError(f"Unexpected BEV shape {tuple(tensor.shape)}")
                grid = grid.T.reshape(1, HIDDEN, side, side).float()
                tensor = nn.functional.avg_pool2d(grid, side // 50)[0]
            saved[key] = tensor.to(torch.float16).to(CPU)
        torch.save(saved, self.capture_dir / "unpooled" / f"{self.step:06d}.pt")

    def _attach_to_hero(self) -> None:
        hero = CarlaDataProvider.get_hero_actor()
        if hero is None:
            raise RuntimeError("No hero vehicle to read state from")
        world = CarlaDataProvider.get_world()
        self.world_state = WorldStateReader(hero, world, CarlaDataProvider.get_map(), CAMERA_HEIGHT)
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

    def _layer_hook(self, index: int) -> Any:
        def hook(_module: nn.Module, _inputs: Any, output: Any) -> None:
            if index in self.keep_raw and self._capturing():
                self.raw[self.keep_raw[index]] = output
            pooled = channel_mean(output)
            if pooled is not None:
                self.calls.setdefault(index, []).append(pooled)
        return hook

    def _neck_hook(self, _module: nn.Module, _inputs: Any, output: Any) -> None:
        levels = [level.detach().float().mean(dim=(0, 2, 3)) for level in output]  # each (cameras, C, H, W)
        self.vision = torch.stack(levels).mean(dim=0)
        if self._capturing():
            self.raw["fpn"] = output[-1]

    def _forward_started(self, _module: nn.Module, _inputs: Any) -> None:
        self.calls = {}
        self.vision = None
        self.raw = {}

    def _forward_done(self, _module: nn.Module, _inputs: Any, _output: Any) -> None:
        self.forwarded = True
        if self.vision is None or not all(index in self.calls for index in self.driving):
            raise RuntimeError("UniAD ran without its image-neck or planning hooks firing")
        fired = [index in self.calls for index in range(len(self.layer_names))]
        # A stage can skip a step (no tracked agents, say); its zeros live on the CPU, so move the means there first.
        layers = torch.stack([torch.stack(self.calls[index]).mean(dim=0).to(CPU) if ran else torch.zeros(HIDDEN)
                              for index, ran in enumerate(fired)])
        self.records.append({"step": self.step, "layer_mean": layers,
                             "layer_driving_mean": layers[self.driving],
                             "vision_bridge_mean": self.vision.to(CPU), "layer_fired": fired,
                             "state": self.pending_state})
        if self._capturing():
            try:  # a capture fault must never end or change the drive; it is logged and the route goes on
                self._save_unpooled()
            except Exception as error:
                print(f"unpooled capture failed at step {self.step}: {type(error).__name__}: {error}", flush=True)
        if len(self.records) % FLUSH_EVERY == 0:
            self._flush()

    def _flush(self) -> None:
        torch.save({"capture_every": self.capture_every, "token_layers": [], "dtype": "float32", "device": "cuda",
                    "layer_names": self.layer_names, "frame_every": FRAME_EVERY, "records": self.records,
                    "collisions": list(self.collisions)}, self.capture_dir / "steps.pt")

    def get_metric_info(self) -> dict[str, Any]:
        """Fail2Drive's base agent has no metric record; the upstream agent asks for one each step."""
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
        super().destroy()
