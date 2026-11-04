"""H16: read Step 6's stop condition, per gap class, from score.py's plain outputs. Refuses a post hoc file.

    PYTHONPATH=src python docs/research/experiments/h16-b7-rollout-free/read_rule.py PLAIN.json [...] --output OUT.json

Also refuses when the rule differs from its lock (job_guard.py) or when M1 and B7-pool no longer reproduce H12's stored
numbers. The output carries each arm's label, the unsettled decisions and the lock commit, so they travel with the result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from job_guard import REPO_ROOT, locked_commit

from baselines.b7_variant_a import UNTESTED, GapEvidence, stop_condition

REPRODUCTION_TOLERANCE = 0.01
ARM_LABELS = {
    "A": "stated before its data: the rule was written before any variant A number existed",
    "pool": ("post hoc: the rule's author had seen the B7-pool table, so its class split, all-gaps test, partial and "
             "no_recovery readings, median margin and B7-only Claim B are choices made after activations were opened. "
             "Stored H12 numbers already read T2 `fires` before any H16 job, so that reading is not an H16 finding"),
}
UNSETTLED = (
    "C34's median clause: pending Chris's review",
    "P19's T2 label: Chris's decision pending; P19 also fails Step 5's single-factor condition",
    "the class split and the partial reading: for Chris to confirm",
)


def read_rule(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if any("evidence" not in report for report in reports):
        raise ValueError("a post hoc report cannot be read by the stop rule")
    reading: dict[str, Any] = {}
    for variant in ("A", "pool"):
        if not all(report["tested"][variant] for report in reports):
            reading[variant] = UNTESTED
            continue
        evidence = {gap_id: GapEvidence(**item) for report in reports for gap_id, item in report["evidence"][variant].items()}
        reading[variant] = stop_condition(evidence)
    return reading


def reproduction_rows(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """M1 and B7-pool against H12's stored numbers. The pool reading means nothing if the pipeline has moved."""
    rows = [report["reproduces_stored"] for report in reports if "reproduces_stored" in report]
    if not rows or not all(row["compared"] for row in rows):
        raise ValueError("no stored number was compared: the pipeline's reproduction is unknown")
    worst = max(row["worst_difference"] for row in rows)
    if worst > REPRODUCTION_TOLERANCE:
        raise ValueError(f"stored numbers do not reproduce: worst difference {worst}")
    return rows


def why_untested(reports: list[dict[str, Any]]) -> dict[str, Any]:
    return {"training_routes": [report["training_routes"] for report in reports],
            "training_explained_variance": {row["run"]: row["training_explained_variance"]
                                            for report in reports for row in report["dictionaries"]}}


def arm(variant: str, reading: Any, reports: list[dict[str, Any]]) -> dict[str, Any]:
    entry = {"label": ARM_LABELS[variant], "reading": reading}
    return {**entry, "why_untested": why_untested(reports)} if reading == UNTESTED else entry


def stop_condition_file(reports: list[dict[str, Any]], rule_commit: str) -> dict[str, Any]:
    rows = reproduction_rows(reports)
    readings = read_rule(reports)
    return {"rule_commit": rule_commit, "unsettled": list(UNSETTLED), "reproduces_stored": rows,
            "arms": {variant: arm(variant, reading, reports) for variant, reading in readings.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(path.read_text()) for path in args.reports]
    reading = stop_condition_file(reports, locked_commit(REPO_ROOT))
    args.output.write_text(json.dumps(reading, indent=2) + "\n")
    print(json.dumps(reading, indent=2))


if __name__ == "__main__":
    main()
