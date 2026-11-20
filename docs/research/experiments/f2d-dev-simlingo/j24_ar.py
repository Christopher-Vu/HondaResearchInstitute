#!/usr/bin/env python3
"""j24: autoregressive surprise. Where the policy's state goes that its own dynamics did not predict.

Every valid frame of every route (passing and failing) is scaled by one root-mean-square and projected with unwhitened
PCA 16, both exactly as j09. One ridge vector autoregression of order 2 (with an unpenalised intercept) is fit on all
routes' frames, no labels: frame t is predicted from frames t-1 and t-2. Each route gives a residual (observed minus
predicted) at every frame from its third on. Two blocks describe the route: the mean residual vector over its last 10
frames (16-dim direction of surprise), and the residual norm profile (mean and max norm over the route, mean of the
last 10 norms minus mean of the first 10). Each block is standardised over all routes and divided by the square root
of its width (m06's weighting); the failing routes are Ward-clustered at cuts 2/3/5 (cache_methods.axes_from), top 10
in that order.

j25 (--direction-only) drops the norm block and keeps only where the surprise points: each route's late mean residual
vector, in j09's unwhitened PCA space with no per-dimension scaling and no centring (zero stays "as predicted"), is
scaled to unit length, so Ward groups routes by the direction of surprise and not by its size.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j24_ar.py FRAMES --output OUT.json [--alpha 1.0]

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
from sklearn.linear_model import Ridge

ORDER = 2
LATE = 10
ALPHA = 1.0


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


def lagged(seq: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Inputs [x_{t-1}, x_{t-2}] and targets x_t for t = ORDER .. T-1."""
    inputs = np.hstack([seq[ORDER - lag:len(seq) - lag] for lag in range(1, ORDER + 1)])
    return inputs, seq[ORDER:]


def residuals(sequences: list[np.ndarray], alpha: float) -> list[np.ndarray]:
    """One ridge VAR(ORDER) fit on every route's frames; per route, observed minus predicted."""
    if any(len(seq) <= ORDER for seq in sequences):
        raise SystemExit(f"j24: every route needs more than {ORDER} valid frames")
    pairs = [lagged(seq) for seq in sequences]
    model = Ridge(alpha=alpha, fit_intercept=True).fit(
        np.concatenate([x for x, _ in pairs]), np.concatenate([y for _, y in pairs]))
    return [y - model.predict(x) for x, y in pairs]


def surprise_blocks(resid: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """(routes, 16) late mean residual and (routes, 3) norm mean, max, late minus early."""
    direction = np.stack([r[-LATE:].mean(axis=0) for r in resid])
    norms = [np.linalg.norm(r, axis=1) for r in resid]
    profile = np.array([[n.mean(), n.max(), n[-LATE:].mean() - n[:LATE].mean()] for n in norms])
    return direction, profile


def weighted_block(x: np.ndarray) -> np.ndarray:
    return cache_methods.standardise(x) / np.sqrt(x.shape[1])


def unit_directions(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norms > 0, norms, 1.0)


def j24_features(block: np.ndarray, n_frames: np.ndarray, alpha: float = ALPHA,
                 direction_only: bool = False) -> np.ndarray:
    sequences = j09.scale_and_project(j09.sequences_from_block(block, n_frames))
    direction, profile = surprise_blocks(residuals(sequences, alpha))
    if direction_only:
        return unit_directions(direction)
    return np.hstack([weighted_block(direction), weighted_block(profile)])


def j24_axes(block: np.ndarray, n_frames: np.ndarray, failing: np.ndarray, ids: list[str], name: str,
             alpha: float = ALPHA, direction_only: bool = False) -> list[dict]:
    features = j24_features(block, n_frames, alpha, direction_only)
    return cache_methods.axes_from(features, failing, ids, name, "ward", (2, 3, 5))[:10]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=None,
                        help="stored layer index; default is round(8/23*(depth-1)) as in j09")
    parser.add_argument("--depth", type=int, default=24)
    parser.add_argument("--alpha", type=float, default=ALPHA, help="ridge penalty of the autoregression")
    parser.add_argument("--direction-only", action="store_true", help="j25: unit-length late residual direction only")
    parser.add_argument("--name", default=None)
    args = parser.parse_args()
    with np.load(args.frames) as cache:
        ids = [str(value) for value in np.asarray(cache["route_id"]).tolist()]
        failing = np.array([not json.loads(str(item))["success"] for item in np.asarray(cache["meta"])])
        layer, position = j09.resolve_layer(np.asarray(cache["layers"]), args.layer, args.depth)
        site = j09._as_str(cache["site"])
        block = np.asarray(cache["frames"][:, position], dtype=np.float64)
        n_frames = np.asarray(cache["n_frames"], dtype=np.int64)
    name = args.name or f"{'j25' if args.direction_only else 'j24'}-{site}-L{layer}-ar"
    axes = j24_axes(block, n_frames, failing, ids, name, args.alpha, args.direction_only)
    settings = vars(args) | {"frames": str(args.frames), "output": str(args.output), "layer": int(layer)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"method": name, "settings": settings, "axes": axes}, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(axis["rollouts"]) for axis in axes]}))


if __name__ == "__main__":
    main()
