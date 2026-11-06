#!/usr/bin/env python3
"""H19: is M2's zero on real pools its clustering settings or its honest answer? DEV DRY RUN, NOT A VERDICT.

    PYTHONPATH=src python docs/research/experiments/h19-m2-settings/sweep.py --output results/savio/h19/result.json

Runs `probe_residual_directive` on H12's pool at layer 10 under a fixed grid of HDBSCAN settings, scores each directive
against H15's throwaway public key, and repeats the grid with a planted group: 25 failures outside every key gap whose
lead_distance error is shifted by 2.3 standard deviations on their window frames. Protocol: protocol.md beside this file.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from discovery.probe_residual import (  # noqa: E402
    ProbeResidualConfig, fit_probes, load_shard, probe_residual_directive, window_rows,
)
from harness.bootstrap import mean_best_jaccard  # noqa: E402
from harness.scoring import jaccard  # noqa: E402
from harness.scoring_run import load_pool  # noqa: E402
from harness.seal import gaps_from_key, load_key  # noqa: E402

POOL = ("step5-background-wave3", "step5-confirm-p4", "step5-confirm-p7", "step5-pilot-p19-main")
KEY = "results/savio/h15/throwaway/as-labelled/key.json"
LAYER, SITE = 10, "driving_queries"
GRID = {"min_cluster_size": (20, 60), "min_samples": (None, 5, 10, 30), "allow_single_cluster": (False, True)}
PLANTED, PLANT_STATE, PLANT_SHIFT, PLANT_SEED = 25, "lead_distance", 2.3, 19
# Amendment of 2026-11-06: lead_distance is NaN without a lead vehicle, and a NaN frame's error is 0, so a planted failure
# must know the state on at least this share of its window frames for the shift to reach it.
PLANT_MIN_KNOWN = 0.6
DEFAULTS = {"min_cluster_size": 60, "min_samples": None, "allow_single_cluster": False}


def settings_grid() -> list[dict]:
    return [dict(zip(GRID, values)) for values in itertools.product(*GRID.values())]


def load_rollouts() -> list:
    sidecars = sorted(path for name in POOL for path in (REPO / "results/savio" / name / "shards").glob("*.json"))
    return [rollout for path in sidecars if (rollout := load_shard(path, SITE, LAYER)) is not None]


def known_share(rollout) -> float:
    values = rollout.states.get(PLANT_STATE)
    if values is None:
        return 0.0
    return float(np.mean(~np.isnan(values[window_rows(rollout, ProbeResidualConfig())])))


def plant(rollouts: list, gap_members: set[str]) -> tuple[list, set[str]]:
    """Shift the true state on the window frames of 25 seeded failures outside every gap, so their decode error moves
    by PLANT_SHIFT standard deviations of that state on success frames."""
    sigma = fit_probes([r for r in rollouts if not r.failed])[PLANT_STATE].sigma
    candidates = sorted(r.rollout_id for r in rollouts if r.failed and r.rollout_id not in gap_members
                        and known_share(r) >= PLANT_MIN_KNOWN)
    size = min(PLANTED, len(candidates))
    chosen = set(np.random.default_rng(PLANT_SEED).choice(candidates, size=size, replace=False).tolist())
    planted = []
    for rollout in rollouts:
        if rollout.rollout_id in chosen:
            rollout = copy.deepcopy(rollout)
            rows = window_rows(rollout, ProbeResidualConfig())
            rollout.states[PLANT_STATE][rows] -= PLANT_SHIFT * sigma
        planted.append(rollout)
    return planted, chosen


def run(rollouts: list, settings: dict, gaps: list, planted: set[str] | None) -> dict:
    directive = probe_residual_directive(rollouts, ProbeResidualConfig(**settings))
    row = {**settings, "axes": len(directive.axes), "supports": sorted((len(a.rollouts) for a in directive.axes), reverse=True),
           "best_jaccard": {gap.gap_id: mean_best_jaccard(directive, [gap]) for gap in gaps}}
    if planted is not None:
        row["planted_best_jaccard"] = max((jaccard(planted, a.rollouts) for a in directive.axes), default=0.0)
    return row


SENTENCES = {
    "default_finds_planted": "M2's default settings recover a planted group of 25 failures, so its zero on the key gaps "
                             "is not a settings blind spot for a group this strong.",
    "settings_hide_signal": "M2's default settings miss a planted group of 25 failures that another tried setting "
                            "recovers, so its zero on real pools can come from its settings.",
    "untested": "H19 is untested: fewer than 20 failures outside the key gaps know lead_distance on enough window "
                "frames to carry the plant.",
    "planted_not_recovered": "No tried setting recovers a planted group of 25 failures, so M2's zero on real pools "
                             "says little about whether the gaps are there.",
}
RECOVERED = 0.5


def outcome(planted_runs: list[dict], planted: int) -> str:
    if planted < ProbeResidualConfig().min_support:
        return "untested"
    default = next(row for row in planted_runs if all(row[k] == v for k, v in DEFAULTS.items()))
    if default["planted_best_jaccard"] >= RECOVERED:
        return "default_finds_planted"
    found = any(row["planted_best_jaccard"] >= RECOVERED for row in planted_runs)
    return "settings_hide_signal" if found else "planted_not_recovered"


def gap_reading(real_runs: list[dict]) -> list[dict]:
    """Settings that reach 0.5 on a key gap, exploratory: the setting is then chosen using the key."""
    return [{**{k: row[k] for k in GRID}, "gap": gap, "jaccard": value}
            for row in real_runs for gap, value in row["best_jaccard"].items() if value >= RECOVERED]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest, failed = load_pool([REPO / f"configs/rollout/{name}.manifest.json" for name in POOL],
                                 [REPO / "results/savio" / name / "routes.jsonl" for name in POOL])
    gaps = [gap for gap in gaps_from_key(load_key(REPO / KEY), manifest, failed) if not gap.is_decoy]
    rollouts = load_rollouts()
    members = set().union(*(gap.failing_rollouts for gap in gaps))
    planted_pool, planted = plant(rollouts, members)
    real = [run(rollouts, settings, gaps, None) for settings in settings_grid()]
    with_plant = [run(planted_pool, settings, gaps, planted) for settings in settings_grid()]
    record = {"label": "DEV DRY RUN, NOT A VERDICT: H19 M2 settings sweep on H12's pool",
              "note": "Any best setting is chosen using the key.", "rollouts": len(rollouts),
              "failures": sum(r.failed for r in rollouts), "key_sizes": {g.gap_id: len(g.failing_rollouts) for g in gaps},
              "planted": PLANTED, "real": real, "planted_runs": with_plant}
    record["planted"] = len(planted)
    record["planted_known_share"] = sorted(round(known_share(r), 2) for r in rollouts if r.rollout_id in planted)
    record["outcome"] = outcome(with_plant, len(planted))
    record["reading"] = SENTENCES[record["outcome"]]
    record["gaps_at_or_above_0_5"] = gap_reading(real)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    default = next(row for row in real if all(row[k] == v for k, v in DEFAULTS.items()))
    planted_default = next(row for row in with_plant if all(row[k] == v for k, v in DEFAULTS.items()))
    print(json.dumps({"default_axes": default["axes"], "planted_default_jaccard": planted_default["planted_best_jaccard"],
                      "settings": len(real), "outcome": record["outcome"], "reading": record["reading"],
                      "gaps_at_or_above_0_5": len(record["gaps_at_or_above_0_5"])}))


if __name__ == "__main__":
    main()
