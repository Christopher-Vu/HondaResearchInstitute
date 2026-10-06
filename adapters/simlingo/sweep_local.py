"""Run a seeded one-route-per-scenario-type sample of Bench2Drive-220 on the Mac, one route at a time.

    .runtime/policy-venv/bin/python adapters/simlingo/sweep_local.py --until 08:45

Each route uses `run_local.py` with a fresh server. Rerunning with the same `--output` resumes,
skipping routes already in `routes.jsonl`. A route is retried once only when it failed
before the evaluator started (launcher or server bring-up), so driving outcomes are never re-rolled.
Results are integration evidence on this Mac; they do not reproduce the 220-route benchmark score.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import signal
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from route_run import ROOT, ROUTES

PENALIZED = ("collisions_layout", "collisions_pedestrian", "collisions_vehicle", "red_light",
             "stop_infraction", "outside_route_lanes", "yield_emergency_vehicle_infractions",
             "scenario_timeouts", "route_dev", "vehicle_blocked", "route_timeout")


def sample_routes(seed: int) -> list[dict[str, str]]:
    by_scenario: dict[str, list[dict[str, str]]] = {}
    for route in ET.parse(ROUTES).getroot().iter("route"):
        scenario = route.find("scenarios/scenario")
        assert scenario is not None
        by_scenario.setdefault(str(scenario.get("type")), []).append(
            {"id": str(route.get("id")), "town": str(route.get("town")), "scenario": str(scenario.get("type"))})
    rng = random.Random(seed)
    chosen = [rng.choice(by_scenario[name]) for name in sorted(by_scenario)]
    rng.shuffle(chosen)
    return chosen


def wait_for_free_port(port: int = 2000, seconds: float = 60) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with socket.socket() as connection:
            connection.settimeout(1)
            if connection.connect_ex(("localhost", port)) != 0:
                return True
        time.sleep(2)
    return False


def kill_wineserver() -> None:
    app = Path.home() / "Applications/Sikarugir/CARLA.app"
    environment = os.environ | {"WINEPREFIX": str(app / "Contents/SharedSupport/prefix"),
                                "DYLD_FALLBACK_LIBRARY_PATH": str(app / "Contents/Frameworks")}
    subprocess.run([str(app / "Contents/SharedSupport/wine/bin/wineserver"), "-k"],
                   env=environment, timeout=15, check=False)


def run_once(route_id: str, output: Path, cap_seconds: float, capture_every: int) -> tuple[int | None, float]:
    command = [sys.executable, str(ROOT / "adapters/simlingo/run_local.py"), "--no-view",
               "--route", route_id, "--output", str(output)]
    if capture_every:
        command += ["--capture-every", str(capture_every)]
    started = time.monotonic()
    with (output.parent / f"{output.name}.launcher.log").open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            return process.wait(timeout=cap_seconds), time.monotonic() - started
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            kill_wineserver()
            return None, time.monotonic() - started


def longest_stationary_seconds(controls: Path, still_below: float = 0.1) -> float:
    """Longest run of simulated seconds the ego stood still, from the agent's control log."""
    longest, started = 0.0, None
    rows = [json.loads(line) for line in controls.read_text().splitlines()] if controls.is_file() else []
    for row in rows:
        if abs(row["speed_metres_per_second"]) >= still_below:
            started = None
            continue
        started = row["simulation_seconds"] if started is None else started
        longest = max(longest, row["simulation_seconds"] - started)
    return round(longest, 2)


def creep_events(evaluator_log: Path) -> int:
    """Times SimLingo's own stuck detector forced it forward (40 simulated seconds still, then 15 creep frames)."""
    return evaluator_log.read_text().count("force_move: 0\n") if evaluator_log.is_file() else 0


def route_record(route: dict[str, str], output: Path, exit_code: int | None, wall: float,
                 attempts: int) -> dict[str, Any]:
    record: dict[str, Any] = {**route, "attempts": attempts, "launcher_wall_seconds": round(wall, 1),
                              "wall_capped": exit_code is None, "exit_code": exit_code,
                              "readiness": (output / "readiness.json").is_file(),
                              "longest_stationary_sim_seconds": longest_stationary_seconds(output / "controls.jsonl"),
                              "creep_events": creep_events(output / "evaluator.log")}
    result_path = output / "result.json"
    if result_path.is_file():
        records = json.loads(result_path.read_text()).get("_checkpoint", {}).get("records", [])
        if records:
            entry = records[0]
            counts = {name: len(entry["infractions"].get(name, [])) for name in PENALIZED}
            record.update({
                "status": entry["status"], **entry["scores"], **entry["meta"],
                "infractions": {name: count for name, count in counts.items() if count},
                "success": entry["status"] in {"Completed", "Perfect"} and not any(counts.values()),
            })
    if "status" not in record:
        log = output.parent / f"{output.name}.launcher.log"
        record["error_tail"] = log.read_text().strip().splitlines()[-3:] if log.is_file() else []
    return record


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if "score_composed" in row]
    mean = (lambda key: round(sum(row[key] for row in scored) / len(scored), 2)) if scored else (lambda key: None)
    return {
        "routes_attempted": len(rows), "routes_scored": len(scored),
        "unscored": [{"id": row["id"], "scenario": row["scenario"], "wall_capped": row["wall_capped"],
                      "longest_stationary_sim_seconds": row.get("longest_stationary_sim_seconds")}
                     for row in rows if "score_composed" not in row],
        "mean_driving_score_over_scored": mean("score_composed"),
        "mean_route_completion_over_scored": mean("score_route"),
        "success_rate_over_scored": round(sum(row["success"] for row in scored) / len(scored), 3) if scored else None,
        "mean_real_time_factor": (round(sum(row["duration_game"] / row["duration_system"] for row in scored)
                                        / len(scored), 4) if scored else None),
    }


def deadline_today(clock: str) -> float:
    hour, minute = map(int, clock.split(":"))
    target = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target.timestamp()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--until", required=True, help="local HH:MM after which no new route starts")
    parser.add_argument("--cap-minutes", type=float, default=35)
    parser.add_argument("--capture-every", type=int, default=0, help="passed to run_local.py")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/local-sweep" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    stop_at = deadline_today(args.until)
    args.output.mkdir(parents=True, exist_ok=True)
    plan = sample_routes(args.seed)
    (args.output / "plan.json").write_text(json.dumps({"seed": args.seed, "routes": plan}, indent=2) + "\n")
    finished = args.output / "routes.jsonl"
    rows = [json.loads(line) for line in finished.read_text().splitlines()] if finished.is_file() else []
    done = {row["id"] for row in rows}
    for route in plan:
        if time.time() > stop_at:
            break
        if route["id"] in done:
            continue
        output = args.output / f"route-{route['id']}"
        attempts, exit_code, wall = 0, None, 0.0
        while attempts < 2:
            attempts += 1
            if not wait_for_free_port():
                kill_wineserver()
            if output.exists():
                output.rename(output.with_name(f"{output.name}-attempt{attempts - 1}"))
            exit_code, wall = run_once(route["id"], output, args.cap_minutes * 60, args.capture_every)
            if exit_code == 0 or (output / "evaluator.log").is_file():
                break
        rows.append(route_record(route, output, exit_code, wall, attempts))
        with finished.open("a") as handle:
            handle.write(json.dumps(rows[-1]) + "\n")
        (args.output / "summary.json").write_text(json.dumps(summarize(rows), indent=2) + "\n")
        print(json.dumps({key: rows[-1].get(key) for key in
                          ("id", "scenario", "town", "status", "score_composed", "launcher_wall_seconds")}),
              flush=True)


if __name__ == "__main__":
    main()
