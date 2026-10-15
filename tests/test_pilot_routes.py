"""The Step 5 pilot generator: pairs on distinct base routes that differ only in the planted weather."""
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

import pilot_routes
from harness.predicates import matches

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rollout/step5-pilot-p3.yaml"


@pytest.fixture(scope="module")
def config():
    loaded = yaml.safe_load(CONFIG.read_text())
    if not (ROOT / loaded["pilot"]["base_routes_file"]).is_file():
        pytest.skip("pinned routes file not installed")
    return loaded


@pytest.fixture(scope="module")
def pilot(config):
    return pilot_routes.generate(config)


def test_each_of_sixty_base_routes_has_one_slice_and_one_neighbourhood_route(pilot):
    _document, entries = pilot
    assert Counter(entry["role"] for entry in entries) == {"pilot_slice": 60, "pilot_neighbourhood": 60}
    assert set(Counter(entry["base_id"] for entry in entries).values()) == {2}


def test_a_pair_differs_only_in_fog(pilot):
    _document, entries = pilot
    by_base = {}
    for entry in entries:
        by_base.setdefault(entry["base_id"], {})[entry["role"]] = entry
    for pair in by_base.values():
        fog, clear = pair["pilot_slice"], pair["pilot_neighbourhood"]
        changed = {name for name in fog["weather"] if fog["weather"][name] != clear["weather"][name]}
        assert changed == {"fog_density"}
        assert (fog["town"], fog["scenario"], fog["param"]) == (clear["town"], clear["scenario"], clear["param"])


def test_the_gap_predicate_matches_the_slice_and_nothing_else(config, pilot):
    _document, entries = pilot
    gaps = yaml.safe_load((ROOT / config["pilot"]["practice_gaps"]).read_text())["gaps"]
    gap = next(gap for gap in gaps if gap["gap_id"] == config["pilot"]["gap_id"])
    assert {entry["id"] for entry in entries if matches(gap["predicate"], entry)} == {
        entry["id"] for entry in entries if entry["role"] == "pilot_slice"}


def test_no_stock_daytime_preset_falls_in_the_gap(config):
    gaps = yaml.safe_load((ROOT / config["pilot"]["practice_gaps"]).read_text())["gaps"]
    gap = next(gap for gap in gaps if gap["gap_id"] == config["pilot"]["gap_id"])
    import dev_routes
    for name in dev_routes.PRESET_VALUES:
        assert not matches(gap["predicate"], {"weather": dev_routes.preset_weather(name)}), name


def test_committed_files_are_what_the_generator_writes(config, pilot):
    document, entries = pilot
    assert (ROOT / config["route"]["routes_file"]).read_text() == document
    assert json.loads((ROOT / config["route"]["manifest"]).read_text()) == entries


def load(name):
    loaded = yaml.safe_load((ROOT / f"configs/rollout/{name}.yaml").read_text())
    if not (ROOT / loaded["pilot"]["base_routes_file"]).is_file():
        pytest.skip("pinned routes file not installed")
    return loaded, pilot_routes.generate(loaded)


def test_camera_fault_pairs_differ_only_in_the_sensor_setting():
    _config, (_document, entries) = load("step5-pilot-p4-screen")
    for entry in entries:
        assert ("sensor" in entry) == (entry["role"] == "pilot_slice")
        assert entry["weather"] == entries[0]["weather"]


def test_pedestrians_are_appended_after_the_authored_scenario_at_the_route_start():
    import xml.etree.ElementTree as ET
    _config, (document, entries) = load("step5-pilot-p5-screen")
    routes = {route.get("id"): route for route in ET.fromstring(document).iter("route")}
    for entry in entries:
        scenarios = routes[entry["id"]].findall("scenarios/scenario")
        injected = entry["role"] == "pilot_slice"
        assert len(scenarios) == 1 + injected and scenarios[0].get("type") == entry["scenario"]
        if injected:
            first = routes[entry["id"]].find("waypoints/position")
            trigger = scenarios[1].find("trigger_point")
            assert scenarios[1].get("type") == "PedestriansOnRoad"
            assert (trigger.get("x"), trigger.get("y")) == (str(float(first.get("x"))), str(float(first.get("y"))))
            assert set(scenarios[1].find("pedestrians").attrib) == {"a", "b", "c"}
        assert pilot_routes.route_length(routes[entry["id"]]) >= 70


def test_screen_and_full_pilot_never_share_a_base_route():
    for gap in ("p4", "p5", "p6"):
        screen = {entry["base_id"] for entry in load(f"step5-pilot-{gap}-screen")[1][1]}
        main = {entry["base_id"] for entry in load(f"step5-pilot-{gap}-main")[1][1]}
        assert len(screen) == 10 and len(main) == 60 and not screen & main


def test_no_two_committed_manifests_share_a_route_id():
    ids = [entry["id"] for path in (ROOT / "configs/rollout").glob("*.manifest.json")
           for entry in json.loads(path.read_text())]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("name", ["step5-pilot-p4-screen", "step5-pilot-p4-main", "step5-pilot-p5-screen",
                                  "step5-pilot-p5-main", "step5-pilot-p6-screen", "step5-pilot-p6-main"])
def test_committed_pilot_files_are_what_the_generator_writes(name):
    config, (document, entries) = load(name)
    assert (ROOT / config["route"]["routes_file"]).read_text() == document
    assert json.loads((ROOT / config["route"]["manifest"]).read_text()) == entries


def test_animal_pairs_differ_only_in_what_crosses_and_animals_rotate():
    config, (_document, entries) = load("step5-pilot-p6-main")
    assert config["simulator"]["carla_build"] == "fail2drive"
    by_base = {}
    for entry in entries:
        by_base.setdefault(entry["base_id"], {})[entry["role"]] = entry
    animals = set()
    for pair in by_base.values():
        animal, person = pair["pilot_slice"]["injected_parameters"], pair["pilot_neighbourhood"]["injected_parameters"]
        assert animal["walker"].startswith("walker.animal.") and person["walker"].startswith("walker.pedestrian.")
        assert {**animal, "walker": None} == {**person, "walker": None}
        animals.add(animal["walker"])
    assert len(animals) == 3

