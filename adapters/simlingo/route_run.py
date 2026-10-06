"""Run one Bench2Drive route with SimLingo against an already running CARLA server.

Shared by the Mac launcher (`run_local.py`) and the Savio launcher (`run_savio.py`).
Both use the same repository layout under `.runtime/` and `checkpoints/`.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artifacts import ROOT, load_manifest

SOURCE = ROOT / ".runtime/simlingo"
BASE_MODEL = ROOT / ".runtime/InternVL2-1B"
CHECKPOINT = ROOT / "checkpoints/simlingo/checkpoints/epoch=013.ckpt/pytorch_model.pt"
ROUTES = SOURCE / "leaderboard/data/bench2drive220.xml"
AGENT = ROOT / "adapters/simlingo/visible_agent.py"
VALID_OUTCOMES = {"Completed", "Perfect", "Failed - Agent timed out",
                  "Failed - Agent deviated from the route", "Failed - Agent got blocked"}


@dataclass(frozen=True)
class Ports:
    rpc: int
    traffic_manager: int


def route_from_xml(route_id: str) -> dict[str, str]:
    selected = ET.parse(ROUTES).find(f".//route[@id='{route_id}']")
    if selected is None:
        raise ValueError(f"Route {route_id} is not in the pinned routes file")
    scenario = selected.find("scenarios/scenario")
    if scenario is None:
        raise ValueError(f"Route {route_id} has no authored scenario")
    return {"id": route_id, "town": str(selected.get("town")), "scenario": str(scenario.get("type"))}


def check_route(config: dict[str, Any]) -> None:
    selected = ET.parse(ROUTES).find(f".//route[@id='{config['route']['id']}']")
    if selected is None or selected.get("town") != config["route"]["town"]:
        raise ValueError("The configured route is missing or its town differs from the pinned routes file")
    scenario = selected.find("scenarios/scenario")
    if scenario is None or scenario.get("type") != config["route"]["scenario"]:
        raise ValueError("The authored scenario does not match the config")


def check_external_server_patch() -> None:
    patch = ROOT / load_manifest()["source"]["benchmark_patch"]
    subprocess.run(["git", "-C", str(SOURCE), "apply", "--reverse", "--check", str(patch)], check=True)


def wait_for_server(port: int, seconds: float = 90,
                    server: subprocess.Popen[Any] | None = None) -> dict[str, str]:
    import carla

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if server is not None and server.poll() is not None:
            raise RuntimeError(f"CARLA exited with code {server.returncode} before accepting clients; "
                               "inspect server.log")
        try:
            client = carla.Client("localhost", port)
            client.set_timeout(2)
            version = client.get_server_version()
            client.get_world().get_map()
            if version != "0.9.15":
                raise ValueError(f"Expected CARLA 0.9.15; server reports {version}")
            return {"server": version, "client": client.get_client_version()}
        except RuntimeError:
            time.sleep(1)
    raise TimeoutError(f"CARLA did not become ready within {seconds:.0f} seconds; inspect server.log")


def policy_environment(output: Path, device: str, carla_pythonapi: Path,
                       visible: bool, extra: dict[str, str]) -> dict[str, str]:
    values = os.environ.copy()
    paths = [SOURCE, SOURCE / "team_code", SOURCE / "Bench2Drive/leaderboard",
             SOURCE / "Bench2Drive/scenario_runner", carla_pythonapi]
    values.update({
        "HF_HUB_OFFLINE": "1", "SIMLINGO_DEVICE": device,
        "SIMLINGO_BASE_MODEL": str(BASE_MODEL), "SIMLINGO_EVIDENCE": str(output),
        "SIMLINGO_VISIBLE": "1" if visible else "0", "PYGAME_HIDE_SUPPORT_PROMPT": "1",
        "WORK_DIR": str(SOURCE), "SCENARIO_RUNNER_ROOT": str(SOURCE / "Bench2Drive/scenario_runner"),
        "SAVE_PATH": str(output) + "/", "PYTHONPATH": os.pathsep.join(map(str, paths)),
    })
    values.update(extra)
    return values


def evaluator_command(output: Path, config: dict[str, Any], ports: Ports, cpu_threads: int,
                      agent: Path = AGENT) -> list[str]:
    evaluator = SOURCE / "Bench2Drive/leaderboard/leaderboard/leaderboard_evaluator.py"
    bootstrap = ("import runpy,torch; "
                 f"torch.set_num_threads({cpu_threads}); "
                 f"runpy.run_path({str(evaluator)!r},run_name='__main__')")
    return [sys.executable, "-u", "-c", bootstrap, "--external-server",
            "--host", "localhost", "--port", str(ports.rpc),
            "--traffic-manager-port", str(ports.traffic_manager),
            "--traffic-manager-seed", str(config["route"]["seed"]),
            "--timeout", str(config["simulator"]["timeout_seconds"]), "--debug", "2",
            "--routes", str(ROUTES), "--routes-subset", config["route"]["id"],
            "--agent", str(agent), "--agent-config", str(CHECKPOINT) + "+agent",
            "--checkpoint", str(output / "result.json"),
            "--debug-checkpoint", str(output / "live.txt")]


def stop_process_group(process: subprocess.Popen[Any], grace_seconds: float = 10) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run_evaluator(output: Path, command: list[str], environment: dict[str, str]) -> bool:
    """Return False when the user stopped the run; raise when the evaluator failed."""
    process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        assert process.stdout is not None
        with (output / "evaluator.log").open("w") as log:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
                if (output / "user-stop.json").is_file():
                    return False
        exit_code = process.wait()
        if (output / "user-stop.json").is_file():
            return False
        if exit_code != 0:
            raise RuntimeError("The evaluator exited unsuccessfully; inspect evaluator.log")
        return True
    finally:
        stop_process_group(process)


def summarize(output: Path, config: dict[str, Any], versions: dict[str, str],
              extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result = json.loads((output / "result.json").read_text())
    records = result["_checkpoint"]["records"]
    if "Skipping scenario" in (output / "evaluator.log").read_text():
        raise RuntimeError("The authored scenario was skipped; this run is invalid")
    if result["entry_status"] != "Finished" or len(records) != 1:
        raise RuntimeError("Bench2Drive did not finish one valid route")
    status = records[0]["status"]
    if status not in VALID_OUTCOMES:
        raise RuntimeError(f"The route did not produce a valid driving outcome: {status}")
    controls = [json.loads(line) for line in (output / "controls.jsonl").read_text().splitlines()]
    if not any(row["model_inference"] and row["throttle"] > 0 for row in controls):
        raise RuntimeError("No model-driven throttle was recorded")
    meta = records[0]["meta"]
    report = {
        "scope": config["scope"], "config": config, "versions": versions,
        "integration_verified": True, "route_completed": status in {"Completed", "Perfect"},
        "model_steps": sum(row["model_inference"] for row in controls),
        "wall_seconds": meta["duration_system"], "simulated_seconds": meta["duration_game"],
        "real_time_factor": meta["duration_game"] / meta["duration_system"],
        "whole_stack_peak_vram": None, "infractions": records[0]["infractions"],
        "savio_verified": False, "fail2drive_custom_build_verified": False,
    }
    report.update(extra or {})
    (output / "readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
