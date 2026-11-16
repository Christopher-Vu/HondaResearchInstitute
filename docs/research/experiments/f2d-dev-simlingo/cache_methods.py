#!/usr/bin/env python3
"""Sprint methods that read only the cache (cache_pool.py): m03, m04, m06, m07 (VARIANTS.md batch 1).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/cache_methods.py CACHE --method m03 \
        --site driving_queries --layer 10 --output m03.json

Inputs are one site and layer of the cache: `--summary window` (the approach window, default), `route` or `early`.
- m03: failing-route clustering. Standardise over all routes, PCA (fitted on all routes) to --dims, then Ward
  clustering of the failing routes.
- m04: error-aware embedding. A balanced logistic pass/fail probe on the PCA components; the failing routes are
  clustered on the --keep components with the largest |coefficient|, each scaled by its coefficient.
- m07: change before failure. The window minus the route's own early mean, then m03.
- m06: --base m03|m04|m07 plus fleet-observable kinematics (B3-behaviour's features), both blocks standardised and
  weighted equally.
Axes, as B3-behaviour: the clusters at cuts k = 2, 3 and 5 (10 axes), in that order, largest first within a cut.
Batch 2 options: several --layer values are concatenated, each layer standardised and weighted equally (m08);
--cluster average|complete|spectral replaces Ward (m12); --cuts replaces 2 3 5 (m13). Only the first 10 axes score.
Batch 3: --auto-layers N (m19) keeps the N layers whose 5-fold pass/fail probe AUROC is highest, weighting each by
AUROC - 0.5; it uses the outcome only, as a fleet could.
Route order is the cache's salted order; route ids are only written to the output.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.cluster import SpectralClustering
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

CUTS = (2, 3, 5)
SUMMARY = {"route": 0, "window": 1, "early": 2}


def standardise(x: np.ndarray) -> np.ndarray:
    sd = x.std(0)
    return (x - x.mean(0)) / np.where(sd > 0, sd, 1.0)


def axes_from(features: np.ndarray, failing: np.ndarray, ids: list[str], label: str, cluster: str = "ward",
              cuts: tuple[int, ...] = CUTS, seed: int = 0) -> list[dict]:
    rows = np.flatnonzero(failing)
    tree = None if cluster == "spectral" else linkage(features[failing], method=cluster)
    axes = []
    for k in cuts:
        labels = (SpectralClustering(n_clusters=k, random_state=seed, affinity="nearest_neighbors")
                  .fit_predict(features[failing]) if tree is None else fcluster(tree, t=k, criterion="maxclust"))
        groups = sorted(({ids[rows[j]] for j in np.flatnonzero(labels == c)} for c in set(labels)), key=len,
                        reverse=True)
        axes += [{"name": f"{label} cut {k} group {n + 1}", "rollouts": sorted(g)} for n, g in enumerate(groups)]
    return axes


def activations(cache, site: str, layers: list[int], summary: str) -> np.ndarray:
    block = cache[site][:, SUMMARY[summary]]
    if block.ndim == 2:
        return block.astype(np.float32)
    parts = [standardise(block[:, layer].astype(np.float32)) for layer in layers]
    return np.hstack(parts) / np.sqrt(len(parts))


def auto_layers(cache, site: str, summary: str, failing: np.ndarray, n: int, seed: int) -> tuple[np.ndarray, list]:
    block = cache[site][:, SUMMARY[summary]]
    picks = []
    for layer in range(block.shape[1]):
        z = PCA(n_components=32, random_state=seed).fit_transform(standardise(block[:, layer].astype(np.float32)))
        auc = cross_val_score(LogisticRegression(class_weight="balanced", max_iter=2000, C=0.1), z, failing, cv=5,
                              scoring="roc_auc").mean()
        picks.append((auc, layer))
    top = sorted(picks, reverse=True)[:n]
    parts = [standardise(block[:, layer].astype(np.float32)) * max(auc - 0.5, 1e-3) for auc, layer in top]
    return np.hstack(parts), [(layer, round(float(auc), 3)) for auc, layer in top]


def kinematic_block(cache, meta) -> np.ndarray:
    path = Path(__file__).with_name("b3_behaviour.py")
    spec = importlib.util.spec_from_file_location("b3_behaviour", path)
    b3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b3)
    kinds = sorted({k for m in meta for k in m["infractions"]})
    return np.array([b3.kinematics(cache["ego_speed"][i], cache["step"][i], m["failure_step"]) +
                     [float(m["infractions"].get(k, 0) or 0) for k in kinds] for i, m in enumerate(meta)])


def embed(method: str, x: np.ndarray, failing: np.ndarray, dims: int, keep: int, seed: int) -> np.ndarray:
    z = PCA(n_components=dims, random_state=seed).fit_transform(standardise(x))
    if method in ("m03", "m07"):
        return z
    probe = LogisticRegression(class_weight="balanced", max_iter=2000, C=0.1).fit(standardise(z), failing)
    coef = probe.coef_[0]
    top = np.argsort(-np.abs(coef))[:keep]
    return standardise(z)[:, top] * coef[top]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--method", choices=("m03", "m04", "m06", "m07"), required=True)
    parser.add_argument("--base", choices=("m03", "m04", "m07"), default="m03", help="m06 only")
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="+", default=[10])
    parser.add_argument("--summary", choices=tuple(SUMMARY), default="window")
    parser.add_argument("--dims", type=int, default=32)
    parser.add_argument("--keep", type=int, default=16)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cluster", choices=("ward", "average", "complete", "spectral"), default="ward")
    parser.add_argument("--cuts", type=int, nargs="+", default=list(CUTS))
    parser.add_argument("--auto-layers", type=int, default=0)
    parser.add_argument("--name", help="method name in the output; default from the settings")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids = cache["route_id"].tolist()
        meta = [json.loads(m) for m in cache["meta"]]
        failing = np.array([not m["success"] for m in meta])
        core = args.base if args.method == "m06" else args.method
        chosen = None
        if args.auto_layers:
            x, chosen = auto_layers(cache, args.site, args.summary, failing, args.auto_layers, args.seed)
        else:
            x = activations(cache, args.site, args.layer, args.summary)
        if core == "m07":
            x = x - activations(cache, args.site, args.layer, "early")
        features = standardise(embed(core, x, failing, args.dims, args.keep, args.seed))
        if args.method == "m06":
            kin = standardise(kinematic_block(cache, meta))
            features = np.hstack([features / np.sqrt(features.shape[1]), kin / np.sqrt(kin.shape[1])])
    name = args.name or f"{args.method}{'-' + args.base if args.method == 'm06' else ''}-{args.site}-L{'+'.join(map(str, args.layer))}-{args.summary}"
    out = {"method": name, "settings": vars(args) | {"cache": str(args.cache), "output": str(args.output), "auto_layers_chosen": chosen},
           "axes": axes_from(features, failing, ids, name, args.cluster, tuple(args.cuts), args.seed)[:10]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(a["rollouts"]) for a in out["axes"]]}))


if __name__ == "__main__":
    main()
