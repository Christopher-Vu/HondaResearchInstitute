#!/usr/bin/env python3
"""j16: frame-to-frame change. How fast and how jerkily the policy's state moves, not where it sits.

A window mean says where a route's frames sit. j16 keeps only how they move: every valid frame of every route
(passing and failing) is scaled by one root-mean-square and projected with unwhitened PCA 16, both exactly as j09.
Each route then gives a sequence of step sizes, the Euclidean norm of the difference between consecutive projected
frames. Six statistics of that sequence describe the route: mean, standard deviation and maximum step, the share of
steps above the 90th percentile of every step in the pool, the mean of the last 10 steps, and straightness (distance
from the first to the last frame over the summed step lengths). The six columns are standardised over all routes and
the failing routes are Ward-clustered at cuts 2/3/5 (cache_methods.axes_from), top 10 in that order.

j17 (--direction) adds the 16-dim net displacement (last projected frame minus first) as a second block; each block is
standardised over all routes and divided by the square root of its width, as m06 weights its blocks.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j16_change.py FRAMES --output OUT.json

FRAMES is the per-frame file (frames_pool.py): route_id, meta, layers, site, frames, n_frames. Pass/fail is read from
meta.success. No scenario, town, route-config or category field is read, and ego_speed is not read. Rows keep the
file's salted order.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

JUMP_PERCENTILE = 90.0
LATE_STEPS = 10


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load("cache_methods")
j09 = _load("j09_hmm")


def step_sizes(sequences: list[np.ndarray]) -> list[np.ndarray]:
    """Norm of each consecutive difference. A route of T frames gives T-1 steps."""
    return [np.linalg.norm(np.diff(seq, axis=0), axis=1) for seq in sequences]


def change_features(sequences: list[np.ndarray]) -> np.ndarray:
    """(routes, 6): mean, sd, max step, share above the pool's 90th percentile, late mean, straightness."""
    steps = step_sizes(sequences)
    if any(len(s) == 0 for s in steps):
        raise SystemExit("j16: every route needs at least two valid frames")
    jump = float(np.percentile(np.concatenate(steps), JUMP_PERCENTILE))
    rows = []
    for seq, s in zip(sequences, steps):
        path = float(s.sum())
        net = float(np.linalg.norm(seq[-1] - seq[0]))
        rows.append([s.mean(), s.std(), s.max(), float(np.mean(s > jump)), s[-LATE_STEPS:].mean(),
                     net / path if path > 0 else 0.0])
    return np.asarray(rows, dtype=np.float64)


def net_displacement(sequences: list[np.ndarray]) -> np.ndarray:
    return np.stack([seq[-1] - seq[0] for seq in sequences])


def weighted_block(x: np.ndarray) -> np.ndarray:
    return cache_methods.standardise(x) / np.sqrt(x.shape[1])


def j16_axes(block: np.ndarray, n_frames: np.ndarray, failing: np.ndarray, ids: list[str], name: str,
             seed: int = 0, direction: bool = False) -> list[dict]:
    sequences = j09.scale_and_project(j09.sequences_from_block(block, n_frames))
    steps = change_features(sequences)
    features = (np.hstack([weighted_block(steps), weighted_block(net_displacement(sequences))]) if direction
                else cache_methods.standardise(steps))
    return cache_methods.axes_from(features, failing, ids, name, "ward", (2, 3, 5), seed=seed)[:10]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=None,
                        help="stored layer index; default is round(8/23*(depth-1)) as in j09")
    parser.add_argument("--depth", type=int, default=24)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--direction", action="store_true", help="j17: add the net displacement block")
    args = parser.parse_args()
    with np.load(args.frames) as cache:
        ids = [str(value) for value in np.asarray(cache["route_id"]).tolist()]
        failing = np.array([not json.loads(str(item))["success"] for item in np.asarray(cache["meta"])])
        layer, position = j09.resolve_layer(np.asarray(cache["layers"]), args.layer, args.depth)
        site = j09._as_str(cache["site"])
        block = np.asarray(cache["frames"][:, position], dtype=np.float64)
        n_frames = np.asarray(cache["n_frames"], dtype=np.int64)
    name = f"{'j17' if args.direction else 'j16'}-{site}-L{layer}-change"
    axes = j16_axes(block, n_frames, failing, ids, name, args.seed, args.direction)
    settings = vars(args) | {"frames": str(args.frames), "output": str(args.output), "layer": int(layer)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"method": name, "settings": settings, "axes": axes}, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(axis["rollouts"]) for axis in axes]}))


if __name__ == "__main__":
    main()
