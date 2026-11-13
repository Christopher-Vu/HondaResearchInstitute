"""Open-loop knock-out of each decoder layer at each hook site (docs/steps/04-layer-site-ablation.md, Part B).

    .runtime/policy-venv/bin/python adapters/simlingo/ablate_replay.py RUN_DIR... --scored ROUTES_JSONL \
        --output OUT_DIR --device cuda

Replays saved model inputs (capture/inputs/*.pt) in the dtype they were logged in. For decoder layer L and
positions P, the layer's update (output minus input) at P is replaced by its mean over a calibration set:
per position for the 30 driving queries (fixed learned tokens), one vector for the other positions. Sites:
driving_queries, context (every other position), all_tokens (both), plus vision_bridge (InternVL's mlp1
output replaced by its mean token). Each condition's effect is the mean distance between the intact and the
knocked-out route waypoints and speed waypoints of one frame.

Frames: `--per-route` drawn per scored route (seed 0); calibration: `--calibration` frames from other
draws (seed 1), never scored. Writes OUT_DIR/means.pt (the calibration means, which `install` applies in a
live run), effects.npz (frames x conditions x 2) and summary.json, the last two rewritten every 25 frames.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from replay_capture import decoder, driving_query_count, load_in_dtype, move
from verify_checkpoint import ROOT

SITES = ("driving_queries", "context", "all_tokens")


def vision_bridge(model: Any) -> Any:
    """InternVL's mlp1 projector, as capture_agent finds it (not imported: that module needs CARLA)."""
    bridges = [module for name, module in model.named_modules() if name.endswith("mlp1")]
    if len(bridges) != 1:
        raise RuntimeError(f"Expected one mlp1 vision bridge, found {len(bridges)}")
    return bridges[0]


class Knockout:
    """Forward hooks on every decoder layer and the vision bridge; collects mean updates or applies one."""

    def __init__(self, model: Any, n_queries: int) -> None:
        self.n = n_queries
        self.layers = list(decoder(model).layers)
        self.mode = "off"
        self.target: tuple[str, int] | None = None
        self.sum_q: dict[int, torch.Tensor] = {}
        self.sum_c: dict[int, torch.Tensor] = {}
        self.count_c: dict[int, int] = {}
        self.frames = 0
        self.bridge_sum: torch.Tensor | None = None
        self.bridge_count = 0
        self.means: dict[str, Any] = {}
        for index, layer in enumerate(self.layers):
            layer.register_forward_hook(self._hook(index), with_kwargs=True)
        vision_bridge(model).register_forward_hook(self._bridge_hook)

    def _hook(self, index: int) -> Any:
        def hook(_module: Any, args: tuple, kwargs: dict, output: Any) -> Any:
            if self.mode == "off":
                return None
            hidden_in = args[0] if args else kwargs["hidden_states"]
            out = output[0] if isinstance(output, tuple) else output
            if self.mode == "collect":
                update = (out - hidden_in)[0].float()
                q, c = update[-self.n:], update[:-self.n]
                self.sum_q[index] = self.sum_q.get(index, 0) + q
                self.sum_c[index] = self.sum_c.get(index, 0) + c.sum(dim=0)
                self.count_c[index] = self.count_c.get(index, 0) + c.shape[0]
                return None
            assert self.target is not None
            site, layer = self.target
            if layer != index or site in ("vision_bridge", "none"):
                return None
            mean_q = self.means["q"][index].to(out.device, out.dtype)
            mean_c = self.means["c"][index].to(out.device, out.dtype)
            new = out.clone()
            if site in ("driving_queries", "all_tokens"):
                new[0, -self.n:] = hidden_in[0, -self.n:] + mean_q
            if site in ("context", "all_tokens"):
                new[0, :-self.n] = hidden_in[0, :-self.n] + mean_c
            return (new, *output[1:]) if isinstance(output, tuple) else new
        return hook

    def _bridge_hook(self, _module: Any, _inputs: Any, output: torch.Tensor) -> Any:
        if self.mode == "collect":
            flat = output.float().reshape(-1, output.shape[-1])
            self.bridge_sum = flat.sum(dim=0) if self.bridge_sum is None else self.bridge_sum + flat.sum(dim=0)
            self.bridge_count += flat.shape[0]
        elif self.mode == "ablate" and self.target is not None and self.target[0] == "vision_bridge":
            mean = self.means["bridge"].to(output.device, output.dtype)
            return mean.expand_as(output).clone()
        return None

    def finish_calibration(self) -> dict[str, Any]:
        """Mean updates from the collected sums; `ablate` mode reads these, as does the live agent."""
        assert self.bridge_sum is not None
        self.means = {"q": {i: (self.sum_q[i] / self.frames).cpu() for i in self.sum_q},
                      "c": {i: (self.sum_c[i] / self.count_c[i]).cpu() for i in self.sum_c},
                      "bridge": (self.bridge_sum / self.bridge_count).cpu(), "frames": self.frames}
        return self.means


def install(model: Any, site: str, layer: int, means_path: Path) -> Knockout:
    """Apply one knock-out for every forward pass of `model` (closed loop, Part C)."""
    knock = Knockout(model, driving_query_count(model))
    knock.means = torch.load(means_path, weights_only=False)
    knock.mode, knock.target = "ablate", (site, layer)
    return knock


def saved_frames(run_dirs: list[Path], scored: set[str]) -> dict[str, list[Path]]:
    out = {}
    for run in run_dirs:
        for route_dir in sorted(run.glob("route-*")):
            route_id = route_dir.name.removeprefix("route-")
            if route_id in scored and route_id not in out:
                inputs = sorted((route_dir / "capture/inputs").glob("*.pt"))
                if inputs:
                    out[route_id] = inputs
    return out


def draw(frames: dict[str, list[Path]], per_route: int, calibration: int) -> tuple[list[Path], list[Path]]:
    rng = random.Random(0)
    scoring = [p for rid in sorted(frames) for p in rng.sample(frames[rid], min(per_route, len(frames[rid])))]
    chosen = set(scoring)
    rest = [p for rid in sorted(frames) for p in frames[rid] if p not in chosen]
    return scoring, random.Random(1).sample(rest, min(calibration, len(rest)))


def load_frame(path: Path, dtype: torch.dtype, device: torch.device) -> Any:
    frame = torch.load(path, weights_only=False)
    return move(frame._replace(camera_images=frame.camera_images.to(dtype)), device)


def plan(model: Any, frame: Any) -> tuple[torch.Tensor, torch.Tensor]:
    with torch.inference_mode():
        speed_wps, route, _language = model(frame)
    return speed_wps.float().reshape(-1, 2), route.float().reshape(-1, 2)


def summarize(conditions: list[tuple[str, int]], effects: np.ndarray, done: int, frames: list[Path],
              seconds: float) -> dict[str, Any]:
    rows = []
    for j, (site, layer) in enumerate(conditions):
        route, speed = effects[:done, j, 0], effects[:done, j, 1]
        rows.append({"site": site, "layer": layer,
                     "route_median_m": float(np.median(route)), "route_p90_m": float(np.percentile(route, 90)),
                     "route_share_over_1m": float(np.mean(route > 1.0)),
                     "speed_median_m": float(np.median(speed)), "speed_p90_m": float(np.percentile(speed, 90))})
    return {"frames_done": done, "frames_planned": len(frames), "seconds": round(seconds, 1),
            "conditions": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--scored", type=Path, required=True, help="routes.jsonl; only routes with a score")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--per-route", type=int, default=4)
    parser.add_argument("--calibration", type=int, default=100)
    parser.add_argument("--limit", type=int, default=0, help="score only the first N frames (smoke test)")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.scored.read_text().splitlines() if line.strip()]
    scored = {str(r["id"]) for r in rows if r.get("score_composed") is not None and not r.get("scenario_skipped")}
    frames, calibration = draw(saved_frames(args.runs, scored), args.per_route, args.calibration)
    frames = frames[: args.limit or None]
    sys.path.insert(0, str(ROOT / ".runtime/simlingo"))
    device, dtype = torch.device(args.device), torch.bfloat16
    model = load_in_dtype(dtype).to(device).eval()
    knock = Knockout(model, driving_query_count(model))
    knock.mode = "collect"
    for path in calibration:
        plan(model, load_frame(path, dtype, device))
        knock.frames += 1
    args.output.mkdir(parents=True, exist_ok=True)
    torch.save(knock.finish_calibration(), args.output / "means.pt")
    # ("none", -1) reruns the intact model: the floor that GPU nondeterminism sets under every effect.
    conditions = ([(site, layer) for site in SITES for layer in range(len(knock.layers))]
                  + [("vision_bridge", -1), ("none", -1)])
    effects: np.ndarray = np.zeros((len(frames), len(conditions), 2), dtype=np.float32)
    (args.output / "frames.json").write_text(json.dumps({"scoring": [str(p) for p in frames],
                                                         "calibration": [str(p) for p in calibration]}) + "\n")
    started = time.monotonic()
    for i, path in enumerate(frames):
        frame = load_frame(path, dtype, device)
        knock.mode = "off"
        speed0, route0 = plan(model, frame)
        knock.mode = "ablate"
        for j, condition in enumerate(conditions):
            knock.target = condition
            speed, route = plan(model, frame)
            effects[i, j] = [(route - route0).norm(dim=1).mean().item(), (speed - speed0).norm(dim=1).mean().item()]
        if (i + 1) % 25 == 0 or i + 1 == len(frames):
            np.savez_compressed(args.output / "effects.npz", effects=effects[: i + 1],
                                conditions=np.array([f"{s}:{l}" for s, l in conditions]))
            summary = summarize(conditions, effects, i + 1, frames, time.monotonic() - started)
            (args.output / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
            print(f"{i + 1}/{len(frames)} frames, {time.monotonic() - started:.0f} s", flush=True)


if __name__ == "__main__":
    main()
