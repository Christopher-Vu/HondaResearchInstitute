"""H13's C24 check, from the screen's shards, frames and task logs.

Run on Savio from the repo root with the policy venv:
    .runtime/policy-venv/bin/python docs/research/experiments/h13-cross-family-gap/check.py CONFIG_NAME FIRST_ARRAY_JOB OUT.json
It prints only the check. OUT.json also holds each route's outcome, so read the check before opening it.
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


def scenario_was_dropped(route_dir: Path) -> bool:
    """The leaderboard drops a scenario whose trigger is off the route and scores the drive anyway."""
    log = route_dir / "evaluator.log"
    return log.is_file() and "Ignoring scenario" in log.read_text(errors="replace")


def route_row(entry: dict, route: dict, name: str, triggers: dict) -> dict:
    route_id = entry["id"]
    route_dir = Path("results/savio") / route["job"] / f"route-{route_id}"
    shard = Path("results/savio") / name / "shards" / f"{route_id}.npz"
    return {"id": route_id, "job": route["job"], "base": entry["base_id"], "scenario": entry["scenario"], "role": entry["role"],
            "preset_sun": entry["weather"]["sun_altitude_angle"], "success": route.get("success"),
            "status": route.get("status"), "infractions": {key: count for key, count in route.get("infractions", {}).items() if count},
            "stationary_s": route.get("longest_stationary_sim_seconds"), "duration_s": route.get("duration_game"),
            "scenario_dropped": scenario_was_dropped(route_dir), "has_shard": shard.is_file(),
            "lowest_black_fraction": lowest_black_fraction(route_dir, tuple(entry["sensor"]["camera_fault"]["box"])),
            **(encounter(shard, triggers[route_id]) if shard.is_file() else {})}


def scored_slices_in_run_order(rows: dict, first_job: str) -> list[dict]:
    """Slices with a driving outcome, in the order they first ran; refuses when the data to judge them is missing."""
    scored = {row["id"]: row for row in rows.values() if row["role"] == "pilot_slice" and row["success"] is not None}
    if not scored:
        raise SystemExit("no scored slice: this is missing data, not a failed check")
    jobs = dict.fromkeys([first_job, *sorted(row["job"] for row in scored.values())])
    order = list(dict.fromkeys(route_id for job in jobs for route_id in run_order(job)))
    in_order = [scored[route_id] for route_id in order if route_id in scored]
    problems = {"without_shard": sorted(key for key, row in scored.items() if not row["has_shard"]),
                "not_in_task_logs": sorted(set(scored) - set(order)),
                "first_array_log_missing": not run_order(first_job),
                "fewer_than_first_routes": len(scored) < FIRST_ROUTES,
                "first_routes_without_frames": [row["id"] for row in in_order[:FIRST_ROUTES] if row["lowest_black_fraction"] is None]}
    if any(problems.values()):
        raise SystemExit(f"cannot judge the check, data is missing: {problems}")
    return in_order


def check_summary(rows: dict, scored: list[dict]) -> dict:
    first = scored[:FIRST_ROUTES]
    meeting = sum(met_traffic(row) and not row["scenario_dropped"] for row in scored)
    return {"first_routes": [row["id"] for row in first],
            "black_holds": all(row["lowest_black_fraction"] >= MIN_BLACK_FRACTION for row in first),
            "meeting_traffic": meeting, "scored_slices": len(scored),
            "traffic_holds": meeting / len(scored) >= MIN_FRACTION_MEETING_TRAFFIC,
            "scenarios_dropped": sorted(row["id"] for row in rows.values() if row["scenario_dropped"]),
            "state_error_samples": sum(row.get("state_error_samples", 0) for row in rows.values())}


def main() -> None:
    name, first_job, output = sys.argv[1:4]
    manifest = json.loads(Path(f"configs/rollout/{name}.manifest.json").read_text())
    routes = {row["id"]: row for row in map(json.loads, (Path("results/savio") / name / "routes.jsonl").read_text().splitlines())}
    triggers = trigger_points(f"configs/rollout/{name}.xml")
    rows = {entry["id"]: route_row(entry, routes[entry["id"]], name, triggers) for entry in manifest if entry["id"] in routes}
    check = check_summary(rows, scored_slices_in_run_order(rows, first_job))
    Path(output).write_text(json.dumps({"check": check, "routes": list(rows.values())}, indent=1) + "\n")
    print(json.dumps(check, indent=1))


if __name__ == "__main__":
    main()
