"""Step 2 scoring rules: which attempt counts, and what reaches Bench2Drive's official merge."""
import json

import pytest

import route_run
import score_routes

ROUTES = """<routes>
<route id="1" town="Town12"><waypoints/><scenarios><scenario type="Accident"/></scenarios></route>
<route id="2" town="Town13"><waypoints/><scenarios><scenario type="InterurbanActorFlow"/></scenarios></route>
<route id="3" town="Town05"><waypoints/><scenarios><scenario type="ControlLoss"/></scenarios></route>
</routes>"""


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    routes = tmp_path / "routes.xml"
    routes.write_text(ROUTES)
    monkeypatch.setattr(route_run, "ROUTES", routes)
    if not score_routes.MERGE_SCRIPT.is_file():
        pytest.skip("Bench2Drive source not installed")
    config = tmp_path / "config.yaml"
    config.write_text('name: test\nroutes: ["1", "2", "3"]\n')
    return tmp_path, config


def attempt(job, route_id, status, composed, log=""):
    path = job / f"route-{route_id}"
    path.mkdir(parents=True)
    record = {"index": 0, "route_id": f"RouteScenario_{route_id}", "status": status,
              "scores": {"score_route": composed, "score_penalty": 1.0, "score_composed": composed},
              "meta": {"duration_game": 10.0, "duration_system": 200.0}, "infractions": {}}
    (path / "result.json").write_text(json.dumps({"_checkpoint": {"records": [record]}}))
    (path / "evaluator.log").write_text(log)


def test_first_driving_outcome_wins_and_crashes_go_to_rerun(campaign):
    root, config = campaign
    first, retry = root / "100", root / "101"
    attempt(first, "1", "Completed", 100.0)
    attempt(retry, "1", "Failed - Agent got blocked", 40.0)
    attempt(first, "2", "Failed - Agent crashed", 5.0)
    attempt(retry, "2", "Completed", 80.0, "Skipping scenario 'InterurbanActorFlow_1'\n")
    attempt(first, "3", "Failed - Simulation crashed", 0.0)
    report = score_routes.score(config, [retry, first], root / "out")
    assert [row["id"] for row in report["rerun"]] == ["3"] and report["not_run"] == []
    assert report["official"]["eval num"] == 2
    assert report["official"]["driving score"] == pytest.approx(90.0)
    assert report["clean"]["routes_scored"] == 1 and report["scenario_skipped"] == ["2"]


def test_routes_never_attempted_are_not_reruns(campaign):
    root, config = campaign
    attempt(root / "100", "1", "Completed", 100.0)
    report = score_routes.score(config, [root / "100"], root / "out")
    assert report["rerun"] == [] and report["not_run"] == ["2", "3"]
