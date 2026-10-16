"""Reproduce Bench2Drive's sidewalk walk for pedestrian-crossing placement, without a policy or a route run.

    .runtime/policy-venv/bin/python scripts/lane_walk_probe.py ROUTES_XML --port 2000 --output OUT.json

Needs a CARLA 0.9.15 server on --port (rendering not needed). For every scenario trigger point in ROUTES_XML
it moves 20 m ahead along the lane, as `DynamicObjectCrossing._initialize_actors` does
(`scenario_runner/srunner/scenarios/object_crash_vehicle.py`), then steps sideways until it reaches a sidewalk:

    stock  `get_left_lane()` (or right) every step, as upstream does; upstream has no step limit
    fixed  the same, but once the lane id changes sign (the walk has crossed into oncoming lanes, whose left
           points back towards the ego) it continues with the opposite call, so it moves away from the ego

Each walk stops at a sidewalk, at None (road edge), at a revisited (road, lane) pair (a cycle, which upstream
would loop on forever), or after 50 steps. docs/infra/left-crossing-stall.md reads the output.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

MAX_STEPS = 50
AHEAD_M = 20.0


def walk(carla, waypoint, side: str, fixed: bool) -> dict:
    current, path, seen = waypoint, [], set()
    start_sign = waypoint.lane_id > 0
    flipped = False
    for step in range(MAX_STEPS):
        key = (current.road_id, current.section_id, current.lane_id)
        path.append([current.road_id, current.lane_id, str(current.lane_type)])
        if current.lane_type == carla.LaneType.Sidewalk:
            return {"end": "sidewalk", "steps": step, "path": path, "crossed_centre": flipped}
        if key in seen:
            return {"end": "cycle", "steps": step, "path": path, "crossed_centre": flipped}
        seen.add(key)
        go_left = side == "left"
        if fixed and (current.lane_id > 0) != start_sign:
            flipped = True
            go_left = not go_left
        nxt = current.get_left_lane() if go_left else current.get_right_lane()
        if nxt is None:
            return {"end": "edge", "steps": step, "path": path, "crossed_centre": flipped}
        if fixed and (nxt.lane_id > 0) != start_sign:
            flipped = True
        current = nxt
    return {"end": "limit", "steps": MAX_STEPS, "path": path, "crossed_centre": flipped}


def triggers(xml: Path) -> list[dict]:
    out = []
    for route in ET.parse(xml).getroot().iter("route"):
        for scenario in route.iter("scenario"):
            point = scenario.find("trigger_point")
            if point is None:
                continue
            out.append({"route": route.get("id"), "town": route.get("town"), "scenario": scenario.get("type"),
                        **{k: float(point.get(k)) for k in ("x", "y", "z", "yaw")}})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("routes", type=Path)
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import carla
    from srunner.tools.scenario_helper import get_location_in_distance_from_wp

    client = carla.Client("localhost", args.port)
    client.set_timeout(300)
    by_town = defaultdict(list)
    for t in triggers(args.routes):
        by_town[t["town"]].append(t)
    rows = []
    for town, points in sorted(by_town.items()):
        world = client.load_world(town)
        wmap = world.get_map()
        print(town, len(points), flush=True)
        for t in points:
            wp = wmap.get_waypoint(carla.Location(t["x"], t["y"], t["z"]))
            location, _ = get_location_in_distance_from_wp(wp, AHEAD_M, False)
            ahead = wmap.get_waypoint(location)
            row = {**t, "lane_id": ahead.lane_id}
            for side in ("left", "right"):
                for fixed in (False, True):
                    row[f"{side}_{'fixed' if fixed else 'stock'}"] = walk(carla, ahead, side, fixed)
            rows.append(row)
    summary = defaultdict(lambda: defaultdict(int))
    for row in rows:
        for key in ("left_stock", "right_stock", "left_fixed", "right_fixed"):
            summary[key][row[key]["end"]] += 1
    args.output.write_text(json.dumps({"points": len(rows), "summary": summary, "rows": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
