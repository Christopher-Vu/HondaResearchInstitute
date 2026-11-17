#!/usr/bin/env python3
"""Score methods over several models in one bootstrap (prereg §4 and A3: the pooled headline; round 2's dev score).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/pooled_score.py --manifest MANIFEST \
        --model simlingo SIM_ROUTES --model tfpp TFPP_ROUTES \
        --gaps simlingo:F2D_FullyBlocked tfpp:F2D_FullyBlocked ... --decoys tfpp:F2D_HardBrake ... \
        --method r01 simlingo=a.json tfpp=b.json --rival B3_behaviour simlingo=c.json tfpp=d.json \
        --tried 191 --output report.json

The models share Fail2Drive routes, so route ids are namespaced "model/id" and the bootstrap resamples pairs jointly:
one draw of pairs weights every model's routes in that pair. The pooled score is the mean of best Jaccard over every
(model, gap) unit, each weighted equally. Per-model and per-gap scores are reported beside it. Per-unit scoring,
distinct axes, the top 10, chance (B1, drawn per model from its failing routes) and the contrasts are sprint_score.py's.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

from harness.scoring_run import load_pool

SPEC = importlib.util.spec_from_file_location("sprint_score", Path(__file__).with_name("sprint_score.py"))
sprint_score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sprint_score)


def tagged(model: str, ids) -> set[str]:
    return {f"{model}/{r}" for r in ids}


def read_entry(name: str, specs: list[str], models: list[str]) -> dict[str, list[set[str]]]:
    """One method or rival: model=spec for every model, each read as sprint_score reads it."""
    given = dict(s.split("=", 1) for s in specs)
    if set(given) != set(models):
        raise SystemExit(f"{name}: needs exactly one spec for each of {models}, got {sorted(given)}")
    return {m: [tagged(m, a) for a in sprint_score.read_method(given[m])[1]] for m in models}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", nargs=2, action="append", required=True, metavar=("NAME", "ROUTES"))
    parser.add_argument("--gaps", nargs="+", required=True, metavar="MODEL:TYPE")
    parser.add_argument("--decoys", nargs="*", default=[], metavar="MODEL:TYPE")
    parser.add_argument("--method", nargs="+", action="append", required=True, metavar="NAME MODEL=SPEC")
    parser.add_argument("--rival", nargs="+", action="append", default=[], metavar="NAME MODEL=SPEC")
    parser.add_argument("--reported-rival", nargs="+", action="append", default=[], metavar="NAME MODEL=SPEC")
    parser.add_argument("--primary-rival", default="B3_behaviour")
    parser.add_argument("--tried", type=int, required=True)
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    models = [m for m, _ in args.model]
    pair_of, failed, gaps, decoys, failing_pool = {}, {}, {}, {}, {}
    for model, routes in args.model:
        manifest, outcome = load_pool([args.manifest], [Path(routes)])
        slices = lambda c: {str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and c in e["practice_gaps"]}
        pair_of |= {f"{model}/{e['id']}": e["pair"] for e in manifest}
        failed |= {f"{model}/{r}": v for r, v in outcome.items()}
        failing_pool[model] = sorted(f"{model}/{r}" for r, v in outcome.items() if v)
        for unit in args.gaps:
            m, c = unit.split(":", 1)
            if m == model:
                gaps[unit] = tagged(model, {r for r in slices(c) if outcome.get(r)})
        for unit in args.decoys:
            m, c = unit.split(":", 1)
            if m == model:
                decoys[unit] = tagged(model, slices(c) & outcome.keys())
    if missing := [u for u in args.gaps if u not in gaps]:
        raise SystemExit(f"gap units naming no --model: {missing}")
    pool = sorted(failed)
    pairs = sorted({pair_of[r] for r in pool})
    index = {p: i for i, p in enumerate(pairs)}
    of_model = lambda d, m: {u: g for u, g in d.items() if u.split(":", 1)[0] == m}

    methods = {e[0]: read_entry(e[0], e[1:], models) for e in args.method}
    rivals = {e[0]: read_entry(e[0], e[1:], models) for e in args.rival + args.reported_rival}
    reported = {e[0] for e in args.reported_rival}
    every = {**methods, **rivals}

    def pooled(entry, weight=None) -> float:
        return float(np.mean([sprint_score.best(entry[u.split(":", 1)[0]], g, weight) for u, g in gaps.items()]))

    rng = np.random.default_rng(args.seed)
    rows = {}
    for name, entry in every.items():
        rows[name] = {
            "role": "method" if name in methods else "rival", "mean_best": pooled(entry),
            "per_model": {m: sprint_score.mean_best(entry[m], of_model(gaps, m)) for m in models if of_model(gaps, m)},
            "per_gap": {u: sprint_score.best(entry[u.split(":", 1)[0]], g) for u, g in gaps.items()},
            "decoy_hit_rate": {m: sprint_score.decoy_rate(entry[m], of_model(decoys, m)) for m in models},
            "chance_B1": float(np.mean([sprint_score.chance(entry[m], of_model(gaps, m), failing_pool[m], rng)
                                        for m in models for _ in of_model(gaps, m)])),
        }

    names = list(every)
    draws = np.zeros((args.replicates, len(names)))
    for b in range(args.replicates):
        counts = np.bincount(rng.integers(0, len(pairs), len(pairs)), minlength=len(pairs)).astype(float)
        weight = {r: counts[index[pair_of[r]]] for r in pool}
        draws[b] = [pooled(every[n], weight) for n in names]
    column = {n: i for i, n in enumerate(names)}

    def contrast(m: str, against: list[str]) -> dict:
        delta = draws[:, column[m]] - draws[:, [column[r] for r in against]].max(axis=1)
        point = rows[m]["mean_best"] - max(rows[r]["mean_best"] for r in against)
        return {"delta": point, "interval": [float(np.percentile(delta, 2.5)), float(np.percentile(delta, 97.5))],
                "p_one_sided": float((delta <= 0).mean())}

    for m in methods:
        if rivals:
            rows[m]["vs"] = {r: contrast(m, [r]) for r in rivals}
            rows[m]["vs_best_rival"] = contrast(m, [r for r in rivals if r not in reported])
    report = {"label": args.label, "methods_tried": args.tried, "budget_m": sprint_score.M, "models": models,
              "gaps": {u: len(g) for u, g in gaps.items()}, "decoys": {u: len(d) for u, d in decoys.items()},
              "primary_rival": args.primary_rival, "reported_rivals": sorted(reported), "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for n in names:
        row = rows[n]
        print(json.dumps({n: round(row["mean_best"], 3), "per_model": {m: round(v, 3) for m, v in row["per_model"].items()},
                          "vs_primary": row.get("vs", {}).get(args.primary_rival, {}).get("delta"),
                          "p": row.get("vs", {}).get(args.primary_rival, {}).get("p_one_sided")}))


if __name__ == "__main__":
    main()
