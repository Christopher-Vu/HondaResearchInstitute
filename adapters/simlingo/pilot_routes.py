"""Generate a practice-gap efficacy pilot (Step 5): paired slice and neighbourhood routes on distinct base routes.

    python adapters/simlingo/pilot_routes.py configs/rollout/step5-pilot-p3.yaml

The config's `pilot` section names one gap in a practice-gap file. Base routes are drawn from the pinned
Bench2Drive-220 routes with the generator seed, one route per base, skipping excluded scenario families and routes
shorter than the gap's `plant.min_route_length_m`. Each base yields a slice route under the gap's `plant` and a
neighbourhood route under its `neighbourhood`, so the pair differs only in the planted factor and the base route is
the unit of analysis (CONFLICTS.md C23). An arm may set:

    weather   a preset with overrides (default ClearNoon)
    sensor    agent-side settings recorded in the manifest, e.g. `camera_fault`, which run_savio.py hands the agent
    scenario  a scenario appended to the route, triggered at its first waypoint: `type`, `parameters` (each written
              as <name value=...>; a list rotates across base routes in draw order) and `attributes` (child
              elements written with attributes, e.g. `pedestrians`); the manifest records the values used

With `pilot.stage`, the generator draws `screen_base_routes` + `plant.base_routes` bases in one order: the first
`screen_base_routes` are the screen, the rest the full pilot, so the full pilot never reuses a screened base.
Routes reuse dev_routes.py's construction: one <weather> element, ids of base id times 100 plus the role offset
plus `pilot.id_offset` (even, 0 to 8), so pilots of different gaps never share a route id.
"""
from __future__ import annotations

import argparse
import math
import random
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from artifacts import ROOT
from dev_routes import (PlannedRoute, build_route, family_of, manifest_document, manifest_entry, routes_document,
                        weather_from_spec)
from harness.predicates import matches

SLICE, NEIGHBOURHOOD = "pilot_slice", "pilot_neighbourhood"
DEFAULT_WEATHER = {"preset": "ClearNoon"}


def waypoints(route: ET.Element) -> list[tuple[float, float, float]]:
    return [(float(p.get("x", 0)), float(p.get("y", 0)), float(p.get("z", 0))) for p in route.iter("position")]


def route_length(route: ET.Element) -> float:
    points = waypoints(route)
    return sum(math.dist(a[:2], b[:2]) for a, b in zip(points, points[1:]))


def eligible(routes: list[ET.Element], gap: dict[str, Any], pilot: dict[str, Any]) -> list[ET.Element]:
    excluded = set(pilot["exclude_scenarios"])
    shortest = gap["plant"].get("min_route_length_m", 0)
    return [route for route in routes if family_of(route) not in excluded and route_length(route) >= shortest]


def draw_bases(routes: list[ET.Element], gap: dict[str, Any], pilot: dict[str, Any]) -> list[ET.Element]:
    count = gap["plant"]["base_routes"]
    screen = pilot.get("screen_base_routes", 0) if pilot.get("stage") else 0
    drawn = random.Random(pilot["generator_seed"]).sample(eligible(routes, gap, pilot), screen + count)
    chosen = drawn[:screen] if pilot.get("stage") == "screen" else drawn[screen:]
    return sorted(chosen, key=lambda route: int(str(route.get("id"))))


def plan_pairs(bases: list[ET.Element], gap: dict[str, Any],
               id_offset: int = 0) -> list[tuple[PlannedRoute, dict[str, Any]]]:
    plant, nearby = gap["plant"], gap["neighbourhood"]
    slice_weather = weather_from_spec(plant.get("weather", DEFAULT_WEATHER))
    neighbourhood_weather = weather_from_spec(nearby.get("weather", DEFAULT_WEATHER))
    return [pair for base in bases for pair in (
        (PlannedRoute(base, SLICE, slice_weather, {}, id_offset), plant),
        (PlannedRoute(base, NEIGHBOURHOOD, neighbourhood_weather, {}, id_offset, (gap["gap_id"],)), nearby))]


def resolved_parameters(spec: dict[str, Any], base_index: int) -> dict[str, Any]:
    return {name: value[base_index % len(value)] if isinstance(value, list) else value
            for name, value in spec.get("parameters", {}).items()}


def injected_scenario(route: ET.Element, spec: dict[str, Any], base_index: int) -> ET.Element:
    (x0, y0, z0), (x1, y1, _z1) = waypoints(route)[:2]
    scenario = ET.Element("scenario", {"name": f"{spec['type']}_injected", "type": spec["type"]})
    for name, value in resolved_parameters(spec, base_index).items():
        ET.SubElement(scenario, name, {"value": str(value)})
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    ET.SubElement(scenario, "trigger_point", {"x": str(x0), "y": str(y0), "z": str(z0), "yaw": f"{yaw:.1f}"})
    for name, attributes in spec.get("attributes", {}).items():
        ET.SubElement(scenario, name, {key: str(value) for key, value in attributes.items()})
    return scenario


def build_arm(planned: PlannedRoute, arm: dict[str, Any], base_index: int) -> ET.Element:
    route = build_route(planned)
    if "scenario" in arm:
        scenarios = route.find("scenarios")
        assert scenarios is not None
        scenarios.append(injected_scenario(route, arm["scenario"], base_index))
    return route


def arm_entry(planned: PlannedRoute, route: ET.Element, arm: dict[str, Any], gap: dict[str, Any],
              base_index: int) -> dict[str, Any]:
    entry = manifest_entry(planned, route, [])
    if "sensor" in arm:
        entry["sensor"] = arm["sensor"]
    if "scenario" in arm:
        entry["injected"] = arm["scenario"]["type"]
        entry["injected_parameters"] = resolved_parameters(arm["scenario"], base_index)
    entry["practice_gaps"] = [gap["gap_id"]] if matches(gap["predicate"], entry) else []
    return entry


def validate(entries: list[dict[str, Any]], expected_bases: int, gap: dict[str, Any]) -> None:
    if len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("Route ids are not unique")
    roles_per_base = Counter((entry["base_id"], entry["role"]) for entry in entries)
    if set(roles_per_base.values()) != {1} or len(roles_per_base) != 2 * expected_bases:
        raise ValueError("Every base route needs exactly one slice and one neighbourhood route")
    for entry in entries:
        if (gap["gap_id"] in entry["practice_gaps"]) != (entry["role"] == SLICE):
            raise ValueError(f"Route {entry['id']} ({entry['role']}) disagrees with {gap['gap_id']}'s predicate")


def generate(config: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    pilot = config["pilot"]
    routes = list(ET.parse(ROOT / pilot["base_routes_file"]).getroot().iter("route"))
    gaps = {gap["gap_id"]: gap for gap in yaml.safe_load((ROOT / pilot["practice_gaps"]).read_text())["gaps"]}
    gap = gaps[pilot["gap_id"]]
    bases = draw_bases(routes, gap, pilot)
    pairs = plan_pairs(bases, gap, pilot.get("id_offset", 0))
    built = [(planned, build_arm(planned, arm, index // 2), arm, index // 2) for index, (planned, arm) in enumerate(pairs)]
    entries = [arm_entry(planned, route, arm, gap, base) for planned, route, arm, base in built]
    validate(entries, len(bases), gap)
    return routes_document([route for _planned, route, _arm, _base in built]), entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    config = yaml.safe_load(parser.parse_args().config.read_text())
    document, entries = generate(config)
    (ROOT / config["route"]["routes_file"]).write_text(document)
    (ROOT / config["route"]["manifest"]).write_text(manifest_document(entries))
    print(f"{len(entries)} routes over {len({entry['base_id'] for entry in entries})} base routes, "
          f"{len({entry['scenario'] for entry in entries})} scenario families")


if __name__ == "__main__":
    main()
