"""H14's effect rule (protocol.md): what `--debug 0` changes against `--debug 2` on paired routes.

Run on Savio from the repo root, after score_routes.py has written results/savio/h14-debug0 and h14-debug2:
    .runtime/policy-venv/bin/python docs/research/experiments/h14-route-markers/analyze.py checks --pairs 80
    .runtime/policy-venv/bin/python docs/research/experiments/h14-route-markers/analyze.py read --stage 1
    .runtime/policy-venv/bin/python docs/research/experiments/h14-route-markers/analyze.py read --stage final --pairs 80

`checks` prints no outcome: it reads the scorer's rerun lists, the route folders and the frame review, and hashes the scored
files without opening their rows. A route with no readiness.json or a guard mismatch becomes a dropped pair; a wrong arm voids
the run. `read` refuses until `checks` has passed on the same scored files. Unless it stops the run, `read --stage 1` shows only
the stop decision and the discordance. A final read short of all pairs needs results/savio/h14-read/stage-2-decision.json with
`stage_2_approved: false`, and it rules out a later final read on all pairs. Results go to results/savio/h14-read/.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import yaml
from scipy.stats import binomtest, norm

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "adapters/simlingo"))

from score_routes import attempts_by_route, chosen_attempt, stop_reason_of  # noqa: E402

ARMS = {"debug0": 0, "debug2": 2}
SEED = 14
STAGE_1_PAIRS, ALL_PAIRS = 80, 213
ALPHA = {"1": 0.005, "final": 0.045}
Z_90 = float(norm.ppf(0.95))
MARGINS = {"success": 8.0, "any_collision": 8.0, "route_completion": 3.0}
COLLISIONS = ("collisions_vehicle", "collisions_pedestrian", "collisions_layout")
FLIPS = BOOTSTRAP_DRAWS = 10_000
ATTEMPTS_ALLOWED = 3
MAX_DROPPED_SHARE = 0.10
FRAMES_TO_VIEW = 20
BRIDGE_ALPHA = 0.05
STEPS_PER_SIMULATED_SECOND = 20
PUBLISHED_DRIVING_SCORE_GAP = 4.2

REAL = "Real effect"
REAL_SMALLER = "Real, smaller than the margin"
NO_EFFECT = "No effect as large as the margin"
UNRESOLVED = "Unresolved"

OUTCOME, DROPPED, WAITING = "outcome", "dropped", "waiting"


def exact_mcnemar(only_debug0: int, only_debug2: int) -> float:
    total = only_debug0 + only_debug2
    return binomtest(only_debug0, total, 0.5).pvalue if total else 1.0


def agresti_min(only_debug0: int, only_debug2: int, pairs: int) -> tuple[float, float]:
    """90% interval for the paired difference in points, with 0.5 added to each of the four cells."""
    a, b, total = only_debug0 + 0.5, only_debug2 + 0.5, pairs + 2.0
    centre = (a - b) / total
    half_width = Z_90 * ((a + b) - (a - b) ** 2 / total) ** 0.5 / total
    return 100 * (centre - half_width), 100 * (centre + half_width)


def sign_flip_p(differences: np.ndarray, flips: int = FLIPS, seed: int = SEED) -> float:
    if not np.any(differences):
        return 1.0
    signs = np.random.default_rng(seed).choice((-1.0, 1.0), size=(flips, differences.size))
    flipped = np.abs((signs * differences).mean(axis=1))
    # The small tolerance keeps a flip that ties the observed mean from losing to rounding error.
    extreme = int(np.sum(flipped >= abs(differences.mean()) - 1e-12))
    return (extreme + 1) / (flips + 1)


def route_bootstrap(differences: np.ndarray, draws: int = BOOTSTRAP_DRAWS, seed: int = SEED) -> tuple[float, float]:
    picks = np.random.default_rng(seed).integers(0, differences.size, size=(draws, differences.size))
    low, high = np.percentile(differences[picks].mean(axis=1), [5, 95])
    return float(low), float(high)


def holm_passes(p_values: dict[str, float], alpha: float) -> dict[str, bool]:
    """Step-down Holm: the smallest p meets alpha/k, the next alpha/(k-1), and the first failure fails all after it."""
    passes = dict.fromkeys(p_values, False)
    for position, name in enumerate(sorted(p_values, key=lambda key: p_values[key])):
        if p_values[name] > alpha / (len(p_values) - position):
            break
        passes[name] = True
    return passes


def inside_margin(interval: tuple[float, float], margin: float) -> bool:
    return interval[0] > -margin and interval[1] < margin


def metric_verdict(holm_passed: bool, inside: bool) -> str:
    return {(True, False): REAL, (True, True): REAL_SMALLER, (False, True): NO_EFFECT, (False, False): UNRESOLVED}[
        (holm_passed, inside)]


def overall_verdict(verdicts: list[str]) -> str:
    return next(verdict for verdict in (REAL, UNRESOLVED, REAL_SMALLER, NO_EFFECT) if verdict in verdicts)


def any_collision(row: dict[str, Any]) -> bool:
    return any(row.get("infractions", {}).get(name) for name in COLLISIONS)


def discordance(pairs: list[tuple[dict, dict]], value: Any) -> tuple[int, int]:
    only_first = sum(bool(value(first)) and not value(second) for first, second in pairs)
    only_second = sum(bool(value(second)) and not value(first) for first, second in pairs)
    return only_first, only_second


def binary_metric(pairs: list[tuple[dict, dict]], value: Any) -> dict[str, Any]:
    only_debug0, only_debug2 = discordance(pairs, value)
    return {"pairs": len(pairs), "only_debug0": only_debug0, "only_debug2": only_debug2,
            "difference_points": 100 * (only_debug0 - only_debug2) / len(pairs),
            "p": exact_mcnemar(only_debug0, only_debug2), "interval_90": agresti_min(only_debug0, only_debug2, len(pairs))}


def completion_metric(pairs: list[tuple[dict, dict]]) -> dict[str, Any]:
    differences = np.array([debug0["score_route"] - debug2["score_route"] for debug0, debug2 in pairs], dtype=float)
    return {"pairs": len(pairs), "routes_differing": int(np.count_nonzero(differences)),
            "difference_points": float(differences.mean()), "p": sign_flip_p(differences),
            "interval_90": route_bootstrap(differences)}


def effect_rule(pairs: list[tuple[dict, dict]], alpha: float) -> dict[str, Any]:
    metrics = {"success": binary_metric(pairs, lambda row: row["success"]),
               "any_collision": binary_metric(pairs, any_collision),
               "route_completion": completion_metric(pairs)}
    passes = holm_passes({name: metric["p"] for name, metric in metrics.items()}, alpha)
    for name, metric in metrics.items():
        metric |= {"margin": MARGINS[name], "holm_passes": passes[name],
                   "inside_margin": inside_margin(metric["interval_90"], MARGINS[name])}
        metric["verdict"] = metric_verdict(metric["holm_passes"], metric["inside_margin"])
    return metrics


@dataclass
class Walk:
    """The draw, followed until enough pairs are counted. A waiting route may still count, so it holds a place."""
    counted: list[str] = field(default_factory=list)
    dropped: list[dict[str, Any]] = field(default_factory=list)
    waiting: list[dict[str, str]] = field(default_factory=list)

    @property
    def dropped_share(self) -> float:
        attempted = len(self.counted) + len(self.dropped)
        return len(self.dropped) / attempted if attempted else 0.0

    def dropped_by_arm(self) -> dict[str, int]:
        return {arm: sum(arm in entry["arms"] for entry in self.dropped) for arm in ARMS}


def route_states(summary: dict[str, Any], not_counted: set[str]) -> dict[str, str]:
    """A route's state from the scorer's lists and the route folders, so that no outcome is read to decide it."""
    states = {route_id: DROPPED for route_id in not_counted | set(summary["scenario_skipped"])}
    states |= dict.fromkeys(summary["not_run"], WAITING)
    for entry in summary["rerun"]:
        states[entry["id"]] = DROPPED if entry["attempts"] >= ATTEMPTS_ALLOWED else WAITING
    return states


def walk_draw(draw: list[str], target: int, states: dict[str, dict[str, str]]) -> Walk:
    walk = Walk()
    for route_id in draw:
        if len(walk.counted) + len(walk.waiting) >= target:
            break
        by_arm = {arm: states[arm].get(route_id, OUTCOME) for arm in ARMS}
        waiting = [arm for arm, state in by_arm.items() if state == WAITING]
        lost = [arm for arm, state in by_arm.items() if state == DROPPED]
        if waiting:
            walk.waiting.append({"id": route_id, "arms": waiting})
        elif lost:
            walk.dropped.append({"id": route_id, "arms": lost})
        else:
            walk.counted.append(route_id)
    return walk


def load_summary(results: Path, arm: str) -> dict[str, Any]:
    return json.loads((results / f"h14-{arm}/summary.json").read_text())


def load_draw() -> list[str]:
    configs = {arm: yaml.safe_load((ROOT / f"configs/rollout/h14-{arm}.yaml").read_text()) for arm in ARMS}
    if configs["debug0"]["routes"] != configs["debug2"]["routes"]:
        raise SystemExit("the two arms' configs list different routes")
    return [str(route) for route in configs["debug0"]["routes"]]


def chosen_attempts(results: Path, summary: dict[str, Any]) -> dict[str, Path]:
    attempts = attempts_by_route([results / job for job in summary["jobs"]])
    chosen = {route_id: chosen_attempt(tried) for route_id, tried in attempts.items()}
    return {route_id: attempt for route_id, attempt in chosen.items() if attempt is not None}


def read_text(path: Path) -> str:
    return path.read_text(errors="replace") if path.is_file() else ""


def scored_files_hash(results: Path) -> str:
    """Compared by `read`, so that a rescore after `checks` cannot pass unnoticed. The hash shows no outcome."""
    digest = hashlib.sha256()
    for arm in ARMS:
        for name in ("summary.json", "routes.jsonl"):
            path = results / f"h14-{arm}/{name}"
            digest.update(path.read_bytes() if path.is_file() else b"")
    return digest.hexdigest()


def arm_problem(route_dir: Path, level: int) -> str | None:
    """A route that names the wrong level or has the wrong live.txt points to a mis-submitted arm, so it voids the run."""
    readiness = route_dir / "readiness.json"
    named = json.loads(readiness.read_text())["config"]["simulator"].get("debug_level") if readiness.is_file() else level
    if named != level:
        return f"readiness names debug_level {named}"
    if (route_dir / "live.txt").is_file() != (level > 0):
        return f"live.txt {'missing' if level else 'present'}"
    return None


def guard_problem(route_dir: Path) -> str | None:
    step_lines = read_text(route_dir / "evaluator.log").count("SimLingo step")
    rows = len(read_text(route_dir / "controls.jsonl").splitlines())
    return None if step_lines == rows else f"{step_lines} step lines against {rows} control rows"


def guard_stops(results: Path, summary: dict[str, Any]) -> dict[str, int]:
    """Every attempt counts here, including the ones a rerun replaced."""
    stops = {"slow simulation or other recorded stop": 0, "evaluator silence": 0}
    for tried in attempts_by_route([results / job for job in summary["jobs"]]).values():
        for attempt in tried:
            stops["slow simulation or other recorded stop"] += stop_reason_of(attempt) is not None
            stops["evaluator silence"] += "printed nothing for" in read_text(attempt / "run.log")
    return stops


def frames_to_view(route_dirs: list[Path]) -> list[str]:
    frames = sorted(str(frame) for route_dir in route_dirs for frame in (route_dir / "frames").glob("*.png"))
    return random.Random(SEED).sample(frames, min(FRAMES_TO_VIEW, len(frames)))


def frame_review_passes(review: dict[str, Any] | None, target: int) -> bool:
    """The seeded frames of this route set, all viewed. One marker in the debug0 arm voids the run, and so does a debug2 arm with none."""
    if not review or review.get("target_pairs") != target or (review.get("frames_viewed_per_arm") or 0) < FRAMES_TO_VIEW:
        return False
    return review.get("debug0_frames_with_marker") == 0 and (review.get("debug2_frames_with_marker") or 0) > 0


def route_problems(route_dirs: dict[str, Path], level: int) -> dict[str, dict[str, str]]:
    arm = {route_id: problem for route_id, path in route_dirs.items() if (problem := arm_problem(path, level))}
    guard = {route_id: problem for route_id, path in route_dirs.items() if (problem := guard_problem(path))}
    no_readiness = {route_id: "no readiness.json" for route_id, path in route_dirs.items() if not (path / "readiness.json").is_file()}
    return {"arm": arm, "no_readiness": no_readiness, "guard": guard}


def checks(results: Path, target: int, output: Path) -> dict[str, Any]:
    draw = load_draw()
    summaries = {arm: load_summary(results, arm) for arm in ARMS}
    attempts = {arm: chosen_attempts(results, summaries[arm]) for arm in ARMS}
    not_played = {arm: {route_id for route_id, path in attempts[arm].items()
                        if "Ignoring scenario" in read_text(path / "evaluator.log")} for arm in ARMS}
    problems = {arm: route_problems(attempts[arm], ARMS[arm]) for arm in ARMS}
    lost_by_check = {arm: sorted({*problems[arm]["no_readiness"], *problems[arm]["guard"]}) for arm in ARMS}
    states = {arm: route_states(summaries[arm], not_played[arm] | set(lost_by_check[arm])) for arm in ARMS}
    walk = walk_draw(draw, target, states)
    used = {route_id: {arm: attempts[arm][route_id] for arm in ARMS} for route_id in walk.counted}
    review_path = output / "frames-viewed.json"
    review = json.loads(review_path.read_text()) if review_path.is_file() else None
    report = {
        "target_pairs": target, "pairs_counted": len(walk.counted), "pairs_dropped": walk.dropped,
        "dropped_by_arm": walk.dropped_by_arm(), "dropped_share": walk.dropped_share,
        "still_to_run": walk.waiting,
        "check_1_arms": {arm: problems[arm]["arm"] for arm in ARMS},
        "check_1_no_readiness": {arm: problems[arm]["no_readiness"] for arm in ARMS},
        "check_2_frames_to_view": {arm: frames_to_view([paths[arm] for paths in used.values()]) for arm in ARMS},
        "check_2_frames_viewed": review,
        "check_3_guard": {arm: problems[arm]["guard"] for arm in ARMS},
        "guard_stops": {arm: guard_stops(results, summaries[arm]) for arm in ARMS},
        "scenario_not_played": {arm: sorted(not_played[arm]) for arm in ARMS},
        "lost_by_check": lost_by_check,
        "scored_files_sha256": scored_files_hash(results),
    }
    report["passed"] = bool(walk.counted and not walk.waiting and frame_review_passes(review, target)
                            and not any(problems[arm]["arm"] for arm in ARMS))
    output.mkdir(parents=True, exist_ok=True)
    (output / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {str(row["id"]): row for row in rows}


def family_interval(pairs: list[tuple[dict, dict]], draws: int = BOOTSTRAP_DRAWS, seed: int = SEED) -> dict[str, Any]:
    """Success difference, resampling whole scenario families in place of routes."""
    by_family: dict[str, list[float]] = {}
    for debug0, debug2 in pairs:
        by_family.setdefault(debug0["scenario"], []).append(100.0 * (int(debug0["success"]) - int(debug2["success"])))
    totals = np.array([sum(values) for values in by_family.values()])
    counts = np.array([len(values) for values in by_family.values()])
    picks = np.random.default_rng(seed).integers(0, len(totals), size=(draws, len(totals)))
    low, high = np.percentile(totals[picks].sum(axis=1) / counts[picks].sum(axis=1), [5, 95])
    return {"families": len(totals), "interval_90": (float(low), float(high))}


def ability_lists() -> dict[str, list[str]]:
    """Bench2Drive's scenario lists; the tool itself imports CARLA, so the assignment is parsed, not imported."""
    tree = ast.parse((ROOT / ".runtime/simlingo/Bench2Drive/tools/ability_benchmark.py").read_text())
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "Ability")
    return ast.literal_eval(assignment.value)


def by_ability(pairs: list[tuple[dict, dict]], abilities: dict[str, list[str]]) -> dict[str, Any]:
    """Whole-route success, so these do not compare with ability_benchmark.py, which also finds each junction."""
    report = {}
    for ability, scenarios in abilities.items():
        members = [pair for pair in pairs if pair[0]["scenario"] in scenarios]
        report[ability] = {"pairs": len(members), **{arm: sum(pair[index]["success"] for pair in members)
                                                     for index, arm in enumerate(ARMS)}}
    return report


def node_of(results: Path, row: dict[str, Any]) -> str:
    readiness = results / str(row["job"]) / f"route-{row['id']}/readiness.json"
    return json.loads(readiness.read_text()).get("node", "unknown") if readiness.is_file() else "unknown"


def arm_by_node(results: Path, pairs: list[tuple[dict, dict]]) -> dict[str, dict[str, dict[str, int]]]:
    report: dict[str, dict[str, dict[str, int]]] = {arm: {} for arm in ARMS}
    for pair in pairs:
        for index, arm in enumerate(ARMS):
            entry = report[arm].setdefault(node_of(results, pair[index]), {"routes": 0, "successes": 0})
            entry["routes"] += 1
            entry["successes"] += int(pair[index]["success"])
    return report


def wall_seconds_per_step(rows: list[dict[str, Any]]) -> float:
    return median(row["duration_system"] / (row["duration_game"] * STEPS_PER_SIMULATED_SECOND)
                  for row in rows if row.get("duration_game"))


def reported(results: Path, pairs: list[tuple[dict, dict]]) -> dict[str, Any]:
    """Reported beside the verdict and never part of it."""
    means = {arm: float(np.mean([pair[index]["score_composed"] for pair in pairs])) for index, arm in enumerate(ARMS)}
    return {
        "driving_score": {**means, "difference_points": means["debug0"] - means["debug2"],
                          "gap_to_published_points": PUBLISHED_DRIVING_SCORE_GAP},
        "success_by_ability": by_ability(pairs, ability_lists()),
        "success_by_scenario_family": family_interval(pairs),
        "arm_by_node": arm_by_node(results, pairs),
        "wall_seconds_per_step": {arm: wall_seconds_per_step([pair[index] for pair in pairs])
                                  for index, arm in enumerate(ARMS)},
    }


def bridge(new_debug2: dict[str, dict], step2: dict[str, dict], route_ids: list[str]) -> dict[str, Any]:
    """The new debug2 arm against Step 2, by McNemar on the two yes-or-no metrics. Either below 0.05 means drift."""
    pairs = [(new_debug2[route_id], step2[route_id]) for route_id in route_ids if "success" in step2.get(route_id, {})]
    report: dict[str, Any] = {"pairs": len(pairs)}
    for name, value in (("success", lambda row: row["success"]), ("any_collision", any_collision)):
        only_new, only_step2 = discordance(pairs, value)
        report[name] = {"only_new": only_new, "only_step2": only_step2, "p": exact_mcnemar(only_new, only_step2)}
    report["pipeline_drifted"] = bool(min(report["success"]["p"], report["any_collision"]["p"]) < BRIDGE_ALPHA)
    return report


def stage_reading(metrics: dict[str, Any], stage: str, dropped_share: float) -> dict[str, Any]:
    """Stage 1 can only stop the run, and only as Real effect. Any other Stage 1 reading gives no verdict yet."""
    verdict = overall_verdict([metric["verdict"] for metric in metrics.values()])
    if dropped_share > MAX_DROPPED_SHARE:
        return {"verdict": UNRESOLVED, "stopped_at_stage_1": False,
                "note": f"{dropped_share:.1%} of pairs dropped, above the 10% limit"}
    if stage == "final":
        return {"verdict": verdict, "stopped_at_stage_1": False}
    if verdict == REAL:
        return {"verdict": REAL, "stopped_at_stage_1": True,
                "note": "The size is overstated, because only a large early estimate can stop the run."}
    return {"verdict": None, "stopped_at_stage_1": False, "note": "No stop. A final read at 0.045 decides."}


def load_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.is_file() else None


def final_read_problem(output: Path, target: int) -> str | None:
    """Stage 2's decision comes first and is made blind: a short final read needs it on file, and spends the final look."""
    if target != ALL_PAIRS:
        decision = load_json(output / "stage-2-decision.json") or {}
        return None if decision.get("stage_2_approved") is False else "record Stage 2's refusal in stage-2-decision.json first"
    earlier = load_json(output / "read-stage-final.json") or {}
    return f"a final read at {earlier['target_pairs']} pairs has already been made" if earlier.get("target_pairs", target) != target else None


def stage_1_without_a_stop(report: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """The stop decision and how often the arms disagree, with no direction, so that no look at effects informs Stage 2."""
    shown = ("stage", "alpha", "pairs", "dropped_by_arm", "dropped_share", "verdict", "stopped_at_stage_1", "note")
    disagreeing = {name: (metrics[name]["only_debug0"] + metrics[name]["only_debug2"]) / report["pairs"]
                   for name in ("success", "any_collision")}
    return {**{key: report[key] for key in shown if key in report}, "discordant_share": disagreeing,
            "route_completion_routes_differing": metrics["route_completion"]["routes_differing"],
            "pipeline_drifted": report["bridge"]["pipeline_drifted"]}


def read(results: Path, stage: str, target: int, step2_path: Path, output: Path) -> dict[str, Any]:
    checked = load_json(output / "checks.json") or {}
    if not checked.get("passed") or checked.get("target_pairs") != target:
        raise SystemExit(f"checks have not passed for {target} pairs: run `checks` and read it first")
    if checked["scored_files_sha256"] != scored_files_hash(results):
        raise SystemExit("the scored files changed after `checks`: run `checks` again")
    if stage == "final" and (problem := final_read_problem(output, target)):
        raise SystemExit(problem)
    summaries = {arm: load_summary(results, arm) for arm in ARMS}
    not_counted = {arm: set(checked["scenario_not_played"][arm]) | set(checked["lost_by_check"][arm]) for arm in ARMS}
    walk = walk_draw(load_draw(), target, {arm: route_states(summaries[arm], not_counted[arm]) for arm in ARMS})
    rows = {arm: load_rows(results / f"h14-{arm}/routes.jsonl") for arm in ARMS}
    pairs = [(rows["debug0"][route_id], rows["debug2"][route_id]) for route_id in walk.counted]
    metrics = effect_rule(pairs, ALPHA[stage])
    report = {"stage": stage, "alpha": ALPHA[stage], "target_pairs": target, "pairs": len(pairs), "dropped_by_arm": walk.dropped_by_arm(),
              "dropped_share": walk.dropped_share, **stage_reading(metrics, stage, walk.dropped_share),
              "metrics": metrics, "bridge": bridge(rows["debug2"], load_rows(step2_path), walk.counted),
              "reported": reported(results, pairs)}
    if stage == "1" and not report["stopped_at_stage_1"]:
        report = stage_1_without_a_stop(report, metrics)
    (output / f"read-stage-{stage}.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["checks", "read"])
    parser.add_argument("--results", type=Path, default=Path("results/savio"))
    parser.add_argument("--output", type=Path, default=Path("results/savio/h14-read"))
    parser.add_argument("--stage", choices=sorted(ALPHA), default="1")
    parser.add_argument("--pairs", type=int, choices=[STAGE_1_PAIRS, ALL_PAIRS], default=STAGE_1_PAIRS)
    parser.add_argument("--step2", type=Path, default=Path("results/savio/step2-bench2drive220/routes.jsonl"))
    args = parser.parse_args()
    if args.stage == "1" and args.pairs != STAGE_1_PAIRS:
        parser.error(f"Stage 1 reads the first {STAGE_1_PAIRS} pairs")
    if args.mode == "checks":
        report = checks(args.results, args.pairs, args.output)
    else:
        report = read(args.results, args.stage, args.pairs, args.step2, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
