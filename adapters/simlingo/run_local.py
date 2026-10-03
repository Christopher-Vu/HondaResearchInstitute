"""Run one visible SimLingo route with a fresh, dedicated Mac CARLA server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import signal
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".runtime/simlingo"
CHECKPOINT = ROOT / "checkpoints/simlingo/checkpoints/epoch=013.ckpt/pytorch_model.pt"
APP = Path.home() / "Applications/Sikarugir/CARLA.app"
CAMERA_APP = ROOT / ".runtime/CARLA Camera.app"
ROUTES = SOURCE / "leaderboard/data/bench2drive220.xml"


def port_in_use() -> bool:
    with socket.socket() as connection:
        connection.settimeout(1)
        return connection.connect_ex(("localhost", 2000)) == 0


def stop_on_signal(_signum: int, _frame: Any) -> None:
    raise KeyboardInterrupt


@contextmanager
def keep_awake() -> Iterator[None]:
    process = subprocess.Popen(["/usr/bin/caffeinate", "-di", "-w", str(os.getpid())])
    try:
        yield
    finally:
        process.terminate()
        process.wait(timeout=5)


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    if (ROOT / ".runtime/maps-installing").is_file():
        raise RuntimeError("CARLA map installation is in progress; wait for its integrity check to finish.")
    from verify_checkpoint import verify_artifacts

    if port_in_use():
        raise RuntimeError("Port 2000 is occupied. Close the existing CARLA server before starting this run.")
    if not (APP / "Contents/MacOS/launcher").is_file():
        raise FileNotFoundError(f"CARLA wrapper is missing: {APP}")
    manifest = verify_artifacts(SOURCE, CHECKPOINT)
    wheel = ROOT / manifest["local_mac"]["client"]["wheel"]
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != manifest["local_mac"]["client"]["sha256"]:
        raise ValueError("Native CARLA wheel checksum differs from the artifact manifest")
    subprocess.run(["git", "-C", str(SOURCE), "apply", "--reverse", "--check",
                    str(ROOT / "adapters/simlingo/patches/external-server.patch")], check=True)
    selected = ET.parse(ROUTES).find(f".//route[@id='{config['route']['id']}']")
    if selected is None or selected.get("town") != config["route"]["town"]:
        raise ValueError("The configured route is missing or its town differs from the pinned routes file")
    scenario = selected.find("scenarios/scenario")
    if scenario is None or scenario.get("type") != config["route"]["scenario"]:
        raise ValueError("The authored scenario does not match the local config")
    return manifest


def configure_wrapper(config: dict[str, Any]) -> None:
    path = APP / "Contents/Info.plist"
    values = plistlib.loads(path.read_bytes())
    values["D3DMETAL"], values["DXVK"] = 1, 0
    values["CLI Custom Commands"] = ""
    values["Program Flags"] = (
        f"-quality-level={config['simulator']['quality']} -nosound -windowed "
        "-ResX=1280 -ResY=720 -carla-rpc-port=2000"
    )
    path.write_bytes(plistlib.dumps(values))


def prepare_camera_app() -> None:
    source = Path(sys.base_prefix) / "Resources/Python.app"
    shutil.copytree(source, CAMERA_APP, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("_CodeSignature"))
    path = CAMERA_APP / "Contents/Info.plist"
    values = plistlib.loads(path.read_bytes())
    values.update({"CFBundleIdentifier": "local.hondaresearch.carla-camera",
                   "CFBundleName": "CARLA Camera", "CFBundleDisplayName": "CARLA Camera"})
    path.write_bytes(plistlib.dumps(values))
    subprocess.run(["codesign", "--force", "--sign", "-", str(CAMERA_APP)], check=True)


def wait_for_server() -> dict[str, str]:
    import carla

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            client = carla.Client("localhost", 2000)
            client.set_timeout(2)
            version = client.get_server_version()
            world = client.get_world()
            world.get_map()
            if version != "0.9.15":
                raise ValueError(f"Expected CARLA 0.9.15; server reports {version}")
            return {"server": version, "client": client.get_client_version()}
        except RuntimeError:
            time.sleep(1)
    raise TimeoutError("CARLA did not become ready within 90 seconds; inspect server.log")


def environment(output: Path, config: dict[str, Any], visible: bool) -> dict[str, str]:
    values = os.environ.copy()
    paths = [SOURCE, SOURCE / "team_code", SOURCE / "Bench2Drive/leaderboard",
             SOURCE / "Bench2Drive/scenario_runner", ROOT / ".runtime/carla-native/PythonAPI/carla"]
    values.update({
        "HF_HUB_OFFLINE": "1", "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        "SIMLINGO_DEVICE": config["policy"]["device"],
        "SIMLINGO_BASE_MODEL": str(ROOT / ".runtime/InternVL2-1B"),
        "SIMLINGO_EVIDENCE": str(output), "SIMLINGO_VISIBLE": "1" if visible else "0",
        "PYGAME_HIDE_SUPPORT_PROMPT": "1", "WORK_DIR": str(SOURCE),
        "SCENARIO_RUNNER_ROOT": str(SOURCE / "Bench2Drive/scenario_runner"),
        "SAVE_PATH": str(output) + "/", "PYTHONPATH": os.pathsep.join(map(str, paths)),
        "__PYVENV_LAUNCHER__": sys.executable,
    })
    return values


def evaluator_command(output: Path, config: dict[str, Any]) -> list[str]:
    evaluator = SOURCE / "Bench2Drive/leaderboard/leaderboard/leaderboard_evaluator.py"
    bootstrap = ("import runpy,torch; "
                 f"torch.set_num_threads({int(config['policy']['cpu_threads'])}); "
                 f"runpy.run_path({str(evaluator)!r},run_name='__main__')")
    return [sys.executable, "-u", "-c", bootstrap, "--external-server",
            "--host", "localhost", "--port", "2000", "--traffic-manager-port", "8000",
            "--traffic-manager-seed", str(config["route"]["seed"]),
            "--timeout", str(config["simulator"]["timeout_seconds"]), "--debug", "2",
            "--routes", str(ROUTES), "--routes-subset", config["route"]["id"],
            "--agent", str(ROOT / "adapters/simlingo/visible_agent.py"),
            "--agent-config", str(CHECKPOINT) + "+agent",
            "--checkpoint", str(output / "result.json"),
            "--debug-checkpoint", str(output / "live.txt")]


def run_evaluator(output: Path, config: dict[str, Any], visible: bool) -> bool:
    process = subprocess.Popen(evaluator_command(output, config), cwd=ROOT,
                               env=environment(output, config, visible), stdout=subprocess.PIPE,
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
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def summarize(output: Path, config: dict[str, Any], versions: dict[str, str]) -> dict[str, Any]:
    result = json.loads((output / "result.json").read_text())
    records = result["_checkpoint"]["records"]
    if "Skipping scenario" in (output / "evaluator.log").read_text():
        raise RuntimeError("The authored scenario was skipped; this run is invalid")
    if result["entry_status"] != "Finished" or len(records) != 1:
        raise RuntimeError("Bench2Drive did not finish one valid route")
    status = records[0]["status"]
    valid_outcomes = {"Completed", "Perfect", "Failed - Agent timed out",
                      "Failed - Agent deviated from the route", "Failed - Agent got blocked"}
    if status not in valid_outcomes:
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
    (output / "readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    for termination in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(termination, stop_on_signal)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rollout/local-mac.yaml")
    parser.add_argument("--no-view", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    manifest = preflight(config)
    output = ROOT / "results/local-mac" / datetime.now().strftime("%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    (output / "artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n")
    configure_wrapper(config)
    prepare_camera_app()
    print(f"Starting CARLA. Evidence will be saved in {output}", flush=True)
    try:
        with keep_awake():
            with (output / "server.log").open("w") as log:
                subprocess.run([str(APP / "Contents/MacOS/launcher")], stdout=log, stderr=subprocess.STDOUT,
                               timeout=30, check=True)
            versions = wait_for_server()
            if not run_evaluator(output, config, not args.no_view):
                print(f"CARLA stopped by user. Partial evidence is in {output}; no readiness result was issued.")
                return
            print(json.dumps(summarize(output, config, versions), indent=2))
    finally:
        prefix = APP / "Contents/SharedSupport/prefix"
        wine_environment = os.environ.copy()
        wine_environment["WINEPREFIX"] = str(prefix)
        wine_environment["DYLD_FALLBACK_LIBRARY_PATH"] = str(APP / "Contents/Frameworks")
        subprocess.run([str(APP / "Contents/SharedSupport/wine/bin/wineserver"), "-k"],
                       env=wine_environment, timeout=10, check=False)


if __name__ == "__main__":
    main()
