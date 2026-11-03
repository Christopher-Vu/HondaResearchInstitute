"""H13's C24 check, from the screen's shards, frames and task logs.

Run on Savio from the repo root with the policy venv:
    .runtime/policy-venv/bin/python docs/research/experiments/h13-cross-family-gap/check.py CONFIG_NAME ARRAY_JOB OUT.json
"""

import json
import sys
from pathlib import Path

EXPERIMENTS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(EXPERIMENTS / "h7-traffic-pressure"), str(EXPERIMENTS / "h5-interactional-screen")]

from check import encounter, met_traffic, trigger_points  # noqa: E402
from manipulation_check import lowest_black_fraction, run_order  # noqa: E402

FIRST_ROUTES = 5
MIN_BLACK_FRACTION = 0.99
MIN_FRACTION_MEETING_TRAFFIC = 0.7


def route_row(entry: dict, route: dict, name: str, job: str, triggers: dict) -> dict:
    route_id = entry["id"]
    shard = Path("results/savio") / name / "shards" / f"{route_id}.npz"
    return {"id": route_id, "base": entry["base_id"], "scenario": entry["scenario"], "role": entry["role"],
            "preset_sun": entry["weather"]["sun_altitude_angle"], "success": route.get("success"),
            "status": route.get("status"), "infractions": {key: count for key, count in route.get("infractions", {}).items() if count},
            "stationary_s": route.get("longest_stationary_sim_seconds"), "duration_s": route.get("duration_game"),
            "lowest_black_fraction": lowest_black_fraction(Path("results/savio") / job / f"route-{route_id}",
                                                           tuple(entry["sensor"]["camera_fault"]["box"])),
            **(encounter(shard, triggers[route_id]) if shard.is_file() else {})}


def main() -> None:
    name, job, output = sys.argv[1:4]
    manifest = json.loads(Path(f"configs/rollout/{name}.manifest.json").read_text())
    routes = {row["id"]: row for row in map(json.loads, (Path("results/savio") / name / "routes.jsonl").read_text().splitlines())}
    triggers = trigger_points(f"configs/rollout/{name}.xml")
    rows = {entry["id"]: route_row(entry, routes[entry["id"]], name, job, triggers) for entry in manifest if entry["id"] in routes}
    scored = [rows[route_id] for route_id in run_order(job)
              if route_id in rows and rows[route_id]["role"] == "pilot_slice" and rows[route_id]["success"] is not None]
    first = scored[:FIRST_ROUTES]
    meeting = sum(map(met_traffic, scored))
    check = {"first_routes": [row["id"] for row in first],
             "black_holds": len(first) == FIRST_ROUTES and all((row["lowest_black_fraction"] or 0) >= MIN_BLACK_FRACTION for row in first),
             "meeting_traffic": meeting, "scored_slices": len(scored),
             "traffic_holds": bool(scored) and meeting / len(scored) >= MIN_FRACTION_MEETING_TRAFFIC}
    Path(output).write_text(json.dumps({"check": check, "routes": list(rows.values())}, indent=1) + "\n")


if __name__ == "__main__":
    main()
