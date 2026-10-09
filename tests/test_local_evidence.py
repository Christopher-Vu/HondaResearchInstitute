"""A process exit or partial drive must never count as experiment readiness."""
import json

import pytest

from adapters.simlingo.run_local import summarize
from adapters.simlingo import run_local


def test_map_installation_blocks_launch_before_any_server_is_started(tmp_path, monkeypatch):
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime/maps-installing").touch()
    monkeypatch.setattr(run_local, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="map installation is in progress"):
        run_local.preflight({})


def write_run(path, status="Perfect", entry="Finished", log="", throttle=0.4):
    record = {"status": status, "meta": {"duration_game": 10, "duration_system": 100},
              "infractions": {"collisions_vehicle": []}}
    (path / "result.json").write_text(json.dumps({"entry_status": entry,
                                                "_checkpoint": {"records": [record]}}))
    (path / "evaluator.log").write_text(log)
    (path / "controls.jsonl").write_text(json.dumps({"model_inference": True,
                                                    "throttle": throttle}) + "\n")


@pytest.mark.parametrize("status", ["Failed - Agent crashed", "Failed - Simulation crashed", "Started"])
def test_partial_drives_are_rejected(tmp_path, status):
    write_run(tmp_path, status=status)
    with pytest.raises(RuntimeError, match="valid driving outcome"):
        summarize(tmp_path, {"scope": "local"}, {})
    assert not (tmp_path / "readiness.json").exists()


def test_missing_scenario_is_rejected(tmp_path):
    write_run(tmp_path, log="Skipping scenario 'SignalizedJunctionRightTurn_1'")
    with pytest.raises(RuntimeError, match="scenario was skipped"):
        summarize(tmp_path, {"scope": "local"}, {})


def test_no_model_throttle_is_rejected(tmp_path):
    write_run(tmp_path, throttle=0)
    with pytest.raises(RuntimeError, match="model-driven throttle"):
        summarize(tmp_path, {"scope": "local"}, {})


def test_driving_failure_is_distinct_from_integration_failure(tmp_path):
    write_run(tmp_path, status="Failed - Agent got blocked")
    report = summarize(tmp_path, {"scope": "local"}, {})
    assert report["integration_verified"]
    assert not report["route_completed"]
    assert report["real_time_factor"] == 0.1
    assert report["whole_stack_peak_vram"] is None
    assert not report["savio_verified"]


def test_completed_route_retains_infractions(tmp_path):
    write_run(tmp_path, status="Completed")
    report = summarize(tmp_path, {"scope": "local"}, {})
    assert report["route_completed"]
    assert report["infractions"] == {"collisions_vehicle": []}
