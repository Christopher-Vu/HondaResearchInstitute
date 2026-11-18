#!/usr/bin/env python3
"""Independent reimplementation of probe-diagnostic.md (commit 8b0d1d6), written from that file alone.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/probe_diagnostic_indep.py \
        --output results/savio/f2d-dev/probe-diag-indep/report.json

Label-reading diagnostic, not a discovery method: it reads the gap labels on purpose and tunes nothing.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors

HERE = Path(__file__).resolve().parent
MANIFEST = Path("configs/rollout/f2d-test-simlingo.manifest.json")
CACHES = {"simlingo": Path("results/savio/f2d-dev/round2/simlingo/cache-w50.npz"),
          "tfpp": Path("results/savio/f2d-dev/round2/tfpp/cache-w50.npz")}
GAPS = {"simlingo": ["F2D_PedestriansOnRoad", "F2D_FullyBlocked", "F2D_BadParking"],
        "tfpp": ["F2D_PedestriansOnRoad", "F2D_FullyBlocked"]}
M23 = {("simlingo", "F2D_PedestriansOnRoad"): 0.591, ("simlingo", "F2D_FullyBlocked"): 0.353,
       ("simlingo", "F2D_BadParking"): 0.171, ("tfpp", "F2D_PedestriansOnRoad"): 0.063,
       ("tfpp", "F2D_FullyBlocked"): 0.171}
FRACTIONS = [("0", 0.0), ("1/4", 0.25), ("8/23", 8 / 23), ("1/2", 0.5), ("3/4", 0.75), ("1", 1.0)]
SUMMARIES = {"window": 1, "route": 0}
MAIN = ("window", "8/23")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cm = load("cache_methods")
b3 = load("b3_behaviour")
standardise = cm.standardise


def logreg() -> LogisticRegression:
    return LogisticRegression(class_weight="balanced", C=0.1, max_iter=2000)


def fold_std(x, tr, te):
    mu, sd = x[tr].mean(0), x[tr].std(0)
    sd = np.where(sd > 0, sd, 1.0)
    return (x[tr] - mu) / sd, (x[te] - mu) / sd


# ---- worker state (set before the pool forks) ----
STATE: dict = {}


def logistic_oof(key, y):
    """Out-of-fold P(gap) for one logistic cell, labels y; folds and fold-standardised features precomputed."""
    out = np.zeros(len(y))
    for tr, te, xtr, xte in STATE["prepped"][key]:
        if y[tr].min() == y[tr].max():
            out[te] = y[tr].mean()
            continue
        out[te] = logreg().fit(xtr, y[tr]).predict_proba(xte)[:, 1]
    return out


def logistic_task(args):
    key, perms = args
    y = STATE["y"][key[0]]
    return key, [roc_auc_score(y[p], logistic_oof(key, y[p])) for p in perms]


def knn_oof(neigh, y):
    out = np.zeros(len(y))
    for te, idx in neigh:
        out[te] = y[idx].mean(1)
    return out


def bal_acc(y, pred):
    return 0.5 * (pred[y == 1].mean() + (1 - pred[y == 0]).mean())


def weighted_auc(y, s, w):
    if w[y == 1].sum() == 0 or w[y == 0].sum() == 0:
        return np.nan
    return roc_auc_score(y, s, sample_weight=w)


def interval(v):
    return [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shuffles", type=int, default=200)
    parser.add_argument("--boots", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    manifest = {str(e["id"]): e for e in json.loads(MANIFEST.read_text())}
    cells, units, findability, notes = [], {}, {}, {}
    for model, cache_path in CACHES.items():
        with np.load(cache_path) as cache:
            ids = cache["route_id"].tolist()
            meta = [json.loads(m) for m in cache["meta"]]
            dq = cache["driving_queries"]
            depth = dq.shape[2]
            failing = np.array([not m["success"] for m in meta])
            fid = [ids[i] for i in np.flatnonzero(failing)]
            groups = np.array([manifest[r]["pair"] for r in fid])
            # activation blocks: standardise over all routes, PCA 32 fit on all, keep failing rows
            act = {}
            for summary, si in SUMMARIES.items():
                for label, f in FRACTIONS:
                    layer = int(np.floor(f * (depth - 1) + 0.5))
                    x = standardise(dq[:, si, layer].astype(np.float32))
                    z = PCA(n_components=32, random_state=0).fit_transform(x)
                    act[(summary, label)] = (layer, z[failing])
            beh_all = standardise(cm.kinematic_block(cache, meta))
        beh = beh_all[failing]
        notes[model] = {"routes": len(ids), "failing": int(failing.sum()), "depth": depth,
                        "behaviour_columns": int(beh.shape[1]),
                        "layers": {lab: act[("window", lab)][0] for lab, _ in FRACTIONS}}
        feats = {}
        for (summary, label), (layer, z) in act.items():
            feats[("act", summary, label)] = z
            feats[("both", summary, label)] = np.hstack([standardise(z) / np.sqrt(z.shape[1]),
                                                         standardise(beh) / np.sqrt(beh.shape[1])])
        feats[("beh", None, None)] = beh

        def in_gap(r, gap):
            e = manifest[r]
            return e.get("role") == "pilot_slice" and gap in e.get("practice_gaps", [])

        ys = {gap: np.array([in_gap(r, gap) for r in fid], dtype=int) for gap in GAPS[model]}
        n = len(fid)
        rng = np.random.default_rng(1)
        perms = [rng.permutation(n) for _ in range(args.shuffles)]
        # pair bootstrap draws, shared by all cells of this model (paired contrasts)
        upairs, pidx = np.unique(groups, return_inverse=True)
        brng = np.random.default_rng(2)
        weights = [np.bincount(brng.integers(0, len(upairs), len(upairs)), minlength=len(upairs))[pidx]
                   for _ in range(args.boots)]

        prepped, knn_neigh, folds_by_gap = {}, {}, {}
        for gap, y in ys.items():
            folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0)
                         .split(np.zeros(n), y, groups))
            folds_by_gap[gap] = folds
            for fk, x in feats.items():
                pre, neigh = [], []
                for tr, te in folds:
                    xtr, xte = fold_std(x, tr, te)
                    pre.append((tr, te, xtr, xte))
                    idx = NearestNeighbors(n_neighbors=10).fit(xtr).kneighbors(xte, return_distance=False)
                    neigh.append((te, tr[idx]))
                prepped[(gap,) + fk] = pre
                knn_neigh[(gap,) + fk] = neigh
        STATE.update(prepped=prepped, y=ys)
        tasks = [(key, perms) for key in prepped]
        with mp.get_context("fork").Pool(args.workers) as pool:
            nulls_log = dict(pool.map(logistic_task, tasks, chunksize=1))

        for gap, y in ys.items():
            unit_cells, scores = [], {}
            for fk in feats:
                key = (gap,) + fk
                kind, summary, label = fk
                for probe in ("logreg", "knn"):
                    if probe == "logreg":
                        s = logistic_oof(key, y)
                        pred = (s >= 0.5).astype(int)
                        null = np.array(nulls_log[key])
                    else:
                        neigh = knn_neigh[key]
                        s = knn_oof(neigh, y)
                        thr = np.zeros(n)
                        for tr, te in folds_by_gap[gap]:
                            thr[te] = y[tr].mean()
                        pred = (s >= thr).astype(int)
                        null = np.array([roc_auc_score(y[p], knn_oof(neigh, y[p])) for p in perms])
                    auc = roc_auc_score(y, s)
                    boot = np.array([weighted_auc(y, s, w) for w in weights])
                    scores[(probe,) + fk] = (s, boot, null)
                    cell = {"model": model, "gap": gap, "features": kind, "summary": summary, "fraction": label,
                            "layer": act[(summary, label)][0] if summary else None, "probe": probe,
                            "auroc": float(auc), "bal_acc": float(bal_acc(y, pred)),
                            "p_perm": float((1 + (null >= auc).sum()) / (len(null) + 1)), "interval": interval(boot)}
                    unit_cells.append(cell)
            cells += unit_cells
            actc = [k for k in scores if k[1] == "act"]
            obs_max = max(roc_auc_score(y, scores[k][0]) for k in actc)
            null_max = np.max([scores[k][2] for k in actc], axis=0)
            p_max = float((1 + (null_max >= obs_max).sum()) / (len(null_max) + 1))
            best = max(actc, key=lambda k: roc_auc_score(y, scores[k][0]))
            bk = ("logreg", "beh", None, None)
            both_k, act_k = ("logreg", "both") + MAIN, ("logreg", "act") + MAIN
            auc_of = lambda k: float(roc_auc_score(y, scores[k][0]))
            d_both = scores[both_k][1] - scores[bk][1]
            d_act = scores[act_k][1] - scores[bk][1]
            units[f"{model}:{gap}"] = {
                "n_gap_failing": int(y.sum()), "n_failing": n, "max_stat_p": p_max, "max_activation_auroc": obs_max,
                "best_activation_cell": list(map(str, best)), "behaviour_logreg_auroc": auc_of(bk),
                "both_logreg_window_8_23_auroc": auc_of(both_k), "act_logreg_window_8_23_auroc": auc_of(act_k),
                "both_minus_behaviour": {"delta": auc_of(both_k) - auc_of(bk), "interval": interval(d_both)},
                "act_minus_behaviour": {"delta": auc_of(act_k) - auc_of(bk), "interval": interval(d_act)},
            }

        # findability: multinomial probe on m23's inputs (window and route at 8/23, each prepared, concatenated)
        x = np.hstack([act[("window", "8/23")][1], act[("route", "8/23")][1]])
        cls = np.zeros(n, dtype=int)
        for j, gap in enumerate(GAPS[model], start=1):
            cls[(ys[gap] == 1) & (cls == 0)] = j
        dec = np.zeros((n, len(GAPS[model]) + 1))
        for tr, te in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0).split(x, cls, groups):
            xtr, xte = fold_std(x, tr, te)
            dec[te] = logreg().fit(xtr, cls[tr]).decision_function(xte)
        axes = cm.axes_from(standardise(dec), np.ones(n, bool), fid, "probe", "ward")[:10]
        for gap in GAPS[model]:
            truth = {fid[i] for i in np.flatnonzero(ys[gap])}
            jac = max(len(truth & set(a["rollouts"])) / len(truth | set(a["rollouts"])) for a in axes)
            findability[f"{model}:{gap}"] = {"supervised_jaccard": jac, "m23_jaccard": M23[(model, gap)],
                                             "gap": jac - M23[(model, gap)]}

    def outcome(keys, need):
        has = [k for k in keys if units[k]["has_information"]]
        if len(has) < need:
            return {"units_with_information": has, "outcome": 1, "median_findability_gap": None}
        med = float(np.median([findability[k]["gap"] for k in has]))
        return {"units_with_information": has, "outcome": 2 if med >= 0.20 else 3, "median_findability_gap": med}

    for k, u in units.items():
        u["beats_null"] = u["max_stat_p"] < 0.05
        u["adds_over_behaviour"] = u["both_minus_behaviour"]["interval"][0] > 0
        u["has_information"] = bool(u["beats_null"] and u["adds_over_behaviour"])
        u["findability"] = findability[k]
    per_model = {}
    for model in CACHES:
        keys = [k for k in units if k.startswith(model + ":")]
        per_model[model] = outcome(keys, len(keys) // 2 + 1)
    report = {"label": "DEV ONLY: label-reading probe diagnostic, independent reimplementation",
              "shuffles": args.shuffles, "boots": args.boots, "notes": notes, "units": units,
              "per_model": per_model, "overall": outcome(list(units), 3), "cells": cells}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: {f: units[k][f] for f in ("max_stat_p", "max_activation_auroc", "behaviour_logreg_auroc",
                                                    "both_minus_behaviour", "has_information")} | findability[k]
                      for k in units}, indent=1))
    print(json.dumps({"per_model": per_model, "overall": report["overall"], "cells": len(cells)}, indent=1))


if __name__ == "__main__":
    main()
