#!/usr/bin/env python3
"""j18: Gaussian mixture over every route, most atypical components first.

m49 fit a diagonal mixture to the failing routes only and ranked components by size. j18 fits the mixture to every
route, so it is a density model of all driving that never sees pass/fail, and ranks its components by how atypical
their routes are under that density.

- Features: m15's, from cache_methods (standardise over all routes, PCA --dims fit on all routes, scores
  standardised).
- Mixture: sklearn GaussianMixture on all routes for each K in --components and covariance diag or full, fixed
  random_state and n_init 3. The lowest BIC wins; a fit that raises is skipped.
- Ranking (label-free): hard assignment by predict; each component's score is the mean log density (score_samples)
  of all its routes, passing and failing; ascending, ties by component index.
- j19 (`--rank failure-rate`): the same mixture, components ranked by the share of their routes that fail, highest
  first; ties by more failing routes, then component index. This ranking reads pass/fail, as m03 does.
- Axes: each ranked component's failing routes (the cache's `meta.success`, as m03 reads it). A component with no
  failing route gives no axis; an exact repeat is dropped (A2); the first 10 are written.

Only the cache is read (route ids, meta.success, the activation site), in its salted row order.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j18_gmm.py CACHE-W50 --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.mixture import GaussianMixture

SPEC = importlib.util.spec_from_file_location("cache_methods", Path(__file__).with_name("cache_methods.py"))
cache_methods = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cache_methods)

COVARIANCES = ("diag", "full")


def fit_mixture(z: np.ndarray, components: list[int], seed: int) -> tuple[GaussianMixture, dict[str, float]]:
    fits, bic = {}, {}
    for k in components:
        for covariance in COVARIANCES:
            key = f"{covariance}-{k}"
            try:
                fits[key] = GaussianMixture(k, covariance_type=covariance, random_state=seed, n_init=3).fit(z)
            except (ValueError, np.linalg.LinAlgError):
                continue
            bic[key] = float(fits[key].bic(z))
    return fits[min(bic, key=bic.get)], bic


def rank_components(model: GaussianMixture, z: np.ndarray) -> tuple[np.ndarray, list[tuple[int, float]]]:
    labels = model.predict(z)
    density = model.score_samples(z)
    used = sorted(set(labels.tolist()))
    order = sorted(((c, float(density[labels == c].mean())) for c in used), key=lambda pair: (pair[1], pair[0]))
    return labels, order


def rank_by_failure_rate(labels: np.ndarray, order: list[tuple[int, float]], failing: np.ndarray) -> list[tuple[int, float]]:
    rate = {c: float(failing[labels == c].mean()) for c, _ in order}
    count = {c: int(failing[labels == c].sum()) for c, _ in order}
    density = dict(order)
    return [(c, density[c]) for c in sorted(rate, key=lambda c: (-rate[c], -count[c], c))]


def axes_from_components(labels: np.ndarray, order: list[tuple[int, float]], failing: np.ndarray, ids: list[str],
                         name: str) -> list[dict]:
    axes, seen = [], set()
    for component, density in order:
        members = frozenset(ids[i] for i in np.flatnonzero((labels == component) & failing))
        if members and members not in seen:
            seen.add(members)
            axes.append({"name": f"{name} component {component} mean log density {density:.3f}",
                         "rollouts": sorted(members)})
    return axes[:10]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="+", default=[8])
    parser.add_argument("--summary", choices=tuple(cache_methods.SUMMARY), default="window")
    parser.add_argument("--dims", type=int, default=32)
    parser.add_argument("--components", type=int, nargs="+", default=[4, 6, 8, 12])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rank", choices=("density", "failure-rate"), default="density")
    parser.add_argument("--name", default="j18")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids = cache["route_id"].tolist()
        failing = np.array([not json.loads(m)["success"] for m in cache["meta"]])
        x = cache_methods.activations(cache, args.site, args.layer, args.summary)
    z = cache_methods.standardise(cache_methods.embed("m03", x, failing, args.dims, 0, args.seed))
    model, bic = fit_mixture(z, args.components, args.seed)
    labels, order = rank_components(model, z)
    if args.rank == "failure-rate":
        order = rank_by_failure_rate(labels, order, failing)
    chosen = {"covariance": model.covariance_type, "k": int(model.n_components), "bic": bic,
              "component_order": [{"component": c, "mean_log_density": d, "routes": int((labels == c).sum()),
                                   "failing": int(((labels == c) & failing).sum())} for c, d in order]}
    out = {"method": args.name, "settings": vars(args) | {"cache": str(args.cache), "output": str(args.output)} | chosen,
           "axes": axes_from_components(labels, order, failing, ids, args.name)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": args.name, "covariance": chosen["covariance"], "k": chosen["k"],
                      "axes": [len(a["rollouts"]) for a in out["axes"]]}))


if __name__ == "__main__":
    main()
