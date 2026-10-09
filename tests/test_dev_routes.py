"""The Step 4 dev pool generator: what it builds from the pinned routes, and what it refuses to build."""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pytest
import yaml

import dev_routes
from harness.predicates import matches

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rollout/step4-dev-pool.yaml"


@pytest.fixture(scope="module")
def config():
    loaded = yaml.safe_load(CONFIG.read_text())
    if not (ROOT / loaded["dev_pool"]["base_routes_file"]).is_file():
        pytest.skip("pinned routes file not installed")
    return loaded


@pytest.fixture(scope="module")
def pool(config):
    return dev_routes.generate(config)


@pytest.fixture(scope="module")
def gaps(config):
    return yaml.safe_load((ROOT / config["dev_pool"]["practice_gaps"]).read_text())["gaps"]


def test_pool_has_the_planned_number_of_routes_per_role(pool):
    _document, entries = pool
    assert Counter(entry["role"] for entry in entries) == {
        "P1_slice": 30, "background": 100, "P2_slice": 30, "P2_neighbourhood": 30}


def test_same_seed_gives_identical_files_and_another_seed_gives_another_draw(config, pool):
    assert dev_routes.generate(config) == pool
    reseeded = {**config, "dev_pool": {**config["dev_pool"], "generator_seed": 1}}
    first_families = {entry["scenario"] for entry in pool[1] if entry["role"] == "P1_slice"}
    assert {entry["scenario"] for entry in dev_routes.generate(reseeded)[1] if entry["role"] == "P1_slice"} != first_families


def test_committed_files_are_what_the_generator_writes(config, pool):
    document, entries = pool
    assert (ROOT / config["route"]["routes_file"]).read_text() == document
    assert (ROOT / config["route"]["manifest"]).read_text() == dev_routes.manifest_document(entries)


def test_each_practice_gap_matches_its_slice_and_nothing_else(pool, gaps):
    _document, entries = pool
    slices = {"P1_dust_storm_night": "P1_slice", "P2_occluded_pedestrian_night": "P2_slice"}
    for gap in gaps:
        matched = {entry["id"] for entry in entries if matches(gap["predicate"], entry)}
        assert matched == {entry["id"] for entry in entries if entry["role"] == slices[gap["gap_id"]]}
        assert all((gap["gap_id"] in entry["practice_gaps"]) == (entry["id"] in matched) for entry in entries)


def test_ids_are_unique_plain_integers_built_from_the_base_id(pool):
    _document, entries = pool
    ids = [entry["id"] for entry in entries]
    assert len(set(ids)) == len(ids)
    assert all(route_id.isdigit() and int(route_id) // 100 == int(entry["base_id"])
               for route_id, entry in zip(ids, entries))


def test_leaderboard_gets_the_same_ids_the_manifest_lists(pool):
    document, entries = pool
    assert [route.get("id") for route in ET.fromstring(document).iter("route")] == [entry["id"] for entry in entries]


def test_excluded_scenarios_and_the_crossing_family_stay_out_of_p1_and_background(pool, config):
    _document, entries = pool
    barred = set(config["dev_pool"]["exclude_scenarios"]) | {"DynamicObjectCrossing"}
    assert not any(entry["scenario"] in barred for entry in entries if entry["role"] in {"P1_slice", "background"})
    assert len({entry["scenario"] for entry in entries if entry["role"] == "P1_slice"}) == 30


def test_p1_base_routes_reappear_in_the_background_as_its_neighbourhood(pool):
    _document, entries = pool
    p1_bases = {entry["base_id"] for entry in entries if entry["role"] == "P1_slice"}
    neighbours = [entry for entry in entries if entry["neighbourhood_of"] == ["P1_dust_storm_night"]]
    assert {entry["base_id"] for entry in neighbours} == p1_bases and len(neighbours) == 30
    assert all(entry["role"] == "background" for entry in neighbours)


def test_p2_grid_covers_every_crossing_route_in_both_lightings(pool):
    _document, entries = pool
    night = [entry for entry in entries if entry["role"] == "P2_slice"]
    noon = [entry for entry in entries if entry["role"] == "P2_neighbourhood"]

    def grid(group):
        return {(entry["base_id"], entry["param"]["distance"], entry["param"]["crossing_angle"]) for entry in group}

    assert len(grid(night)) == 30 and grid(night) == grid(noon)
    assert len({entry["base_id"] for entry in night}) == 5
    assert all(entry["param"]["blocker_model"] == "static.prop.container" for entry in night + noon)
    assert all(entry["weather"]["sun_altitude_angle"] < 0 for entry in night)
    assert all(entry["weather"]["sun_altitude_angle"] > 0 for entry in noon)
    assert all(entry["neighbourhood_of"] == ["P2_occluded_pedestrian_night"] for entry in noon)


def test_background_routes_use_stock_presets_without_the_dust_storm(pool):
    _document, entries = pool
    presets = [dev_routes.preset_weather(name) for name in dev_routes.BACKGROUND_PRESETS]
    background = [entry for entry in entries if entry["role"] == "background"]
    assert all(entry["weather"] in presets for entry in background)
    assert all(entry["weather"]["dust_storm"] == 0 for entry in background)
    assert len({tuple(entry["weather"].values()) for entry in background}) > 10


def test_every_route_has_one_weather_element_so_the_dust_storm_is_not_dropped(pool):
    """With two, the leaderboard's RouteWeatherBehavior re-sets the weather without dust_storm."""
    document, entries = pool
    for route, entry in zip(ET.fromstring(document).iter("route"), entries):
        weathers = route.findall("weathers/weather")
        assert len(weathers) == 1 and weathers[0].get("route_percentage") == "0"
        assert {name: float(value) for name, value in weathers[0].attrib.items() if name != "route_percentage"} \
            == entry["weather"]


def test_routes_differ_from_their_base_only_in_weather_and_the_named_parameters(config, pool):
    document, entries = pool
    bases = {route.get("id"): route
             for route in ET.parse(ROOT / config["dev_pool"]["base_routes_file"]).getroot().iter("route")}
    for route, entry in zip(ET.fromstring(document).iter("route"), entries):
        base = bases[entry["base_id"]]
        assert route.get("town") == base.get("town")
        assert [position.attrib for position in route.iter("position")] \
            == [position.attrib for position in base.iter("position")]
        assert route.find("scenarios/scenario").attrib == base.find("scenarios/scenario").attrib
        assert route.find("scenarios/scenario/trigger_point").attrib == base.find("scenarios/scenario/trigger_point").attrib
        base_parameters = dev_routes.scenario_parameters(base.find("scenarios/scenario"))
        changed = {name for name in entry["param"] if entry["param"][name] != base_parameters[name]}
        assert entry["param"].keys() == base_parameters.keys()
        assert changed <= ({"distance", "crossing_angle", "blocker_model"} if entry["role"].startswith("P2") else set())


def test_preset_table_matches_the_collection_presets_in_carla():
    carla = pytest.importorskip("carla")
    collection = set(dir(carla.WeatherParameters)[:22]) - {"Default"}
    assert set(dev_routes.PRESET_VALUES) == collection
    for name in collection:
        for parameter, value in dev_routes.preset_weather(name).items():
            assert getattr(getattr(carla.WeatherParameters, name), parameter) == pytest.approx(value, rel=1e-6)


def test_weather_spec_replaces_named_parameters_and_rejects_unknown_ones():
    weather = dev_routes.weather_from_spec({"preset": "DustStorm", "sun_altitude_angle": -90.0})
    assert weather["dust_storm"] == 100.0 and weather["sun_altitude_angle"] == -90.0
    with pytest.raises(ValueError, match="Unknown weather parameter"):
        dev_routes.weather_from_spec({"preset": "ClearNoon", "sunshine": 3})


def counts(**roles):
    return Counter(roles)


def row(route_id, role, practice_gaps=()):
    return {"id": route_id, "role": role, "practice_gaps": list(practice_gaps)}


def test_validation_accepts_a_consistent_pool():
    dev_routes.validate([row("1", "P1_slice", ["P1_dust_storm_night"]), row("2", "background")],
                        counts(P1_slice=1, background=1))


def test_validation_refuses_repeated_ids_and_wrong_counts():
    with pytest.raises(ValueError, match="not unique"):
        dev_routes.validate([row("1", "background"), row("1", "background")], counts(background=2))
    with pytest.raises(ValueError, match="differ from the expected"):
        dev_routes.validate([row("1", "background")], counts(background=2))


def test_validation_refuses_a_predicate_that_leaks_out_of_or_misses_its_slice():
    expected = counts(P1_slice=1, background=1)
    with pytest.raises(ValueError, match="P1_dust_storm_night matches 2 routes but its slice holds 1"):
        dev_routes.validate([row("1", "P1_slice", ["P1_dust_storm_night"]),
                             row("2", "background", ["P1_dust_storm_night"])], expected)
    with pytest.raises(ValueError, match="matches 0 routes but its slice holds 1"):
        dev_routes.validate([row("1", "P1_slice"), row("2", "background")], expected)


def test_manifest_is_a_json_list_with_one_route_per_line(pool):
    _document, entries = pool
    text = dev_routes.manifest_document(entries)
    assert json.loads(text) == entries and len(text.splitlines()) == len(entries) + 2
