"""Efficacy of a practice gap from a pilot's manifest and scored routes, by PRD 9.1's rule and by CONFLICTS.md C23's.

    python -m src.harness.efficacy MANIFEST.json ROUTES.jsonl --gap GAP_ID [--output OUT.json]

PRD 9.1, the rule in force: slice against neighbourhood as unrelated groups, two-sided Fisher exact, through
harness.schema.Gap.passes_efficacy. C23, proposed: the base route is the unit. Each base route with an outcome on
both its slice and its neighbourhood route is a pair; McNemar's exact test (two-sided binomial on the discordant
pairs) replaces Fisher, with the same uplift and ratio thresholds, at least 60 pairs from at least 30 base routes.
Routes without an outcome are left out of both and counted.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import binomtest, fisher_exact

from src.harness.schema import Gap

MIN_UPLIFT_PP = 20.0
MIN_RATIO = 2.0
MAX_P = 0.01
MIN_PAIRS = 60
MIN_BASE_ROUTES = 30


def outcomes_by_route(rows: list[dict[str, Any]]) -> dict[str, bool]:
    """Route id to failed, for routes the scorer gave an outcome."""
    return {str(row["id"]): not row["success"] for row in rows if row.get("success") is not None}


def roles(entry: dict[str, Any], gap_id: str) -> tuple[bool, bool]:
    return gap_id in entry["practice_gaps"], gap_id in entry.get("neighbourhood_of", [])


def rates(failures_in: int, n_in: int, failures_nbhd: int, n_nbhd: int) -> dict[str, Any]:
    p_in, p_nbhd = failures_in / n_in, failures_nbhd / n_nbhd
    return {"fail_rate_in": p_in, "fail_rate_neighbourhood": p_nbhd, "uplift_pp": 100.0 * (p_in - p_nbhd),
            "ratio": p_in / p_nbhd if p_nbhd else float("inf")}


def unpaired(manifest: list[dict[str, Any]], failed: dict[str, bool], gap_id: str) -> dict[str, Any]:
    inside = [failed[entry["id"]] for entry in manifest if entry["id"] in failed and roles(entry, gap_id)[0]]
    nearby = [failed[entry["id"]] for entry in manifest if entry["id"] in failed and roles(entry, gap_id)[1]]
    counts = {"n_in": len(inside), "failures_in": sum(inside),
              "n_neighbourhood": len(nearby), "failures_neighbourhood": sum(nearby)}
    if not inside or not nearby:
        return {**counts, "passes": False}
    table = [[sum(inside), len(inside) - sum(inside)], [sum(nearby), len(nearby) - sum(nearby)]]
    stats = {**counts, **rates(sum(inside), len(inside), sum(nearby), len(nearby)),
             "fisher_p": float(fisher_exact(table)[1])}
    return {**stats, "passes": bool(Gap(gap_id, "T0_control", set(), efficacy=stats).passes_efficacy())}


def outcome_pairs(manifest: list[dict[str, Any]], failed: dict[str, bool], gap_id: str) -> dict[str, tuple[bool, bool]]:
    """Base route to (slice failed, neighbourhood failed), for bases with an outcome on both."""
    by_base: dict[str, dict[str, bool]] = defaultdict(dict)
    for entry in manifest:
        in_slice, in_nbhd = roles(entry, gap_id)
        if entry["id"] in failed and (in_slice or in_nbhd):
            by_base[entry["base_id"]]["slice" if in_slice else "neighbourhood"] = failed[entry["id"]]
    return {base: (pair["slice"], pair["neighbourhood"]) for base, pair in by_base.items() if len(pair) == 2}


def paired(pairs: dict[str, tuple[bool, bool]]) -> dict[str, Any]:
    n = len(pairs)
    slice_only = sum(slice_failed and not nbhd_failed for slice_failed, nbhd_failed in pairs.values())
    nbhd_only = sum(nbhd_failed and not slice_failed for slice_failed, nbhd_failed in pairs.values())
    counts = {"pairs": n, "base_routes": n, "slice_only_failed": slice_only, "neighbourhood_only_failed": nbhd_only}
    if not n:
        return {**counts, "passes": False}
    stats = {**counts, **rates(sum(pair[0] for pair in pairs.values()), n, sum(pair[1] for pair in pairs.values()), n),
             "mcnemar_p": float(binomtest(slice_only, slice_only + nbhd_only, 0.5).pvalue) if slice_only + nbhd_only
             else 1.0}
    passes = bool(stats["uplift_pp"] >= MIN_UPLIFT_PP and stats["ratio"] >= MIN_RATIO and stats["mcnemar_p"] < MAX_P
                  and n >= MIN_PAIRS and n >= MIN_BASE_ROUTES)
    return {**stats, "passes": passes}


def efficacy(manifest: list[dict[str, Any]], rows: list[dict[str, Any]], gap_id: str) -> dict[str, Any]:
    failed = outcomes_by_route(rows)
    listed = [entry for entry in manifest if any(roles(entry, gap_id))]
    return {"gap_id": gap_id, "routes_listed": len(listed),
            "routes_without_outcome": sorted(entry["id"] for entry in listed if entry["id"] not in failed),
            "prd_9_1": unpaired(manifest, failed, gap_id), "c23_paired": paired(outcome_pairs(manifest, failed, gap_id))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("routes", type=Path, help="routes.jsonl written by score_routes.py")
    parser.add_argument("--gap", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.routes.read_text().splitlines() if line.strip()]
    report = efficacy(json.loads(args.manifest.read_text()), rows, args.gap)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
