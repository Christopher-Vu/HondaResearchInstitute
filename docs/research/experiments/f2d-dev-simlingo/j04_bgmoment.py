#!/usr/bin/env python3
"""j04: cluster failures in the coordinates normal driving does not use.

m04 fits a signed pass/fail probe on pooled, column-standardised PCA scores.
Opposite failure modes cancel in that probe, and it scored 0.120 on SimLingo
(dev, measured, 6 configurations tried at the time). Contrastive PCA (j02)
looks for directions where failing routes vary more than passing routes. A
tight mode sitting in a direction passing routes barely use is a mean shift,
not extra variance, so that contrast misses it.

j04 estimates the covariance of passing routes only, whitens with a ridge
(ridge = 0.02 times the leading eigenvalue, so near-null directions do not
explode), and keeps the coordinates whose failing routes have the largest
second moment. The second moment is unsigned, so two groups on opposite sides
of one direction both count. Scores are not standardised again. Pass/fail is
a fleet outcome. Gap-type labels are not read.

Layers default to fractions 5/23, 8/23 and 20/23 of whatever depth the cache
tensor has (5, 8 and 20 when there are 24 layers). Columns are not
standardised. Each layer is divided by its root-mean-square before
concatenation so one layer's magnitude does not dominate.

There are 828 passing routes and the width is 896 or 2,688, so the passing
span has at most 827 dimensions and cannot hold every failure direction. On
synthetic data of that shape the passing-span projection scored 0.08, the
no-signal floor, where unwhitened PCA scored 0.88, and reducing to 32
components first scored 0.95 to 1.0 in every cell. embed_bg_moment therefore
reduces all routes with unwhitened PCA to 32 components before the background
whitening; 0 turns that off. The width 32 was measured on synthetic data
only, five seeds, and chosen before any SimLingo score.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j04_bgmoment.py CACHE \
        --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

RIDGE_FRAC = 0.02
DIMS = 8
PRE_DIMS = 32
FRACS = (5 / 23, 8 / 23, 20 / 23)
SUMMARY = {"route": 0, "window": 1, "early": 2}


def _load_cache_methods():
    path = Path(__file__).with_name("cache_methods.py")
    spec = importlib.util.spec_from_file_location("cache_methods", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fractional_layers(n_layers: int, fracs=FRACS) -> list[int]:
    """Indices at frac * (n_layers - 1), clamped, unique, then sorted."""
    last = max(n_layers - 1, 0)
    picked = []
    for frac in fracs:
        index = int(round(float(frac) * last))
        picked.append(min(max(index, 0), last))
    return sorted(set(picked))


def _unwhitened(x: np.ndarray, dims: int, seed: int) -> np.ndarray:
    n_components = min(dims, x.shape[0] - 1, x.shape[1])
    if n_components < 1:
        return np.zeros((x.shape[0], 1), dtype=np.float64)
    return PCA(n_components=n_components, random_state=seed, whiten=False).fit_transform(x)


def embed_bg_moment(x: np.ndarray, failing: np.ndarray, dims: int = DIMS, ridge_frac: float = RIDGE_FRAC,
                    seed: int = 0, pre_dims: int = PRE_DIMS) -> np.ndarray:
    """Background-whitened coordinates with the largest failure second moment.

    Falls back to unwhitened PCA when there are too few passing or failing
    routes for a covariance, or when the passing routes have no variance.
    When pre_dims is positive and narrower than the matrix, all routes are
    reduced with unwhitened PCA to that width first.
    """
    data = np.asarray(x, dtype=np.float64)
    failing = np.asarray(failing, dtype=bool)
    n_fail = int(failing.sum())
    n_pass = int((~failing).sum())
    if data.ndim != 2 or data.shape[0] < 3 or n_pass < 3 or n_fail < 2:
        return _unwhitened(data, dims, seed)
    n_routes, d = data.shape
    if 0 < pre_dims < min(n_routes - 1, d):
        data = PCA(n_components=pre_dims, whiten=False, random_state=seed).fit_transform(
            data - data.mean(axis=0))
    background = data[~failing]
    centered = data - background.mean(axis=0)
    background = background - background.mean(axis=0)
    n_comp = min(background.shape[0] - 1, background.shape[1])
    if n_comp < 1:
        return _unwhitened(centered, dims, seed)
    pca = PCA(n_components=n_comp, random_state=seed, whiten=False).fit(background)
    eigenvalues = np.asarray(pca.explained_variance_, dtype=np.float64)
    leading = float(eigenvalues[0])
    if leading <= 1e-12:
        return _unwhitened(centered, dims, seed)
    scale = 1.0 / np.sqrt(eigenvalues + ridge_frac * leading)
    scores = (centered @ pca.components_.T) * scale
    moment = np.mean(scores[failing] ** 2, axis=0)
    keep = min(dims, scores.shape[1])
    chosen = np.argsort(-moment)[:keep]
    return scores[:, chosen]


def layer_matrix(cache, site: str, layers: list[int], summary: str) -> np.ndarray:
    """Activations for the requested layers. No per-column standardisation."""
    block = np.asarray(cache[site][:, SUMMARY[summary]], dtype=np.float64)
    if block.ndim == 2:
        return block
    parts = []
    for layer in layers:
        part = block[:, layer]
        rms = float(np.sqrt(np.mean(part * part)))
        parts.append(part if rms == 0.0 else part / rms)
    if not parts:
        raise SystemExit(f"j04: no usable layer for {site}")
    return np.concatenate(parts, axis=1)


def resolve_layers(n_layers: int, requested: list[int] | None) -> list[int]:
    if not requested:
        return fractional_layers(n_layers)
    kept = [layer for layer in requested if 0 <= layer < n_layers]
    if not kept:
        raise SystemExit(f"j04: layers {requested} outside 0..{n_layers - 1}")
    return kept


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(SUMMARY), default="window")
    parser.add_argument("--dims", type=int, default=DIMS)
    parser.add_argument("--ridge", type=float, default=RIDGE_FRAC)
    parser.add_argument("--pre-dims", type=int, default=PRE_DIMS,
                        help="unwhitened PCA width on all routes before background whitening; 0 disables")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache_methods = _load_cache_methods()
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j04: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = resolve_layers(n_layers, args.layer)
        features = embed_bg_moment(layer_matrix(cache, args.site, layers, args.summary), failing,
                                   dims=args.dims, ridge_frac=args.ridge, seed=args.seed, pre_dims=args.pre_dims)
    name = f"j04-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    axes = cache_methods.axes_from(features, failing, ids, name, "ward", cache_methods.CUTS, args.seed)[:10]
    payload = {
        "method": name,
        "settings": {
            "cache": str(args.cache),
            "site": args.site,
            "layer": layers,
            "summary": args.summary,
            "dims": args.dims,
            "pre_dims": args.pre_dims,
            "ridge": args.ridge,
            "seed": args.seed,
        },
        "axes": axes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({"method": name, "layer": layers, "axes": [len(axis["rollouts"]) for axis in axes]}))


if __name__ == "__main__":
    main()
