#!/usr/bin/env python3
"""H24 and H25's scorer: groups of failing routes against public categories, with B3 and a matched random control.

    PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/score_sets.py --axes axes.json \
        --manifests M.json [...] --routes R.jsonl [...] --categories C [...] --b3 B3.json --min-runs 12 \
        --pool NAME --label TEXT --output report.json [--restrict-to IDS.json] [--pairs]

`--axes` holds {method: [{"run": r, "axes": [[route id, ...], ...]}]}. A category's failing set is its slice routes
that failed, from the public manifests and outcomes. A run's score on a category is the best Jaccard of any of its
axes with the category's failing set (the best axis is chosen using that set). The method score is the mean over
categories.

Rivals per run: B3 (the directive in `--b3`) and the matched random control: RANDOM_DRAWS random partitions of the
pool's failing routes into groups of the run's own axis sizes (independent draws when the sizes sum to more than the
pool), averaged. Delta = method minus the better rival, as a category mean.

The rule (all three needed for `ahead`):
1. the median delta over runs is at least MARGIN;
2. for every category, the median over runs of that category's delta is above 0 (with three categories this is what a
   category bootstrap's lower end measures, so it is stated directly);
3. a route bootstrap (resample each category's failing routes with replacement, REPLICATES times, recompute every
   score with weighted Jaccard, the random draws held fixed) has its 2.5th percentile of the median delta above 0.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any, Sequence

import numpy as np

from harness.scoring_run import load_pool

MARGIN, PAIR_FLOOR, RANDOM_DRAWS, REPLICATES, SEED = 0.15, 0.3, 50, 1000, 20261016
SENTENCES = {
    "untested": "{label} is untested: {method} produced fewer than {min_runs} runs with an axis.",
    "ahead": "On {pool}, {method} recovers the categories' failing routes better than B3 and random groups of the "
             "same sizes, by a median of at least 0.15 Jaccard, on every category.",
    "not_ahead": "On {pool}, {method} is not shown to recover the categories' failing routes better than B3 and "
                 "random groups of the same sizes.",
}


def category_sets(manifest: Sequence[dict], failed: dict[str, bool], categories: Sequence[str]) -> list[set[str]]:
    sets = [{str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and category in e["practice_gaps"]
             and failed.get(str(e["id"]))} for category in categories]
    empty = [c for c, s in zip(categories, sets) if not s]
    if empty:
        raise ValueError(f"categories with no failing route (misspelt?): {empty}")
    return sets


def slice_only_pairs(manifest: Sequence[dict], failed: dict[str, bool], category: str) -> list[tuple[str, str]]:
    twins = {e["base_id"]: str(e["id"]) for e in manifest if e["role"] == "pilot_neighbourhood"}
    pairs = []
    for e in manifest:
        twin = twins.get(e["base_id"])
        if e["role"] == "pilot_slice" and category in e["practice_gaps"] and twin in failed and failed.get(str(e["id"])):
            if not failed[twin]:
                pairs.append((str(e["id"]), twin))
    return pairs


def matrix(groups: Sequence[Sequence[str]], index: dict[str, int]) -> np.ndarray:
    out = np.zeros((len(groups), len(index)), bool)
    for row, group in enumerate(groups):
        out[row, [index[m] for m in group]] = True
    return out


def best_scores(axes: np.ndarray, targets: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """Per category, the best weighted Jaccard of any axis (rows of `axes`) with each target row. 0 with no axes."""
    if not len(axes):
        return np.zeros(len(targets))
    tw = targets * weight
    inter = axes.astype(float) @ tw.T
    union = (axes.astype(float) @ weight)[:, None] + tw.sum(axis=1)[None, :] - inter
    return np.where(union > 0, inter / np.where(union > 0, union, 1), 0.0).max(axis=0)


def random_draws(sizes: Sequence[int], n: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(RANDOM_DRAWS):
        rows = np.zeros((len(sizes), n), bool)
        if sum(sizes) <= n:
            order, start = rng.permutation(n), 0
            for row, size in enumerate(sizes):
                rows[row, order[start:start + size]] = True
                start += size
        else:
            for row, size in enumerate(sizes):
                rows[row, rng.choice(n, size=min(size, n), replace=False)] = True
        draws.append(rows)
    return draws


def scores_under(runs: list[np.ndarray], draws: list[list[np.ndarray]], b3: np.ndarray, targets: np.ndarray,
                 weight: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    method = np.stack([best_scores(axes, targets, weight) for axes in runs])
    rand = np.stack([np.mean([best_scores(d, targets, weight) for d in run], axis=0) for run in draws])
    return method, rand, best_scores(b3, targets, weight)


def category_deltas(method: np.ndarray, rand: np.ndarray, b3: np.ndarray) -> np.ndarray:
    return method - np.maximum(rand, b3[None, :])


def route_bootstrap(runs, draws, b3, targets, n) -> list[float]:
    rng = np.random.default_rng(SEED)
    out = []
    for _ in range(REPLICATES):
        weight = np.ones(n)
        for target in targets:
            members = np.flatnonzero(target)
            weight[members] = np.bincount(rng.integers(0, len(members), len(members)), minlength=len(members))
        method, rand, b3s = scores_under(runs, draws, b3, targets, weight)
        out.append(float(np.median(method.mean(axis=1) - np.maximum(rand.mean(axis=1), b3s.mean()))))
    return out


def outcome(median_delta: float, per_category: Sequence[float], low: float, runs_with_axes: int, min_runs: int) -> str:
    if runs_with_axes < min_runs:
        return "untested"
    ahead = median_delta >= MARGIN and all(d > 0 for d in per_category) and low > 0
    return "ahead" if ahead else "not_ahead"


def method_report(runs_raw: list[dict], index: dict[str, int], targets: np.ndarray, categories: Sequence[str],
                  b3: np.ndarray, pairs: dict | None, min_runs: int, seed: int) -> dict[str, Any]:
    if not runs_raw:
        return {"runs": 0, "runs_with_axes": 0, "outcome": "untested"}
    runs = [matrix(run["axes"], index) for run in runs_raw]
    draws = [random_draws([int(a.sum()) for a in axes], len(index), seed + i) for i, axes in enumerate(runs)]
    ones = np.ones(len(index))
    method, rand, b3s = scores_under(runs, draws, b3, targets, ones)
    deltas = category_deltas(method, rand, b3s)
    run_delta = method.mean(axis=1) - np.maximum(rand.mean(axis=1), b3s.mean())
    per_category = [float(np.median(deltas[:, i])) for i in range(len(categories))]
    boot = route_bootstrap(runs, draws, b3, targets, len(index))
    low, high = (float(v) for v in np.percentile(boot, [2.5, 97.5]))
    with_axes = sum(bool(len(a)) for a in runs)
    report = {"runs": len(runs), "runs_with_axes": with_axes,
              "median_delta": float(np.median(run_delta)), "median_delta_vs_random_only":
              float(np.median(method.mean(axis=1) - rand.mean(axis=1))),
              "route_bootstrap": [low, high], "replicates": REPLICATES,
              "categories": {c: {"best": float(method[:, i].max()), "median": float(np.median(method[:, i])),
                                 "random_median": float(np.median(rand[:, i])), "median_delta": per_category[i]}
                             for i, c in enumerate(categories)},
              "mean_over_categories": {"best": float(method.mean(axis=1).max()),
                                       "median": float(np.median(method.mean(axis=1))),
                                       "random_median": float(np.median(rand.mean(axis=1)))}}
    sizes = [int(a.sum()) for axes in runs for a in axes]
    report["axis_sizes"] = {"count": len(sizes), "median": float(median(sizes)) if sizes else 0, "max": max(sizes, default=0)}
    report["outcome"] = outcome(report["median_delta"], per_category, low, with_axes, min_runs)
    if pairs is not None:
        for i, c in enumerate(categories):
            hits = [pair_hits(raw["axes"], pairs[c], targets[i], index) for raw in runs_raw]
            report["categories"][c].update({"slice_only_pairs": len(pairs[c]), "pair_hits_best": max(hits),
                                            "pair_hits_median": median(hits)})
    return report


def pair_hits(groups: Sequence[Sequence[str]], pairs: Sequence[tuple[str, str]], target: np.ndarray,
              index: dict[str, int]) -> int:
    """Slice routes of slice-only pairs that sit in an axis with Jaccard >= PAIR_FLOOR. Axes hold failures only, so
    the twin, which did not fail, is never in an axis: C38's twin condition is automatically met here."""
    kept = [set(g) for g in groups if best_scores(matrix([g], index), target[None], np.ones(len(index)))[0] >= PAIR_FLOOR]
    return sum(any(s in g for g in kept) for s, _ in pairs)


def b3_axes(path: Path) -> list[list[str]]:
    directive = json.loads(path.read_text())["directive"]
    return [[e["episode_id"] for e in axis["supporting_episodes"]] for axis in directive["axes"]]


def restrict(groups: Sequence[Sequence[str]], keep: set[str]) -> list[list[str]]:
    return [kept for g in groups if (kept := [m for m in g if m in keep])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--axes", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, nargs="+", required=True)
    parser.add_argument("--routes", type=Path, nargs="+", required=True)
    parser.add_argument("--categories", nargs="+", required=True)
    parser.add_argument("--b3", type=Path, required=True)
    parser.add_argument("--restrict-to", type=Path, help="JSON list of failing route ids to score on (H25: routes with frames)")
    parser.add_argument("--pairs", action="store_true", help="report the pair reading (Fail2Drive)")
    parser.add_argument("--min-runs", type=int, required=True)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"{args.output} exists: each reading happens once")
    manifest, failed = load_pool(args.manifests, args.routes)
    failing = sorted(r for r, f in failed.items() if f)
    if args.restrict_to:
        keep = set(json.loads(args.restrict_to.read_text()))
        failing = [r for r in failing if r in keep]
        failed = {r: f for r, f in failed.items() if not f or r in keep}
    index = {r: i for i, r in enumerate(failing)}
    target_sets = category_sets(manifest, failed, args.categories)
    targets = matrix([sorted(t) for t in target_sets], index)
    b3_groups = b3_axes(args.b3)
    stray = {m for g in b3_groups for m in g} - set(failed)
    if stray:
        raise ValueError(f"B3 groups routes outside this pool: {sorted(stray)[:5]}")
    b3 = matrix(restrict(b3_groups, set(failing)), index)
    methods = json.loads(args.axes.read_text())
    for name, runs in methods.items():
        stray = {m for run in runs for axis in run["axes"] for m in axis} - set(index)
        if stray and not args.restrict_to:
            raise ValueError(f"{name} groups routes that are not failures in this pool: {sorted(stray)[:5]}")
        for run in runs:
            run["axes"] = restrict(run["axes"], set(index))
    pairs = {c: [p for p in slice_only_pairs(manifest, failed, c) if p[0] in index] for c in args.categories} \
        if args.pairs else None
    reports = {name: method_report(runs, index, targets, args.categories, b3, pairs, args.min_runs, SEED + 1000 * k)
               for k, (name, runs) in enumerate(sorted(methods.items()))}
    for name, report in reports.items():
        report["reading"] = SENTENCES[report["outcome"]].format(label=args.label, method=name, pool=args.pool,
                                                                 min_runs=args.min_runs)
    b3_scores = best_scores(b3, targets, np.ones(len(index)))
    record = {"label": args.label, "pool": {"name": args.pool, "failures_scored": len(failing),
                                            "restricted": bool(args.restrict_to)},
              "note": "The best axis is chosen using each category's failing set.",
              "categories": {c: int(t.sum()) for c, t in zip(args.categories, targets)},
              "b3": {c: float(v) for c, v in zip(args.categories, b3_scores)} | {"mean": float(b3_scores.mean())},
              "methods": reports}
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({name: [r["outcome"], round(r.get("median_delta", float("nan")), 3)] for name, r in reports.items()}))


if __name__ == "__main__":
    main()
