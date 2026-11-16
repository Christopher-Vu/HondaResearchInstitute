#!/usr/bin/env python3
"""j01: Ward cuts on PCA scores that keep their eigenvalue scale.

m03 and m08 standardise the PCA scores (embed, then standardise again in main),
so the last component weighs the same as the first. j01 uses the same cuts,
2, 3 and 5, largest cluster first, and leaves the scores on the eigenvalue scale.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j01_unwhite.py CACHE \
        --site driving_queries --layer 5 8 20 --summary window --dims 32 \
        --cluster ward --cuts 2 3 5 --output OUT.json

Several --layer values are concatenated without column standardisation. Each
layer is divided by its own root-mean-square so layers share a scale and the
relative column scales inside a layer stay put. Column standardisation before
PCA hides the planted groups this method is aimed at (measured Jaccard about
0.41 and 0.39 on the unit-test generator). PCA scores are not standardised
afterwards either. Axes are cache_methods.axes_from on those scores. With no
--layer, the layers are fractions 5/23, 8/23 and 20/23 of the tensor depth.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA


def _load_cache_methods():
    path = Path(__file__).with_name("cache_methods.py")
    spec = importlib.util.spec_from_file_location("cache_methods", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_j04():
    path = Path(__file__).with_name("j04_bgmoment.py")
    spec = importlib.util.spec_from_file_location("j04_bgmoment", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load_cache_methods()


def embed_unwhitened(x: np.ndarray, dims: int, seed: int) -> np.ndarray:
    """PCA scores on the eigenvalue scale. PCA may center; columns are not standardised."""
    dims_used = min(dims, x.shape[0] - 1, x.shape[1])
    return PCA(n_components=dims_used, random_state=seed, whiten=False).fit_transform(x)


def layer_matrix(cache, site: str, layers: list[int], summary: str) -> np.ndarray:
    """Window (or route, or early) activations. No per-column standardisation.

    Each layer is divided by its root-mean-square, including when only one
    layer is requested, then concatenated, so a layer's internal column scales
    survive and no layer dominates by its raw magnitude.
    """
    block = np.asarray(cache[site][:, cache_methods.SUMMARY[summary]], dtype=np.float64)
    if block.ndim == 2:
        return block
    n_layers = block.shape[1]
    missing = [layer for layer in layers if layer < 0 or layer >= n_layers]
    if missing:
        raise SystemExit(f"j01: layers {missing} outside 0..{n_layers - 1} for {site}")
    parts = []
    for layer in layers:
        part = block[:, layer]
        rms = float(np.sqrt(np.mean(part * part)))
        parts.append(part if rms == 0.0 else part / rms)
    return np.concatenate(parts, axis=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(cache_methods.SUMMARY), default="window")
    parser.add_argument("--dims", type=int, default=32)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cluster", choices=("ward", "average", "complete", "spectral"), default="ward")
    parser.add_argument("--cuts", type=int, nargs="+", default=list(cache_methods.CUTS))
    parser.add_argument("--name", help="method name in the output; default starts with j01")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    j04 = _load_j04()
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j01: cache has no site {args.site}")
        ids = cache["route_id"].tolist()
        meta = [json.loads(m) for m in cache["meta"]]
        failing = np.array([not m["success"] for m in meta])
        block = cache[args.site][:, cache_methods.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = j04.resolve_layers(n_layers, args.layer)
        features = embed_unwhitened(layer_matrix(cache, args.site, layers, args.summary), args.dims, args.seed)
    name = args.name or f"j01-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    if not name.startswith("j01"):
        name = f"j01-{name}"
    out = {"method": name, "settings": vars(args) | {"cache": str(args.cache), "output": str(args.output),
                                                     "layer": layers},
           "axes": cache_methods.axes_from(features, failing, ids, name, args.cluster, tuple(args.cuts), args.seed)[:10]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(a["rollouts"]) for a in out["axes"]]}))


if __name__ == "__main__":
    main()
