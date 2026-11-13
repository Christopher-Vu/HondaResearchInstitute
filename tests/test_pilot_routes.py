"""The Step 5 pilot generator: pairs on distinct base routes that differ only in the planted weather."""
import importlib.util
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pytest
import yaml

import cut_routes
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
    """An amended screen re-lists its original's routes on purpose; its new ids are checked with it. Fail2Drive's routes
    keep Fail2Drive's own ids, so its screen and its full set share them by design and are checked one manifest at a time."""
    manifests = [json.loads(path.read_text()) for path in (ROOT / "configs/rollout").glob("*.manifest.json")
                 if not path.name.endswith("-amended.manifest.json")]
    ours = [entry["id"] for manifest in manifests for entry in manifest if entry.get("source") != "fail2drive"]
    assert len(ours) == len(set(ours))
    for manifest in manifests:
        theirs = [entry["id"] for entry in manifest if entry.get("source") == "fail2drive"]
        assert len(theirs) == len(set(theirs))
    fail2drive = {entry["id"] for manifest in manifests for entry in manifest if entry.get("source") == "fail2drive"}
    assert not fail2drive & set(ours)


def amended_p20_screen():
    original = ROOT / "configs/rollout/step5-pilot-p20-screen"
    amended = ROOT / "configs/rollout/step5-pilot-p20-screen-amended"
    return tuple({route.get("id"): route for route in ET.parse(f"{path}.xml").getroot().iter("route")} for path in (original, amended)), tuple(
        {entry["id"]: entry for entry in json.loads(Path(f"{path}.manifest.json").read_text())} for path in (original, amended))


def test_the_amended_p20_screen_changes_only_the_three_recut_pairs():
    (old_routes, new_routes), (old_entries, new_entries) = amended_p20_screen()
    kept = set(old_routes) & set(new_routes)
    assert len(new_routes) == len(new_entries) == 20 and len(kept) == 14
    assert all(ET.tostring(old_routes[route_id]) == ET.tostring(new_routes[route_id]) and old_entries[route_id] == new_entries[route_id]
               for route_id in kept)
    recut = {route_id: entry for route_id, entry in new_entries.items() if "recut_of" in entry}
    assert {entry["recut_of"] for entry in recut.values()} == {"64155", "64223", "64250"} and len(recut) == 6
    for route_id, entry in recut.items():
        old_id = entry["recut_of"] + route_id[-2:]
        assert {**entry, "id": old_id, "base_id": entry["recut_of"]} == {**old_entries[old_id], "recut_of": entry["recut_of"]}
        old, new = old_routes[old_id], new_routes[route_id]
        assert ET.tostring(old.find("scenarios")) == ET.tostring(new.find("scenarios"))
        assert ET.tostring(old.find("weathers")) == ET.tostring(new.find("weathers"))
        assert pilot_routes.waypoints(new)[:2] == pilot_routes.waypoints(old) and len(pilot_routes.waypoints(new)) == 3


def test_recut_ids_are_new_and_both_arms_drive_one_road_past_the_hazard():
    (_old, new_routes), (_entries, new_entries) = amended_p20_screen()
    recut = [route_id for route_id, entry in new_entries.items() if "recut_of" in entry]
    elsewhere = {entry["id"] for path in (ROOT / "configs/rollout").glob("*.manifest.json") if not path.name.endswith("-amended.manifest.json")
                 for entry in json.loads(path.read_text())}
    assert not set(recut) & elsewhere
    for slice_id in (route_id for route_id in recut if route_id.endswith("39")):
        arm = new_routes[slice_id]
        assert pilot_routes.waypoints(arm) == pilot_routes.waypoints(new_routes[slice_id[:-2] + "49"])
        scenario = next(arm.iter("scenario"))
        hazard = float(scenario.find("distance").get("value")) + float(getattr(scenario.find("bicycle_drive_distance"), "attrib", {}).get("value", 0))
        assert math.dist(pilot_routes.waypoints(arm)[-1][:2], cut_routes.trigger_of(scenario)) >= hazard + 60


@pytest.mark.parametrize("name", ["step5-pilot-p4-screen", "step5-pilot-p4-main", "step5-pilot-p5-screen",
                                  "step5-pilot-p5-main", "step5-pilot-p6-screen", "step5-pilot-p6-main",
                                  "step5-pilot-p7-screen", "step5-pilot-p8-screen", "step5-pilot-p9-screen",
                                  "step5-pilot-p20-screen"])
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



def test_trigger_after_m_moves_the_trigger_along_the_route():
    import xml.etree.ElementTree as ET
    route = ET.fromstring('<route><waypoints>' + "".join(
        '<position x="%d" y="0" z="0"/>' % x for x in (0, 30, 60, 90, 120)) + '</waypoints></route>')
    at_start = pilot_routes.injected_scenario(route, {"type": "HardBreakRoute"}, 0).find("trigger_point")
    later = pilot_routes.injected_scenario(route, {"type": "HardBreakRoute", "trigger_after_m": 50}, 0)
    assert at_start.get("x") == "0.0" and later.find("trigger_point").get("x") == "60.0"
    far = pilot_routes.injected_scenario(route, {"type": "HardBreakRoute", "trigger_after_m": 500}, 0)
    assert far.find("trigger_point").get("x") == "90.0" and far.find("trigger_point").get("yaw") == "0.0"


def test_include_scenarios_restricts_the_base_routes_to_those_families():
    config, (_document, entries) = load("step5-pilot-p9-screen")
    gap = {g["gap_id"]: g for g in yaml.safe_load((ROOT / config["pilot"]["practice_gaps"]).read_text())["gaps"]}[
        config["pilot"]["gap_id"]]
    assert len(entries) == 20
    assert {entry["scenario"] for entry in entries} <= set(gap["plant"]["include_scenarios"])
    assert all("Signalized" in entry["scenario"] or "RedLight" in entry["scenario"] for entry in entries)


def test_an_even_screen_takes_two_from_each_family_and_shares_weather_within_a_pair():
    _config, (_document, entries) = load("step5-pilot-p20-screen")
    slices = [entry for entry in entries if entry["role"] == "pilot_slice"]
    assert set(Counter(entry["scenario"] for entry in slices).values()) == {2} and len(slices) == 10
    weather = {entry["base_id"]: entry["weather"] for entry in slices}
    assert len({str(value) for value in weather.values()}) > 1
    for entry in entries:
        assert entry["weather"] == weather[entry["base_id"]]
        assert ("left" if entry["sensor"]["camera_fault"]["box"][0] == 0.0 else "right") == (
            "left" if entry["role"] == "pilot_slice" else "right")


def test_base_scenario_parameters_replace_a_value_and_an_interval():
    route = ET.fromstring('<route id="1"><scenarios><scenario type="X"><flow_speed value="10"/>'
                          '<frequency from="60" to="130"/></scenario></scenarios></route>')
    pilot_routes.set_base_parameters(route, {"flow_speed": 15, "frequency": {"from": 30, "to": 45}})
    assert route.find(".//flow_speed").attrib == {"value": "15"}
    assert route.find(".//frequency").attrib == {"from": "30", "to": "45"}
    with pytest.raises(ValueError, match="no parameter"):
        pilot_routes.set_base_parameters(route, {"missing": 1})
    pilot_routes.set_base_parameters(route, {"missing": 1}, may_add=True)
    assert route.find(".//missing").attrib == {"value": "1"}


def test_a_cut_keeps_one_scenario_and_the_road_around_its_trigger():
    route = ET.fromstring('<route id="9" town="T"><waypoints>' + "".join(
        f'<position x="{x}" y="0" z="0"/>' for x in (0, 100, 200, 300, 400)) + '</waypoints><scenarios>'
        '<scenario type="A"><trigger_point x="210" y="0"/></scenario><scenario type="B"><trigger_point x="310" y="0"/></scenario>'
        '</scenarios></route>')
    scenario = next(route.iter("scenario"))
    points = pilot_routes.waypoints(route)
    bounds = cut_routes.cut_bounds(points, cut_routes.trigger_of(scenario), lead_m=20, tail_m=60)
    assert bounds == (1, 3)
    cut = cut_routes.cut_route(route, scenario, bounds, 60000)
    assert cut.get("id") == "60000" and [point[0] for point in pilot_routes.waypoints(cut)] == [100, 200, 300]
    assert [item.get("type") for item in cut.iter("scenario")] == ["A"]
    assert cut_routes.cut_bounds(points, (5, 0), lead_m=20, tail_m=60) is None
    assert cut_routes.cut_bounds(points, (150, 0), lead_m=20, tail_m=60) == (1, 3)  # far from every waypoint
    assert not cut_routes.spaced((0, 0), [(50, 0)], 100) and cut_routes.spaced((0, 0), [(150, 0)], 100)


def route_with_hazard(*parameters):
    return ET.fromstring('<route id="9" town="T"><waypoints>' + "".join(
        f'<position x="{x}" y="0" z="0"/>' for x in (0, 100, 200, 300, 400)) + '</waypoints><scenarios><scenario type="A">'
        '<trigger_point x="110" y="0"/>' + "".join(f'<{name} value="{value}"/>' for name, value in parameters) + '</scenario></scenarios></route>')


def cut_ends(route, **tail):
    spec = {"lead_m": 20, "tail_m": 60, "min_spacing_m": 100, **tail}
    return [pilot_routes.waypoints(cut)[-1][0] for cut in cut_routes.cuts_from([route], {"A"}, [], spec, 60000)]


def test_tail_past_hazard_runs_past_the_hazard_and_any_bicycle_ride():
    assert cut_ends(route_with_hazard(("distance", 90)), tail_past_hazard_m=60) == [300]
    assert cut_ends(route_with_hazard(("distance", 90), ("bicycle_drive_distance", 100)), tail_past_hazard_m=60) == [400]


def test_without_the_key_a_tail_ignores_the_hazard():
    assert cut_ends(route_with_hazard(("distance", 90), ("bicycle_drive_distance", 100))) == [200]


def test_tail_past_hazard_keeps_every_road_on_its_id_and_drops_what_cannot_reach():
    spec = {"lead_m": 20, "tail_m": 60, "min_spacing_m": 100}
    cannot_reach = route_with_hazard(("distance", 400))
    can_reach = route_with_hazard(("distance", 90))
    next(can_reach.iter("trigger_point")).set("x", "220")
    routes = [cannot_reach, can_reach]
    assert [cut.get("id") for cut in cut_routes.cuts_from(routes, {"A"}, [], spec, 60000)] == ["60000", "60001"]
    keyed = cut_routes.cuts_from(routes, {"A"}, [], {**spec, "tail_past_hazard_m": 60}, 60000)
    assert [cut.get("id") for cut in keyed] == ["60001"]


def test_report_lists_a_hazard_past_the_route_end_and_keeps_the_ride_visible():
    route = route_with_hazard(("distance", 200), ("bicycle_drive_distance", 100))
    assert cut_routes.hazards_past_route_end([route]) == [
        {"route": "9", "scenario": "A", "hazard_starts_m": 200.0, "hazard_m": 300.0, "end_m": 290.0}]
    assert cut_routes.hazards_past_route_end([route_with_hazard(("distance", 200))]) == []
    assert cut_routes.hazards_past_route_end([route_with_hazard()]) == []


def test_report_finds_the_three_short_p20_pairs_and_none_of_their_recuts():
    def listed_bases(name):
        routes = ET.parse(ROOT / f"configs/rollout/{name}.xml").getroot().iter("route")
        return {row["route"][:-2] for row in cut_routes.hazards_past_route_end(list(routes))}
    assert {"64155", "64223", "64250"} <= listed_bases("step5-pilot-p20-screen")
    assert not {"64155", "64223", "64250", "64901", "64902", "64903"} & listed_bases("step5-pilot-p20-screen-amended")


def test_recut_script_writes_the_committed_amended_files():
    if not (ROOT / ".runtime/simlingo/leaderboard/data/routes_training.xml").is_file():
        pytest.skip("long routes not installed")
    spec = importlib.util.spec_from_file_location("recut_pairs", ROOT / "docs/research/experiments/h13-cross-family-gap/recut_pairs.py")
    recut_pairs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recut_pairs)
    document, entries = recut_pairs.amended_screen()
    amended = ROOT / "configs/rollout/step5-pilot-p20-screen-amended"
    assert Path(f"{amended}.xml").read_text() == document
    assert json.loads(Path(f"{amended}.manifest.json").read_text()) == entries

