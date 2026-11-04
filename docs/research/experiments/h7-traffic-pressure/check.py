"""H7's C24 check and per-route reading, from each screen's shards and route file.

Run on Savio from the repo root with the policy venv:
    .runtime/policy-venv/bin/python docs/research/experiments/h7-traffic-pressure/check.py OUT.json [GAP=CONFIG_NAME ...]
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

NAMES = {"P14": "step5-pilot-p14-screen", "P15": "step5-pilot-p15-screen", "P16": "step5-pilot-p16-screen"}
MAX_TRIGGER_MISS_M = 5.0
TRAFFIC_WINDOW_SAMPLES = 40  # 10 s at one sample per 0.25 s
REQUIRED_FRACTION = 0.7


def trigger_points(xml_path: str) -> dict[str, tuple[float, float]]:
    points = {}
    for route in ET.parse(xml_path).getroot().iter("route"):
        point = next(route.iter("scenario")).find("trigger_point")
        points[route.get("id")] = (float(point.get("x")), float(point.get("y")))
    return points


def encounter(shard: Path, trigger: tuple[float, float]) -> dict:
    data = np.load(shard)
    x, y, speed, vehicles = (data[key].astype(float) for key in ("ego_x", "ego_y", "ego_speed", "vehicles_50m"))
    misses = np.hypot(x - trigger[0], y - trigger[1])
    at_trigger = int(np.nanargmin(misses))
    window = vehicles[at_trigger:at_trigger + TRAFFIC_WINDOW_SAMPLES]
    return {"trigger_miss_m": round(float(misses[at_trigger]), 1), "speed_at_trigger": round(float(speed[at_trigger]), 2),
            "most_vehicles_50m": int(np.nanmax(window)) if np.isfinite(window).any() else 0,
            "mean_speed": round(float(np.nanmean(speed)), 2), "state_error_samples": int(np.isnan(x).sum()),
            "biggest_lead_closing_m_s": round(float(np.nanmax(np.abs(data["lead_relative_speed"]))), 2)
            if np.isfinite(data["lead_relative_speed"]).any() else None}


def route_row(route: dict, shards: Path, triggers: dict[str, tuple[float, float]]) -> dict:
    route_id = route["id"]
    row = {"id": route_id, "arm": "slice" if route_id[-2] == "7" else "neighbourhood", "base": route_id[:-2],
           "scenario": route.get("scenario"), "success": route.get("success"), "status": route.get("status"),
           "infractions": {name: count for name, count in route.get("infractions", {}).items() if count},
           "duration_s": route.get("duration_game"), "stationary_s": route.get("longest_stationary_sim_seconds")}
    shard = shards / f"{route_id}.npz"
    return row | encounter(shard, triggers[route_id]) if shard.is_file() else row


def met_traffic(row: dict) -> bool:
    return row.get("trigger_miss_m", np.inf) <= MAX_TRIGGER_MISS_M and row.get("most_vehicles_50m", 0) > 0


def check_summary(rows: list[dict]) -> dict:
    scored = [row for row in rows if row["arm"] == "slice" and row["success"] is not None]
    passing = sum(map(met_traffic, scored))
    return {"passing": passing, "scored_slices": len(scored), "required_fraction": REQUIRED_FRACTION,
            "holds": bool(scored) and passing / len(scored) >= REQUIRED_FRACTION}


def gap_rows(name: str) -> list[dict]:
    folder = Path("results/savio") / name
    triggers = trigger_points(f"configs/rollout/{name}.xml")
    routes = [json.loads(line) for line in (folder / "routes.jsonl").read_text().splitlines()]
    return [route_row(route, folder / "shards", triggers) for route in routes]


def main() -> None:
    names = dict(pair.split("=") for pair in sys.argv[2:]) or NAMES
    table = {gap: gap_rows(name) for gap, name in names.items()}
    report = {gap: {"check": check_summary(rows), "routes": rows} for gap, rows in table.items()}
    Path(sys.argv[1]).write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
