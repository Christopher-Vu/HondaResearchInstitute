"""H14's effect rule on synthetic pairs: every verdict row, Holm's order, the two-look stop, and the checks that gate reading."""
import importlib.util
import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

EXPERIMENT = Path(__file__).resolve().parents[1] / "docs/research/experiments/h14-route-markers"
CONFIGS = Path(__file__).resolve().parents[1] / "configs/rollout"


def load(name):
    spec = importlib.util.spec_from_file_location(f"h14_{name}", EXPERIMENT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"h14_{name}"] = module
    spec.loader.exec_module(module)
    return module


analyze = load("analyze")
power = load("power")


def row(route_id, success=True, score_route=100.0, collision=None, scenario="ParkedObstacle", **extra):
    return {"id": str(route_id), "scenario": scenario, "job": "1", "success": success, "score_route": score_route,
            "score_composed": score_route if success else score_route * 0.6, "duration_game": 40.0, "duration_system": 400.0,
            "infractions": {collision: 1} if collision else {}, **extra}


def pairs_with(only_debug0=0, only_debug2=0, same=0, value="success"):
    """`only_debug0` pairs where debug0 alone has the property, and so on. Success and collision are built the same way."""
    def side(has):
        return {"success": has} if value == "success" else {"collision": "collisions_vehicle" if has else None}

    built = [(True, False)] * only_debug0 + [(False, True)] * only_debug2 + [(False, False)] * same
    return [(row(i, **side(first)), row(i, **side(second))) for i, (first, second) in enumerate(built)]


def completion_pairs(differences):
    return [(row(i, score_route=100.0), row(i, score_route=100.0 - difference)) for i, difference in enumerate(differences)]


# Each verdict row of the protocol's table, from data that lands on it at the final threshold.
def test_verdict_row_passes_and_reaches_past_the_margin_is_real_effect():
    metrics = analyze.effect_rule(pairs_with(only_debug0=40, same=173), 0.045)
    assert metrics["success"]["holm_passes"] and not metrics["success"]["inside_margin"]
    assert metrics["success"]["verdict"] == analyze.REAL


def test_verdict_row_passes_and_inside_the_margin_is_real_but_smaller():
    metrics = analyze.effect_rule(completion_pairs([0.5] * 30 + [0.0] * 183), 0.045)
    assert metrics["route_completion"]["holm_passes"] and metrics["route_completion"]["inside_margin"]
    assert metrics["route_completion"]["verdict"] == analyze.REAL_SMALLER


def test_verdict_row_fails_and_inside_the_margin_is_no_effect():
    metrics = analyze.effect_rule(pairs_with(only_debug0=5, only_debug2=5, same=203), 0.045)
    assert not metrics["success"]["holm_passes"] and metrics["success"]["inside_margin"]
    assert metrics["success"]["verdict"] == analyze.NO_EFFECT


def test_verdict_row_fails_and_reaches_past_the_margin_is_unresolved():
    metrics = analyze.effect_rule(pairs_with(only_debug0=14, only_debug2=8, same=58), 0.045)
    assert not metrics["success"]["holm_passes"] and not metrics["success"]["inside_margin"]
    assert metrics["success"]["verdict"] == analyze.UNRESOLVED


def test_collision_is_any_of_three_kinds_and_other_infractions_do_not_count():
    for kind in ("collisions_vehicle", "collisions_pedestrian", "collisions_layout"):
        assert analyze.any_collision(row(1, collision=kind))
    assert not analyze.any_collision(row(1, collision="red_light"))
    assert not analyze.any_collision(row(1))


def test_differences_are_debug0_minus_debug2_in_both_directions():
    worse = analyze.effect_rule(pairs_with(only_debug2=40, same=173), 0.045)["success"]
    assert worse["difference_points"] == pytest.approx(-100 * 40 / 213)
    assert worse["interval_90"][1] < 0
    assert worse["verdict"] == analyze.REAL
    collisions = analyze.effect_rule(pairs_with(only_debug0=30, same=183, value="collision"), 0.045)["any_collision"]
    assert collisions["only_debug0"] == 30 and collisions["difference_points"] > 0


def test_overall_verdict_follows_the_protocols_order():
    assert analyze.overall_verdict([analyze.NO_EFFECT, analyze.UNRESOLVED, analyze.REAL]) == analyze.REAL
    assert analyze.overall_verdict([analyze.REAL_SMALLER, analyze.UNRESOLVED, analyze.NO_EFFECT]) == analyze.UNRESOLVED
    assert analyze.overall_verdict([analyze.REAL_SMALLER, analyze.NO_EFFECT, analyze.NO_EFFECT]) == analyze.REAL_SMALLER
    assert analyze.overall_verdict([analyze.NO_EFFECT] * 3) == analyze.NO_EFFECT


def test_holm_steps_down_and_stops_at_the_first_failure():
    p = {"a": 0.001, "b": 0.02, "c": 0.04}
    assert analyze.holm_passes(p, 0.045) == {"a": True, "b": True, "c": True}
    assert analyze.holm_passes({"a": 0.02, "b": 0.001, "c": 0.04}, 0.045) == {"a": True, "b": True, "c": True}
    assert analyze.holm_passes({"a": 0.016, "b": 0.016, "c": 0.016}, 0.045) == {"a": False, "b": False, "c": False}
    assert analyze.holm_passes({"a": 0.001, "b": 0.03, "c": 0.031}, 0.045) == {"a": True, "b": False, "c": False}


def test_holm_passes_exactly_at_its_threshold():
    assert analyze.holm_passes({"a": 0.015, "b": 0.5, "c": 0.5}, 0.045)["a"]


def test_agresti_min_matches_the_hand_value_and_the_power_simulation():
    low, high = analyze.agresti_min(10, 2, 80)
    centre, half_width = 100 * 8 / 82, 100 * 1.644854 * (13 - 64 / 82) ** 0.5 / 82
    assert (low, high) == pytest.approx((centre - half_width, centre + half_width), abs=1e-3)
    for only_a, only_b, n in [(10, 2, 80), (6, 6, 80), (20, 18, 213), (1, 0, 213), (30, 1, 213)]:
        expected = power.inside_margin(np.array([only_a]), np.array([only_b]), n)[0]
        assert analyze.inside_margin(analyze.agresti_min(only_a, only_b, n), 8.0) == bool(expected)


def test_mcnemar_is_exact_and_matches_the_power_simulation():
    assert analyze.exact_mcnemar(0, 0) == 1.0
    assert analyze.exact_mcnemar(5, 0) == pytest.approx(2 / 2 ** 5)
    assert analyze.exact_mcnemar(30, 12) == pytest.approx(power.mcnemar_p(30, 12))


def test_sign_flip_is_seeded_one_when_nothing_differs_and_never_zero():
    assert analyze.sign_flip_p(np.zeros(80)) == 1.0
    differences = np.array([1.0] * 20 + [0.0] * 60)
    assert analyze.sign_flip_p(differences) == analyze.sign_flip_p(differences)
    assert 0 < analyze.sign_flip_p(differences) < 0.001
    assert analyze.sign_flip_p(np.array([1.0, -1.0] * 40)) > 0.9


def test_route_bootstrap_is_seeded_and_brackets_the_mean():
    differences = np.array([3.0] * 10 + [0.0] * 70)
    low, high = analyze.route_bootstrap(differences)
    assert (low, high) == analyze.route_bootstrap(differences)
    assert low < differences.mean() < high


def test_stage_1_stops_only_as_real_effect_and_otherwise_gives_no_verdict():
    large = analyze.effect_rule(pairs_with(only_debug0=30, same=50), analyze.ALPHA["1"])
    assert analyze.stage_reading(large, "1", 0.0)["stopped_at_stage_1"]
    assert analyze.stage_reading(large, "1", 0.0)["verdict"] == analyze.REAL
    middling = analyze.effect_rule(pairs_with(only_debug0=12, only_debug2=2, same=66), analyze.ALPHA["1"])
    reading = analyze.stage_reading(middling, "1", 0.0)
    assert not reading["stopped_at_stage_1"] and reading["verdict"] is None
    assert analyze.effect_rule(pairs_with(only_debug0=12, only_debug2=2, same=66), analyze.ALPHA["final"])["success"]["holm_passes"]


def test_a_small_real_change_at_stage_1_is_not_a_stop():
    metrics = analyze.effect_rule(completion_pairs([0.5] * 30 + [0.0] * 50), analyze.ALPHA["1"])
    assert metrics["route_completion"]["verdict"] == analyze.REAL_SMALLER
    assert not analyze.stage_reading(metrics, "1", 0.0)["stopped_at_stage_1"]


def test_over_ten_percent_dropped_is_unresolved_whatever_the_metrics_say():
    metrics = analyze.effect_rule(pairs_with(only_debug0=40, same=173), 0.045)
    assert analyze.stage_reading(metrics, "final", 0.11)["verdict"] == analyze.UNRESOLVED
    assert analyze.stage_reading(metrics, "final", 0.10)["verdict"] == analyze.REAL


def summary(not_run=(), rerun=(), skipped=()):
    return {"not_run": list(not_run), "scenario_skipped": list(skipped), "jobs": ["1"],
            "rerun": [{"id": route_id, "attempts": attempts} for route_id, attempts in rerun]}


def walk(draw, target, debug0=None, debug2=None):
    states = {"debug0": analyze.route_states(debug0 or summary(), set()), "debug2": analyze.route_states(debug2 or summary(), set())}
    return analyze.walk_draw(draw, target, states)


def test_a_route_lost_after_two_reruns_is_dropped_by_arm_and_the_next_id_replaces_it():
    result = walk(list("abcd"), 3, debug0=summary(rerun=[("b", 3)]))
    assert result.counted == ["a", "c", "d"]
    assert result.dropped == [{"id": "b", "arms": ["debug0"]}]
    assert result.dropped_by_arm() == {"debug0": 1, "debug2": 0}
    assert result.dropped_share == pytest.approx(0.25)


def test_a_route_with_reruns_left_waits_and_holds_its_place():
    result = walk(list("abcd"), 3, debug2=summary(rerun=[("b", 2)]))
    assert result.counted == ["a", "c"]
    assert result.waiting == [{"id": "b", "arms": ["debug2"]}]


def test_a_skipped_scenario_or_one_the_evaluator_ignored_drops_the_pair():
    assert walk(list("abc"), 2, debug0=summary(skipped=["a"])).counted == ["b", "c"]
    states = {"debug0": analyze.route_states(summary(), {"a"}), "debug2": analyze.route_states(summary(), set())}
    assert analyze.walk_draw(list("abc"), 2, states).counted == ["b", "c"]


def test_a_replacement_not_yet_driven_is_listed_to_run():
    result = walk(list("abc"), 2, debug0=summary(rerun=[("a", 3)], not_run=["c"]), debug2=summary(not_run=["c"]))
    assert result.counted == ["b"]
    assert result.waiting == [{"id": "c", "arms": ["debug0", "debug2"]}]


def test_the_two_configs_differ_only_in_name_scope_and_level_and_hold_the_protocols_draw():
    debug0, debug2 = (yaml.safe_load((CONFIGS / f"h14-debug{level}.yaml").read_text()) for level in (0, 2))
    assert debug0["simulator"]["debug_level"] == 0 and debug2["simulator"]["debug_level"] == 2
    assert debug0["simulator"]["timeout_seconds"] == 600 and debug0["route"]["seed"] == 0 and debug0["capture_every"] == 10
    assert "capture_token_layers" not in debug0 and debug0["policy"]["cot"] is False
    for config in (debug0, debug2):
        config.pop("name"), config.pop("scope"), config["simulator"].pop("debug_level")
    assert debug0 == debug2
    step2 = yaml.safe_load((CONFIGS / "step2-bench2drive220.yaml").read_text())["routes"]
    skipped = {"23700", "23901", "23910", "23918", "23930", "24078", "24098"}
    draw = sorted((str(route) for route in step2 if str(route) not in skipped), key=int)
    random.Random(14).shuffle(draw)
    assert debug0["routes"] == draw
    assert draw[:3] == ["25358", "2664", "26418"] and draw[79] == "3712" and len(draw) == 213


def write_route(job_dir, route_id, level, step_lines=3, control_rows=3, status="Completed", live=None, node="n0001"):
    route_dir = job_dir / f"route-{route_id}"
    (route_dir / "frames").mkdir(parents=True)
    (route_dir / "frames/000020.png").write_bytes(b"")
    (route_dir / "result.json").write_text(json.dumps({"_checkpoint": {"records": [{"status": status}]}}))
    (route_dir / "readiness.json").write_text(json.dumps({"config": {"simulator": {"debug_level": level}}, "node": node}))
    (route_dir / "evaluator.log").write_text("SimLingo step 1\n" * step_lines)
    (route_dir / "controls.jsonl").write_text("{}\n" * control_rows)
    if live if live is not None else level > 0:
        (route_dir / "live.txt").write_text("")


def fake_run(tmp_path, monkeypatch, route_ids=("a", "b"), **debug0_route):
    monkeypatch.setattr(analyze, "load_draw", lambda: list(route_ids))
    for arm, level, job in (("debug0", 0, "10"), ("debug2", 2, "20")):
        for route_id in route_ids:
            write_route(tmp_path / job, route_id, level, **(debug0_route if arm == "debug0" else {}))
        (tmp_path / f"h14-{arm}").mkdir()
        (tmp_path / f"h14-{arm}/summary.json").write_text(json.dumps({**summary(), "jobs": [job]}))
    return tmp_path, tmp_path / "read"


def review(output, debug0=0, debug2=3, target=2, viewed=analyze.FRAMES_TO_VIEW):
    output.mkdir(exist_ok=True)
    (output / "frames-viewed.json").write_text(json.dumps({"debug0_frames_with_marker": debug0, "debug2_frames_with_marker": debug2,
                                                           "target_pairs": target, "frames_viewed_per_arm": viewed}))


def test_checks_pass_on_a_clean_run_and_print_no_outcome(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch)
    review(output)
    report = analyze.checks(results, 2, output)
    assert report["passed"] and report["pairs_counted"] == 2
    assert len(report["check_2_frames_to_view"]["debug0"]) == 2
    assert not {"success", "score_route", "infractions"} & set(json.dumps(report).replace('"', " ").split())


def test_checks_fail_until_someone_has_viewed_the_frames(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch)
    assert not analyze.checks(results, 2, output)["passed"]


@pytest.mark.parametrize("debug0, debug2", [(1, 3), (0, 0)])
def test_a_marker_at_debug_0_or_none_at_debug_2_voids_the_run(tmp_path, monkeypatch, debug0, debug2):
    results, output = fake_run(tmp_path, monkeypatch)
    review(output, debug0, debug2)
    assert not analyze.checks(results, 2, output)["passed"]


def test_live_txt_at_debug_0_fails_the_arm_check(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch, live=True)
    review(output)
    report = analyze.checks(results, 2, output)
    assert not report["passed"] and report["check_1_arms"]["debug0"]["a"] == "live.txt present"


def test_a_step_line_mismatch_drops_that_pair_by_arm_and_the_next_id_replaces_it(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch, route_ids=("a", "b", "c"))
    review(output)
    (results / "10/route-a/evaluator.log").write_text("SimLingo step 1\n" * 2)
    report = analyze.checks(results, 2, output)
    assert report["passed"] and "2 step lines" in report["check_3_guard"]["debug0"]["a"]
    assert report["pairs_dropped"] == [{"id": "a", "arms": ["debug0"]}] and report["pairs_counted"] == 2
    assert report["dropped_by_arm"] == {"debug0": 1, "debug2": 0} and report["lost_by_check"]["debug0"] == ["a"]


def test_a_route_with_no_readiness_is_dropped_and_read_walks_the_same_pairs(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch, route_ids=("a", "b", "c"))
    monkeypatch.setattr(analyze, "ability_lists", lambda: {"Overtaking": ["ParkedObstacle"]})
    (results / "20/route-b/readiness.json").unlink()
    for arm, job in (("debug0", "10"), ("debug2", "20")):
        write_scored(results, arm, [row(route_id, job=job) for route_id in "abc"])
    review(output)
    decide_stage_2(output)
    report = analyze.checks(results, 2, output)
    assert report["passed"] and report["pairs_dropped"] == [{"id": "b", "arms": ["debug2"]}]
    assert report["check_1_no_readiness"]["debug2"] == {"b": "no readiness.json"}
    step2 = tmp_path / "step2.jsonl"
    step2.write_text("".join(json.dumps(row(route_id)) + "\n" for route_id in "abc"))
    assert analyze.read(results, "final", 2, step2, output)["dropped_by_arm"] == {"debug0": 0, "debug2": 1}


def test_every_route_lost_to_checks_does_not_pass(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch, step_lines=2)
    review(output)
    assert not analyze.checks(results, 2, output)["passed"]


def test_a_wrong_level_in_any_route_voids_the_run_even_on_a_route_outside_the_pairs(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch, route_ids=("a", "b", "c"))
    review(output)
    readiness = results / "10/route-c/readiness.json"
    readiness.write_text(json.dumps({"config": {"simulator": {"debug_level": 2}}, "node": "n0001"}))
    report = analyze.checks(results, 2, output)
    assert not report["passed"] and report["check_1_arms"]["debug0"]["c"] == "readiness names debug_level 2"


def test_live_txt_on_a_route_with_no_readiness_still_voids_the_run(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch, route_ids=("a", "b", "c"))
    review(output)
    (results / "10/route-a/readiness.json").unlink()
    (results / "10/route-a/live.txt").write_text("")
    assert not analyze.checks(results, 2, output)["passed"]


@pytest.mark.parametrize("fields", [{"target": 213}, {"viewed": analyze.FRAMES_TO_VIEW - 1}])
def test_a_frame_review_of_other_routes_or_too_few_frames_does_not_count(tmp_path, monkeypatch, fields):
    results, output = fake_run(tmp_path, monkeypatch)
    review(output, **fields)
    assert not analyze.checks(results, 2, output)["passed"]


def write_scored(results, arm, rows):
    (results / f"h14-{arm}/routes.jsonl").write_text("".join(json.dumps(item) + "\n" for item in rows))


def decide_stage_2(output, approved=False):
    output.mkdir(exist_ok=True)
    (output / "stage-2-decision.json").write_text(json.dumps({"stage_2_approved": approved}))


def scored_run(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch)
    monkeypatch.setattr(analyze, "ability_lists", lambda: {"Overtaking": ["ParkedObstacle"]})
    write_scored(results, "debug0", [row("a", job="10"), row("b", job="10", success=False)])
    write_scored(results, "debug2", [row("a", job="20"), row("b", job="20")])
    step2 = tmp_path / "step2.jsonl"
    step2.write_text(json.dumps(row("a")) + "\n" + json.dumps(row("b")) + "\n")
    review(output)
    analyze.checks(results, 2, output)
    return results, output, step2


def test_stage_1_without_a_stop_shows_only_the_stop_and_the_discordance(tmp_path, monkeypatch):
    results, output, step2 = scored_run(tmp_path, monkeypatch)
    report = analyze.read(results, "1", 2, step2, output)
    assert report["verdict"] is None and not report["stopped_at_stage_1"]
    assert report["discordant_share"]["success"] == pytest.approx(0.5)
    written = (output / "read-stage-1.json").read_text()
    for hidden in ("metrics", "reported", "only_debug0", "difference_points", "interval_90", "bridge"):
        assert hidden not in written


def test_a_stage_1_stop_keeps_the_full_report(tmp_path, monkeypatch):
    results, output, step2 = scored_run(tmp_path, monkeypatch)
    monkeypatch.setattr(analyze, "stage_reading", lambda *_: {"verdict": analyze.REAL, "stopped_at_stage_1": True})
    assert "metrics" in analyze.read(results, "1", 2, step2, output)


def test_a_short_final_read_waits_for_a_recorded_refusal_of_stage_2(tmp_path, monkeypatch):
    results, output, step2 = scored_run(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="stage-2-decision"):
        analyze.read(results, "final", 2, step2, output)
    decide_stage_2(output, approved=True)
    with pytest.raises(SystemExit, match="stage-2-decision"):
        analyze.read(results, "final", 2, step2, output)
    decide_stage_2(output)
    assert analyze.read(results, "final", 2, step2, output)["pairs"] == 2


def test_a_short_final_read_rules_out_a_later_read_on_all_pairs(tmp_path):
    (tmp_path / "read-stage-final.json").write_text(json.dumps({"target_pairs": analyze.STAGE_1_PAIRS}))
    assert "already" in analyze.final_read_problem(tmp_path, analyze.ALL_PAIRS)
    (tmp_path / "read-stage-final.json").unlink()
    assert analyze.final_read_problem(tmp_path, analyze.ALL_PAIRS) is None


def test_read_refuses_when_the_files_were_rescored_after_checks(tmp_path, monkeypatch):
    results, output, step2 = scored_run(tmp_path, monkeypatch)
    write_scored(results, "debug0", [row("a", job="10"), row("b", job="10")])
    with pytest.raises(SystemExit, match="changed"):
        analyze.read(results, "1", 2, step2, output)


def test_read_refuses_before_checks_pass_and_writes_the_verdict_after(tmp_path, monkeypatch):
    results, output = fake_run(tmp_path, monkeypatch)
    monkeypatch.setattr(analyze, "ability_lists", lambda: {"Overtaking": ["ParkedObstacle"]})
    write_scored(results, "debug0", [row("a", job="10"), row("b", job="10", success=False, collision="collisions_vehicle")])
    write_scored(results, "debug2", [row("a", job="20"), row("b", job="20")])
    step2 = tmp_path / "step2.jsonl"
    step2.write_text(json.dumps(row("a")) + "\n" + json.dumps(row("b")) + "\n")
    with pytest.raises(SystemExit):
        analyze.read(results, "final", 2, step2, output)
    review(output)
    decide_stage_2(output)
    analyze.checks(results, 2, output)
    report = analyze.read(results, "final", 2, step2, output)
    assert report["metrics"]["success"]["only_debug2"] == 1 and report["metrics"]["any_collision"]["only_debug0"] == 1
    assert report["verdict"] == analyze.UNRESOLVED
    assert report["bridge"] == {"pairs": 2, "success": {"only_new": 0, "only_step2": 0, "p": 1.0},
                                "any_collision": {"only_new": 0, "only_step2": 0, "p": 1.0}, "pipeline_drifted": False}
    assert report["reported"]["arm_by_node"]["debug0"]["n0001"] == {"routes": 2, "successes": 1}
    assert report["reported"]["success_by_ability"]["Overtaking"] == {"pairs": 2, "debug0": 1, "debug2": 2}
    assert report["reported"]["wall_seconds_per_step"]["debug0"] == pytest.approx(0.5)
    assert json.loads((output / "read-stage-final.json").read_text())["verdict"] == analyze.UNRESOLVED


def test_bridge_flags_drift_only_below_its_threshold():
    new = {str(i): row(i, success=i >= 12) for i in range(20)}
    step2 = {str(i): row(i) for i in range(20)}
    assert analyze.bridge(new, step2, list(new))["pipeline_drifted"]
    assert not analyze.bridge(step2, step2, list(new))["pipeline_drifted"]


def test_the_family_interval_resamples_families():
    pairs = [(row(i, success=True, scenario=f"f{i % 4}"), row(i, success=i % 4 != 0, scenario=f"f{i % 4}")) for i in range(40)]
    result = analyze.family_interval(pairs)
    assert result["families"] == 4
    assert result["interval_90"][0] < 25 < result["interval_90"][1]


def test_ability_lists_parse_from_the_pinned_tool_without_importing_carla():
    if not (analyze.ROOT / ".runtime/simlingo/Bench2Drive/tools/ability_benchmark.py").is_file():
        pytest.skip("evaluator not installed")
    assert set(analyze.ability_lists()) == {"Overtaking", "Merging", "Emergency_Brake", "Give_Way", "Traffic_Signs"}
