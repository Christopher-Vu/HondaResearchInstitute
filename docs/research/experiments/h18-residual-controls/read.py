#!/usr/bin/env python3
"""H18's read: each control's M1 raw median on P19 against H15's plain and residual medians. Dev only, not a verdict.

    python docs/research/experiments/h18-residual-controls/read.py results/savio/h18 --output results/savio/h18/result.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

H15 = Path(__file__).resolve().parents[3] / "research" / "data" / "h15_dry_run.json"
CONTROLS = ("shuffle", "top-variance")
GAPS = ("P19_wide_invading_turn", "P4_camera_occlusion", "P7_camera_freeze")
FAMILIES = ("M1_raw", "M1_capped", "B7_pool")
DICTIONARIES, MIN_COUNTED, SEED, DRAWS = 18, 12, 18, 5000
SENTENCES = {
    "untested": "H18 is untested: a control did not run in full.",
    "needs_vision": "On P19, neither control reaches halfway to the residualization gain, so the gain needs the visual fit.",
    "not_vision": "A fit on shuffled vision reaches halfway to the residualization gain on P19, so the gain does not need "
                  "the visual fit.",
    "not_shown_specific": "Removing as much variance without vision reaches halfway to the gain on P19, so H18 cannot "
                          "show that the gain is specific to vision.",
}


def residual_scores(report: dict, family: str, gap: str) -> list[float]:
    return sorted(method["best_jaccard"][gap] for method in report["methods"].values()
                  if method["family"] == family and method["preprocessing"] == "action_residual" and method["counts"])


def summary(scores: list[float]) -> dict:
    return {"best": max(scores), "median": float(np.median(scores)), "at_or_above_0_5": sum(s >= 0.5 for s in scores),
            "dictionaries": len(scores)}


def median_difference_interval(control: list[float], real_median: float) -> list[float]:
    rng = np.random.default_rng(SEED)
    draws = rng.choice(np.array(control), size=(DRAWS, len(control)), replace=True)
    differences = np.median(draws, axis=1) - real_median
    return [float(np.percentile(differences, 2.5)), float(np.percentile(differences, 97.5))]


def outcome(medians: dict[str, float], halfway: float, complete: bool) -> str:
    if not complete:
        return "untested"
    if medians["shuffle"] >= halfway:
        return "not_vision"
    return "not_shown_specific" if medians["top-variance"] >= halfway else "needs_vision"


def control_complete(run: Path, report: dict) -> bool:
    """All 18 dictionaries trained, and at least 12 count (explained variance of 0.8 or more, as `scoring_run` decides)."""
    trained = len(list(run.glob("sae/L10_*/metrics.json")))
    return trained == DICTIONARIES and len(residual_scores(report, "M1_raw", GAPS[0])) >= MIN_COUNTED


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    h15 = json.loads(H15.read_text())["spread"]
    plain, real = h15["M1_raw@non_residualized"]["P19_wide_invading_turn"]["median"], h15["M1_raw@action_residual"]["P19_wide_invading_turn"]["median"]
    halfway = plain + (real - plain) / 2
    controls, medians, complete = {}, {}, True
    for control in CONTROLS:
        run = args.out / control
        report_path = run / "report-all-dictionaries.json"
        report = json.loads(report_path.read_text()) if report_path.is_file() else None
        if report is None or not control_complete(run, report):
            complete = False
            continue
        primary = residual_scores(report, "M1_raw", GAPS[0])
        medians[control] = float(np.median(primary))
        controls[control] = {
            "fit": json.loads((run / "fit.json").read_text()),
            "scores": {family: {gap: summary(residual_scores(report, family, gap)) for gap in GAPS} for family in FAMILIES},
            "median_minus_real_interval": median_difference_interval(primary, real),
        }
    result = outcome(medians, halfway, complete)
    record = {"label": "DEV DRY RUN, NOT A VERDICT: H18 residualization controls on H12's pool",
              "note": "The best axis is chosen using the key.", "plain_median": plain, "real_residual_median": real,
              "halfway": halfway, "control_medians": medians, "outcome": result, "reading": SENTENCES[result],
              "controls": controls}
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({key: record[key] for key in ("control_medians", "halfway", "outcome", "reading")}, indent=1))


if __name__ == "__main__":
    main()
