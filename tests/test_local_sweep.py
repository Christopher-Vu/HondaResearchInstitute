"""The local sweep's sample and scoring rules, which its overnight numbers depend on."""
import json

import pytest

from adapters.simlingo import route_run, sweep_local

ROUTES = """<routes>
<route id="1" town="Town12"><waypoints/><scenarios><scenario type="Accident"/></scenarios></route>
<route id="2" town="Town13"><waypoints/><scenarios><scenario type="Accident"/></scenarios></route>
<route id="3" town="Town05"><waypoints/><scenarios><scenario type="ControlLoss"/></scenarios></route>
<route id="4" town="Town01"><waypoints/><scenarios><scenario type="HighwayExit"/></scenarios></route>
</routes>"""


@pytest.fixture
def routes_file(tmp_path, monkeypatch):
    path = tmp_path / "routes.xml"
    path.write_text(ROUTES)
    monkeypatch.setattr(sweep_local, "ROUTES", path)
    monkeypatch.setattr(route_run, "ROUTES", path)
    return path


def test_sample_takes_one_route_per_scenario_type_and_is_seeded(routes_file):
    plan = sweep_local.sample_routes(0)
    assert sorted(route["scenario"] for route in plan) == ["Accident", "ControlLoss", "HighwayExit"]
    assert plan == sweep_local.sample_routes(0)


def test_route_override_reads_town_and_scenario_from_the_pinned_file(routes_file):
    assert route_run.route_from_xml("3") == {"id": "3", "town": "Town05", "scenario": "ControlLoss"}
    with pytest.raises(ValueError, match="not in the pinned routes file"):
        route_run.route_from_xml("99")


def write_result(path, status, infractions):
    path.mkdir()
    record = {"status": status, "scores": {"score_route": 100, "score_penalty": 1.0, "score_composed": 100.0},
              "meta": {"route_length": 70.0, "duration_game": 10.0, "duration_system": 200.0},
              "infractions": infractions}
    (path / "result.json").write_text(json.dumps({"_checkpoint": {"records": [record]}}))


def test_minimum_speed_infractions_do_not_cost_success(tmp_path):
    write_result(tmp_path / "run", "Completed", {"min_speed_infractions": ["slow"] * 16})
    row = sweep_local.route_record({"id": "1"}, tmp_path / "run", 0, 250.0, 1)
    assert row["success"] and row["infractions"] == {}


def test_counted_infraction_fails_a_completed_route(tmp_path):
    write_result(tmp_path / "run", "Completed", {"collisions_vehicle": ["hit"]})
    row = sweep_local.route_record({"id": "1"}, tmp_path / "run", 0, 250.0, 1)
    assert not row["success"] and row["infractions"] == {"collisions_vehicle": 1}


def test_wall_capped_route_is_unscored_not_failed(tmp_path):
    (tmp_path / "run").mkdir()
    (tmp_path / "run.launcher.log").write_text("Starting CARLA\nSimLingo step 9000\n")
    row = sweep_local.route_record({"id": "1", "scenario": "Accident"}, tmp_path / "run", None, 2100.0, 1)
    summary = sweep_local.summarize([row])
    assert row["wall_capped"] and "score_composed" not in row
    assert summary["routes_scored"] == 0 and summary["unscored"][0]["wall_capped"]


def test_stationary_time_is_the_longest_still_run_in_simulated_seconds(tmp_path):
    speeds = [0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 2.0]
    (tmp_path / "controls.jsonl").write_text("".join(
        json.dumps({"simulation_seconds": 0.5 * i, "speed_metres_per_second": v}) + "\n"
        for i, v in enumerate(speeds)))
    assert sweep_local.longest_stationary_seconds(tmp_path / "controls.jsonl") == 1.0
    assert sweep_local.longest_stationary_seconds(tmp_path / "missing.jsonl") == 0.0
