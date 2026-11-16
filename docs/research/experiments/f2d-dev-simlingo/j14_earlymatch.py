#!/usr/bin/env python3
"""j14: subtract passing routes matched on the early summary, scored on the window.

j05 picks each failure's nearest passing routes in the same approach-window
scores it then subtracts. The window already contains the failure, so those
neighbours partly match the failure and the subtraction removes some of it.
j14 chooses the neighbours in the early summary, the route's first frames,
before the approach window, and subtracts their window scores. The control
is the scene measured before the failure.

Two unwhitened PCAs are fit on every route (j04's helper, whiten=False). Each
keeps --pre-dims components (default 32) and is zero-padded to that width,
the same way as j05, when the rank is short. One PCA is the approach window:
that is the score space. The other is the early summary: that is the match
space. For each failing route the --k nearest passing routes, by Euclidean
distance in the early scores, are averaged in the window scores, and that
mean is subtracted. --k defaults to 10 and is clamped to the number of
passing routes. Passing rows of the returned array are zero. With no passing
route the result is the window scores themselves. With no failing route every
row is zero. When the early matrix equals the window matrix the residual
equals j05's.

A non-finite value in the early matrix raises SystemExit. The H21 cache
stores NaN in its early slots, so this method reads a cache that has them.

Residuals are not standardised. Ward cuts at 2, 3 and 5 go through
cache_methods.axes_from, and the first 10 axes are written. Only the
pass/fail outcome is read. Category, scenario, town and route identity are
not.

Features match j05's scaling. The site is driving_queries. The layers default
to fractions 5/23, 8/23 and 20/23 of the tensor depth. Columns are not
standardised. Each layer is divided by its root-mean-square before
concatenation.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j14_earlymatch.py CACHE \
        --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

PRE_DIMS = 32
K = 10
SUMMARY_SCORE = "window"
SUMMARY_MATCH = "early"


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_j04 = _load("j04_bgmoment")
resolve_layers = _j04.resolve_layers
layer_matrix = _j04.layer_matrix


def _scores(x: np.ndarray, pre_dims: int, seed: int) -> np.ndarray:
    """Unwhitened PCA scores. Zero-pad when the matrix cannot fill pre_dims."""
    scores = np.asarray(_j04._unwhitened(x, pre_dims, seed), dtype=np.float64)
    if pre_dims > 0 and scores.shape[1] < pre_dims:
        padded = np.zeros((scores.shape[0], pre_dims), dtype=np.float64)
        padded[:, : scores.shape[1]] = scores
        return padded
    return scores


def embed_early_match(window: np.ndarray, early: np.ndarray, failing: np.ndarray,
                      pre_dims: int = PRE_DIMS, k: int = K, seed: int = 0) -> np.ndarray:
    """Failing rows are the window score minus the mean window score of early neighbours.

    Neighbours are the k nearest passing routes by Euclidean distance in the
    early scores. Passing rows are zero. k is clamped to the number of passing
    routes. With none, the result is the unwhitened PCA scores of the window.
    With no failing route the result is zeros. The width is pre_dims, padded
    with zero columns when the rank is short of that. A non-finite early
    matrix raises SystemExit.
    """
    window = np.asarray(window, dtype=np.float64)
    early = np.asarray(early, dtype=np.float64)
    failing = np.asarray(failing, dtype=bool)
    if window.ndim != 2 or early.ndim != 2:
        raise ValueError(
            f"j14 expected route-by-feature matrices, got window {window.shape} and early {early.shape}")
    if window.shape[0] != early.shape[0]:
        raise ValueError(
            f"j14 window and early have different numbers of routes: {window.shape[0]} and {early.shape[0]}")
    if not np.isfinite(early).all():
        raise SystemExit("j14: early summary has non-finite values; the H21 cache has NaN early slots")
    if failing.shape != (window.shape[0],):
        raise ValueError("j14 failing mask does not match the number of routes")
    sw = _scores(window, pre_dims, seed)
    n_pass = int((~failing).sum())
    if n_pass < 1:
        return sw
    # Every route passed. There is no failing row to fill.
    if not failing.any():
        return np.zeros_like(sw)
    k_eff = min(int(k), n_pass)
    if k_eff < 1:
        return sw
    out = np.zeros_like(sw)
    pass_sw = sw[~failing]
    fail_sw = sw[failing]
    if k_eff == n_pass:
        out[failing] = fail_sw - pass_sw.mean(axis=0)
        return out
    # Same distance and the same unordered k nearest as j05, in the early scores.
    se = _scores(early, pre_dims, seed)
    pass_se = se[~failing]
    fail_se = se[failing]
    pass_norm = np.einsum("ij,ij->i", pass_se, pass_se)
    fail_norm = np.einsum("ij,ij->i", fail_se, fail_se)
    distances = np.maximum(fail_norm[:, None] + pass_norm[None, :] - 2.0 * fail_se @ pass_se.T, 0.0)
    nearest = np.argpartition(distances, k_eff - 1, axis=1)[:, :k_eff]
    out[failing] = fail_sw - pass_sw[nearest].mean(axis=1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--pre-dims", type=int, default=PRE_DIMS,
                        help="unwhitened PCA width; neighbours are Euclidean in the early scores, residuals in the window scores")
    parser.add_argument("--k", type=int, default=K,
                        help="passing neighbours matched in the early scores and subtracted in the window scores; clamped to how many pass")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if _j04.SUMMARY[SUMMARY_SCORE] != 1 or _j04.SUMMARY[SUMMARY_MATCH] != 2:
        raise SystemExit(
            f"j14: expected window index 1 and early index 2, got {_j04.SUMMARY}")
    cache_methods = _load("cache_methods")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j14: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        failing = np.array([not json.loads(item)["success"] for item in cache["meta"]])
        block = cache[args.site][:, _j04.SUMMARY[SUMMARY_SCORE]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = resolve_layers(n_layers, args.layer)
        window = layer_matrix(cache, args.site, layers, SUMMARY_SCORE)
        early = layer_matrix(cache, args.site, layers, SUMMARY_MATCH)
        features = embed_early_match(
            window, early, failing, pre_dims=args.pre_dims, k=args.k, seed=args.seed)
    name = f"j14-{args.site}-L{'+'.join(map(str, layers))}-earlymatch"
    axes = cache_methods.axes_from(features, failing, ids, name, "ward", cache_methods.CUTS, args.seed)[:10]
    payload = {
        "method": name,
        "settings": {
            "cache": str(args.cache),
            "site": args.site,
            "layer": layers,
            "summary_match": SUMMARY_MATCH,
            "summary_score": SUMMARY_SCORE,
            "pre_dims": args.pre_dims,
            "k": args.k,
            "seed": args.seed,
        },
        "axes": axes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({"method": name, "layer": layers, "k": args.k, "pre_dims": args.pre_dims,
                      "axes": [len(axis["rollouts"]) for axis in axes]}))


if __name__ == "__main__":
    main()
