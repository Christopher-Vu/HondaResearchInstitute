#!/usr/bin/env python3
"""j11: unit-normalise j05's kNN residuals, then cluster those directions.

j05 subtracts the mean of the k nearest passing routes and clusters that
residual. Residual length mixes scene density with failure kind; clusters
should form on the direction of deviation. Each failing row is divided by
its Euclidean norm. A row whose norm is below 1e-12 stays zero. Passing
rows stay zero.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j11_knndir.py CACHE \
        --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j05 = _load("j05_knnresid")


def embed_knn_direction(x: np.ndarray, failing: np.ndarray, pre_dims: int = j05.PRE_DIMS, k: int = j05.K,
                        seed: int = 0) -> np.ndarray:
    """j05 residual, with each failing row divided by its Euclidean norm.

    Passing rows are unchanged. A failing row with norm below 1e-12 is left
    at zero so a failure that sits on its passing neighbours does not become
    a unit vector of numerical noise.
    """
    failing = np.asarray(failing, dtype=bool)
    residual = np.asarray(
        j05.embed_knn_residual(x, failing, pre_dims=pre_dims, k=k, seed=seed),
        dtype=np.float64,
    ).copy()
    rows = residual[failing]
    if rows.shape[0]:
        norms = np.linalg.norm(rows, axis=1)
        small = norms < 1e-12
        rows[small] = 0.0
        if np.any(~small):
            rows[~small] /= norms[~small, None]
        residual[failing] = rows
    return residual


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
                        help="passing neighbours subtracted from each failing route; clamped to how many pass")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache_methods = _load("cache_methods")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j11: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, j05._j04.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = j05.resolve_layers(n_layers, args.layer)
        features = embed_knn_direction(
            j05.layer_matrix(cache, args.site, layers, args.summary), failing,
            pre_dims=args.pre_dims, k=args.k, seed=args.seed)
    name = f"j11-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
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
