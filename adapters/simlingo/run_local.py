"""Run one visible SimLingo route with a fresh, dedicated Mac CARLA server."""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import signal
import socket
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from artifacts import sha256, verify_artifacts
from route_run import (AGENT, CHECKPOINT, ROOT, SOURCE, Ports, check_external_server_patch, check_route,
                       evaluator_command, policy_environment, route_from_xml, run_evaluator, summarize,
                       wait_for_server)

APP = Path.home() / "Applications/Sikarugir/CARLA.app"
CAMERA_APP = ROOT / ".runtime/CARLA Camera.app"
PORTS = Ports(rpc=2000, traffic_manager=8000)


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
    if port_in_use():
        raise RuntimeError("Port 2000 is occupied. Close the existing CARLA server before starting this run.")
    if not (APP / "Contents/MacOS/launcher").is_file():
        raise FileNotFoundError(f"CARLA wrapper is missing: {APP}")
    manifest = verify_artifacts(SOURCE, CHECKPOINT)
    wheel = ROOT / manifest["local_mac"]["client"]["wheel"]
    if sha256(wheel) != manifest["local_mac"]["client"]["sha256"]:
        raise ValueError("Native CARLA wheel checksum differs from the artifact manifest")
    check_external_server_patch()
    check_route(config)
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


def main() -> None:
    for termination in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(termination, stop_on_signal)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rollout/local-mac.yaml")
    parser.add_argument("--no-view", action="store_true")
    parser.add_argument("--route", help="Bench2Drive route id; town and scenario come from the routes file")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capture-every", type=int,
                        help="record Step 3 activations each step and replay inputs every N steps")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    if args.route:
        config["route"].update(route_from_xml(args.route))
    manifest = preflight(config)
    output = args.output or ROOT / "results/local-mac" / datetime.now().strftime("%Y%m%d-%H%M%S")
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
            versions = wait_for_server(PORTS.rpc)
            extra = {"PYTORCH_ENABLE_MPS_FALLBACK": "1", "__PYVENV_LAUNCHER__": sys.executable}
            agent = AGENT
            if args.capture_every:
                extra["SIMLINGO_CAPTURE_EVERY"] = str(args.capture_every)
                agent = AGENT.with_name("capture_agent.py")
            environment = policy_environment(
                output, config["policy"]["device"], ROOT / ".runtime/carla-native/PythonAPI/carla",
                not args.no_view, extra)
            command = evaluator_command(output, config, PORTS, int(config["policy"]["cpu_threads"]), agent)
            if not run_evaluator(output, command, environment):
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
