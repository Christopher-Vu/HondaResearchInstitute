#!/usr/bin/env python3
"""j07: stratify failing routes by behaviour, then cluster activations within each stratum.

On the H21 pool, four speed features (kin) explain 40% of the layer-10 activation
variance and the kin-only rival wins (measured on H21). That rival's cut-2 split of
failing routes is 39 / 13 (measured on H21). Two of the target failure kinds both
end with a stopped car, so speed alone cannot separate them, and removing the
speed-linear part (j06) did not help (measured on H21). j07 conditions on a
behaviour stratum (a hard, nonlinear split) and lets activations split each stratum,
so scene content can separate kinds of stop.

Behaviour is standardised over every route, the same construction as h21_cache.py's
b3_kin, then Ward-cut into --strata clusters of the failing routes. Activations are
j01's unwhitened PCA on all routes: no failure label and no behaviour features.
Each stratum of at least 3 routes is clustered on that embedding; a smaller stratum
is skipped. Axes are the clusters at each --cuts value below the stratum size,
largest group first, and only the first 10 are kept.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j07_stratify.py CACHE \
        --site driving_queries --layer 5 8 20 --summary window --dims 32 \
        --strata 2 --cuts 2 3 --cluster ward --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.cluster import SpectralClustering


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j01 = _load("j01_unwhite")
j06 = _load("j06_kinresid")


def _ordered_groups(labels: np.ndarray, route_ids: list[str]) -> list[list[str]]:
    """Groups largest first. Equal sizes break toward the smallest route id."""
    groups = []
    for label in set(np.asarray(labels).tolist()):
        members = sorted(route_ids[j] for j in np.flatnonzero(np.asarray(labels) == label))
        if members:
            groups.append(members)
    groups.sort(key=lambda members: (-len(members), members[0]))
    return groups


def _ordered_strata(labels: np.ndarray, rows: np.ndarray, ids: list[str]) -> list[np.ndarray]:
    """Failing-row indices, largest stratum first. Ties break toward the smallest route id."""
    strata = []
    for label in set(np.asarray(labels).tolist()):
        chosen = rows[np.flatnonzero(np.asarray(labels) == label)]
        if len(chosen):
            strata.append(chosen)
    strata.sort(key=lambda chosen: (-len(chosen), min(ids[i] for i in chosen)))
    return strata


def _labels(block: np.ndarray, tree, k: int, cluster: str, seed: int) -> np.ndarray:
    if cluster == "spectral":
        n_neighbors = min(10, block.shape[0] - 1)
        return SpectralClustering(
            n_clusters=k, random_state=seed, affinity="nearest_neighbors", n_neighbors=n_neighbors,
        ).fit_predict(block)
    return fcluster(tree, t=k, criterion="maxclust")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(j01.cache_methods.SUMMARY), default="window")
    parser.add_argument("--dims", type=int, default=32)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cluster", choices=("ward", "average", "complete", "spectral"), default="ward")
    parser.add_argument("--strata", type=int, default=2, help="Ward clusters of the failing routes on behaviour")
    parser.add_argument("--cuts", type=int, nargs="+", default=[2, 3])
    parser.add_argument("--name", help="method name in the output; default starts with j07")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    j04 = _load("j04_bgmoment")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j07: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(m) for m in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, j01.cache_methods.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = j04.resolve_layers(n_layers, args.layer)
        behaviour, behaviour_name = j06.behaviour_matrix(cache, meta)
        behaviour = np.asarray(behaviour, dtype=np.float64)
        # Over every route, matching h21_cache.py's b3_kin construction.
        scale = np.where(behaviour.std(0) > 0, behaviour.std(0), 1.0)
        standardised = (behaviour - behaviour.mean(0)) / scale
        rows = np.flatnonzero(failing)
        if len(rows) < 2:
            raise SystemExit(f"j07: need at least 2 failing routes to stratify, got {len(rows)}")
        strata = _ordered_strata(
            fcluster(linkage(standardised[rows], method="ward"), t=args.strata, criterion="maxclust"),
            rows, ids)
        features = j01.embed_unwhitened(
            j01.layer_matrix(cache, args.site, layers, args.summary), args.dims, args.seed)
    name = args.name or f"j07-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    if not name.startswith("j07"):
        name = f"j07-{name}"
    axes = []
    for stratum_index, chosen in enumerate(strata, start=1):
        if len(chosen) < 3:
            continue
        block = np.asarray(features[chosen], dtype=np.float64)
        tree = None if args.cluster == "spectral" else linkage(block, method=args.cluster)
        stratum_ids = [ids[i] for i in chosen]
        for k in args.cuts:
            if k < 1 or k >= len(chosen):
                continue
            labels = _labels(block, tree, k, args.cluster, args.seed)
            for group_index, members in enumerate(_ordered_groups(labels, stratum_ids), start=1):
                axes.append({
                    "name": f"{name} stratum {stratum_index} cut {k} group {group_index}",
                    "rollouts": members,
                })
    strata_sizes = [int(len(chosen)) for chosen in strata]
    out = {"method": name, "settings": vars(args) | {"cache": str(args.cache), "output": str(args.output),
                                                     "layer": layers, "behaviour": behaviour_name,
                                                     "strata_sizes": strata_sizes},
           "axes": axes[:10]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(axis["rollouts"]) for axis in out["axes"]],
                      "strata_sizes": strata_sizes}))


if __name__ == "__main__":
    main()
