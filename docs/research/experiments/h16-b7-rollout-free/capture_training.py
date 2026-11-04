"""H16, B7 variant A: read SimLingo's stored training frames through the model, with no simulator.

    PYTHONPATH=adapters/simlingo:src python docs/research/experiments/h16-b7-rollout-free/capture_training.py capture \\
        --stage STAGE --output results/savio/h16/training --task 0 --device cuda --dtype bfloat16
    ... capture_training.py check --rollouts results/savio/40715498 --stage STAGE --output CHECK.json

`capture` writes one `<route name>.npz` per listed route found under STAGE: `driving_queries`, (frames, hidden), the
layer-10 driving-query mean of every stored frame in float16, as a rollout shard stores that site, and `frame`, the
stored frame numbers. The forward pass stops inside layer 10, since nothing later can change that layer's output.

`check` compares this input path with what the agent itself saved on unplanted rollouts, before any capture is paid
for: a rebuilt input must equal the saved one exactly, stopping early must equal a full forward pass, and the mean must
match the one logged. It also runs training frames to the route head, the one check that reads the stored measurements:
a wrong target point moves the route by metres on a bend. It reads waypoints only, never a latent.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from export_activations import float16_checked
from PIL import Image
from replay_capture import ROOT, decoder, driving_query_count, load_in_dtype, move
from torch.utils.data import DataLoader, Dataset
from transformers import AutoConfig, AutoTokenizer
from verify_checkpoint import SPECIAL_TOKENS

from baselines.b7_variant_a import (
    driving_prompt,
    equal_spaced_route,
    frame_stems,
    measurement_inputs,
    read_measurement,
    read_route_list,
    route_bend_m,
    route_check_saw_a_bend,
    route_key,
)

sys.path.insert(0, str(ROOT / ".runtime/simlingo"))
from simlingo_training.utils.custom_types import DrivingInput, LanguageLabel  # noqa: E402
from simlingo_training.utils.internvl2_utils import build_transform, dynamic_preprocess  # noqa: E402
from team_code.simlingo_utils import get_camera_extrinsics, get_camera_intrinsics  # noqa: E402

LAYER = 10
BASE_MODEL = ROOT / ".runtime/InternVL2-1B"
TILE_SIZE = 448
TILES = 2
CAMERA_FOV = 110
RELATIVE_MEAN_TOLERANCE = 1e-2
ROUTE_HEAD_TOLERANCE_M = 1.0


class PromptLabels:
    """Tokenised prompts, built the way the agent builds them. Only the speed changes the text, so text is cached."""

    def __init__(self, tokenizer: Any) -> None:
        self.tokenizer = tokenizer
        spec = importlib.util.spec_from_file_location("get_conv_template", BASE_MODEL / "conversation.py")
        self.conversation = importlib.util.module_from_spec(spec)
        sys.modules["get_conv_template"] = self.conversation
        spec.loader.exec_module(self.conversation)
        config = AutoConfig.from_pretrained(BASE_MODEL, trust_remote_code=True)
        patches = (config.force_image_size or config.vision_config.image_size) // config.vision_config.patch_size
        self.image_tokens = int(patches ** 2 * config.downsample_ratio ** 2)
        self.target_token = tokenizer.convert_tokens_to_ids("<TARGET_POINT>")
        self.tokenised = lru_cache(maxsize=None)(self._tokenise)

    def _query(self, speed: float) -> str:
        template = self.conversation.get_conv_template("internlm2-chat")
        template.append_message(template.roles[0], f"<image>\n{driving_prompt(speed)}")
        template.append_message(template.roles[1], None)
        system = template.system_template.replace("{system_message}", template.system_message) + template.sep
        image = "<img>" + "<IMG_CONTEXT>" * self.image_tokens * TILES + "</img>"
        return template.get_prompt().replace(system, "").replace("<image>", image, 1)

    def _tokenise(self, speed: float) -> tuple[str, torch.Tensor]:
        query = self._query(speed)
        return query, self.tokenizer([query], padding=True, return_tensors="pt", add_special_tokens=False)["input_ids"]

    def label(self, speed: float, target_points: np.ndarray) -> Any:
        query, ids = self.tokenised(speed)
        valid = ids != self.tokenizer.pad_token_id
        return LanguageLabel(phrase_ids=ids, phrase_valid=valid, phrase_mask=valid,
                             placeholder_values=[{self.target_token: target_points}],
                             language_string=[query], loss_masking=None)


def camera_tiles(bgr: np.ndarray) -> torch.Tensor:
    """(1, 1, tiles, 3, 448, 448) from a decoded JPEG, as agent_simlingo.tick and the training loader crop and tile it."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb = rgb[:int(rgb.shape[0] - (rgb.shape[0] * 4.8) // 16), :, :]
    tiles = dynamic_preprocess(Image.fromarray(rgb), image_size=TILE_SIZE, use_thumbnail=False, max_num=TILES)
    transform = build_transform(input_size=TILE_SIZE)
    return torch.stack([transform(tile) for tile in tiles])[None, None]


def driving_input(tiles: torch.Tensor, speed: float, target_points: np.ndarray, labels: PromptLabels,
                  dtype: torch.dtype) -> Any:
    label = labels.label(speed, target_points)
    intrinsics = get_camera_intrinsics(TILE_SIZE, TILE_SIZE, CAMERA_FOV).unsqueeze(0).view(1, 3, 3).float()
    extrinsics = get_camera_extrinsics().unsqueeze(0).view(1, 4, 4).float()
    return DrivingInput(camera_images=tiles.to(dtype), image_sizes=None, camera_intrinsics=(intrinsics,),
                        camera_extrinsics=(extrinsics,), vehicle_speed=torch.FloatTensor([speed]).unsqueeze(0),
                        target_point=torch.from_numpy(target_points[0][None]).float(), prompt=label,
                        prompt_inference=label)


class _ReachedLayer(Exception):
    pass


class LayerMean:
    """The driving-query mean of one decoder layer's output, computed as capture_agent logs layer_driving_mean."""

    def __init__(self, model: Any, device: torch.device) -> None:
        self.model, self.device = model, device
        self.driving_tokens = driving_query_count(model)
        self.stop = True
        self.mean: torch.Tensor | None = None
        decoder(model).layers[LAYER].register_forward_hook(self._hook)

    def _hook(self, _module: Any, _inputs: Any, output: Any) -> None:
        tokens = output[0] if isinstance(output, tuple) else output
        self.mean = tokens[0, -self.driving_tokens:].float().mean(dim=0).cpu()
        if self.stop:
            raise _ReachedLayer

    @torch.inference_mode()
    def read(self, frame: Any) -> torch.Tensor:
        self.stop = True
        try:
            self.model(move(frame, self.device))
        except _ReachedLayer:
            pass
        assert self.mean is not None
        return self.mean

    @torch.inference_mode()
    def full(self, frame: Any) -> tuple[torch.Tensor, np.ndarray]:
        self.stop = False
        _speed_wps, route, _language = self.model(move(frame, self.device))
        assert self.mean is not None
        return self.mean, route.float().cpu().numpy().reshape(-1, 2)


def load(device: torch.device, dtype: torch.dtype) -> tuple[LayerMean, PromptLabels]:
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, local_files_only=True)
    tokenizer.add_special_tokens({"additional_special_tokens": SPECIAL_TOKENS})
    tokenizer.padding_side = "left"
    model = load_in_dtype(dtype)
    model.to(device)
    return LayerMean(model, device), PromptLabels(tokenizer)


@dataclass(frozen=True)
class FrameRef:
    route: str
    stem: str


class TrainingFrames(Dataset):
    """Reads and tiles frames in loader workers, so the GPU waits on the forward pass and not on JPEG decoding."""

    def __init__(self, stage: Path, routes: dict[str, list[str]]) -> None:
        self.stage = stage
        self.refs = [FrameRef(route, stem) for route, stems in routes.items() for stem in stems]

    def __len__(self) -> int:
        return len(self.refs)

    def __getitem__(self, position: int) -> dict[str, Any]:
        ref = self.refs[position]
        try:
            bgr = cv2.imread(str(self.stage / ref.route / "rgb" / f"{ref.stem}.jpg"), cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError(f"unreadable image {ref.stem}")
            speed, target_points = measurement_inputs(read_measurement(self.stage / ref.route, ref.stem))
            return {"position": position, "tiles": camera_tiles(bgr), "speed": speed, "target_points": target_points}
        except (ValueError, OSError, EOFError, KeyError) as error:
            return {"position": position, "error": f"{ref.stem}: {error}"}


def routes_to_capture(stage: Path, output: Path) -> tuple[dict[str, list[str]], dict[str, str], int]:
    """Listed routes this chunk holds and no earlier run finished, then those that cannot be read, then those done."""
    routes, lost, done = {}, {}, 0
    for route in read_route_list():
        if not (stage / route).is_dir():
            continue
        if (output / f"{route_key(route)}.npz").exists():
            done += 1
            continue
        try:
            routes[route] = frame_stems(stage / route)
        except ValueError as error:
            lost[route] = str(error)
    return routes, lost, done


def save_route(output: Path, route: str, stems: list[str], means: list[torch.Tensor]) -> None:
    pending = output / f"{route_key(route)}.tmp.npz"
    np.savez(pending, driving_queries=float16_checked(torch.stack(means).numpy(), route),
             frame=np.array([int(stem) for stem in stems], dtype=np.int64))
    os.replace(pending, output / f"{route_key(route)}.npz")


def capture(args: argparse.Namespace) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    routes, lost, done = routes_to_capture(args.stage, args.output)
    reader, labels = load(torch.device(args.device), getattr(torch, args.dtype))
    frames = TrainingFrames(args.stage, routes)
    loader = DataLoader(frames, batch_size=None, num_workers=args.workers, prefetch_factor=8 if args.workers else None)
    started = time.monotonic()
    means: list[torch.Tensor] = []
    captured = count = 0
    for item in loader:
        ref = frames.refs[int(item["position"])]
        if "error" in item:
            lost.setdefault(ref.route, item["error"])
        elif ref.route not in lost:
            target_points = item["target_points"].numpy()
            means.append(reader.read(driving_input(item["tiles"], item["speed"], target_points, labels,
                                                   getattr(torch, args.dtype))))
            count += 1
        if ref.stem == routes[ref.route][-1]:
            if ref.route not in lost:
                save_route(args.output, ref.route, routes[ref.route], means)
                captured += 1
            means = []
    seconds = time.monotonic() - started
    summary = {"task": args.task, "routes_captured": captured, "routes_already_done": done, "lost": lost,
               "frames": count, "seconds": round(seconds, 1), "seconds_per_frame": seconds / max(count, 1)}
    (args.output / f"capture-task-{args.task}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "lost"} | {"lost": len(lost)}))


def rebuilt_from_saved(saved: Any, png: Path, labels: PromptLabels, dtype: torch.dtype) -> Any:
    """The saved frame PNG and the saved speed and target points through this file's input path."""
    bgr = np.asarray(Image.open(png).convert("RGB"))[:, :, ::-1]
    _, jpeg = cv2.imencode(".jpg", np.ascontiguousarray(bgr))
    tiles = camera_tiles(cv2.imdecode(jpeg, cv2.IMREAD_UNCHANGED))
    speed = round(float(saved.vehicle_speed), 1)
    target_points = saved.prompt.placeholder_values[0][labels.target_token]
    return driving_input(tiles, speed, target_points, labels, dtype)


def inputs_equal(built: Any, saved: Any, target_token: int) -> dict[str, bool]:
    return {
        "camera_images": torch.equal(built.camera_images, saved.camera_images),
        "phrase_ids": torch.equal(built.prompt.phrase_ids, saved.prompt.phrase_ids),
        "language_string": built.prompt.language_string == saved.prompt.language_string,
        "target_points": np.array_equal(built.prompt.placeholder_values[0][target_token],
                                        saved.prompt.placeholder_values[0][target_token]),
        "vehicle_speed": torch.equal(built.vehicle_speed, saved.vehicle_speed),
        "target_point": torch.equal(built.target_point, saved.target_point),
        "intrinsics": torch.equal(built.camera_intrinsics[0], saved.camera_intrinsics[0]),
        "extrinsics": torch.equal(built.camera_extrinsics[0], saved.camera_extrinsics[0]),
    }


def steps_with_frame_and_input(route_dir: Path) -> list[str]:
    inputs = {path.stem for path in (route_dir / "capture/inputs").glob("*.pt")}
    return sorted(inputs & {path.stem for path in (route_dir / "frames").glob("*.png")})


def check_rollout_frame(route_dir: Path, stem: str, logged: dict[int, Any], reader: LayerMean, labels: PromptLabels,
                        dtype: torch.dtype) -> dict[str, Any]:
    saved = torch.load(route_dir / "capture/inputs" / f"{stem}.pt", weights_only=False)
    built = rebuilt_from_saved(saved, route_dir / "frames" / f"{stem}.png", labels, dtype)
    equal = inputs_equal(built, saved, labels.target_token)
    started = time.monotonic()
    early = reader.read(built)
    early_seconds = time.monotonic() - started
    again = reader.read(built)
    started = time.monotonic()
    full, _route = reader.full(built)
    full_seconds = time.monotonic() - started
    expected = logged[int(stem)]["layer_driving_mean"][LAYER].float()
    return {"route": route_dir.name, "step": int(stem), "unequal": [name for name, same in equal.items() if not same],
            "early_equals_full": bool(torch.equal(early, full) and torch.equal(again, full)),
            "relative_mean_error": float((early - expected).norm() / expected.norm()),
            "early_seconds": round(early_seconds, 4), "full_seconds": round(full_seconds, 4)}


def check_rollouts(rollouts: Path, reader: LayerMean, labels: PromptLabels, dtype: torch.dtype, routes: int, frames: int
                   ) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    checked = 0
    for route_dir in sorted(rollouts.glob("route-*")) + [rollouts]:
        stems = steps_with_frame_and_input(route_dir)
        if not stems:
            continue
        records = torch.load(route_dir / "capture/steps.pt", weights_only=False)["records"]
        logged = {record["step"]: record for record in records}
        usable = [stem for stem in stems if int(stem) in logged and int(stem) > 0]
        rows += [check_rollout_frame(route_dir, stem, logged, reader, labels, dtype) for stem in usable[:frames]]
        checked += 1
        if checked == routes:
            break
    return rows


def route_head_error(predicted: np.ndarray, stored_route: np.ndarray) -> float:
    return float(np.linalg.norm(predicted - equal_spaced_route(stored_route), axis=1).mean())


def sharpest_frame(stage: Path, routes: list[str]) -> tuple[Path, str] | None:
    """The frame whose stored route bends most, over the routes on disk. A route the cut stream truncated is skipped."""
    best, sharpest = None, -1.0
    for route in routes:
        try:
            for stem in frame_stems(stage / route):
                bend = route_bend_m(np.array(read_measurement(stage / route, stem)["route"]))
                if bend > sharpest:
                    best, sharpest = (stage / route, stem), bend
        except (ValueError, OSError, EOFError):
            continue
    return best


def route_head_row(route_dir: Path, stem: str, reader: LayerMean, labels: PromptLabels, dtype: torch.dtype) -> dict[str, Any]:
    measurement = read_measurement(route_dir, stem)
    speed, target_points = measurement_inputs(measurement)
    stored_route = np.array(measurement["route"])
    tiles = camera_tiles(cv2.imread(str(route_dir / "rgb" / f"{stem}.jpg"), cv2.IMREAD_COLOR))
    _mean, predicted = reader.full(driving_input(tiles, speed, target_points, labels, dtype))
    return {"route": route_dir.name, "frame": int(stem), "speed": speed, "route_bend_m": route_bend_m(stored_route),
            "route_head_error_m": route_head_error(predicted, stored_route)}


def check_training(stage: Path, reader: LayerMean, labels: PromptLabels, dtype: torch.dtype, frames: int
                   ) -> list[dict[str, Any]]:
    listed = [route for route in read_route_list() if (stage / route / "rgb").is_dir()]
    if not listed:
        raise ValueError(f"no listed route under {stage}")
    route_dir = stage / listed[0]
    stems = frame_stems(route_dir)
    picks = [(route_dir, stem) for stem in stems[:: max(1, len(stems) // frames)][:frames]]
    sharpest = sharpest_frame(stage, listed)
    if sharpest is not None and sharpest not in picks:
        picks.append(sharpest)
    return [route_head_row(directory, stem, reader, labels, dtype) for directory, stem in picks]


def check_verdict(rollout_rows: list[dict[str, Any]], training_rows: list[dict[str, Any]]) -> dict[str, Any]:
    head = max(row["route_head_error_m"] for row in training_rows)
    worst = max(row["relative_mean_error"] for row in rollout_rows)
    verdict = {"inputs_equal": not any(row["unequal"] for row in rollout_rows),
               "early_equals_full": all(row["early_equals_full"] for row in rollout_rows),
               "worst_relative_mean_error": worst, "mean_within_tolerance": worst <= RELATIVE_MEAN_TOLERANCE,
               "worst_route_head_error_m": head, "route_head_within_tolerance": head <= ROUTE_HEAD_TOLERANCE_M,
               "route_head_saw_a_bend": route_check_saw_a_bend(training_rows),
               "median_early_seconds": float(np.median([row["early_seconds"] for row in rollout_rows])),
               "median_full_seconds": float(np.median([row["full_seconds"] for row in rollout_rows]))}
    verdict["passes"] = (verdict["inputs_equal"] and verdict["early_equals_full"] and verdict["mean_within_tolerance"]
                         and verdict["route_head_within_tolerance"] and verdict["route_head_saw_a_bend"])
    return verdict


def check(args: argparse.Namespace) -> None:
    dtype = getattr(torch, args.dtype)
    reader, labels = load(torch.device(args.device), dtype)
    rollout_rows = check_rollouts(args.rollouts, reader, labels, dtype, args.check_routes, args.check_frames)
    training_rows = check_training(args.stage, reader, labels, dtype, args.check_frames)
    verdict = check_verdict(rollout_rows, training_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({**verdict, "rollouts": rollout_rows, "training": training_rows}, indent=2) + "\n")
    print(json.dumps(verdict, indent=2))
    if not verdict["passes"]:
        raise SystemExit("input check failed: do not submit the capture")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["capture", "check"])
    parser.add_argument("--stage", type=Path, required=True, help="holds route directories at their paths in the tars")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", choices=["float32", "bfloat16"], default="bfloat16")
    parser.add_argument("--task", type=int, default=0)
    parser.add_argument("--workers", type=int, default=7)
    parser.add_argument("--rollouts", type=Path, help="check: a rollout directory, or a parent of route-<id> directories")
    parser.add_argument("--check-routes", type=int, default=5)
    parser.add_argument("--check-frames", type=int, default=8)
    args = parser.parse_args()
    torch.set_num_threads(8)
    cv2.setNumThreads(0)
    {"capture": capture, "check": check}[args.mode](args)


if __name__ == "__main__":
    main()
