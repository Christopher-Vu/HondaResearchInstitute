#!/usr/bin/env python3
"""Robustness of the sprint's leads on SimLingo dev (VARIANTS.md "Lead robustness"). Scoring side: reads the key.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/robustness.py --replicates 30 --output OUT.json

Two checks, both fixed before they run:
1. Resampling. Draw 80% of Fail2Drive pairs without replacement, a pair carrying all its routes. On those routes only,
   refit every lead from scratch (standardising, PCA, clustering, pooling) and refit B3-behaviour; B3-infraction is
   regrouped; B7-pool's axes are fixed (its dictionary is not retrained) and cut to the sample. Score each against the
   gaps cut to the sample. Reported per method: score mean, sd and 5th to 95th percentile; the share of replicates
   where it beats each rival and all rivals; and axis stability, the mean over the full-pool axes of the best Jaccard
   with a replicate axis, both cut to the sample.
2. Neighbours. The same lead with one setting moved one step (layer +-1, PCA width +-16, or +-4 for m49), on the full
   pool. These are counted as tries but cannot replace the lead: they say whether the lead sits on a narrow peak.
3. m49 seeds: its mixture refit with seeds 1 to 10 on the full pool. Not tries; nothing is picked from them.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from itertools import zip_longest
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture

from harness.scoring import jaccard
from harness.scoring_run import load_pool


def _load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cm, ss, b3 = _load("cache_methods"), _load("sprint_score"), _load("b3_behaviour")
S = "results/savio/f2d-dev/simlingo"
GAPS = ["F2D_PedestriansOnRoad", "F2D_FullyBlocked", "F2D_BadParking"]

# source: (cache, layers, summary, linkage, PCA width); all on driving_queries
SOURCES = {
    "w50L8": ("w50", [8], "window", "ward", 32), "w50L8p64": ("w50", [8], "window", "ward", 64),
    "w50L8p48": ("w50", [8], "window", "ward", 48), "w50L8p80": ("w50", [8], "window", "ward", 80),
    "m12": ("w6", [8], "window", "average", 32), "m12L7": ("w6", [7], "window", "average", 32),
    "m12L9": ("w6", [9], "window", "average", 32),
    "R20": ("w50", [20], "route", "ward", 32), "R19": ("w50", [19], "route", "ward", 32),
    "R21": ("w50", [21], "route", "ward", 32), "R8": ("w50", [8], "route", "ward", 32),
    "R7": ("w50", [7], "route", "ward", 32), "R9": ("w50", [9], "route", "ward", 32),
    # m49 (probe_mixture.py gmm): diagonal GMM on the failing routes' PCA scores, K 4 to 12 by BIC
    "g8": ("w50", [8], "window", "gmm", 16), "g7": ("w50", [7], "window", "gmm", 16),
    "g9": ("w50", [9], "window", "gmm", 16), "g8p12": ("w50", [8], "window", "gmm", 12),
    "g8p20": ("w50", [8], "window", "gmm", 20),
}
LEADS = {"m41": ["m12", "R20"], "m40": ["w50L8p64", "R20"], "m44": ["w50L8", "R20"], "m23": ["w50L8", "R8"],
         "m39-p64": ["w50L8p64"], "m12": ["m12"], "m49": ["g8"]}
NEIGHBOURS = {"m41|R19": ["m12", "R19"], "m41|R21": ["m12", "R21"], "m41|m12L7": ["m12L7", "R20"],
              "m41|m12L9": ["m12L9", "R20"], "m40|p48": ["w50L8p48", "R20"], "m40|p80": ["w50L8p80", "R20"],
              "m23|R7": ["w50L8", "R7"], "m23|R9": ["w50L8", "R9"],
              "m49|L7": ["g7"], "m49|L9": ["g9"], "m49|p12": ["g8p12"], "m49|p20": ["g8p20"]}
SEEDS = range(1, 11)  # m49's mixture refit with other seeds on the full pool: not tries, nothing is picked from them


def source_axes(raw, name, rows, failing, ids, seed=0):
    cache, layers, summary, method, dims = SOURCES[name]
    block = raw[cache][summary]
    x = np.hstack([cm.standardise(block[rows][:, l].astype(np.float32)) for l in layers])
    if method == "gmm":
        z = PCA(n_components=dims, random_state=0).fit_transform(cm.standardise(x))[failing[rows]]
        fits = {}
        for k in range(4, 13):  # a K whose fit collapses on a resample is skipped; BIC picks among those that fit
            try:
                fits[k] = GaussianMixture(k, covariance_type="diag", random_state=seed, n_init=3).fit(z)
            except ValueError:
                pass
        labels = min(fits.values(), key=lambda m: m.bic(z)).predict(z)
        fail_ids = [ids[r] for r in rows[failing[rows]]]
        groups = sorted(({fail_ids[j] for j in np.flatnonzero(labels == c)} for c in set(labels)), key=len, reverse=True)
        return ss.distinct(groups)
    z = cm.standardise(PCA(n_components=dims, random_state=0).fit_transform(cm.standardise(x)))
    sub_ids = [ids[r] for r in rows]
    return ss.distinct([set(a["rollouts"]) for a in cm.axes_from(z, failing[rows], sub_ids, name, method)])


def pool(ranked):
    if len(ranked) == 1:
        return ranked[0]
    kept = []
    for layer in zip_longest(*ranked):
        for axis in layer:
            if axis and len(kept) < 10 and all(jaccard(axis, k) < 0.8 for k in kept):
                kept.append(axis)
    return kept


def b3_axes(cache, meta, rows, failing, ids):
    kinds = sorted({k for m in meta for k in m["infractions"]})
    f = np.array([b3.kinematics(cache["ego_speed"][i], cache["step"][i], meta[i]["failure_step"]) +
                  [float(meta[i]["infractions"].get(k, 0) or 0) for k in kinds] for i in rows])
    f = (f - f.mean(0)) / np.where(f.std(0) > 0, f.std(0), 1.0)
    return ss.distinct([set(a["rollouts"]) for a in cm.axes_from(f, failing[rows], [ids[r] for r in rows], "b3", "ward")])


def infraction_axes(meta, rows, failing, ids):
    groups = {}
    for r in rows:
        if failing[r]:
            for kind in [k for k, v in meta[r]["infractions"].items() if v] or ["none"]:
                groups.setdefault(kind, set()).add(ids[r])
    return ss.distinct([g for _, g in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replicates", type=int, default=30)
    parser.add_argument("--fraction", type=float, default=0.8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest, failed = load_pool([Path("configs/rollout/f2d-test-simlingo.manifest.json")],
                                 [Path("results/savio/f2d-test-simlingo/routes.jsonl")])
    slices = lambda c: {str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and c in e["practice_gaps"]}
    gaps = {c: {r for r in slices(c) if failed.get(r)} for c in GAPS}
    pair_of = {str(e["id"]): e["pair"] for e in manifest}
    raw, ids = {}, None
    for key, path in (("w6", f"{S}/cache.npz"), ("w50", f"{S}/cache-w50.npz")):
        with np.load(path) as c:
            these = c["route_id"].tolist()
            assert ids is None or these == ids, "caches differ in route order"
            ids = these
            raw[key] = {"window": c["driving_queries"][:, 1], "route": c["driving_queries"][:, 0]}
            if key == "w6":
                meta = [json.loads(m) for m in c["meta"]]
                kin = {"ego_speed": c["ego_speed"], "step": c["step"]}
    failing = np.array([not m["success"] for m in meta])
    b7 = ss.read_method(f"{S}/v1/plain/directives-ms20:B7_pool:L10_k64_s0")[1]
    pairs = sorted({pair_of[r] for r in ids})
    rng = np.random.default_rng(0)

    def run(rows, names):
        cut = {c: g & {ids[r] for r in rows} for c, g in gaps.items()}
        cache = {n: source_axes(raw, n, rows, failing, ids) for n in {s for v in names.values() for s in v}}
        scores = {m: ss.mean_best(pool([cache[s] for s in src]), cut) for m, src in names.items()}
        axes = {m: pool([cache[s] for s in src]) for m, src in names.items()}
        keep = {ids[r] for r in rows}
        rivals = {"B3_behaviour": b3_axes(kin, meta, rows, failing, ids), "B3_infraction": infraction_axes(meta, rows, failing, ids),
                  "B7_pool": ss.distinct([a & keep for a in b7 if a & keep])}
        scores |= {r: ss.mean_best(a, cut) for r, a in rivals.items()}
        return scores, axes

    full_rows = np.arange(len(ids))
    full, full_axes = run(full_rows, LEADS | NEIGHBOURS)
    reps = []
    for _ in range(args.replicates):
        chosen = set(rng.choice(pairs, size=int(round(args.fraction * len(pairs))), replace=False))
        rows = np.array([i for i, r in enumerate(ids) if pair_of[r] in chosen])
        scores, axes = run(rows, LEADS)
        keep = {ids[r] for r in rows}
        stab = {}
        for m in LEADS:
            ref = [a & keep for a in full_axes[m] if a & keep]
            stab[m] = float(np.mean([max(jaccard(a, b) for b in axes[m]) for a in ref]))
        reps.append({"scores": scores, "stability": stab})
    rivals = ("B3_behaviour", "B3_infraction", "B7_pool")
    summary = {}
    for m in LEADS:
        s = np.array([r["scores"][m] for r in reps])
        summary[m] = {"full": full[m], "mean": float(s.mean()), "sd": float(s.std()),
                      "p5_p95": [float(np.percentile(s, 5)), float(np.percentile(s, 95))],
                      "beats": {r: float(np.mean([x["scores"][m] > x["scores"][r] for x in reps])) for r in rivals},
                      "beats_all": float(np.mean([all(x["scores"][m] > x["scores"][r] for r in rivals) for x in reps])),
                      "stability": float(np.mean([x["stability"][m] for x in reps]))}
    cut_all = gaps
    seeds = {}
    for seed in SEEDS:
        seeds[seed] = ss.mean_best(source_axes(raw, "g8", full_rows, failing, ids, seed), cut_all)
    rival_summary = {r: {"full": full[r], "mean": float(np.mean([x["scores"][r] for x in reps]))} for r in rivals}
    out = {"label": "DEV robustness; scoring side", "replicates": args.replicates, "fraction": args.fraction,
           "leads": summary, "rivals": rival_summary, "neighbours": {n: full[n] for n in NEIGHBOURS},
           "m49_seeds": seeds}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
