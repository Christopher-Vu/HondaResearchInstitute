"""Efficacy of a practice gap from a pilot's manifest and scored routes, by PRD 9.1's rule and by CONFLICTS.md C23's.

    python -m src.harness.efficacy MANIFEST.json ROUTES.jsonl --gap GAP_ID [--output OUT.json]
    python -m src.harness.efficacy --screen REPORT.json --gaps gaps/practice/practice_v2.yaml   # exit 0 if it passes

PRD 9.1, the rule in force: slice against neighbourhood as unrelated groups, two-sided Fisher exact, through
harness.schema.Gap.passes_efficacy. C23, proposed: the base route is the unit. Each base route with an outcome on
both its slice and its neighbourhood route is a pair; McNemar's exact test (two-sided binomial on the discordant
pairs) replaces Fisher, with the same uplift and ratio thresholds, at least 60 pairs from at least 30 base routes.
Routes without an outcome are left out of both and counted. When a base route carries several pairs, the n-th slice
route listed for that base pairs with its n-th neighbourhood route, so a lost route leaves its own twin unpaired and
does not shift the others.

C31's decoy rule is `decoy_verdict`. `pool_efficacy` computes all of it on the test pool from a sealed key's
predicates, because that pool's manifest carries no roles (docs/steps/08-seal-generate-score.md).

A screen (Step 5's 10-pair first stage) passes its gap's `screen_rule` when, among pairs, slice-only failures exceed
neighbourhood-only failures by at least `min_excess_slice_only_failures`; `--screen` exits 0 then, 3 otherwise, and 4 when the report holds no pair or fewer than the rule's `min_pairs`, which is no result.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import binomtest, fisher_exact

from .predicates import matches
from .schema import Gap

MIN_UPLIFT_PP = 20.0
MIN_RATIO = 2.0
MAX_P = 0.01
MIN_PAIRS = 60
MIN_BASE_ROUTES = 30
DECOY_MAX_ABS_UPLIFT_PP = 10.0
DECOY_MIN_P = 0.2
DECOY_OLD_BAND_PP = 5.0


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


def outcome_pairs(manifest: list[dict[str, Any]], failed: dict[str, bool], gap_id: str
                  ) -> dict[tuple[str, int], tuple[bool, bool]]:
    """(base route, n-th pair on it) to (slice failed, neighbourhood failed), for pairs with an outcome on both."""
    listed: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"slice": [], "neighbourhood": []})
    for entry in manifest:
        in_slice, in_nbhd = roles(entry, gap_id)
        if in_slice or in_nbhd:
            listed[entry["base_id"]]["slice" if in_slice else "neighbourhood"].append(entry["id"])
    return {(base, n): (failed[slice_id], failed[nbhd_id]) for base, arms in listed.items()
            for n, (slice_id, nbhd_id) in enumerate(zip(arms["slice"], arms["neighbourhood"]))
            if slice_id in failed and nbhd_id in failed}


def paired(pairs: dict[tuple[str, int], tuple[bool, bool]]) -> dict[str, Any]:
    n, base_routes = len(pairs), len({base for base, _ in pairs})
    slice_only = sum(slice_failed and not nbhd_failed for slice_failed, nbhd_failed in pairs.values())
    nbhd_only = sum(nbhd_failed and not slice_failed for slice_failed, nbhd_failed in pairs.values())
    counts = {"pairs": n, "base_routes": base_routes, "slice_only_failed": slice_only,
              "neighbourhood_only_failed": nbhd_only}
    if not n:
        return {**counts, "passes": False}
    stats = {**counts, **rates(sum(pair[0] for pair in pairs.values()), n, sum(pair[1] for pair in pairs.values()), n),
             "mcnemar_p": float(binomtest(slice_only, slice_only + nbhd_only, 0.5).pvalue) if slice_only + nbhd_only
             else 1.0}
    passes = bool(stats["uplift_pp"] >= MIN_UPLIFT_PP and stats["ratio"] >= MIN_RATIO and stats["mcnemar_p"] < MAX_P
                  and n >= MIN_PAIRS and base_routes >= MIN_BASE_ROUTES)
    return {**stats, "passes": passes}


def decoy_verdict(paired_report: dict[str, Any]) -> dict[str, Any]:
    """C31's rule on a decoy's paired pilot, with PRD 9.1's old 5-point band beside it for the report (C31's reversal)."""
    if not paired_report["pairs"]:
        return {"passes": False, "within_old_band": False}
    close = abs(paired_report["uplift_pp"])
    return {"passes": bool(paired_report["pairs"] >= MIN_PAIRS and close <= DECOY_MAX_ABS_UPLIFT_PP
                           and paired_report["mcnemar_p"] > DECOY_MIN_P),
            "within_old_band": bool(close <= DECOY_OLD_BAND_PP)}


def efficacy_from_outcomes(manifest: list[dict[str, Any]], failed: dict[str, bool], gap_id: str) -> dict[str, Any]:
    listed = [entry for entry in manifest if any(roles(entry, gap_id))]
    return {"gap_id": gap_id, "routes_listed": len(listed),
            "routes_without_outcome": sorted(entry["id"] for entry in listed if entry["id"] not in failed),
            "prd_9_1": unpaired(manifest, failed, gap_id), "c23_paired": paired(outcome_pairs(manifest, failed, gap_id))}


def efficacy(manifest: list[dict[str, Any]], rows: list[dict[str, Any]], gap_id: str) -> dict[str, Any]:
    return efficacy_from_outcomes(manifest, outcomes_by_route(rows), gap_id)


def role_labels(spec: dict[str, Any], manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The manifest entries a key's gap touches, with the roles that manifest itself does not carry."""
    gap_id, labelled = spec["gap_id"], []
    for entry in manifest:
        in_slice, in_nbhd = matches(spec["predicate"], entry), matches(spec["neighbourhood_predicate"], entry)
        if in_slice and in_nbhd:
            raise ValueError(f"{gap_id}: route {entry['id']} matches both its slice and its neighbourhood")
        if in_slice or in_nbhd:
            labelled.append({"id": str(entry["id"]), "base_id": str(entry["base_id"]),
                             "practice_gaps": [gap_id] if in_slice else [],
                             "neighbourhood_of": [gap_id] if in_nbhd else []})
    return labelled


def pool_efficacy(spec: dict[str, Any], manifest: list[dict[str, Any]], failed: dict[str, bool]) -> dict[str, Any]:
    """One key gap's efficacy on the pool, in the shape harness.schema.Gap reads: PRD 9.1's stats flat, C23's and C31's
    nested. An arm with no outcome has no rates or p value, so the defaults make it read as not re-confirming."""
    report = efficacy_from_outcomes(role_labels(spec, manifest), failed, spec["gap_id"])
    return {"fail_rate_in": 0.0, "fail_rate_neighbourhood": 0.0, "fisher_p": 1.0, **report["prd_9_1"],
            "c23_paired": report["c23_paired"], "c31_decoy": decoy_verdict(report["c23_paired"]),
            "routes_listed": report["routes_listed"], "routes_without_outcome": report["routes_without_outcome"]}


NO_RESULT_EXIT = 4


def screen_passes(report: dict[str, Any], rule: dict[str, Any]) -> bool:
    paired_report = report["c23_paired"]
    excess = paired_report["slice_only_failed"] - paired_report["neighbourhood_only_failed"]
    return excess >= rule["min_excess_slice_only_failures"]


def screen_verdict(report_path: Path, gaps_path: Path) -> int:
    import yaml
    report = json.loads(report_path.read_text())
    gaps = {gap["gap_id"]: gap for gap in yaml.safe_load(gaps_path.read_text())["gaps"]}
    rule = gaps[report["gap_id"]]["screen_rule"]
    passed = screen_passes(report, rule)
    paired_report = report["c23_paired"]
    has_result = paired_report["pairs"] >= max(1, rule.get("min_pairs", 1))
    verdict = f"passes: {passed}" if has_result else "no result"
    print(f"{report['gap_id']} screen: {paired_report['slice_only_failed']} slice-only against "
          f"{paired_report['neighbourhood_only_failed']} neighbourhood-only failures on {paired_report['pairs']} pairs, "
          f"{len(report['routes_without_outcome'])} routes without an outcome; {verdict}")
    if not has_result:
        return NO_RESULT_EXIT
    return 0 if passed else 3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("routes", type=Path, nargs="?", help="routes.jsonl written by score_routes.py")
    parser.add_argument("--gap")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--screen", type=Path, help="a screen's efficacy report: judge it by its gap's screen_rule")
    parser.add_argument("--gaps", type=Path, help="the practice-gap file holding that screen_rule")
    args = parser.parse_args()
    if args.screen:
        raise SystemExit(screen_verdict(args.screen, args.gaps))
    if not (args.manifest and args.routes and args.gap):
        parser.error("manifest, routes and --gap are required unless --screen is given")
    rows = [json.loads(line) for line in args.routes.read_text().splitlines() if line.strip()]
    report = efficacy(json.loads(args.manifest.read_text()), rows, args.gap)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
