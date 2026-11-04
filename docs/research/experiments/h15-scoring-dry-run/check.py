#!/usr/bin/env python3
"""H15's bug check: does the scoring path reproduce what the repo already measured? DEV DRY RUN, NOT A VERDICT.

    python docs/research/experiments/h15-scoring-dry-run/check.py results/savio/h15 --output results/savio/h15/check.json

Exit 0 when no check finds a bug, 1 otherwise. Each check returns the list of disagreements it found. None of them
reads a method's score as good or bad: that a method misses a gap is not a bug here (protocol, "What is not a bug").
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from discovery.probe_residual import RIDGE_ALPHAS  # noqa: E402
from discovery.residualize import ActionResidual, read_sites, sidecars  # noqa: E402
from harness.schema import ACTION_RESIDUAL, NON_RESIDUALIZED  # noqa: E402

H12_PLAIN = "docs/research/data/h12_layer10_plain.json"
STORED_EFFICACY = {"P4_camera_occlusion": "results/savio/step5-confirm-p4/efficacy.json",
                   "P7_camera_freeze": "results/savio/step5-confirm-p7/efficacy.json",
                   "P19_wide_invading_turn": "results/savio/step5-pilot-p19-main/efficacy.json"}
H12_SHARDS = ("results/savio/step5-background-wave3/shards", "results/savio/step5-confirm-p4/shards",
              "results/savio/step5-confirm-p7/shards", "results/savio/step5-pilot-p19-main/shards")
EXACT = 1e-12
SAE_TOLERANCE = 0.01
MAX_REFIT_R2 = 0.01
LEAK_WORDS = ("predicate", "neighbourhood_of", "camera_fault", "base_scenario_parameters")


def pool_counts(report: dict[str, Any], h12: dict[str, Any]) -> list[str]:
    problems = []
    for name, stored, found in (("rollouts", h12["corpus"]["rollouts"], report["pool"]["rollouts"]),
                                ("failures", h12["corpus"]["failures"], report["pool"]["failures"])):
        if stored != found:
            problems.append(f"{name}: H12 had {stored}, the key path has {found}")
    for gap_id, stored in h12["corpus"]["key"].items():
        if report["gaps"][gap_id]["key_size"] != stored:
            problems.append(f"{gap_id} key: H12 had {stored}, the key path has {report['gaps'][gap_id]['key_size']}")
    return problems


def efficacy_matches_stored(report: dict[str, Any], stored_by_gap: dict[str, dict[str, Any]]) -> list[str]:
    """The pool's efficacy, from a key's predicates, against the pilot's own report: every number must be the same."""
    problems = []
    for gap_id, stored in stored_by_gap.items():
        found = report["gaps"][gap_id]["efficacy"]
        problems += [f"{gap_id} prd_9_1 {name}: stored {value}, found {found.get(name)}"
                     for name, value in stored["prd_9_1"].items() if found.get(name) != value]
        problems += [f"{gap_id} c23 {name}: stored {value}, found {found['c23_paired'].get(name)}"
                     for name, value in stored["c23_paired"].items() if found["c23_paired"].get(name) != value]
    return problems


def h12_row(h12: dict[str, Any], family: str, dictionary: str | None) -> dict[str, Any] | None:
    for label, row in h12["methods"].items():
        if row["family"] == family and (dictionary is None or label.endswith("/" + dictionary)):
            return row
    return None


def jaccards_match_h12(report: dict[str, Any], h12: dict[str, Any]) -> list[str]:
    """Same dictionaries, same shards, same code: non-SAE rows must be exact, SAE rows within GPU rounding."""
    problems = []
    for label, row in report["methods"].items():
        stored = None if row["preprocessing"] != NON_RESIDUALIZED else h12_row(h12, row["family"], row["dictionary"])
        tolerance = SAE_TOLERANCE if row["dictionary"] else EXACT
        for gap_id, found in row["best_jaccard"].items() if stored else ():
            expected = stored["gaps"].get(gap_id, {}).get("best_jaccard")
            if expected is not None and abs(found - expected) > tolerance:
                problems.append(f"{label} {gap_id}: H12 {expected:.4f}, found {found:.4f}")
    return problems


def h12_rows_reached(report: dict[str, Any], h12: dict[str, Any]) -> list[str]:
    """H12's rows that this run never scored, so the comparison above is not silently empty."""
    found = {(row["family"], row["dictionary"]) for row in report["methods"].values()
             if row["preprocessing"] == NON_RESIDUALIZED}
    return [f"H12 row {label} was not scored" for label, row in h12["methods"].items()
            if (row["family"], Path(row["sae"]).name if row["sae"] else None) not in found]


def delta_agrees(report: dict[str, Any]) -> list[str]:
    """Condition 2's point delta against the maxima recomputed from the per-gap table."""
    used = report["condition_2"]
    t2 = [gap_id for gap_id, gap in report["gaps"].items() if gap["tier"] == "T2_interactional" and not gap["decoy"]]

    def mean_over_t2(label: str) -> float:
        return sum(report["methods"][label]["best_jaccard"][gap_id] for gap_id in t2) / len(t2)

    expected = max(map(mean_over_t2, used["activation"])) - max(map(mean_over_t2, used["baselines"]))
    found = used["arithmetic"]["delta"]
    return [] if abs(expected - found) <= EXACT else [f"delta: table gives {expected}, advantage gave {found}"]


def only_non_residualized_validates(report: dict[str, Any]) -> list[str]:
    counted = [label for label, found in report["condition_1"]["t0_recovered_by"].items()
               if report["methods"][label]["preprocessing"] == NON_RESIDUALIZED
               and report["methods"][label]["kind"] == "activation"]
    return [f"valid under {rule} with no non-residualized activation method recovering a control gap"
            for rule, verdict in report["condition_1"]["by_rule"].items() if verdict["valid"] and not counted]


def report_is_labelled_and_clean(text: str) -> list[str]:
    problems = [f"report text holds {word!r}" for word in LEAK_WORDS if word in text]
    return problems + ([] if "DEV DRY RUN" in text else ["report is not labelled as a dev dry run"])


def decoy_path_ran(report: dict[str, Any], decoy: str = "P7_camera_freeze") -> list[str]:
    gap = report["gaps"].get(decoy, {})
    problems = [] if gap.get("decoy") else [f"{decoy} is not a decoy in the branch report"]
    if "c31_decoy" not in gap.get("efficacy", {}):
        problems.append("the branch report has no C31 verdict")
    problems += [f"{label} matched the decoy" for label, row in report["methods"].items()
                 if decoy in {match["gap_id"] for match in row["score"]["matches"]}]
    return problems


def residual_shards_sound(residual_dir: Path, source_dirs: list[Path], model: ActionResidual) -> list[str]:
    """The stored residual equals the model's arithmetic, holds nothing at other layers, and vision no longer predicts
    it on the frames the fit used. A rollout with an outcome that lacks a residual shard is a bug too."""
    problems, residuals, visuals = [], [], []
    for source in sidecars(source_dirs):
        meta = json.loads(source.read_text())
        if meta.get("success") is None:
            continue
        target = residual_dir / source.name
        if not target.is_file():
            problems.append(f"{source.stem} has an outcome and no residual shard")
            continue
        tagged = json.loads(target.read_text())
        if tagged.get("preprocessing") != ACTION_RESIDUAL or tagged["success"] != meta["success"]:
            problems.append(f"{source.stem}: residual sidecar is untagged or its outcome differs")
        queries, visual = read_sites(source, model.layer)
        with np.load(target.with_suffix(".npz")) as archive:
            stored = archive["driving_queries"].astype(np.float64)
        if not np.allclose(stored[:, model.layer], model.residual(queries, visual), atol=1e-3):
            problems.append(f"{source.stem}: stored residual differs from the model's")
        if not np.isnan(stored[:, :model.layer]).all():
            problems.append(f"{source.stem}: a layer other than {model.layer} holds values")
        if meta["success"]:
            residuals.append(stored[:, model.layer])
            visuals.append(visual)
    if residuals:
        features, targets = np.concatenate(visuals), np.concatenate(residuals)
        refit = make_pipeline(StandardScaler(), RidgeCV(alphas=RIDGE_ALPHAS)).fit(features, targets)
        r2 = float(refit.score(features, targets))
        if r2 > MAX_REFIT_R2:
            problems.append(f"vision still predicts the residual on fit frames: R2 {r2:.4f} above {MAX_REFIT_R2}")
    return problems


def outcomes_agree(report_routes: list[Path], source_dirs: list[Path]) -> list[str]:
    """routes.jsonl feeds scoring and the sidecars feed the methods, so they must tell the same story."""
    rows = [json.loads(line) for path in report_routes for line in path.read_text().splitlines() if line.strip()]
    scored = {str(row["id"]): not row["success"] for row in rows if row.get("success") is not None}
    sides = {str(meta["route_id"]): not meta["success"]
             for path in sidecars(source_dirs) if (meta := json.loads(path.read_text()))["success"] is not None}
    differing = sorted(route for route in scored.keys() | sides.keys() if scored.get(route) != sides.get(route))
    return [f"{len(differing)} routes differ between routes.jsonl and sidecars, such as {differing[:5]}"] if differing else []


def run_checks(out: Path, repo: Path = REPO) -> dict[str, list[str]]:
    texts = {name: (out / f"report-{name}.json").read_text() for name in ("as-labelled", "all-dictionaries", "branch")}
    labelled, branch = json.loads(texts["as-labelled"]), json.loads(texts["branch"])
    h12 = json.loads((repo / H12_PLAIN).read_text())
    stored = {gap_id: json.loads((repo / path).read_text()) for gap_id, path in STORED_EFFICACY.items()}
    sources = [repo / path for path in H12_SHARDS]
    routes = [path.parent / "routes.jsonl" for path in sources]
    return {
        "pool_and_key_sizes_match_h12": pool_counts(labelled, h12),
        "efficacy_matches_stored_pilots": efficacy_matches_stored(labelled, stored),
        "jaccards_match_h12": jaccards_match_h12(labelled, h12),
        "every_h12_row_was_scored": h12_rows_reached(labelled, h12),
        "delta_agrees_with_the_table": [problem for text in texts.values() for problem in delta_agrees(json.loads(text))],
        "only_non_residualized_validates": only_non_residualized_validates(labelled),
        "reports_labelled_and_clean": [problem for text in texts.values() for problem in report_is_labelled_and_clean(text)],
        "decoy_path_ran": decoy_path_ran(branch),
        "residual_shards_sound": residual_shards_sound(out / "residual-shards", sources,
                                                       ActionResidual.load(out / "action_residual.npz")),
        "outcomes_agree": outcomes_agree(routes, sources),
        "no_real_commitment_written": [] if not (repo / "src/harness/KEY_COMMITMENT.txt").exists()
        else ["src/harness/KEY_COMMITMENT.txt exists"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path, help="the experiment's output directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    found = run_checks(args.out)
    bugs = {name: problems for name, problems in found.items() if problems}
    args.output.write_text(json.dumps({"label": "DEV DRY RUN, NOT A VERDICT", "bugs_found": bool(bugs),
                                       "checks": found}, indent=1) + "\n")
    for name, problems in found.items():
        print(f"{'BUG' if problems else 'ok '} {name}: {'; '.join(problems[:3])}")
    raise SystemExit(1 if bugs else 0)


if __name__ == "__main__":
    main()
