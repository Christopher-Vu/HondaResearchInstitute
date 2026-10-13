"""Generate a practice-gap efficacy pilot (Step 5): paired slice and neighbourhood routes on distinct base routes.

    python adapters/simlingo/pilot_routes.py configs/rollout/step5-pilot-p3.yaml

The config's `pilot` section names one gap in a practice-gap file. Its `plant.base_routes` base routes are drawn
from the pinned Bench2Drive-220 routes with the generator seed, one route per base. Each base yields a slice route
under the gap's planted weather and a neighbourhood route under its neighbourhood weather, so the pair differs only
in the planted factor and the base route is the unit of analysis (CONFLICTS.md C23). Routes reuse dev_routes.py's
construction: one <weather> element, ids of base id times 100 plus the role offset.
"""
from __future__ import annotations

import argparse
import random
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from artifacts import ROOT
from dev_routes import (PlannedRoute, build_route, family_of, manifest_document, manifest_entry, routes_document,
                        weather_from_spec)

SLICE, NEIGHBOURHOOD = "pilot_slice", "pilot_neighbourhood"


def plan_pairs(routes: list[ET.Element], gap: dict[str, Any], pilot: dict[str, Any]) -> list[PlannedRoute]:
    excluded = set(pilot["exclude_scenarios"])
    eligible = [route for route in routes if family_of(route) not in excluded]
    bases = sorted(random.Random(pilot["generator_seed"]).sample(eligible, gap["plant"]["base_routes"]),
                   key=lambda route: int(str(route.get("id"))))
    slice_weather = weather_from_spec(gap["plant"]["weather"])
    neighbourhood_weather = weather_from_spec(gap["neighbourhood"]["weather"])
    return [planned for base in bases for planned in (
        PlannedRoute(base, SLICE, slice_weather, {}),
        PlannedRoute(base, NEIGHBOURHOOD, neighbourhood_weather, {}, neighbourhood_of=(gap["gap_id"],)))]


def validate(entries: list[dict[str, Any]], gap: dict[str, Any]) -> None:
    if len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("Route ids are not unique")
    roles_per_base = Counter((entry["base_id"], entry["role"]) for entry in entries)
    if set(roles_per_base.values()) != {1} or len(roles_per_base) != 2 * gap["plant"]["base_routes"]:
        raise ValueError("Every base route needs exactly one slice and one neighbourhood route")
    for entry in entries:
        if (gap["gap_id"] in entry["practice_gaps"]) != (entry["role"] == SLICE):
            raise ValueError(f"Route {entry['id']} ({entry['role']}) disagrees with {gap['gap_id']}'s predicate")


def generate(config: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    pilot = config["pilot"]
    routes = list(ET.parse(ROOT / pilot["base_routes_file"]).getroot().iter("route"))
    gaps = {gap["gap_id"]: gap for gap in yaml.safe_load((ROOT / pilot["practice_gaps"]).read_text())["gaps"]}
    gap = gaps[pilot["gap_id"]]
    planned = plan_pairs(routes, gap, pilot)
    built = [build_route(route) for route in planned]
    entries = [manifest_entry(route, element, [gap]) for route, element in zip(planned, built)]
    validate(entries, gap)
    return routes_document(built), entries


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
