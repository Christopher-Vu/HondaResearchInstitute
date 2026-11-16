#!/usr/bin/env python3
"""j06: subtract the behaviour linear prediction, then cluster like j01.

On the H21 pool, four speed features (kin) explain 40% of the layer-10
activation variance (null 2%) and 81% of PC1 (measured on H21), and activation
clusters largely re-find speed clusters. j06 removes the part of the activations
that the fleet-logged behaviour features predict linearly, then clusters exactly
as j01 does, so j06 versus j01 isolates that one step. The failure label is not
used in the residual.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j06_kinresid.py CACHE \
        --site driving_queries --layer 5 8 20 --summary window --dims 32 \
        --cluster ward --cuts 2 3 5 --output OUT.json

The behaviour block is the cache's kin array when it is present. Otherwise each
route is b3_behaviour.kinematics on ego speed, step and failure_step, with no
infraction counts. Columns are standardised over all routes; a column whose
standard deviation is 0 is set to 0. An intercept is prepended and OLS is fit
with np.linalg.lstsq on every route. Scores stay on the eigenvalue scale
(j01.embed_unwhitened). Axes are cache_methods.axes_from, the first 10.
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


j01 = _load("j01_unwhite")
cache_methods = _load("cache_methods")


def behaviour_design(behaviour: np.ndarray) -> np.ndarray:
    """Intercept plus behaviour columns, standardised over routes. Std 0 becomes 0."""
    block = np.asarray(behaviour, dtype=np.float64)
    if block.ndim == 1:
        block = block.reshape(-1, 1)
    if block.ndim != 2:
        raise ValueError(f"j06 expected a route-by-feature behaviour block, got shape {block.shape}")
    centred = block - block.mean(axis=0)
    sd = block.std(axis=0)
    scaled = np.zeros_like(centred)
    keep = sd > 0
    scaled[:, keep] = centred[:, keep] / sd[keep]
    return np.column_stack([np.ones(block.shape[0], dtype=np.float64), scaled])


def residualise(activations: np.ndarray, behaviour: np.ndarray) -> np.ndarray:
    """Activations minus their linear prediction from behaviour. Fit on every route."""
    data = np.asarray(activations, dtype=np.float64)
    design = behaviour_design(behaviour)
    if design.shape[0] != data.shape[0]:
        raise ValueError(f"j06 behaviour has {design.shape[0]} rows and activations have {data.shape[0]}")
    coef, *_ = np.linalg.lstsq(design, data, rcond=None)
    return data - design @ coef


def behaviour_matrix(cache, meta: list[dict]) -> tuple[np.ndarray, str]:
    """kin if the cache stored it, otherwise per-route kinematics. No infraction counts."""
    if "kin" in cache.files:
        block = np.asarray(cache["kin"], dtype=np.float64)
        if block.ndim == 1:
            block = block.reshape(-1, 1)
        if block.ndim != 2 or block.shape[0] != len(meta):
            raise SystemExit(f"j06: kin has shape {block.shape} for {len(meta)} routes")
        return block, "kin"
    if "ego_speed" in cache.files and "step" in cache.files:
        b3 = _load("b3_behaviour")
        rows = [
            b3.kinematics(cache["ego_speed"][i], cache["step"][i], item["failure_step"])
            for i, item in enumerate(meta)
        ]
        return np.asarray(rows, dtype=np.float64), "b3_kinematics"
    raise SystemExit(
        "j06: cache has neither a 'kin' array nor ego_speed and step, so the behaviour block cannot be built"
    )


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
    parser.add_argument("--name", help="method name in the output; default starts with j06")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    j04 = _load("j04_bgmoment")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j06: cache has no site {args.site}")
        ids = cache["route_id"].tolist()
        meta = [json.loads(m) for m in cache["meta"]]
        failing = np.array([not m["success"] for m in meta])
        block = cache[args.site][:, cache_methods.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = j04.resolve_layers(n_layers, args.layer)
        behaviour, behaviour_name = behaviour_matrix(cache, meta)
        features = j01.embed_unwhitened(
            residualise(j01.layer_matrix(cache, args.site, layers, args.summary), behaviour),
            args.dims, args.seed)
    name = args.name or f"j06-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    if not name.startswith("j06"):
        name = f"j06-{name}"
    out = {"method": name, "settings": vars(args) | {"cache": str(args.cache), "output": str(args.output),
                                                     "layer": layers, "behaviour": behaviour_name},
           "axes": cache_methods.axes_from(features, failing, ids, name, args.cluster, tuple(args.cuts), args.seed)[:10]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(a["rollouts"]) for a in out["axes"]]}))


if __name__ == "__main__":
    main()
