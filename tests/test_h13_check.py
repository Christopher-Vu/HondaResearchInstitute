"""H13's check must refuse on missing data rather than read it as a failed manipulation, and must hold to Step 1's numbers."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from PIL import Image

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs/research/experiments"
CHECK_SCRIPT = EXPERIMENTS / "h13-cross-family-gap/check.py"
BOX = [0.0, 0.25, 0.45, 0.65]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h7_check = load("h7_check", EXPERIMENTS / "h7-traffic-pressure/check.py")
manipulation_check = load("manipulation_check", EXPERIMENTS / "h5-interactional-screen/manipulation_check.py")
with mock.patch.dict(sys.modules, {"check": h7_check, "manipulation_check": manipulation_check}), mock.patch.object(sys, "path", list(sys.path)):
    h13_check = load("h13_check", CHECK_SCRIPT)


def slice_row(route_id, job="1", **overrides):
    return {"id": route_id, "job": job, "role": "pilot_slice", "success": True, "has_shard": True, "scenario_dropped": False,
            "trigger_miss_m": 1.0, "most_vehicles_50m": 2, "lowest_black_fraction": 1.0, **overrides}


def write_task_log(folder, job, *route_ids):
    (folder / f"route-sample-{job}_0.out").write_text("".join(f"=== route {route_id} (array task 0)\n" for route_id in route_ids))


def five_rows():
    return {str(route_id): slice_row(str(route_id)) for route_id in range(5)}


@pytest.mark.parametrize("rows, logged, refusal", [
    ({}, ["0"], "missing"),
    ({**five_rows(), "0": slice_row("0", has_shard=False)}, list("01234"), "without_shard"),
    (five_rows(), list("0123"), "not_in_task_logs"),
    ({key: row for key, row in five_rows().items() if key != "4"}, list("0123"), "fewer_than_first_routes"),
    ({**five_rows(), "0": slice_row("0", lowest_black_fraction=None)}, list("01234"), "first_routes_without_frames"),
])
def test_missing_data_refuses(tmp_path, monkeypatch, rows, logged, refusal):
    monkeypatch.chdir(tmp_path)
    write_task_log(tmp_path, "1", *logged)
    with pytest.raises(SystemExit, match=refusal) as refused:
        h13_check.scored_slices_in_run_order(rows, "1")
    if refusal != "missing":
        assert f"'{refusal}': []" not in str(refused.value) and f"'{refusal}': False" not in str(refused.value)


def test_a_missing_first_array_log_refuses_even_when_a_retry_covers_every_route(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task_log(tmp_path, "2", *"43210")
    rows = {key: {**row, "job": "2"} for key, row in five_rows().items()}
    with pytest.raises(SystemExit, match="'first_array_log_missing': True"):
        h13_check.scored_slices_in_run_order(rows, "1")


def test_a_rerun_keeps_its_first_array_position_and_counts_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task_log(tmp_path, "1", "5", "0", "1", "2", "3", "4")
    write_task_log(tmp_path, "2", "0")
    rows = {**five_rows(), "0": slice_row("0", job="2"), "5": slice_row("5")}
    assert [row["id"] for row in h13_check.scored_slices_in_run_order(rows, "1")] == ["5", "0", "1", "2", "3", "4"]


def test_the_first_array_decides_the_order_even_when_every_row_comes_from_a_retry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task_log(tmp_path, "1", *"01234")
    write_task_log(tmp_path, "2", *"43210")
    rows = {key: {**row, "job": "2"} for key, row in five_rows().items()}
    assert [row["id"] for row in h13_check.scored_slices_in_run_order(rows, "1")] == list("01234")


def test_only_scored_slices_enter_the_check(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task_log(tmp_path, "1", *"0123456")
    rows = {**five_rows(), "5": slice_row("5", success=None), "6": slice_row("6", role="pilot_neighbourhood")}
    assert [row["id"] for row in h13_check.scored_slices_in_run_order(rows, "1")] == list("01234")


def test_a_failed_drive_is_still_scored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task_log(tmp_path, "1", *"01234")
    rows = {**five_rows(), "0": slice_row("0", success=False)}
    assert len(h13_check.scored_slices_in_run_order(rows, "1")) == 5


@pytest.mark.parametrize("black, holds", [(0.99, True), (0.9899, False)])
def test_the_black_check_needs_99_percent_on_each_of_the_first_five(black, holds):
    scored = [slice_row(str(index)) for index in range(4)] + [slice_row("4", lowest_black_fraction=black)]
    assert h13_check.check_summary({row["id"]: row for row in scored}, scored)["black_holds"] is holds


def test_the_black_check_reads_only_the_first_five():
    scored = [slice_row(str(index)) for index in range(5)] + [slice_row("5", lowest_black_fraction=0.0)]
    assert h13_check.check_summary({row["id"]: row for row in scored}, scored)["black_holds"] is True


@pytest.mark.parametrize("meeting, holds", [(7, True), (6, False)])
def test_traffic_needs_70_percent_of_scored_slices(meeting, holds):
    scored = [slice_row(str(index), trigger_miss_m=1.0 if index < meeting else 9.0) for index in range(10)]
    summary = h13_check.check_summary({row["id"]: row for row in scored}, scored)
    assert summary["meeting_traffic"] == meeting and summary["traffic_holds"] is holds


def test_a_dropped_scenario_does_not_count_as_meeting_traffic():
    scored = [slice_row("7"), slice_row("8", scenario_dropped=True)]
    summary = h13_check.check_summary({row["id"]: row for row in scored}, scored)
    assert summary["meeting_traffic"] == 1 and summary["scenarios_dropped"] == ["8"]


def test_one_unreadable_state_sample_neither_crashes_nor_moves_the_trigger(tmp_path):
    shard = tmp_path / "route.npz"
    np.savez(shard, ego_x=np.array([np.nan, 5.0, 0.0, 9.0]), ego_y=np.zeros(4), ego_speed=np.array([np.nan, 1.0, 2.0, 3.0]),
             vehicles_50m=np.array([np.nan, 0.0, 4.0, 1.0]), lead_relative_speed=np.full(4, np.nan))
    result = h7_check.encounter(shard, (0.0, 0.0))
    assert result["trigger_miss_m"] == 0.0 and result["speed_at_trigger"] == 2.0
    assert result["most_vehicles_50m"] == 4 and result["state_error_samples"] == 1


def small_tree(root, route_ids=tuple("12345")):
    """A pilot of five slices driven by job 1, each with a black box, a shard at its trigger and a failed drive."""
    (root / "configs/rollout").mkdir(parents=True)
    shards = root / "results/savio/c/shards"
    shards.mkdir(parents=True)
    manifest, routes, xml = [], [], []
    frame = np.full((100, 100), 200, dtype=np.uint8)
    frame[25:65, :45] = 0
    for route_id in route_ids:
        manifest.append({"id": route_id, "base_id": route_id, "scenario": "S", "role": "pilot_slice",
                         "weather": {"sun_altitude_angle": 30}, "sensor": {"camera_fault": {"box": BOX}}})
        routes.append({"id": route_id, "job": "1", "success": False, "status": "Failed", "infractions": {"collisions_vehicle": 1}})
        xml.append(f'<route id="{route_id}"><scenarios><scenario><trigger_point x="0" y="0"/></scenario></scenarios></route>')
        frames = root / f"results/savio/1/route-{route_id}/frames"
        frames.mkdir(parents=True)
        Image.fromarray(frame).save(frames / "000000.png")
        np.savez(shards / f"{route_id}.npz", ego_x=np.zeros(3), ego_y=np.zeros(3), ego_speed=np.ones(3), vehicles_50m=np.full(3, 2.0),
                 lead_relative_speed=np.full(3, np.nan))
    (root / "configs/rollout/c.manifest.json").write_text(json.dumps(manifest))
    (root / "configs/rollout/c.xml").write_text(f"<routes>{''.join(xml)}</routes>")
    (root / "results/savio/c/routes.jsonl").write_text("".join(json.dumps(row) + "\n" for row in routes))
    write_task_log(root, "1", *route_ids)


def run_script(root):
    return subprocess.run([sys.executable, str(CHECK_SCRIPT), "c", "1", "out.json"], cwd=root, capture_output=True, text=True)


def test_the_script_runs_and_prints_only_the_check(tmp_path):
    small_tree(tmp_path)
    done = run_script(tmp_path)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"first_routes": list("12345"), "black_holds": True, "meeting_traffic": 5, "scored_slices": 5,
                                       "traffic_holds": True, "scenarios_dropped": [], "state_error_samples": 0}
    assert json.loads((tmp_path / "out.json").read_text())["routes"][0]["success"] is False


def test_the_script_refuses_when_a_first_route_has_no_frames(tmp_path):
    small_tree(tmp_path)
    (tmp_path / "results/savio/1/route-3/frames/000000.png").unlink()
    done = run_script(tmp_path)
    assert done.returncode != 0 and "first_routes_without_frames" in done.stderr and not done.stdout
