#!/usr/bin/env python3
"""Sprint batch 5 (VARIANTS.md m47, m49): a probe beyond logistic, and a mixture model, on one cache site and layer.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/probe_mixture.py CACHE --mode rf|gmm \
        --layer 8 --output OUT.json

Inputs as cache_methods.py: one site, layers concatenated, `--summary window` by default; standardised over all
routes, PCA fitted on all routes. Pass/fail is the only outcome read.
- rf (m47): a random forest pass/fail probe (500 trees, leaves of at least 5 routes, balanced classes). Failing routes
  that share leaves are alike in the ways that matter for failing: each failing route is embedded by its one-hot
  leaf memberships, reduced to 32 dimensions (truncated SVD), then cache_methods.axes_from (Ward, A2 rule).
- gmm (m49): a diagonal Gaussian mixture on the failing routes' PCA 16 scores, components 4 to 12 chosen by BIC. Each
  component's members (hard assignment) is an axis, largest first; only the first 10 count.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.ensemble import RandomForestClassifier
from sklearn.mixture import GaussianMixture

spec = importlib.util.spec_from_file_location("cache_methods", Path(__file__).with_name("cache_methods.py"))
cache_methods = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache_methods)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--mode", choices=("rf", "gmm"), required=True)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="+", default=[8])
    parser.add_argument("--layer-fraction", type=cache_methods.FRACTION, nargs="+", default=None,
                        help="transfer spec: layers as fractions of the site's depth (cache_methods.depth_layers)")
    parser.add_argument("--summary", choices=tuple(cache_methods.SUMMARY), default="window")
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids = cache["route_id"].tolist()
        failing = np.array([not json.loads(m)["success"] for m in cache["meta"]])
        if args.layer_fraction:
            args.layer = cache_methods.depth_layers(cache[args.site].shape[2], args.layer_fraction)
        x = cache_methods.activations(cache, args.site, args.layer, args.summary)
    if args.mode == "rf":
        z = PCA(n_components=32, random_state=0).fit_transform(cache_methods.standardise(x))
        forest = RandomForestClassifier(n_estimators=500, min_samples_leaf=5, class_weight="balanced", random_state=0,
                                        n_jobs=4).fit(z, failing)
        leaves = forest.apply(z)  # (routes, trees)
        codes = np.concatenate([np.unique(leaves[:, t], return_inverse=True)[1][:, None] for t in range(leaves.shape[1])], 1)
        offsets = np.r_[0, np.cumsum(codes.max(0) + 1)[:-1]]
        rows = np.repeat(np.arange(len(ids)), codes.shape[1])
        onehot = csr_matrix((np.ones(codes.size), (rows, (codes + offsets).ravel())))
        features = TruncatedSVD(n_components=32, random_state=0).fit_transform(onehot)
        axes = cache_methods.axes_from(features, failing, ids, args.name, "ward", cache_methods.CUTS)[:10]
        extra = {}
    else:
        z = PCA(n_components=16, random_state=0).fit_transform(cache_methods.standardise(x))[failing]
        fits = {k: GaussianMixture(k, covariance_type="diag", random_state=0, n_init=3).fit(z) for k in range(4, 13)}
        bic = {k: float(m.bic(z)) for k, m in fits.items()}
        k = min(bic, key=bic.get)
        labels = fits[k].predict(z)
        rows = np.flatnonzero(failing)
        groups = sorted(({ids[rows[j]] for j in np.flatnonzero(labels == c)} for c in set(labels)), key=len, reverse=True)
        axes = [{"name": f"{args.name} component {n + 1}", "rollouts": sorted(g)} for n, g in enumerate(groups)][:10]
        extra = {"k": k, "bic": bic}
    out = {"method": args.name, "probe_settings": vars(args) | {"cache": str(args.cache), "output": str(args.output)} | extra,
           "axes": axes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": args.name, "axes": [len(a["rollouts"]) for a in axes]} | extra))


if __name__ == "__main__":
    main()
