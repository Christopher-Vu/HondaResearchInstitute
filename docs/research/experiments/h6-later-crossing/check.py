"""H6's C24 check and per-route reading, from the screen's shards and route file.

Run on Savio from the repo root with the policy venv:
    .runtime/policy-venv/bin/python docs/research/experiments/h6-later-crossing/check.py OUT.json
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

NAME = "step5-pilot-p13-screen"
SLICE_START_S = 1.2
NEIGHBOURHOOD_START_S = 2.1
CROSSING_AFTER_TRIGGER_M = 20.0
MIN_TRIGGER_DISTANCE_M = 6.0
MAX_TRIGGER_MISS_M = 5.0
MOVING_METRES_PER_SECOND = 4.0
STOPPED_METRES_PER_SECOND = 1.0
REQUIRED_FRACTION = 0.7
SAMPLE_SECONDS = 0.25


def trigger_points(xml_path: str) -> dict[str, tuple[float, float]]:
    points = {}
    for route in ET.parse(xml_path).getroot().iter("route"):
        for scenario in route.iter("scenario"):
            if scenario.get("name", "").endswith("_injected"):
                point = scenario.find("trigger_point")
                points[route.get("id")] = (float(point.get("x")), float(point.get("y")))
    return points


def first_index(condition: np.ndarray) -> int | None:
    hits = np.flatnonzero(condition)
    return int(hits[0]) if hits.size else None


def encounter(shard: Path, trigger: tuple[float, float], start_seconds: float) -> dict:
    data = np.load(shard)
    x, y, speed = (data[key].astype(float) for key in ("ego_x", "ego_y", "ego_speed"))
    misses = np.hypot(x - trigger[0], y - trigger[1])
    at_trigger = int(np.argmin(misses))
    reading = {"trigger_miss_m": round(float(misses[at_trigger]), 1), "speed_at_trigger": round(float(speed[at_trigger]), 2),
               "min_walker_m": round(float(np.nanmin(data["pedestrian_distance"])), 2)
               if np.isfinite(data["pedestrian_distance"]).any() else None}
    if misses[at_trigger] > MAX_TRIGGER_MISS_M:
        return reading
    travelled = np.r_[0.0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    to_crossing = travelled[at_trigger] + CROSSING_AFTER_TRIGGER_M - travelled
    time_to_crossing = np.divide(to_crossing, speed, out=np.full_like(speed, np.inf), where=speed > 0.1)
    started = (to_crossing < MIN_TRIGGER_DISTANCE_M) | (time_to_crossing < start_seconds)
    start = first_index(started & (np.arange(len(speed)) >= at_trigger))
    if start is None:
        return reading
    reading |= {"speed_at_walker_start": round(float(speed[start]), 2), "to_crossing_at_start_m": round(float(to_crossing[start]), 1)}
    stop = first_index((speed < STOPPED_METRES_PER_SECOND) & (np.arange(len(speed)) >= start))
    if stop is not None:
        reading |= {"stop_after_start_s": (stop - start) * SAMPLE_SECONDS, "to_crossing_at_stop_m": round(float(to_crossing[stop]), 1)}
    return reading


def route_row(route: dict, shards: Path, triggers: dict[str, tuple[float, float]]) -> dict:
    route_id = route["id"]
    is_slice = route_id[-2] == "7"
    infractions = route.get("infractions", {})
    row = {"id": route_id, "arm": "slice" if is_slice else "neighbourhood", "base": route_id[:-2], "success": route.get("success"),
           "status": route.get("status"), "infractions": {name: count for name, count in infractions.items() if count},
           "walker_struck": infractions.get("collisions_pedestrian", 0) > 0, "duration_s": route.get("duration_game"),
           "stationary_s": route.get("longest_stationary_sim_seconds")}
    shard = shards / f"{route_id}.npz"
    if shard.is_file():
        row |= encounter(shard, triggers[route_id], SLICE_START_S if is_slice else NEIGHBOURHOOD_START_S)
    return row


def met_at_speed(row: dict) -> bool:
    return (row.get("trigger_miss_m", np.inf) <= MAX_TRIGGER_MISS_M
            and row.get("speed_at_trigger", 0.0) > MOVING_METRES_PER_SECOND)


def check_summary(rows: list[dict]) -> dict:
    scored = [row for row in rows if row["arm"] == "slice" and row["success"] is not None]
    passing = sum(map(met_at_speed, scored))
    return {"passing": passing, "scored_slices": len(scored), "required_fraction": REQUIRED_FRACTION,
            "holds": bool(scored) and passing / len(scored) >= REQUIRED_FRACTION}


def main() -> None:
    folder = Path("results/savio") / NAME
    triggers = trigger_points(f"configs/rollout/{NAME}.xml")
    routes = [json.loads(line) for line in (folder / "routes.jsonl").read_text().splitlines()]
    rows = [route_row(route, folder / "shards", triggers) for route in routes]
    Path(sys.argv[1]).write_text(json.dumps({"check": check_summary(rows), "routes": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
