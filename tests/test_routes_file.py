"""A rollout config can name its own routes file and take its route list from a manifest."""
import json

import pytest
import yaml

import route_run
from route_run import ROOT, Ports, check_route, configured_route_ids, evaluator_command, route_from_xml, routes_file

PINNED = '<routes><route id="1" town="Town12"><waypoints/><scenarios><scenario type="Accident"/></scenarios></route></routes>'
CUSTOM = '<routes><route id="7" town="Town05"><waypoints/><scenarios><scenario type="ControlLoss"/></scenarios></route></routes>'


@pytest.fixture
def files(tmp_path, monkeypatch):
    pinned, custom = tmp_path / "pinned.xml", tmp_path / "custom.xml"
    pinned.write_text(PINNED)
    custom.write_text(CUSTOM)
    monkeypatch.setattr(route_run, "ROUTES", pinned)
    return pinned, custom


def config_for(routes_path=None, **route):
    return {"route": ({"routes_file": str(routes_path)} if routes_path else {}) | {"seed": 1, **route},
            "simulator": {"timeout_seconds": 600}}


def test_config_without_a_routes_file_uses_the_pinned_one(files):
    pinned, _custom = files
    assert routes_file(None) == routes_file(config_for()) == pinned


def test_routes_file_is_resolved_against_the_repository_root():
    assert routes_file({"route": {"routes_file": "configs/rollout/step4-dev-pool.xml"}}) \
        == ROOT / "configs/rollout/step4-dev-pool.xml"


def test_route_is_looked_up_in_the_configs_routes_file(files):
    _pinned, custom = files
    assert route_from_xml("7", config_for(custom)) == {"id": "7", "town": "Town05", "scenario": "ControlLoss"}
    assert route_from_xml("1") == {"id": "1", "town": "Town12", "scenario": "Accident"}
    with pytest.raises(ValueError, match="not in the pinned routes file"):
        route_from_xml("7")
    with pytest.raises(ValueError, match="custom.xml"):
        route_from_xml("1", config_for(custom))


def test_check_route_reads_the_configs_routes_file(files):
    _pinned, custom = files
    check_route(config_for(custom, id="7", town="Town05", scenario="ControlLoss"))
    with pytest.raises(ValueError, match="town differs"):
        check_route(config_for(custom, id="7", town="Town04", scenario="ControlLoss"))
    with pytest.raises(ValueError, match="does not match"):
        check_route(config_for(custom, id="7", town="Town05", scenario="Accident"))
    with pytest.raises(ValueError, match="missing"):
        check_route(config_for(None, id="7", town="Town05", scenario="ControlLoss"))


def test_evaluator_is_given_the_configs_routes_file(files, tmp_path):
    pinned, custom = files

    def routes_argument(config):
        command = evaluator_command(tmp_path, config, Ports(rpc=2000, traffic_manager=8000), 4)
        return command[command.index("--routes") + 1]

    assert routes_argument(config_for(custom, id="7")) == str(custom)
    assert routes_argument(config_for(None, id="1")) == str(pinned)


def test_route_ids_come_from_the_manifest_unless_the_config_lists_routes(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"id": "7"}, {"id": "9"}]))
    assert configured_route_ids({"route": {"manifest": str(manifest)}}) == ["7", "9"]
    assert configured_route_ids({"routes": ["3"], "route": {"manifest": str(manifest)}}) == ["3"]


def test_committed_dev_pool_routes_resolve_through_its_config():
    config = yaml.safe_load((ROOT / "configs/rollout/step4-dev-pool.yaml").read_text())
    assert "routes" not in config
    ids = configured_route_ids(config)
    assert len(ids) == 190 and len(set(ids)) == 190
    manifest = {entry["id"]: entry for entry in json.loads((ROOT / config["route"]["manifest"]).read_text())}
    for route_id in ids:
        config["route"].update(route_from_xml(route_id, config))
        assert config["route"]["scenario"] == manifest[route_id]["scenario"]
        assert config["route"]["town"] == manifest[route_id]["town"]
        check_route(config)
