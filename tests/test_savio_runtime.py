"""Savio runtime behaviour that a cluster job cannot cheaply rediscover."""
import hashlib
import socket
import subprocess

import pytest

import run_savio
from run_savio import CARLA_ROOT, GpuMonitor, free_port_block, job_ports, server_command, torch_threads
from setup_savio import download


def hold_port_below(limit: int) -> tuple[socket.socket, int]:
    """Port 0 can return an ephemeral port above the CARLA search range, so hold one inside it."""
    for port in range(30001, limit):
        held = socket.socket()
        try:
            held.bind(("", port))
            return held, port
        except OSError:
            held.close()
    raise RuntimeError("no free port to hold")


def test_occupied_port_moves_the_whole_carla_block(tmp_path):
    held, taken = hold_port_below(59000)
    with held:
        first = free_port_block(3, taken - 1)
    assert taken not in range(first, first + 3)


def test_host_server_runs_carla_directly():
    command = server_command("Epic", 20000, None)
    assert command[0] == str(CARLA_ROOT / "CarlaUE4.sh")
    assert "-RenderOffScreen" in command and "-carla-rpc-port=20000" in command


def test_container_fallback_binds_the_scratch_carla_tree():
    command = server_command("Epic", 20000, "/scratch/carla.sif")
    assert command[:6] == ["apptainer", "exec", "--nv", "--bind", str(CARLA_ROOT), "/scratch/carla.sif"]
    assert command[6] == str(CARLA_ROOT / "CarlaUE4.sh")


def test_peak_vram_is_the_maximum_and_utilization_the_mean_over_samples(monkeypatch):
    samples = iter(["GPU-a, NVIDIA RTX A5000, 6000, 20\n", "GPU-a, NVIDIA RTX A5000, 11776, 70\n",
                    "GPU-a, NVIDIA RTX A5000, 3000, 30\n"])
    monkeypatch.setattr(run_savio.subprocess, "run",
                        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, next(samples)))
    monitor = GpuMonitor()
    for _ in range(3):
        monitor.sample()
    report = monitor.report()
    assert report["whole_stack_peak_vram"] == 11.5
    assert report["gpus"] == [{"uuid": "GPU-a", "name": "NVIDIA RTX A5000", "peak_mib": 11776,
                               "mean_utilization_percent": 40.0, "samples": 3}]


def test_unsampled_monitor_reports_no_peak():
    assert GpuMonitor().report()["whole_stack_peak_vram"] is None


def test_corrupt_download_is_deleted_and_a_verified_one_is_not_refetched(tmp_path):
    source = tmp_path / "archive.tar.gz"
    source.write_bytes(b"carla" * 100)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target = tmp_path / "downloads/archive.tar.gz"

    with pytest.raises(ValueError, match="checksum differs"):
        download(source.as_uri(), target, 500, "0" * 64)
    assert not target.exists() and not target.with_name("archive.tar.gz.part").exists()

    download(source.as_uri(), target, 500, digest)
    assert target.read_bytes() == source.read_bytes()
    source.unlink()
    download(source.as_uri(), target, 500, digest)


def test_short_download_is_rejected(tmp_path):
    source = tmp_path / "archive.tar.gz"
    source.write_bytes(b"x" * 10)
    with pytest.raises(ValueError, match="expected 20 bytes"):
        download(source.as_uri(), tmp_path / "out/archive.tar.gz", 20, None)


def test_route_sample_array_covers_exactly_the_configured_routes():
    import re
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[1]
    routes = yaml.safe_load((root / "configs/rollout/savio-mac-paired.yaml").read_text())["routes"]
    header = (root / "scripts/route_sample.sbatch").read_text()
    first, last = map(int, re.search(r"#SBATCH --array=(\d+)-(\d+)", header).groups())
    assert (first, last) == (0, len(routes) - 1)
    assert len(set(routes)) == len(routes)


def test_route_sample_ids_exist_in_the_pinned_routes_file():
    from pathlib import Path

    import yaml
    from route_run import ROUTES, route_from_xml
    if not ROUTES.is_file():
        pytest.skip("pinned routes file not installed")
    root = Path(__file__).resolve().parents[1]
    for route_id in yaml.safe_load((root / "configs/rollout/savio-mac-paired.yaml").read_text())["routes"]:
        assert route_from_xml(route_id)["id"] == route_id


def test_step2_config_runs_every_pinned_route_once_in_file_order():
    import xml.etree.ElementTree as ET
    from pathlib import Path

    import yaml
    from route_run import ROUTES
    if not ROUTES.is_file():
        pytest.skip("pinned routes file not installed")
    root = Path(__file__).resolve().parents[1]
    routes = yaml.safe_load((root / "configs/rollout/step2-bench2drive220.yaml").read_text())["routes"]
    assert routes == [route.get("id") for route in ET.parse(ROUTES).getroot().iter("route")]
    assert len(routes) == 220


def test_capture_setting_selects_the_capture_agent():
    from route_run import AGENT, agent_and_capture_environment
    assert agent_and_capture_environment(None) == (AGENT, {})
    agent, environment = agent_and_capture_environment(10)
    assert agent.name == "capture_agent.py" and environment == {"SIMLINGO_CAPTURE_EVERY": "10"}


def test_two_slots_of_one_job_get_disjoint_ports(monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "39732999")
    first, second = job_ports(0), job_ports(1)
    used = [set(range(ports.rpc, ports.rpc + 3)) | {ports.traffic_manager} for ports in (first, second)]
    assert not used[0] & used[1]
    assert max(ports.traffic_manager for ports in (first, second)) < 60000


def test_slots_split_the_job_cpus_for_torch(monkeypatch):
    monkeypatch.setenv("SLURM_CPUS_PER_TASK", "8")
    assert torch_threads(1) == 8 and torch_threads(2) == 4 and torch_threads(16) == 1


def test_silent_evaluator_is_stopped_and_reported(tmp_path):
    import sys
    import time

    from route_run import run_evaluator
    command = [sys.executable, "-c", "print('loading', flush=True); import time; time.sleep(60)"]
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="printed nothing"):
        run_evaluator(tmp_path, command, {}, silence_limit_seconds=1)
    assert time.monotonic() - started < 20
    assert (tmp_path / "evaluator.log").read_text() == "loading\n"


def test_chatty_evaluator_finishes_normally(tmp_path):
    import sys

    from route_run import run_evaluator
    command = [sys.executable, "-c", "import time\nfor i in range(4):\n    print(i, flush=True); time.sleep(0.4)"]
    assert run_evaluator(tmp_path, command, {}, silence_limit_seconds=1) is True
