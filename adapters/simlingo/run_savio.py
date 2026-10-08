"""Run Step 1 on a Savio GPU node: an off-screen render check, then one SimLingo route.

    .runtime/policy-venv/bin/python adapters/simlingo/run_savio.py render
    .runtime/policy-venv/bin/python adapters/simlingo/run_savio.py route

`scripts/step1.sbatch` runs both, in order, inside one GPU allocation. `--route` replaces the
config's route, which is how `scripts/route_sample.sbatch` runs one route per array task.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

import yaml
from artifacts import verify_artifacts
from route_run import (CHECKPOINT, ROOT, SOURCE, Ports, agent_and_capture_environment,
                       check_external_server_patch, check_route, evaluator_command, policy_environment,
                       route_from_xml, run_evaluator, stop_process_group, summarize, wait_for_server)

CARLA_ROOT = ROOT / ".runtime/carla-linux"
STEP1_CONFIG = ROOT / "configs/rollout/step1-single-route.yaml"
CLUSTER_CONFIG = ROOT / "configs/cluster/savio.yaml"
SERVER_STARTUP_SECONDS = 300
CARLA_PORTS_PER_SERVER = 3


def port_block_is_free(first: int, count: int) -> bool:
    for port in range(first, first + count):
        with socket.socket() as probe:
            try:
                probe.bind(("", port))
            except OSError:
                return False
    return True


def free_port_block(count: int, start: int) -> int:
    """GPU nodes are shared, so another job's CARLA may already hold the default ports."""
    for first in range(start, 60000 - count, count):
        if port_block_is_free(first, count):
            return first
    raise RuntimeError("No free port block for CARLA on this node")


def job_ports() -> Ports:
    job = int(os.environ.get("SLURM_JOB_ID", "0"))
    rpc = free_port_block(CARLA_PORTS_PER_SERVER, 20000 + (job % 1000) * 10)
    return Ports(rpc=rpc, traffic_manager=free_port_block(1, rpc + CARLA_PORTS_PER_SERVER))


def server_command(quality: str, rpc_port: int, container: str | None) -> list[str]:
    command = [str(CARLA_ROOT / "CarlaUE4.sh"), "-RenderOffScreen", "-nosound",
               f"-quality-level={quality}", f"-carla-rpc-port={rpc_port}"]
    if container is None:
        return command
    return ["apptainer", "exec", "--nv", "--bind", str(CARLA_ROOT), container, *command]


def parse_gpu_samples(output: str) -> list[tuple[str, str, int, int]]:
    rows = []
    for line in output.strip().splitlines():
        uuid, name, used, utilization = (part.strip() for part in line.split(","))
        rows.append((uuid, name, int(used), int(utilization)))
    return rows


class GpuMonitor:
    """Samples nvidia-smi so peak memory and mean utilization cover the CARLA server and the policy together.

    Mean utilization says whether one route leaves room to share the GPU with a second one.
    """

    def __init__(self, interval_seconds: float = 1.0) -> None:
        self.interval_seconds = interval_seconds
        self.peaks_mib: dict[str, int] = {}
        self.utilization: dict[str, list[int]] = {}
        self.names: dict[str, str] = {}
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> GpuMonitor:
        self._thread.start()
        return self

    def __exit__(self, kind: type[BaseException] | None, value: BaseException | None,
                 traceback: TracebackType | None) -> None:
        self._stop.set()
        self._thread.join(timeout=30)

    def sample(self) -> None:
        output = subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid,name,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=30).stdout
        for uuid, name, used, utilization in parse_gpu_samples(output):
            self.names[uuid] = name
            self.peaks_mib[uuid] = max(self.peaks_mib.get(uuid, 0), used)
            self.utilization.setdefault(uuid, []).append(utilization)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.sample()
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                self.error = str(error)
                return
            self._stop.wait(self.interval_seconds)

    def report(self) -> dict[str, Any]:
        peak = max(self.peaks_mib.values(), default=None)
        return {
            "whole_stack_peak_vram": None if peak is None else round(peak / 1024, 2),
            "gpus": [{"uuid": uuid, "name": self.names[uuid], "peak_mib": mib,
                      "mean_utilization_percent": round(sum(self.utilization[uuid]) / len(self.utilization[uuid]), 1),
                      "samples": len(self.utilization[uuid])}
                     for uuid, mib in self.peaks_mib.items()],
            "gpu_monitor_error": self.error,
        }


@contextmanager
def carla_server(output: Path, quality: str, container: str | None) -> Iterator[tuple[Ports, dict[str, str]]]:
    ports = job_ports()
    with (output / "server.log").open("w") as log:
        server = subprocess.Popen(server_command(quality, ports.rpc, container), stdout=log,
                                  stderr=subprocess.STDOUT, start_new_session=True)
        try:
            yield ports, wait_for_server(ports.rpc, SERVER_STARTUP_SECONDS, server)
        finally:
            stop_process_group(server, grace_seconds=30)


def job_facts() -> dict[str, Any]:
    return {"environment": "savio", "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "node": socket.gethostname()}


def render(output: Path, config: dict[str, Any], container: str | None) -> dict[str, Any]:
    import carla
    from verify_carla import verify

    with GpuMonitor() as gpu:
        with carla_server(output, config["simulator"]["quality"], container) as (ports, _versions):
            client = carla.Client("localhost", ports.rpc)
            client.set_timeout(30)
            report = verify(client, output, ticks=100)
    report.update({**job_facts(), **gpu.report(), "container": container})
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def route(output: Path, config: dict[str, Any], container: str | None) -> dict[str, Any]:
    manifest = verify_artifacts(SOURCE, CHECKPOINT)
    check_external_server_patch()
    check_route(config)
    (output / "artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n")
    threads = int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count() or 1))
    agent, capture = agent_and_capture_environment(config.get("capture_every"))
    with GpuMonitor() as gpu:
        with carla_server(output, config["simulator"]["quality"], container) as (ports, versions):
            environment = policy_environment(output, config["policy"]["device"],
                                             CARLA_ROOT / "PythonAPI/carla", False, capture)
            run_evaluator(output, evaluator_command(output, config, ports, threads, agent), environment)
    return summarize(output, config, versions,
                     {**job_facts(), **gpu.report(), "container": container, "savio_verified": True})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["render", "route"])
    parser.add_argument("--config", type=Path, default=STEP1_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--route", help="Bench2Drive route id; town and scenario come from the routes file")
    args = parser.parse_args()
    run_id = os.environ.get("SLURM_JOB_ID") or datetime.now().strftime("%Y%m%d-%H%M%S")
    output = args.output or ROOT / "results/savio" / run_id / args.mode
    output.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(args.config.read_text())
    if args.route:
        config["route"].update(route_from_xml(args.route))
    container = yaml.safe_load(CLUSTER_CONFIG.read_text())["carla"]["container"]
    report = (render if args.mode == "render" else route)(output, config, container)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
