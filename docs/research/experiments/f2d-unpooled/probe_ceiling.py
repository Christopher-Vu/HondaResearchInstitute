#!/usr/bin/env python3
"""The unpooled experiment's probe ceiling (protocol.md, reference rows): label-reading, reported only, not a try.

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/probe_ceiling.py FEATURES.npz --output report.json

For every row in unpooled_methods.py's features.npz, and for B3-behaviour's features, the probe diagnostic's logistic
probe (probe_diagnostic.py: PCA 32 over all routes, failing routes only, one gap against the other failures, 5 folds
grouped by Fail2Drive pair). It reports the AUROC per SimLingo named gap as mean, minimum and maximum over 20 split
seeds, because one split is not trustworthy at 3 to 6 pairs per gap (probe-diagnostic.md, amendment).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

SPEC = importlib.util.spec_from_file_location(
    "probe_diagnostic", Path(__file__).resolve().parent.parent / "f2d-dev-simlingo/probe_diagnostic.py")
pd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pd)
SEEDS = 20


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("features", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fids, pairs, _, beh, labels = pd.load_model("simlingo")
    with np.load(args.features) as f:
        ids = [str(r) for r in f["route_id"]]
        failing = f["failing"]
        rows = {k: f[k] for k in f.files if k not in ("route_id", "failing")}
    where = {r: i for i, r in enumerate(ids)}
    keep = [j for j, r in enumerate(fids) if r in where and failing[where[r]]]
    sel = np.array([where[fids[j]] for j in keep])
    feats = {"B3_behaviour": beh[keep]}
    for name, x in sorted(rows.items()):
        feats[name] = PCA(n_components=32, random_state=0).fit_transform(pd.z(x.astype(np.float64)))[sel]
    out = {"label": "LABEL-READING probe ceiling (protocol.md); not a method, not a try; outcomes already read",
           "failing_routes": len(keep), "failing_in_cache": len(fids), "split_seeds": SEEDS, "cells": []}
    for gap, y_all in labels.items():
        y, g = y_all[keep], pairs[keep]
        splits = []
        for seed in range(SEEDS):
            folds = list(StratifiedGroupKFold(5, shuffle=True, random_state=seed).split(np.zeros(len(y)), y, g))
            if all(y[tr].any() for tr, _ in folds):
                splits.append(folds)
        for name, x in feats.items():
            a = np.array([roc_auc_score(y, pd.oof(x, y, folds, "logreg")[0]) for folds in splits])
            out["cells"].append({"gap": gap, "row": name, "positive_routes": int(y.sum()), "positive_pairs": len(set(g[y])),
                                 "seeds_used": len(a), "auroc_mean": round(float(a.mean()), 3),
                                 "auroc_min": round(float(a.min()), 3), "auroc_max": round(float(a.max()), 3)})
            print(json.dumps(out["cells"][-1]), flush=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
