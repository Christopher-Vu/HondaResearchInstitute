#!/usr/bin/env python3
"""Contrastive PCA on a SimLingo activation cache (j02).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j02_cpca.py CACHE \
        --site driving_queries --layer 5 8 20 --summary window --dims 8 --output OUT.json

Pass/fail is a fleet outcome; gap-type labels are not read. The embedding is contrastive PCA
(Abid et al.): the covariance of failing routes minus alpha times the covariance of passing
routes. Alphas are exactly (0.1, 1, 10, 30, 100). Among alphas whose leading eigenvalue is
positive, the one with the largest gap between the largest and second-largest eigenvalue is
kept. The median-affinity alpha rule is not used: on a buried signal it picks the small alphas
where normal driving still dominates. Features are column-centered and not divided by column
standard deviation, so that variance contrast survives. Several layers are centered separately,
scaled by 1/sqrt(n_columns), and concatenated. Failing routes are clustered with axes_from
(Ward, cuts 2, 3 and 5). The first 10 axes are written, largest group first within each cut.

With no --layer, the layers are fractions 5/23, 8/23 and 20/23 of the tensor depth.
Before the covariances, unwhitened PCA on all routes reduces the width to 32; 0 disables
it. Fewer than two failing or two passing routes skips the covariances and uses unwhitened PCA.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

ALPHAS = (0.1, 1, 10, 30, 100)
CUTS = (2, 3, 5)
PRE_DIMS = 32
SUMMARY = {"route": 0, "window": 1, "early": 2}


def _load_cache_methods():
    path = Path(__file__).with_name("cache_methods.py")
    spec = importlib.util.spec_from_file_location("cache_methods", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_j04():
    path = Path(__file__).with_name("j04_bgmoment.py")
    spec = importlib.util.spec_from_file_location("j04_bgmoment", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _unwhitened_fallback(centered: np.ndarray, dims: int, seed: int) -> tuple[np.ndarray, dict]:
    n_components = min(dims, centered.shape[0], centered.shape[1])
    scores = PCA(n_components=n_components, whiten=False, random_state=seed).fit_transform(centered)
    return scores, {"fallback": "unwhitened_pca"}


def embed_cpca(x: np.ndarray, failing: np.ndarray, dims: int = 4, seed: int = 0,
               pre_dims: int = PRE_DIMS) -> tuple[np.ndarray, dict]:
    """Column-centered contrastive scores. info has alpha, or fallback when every leading eigenvalue is <= 0.

    Fewer than two failing or two passing routes skips the covariances. pre_dims reduces all
    routes with unwhitened PCA before the covariances; 0 leaves the width unchanged.
    """
    data = np.asarray(x, dtype=np.float64)
    failing = np.asarray(failing, dtype=bool)
    n_routes, d = data.shape
    if 0 < pre_dims < min(n_routes - 1, d):
        data = PCA(n_components=pre_dims, whiten=False, random_state=seed).fit_transform(
            data - data.mean(axis=0))
    centered = data - data.mean(axis=0)
    n_fail = int(failing.sum())
    n_pass = int((~failing).sum())
    if n_fail < 2 or n_pass < 2:
        return _unwhitened_fallback(centered, dims, seed)
    foreground = np.cov(centered[failing], rowvar=False)
    background = np.cov(centered[~failing], rowvar=False)
    chosen = None
    for alpha in ALPHAS:
        matrix = foreground - alpha * background
        matrix = (matrix + matrix.T) * 0.5
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        leading = float(eigenvalues[-1])
        if leading <= 0.0:
            continue
        second = float(eigenvalues[-2]) if eigenvalues.size > 1 else 0.0
        gap = leading - second
        if chosen is None or gap > chosen[0]:
            chosen = (gap, alpha, eigenvalues, eigenvectors)
    if chosen is None:
        return _unwhitened_fallback(centered, dims, seed)
    _, alpha, eigenvalues, eigenvectors = chosen
    order = np.argsort(eigenvalues)[::-1][:dims]
    return centered @ eigenvectors[:, order], {"alpha": alpha}


def centered_layers(cache, site: str, layers: list[int], summary: str) -> np.ndarray:
    """Column-center each requested layer and concatenate. Do not column-standardise."""
    block = np.asarray(cache[site][:, SUMMARY[summary]], dtype=np.float64)
    if block.ndim == 2:
        return block - block.mean(axis=0)
    parts = []
    several = len(layers) > 1
    for layer in layers:
        part = block[:, layer]
        part = part - part.mean(axis=0)
        if several:
            part = part / np.sqrt(part.shape[1])
        parts.append(part)
    return np.concatenate(parts, axis=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(SUMMARY), default="window")
    parser.add_argument("--dims", type=int, default=8)
    parser.add_argument("--pre-dims", type=int, default=PRE_DIMS,
                        help="unwhitened PCA width on all routes before the covariances; 0 disables")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache_methods = _load_cache_methods()
    layer_rules = _load_j04()
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j02: cache has no site {args.site}")
        ids = cache["route_id"].tolist()
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = layer_rules.resolve_layers(n_layers, args.layer)
        features = centered_layers(cache, args.site, layers, args.summary)
    scores, info = embed_cpca(features, failing, dims=args.dims, seed=args.seed, pre_dims=args.pre_dims)
    name = f"j02-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    settings = {
        "cache": str(args.cache),
        "site": args.site,
        "layer": list(layers),
        "summary": args.summary,
        "dims": args.dims,
        "pre_dims": args.pre_dims,
        "seed": args.seed,
        "output": str(args.output),
    }
    settings.update(info)
    axes = cache_methods.axes_from(scores, failing, ids, name, "ward", CUTS, args.seed)[:10]
    payload = {"method": name, "settings": settings, "axes": axes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({"method": name, "settings": {k: settings[k] for k in ("alpha", "fallback") if k in settings},
                      "axes": [len(axis["rollouts"]) for axis in axes]}))


if __name__ == "__main__":
    main()
