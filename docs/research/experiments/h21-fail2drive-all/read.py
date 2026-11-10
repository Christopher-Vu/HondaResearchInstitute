#!/usr/bin/env python3
"""H21's read: pooled over all Fail2Drive pairs, then a screen per category. Dev only, public routes.

    python docs/research/experiments/h21-fail2drive-all/read.py configs/rollout/f2d-all.manifest.json \
        results/savio/f2d-all/routes.jsonl --output docs/research/data/h21_result.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.harness.efficacy import efficacy_from_outcomes, outcomes_by_route, paired  # noqa: E402

MIN_PAIRS, MAX_P, SCREEN_EXCESS = 80, 0.01, 3
SENTENCES = {
    "untested": "H21 is untested: fewer than 80 Fail2Drive pairs drove in both arms.",
    "reproduces": "On our harness, SimLingo fails Fail2Drive's generalization routes more often than their base twins.",
    "not_reproduced": "On our harness, SimLingo's failures on Fail2Drive's generalization routes are not shown to exceed "
                      "those on their base twins.",
}


def pooled_pairs(manifest: list[dict], failed: dict[str, bool]) -> dict:
    arms: dict[str, dict[str, str]] = {}
    for entry in manifest:
        arms.setdefault(entry["base_id"], {})["slice" if entry["role"] == "pilot_slice" else "base"] = entry["id"]
    return {(base, 0): (failed[ids["slice"]], failed[ids["base"]]) for base, ids in arms.items()
            if ids.get("slice") in failed and ids.get("base") in failed}


def outcome(pooled: dict) -> str:
    if pooled["pairs"] < MIN_PAIRS:
        return "untested"
    excess = pooled["slice_only_failed"] > pooled["neighbourhood_only_failed"]
    return "reproduces" if excess and pooled["mcnemar_p"] < MAX_P else "not_reproduced"


def infractions(rows: list[dict], ids: set[str]) -> dict[str, int]:
    total: Counter = Counter()
    for row in rows:
        if str(row["id"]) in ids:
            total.update({key: count for key, count in row.get("infractions", {}).items() if count})
    return dict(total)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("routes", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = [json.loads(line) for line in args.routes.read_text().splitlines() if line.strip()]
    failed = outcomes_by_route(rows)
    pooled = paired(pooled_pairs(manifest, failed))
    result = outcome(pooled)
    gaps = sorted({gap for entry in manifest for gap in entry["practice_gaps"]})
    categories = {}
    for gap in gaps:
        report = efficacy_from_outcomes(manifest, failed, gap)["c23_paired"]
        excess = report["slice_only_failed"] - report["neighbourhood_only_failed"]
        categories[gap] = {**report, "excess": excess, "screen_candidate": excess >= SCREEN_EXCESS}
    by_role = {role: {str(e["id"]) for e in manifest if e["role"] == role} for role in ("pilot_slice", "pilot_neighbourhood")}
    record = {"label": "DEV ONLY: H21, Fail2Drive's public routes on our harness; never enters the sealed key",
              "routes_with_outcome": len(failed), "pooled": pooled, "outcome": result, "reading": SENTENCES[result],
              "categories": categories,
              "screen_candidates": sorted(gap for gap, row in categories.items() if row["screen_candidate"]),
              "infractions": {role: infractions(rows, ids) for role, ids in by_role.items()}}
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({key: record[key] for key in ("routes_with_outcome", "outcome", "reading", "screen_candidates")}))


if __name__ == "__main__":
    main()
