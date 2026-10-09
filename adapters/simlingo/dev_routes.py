"""Generate the Step 4 dev pool: a routes file for the leaderboard and a manifest describing each route.

    python adapters/simlingo/dev_routes.py configs/rollout/step4-dev-pool.yaml

Every route is a copy of a Bench2Drive-220 route (town, waypoints, scenario) with its weather replaced
and, for the second practice gap, three scenario parameters replaced. The config's `dev_pool` section
and gaps/practice/practice_v1.yaml say what to build; the same config gives the same files.

    P1_slice          one route from each of 30 scenario families, in a dust storm at night
    background        those 30 routes plus others, each under one stock weather preset
    P2_slice          every DynamicObjectCrossing route x distance x crossing angle, container blocker, clear night
    P2_neighbourhood  the same combinations at clear noon

A route's id is its base route's id times 100 plus an offset for its role and grid position, so ids stay
plain integers, which the leaderboard's --routes-subset requires.

Each route carries one <weather> element, not the two Bench2Drive writes. With two, the leaderboard's
RouteWeatherBehavior re-sets the weather as the car advances and interpolates 13 attributes, dust_storm
not among them, so a dust storm would stop within the first few steps. With one, the weather is set once.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import random
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from artifacts import ROOT

sys.path.insert(0, str(ROOT / "src"))
from harness.predicates import matches  # noqa: E402

P1_GAP = "P1_dust_storm_night"
P2_GAP = "P2_occluded_pedestrian_night"
P2_FAMILY = "DynamicObjectCrossing"
SLICE_ROLE = {P1_GAP: "P1_slice", P2_GAP: "P2_slice"}
ROLE_ID_OFFSET = {"background": 0, "P1_slice": 1, "P2_slice": 10, "P2_neighbourhood": 20}

# Read from CARLA 0.9.15 (carla.WeatherParameters.<preset>) with float32 noise rounded to 6 digits;
# tests/test_dev_routes.py compares them with CARLA when it is installed. These are the presets of
# dir(carla.WeatherParameters)[:22], which SimLingo's data collection drew from, less "Default", whose
# every field is -1 and so is not a weather, plus DustStorm for the first practice gap.
PRESET_FIELDS = ("cloudiness", "precipitation", "precipitation_deposits", "wind_intensity", "sun_altitude_angle",
                 "fog_density", "fog_distance", "fog_falloff", "wetness", "dust_storm")
PRESET_VALUES = {
    "ClearNight": (5, 0, 0, 10, -90, 60, 75, 1, 0, 0),
    "ClearNoon": (5, 0, 0, 10, 45, 2, 0.75, 0.1, 0, 0),
    "ClearSunset": (5, 0, 0, 10, 15, 2, 0.75, 0.1, 0, 0),
    "CloudyNight": (60, 0, 0, 10, -90, 60, 0.75, 0.1, 0, 0),
    "CloudyNoon": (60, 0, 0, 10, 45, 3, 0.75, 0.1, 0, 0),
    "CloudySunset": (60, 0, 0, 10, 15, 3, 0.75, 0.1, 0, 0),
    "DustStorm": (100, 0, 0, 100, 45, 2, 0.75, 0.1, 0, 100),
    "HardRainNight": (100, 100, 90, 100, -90, 100, 0.75, 0.1, 100, 0),
    "HardRainNoon": (100, 100, 90, 100, 45, 7, 0.75, 0.1, 0, 0),
    "HardRainSunset": (100, 100, 90, 100, 15, 7, 0.75, 0.1, 0, 0),
    "MidRainSunset": (60, 60, 60, 60, 15, 3, 0.75, 0.1, 0, 0),
    "MidRainyNight": (80, 60, 60, 60, -90, 60, 0.75, 0.1, 80, 0),
    "MidRainyNoon": (60, 60, 60, 60, 45, 3, 0.75, 0.1, 0, 0),
    "SoftRainNight": (60, 30, 50, 30, -90, 60, 0.75, 0.1, 60, 0),
    "SoftRainNoon": (20, 30, 50, 30, 45, 3, 0.75, 0.1, 0, 0),
    "SoftRainSunset": (20, 30, 50, 30, 15, 2, 0.75, 0.1, 0, 0),
    "WetCloudyNight": (60, 0, 50, 10, -90, 60, 0.75, 0.1, 60, 0),
    "WetCloudyNoon": (60, 0, 50, 10, 45, 3, 0.75, 0.1, 0, 0),
    "WetCloudySunset": (60, 0, 50, 10, 15, 2, 0.75, 0.1, 0, 0),
    "WetNight": (5, 0, 50, 10, -90, 60, 75, 1, 60, 0),
    "WetNoon": (5, 0, 50, 10, 45, 3, 0.75, 0.1, 0, 0),
}
SHARED_WEATHER = {"sun_azimuth_angle": -1.0, "scattering_intensity": 1.0,
                  "mie_scattering_scale": 0.03, "rayleigh_scattering_scale": 0.0331}
BACKGROUND_PRESETS = tuple(name for name in PRESET_VALUES if name != "DustStorm")


def preset_weather(name: str) -> dict[str, float]:
    return SHARED_WEATHER | dict(zip(PRESET_FIELDS, map(float, PRESET_VALUES[name])))


def weather_from_spec(spec: dict[str, Any]) -> dict[str, float]:
    """A preset name, with any other keys replacing that preset's parameters."""
    weather = preset_weather(spec["preset"])
    overrides = {name: float(value) for name, value in spec.items() if name != "preset"}
    unknown = overrides.keys() - weather.keys()
    if unknown:
        raise ValueError(f"Unknown weather parameter(s) {sorted(unknown)}")
    return weather | overrides


def scenario_of(route: ET.Element) -> ET.Element:
    scenario = route.find("scenarios/scenario")
    if scenario is None:
        raise ValueError(f"Route {route.get('id')} has no authored scenario")
    return scenario


def family_of(route: ET.Element) -> str:
    return str(scenario_of(route).get("type"))


@dataclass(frozen=True)
class PlannedRoute:
    base: ET.Element
    role: str
    weather: dict[str, float]
    parameters: dict[str, Any]
    grid_position: int = 0
    neighbourhood_of: tuple[str, ...] = ()

    @property
    def route_id(self) -> str:
        return str(int(str(self.base.get("id"))) * 100 + ROLE_ID_OFFSET[self.role] + self.grid_position)


def plan_p1_slice(routes: list[ET.Element], gap: dict[str, Any], excluded: set[str],
                  rng: random.Random) -> list[PlannedRoute]:
    plant = gap["plant"]
    families = sorted({family_of(route) for route in routes} - excluded - {P2_FAMILY})
    weather = weather_from_spec(plant["weather"])
    return [PlannedRoute(rng.choice([route for route in routes if family_of(route) == family]),
                         "P1_slice", weather, {})
            for family in sorted(rng.sample(families, plant["base_routes"]))]


def plan_background(routes: list[ET.Element], p1_bases: list[ET.Element], excluded: set[str], size: int,
                    rng: random.Random) -> list[PlannedRoute]:
    p1_ids = {base.get("id") for base in p1_bases}
    remaining = [route for route in routes
                 if family_of(route) not in excluded | {P2_FAMILY} and route.get("id") not in p1_ids]
    bases = p1_bases + rng.sample(remaining, size - len(p1_bases))
    return [PlannedRoute(base, "background", preset_weather(rng.choice(BACKGROUND_PRESETS)), {},
                         neighbourhood_of=(P1_GAP,) if base.get("id") in p1_ids else ())
            for base in bases]


def plan_p2(routes: list[ET.Element], gap: dict[str, Any], role: str, weather_spec: dict[str, Any],
            neighbourhood_of: tuple[str, ...]) -> list[PlannedRoute]:
    grid = gap["plant"]["grid"]
    weather = weather_from_spec(weather_spec)
    return [PlannedRoute(base, role, weather, gap["plant"]["param"] | dict(zip(grid, values)), position,
                         neighbourhood_of)
            for base in routes if family_of(base) == P2_FAMILY
            for position, values in enumerate(itertools.product(*grid.values()))]


def plan_pool(routes: list[ET.Element], gaps: dict[str, dict[str, Any]], pool: dict[str, Any]) -> list[PlannedRoute]:
    rng = random.Random(pool["generator_seed"])
    excluded = set(pool["exclude_scenarios"])
    p1 = plan_p1_slice(routes, gaps[P1_GAP], excluded, rng)
    background = plan_background(routes, [planned.base for planned in p1], excluded, pool["background"], rng)
    p2 = gaps[P2_GAP]
    return (p1 + background
            + plan_p2(routes, p2, "P2_slice", p2["plant"]["weather"], ())
            + plan_p2(routes, p2, "P2_neighbourhood", p2["neighbourhood"]["weather"], (P2_GAP,)))


def set_parameter(scenario: ET.Element, name: str, value: Any) -> None:
    element = scenario.find(name)
    if element is None:
        raise ValueError(f"Scenario {scenario.get('name')} has no {name} parameter to replace")
    element.set("value", str(value))


def build_route(planned: PlannedRoute) -> ET.Element:
    route = copy.deepcopy(planned.base)
    route.set("id", planned.route_id)
    for name, value in planned.parameters.items():
        set_parameter(scenario_of(route), name, value)
    weathers = route.find("weathers")
    if weathers is None:
        raise ValueError(f"Route {planned.base.get('id')} has no weathers element")
    weathers.clear()
    ET.SubElement(weathers, "weather", {"route_percentage": "0"}
                  | {name: str(value) for name, value in sorted(planned.weather.items())})
    return route


def routes_document(routes: list[ET.Element]) -> str:
    root = ET.Element("routes")
    root.extend(routes)
    ET.indent(root, space="   ")
    return ET.tostring(root, encoding="unicode") + "\n"


def typed(value: str) -> int | float | str:
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def scenario_parameters(scenario: ET.Element) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for element in scenario:
        if element.tag == "trigger_point":
            continue
        values = {name: typed(value) for name, value in element.attrib.items()}
        parameters[element.tag] = values["value"] if list(values) == ["value"] else values
    return parameters


def manifest_entry(planned: PlannedRoute, route: ET.Element, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": route.get("id"), "base_id": planned.base.get("id"), "town": route.get("town"),
        "scenario": family_of(route), "role": planned.role, "weather": dict(sorted(planned.weather.items())),
        "param": scenario_parameters(scenario_of(route))}
    entry["practice_gaps"] = [gap["gap_id"] for gap in gaps if matches(gap["predicate"], entry)]
    entry["neighbourhood_of"] = list(planned.neighbourhood_of)
    return entry


def expected_role_counts(routes: list[ET.Element], gaps: dict[str, dict[str, Any]],
                         pool: dict[str, Any]) -> Counter[str]:
    p2_routes = sum(family_of(route) == P2_FAMILY for route in routes)
    p2_combinations = len(list(itertools.product(*gaps[P2_GAP]["plant"]["grid"].values())))
    return Counter({"P1_slice": gaps[P1_GAP]["plant"]["base_routes"], "background": pool["background"],
                    "P2_slice": p2_routes * p2_combinations, "P2_neighbourhood": p2_routes * p2_combinations})


def validate(entries: list[dict[str, Any]], expected_counts: Counter[str]) -> None:
    repeated = sorted(route_id for route_id, count in Counter(entry["id"] for entry in entries).items() if count > 1)
    if repeated:
        raise ValueError(f"Route ids are not unique: {repeated}")
    counts = Counter(entry["role"] for entry in entries)
    if counts != expected_counts:
        raise ValueError(f"Routes per role {dict(counts)} differ from the expected {dict(expected_counts)}")
    for gap_id, role in SLICE_ROLE.items():
        matched = {entry["id"] for entry in entries if gap_id in entry["practice_gaps"]}
        in_slice = {entry["id"] for entry in entries if entry["role"] == role}
        if matched != in_slice:
            raise ValueError(f"{gap_id} matches {len(matched)} routes but its slice holds {len(in_slice)}; "
                             f"in one and not the other: {sorted(matched ^ in_slice)}")


def generate(config: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    pool = config["dev_pool"]
    routes = list(ET.parse(ROOT / pool["base_routes_file"]).getroot().iter("route"))
    gaps = {gap["gap_id"]: gap for gap in yaml.safe_load((ROOT / pool["practice_gaps"]).read_text())["gaps"]}
    planned = plan_pool(routes, gaps, pool)
    built = [build_route(route) for route in planned]
    entries = [manifest_entry(route, element, list(gaps.values())) for route, element in zip(planned, built)]
    validate(entries, expected_role_counts(routes, gaps, pool))
    return routes_document(built), entries


def manifest_document(entries: list[dict[str, Any]]) -> str:
    return "[\n" + ",\n".join(json.dumps(entry) for entry in entries) + "\n]\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    config = yaml.safe_load(parser.parse_args().config.read_text())
    document, entries = generate(config)
    (ROOT / config["route"]["routes_file"]).write_text(document)
    (ROOT / config["route"]["manifest"]).write_text(manifest_document(entries))
    print(f"{len(entries)} routes: {dict(Counter(entry['role'] for entry in entries))}")
    print("P1 families:", ", ".join(sorted(entry["scenario"] for entry in entries if entry["role"] == "P1_slice")))


if __name__ == "__main__":
    main()
