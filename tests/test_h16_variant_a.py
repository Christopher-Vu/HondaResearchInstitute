"""H16: the training-frame inputs, the stop rule's reading per gap class, and the plain and post hoc paths apart."""
import gzip
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
HERE = ROOT / "docs/research/experiments/h16-b7-rollout-free"
sys.path.insert(0, str(HERE))

import job_guard as guard  # noqa: E402

from baselines import b7_variant_a as variant_a  # noqa: E402
from baselines.b7_variant_a import GapEvidence  # noqa: E402
from discovery import sae  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(f"h16_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


score = load("score")
read_rule = load("read_rule")
GAP = "P4_camera_occlusion"
HIDDEN, LAYERS = 24, 11
STEPS = np.arange(0, 120, 5)


def evidence(**overrides):
    values = dict(b7_recovers=True, b7_best=0.6, b7_median=0.5, methods_recover=True, methods_best=0.9,
                  methods_median=0.8, claim_b_holds=True)
    return GapEvidence(**{**values, **overrides})


def test_route_list_loads_with_unique_names():
    routes = variant_a.read_route_list()
    assert len(routes) == 1000 and all(route.startswith("data/simlingo/") for route in routes)


def test_every_drawn_chunk_is_named_once_and_every_route_family_has_one():
    assert len(set(variant_a.CHUNKS)) == 6
    folders = {route.split("/")[2] for route in variant_a.read_route_list()}
    assert folders == {"lb1_split", "training_1_scenario", "training_3_scenarios"}


def test_frame_without_a_measurement_loses_the_route(tmp_path):
    (tmp_path / "rgb").mkdir()
    (tmp_path / "measurements").mkdir()
    for stem in ("0000", "0001"):
        (tmp_path / "rgb" / f"{stem}.jpg").write_bytes(b"")
    (tmp_path / "measurements/0000.json.gz").write_bytes(b"")
    with pytest.raises(ValueError):
        variant_a.frame_stems(tmp_path)
    (tmp_path / "measurements/0001.json.gz").write_bytes(b"")
    assert variant_a.frame_stems(tmp_path) == ["0000", "0001"]


def test_measurement_gives_the_rounded_speed_and_both_target_points(tmp_path):
    (tmp_path / "measurements").mkdir()
    with gzip.open(tmp_path / "measurements/0003.json.gz", "wt") as handle:
        json.dump({"speed": 3.8656, "target_point": [19.5, -0.03], "target_point_next": [33.1, -13.0]}, handle)
    speed, target_points = variant_a.measurement_inputs(variant_a.read_measurement(tmp_path, "0003"))
    assert speed == 3.9 and target_points.tolist() == [[19.5, -0.03], [33.1, -13.0]]
    assert variant_a.driving_prompt(speed) == ("Current speed: 3.9 m/s. Target waypoint: "
                                               "<TARGET_POINT><TARGET_POINT>. Predict the waypoints.")


def test_gap_classes_are_the_tiers_in_the_gap_files():
    tiers = {gap["gap_id"]: gap["tier"] for name in ("practice_v2", "practice_v3")
             for gap in yaml.safe_load((ROOT / "gaps/practice" / f"{name}.yaml").read_text())["gaps"]}
    assert variant_a.GAP_CLASS == {gap_id: tiers[gap_id] for gap_id in variant_a.GAP_CLASS}


@pytest.mark.parametrize("overrides, reading", [
    ({}, variant_a.BELOW),
    ({"claim_b_holds": False}, variant_a.MATCHES),
    ({"b7_median": 0.7}, variant_a.MATCHES),
    ({"b7_recovers": False}, variant_a.BELOW),
    ({"b7_recovers": False, "methods_recover": False}, variant_a.NO_RECOVERY),
])
def test_gap_reading(overrides, reading):
    assert variant_a.gap_reading(evidence(**overrides)) == reading


def test_a_median_margin_of_exactly_the_margin_keeps_our_methods_ahead():
    assert variant_a.gap_reading(evidence(b7_median=0.65)) == variant_a.BELOW


def test_a_class_fires_only_when_all_its_gaps_match():
    matching, ahead = evidence(claim_b_holds=False), evidence()
    conditions = variant_a.stop_condition({"P4_camera_occlusion": matching, "P7_camera_freeze": ahead,
                                           "P19_wide_invading_turn": matching})
    assert conditions["T0_control"]["reading"] == variant_a.PARTIAL
    assert conditions["T2_interactional"]["reading"] == variant_a.FIRES
    assert variant_a.class_reading({"P4_camera_occlusion": variant_a.BELOW}) == variant_a.CLEAR


def test_a_class_where_nothing_recovers_is_not_a_clear():
    neither = evidence(b7_recovers=False, methods_recover=False, b7_best=0.339, b7_median=0.2, methods_best=0.275)
    conditions = variant_a.stop_condition({"P4_camera_occlusion": neither, "P7_camera_freeze": neither})
    assert conditions["T0_control"]["reading"] == variant_a.NO_RECOVERY != variant_a.CLEAR
    assert conditions["T0_control"]["scores"]["P7_camera_freeze"]["b7_best"] == 0.339
    assert conditions["T0_control"]["scores"]["P7_camera_freeze"]["methods_best"] == 0.275


def test_a_mixed_class_with_no_match_stays_clear_and_names_each_gap():
    gaps = {"P4_camera_occlusion": variant_a.BELOW, "P7_camera_freeze": variant_a.NO_RECOVERY}
    assert variant_a.class_reading(gaps) == variant_a.CLEAR


def test_a_score_just_under_the_line_cannot_fire_and_shows_beside_the_reading():
    close = evidence(b7_recovers=False, b7_best=0.49, b7_median=0.49, methods_best=0.5, methods_median=0.5, claim_b_holds=False)
    condition = variant_a.stop_condition({"P19_wide_invading_turn": close})["T2_interactional"]
    assert condition["reading"] == variant_a.CLEAR
    assert condition["scores"]["P19_wide_invading_turn"]["b7_best"] == 0.49


def stored_h12_evidence(gap_id, claim_b_holds):
    """What the rule reads from H12's stored numbers: Claim B is not stored, so the caller sets it."""
    methods = json.loads((ROOT / "docs/research/data/h12_layer10_plain.json").read_text())["methods"]
    b7 = [run["gaps"][gap_id] for run in methods.values() if run["family"] == "B7_pool" and run["counts"]]
    per_dictionary = {}
    for run in methods.values():
        if run["family"] in ("M1_raw", "M1_capped") and run["counts"]:
            record = run["gaps"][gap_id]
            per_dictionary[run["sae"]] = max(per_dictionary.get(run["sae"], 0.0), record["best_jaccard"])
    ours = list(per_dictionary.values())
    b7_scores = [record["best_jaccard"] for record in b7]
    return GapEvidence(any(record["recovers"] for record in b7), max(b7_scores), float(np.median(b7_scores)),
                       max(ours) >= 0.5, max(ours), float(np.median(ours)), claim_b_holds)


@pytest.mark.parametrize("claim_b_holds", [True, False])
def test_the_pool_arm_already_fires_on_stored_h12_data_whichever_way_claim_b_goes(claim_b_holds):
    """The protocol discloses this result. If it stops holding, the disclosure must change with it."""
    stored = stored_h12_evidence("P19_wide_invading_turn", claim_b_holds)
    assert stored.b7_best == 0.5
    assert stored.methods_median - stored.b7_median == pytest.approx(0.003, abs=0.001)
    assert variant_a.stop_condition({"P19_wide_invading_turn": stored})["T2_interactional"]["reading"] == variant_a.FIRES


def test_stored_h12_camera_gaps_read_no_recovery_with_b7_above_our_methods_on_p7():
    p4, p7 = (stored_h12_evidence(gap_id, False) for gap_id in ("P4_camera_occlusion", "P7_camera_freeze"))
    assert variant_a.stop_condition({"P4_camera_occlusion": p4, "P7_camera_freeze": p7})["T0_control"]["reading"] == variant_a.NO_RECOVERY
    assert p7.b7_best > p7.methods_best


def test_a_gap_with_no_class_is_an_error():
    with pytest.raises(KeyError):
        variant_a.stop_condition({"P99": evidence()})


def test_floors_make_variant_a_untested_rather_than_clear():
    assert variant_a.variant_a_tested(950, 9)
    assert not variant_a.variant_a_tested(949, 18)
    assert not variant_a.variant_a_tested(1000, 8)
    report = {"tested": {"A": False, "pool": True}, "evidence": {"A": {}, "pool": {GAP: vars(evidence())}}}
    assert read_rule.read_rule([report])["A"] == variant_a.UNTESTED


def plain_report(worst=0.0, compared=162, **overrides):
    return {"tested": {"A": True, "pool": True}, "training_routes": 1000,
            "dictionaries": [{"run": "L10_k32_s0", "training_explained_variance": 0.6}],
            "reproduces_stored": {"compared": compared, "worst_difference": worst},
            "evidence": {"A": {GAP: vars(evidence())}, "pool": {"P19_wide_invading_turn": vars(evidence(claim_b_holds=False))}},
            **overrides}


def test_the_file_labels_the_pool_arm_post_hoc_and_carries_the_lock_and_what_is_unsettled():
    written = read_rule.stop_condition_file([plain_report()], "abc123")
    assert written["rule_commit"] == "abc123"
    assert written["arms"]["pool"]["label"].startswith("post hoc")
    assert written["arms"]["A"]["label"].startswith("stated before its data")
    assert written["arms"]["pool"]["reading"]["T2_interactional"]["reading"] == variant_a.FIRES
    assert any("C34" in item for item in written["unsettled"])
    assert any("partial" in item for item in written["unsettled"])


@pytest.mark.parametrize("report", [plain_report(worst=0.02), plain_report(compared=0, worst=None)])
def test_the_file_refuses_when_stored_numbers_do_not_reproduce(report):
    with pytest.raises(ValueError):
        read_rule.stop_condition_file([report], "abc123")


def test_the_file_refuses_when_nothing_was_checked_against_stored_numbers():
    report = plain_report()
    del report["reproduces_stored"]
    with pytest.raises(ValueError):
        read_rule.stop_condition_file([report], "abc123")


def test_an_untested_variant_a_reports_explained_variance_per_dictionary():
    report = plain_report(tested={"A": False, "pool": True})
    arm = read_rule.stop_condition_file([report], "abc123")["arms"]["A"]
    assert arm["reading"] == variant_a.UNTESTED
    assert arm["why_untested"]["training_explained_variance"] == {"L10_k32_s0": 0.6}


@pytest.mark.parametrize("limit, minutes", [("3:30:00", 210), ("30:00", 30), ("1-00:00:00", 1440), ("0:01", 1)])
def test_limit_minutes_reads_squeue(limit, minutes):
    assert guard.limit_minutes(limit) == minutes


def test_limit_minutes_refuses_no_limit():
    with pytest.raises(ValueError):
        guard.limit_minutes("UNLIMITED")


def test_the_ledger_counts_a_running_job_at_its_whole_limit():
    rows = "COMPLETED|3600|210\nCANCELLED by 42|7200|210\nRUNNING|60|210\nPENDING|0|210\n"
    assert guard.committed_su(rows) == pytest.approx((1 + 2 + 3.5) * 29)


def test_six_full_capture_tasks_reach_the_cap_and_a_seventh_is_refused():
    mode = guard.MODES["capture"]
    six = "RUNNING|0|210\n" * 6
    assert guard.refusal(mode, "h16-capture", 210, guard.committed_su(six), 0) is None
    assert "cap" in guard.refusal(mode, "h16-capture", 210, guard.committed_su(six + "RUNNING|0|210\n"), 0)


@pytest.mark.parametrize("name, minutes, spent, size, word", [
    ("h16-capture", 211, 0, 0, "limit"),
    ("h16-other", 210, 0, 0, "name"),
    ("h16-capture", 210, 0, guard.MAX_TRAINING_BYTES + 1, "holds"),
])
def test_guard_refuses(name, minutes, spent, size, word):
    assert word in guard.refusal(guard.MODES["capture"], name, minutes, spent, size)


def test_every_mode_fits_one_full_run_inside_its_cap():
    for mode in guard.MODES.values():
        assert mode.max_minutes / 60 * guard.SU_PER_HOUR <= mode.cap_su


@pytest.mark.parametrize("name, mode", [("capture.sbatch", "$MODE"), ("score.sbatch", "score")])
def test_jobs_carry_a_default_limit_and_run_the_guard_before_real_work(name, mode):
    text = (HERE / name).read_text()
    assert "#SBATCH --time=" in text
    assert text.index("job_guard.py") < text.index("capture_training.py" if name == "capture.sbatch" else "score.py")
    assert mode in text


def locked_repo(tmp_path):
    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                       capture_output=True)
    run("init")
    for path in guard.LOCKED_FILES:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("rule\n")
    run("add", ".")
    run("commit", "-m", "lock")
    head = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    return head.stdout.strip()


def test_lock_holds_only_while_the_locked_files_match_their_commit(tmp_path):
    head = locked_repo(tmp_path)
    with pytest.raises(ValueError, match="not locked"):
        guard.locked_commit(tmp_path)
    (tmp_path / guard.LOCK_FILE).write_text(head + "\n")
    assert guard.locked_commit(tmp_path) == head
    (tmp_path / guard.LOCKED_FILES[0]).write_text("edited after the capture\n")
    with pytest.raises(ValueError, match="differs"):
        guard.locked_commit(tmp_path)


def test_lock_refuses_a_commit_without_the_file(tmp_path):
    locked_repo(tmp_path)
    (tmp_path / guard.LOCK_FILE).write_text("0" * 40 + "\n")
    with pytest.raises(ValueError, match="not in lock commit"):
        guard.locked_commit(tmp_path)


def bend_route(sideways):
    return np.stack([np.arange(1.0, 31.0), np.linspace(0.0, sideways, 30)], axis=1)


def test_route_check_needs_a_frame_on_a_real_bend():
    straight = {"route_bend_m": variant_a.route_bend_m(bend_route(0.1))}
    bend = {"route_bend_m": variant_a.route_bend_m(bend_route(13.0))}
    assert not variant_a.route_check_saw_a_bend([straight, straight])
    assert variant_a.route_check_saw_a_bend([straight, bend])


def test_stopwatch_finds_the_best_cut_of_longest_failures():
    frames = [score.Frames(name, np.zeros((length, 2)), np.arange(length), True, None)
              for name, length in (("a", 9), ("b", 8), ("c", 7), ("d", 1))]
    gap = score.Gap("G", "T0_control", {"a", "c"})
    assert score.stopwatch_jaccard(gap, frames, {"a", "b", "c", "d"}) == pytest.approx(2 / 3)


def write_shard(directory, route_id, base_id, *, success, frames, gaps=()):
    np.savez(directory / f"{route_id}.npz", driving_queries=frames.astype(np.float16), step=STEPS.astype(np.int32))
    (directory / f"{route_id}.json").write_text(json.dumps({
        "route_id": route_id, "base_id": base_id, "success": success, "first_collision_step": None if success else 100,
        "infractions": {}, "practice_gaps": list(gaps), "role": "pilot_slice" if gaps else None}))


def noise_frames(rng, spike=False):
    frames = rng.normal(size=(len(STEPS), LAYERS, HIDDEN))
    if spike:
        frames[5:8, 10, 0] += 12.0
    return frames


def write_dictionary(path):
    """Reconstructs exactly; unit 0's positive latent fires only on a spike, every other latent on most frames."""
    identity, pre_bias = torch.eye(HIDDEN), torch.zeros(HIDDEN)
    pre_bias[0] = 0.7
    model = sae.TopKSae(HIDDEN, 2 * HIDDEN, 2 * HIDDEN, pre_bias)
    model.encoder.data = torch.cat([identity, -identity])
    model.decoder.data = torch.cat([identity, -identity], dim=1)
    path.mkdir(parents=True)
    torch.save({"config": {"layer": 10, "k": 2 * HIDDEN, "seed": 0}, "state": model.state_dict()}, path / "sae.pt")


def write_training(directory, spiked_routes):
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(5)
    for index in range(20):
        frames = rng.normal(size=(len(STEPS), HIDDEN))
        if index in spiked_routes:
            frames[5:8, 0] += 12.0
        np.savez(directory / f"route{index}.npz", driving_queries=frames.astype(np.float16), frame=np.arange(len(STEPS)))


@pytest.fixture
def pool(tmp_path):
    shards = tmp_path / "shards"
    shards.mkdir()
    rng = np.random.default_rng(3)
    for index in range(12):
        write_shard(shards, f"gap{index}", f"b{index}", success=False, frames=noise_frames(rng, True), gaps=[GAP])
        write_shard(shards, f"other{index}", f"c{index}", success=False, frames=noise_frames(rng))
        write_shard(shards, f"ok{index}", f"d{index}", success=True, frames=noise_frames(rng))
    write_dictionary(tmp_path / "dictionary")
    return tmp_path


def run_score(root, training, **kwargs):
    with mock.patch.object(score, "read_route_list", lambda: [f"x/route{i}" for i in range(20)]):
        return score.evaluate([root / "shards"], training, [root / "dictionary"], [GAP], torch.device("cpu"),
                              kwargs.get("stale_latent", False), None, replicates=20)


def test_variant_a_ranks_from_training_frames_only(pool):
    write_training(pool / "seen", {0, 1, 2, 3})
    write_training(pool / "unseen", set())
    seen = run_score(pool, pool / "seen")
    unseen = run_score(pool, pool / "unseen")
    assert seen["evidence"]["A"][GAP]["b7_best"] == 1.0
    assert seen["dictionaries"][0]["latents_surviving_on_training"] == 1
    assert unseen["evidence"]["A"][GAP]["b7_best"] == 0.0
    assert not unseen["evidence"]["A"][GAP]["b7_recovers"]
    assert seen["evidence"]["pool"][GAP] == unseen["evidence"]["pool"][GAP]


def test_a_dictionary_that_does_not_fit_training_frames_stops_counting_for_variant_a_alone(pool):
    write_training(pool / "seen", {0, 1, 2, 3})
    real = score.dev_eval.encode_frames

    def poor_on_training(model, frames, device, stale_latent=False):
        rollouts, explained = real(model, frames, device, stale_latent)
        return rollouts, 0.5 if frames[0].rollout_id.startswith("route") else explained

    with mock.patch.object(score.dev_eval, "encode_frames", poor_on_training):
        report = run_score(pool, pool / "seen")
    counts = {row["family"]: row["counts"] for row in report["methods"].values()}
    assert counts == {"M1_raw": True, "M1_capped": True, "B7_A": False, "B7_pool": True}
    assert report["evidence"]["A"] == {} and report["evidence"]["pool"]
    assert report["tested"]["A"] is False


def test_post_hoc_output_holds_no_evidence_and_the_rule_refuses_it(pool):
    write_training(pool / "seen", {0, 1, 2, 3})
    report = run_score(pool, pool / "seen", stale_latent=True)
    assert report["label"].startswith("post hoc") and "evidence" not in report
    with pytest.raises(ValueError):
        read_rule.read_rule([report])


def test_the_rule_reads_plain_evidence_per_class(pool):
    write_training(pool / "seen", {0, 1, 2, 3})
    report = json.loads(json.dumps(run_score(pool, pool / "seen"), default=str))
    assert all(type(item[name]) is bool for item in report["evidence"]["pool"].values()
               for name in ("b7_recovers", "methods_recover", "claim_b_holds"))
    reading = read_rule.read_rule([report])
    assert reading["A"] == variant_a.UNTESTED
    assert set(reading["pool"]) == {"T0_control"} and set(reading["pool"]["T0_control"]["gaps"]) == {GAP}


def test_the_rule_joins_gaps_across_reports():
    plain = {"tested": {"A": True, "pool": True}, "evidence": {"A": {"P4_camera_occlusion": vars(evidence())}, "pool": {}}}
    matching = vars(evidence(claim_b_holds=False))
    extended = {"tested": {"A": True, "pool": True}, "evidence": {"A": {"P8_camera_latency": matching}, "pool": {}}}
    reading = read_rule.read_rule([plain, extended])["A"]["T0_control"]
    assert reading["reading"] == variant_a.PARTIAL and set(reading["gaps"]) == {"P4_camera_occlusion", "P8_camera_latency"}


def test_scoring_job_never_globs_the_pilot_folders():
    lines = [line for line in (HERE / "score.sbatch").read_text().splitlines() if not line.startswith("#")]
    assert not any("step5-pilot-*" in line or "p20" in line.lower() for line in lines)
