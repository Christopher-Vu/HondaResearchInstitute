"""Savio runtime behaviour that a cluster job cannot cheaply rediscover."""
import hashlib
import socket
import subprocess

import pytest

import run_savio
from run_savio import CARLA_ROOT, GpuMemoryMonitor, free_port_block, server_command
from setup_savio import download


def test_occupied_port_moves_the_whole_carla_block(tmp_path):
    with socket.socket() as held:
        held.bind(("", 0))
        taken = held.getsockname()[1]
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


def test_peak_vram_is_the_maximum_over_samples(monkeypatch):
    samples = iter(["GPU-a, NVIDIA RTX A5000, 6000\n", "GPU-a, NVIDIA RTX A5000, 11776\n",
                    "GPU-a, NVIDIA RTX A5000, 3000\n"])
    monkeypatch.setattr(run_savio.subprocess, "run",
                        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, next(samples)))
    monitor = GpuMemoryMonitor()
    for _ in range(3):
        monitor.sample()
    report = monitor.report()
    assert report["whole_stack_peak_vram"] == 11.5
    assert report["gpus"] == [{"uuid": "GPU-a", "name": "NVIDIA RTX A5000", "peak_mib": 11776}]


def test_unsampled_monitor_reports_no_peak():
    assert GpuMemoryMonitor().report()["whole_stack_peak_vram"] is None


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
