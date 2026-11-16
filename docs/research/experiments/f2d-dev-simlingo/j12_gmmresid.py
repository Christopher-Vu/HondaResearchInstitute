#!/usr/bin/env python3
"""j12: subtract a mixture of passing routes, then cluster the residuals.

j05 subtracts the mean of the k nearest passing routes. Passing routes can
occupy several modes, so a failure is measured from the mixture of those
modes. j12 fits that mixture and subtracts the responsibility-weighted means.

One unwhitened PCA is fit on every route, the same scores as j05. The mixture
is full covariance and is fit on the passing scores only. The ridge on each
covariance is 1e-3 times the mean per-coordinate variance of those scores. K
runs from 1 to 6 and never above the number of passing routes. Each fit uses
five initialisations and at most 500 iterations. The lowest BIC wins, and a
tie keeps the smaller K.

A failing route's residual is its score minus the sum of responsibility times
component mean. Residuals are not whitened and not normalised. Passing rows
are zero. With no passing route the result is the unwhitened PCA scores. With
no failing route every row is zero.

Ward cuts at 2, 3 and 5 go through cache_methods.axes_from, and the first 10
axes are written. Only the cache is read: route ids, the success flag, and
the activation site.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j12_gmmresid.py CACHE \
        --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.mixture import GaussianMixture


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j05 = _load("j05_knnresid")


def _select_gmm(passing: np.ndarray, reg: float, seed: int) -> tuple[GaussianMixture, dict[int, float], int]:
    """Lowest BIC on K = 1..min(6, n_passing). A tie keeps the smaller K."""
    n_pass = int(passing.shape[0])
    bics: dict[int, float] = {}
    best_bic = None
    best_k = None
    best = None
    for k in range(1, min(6, n_pass) + 1):
        gmm = GaussianMixture(
            n_components=k,
            covariance_type="full",
            reg_covar=reg,
            n_init=5,
            random_state=seed,
            max_iter=500,
        ).fit(passing)
        bic = float(gmm.bic(passing))
        bics[k] = bic
        # Strictly smaller, so an equal BIC leaves the earlier, smaller K.
        if best_bic is None or bic < best_bic:
            best_bic = bic
            best_k = k
            best = gmm
    return best, bics, int(best_k)


def embed_gmm_residual(x: np.ndarray, failing: np.ndarray, pre_dims: int = j05.PRE_DIMS,
                       seed: int = 0) -> tuple[np.ndarray, dict]:
    """Failing rows are the PCA score minus the responsibility-weighted means.

    Passing rows are zero. With no passing route the result is the unwhitened
    PCA scores of every route. With no failing route the result is zeros. The
    dict holds the chosen K, the BIC of every K that was fit, and reg_covar.
    sklearn refuses a one-row fit, so a single passing route is the K=1 mean
    and records no BIC.
    """
    data = np.asarray(x, dtype=np.float64)
    failing = np.asarray(failing, dtype=bool)
    if data.ndim != 2:
        raise ValueError(f"j12 expected a route-by-feature matrix, got shape {data.shape}")
    if failing.shape != (data.shape[0],):
        raise ValueError("j12 failing mask does not match the number of routes")
    scores = j05._scores(data, pre_dims, seed)
    n_pass = int((~failing).sum())
    if n_pass < 1:
        return scores, {"K": None, "bic": {}, "reg_covar": None}
    passing = scores[~failing]
    reg = float(1e-3 * passing.var(axis=0).mean())
    if n_pass < 2:
        gmm, bics, chosen = None, {}, 1
    else:
        gmm, bics, chosen = _select_gmm(passing, reg, seed)
    fit = {"K": chosen, "bic": bics, "reg_covar": reg}
    if not failing.any():
        return np.zeros_like(scores), fit
    out = np.zeros_like(scores)
    z = scores[failing]
    if gmm is None:
        out[failing] = z - passing.mean(axis=0)
    else:
        responsibility = gmm.predict_proba(z)
        out[failing] = z - responsibility @ np.asarray(gmm.means_, dtype=np.float64)
    return out, fit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(j05._j04.SUMMARY), default="window")
    parser.add_argument("--pre-dims", type=int, default=j05.PRE_DIMS,
                        help="unwhitened PCA width on all routes; the mixture is fit in that space")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache_methods = _load("cache_methods")
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j12: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[args.site][:, j05._j04.SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = j05.resolve_layers(n_layers, args.layer)
        features, fit = embed_gmm_residual(
            j05.layer_matrix(cache, args.site, layers, args.summary), failing,
            pre_dims=args.pre_dims, seed=args.seed)
    name = f"j12-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    axes = cache_methods.axes_from(features, failing, ids, name, "ward", cache_methods.CUTS, args.seed)[:10]
    payload = {
        "method": name,
        "settings": {
            "cache": str(args.cache),
            "site": args.site,
            "layer": layers,
            "summary": args.summary,
            "pre_dims": args.pre_dims,
            "seed": args.seed,
            "K": fit["K"],
            "bic": {str(k): float(value) for k, value in fit["bic"].items()},
            "reg_covar": fit["reg_covar"],
        },
        "axes": axes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({
        "method": name,
        "layer": layers,
        "K": fit["K"],
        "bic": {str(k): float(value) for k, value in fit["bic"].items()},
        "reg_covar": fit["reg_covar"],
        "axes": [len(axis["rollouts"]) for axis in axes],
    }))


if __name__ == "__main__":
    main()
