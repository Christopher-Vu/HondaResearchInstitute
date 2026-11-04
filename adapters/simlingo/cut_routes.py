"""Cut one-scenario base routes out of the leaderboard's long routes, for pilots that need more roads than Bench2Drive-220.

    python adapters/simlingo/cut_routes.py configs/rollout/step5-pilot-p14-main.yaml

Each cut keeps one scenario and the waypoints around its trigger: from the last waypoint at least `lead_m` before it to the first at
least `tail_m` after it, or at least `tail_past_hazard_m` past its hazard when the spec sets that key; a cut that cannot reach it is dropped and its id stays unused. The leaderboard interpolates between waypoints, so a cut drives the same road as the long route. A trigger
within `min_spacing_m` of an earlier cut of the same family is skipped, and only routes of `min_length_m` to `max_length_m` stay. Bases named in `excluded_bases` are dropped, cuts included: a full
pilot never reuses a screened base. Length filtering comes after numbering, so a config with the same `first_id` gives a road the same id.
"""
from __future__ import annotations

import argparse
import copy
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml
from artifacts import ROOT
from dev_routes import routes_document
from pilot_routes import route_length, waypoints


def trigger_of(scenario: ET.Element) -> tuple[float, float]:
    point = scenario.find("trigger_point")
    assert point is not None
    return float(point.get("x", 0)), float(point.get("y", 0))


ROUTE_END_MARGIN_M = 10  # a route ends once over 90% complete and within this of its last waypoint


def parameter(scenario: ET.Element, name: str) -> float:
    element = scenario.find(name)
    return float(element.get("value", 0)) if element is not None else 0.0


def required_tail_m(scenario: ET.Element, past_hazard_m: float) -> float:
    """Straight-line metres past the trigger: the hazard, plus any distance its bicycles ride, plus a margin."""
    return parameter(scenario, "distance") + parameter(scenario, "bicycle_drive_distance") + past_hazard_m


def hazards_past_route_end(routes: list[ET.Element]) -> list[dict[str, Any]]:
    """Report only: each scenario whose hazard, bicycle ride included, lies further from its trigger than the route's
    last waypoint does.

    A straight line is shorter than the road on a bend, so a listed route may still reach its hazard by road, and
    `hazard_starts_m` shows when only the end of a ride falls past the route's end.
    """
    listed = []
    for route in routes:
        end = waypoints(route)[-1][:2]
        for scenario in route.iter("scenario"):
            hazard_m, end_m = required_tail_m(scenario, 0), math.dist(end, trigger_of(scenario))
            if hazard_m > end_m - ROUTE_END_MARGIN_M:
                listed.append({"route": route.get("id"), "scenario": scenario.get("type"),
                               "hazard_starts_m": parameter(scenario, "distance"), "hazard_m": hazard_m,
                               "end_m": round(end_m, 1)})
    return listed


def distance_to_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    along_x, along_y = end[0] - start[0], end[1] - start[1]
    squared = along_x ** 2 + along_y ** 2
    share = 0.0 if not squared else min(1.0, max(0.0, ((point[0] - start[0]) * along_x + (point[1] - start[1]) * along_y) / squared))
    return math.dist(point, (start[0] + share * along_x, start[1] + share * along_y))


def segment_of(points: list[tuple[float, float, float]], trigger: tuple[float, float]) -> int:
    """Index of the waypoint that starts the segment holding the trigger."""
    return min(range(len(points) - 1), key=lambda index: distance_to_segment(trigger, points[index][:2], points[index + 1][:2]))


def cut_bounds(points: list[tuple[float, float, float]], trigger: tuple[float, float], lead_m: float,
               tail_m: float) -> tuple[int, int] | None:
    """First and last waypoint of the cut, or None when the route has too little road on either side."""
    segment = segment_of(points, trigger)
    first = next((index for index in range(segment, -1, -1) if math.dist(points[index][:2], trigger) >= lead_m), None)
    last = next((index for index in range(segment + 1, len(points)) if math.dist(points[index][:2], trigger) >= tail_m), None)
    return None if first is None or last is None else (first, last)


def cut_route(route: ET.Element, scenario: ET.Element, bounds: tuple[int, int], base_id: int) -> ET.Element:
    cut = copy.deepcopy(route)
    cut.set("id", str(base_id))
    wanted = list(cut.iter("position"))[bounds[0]:bounds[1] + 1]
    holder = cut.find("waypoints")
    scenarios = cut.find("scenarios")
    assert holder is not None and scenarios is not None
    holder.clear()
    holder.extend(wanted)
    scenarios.clear()
    scenarios.append(copy.deepcopy(scenario))
    return cut


def spaced(trigger: tuple[float, float], earlier: list[tuple[float, float]], minimum: float) -> bool:
    return all(math.dist(trigger, other) >= minimum for other in earlier)


def cuts_from(routes: list[ET.Element], families: set[str], required: list[str], spec: dict[str, Any],
              first_id: int) -> list[ET.Element]:
    cuts: list[ET.Element] = []
    numbered = 0
    seen: dict[str, list[tuple[float, float]]] = {family: [] for family in families}
    for route in routes:
        points = waypoints(route)
        for scenario in route.iter("scenario"):
            family = scenario.get("type", "")
            if family not in families or any(scenario.find(name) is None for name in required):
                continue
            trigger = trigger_of(scenario)
            bounds = cut_bounds(points, trigger, spec["lead_m"], spec["tail_m"])
            if bounds is None or not spaced(trigger, seen[family], spec["min_spacing_m"]):
                continue
            seen[family].append(trigger)
            base_id = first_id + numbered
            numbered += 1
            if "tail_past_hazard_m" in spec:
                bounds = cut_bounds(points, trigger, spec["lead_m"], required_tail_m(scenario, spec["tail_past_hazard_m"]))
            if bounds is not None:
                cuts.append(cut_route(route, scenario, bounds, base_id))
    return cuts


def generate(config: dict[str, Any]) -> list[ET.Element]:
    spec = config["pilot"]["cut_routes"]
    gaps = yaml.safe_load((ROOT / config["pilot"]["practice_gaps"]).read_text())["gaps"]
    gap = next(gap for gap in gaps if gap["gap_id"] == config["pilot"]["gap_id"])
    families = set(gap["plant"]["include_scenarios"])
    required = list(gap["plant"].get("base_scenario_parameters", {}))
    long_routes = [route for path in spec["from"] for route in ET.parse(ROOT / path).getroot().iter("route")]
    kept = [route for route in ET.parse(ROOT / spec["bench2drive"]).getroot().iter("route")
            if next(route.iter("scenario")).get("type") in families]
    excluded = set(map(str, spec["excluded_bases"]))
    bases = kept + cuts_from(long_routes, families, required, spec, spec["first_id"])
    return [base for base in bases if str(base.get("id")) not in excluded
            and spec["min_length_m"] <= route_length(base) <= spec["max_length_m"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    config = yaml.safe_load(parser.parse_args().config.read_text())
    bases = generate(config)
    (ROOT / config["pilot"]["base_routes_file"]).write_text(routes_document(bases))
    print(f"{len(bases)} bases, median length {sorted(map(route_length, bases))[len(bases) // 2]:.0f} m")
    for listed in hazards_past_route_end(bases):
        print(f"route {listed['route']} ({listed['scenario']}) ends {listed['end_m']} m past its trigger, "
              f"hazard from {listed['hazard_starts_m']} to {listed['hazard_m']} m by straight line")


if __name__ == "__main__":
    main()
