#!/usr/bin/env python3
"""j13: remove the local passing tangent, then cluster what is left.

j05 subtracts the mean of the k nearest passing routes. A failure that only
slides along the passing routes next to it still gets a residual, because the
mean removes the centre of that neighbourhood and nothing else. j13 also
removes the neighbourhood's tangent.

One unwhitened PCA is fit on every route, the same scores as j05. For each
failing route the k nearest passing routes are chosen by Euclidean distance
in that score space, with the same distance and argpartition as j05. k
defaults to 10 and is clamped to the number of passing routes. The residual
starts as the score minus the neighbour mean. The centred neighbours' top t
right singular vectors are the tangent; t defaults to 2 and is clamped to
k - 1. A direction is kept only when its singular value exceeds 1e-12 times
the largest one. The residual's projection on those directions is removed.
With none left, the residual is j05's. With --tangent-dims 0 the features
equal j05.

Residuals are not whitened and not normalised. Passing rows are zero. With
no passing route the result is the unwhitened PCA scores. With no failing
route every row is zero.

Ward cuts at 2, 3 and 5 go through cache_methods.axes_from, and the first 10
axes are written. Only the cache is read: route ids, the success flag, and
the activation site.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j13_knntangent.py CACHE \
        --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


TANGENT_DIMS = 2


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j05 = _load("j05_knnresid")
resolve_layers = j05.resolve_layers
layer_matrix = j05.layer_matrix


def _tangent_basis(centered: np.ndarray, t: int) -> np.ndarray:
    """Top right singular vectors of centred neighbours, as orthonormal rows.

    t is already clamped to k - 1. Directions whose singular value is not
    strictly above 1e-12 times the largest are dropped, so a flat
    neighbourhood does not invent a tangent out of numerical noise.
    """
    width = int(centered.shape[-1])
    empty = np.zeros((0, width), dtype=np.float64)
    if t < 1 or centered.shape[0] < 2:
        return empty
    _left, singular, vt = np.linalg.svd(np.asarray(centered, dtype=np.float64), full_matrices=False)
    if singular.size == 0 or not (float(singular[0]) > 0.0):
        return empty
    thresh = 1e-12 * float(singular[0])
    t_eff = 0
    limit = min(int(t), int(singular.shape[0]))
    while t_eff < limit and float(singular[t_eff]) > thresh:
        t_eff += 1
    if t_eff < 1:
        return empty
    return np.asarray(vt[:t_eff], dtype=np.float64)


def _apply_basis(basis: np.ndarray, residual: np.ndarray) -> np.ndarray:
    """r - U^T (U r), with the rows of U orthonormal. No rows leaves r as it is."""
    if basis.shape[0] == 0:
        return residual
    if residual.ndim == 1:
        return residual - basis.T @ (basis @ residual)
    return residual - (residual @ basis.T) @ basis


def _strip(centered: np.ndarray, residual: np.ndarray, tangent_dims: int, k_eff: int) -> np.ndarray:
    """Remove the tangent from residual. centered is (k, d) or one (k, d) block per row."""
    t = min(int(tangent_dims), k_eff - 1)
    if t < 1:
        return residual
    if centered.ndim == 2:
        return _apply_basis(_tangent_basis(centered, t), residual)
    kept = np.empty_like(residual)
    for i in range(residual.shape[0]):
        kept[i] = _apply_basis(_tangent_basis(centered[i], t), residual[i])
    return kept


def embed_knn_tangent(x: np.ndarray, failing: np.ndarray, pre_dims: int = j05.PRE_DIMS, k: int = j05.K,
                      tangent_dims: int = TANGENT_DIMS, seed: int = 0) -> np.ndarray:
    """Failing rows are the j05 residual with the local passing tangent removed.

    Passing rows are zero. k is clamped to the number of passing routes.
    tangent_dims is clamped to k - 1. With no passing route the result is the
    unwhitened PCA scores of every route. With no failing route the result is
    zeros. tangent_dims 0 is j05's residual, including the same neighbour mean.
    """
    data = np.asarray(x, dtype=np.float64)
    failing = np.asarray(failing, dtype=bool)
    if data.ndim != 2:
        raise ValueError(f"j13 expected a route-by-feature matrix, got shape {data.shape}")
    if failing.shape != (data.shape[0],):
        raise ValueError("j13 failing mask does not match the number of routes")
    scores = j05._scores(data, pre_dims, seed)
    n_pass = int((~failing).sum())
    if n_pass < 1:
        return scores
    if not failing.any():
        return np.zeros_like(scores)
    k_eff = min(int(k), n_pass)
    if k_eff < 1:
        return scores
    out = np.zeros_like(scores)
    pass_scores = scores[~failing]
    fail_scores = scores[failing]
    if k_eff == n_pass:
        mu = pass_scores.mean(axis=0)
        residual = fail_scores - mu
        out[failing] = _strip(pass_scores - mu, residual, tangent_dims, k_eff)
        return out
    # Same distance and the same unordered k nearest as j05.embed_knn_residual.
    pass_norm = np.einsum("ij,ij->i", pass_scores, pass_scores)
    fail_norm = np.einsum("ij,ij->i", fail_scores, fail_scores)
    distances = np.maximum(fail_norm[:, None] + pass_norm[None, :] - 2.0 * fail_scores @ pass_scores.T, 0.0)
    nearest = np.argpartition(distances, k_eff - 1, axis=1)[:, :k_eff]
    neighbors = pass_scores[nearest]
    mu = neighbors.mean(axis=1)
    residual = fail_scores - mu
    out[failing] = _strip(neighbors - mu[:, None, :], residual, tangent_dims, k_eff)
    return out


def _removal_stats(base: np.ndarray, features: np.ndarray, failing: np.ndarray) -> dict:
    """How much of the j05 residual the tangent projection took off.

    For each failing row with ||r|| > 1e-12, the fraction removed is
    ||r - r_tangent|| / ||r||. The length drop is 1 - ||r_tangent|| / ||r||,
    and the energy fraction is the square of the first. The mean is unweighted
    across those rows.
    """
    residual = np.asarray(base[failing], dtype=np.float64)
    kept = np.asarray(features[failing], dtype=np.float64)
    removed = residual - kept
    norms = np.linalg.norm(residual, axis=1)
    removed_norms = np.linalg.norm(removed, axis=1)
    kept_norms = np.linalg.norm(kept, axis=1)
    mask = norms > 1e-12
    stats = {
        "n_fail": int(failing.sum()),
        "n_fail_nonzero": int(mask.sum()),
        "mean_fraction_removed": None,
        "min_fraction_removed": None,
        "max_fraction_removed": None,
        "mean_energy_removed": None,
        "mean_length_drop": None,
    }
    if not np.any(mask):
        return stats
    fraction = removed_norms[mask] / norms[mask]
    stats["mean_fraction_removed"] = float(fraction.mean())
    stats["min_fraction_removed"] = float(fraction.min())
    stats["max_fraction_removed"] = float(fraction.max())
    stats["mean_energy_removed"] = float(np.mean(fraction ** 2))
    stats["mean_length_drop"] = float(np.mean(1.0 - kept_norms[mask] / norms[mask]))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(j05._j04.SUMMARY), default="window")
    parser.add_argument("--pre-dims", type=int, default=j05.PRE_DIMS,
                        help="unwhitened PCA width on all routes; neighbour distances are Euclidean in that space")
    parser.add_argument("--k", type=int, default=j05.K,
                        help="passing neighbours of each failing route; clamped to how many pass")
    parser.add_argument("--tangent-dims", type=int, default=TANGENT_DIMS,
                        help="tangent directions removed from each residual; clamped to k - 1; 0 is j05")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache_methods = _load("cache_methods")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j13: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, j05._j04.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = resolve_layers(n_layers, args.layer)
        matrix = layer_matrix(cache, args.site, layers, args.summary)
        features = embed_knn_tangent(
            matrix, failing, pre_dims=args.pre_dims, k=args.k,
            tangent_dims=args.tangent_dims, seed=args.seed)
    base = j05.embed_knn_residual(matrix, failing, pre_dims=args.pre_dims, k=args.k, seed=args.seed)
    removed = _removal_stats(base, features, failing)
    name = f"j13-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
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
            "tangent_dims": args.tangent_dims,
            "seed": args.seed,
        },
        "axes": axes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({
        "method": name,
        "layer": layers,
        "k": args.k,
        "tangent_dims": args.tangent_dims,
        "pre_dims": args.pre_dims,
        "axes": [len(axis["rollouts"]) for axis in axes],
        **removed,
    }))


if __name__ == "__main__":
    main()
