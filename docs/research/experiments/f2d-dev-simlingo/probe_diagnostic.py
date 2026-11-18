#!/usr/bin/env python3
"""Label-reading probe diagnostic (probe-diagnostic.md). Not a method and not a try; never used to tune one.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/probe_diagnostic.py --output report.json

Per (model, gap): one-vs-rest probes on failing routes only, CV grouped by Fail2Drive pair, a 200-shuffle permutation
null, pair-bootstrap intervals, and a findability step (m23-style clustering in a multinomial probe's out-of-fold
decision space). The decision rule is the protocol's, fixed before running.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier

HERE = Path(__file__).parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cm, b3 = _load("cache_methods"), _load("b3_behaviour")
MANIFEST = Path("configs/rollout/f2d-test-simlingo.manifest.json")
R2 = Path("results/savio/f2d-dev/round2")
MODELS = {"simlingo": ["F2D_PedestriansOnRoad", "F2D_FullyBlocked", "F2D_BadParking"],
          "tfpp": ["F2D_PedestriansOnRoad", "F2D_FullyBlocked"]}
FRACTIONS = {"0": 0.0, "1/4": 0.25, "8/23": 8 / 23, "1/2": 0.5, "3/4": 0.75, "1": 1.0}
SUMMARIES = {"route": 0, "window": 1}
M23 = {("simlingo", "F2D_PedestriansOnRoad"): 0.591, ("simlingo", "F2D_FullyBlocked"): 0.353,
       ("simlingo", "F2D_BadParking"): 0.171, ("tfpp", "F2D_PedestriansOnRoad"): 0.063,
       ("tfpp", "F2D_FullyBlocked"): 0.171}


def z(x):
    sd = x.std(0)
    return (x - x.mean(0)) / np.where(sd > 0, sd, 1.0)


def load_model(model: str):
    manifest = json.loads(MANIFEST.read_text())
    entry = {str(e["id"]): e for e in manifest}
    with np.load(R2 / model / "cache-w50.npz") as c:
        ids = [str(r) for r in c["route_id"].tolist()]
        meta = [json.loads(m) for m in c["meta"]]
        fail = np.array([not m["success"] for m in meta])
        act = {}
        for s, si in SUMMARIES.items():
            block = c["driving_queries"][:, si]
            for fname, f in FRACTIONS.items():
                layer = cm.depth_layers(block.shape[1], [f])[0]
                x = z(block[:, layer].astype(np.float64))
                act[(s, fname)] = PCA(n_components=32, random_state=0).fit_transform(x)[fail]
        kinds = sorted({k for m in meta for k in m["infractions"]})
        beh = np.array([b3.kinematics(c["ego_speed"][i], c["step"][i], m["failure_step"]) +
                        [float(m["infractions"].get(k, 0) or 0) for k in kinds] for i, m in enumerate(meta)])
    beh = z(beh)[fail]
    fids = [r for r, f in zip(ids, fail) if f]
    pairs = np.array([entry[r]["pair"] for r in fids])
    labels = {g: np.array([entry[r]["role"] == "pilot_slice" and g in entry[r]["practice_gaps"] for r in fids])
              for g in MODELS[model]}
    return fids, pairs, act, beh, labels


def both(a, b):
    return np.hstack([z(a) / np.sqrt(a.shape[1]), z(b) / np.sqrt(b.shape[1])])


def oof(x, y, folds, probe):
    """Pooled out-of-fold scores and balanced-accuracy predictions."""
    score, pred = np.zeros(len(y)), np.zeros(len(y), bool)
    for tr, te in folds:
        mu, sd = x[tr].mean(0), x[tr].std(0)
        sd = np.where(sd > 0, sd, 1.0)
        xtr, xte = (x[tr] - mu) / sd, (x[te] - mu) / sd
        if probe == "logreg":
            m = LogisticRegression(class_weight="balanced", C=0.1, max_iter=2000).fit(xtr, y[tr])
            score[te] = m.predict_proba(xte)[:, 1]
            pred[te] = score[te] >= 0.5
        else:
            m = KNeighborsClassifier(n_neighbors=10).fit(xtr, y[tr])
            score[te] = m.predict_proba(xte)[:, list(m.classes_).index(True)]
            pred[te] = score[te] >= y[tr].mean()
    return score, pred


def bal_acc(y, pred):
    return float(0.5 * (pred[y].mean() + (~pred[~y]).mean()))


def cell_list(act, beh):
    cells = [("act", s, f, p, act[(s, f)]) for s in SUMMARIES for f in FRACTIONS for p in ("logreg", "knn")]
    cells += [("beh", None, None, p, beh) for p in ("logreg", "knn")]
    cells += [("both", s, f, p, both(act[(s, f)], beh)) for s in SUMMARIES for f in FRACTIONS for p in ("logreg", "knn")]
    return cells


def null_row(cells, y, folds, seed):
    yp = np.random.default_rng(seed).permutation(y)
    return [roc_auc_score(yp, oof(x, yp, folds, p)[0]) for *_, p, x in cells]


def boot_weights(pairs, n, seed):
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(pairs, return_inverse=True)
    for _ in range(n):
        counts = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        yield counts[inv].astype(float)


def wauc(y, s, w):
    if w[y].sum() == 0 or w[~y].sum() == 0:
        return np.nan
    return roc_auc_score(y, s, sample_weight=w)


def repeated_splits(args) -> None:
    """Post hoc: how much each cell's AUROC moves with the fold assignment alone."""
    rows = []
    for model, gaps in MODELS.items():
        fids, pairs, act, beh, labels = load_model(model)
        cells = cell_list(act, beh)
        for gap in gaps:
            y = labels[gap]
            per_seed = []
            for seed in range(args.split_seeds):
                folds = list(StratifiedGroupKFold(5, shuffle=True, random_state=seed).split(np.zeros(len(y)), y, pairs))
                per_seed.append([roc_auc_score(y, oof(x, y, folds, p)[0]) for *_, p, x in cells])
            a = np.array(per_seed)
            for i, (kind, s, f, p, _) in enumerate(cells):
                rows.append({"model": model, "gap": gap, "features": kind, "summary": s, "fraction": f, "probe": p,
                             "positive_pairs": len(set(pairs[y])), "auroc_mean": float(a[:, i].mean()),
                             "auroc_min": float(a[:, i].min()), "auroc_max": float(a[:, i].max())})
            print(model, gap, flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"label": "POST HOC split-seed check (probe-diagnostic.md amendment)",
                                       "split_seeds": args.split_seeds, "cells": rows}, indent=1) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shuffles", type=int, default=200)
    parser.add_argument("--boots", type=int, default=1000)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--split-seeds", type=int, default=0,
                        help="post hoc (probe-diagnostic.md, amendment): AUROC of every cell over this many CV split "
                             "seeds, no null, bootstrap or findability")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.split_seeds:
        return repeated_splits(args)
    out = {"label": "LABEL-READING DIAGNOSTIC (probe-diagnostic.md); not a method, not a try", "cells": [], "units": {}}
    for model, gaps in MODELS.items():
        fids, pairs, act, beh, labels = load_model(model)
        cells = cell_list(act, beh)
        for gap in gaps:
            y = labels[gap]
            folds = list(StratifiedGroupKFold(5, shuffle=True, random_state=0).split(np.zeros(len(y)), y, pairs))
            obs = [oof(x, y, folds, p) for *_, p, x in cells]
            auc = np.array([roc_auc_score(y, s) for s, _ in obs])
            # Shuffle k uses default_rng(1)'s k-th child seed, so parallel order does not matter.
            seeds = np.random.default_rng(1).integers(0, 2**63 - 1, args.shuffles)
            null = np.array(Parallel(n_jobs=args.jobs)(delayed(null_row)(cells, y, folds, int(s)) for s in seeds))
            weights = list(boot_weights(pairs, args.boots, 2))
            boot = np.array([[wauc(y, s, w) for s, _ in obs] for w in weights])
            is_act = np.array([c[0] == "act" for c in cells])
            for i, (kind, s, f, p, _) in enumerate(cells):
                out["cells"].append({"model": model, "gap": gap, "features": kind, "summary": s, "fraction": f,
                                     "probe": p, "auroc": float(auc[i]), "bal_acc": bal_acc(y, obs[i][1]),
                                     "p_perm": float((1 + (null[:, i] >= auc[i]).sum()) / (args.shuffles + 1)),
                                     "interval": np.nanpercentile(boot[:, i], [2.5, 97.5]).tolist()})
            ix = {(c[0], c[1], c[2], c[3]): i for i, c in enumerate(cells)}
            maxp = float((1 + (null[:, is_act].max(1) >= auc[is_act].max()).sum()) / (args.shuffles + 1))

            def contrast(a, b):
                d = boot[:, ix[a]] - boot[:, ix[b]]
                return {"delta": float(auc[ix[a]] - auc[ix[b]]), "interval": np.nanpercentile(d, [2.5, 97.5]).tolist()}

            add = contrast(("both", "window", "8/23", "logreg"), ("beh", None, None, "logreg"))
            act_vs = contrast(("act", "window", "8/23", "logreg"), ("beh", None, None, "logreg"))
            best = int(np.flatnonzero(is_act)[auc[is_act].argmax()])
            out["units"][f"{model}:{gap}"] = {
                "n_gap": int(y.sum()), "n_failing": len(y), "max_stat_p": maxp,
                "best_act_cell": {k: out["cells"][-len(cells) + best][k] for k in ("summary", "fraction", "probe", "auroc")},
                "beh_logreg_auroc": float(auc[ix[("beh", None, None, "logreg")]]),
                "both_minus_beh": add, "act_minus_beh": act_vs,
                "has_information": bool(maxp < 0.05 and add["interval"][0] > 0)}
        # Findability: multinomial probe on m23's inputs, out-of-fold decision space, m23-style clustering.
        x = np.hstack([act[("window", "8/23")], act[("route", "8/23")]])
        cls = np.zeros(len(fids), int)
        for k, g in enumerate(gaps, 1):
            cls[labels[g]] = k
        dec = np.zeros((len(fids), len(gaps) + 1))
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=0).split(x, cls, pairs):
            mu, sd = x[tr].mean(0), x[tr].std(0)
            sd = np.where(sd > 0, sd, 1.0)
            m = LogisticRegression(class_weight="balanced", C=0.1, max_iter=2000).fit((x[tr] - mu) / sd, cls[tr])
            dec[te] = m.decision_function((x[te] - mu) / sd)
        axes = cm.axes_from(z(dec), np.ones(len(fids), bool), fids, "probe-subspace")[:10]
        sets = [set(a["rollouts"]) for a in axes]
        for g in gaps:
            gset = {r for r, v in zip(fids, labels[g]) if v}
            sup = max(len(gset & a) / len(gset | a) for a in sets)
            u = out["units"][f"{model}:{g}"]
            u["findability"] = {"supervised_subspace_jaccard": sup, "m23_jaccard": M23[(model, g)],
                                "gap": sup - M23[(model, g)]}

    def outcome(keys):
        have = [k for k in keys if out["units"][k]["has_information"]]
        enough = len(have) >= 3 if len(keys) == 5 else 2 * len(have) > len(keys)  # overall: 3 of 5; per model: majority
        if not enough:
            return {"outcome": 1, "units_with_information": have}
        med = float(np.median([out["units"][k]["findability"]["gap"] for k in have]))
        return {"outcome": 2 if med >= 0.20 else 3, "units_with_information": have, "median_findability_gap": med}

    out["cells_tested"] = len(out["cells"])
    out["overall"] = outcome(list(out["units"]))
    out["per_model"] = {m: outcome([k for k in out["units"] if k.startswith(m + ":")]) for m in MODELS}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    for k, u in out["units"].items():
        print(json.dumps({k: {"maxp": u["max_stat_p"], "best": u["best_act_cell"]["auroc"], "beh": u["beh_logreg_auroc"],
                              "add": u["both_minus_beh"], "find": u["findability"], "info": u["has_information"]}}))
    print(json.dumps({"overall": out["overall"], "per_model": out["per_model"], "cells": out["cells_tested"]}))


if __name__ == "__main__":
    main()
