#!/usr/bin/env python3
"""j05: subtract each failure's nearest passing routes, then cluster the residuals.

Activations mix the scene (town, road, scenario) with the failure. On a
clustered background, unwhitened PCA (j01) and the passing-covariance
second-moment embedding (j04) spend their leading coordinates on those
clusters, and the column-standardised m03 embedding beats both. j05 takes the
local background out of each failing route instead of whitening one global
passing covariance.

One unwhitened PCA is fit on every route. Scores stay on the eigenvalue scale
(j04's helper, whiten=False). For each failing route the --k nearest passing
routes, by Euclidean distance in that score space, are averaged, and that mean
is subtracted. --k defaults to 10 and is clamped to the number of passing
routes. Passing rows of the returned array are zero. With no passing route the
result is the unwhitened PCA scores themselves. Only the pass/fail outcome is
read. Category, scenario, town and route identity are not.

Residuals are not standardised. Ward cuts at 2, 3 and 5 go through
cache_methods.axes_from, and the first 10 axes are written.

Features match j04. The site is driving_queries, the summary is the approach
window, and the layers default to fractions 5/23, 8/23 and 20/23 of the tensor
depth. Columns are not standardised. Each layer is divided by its
root-mean-square before concatenation.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j05_knnresid.py CACHE \
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


def embed_knn_residual(x: np.ndarray, failing: np.ndarray, pre_dims: int = PRE_DIMS, k: int = K,
                       seed: int = 0) -> np.ndarray:
    """Failing rows are PCA score minus the mean of the k nearest passing scores.

    Passing rows are zero. k is clamped to the number of passing routes. With
    none, the result is the unwhitened PCA scores of every route. The width is
    pre_dims, padded with zero columns when the rank is short of that.
    """
    data = np.asarray(x, dtype=np.float64)
    failing = np.asarray(failing, dtype=bool)
    if data.ndim != 2:
        raise ValueError(f"j05 expected a route-by-feature matrix, got shape {data.shape}")
    if failing.shape != (data.shape[0],):
        raise ValueError("j05 failing mask does not match the number of routes")
    scores = _scores(data, pre_dims, seed)
    n_pass = int((~failing).sum())
    if n_pass < 1:
        return scores
    # Every route passed. There is no failing row to fill.
    if not failing.any():
        return np.zeros_like(scores)
    k_eff = min(int(k), n_pass)
    if k_eff < 1:
        return scores
    out = np.zeros_like(scores)
    pass_scores = scores[~failing]
    fail_scores = scores[failing]
    if k_eff == n_pass:
        out[failing] = fail_scores - pass_scores.mean(axis=0)
        return out
    pass_norm = np.einsum("ij,ij->i", pass_scores, pass_scores)
    fail_norm = np.einsum("ij,ij->i", fail_scores, fail_scores)
    distances = np.maximum(fail_norm[:, None] + pass_norm[None, :] - 2.0 * fail_scores @ pass_scores.T, 0.0)
    nearest = np.argpartition(distances, k_eff - 1, axis=1)[:, :k_eff]
    out[failing] = fail_scores - pass_scores[nearest].mean(axis=1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(_j04.SUMMARY), default="window")
    parser.add_argument("--pre-dims", type=int, default=PRE_DIMS,
                        help="unwhitened PCA width on all routes; neighbour distances are Euclidean in that space")
    parser.add_argument("--k", type=int, default=K,
                        help="passing neighbours subtracted from each failing route; clamped to how many pass")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache_methods = _load("cache_methods")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j05: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, _j04.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = resolve_layers(n_layers, args.layer)
        features = embed_knn_residual(
            layer_matrix(cache, args.site, layers, args.summary), failing,
            pre_dims=args.pre_dims, k=args.k, seed=args.seed)
    name = f"j05-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    axes = cache_methods.axes_from(features, failing, ids, name, "ward", cache_methods.CUTS, args.seed)[:10]
    payload = {
        "method": name,
        "settings": {
            "cache": str(args.cache),
            "site": args.site,
            "layer": layers,
            "summary": args.summary,
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
