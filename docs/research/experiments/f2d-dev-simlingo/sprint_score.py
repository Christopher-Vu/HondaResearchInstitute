#!/usr/bin/env python3
"""The discovery sprint's scorer (docs/prd-discovery-sprint.md §4; prereg amendment A1).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/sprint_score.py \
        --method m03.json --rival B3_behaviour=b3.json --rival B7=DIR:B7_actstats:L10_k64_s0 ... \
        --manifest MANIFEST --routes routes.jsonl --gaps F2D_A F2D_B --decoys F2D_C --tried 3 --output report.json

A method file is {"method": name, "axes": [{"name": ..., "rollouts": [route ids]}, ...]} in the method's own rank
order. A rival can also be read from a discovery.emit_directives directory as DIR:FAMILY[:DICTIONARY], its axes in
their own rank order. Only the first M = 10 distinct axes count (amendment A2 drops exact repeats first): nobody
picks an axis with the key.

Per method: mean over gaps of the best Jaccard among its top 10 (primary); recall at Jaccard 0.5 under one Hungarian
assignment; decoy hit rate; chance (B1: random axes of the same sizes drawn from the failing routes, mean of 50 draws; before 2026-11-15
it drew from all routes and read too low, found by Jerry's agent). Against each rival and the
best rival (re-taken in every replicate; reported rivals are compared but never the best rival): delta, 95% percentile interval and one-sided p from a paired bootstrap that
resamples Fail2Drive pairs, each pair carrying all its seeds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from harness.bootstrap import weighted_jaccard
from harness.scoring import MATCH_THRESHOLD, _hungarian, jaccard
from harness.scoring_run import load_pool

M = 10


def distinct(axes: list[set[str]]) -> list[set[str]]:
    """Amendment A2: an axis identical to one listed earlier is dropped before the top 10 is taken."""
    kept: list[set[str]] = []
    for axis in axes:
        if axis not in kept:
            kept.append(axis)
    return kept[:M]


def read_method(spec: str) -> tuple[str, list[set[str]]]:
    if spec.endswith(".json") and Path(spec).is_file():
        raw = json.loads(Path(spec).read_text())
        return raw["method"], distinct([set(map(str, a["rollouts"])) for a in raw["axes"]])
    directory, family, *dictionary = spec.split(":")
    for path in sorted(Path(directory).glob("*.json")):
        raw = json.loads(path.read_text())
        if raw["family"] == family and (not dictionary or raw["dictionary"] == dictionary[0]):
            axes = sorted(raw["directive"]["axes"], key=lambda a: a["rank"])
            return family, distinct([{e["episode_id"] for e in a["supporting_episodes"]} for a in axes])
    raise ValueError(f"no directive for {spec}")


def best(axes: list[set[str]], gap: set[str], weight: dict[str, float] | None = None) -> float:
    return max((jaccard(gap, a) if weight is None else weighted_jaccard(gap, a, weight) for a in axes), default=0.0)


def mean_best(axes, gaps, weight=None) -> float:
    return float(np.mean([best(axes, g, weight) for g in gaps.values()]))


def recall(axes, gaps) -> float:
    if not axes:
        return 0.0
    matrix = [[jaccard(g, a) for a in axes] for g in gaps.values()]
    return sum(matrix[r][c] >= MATCH_THRESHOLD for r, c in _hungarian(matrix)) / len(gaps)


def decoy_rate(axes, decoys) -> float | None:
    if not decoys or not axes:
        return None
    return sum(any(len(a & d) / len(a) >= 0.5 for d in decoys.values()) for a in axes if a) / len(axes)


def chance(axes, gaps, pool: list[str], rng) -> float:
    draws = [[set(rng.choice(pool, size=min(len(a), len(pool)), replace=False)) for a in axes] for _ in range(50)]
    return float(np.mean([mean_best(d, gaps) for d in draws]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--method", action="append", required=True, help="a method file or directory spec")
    parser.add_argument("--rival", action="append", default=[], help="NAME=spec")
    parser.add_argument("--reported-rival", action="append", default=[],
                        help="NAME=spec: compared with every method, but not part of the best rival (A2: B3-infraction)")
    parser.add_argument("--primary-rival", default="B3_behaviour")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--gaps", nargs="+", required=True)
    parser.add_argument("--decoys", nargs="*", default=[])
    parser.add_argument("--tried", type=int, required=True, help="methods tried on this pool so far, this one included")
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest, failed = load_pool([args.manifest], [args.routes])
    slices = lambda c: {str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and c in e["practice_gaps"]}
    gaps = {c: {r for r in slices(c) if failed.get(r)} for c in args.gaps}
    decoys = {c: slices(c) & failed.keys() for c in args.decoys}
    pool = sorted(failed)
    failing_pool = [r for r in pool if failed[r]]  # B1 draws failing routes only, as every method's axes do
    pair_of = {str(e["id"]): e["pair"] for e in manifest}
    pairs = sorted({pair_of[r] for r in pool})
    index = {p: i for i, p in enumerate(pairs)}

    methods = dict(read_method(spec) for spec in args.method)
    rivals = {name: read_method(spec)[1] for name, spec in (r.split("=", 1) for r in args.rival + args.reported_rival)}
    reported = {r.split("=", 1)[0] for r in args.reported_rival}
    rng = np.random.default_rng(args.seed)
    rows = {}
    for name, axes in {**methods, **rivals}.items():
        rows[name] = {"role": "method" if name in methods else "rival", "axes": len(axes),
                      "mean_best": mean_best(axes, gaps), "recall_at_0.5": recall(axes, gaps),
                      "decoy_hit_rate": decoy_rate(axes, decoys), "chance_B1": chance(axes, gaps, failing_pool, rng),
                      "per_gap": {c: best(axes, g) for c, g in gaps.items()}}

    draws = np.zeros((args.replicates, len(methods) + len(rivals)))
    names = [*methods, *rivals]
    every = {**methods, **rivals}
    for b in range(args.replicates):
        counts = np.bincount(rng.integers(0, len(pairs), len(pairs)), minlength=len(pairs)).astype(float)
        weight = {r: counts[index[pair_of[r]]] for r in pool}
        draws[b] = [mean_best(every[n], gaps, weight) for n in names]
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
    report = {"label": "DEV: SimLingo Fail2Drive test pool; p values exploratory", "methods_tried": args.tried,
              "budget_m": M, "gaps": {c: len(g) for c, g in gaps.items()},
              "decoys": {c: len(d) for c, d in decoys.items()}, "primary_rival": args.primary_rival,
              "reported_rivals": sorted(reported), "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for m in methods:
        row, versus = rows[m], rows[m].get("vs", {}).get(args.primary_rival)
        print(json.dumps({"method": m, "mean_best": round(row["mean_best"], 3),
                          "per_gap": {c: round(v, 3) for c, v in row["per_gap"].items()},
                          "vs_primary": versus, "vs_best_rival": row.get("vs_best_rival"), "tried": args.tried}))
    for r in rivals:
        print(json.dumps({"rival": r, "mean_best": round(rows[r]["mean_best"], 3),
                          "per_gap": {c: round(v, 3) for c, v in rows[r]["per_gap"].items()}}))


if __name__ == "__main__":
    main()
