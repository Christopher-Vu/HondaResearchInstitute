#!/usr/bin/env python3
"""H22's scorer: C38's frozen-method reading on Fail2Drive's three screened categories. Public routes, not blind.

    PYTHONPATH=src python docs/research/experiments/h22-f2d-frozen-eval/score.py --directives DIR \
        --shared PLAIN_DIR --manifest configs/rollout/f2d-all.manifest.json --routes routes.jsonl \
        --variant plain --output report.json

A category's failing set is its generalization routes that failed, read from the public manifest and the outcomes;
no key file exists because nothing here is sealed. B1, B2 and B3 read no activations, so every variant takes them
from `--shared` (the plain directives). B2 is the ceiling (C38 item 4) and never enters the comparison.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Sequence

import numpy as np

from harness.scoring import jaccard
from harness.scoring_run import Emitted, load_emitted, load_pool, require_scored_members

CATEGORIES = ("F2D_CustomObstacles", "F2D_PedestriansOnRoad", "F2D_Wall")
ACTIVATION = ("M1_raw", "M1_capped", "M2_probe_residual")
RIVALS = ("B1_random", "B3_behavioral", "B7_pool")
SHARED = ("B1_random", "B2_taxonomy", "B3_behavioral")
PRIMARY = "M1_raw"
PAIR_FLOOR, MARGIN, MIN_COUNTED = 0.3, 0.15, 12
REPLICATES, SEED = 10_000, 20261016
LABEL = "DEV ONLY, NOT BLIND: H22, frozen methods on Fail2Drive's public categories (C38)"
SENTENCES = {
    "untested": "H22 is untested: the primary variant did not produce 12 counted dictionaries for every method.",
    "ahead": "On Fail2Drive's three screened categories, activation methods recover the failing routes better than "
             "the activation-free and pooled baselines, by a median of at least 0.15 Jaccard across dictionaries.",
    "not_ahead": "On Fail2Drive's three screened categories, activation methods are not shown to recover the failing "
                 "routes better than the activation-free and pooled baselines.",
}


def category_sets(manifest: Sequence[dict], failed: dict[str, bool]) -> dict[str, set[str]]:
    return {category: {str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and category in e["practice_gaps"]
                       and failed.get(str(e["id"]))} for category in CATEGORIES}


def slice_only_pairs(manifest: Sequence[dict], failed: dict[str, bool]) -> dict[str, list[tuple[str, str]]]:
    twin = {e["base_id"]: str(e["id"]) for e in manifest if e["role"] != "pilot_slice"}
    pairs: dict[str, list[tuple[str, str]]] = {category: [] for category in CATEGORIES}
    for entry in manifest:
        slice_id, twin_id = str(entry["id"]), twin.get(entry["base_id"])
        if entry["role"] != "pilot_slice" or twin_id not in failed or slice_id not in failed:
            continue
        for category in set(entry["practice_gaps"]) & set(CATEGORIES):
            if failed[slice_id] and not failed[twin_id]:
                pairs[category].append((slice_id, twin_id))
    return pairs


def best_by_category(item: Emitted, failing: dict[str, set[str]]) -> np.ndarray:
    return np.array([max((jaccard(axis.rollouts, failing[c]) for axis in item.directive.axes), default=0.0)
                     for c in CATEGORIES])


def pair_hits(item: Emitted, pairs: list[tuple[str, str]], failing: set[str]) -> int:
    """C38's guarded pair reading: an emitted axis holds the slice route, not its twin, and has Jaccard >= 0.3."""
    axes = [axis.rollouts for axis in item.directive.axes if jaccard(axis.rollouts, failing) >= PAIR_FLOOR]
    return sum(any(s in axis and t not in axis for axis in axes) for s, t in pairs)


def dictionary_deltas(rows: dict[str, np.ndarray], families: dict[str, tuple[str, str | None]],
                      dictionaries: Sequence[str], weight: np.ndarray) -> list[float]:
    """Per dictionary: best activation method minus best rival, each a weighted mean over categories, both re-picked."""
    shared = {name for name, (_family, dictionary) in families.items() if dictionary is None}
    out = []
    for d in dictionaries:
        members = shared | {name for name, (_f, dictionary) in families.items() if dictionary == d}
        score = {name: float(rows[name] @ weight) / weight.sum() for name in members}
        act = [score[n] for n in members if families[n][0] in ACTIVATION]
        riv = [score[n] for n in members if families[n][0] in RIVALS]
        out.append(max(act) - max(riv))
    return out


def comparison(rows: dict[str, np.ndarray], families: dict[str, tuple[str, str | None]],
               dictionaries: Sequence[str]) -> dict[str, Any]:
    point = dictionary_deltas(rows, families, dictionaries, np.ones(len(CATEGORIES)))
    rng = np.random.default_rng(SEED)
    medians = np.empty(REPLICATES)
    for i in range(REPLICATES):
        weight = np.bincount(rng.integers(0, len(CATEGORIES), len(CATEGORIES)), minlength=len(CATEGORIES)).astype(float)
        medians[i] = median(dictionary_deltas(rows, families, dictionaries, weight))
    low, high = (float(v) for v in np.percentile(medians, [2.5, 97.5]))
    return {"median_delta": median(point), "best_delta": max(point), "interval": [low, high],
            "dictionaries": len(dictionaries), "replicates": REPLICATES, "unit": "category"}


def outcome(counted: dict[str, int], compared: dict[str, Any] | None) -> str:
    if compared is None or min(counted.get(f, 0) for f in ("M1_raw", "M1_capped", "B7_pool")) < MIN_COUNTED:
        return "untested"
    return "ahead" if compared["median_delta"] >= MARGIN and compared["interval"][0] > 0 else "not_ahead"


def family_table(emitted: Sequence[Emitted], rows: dict[str, np.ndarray], hits: dict[str, dict[str, int]]) -> dict:
    grouped: dict[str, list[Emitted]] = defaultdict(list)
    for item in emitted:
        if item.counts:
            grouped[item.family].append(item)
    table = {}
    for family, items in sorted(grouped.items()):
        per = {}
        for i, category in enumerate(CATEGORIES):
            values = [float(rows[item.label][i]) for item in items]
            pair = [hits[item.label][category] for item in items]
            per[category] = {"best": max(values), "median": median(values), "pair_hits_best": max(pair),
                             "pair_hits_median": median(pair)}
        table[family] = {"directives": len(items), "categories": per,
                         "mean_over_categories": {"best": max(float(rows[i.label].mean()) for i in items),
                                                  "median": median(float(rows[i.label].mean()) for i in items)}}
    return table


def report(emitted: list[Emitted], manifest: list[dict], failed: dict[str, bool], variant: str) -> dict[str, Any]:
    require_scored_members(emitted, failed)
    failing = category_sets(manifest, failed)
    pairs = slice_only_pairs(manifest, failed)
    rows = {item.label: best_by_category(item, failing) for item in emitted}
    hits = {item.label: {c: pair_hits(item, pairs[c], failing[c]) for c in CATEGORIES} for item in emitted}
    used = [item for item in emitted if item.counts and item.family in ACTIVATION + RIVALS]
    families = {item.label: (item.family, item.dictionary) for item in used}
    dictionaries = sorted({item.dictionary for item in used if item.dictionary is not None})
    counted = {f: sum(item.family == f for item in used) for f in ACTIVATION + RIVALS}
    compared = comparison({k: rows[k] for k in families}, families, dictionaries) if dictionaries else None
    result = outcome(counted, compared) if variant == "plain" else "secondary"
    failures = sum(failed.values())
    return {"label": f"{LABEL} ({variant})", "variant": variant, "outcome": result,
            "reading": SENTENCES.get(result, "Secondary variant, reported beside the primary with no bearing on it."),
            "note": "The best axis is chosen using the category's failing set; the categories were chosen on these pairs.",
            "pool": {"rollouts": len(failed), "failures": failures},
            "categories": {c: {"failing": len(failing[c]), "slice_only_pairs": len(pairs[c]),
                               "catch_all_jaccard": len(failing[c]) / max(1, failures)} for c in CATEGORIES},
            "counted": counted, "comparison": compared, "families": family_table(emitted, rows, hits)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--directives", type=Path, required=True)
    parser.add_argument("--shared", type=Path, required=True, help="plain directives; only B1, B2 and B3 are taken")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--variant", choices=("plain", "centre", "vision"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"{args.output} exists: each variant is scored once")
    own = [item for item in load_emitted([args.directives]) if item.family not in SHARED]
    shared = [item for item in load_emitted([args.shared]) if item.family in SHARED]
    manifest, failed = load_pool([args.manifest], [args.routes])
    record = report(own + shared, manifest, failed, args.variant)
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("label", "outcome", "comparison", "counted")}))


if __name__ == "__main__":
    main()
