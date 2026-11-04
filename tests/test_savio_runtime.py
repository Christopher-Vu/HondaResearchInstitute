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


def test_run_order_spreads_every_role_across_the_array():
    import json
    from collections import Counter
    from pathlib import Path

    import yaml
    from route_run import configured_route_ids, run_order
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/rollout/step4-dev-pool.yaml").read_text())
    role = {entry["id"]: entry["role"] for entry in json.loads((root / config["route"]["manifest"]).read_text())}
    ordered = run_order(configured_route_ids(config))
    assert sorted(ordered) == sorted(role) and run_order(list(role)) == run_order(list(role))
    quarter = len(ordered) // 4
    for start in range(0, 4 * quarter, quarter):
        assert set(Counter(role[route] for route in ordered[start:start + quarter])) == set(role.values())


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
    _agent, environment = agent_and_capture_environment(10, [10])
    assert environment == {"SIMLINGO_CAPTURE_EVERY": "10", "SIMLINGO_TOKEN_LAYERS": "10"}


def test_a_route_with_a_camera_fault_passes_it_to_the_agent(tmp_path, monkeypatch):
    import json
    import route_run
    fault = {"kind": "occlusion", "box": [0.3, 0.2, 0.6, 0.6]}
    (tmp_path / "manifest.json").write_text(json.dumps([{"id": "101", "sensor": {"camera_fault": fault}},
                                                        {"id": "102"}]))
    monkeypatch.setattr(route_run, "ROOT", tmp_path)
    config = {"route": {"manifest": "manifest.json", "id": "101"}}
    assert json.loads(route_run.route_environment(config)["SIMLINGO_CAMERA_FAULT"]) == fault
    assert route_run.route_environment({"route": {"manifest": "manifest.json", "id": "102"}}) == {}
    assert route_run.route_environment({"route": {"id": "101"}}) == {}


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


def test_a_config_can_name_the_fail2drive_server_and_otherwise_gets_stock():
    from run_savio import ROOT, server_root
    assert server_root(None) == CARLA_ROOT and server_root("stock-linux-release") == CARLA_ROOT
    assert server_root("fail2drive") == ROOT / ".runtime/fail2drive-carla"
    assert server_command("Epic", 20000, None, server_root("fail2drive"))[0].endswith("fail2drive-carla/CarlaUE4.sh")



def test_carla_0915_and_its_patch_builds_are_accepted_and_others_refused():
    from route_run import CARLA_0915
    assert all(CARLA_0915.match(v) for v in ("0.9.15", "0.9.15.2", "0.9.15.2-dirty"))
    assert not any(CARLA_0915.match(v) for v in ("0.9.14", "0.9.16", "0.9.150", "1.0"))


def test_local_server_variable_replaces_only_the_stock_server(monkeypatch):
    from pathlib import Path

    from run_savio import server_root
    monkeypatch.setenv("CARLA_SERVER_ROOT", "/tmp/carla-local-7")
    assert server_root(None) == server_root("stock-linux-release") == Path("/tmp/carla-local-7")
    assert server_command("Epic", 20000, None, server_root(None))[0] == "/tmp/carla-local-7/CarlaUE4.sh"
    with pytest.raises(ValueError, match="fail2drive"):
        server_root("fail2drive")


def test_a_staged_named_build_serves_only_configs_naming_that_build(monkeypatch):
    from pathlib import Path

    from run_savio import server_root
    monkeypatch.setenv("CARLA_SERVER_ROOT", "/tmp/f2d-local-7")
    monkeypatch.setenv("CARLA_SERVER_BUILD", "fail2drive")
    assert server_root("fail2drive") == Path("/tmp/f2d-local-7")
    with pytest.raises(ValueError, match="stock"):
        server_root(None)


def test_job_facts_name_the_server_a_run_used():
    from pathlib import Path

    from run_savio import job_facts
    assert job_facts()["carla_server_root"] == str(CARLA_ROOT)
    assert job_facts(Path("/tmp/carla-local-7"))["carla_server_root"] == "/tmp/carla-local-7"


@pytest.fixture
def route_sample(tmp_path):
    """route_sample.sbatch in a submit directory whose fake policy python reports the server it was handed."""
    import os
    import shutil
    import tarfile
    from pathlib import Path
    from types import SimpleNamespace

    python = tmp_path / ".runtime/policy-venv/bin/python"
    python.parent.mkdir(parents=True)
    job = f"pytest-{os.getpid()}"
    environment = {"PATH": os.environ["PATH"], "SLURM_SUBMIT_DIR": str(tmp_path), "SLURM_JOB_ID": job,
                   "SLURM_ARRAY_JOB_ID": "1", "SLURM_ARRAY_TASK_ID": "0", "ROUTE_IDS": "7"}
    command = ["bash", str(Path(__file__).resolve().parents[1] / "scripts/route_sample.sbatch"), "config.yaml"]

    def fake_python(body):
        python.write_text("#!/usr/bin/env bash\n" + body)
        python.chmod(0o755)

    def carla_tar(*names):
        with tarfile.open(tmp_path / "carla.tar", "w") as archive:
            for name in names:
                (tmp_path / name).write_text("#!/usr/bin/env bash\n")
                (tmp_path / name).chmod(0o755)
                archive.add(tmp_path / name, arcname=name)
        return {"CARLA_LOCAL_TAR": str(tmp_path / "carla.tar")}

    def venv_tar():
        (tmp_path / "stagedvenv/bin").mkdir(parents=True)
        staged = tmp_path / "stagedvenv/bin/python"
        staged.write_text('#!/usr/bin/env bash\necho "python=staged"\n')
        staged.chmod(0o755)
        with tarfile.open(tmp_path / "venv.tar", "w") as archive:
            archive.add(tmp_path / "stagedvenv", arcname=".")
        return {"POLICY_VENV_LOCAL_TAR": str(tmp_path / "venv.tar")}

    def run(body='echo "server=${CARLA_SERVER_ROOT:-none}"; ls ${CARLA_SERVER_ROOT:-}', stage=None):
        fake_python(body)
        return subprocess.run(command, env={**environment, **(stage or {})}, capture_output=True, text=True, timeout=60)

    def stages():
        return list(Path("/tmp").glob(f"route-local-{job}.*"))

    yield SimpleNamespace(run=run, carla_tar=carla_tar, venv_tar=venv_tar, fake_python=fake_python, command=command,
                          environment=environment, stages=stages, output=tmp_path / "results/savio/1/route-7")
    for stage in stages():
        shutil.rmtree(stage, ignore_errors=True)


def test_route_sample_runs_the_stock_server_unless_given_a_tar(route_sample):
    finished = route_sample.run()
    assert finished.returncode == 0, finished.stderr
    assert "server=none" in (route_sample.output / "run.log").read_text()
    assert not route_sample.stages()


def test_route_sample_stages_the_tar_for_the_route_and_removes_it_afterwards(route_sample):
    finished = route_sample.run(stage=route_sample.carla_tar("CarlaUE4.sh", "Engine"))
    assert finished.returncode == 0, finished.stderr
    log = (route_sample.output / "run.log").read_text()
    assert "server=/tmp/route-local-" in log and "CarlaUE4.sh" in log and "Engine" in log
    assert not route_sample.stages()


def test_route_sample_runs_the_route_with_the_staged_python_when_given_its_tar(route_sample):
    finished = route_sample.run(stage=route_sample.venv_tar())
    assert finished.returncode == 0, finished.stderr
    assert "python=staged" in (route_sample.output / "run.log").read_text()
    assert not route_sample.stages()


def test_route_sample_ignores_an_inherited_server_path(route_sample):
    finished = route_sample.run(stage={"CARLA_SERVER_ROOT": "/some/stale/path"})
    assert finished.returncode == 0, finished.stderr
    assert "server=none" in (route_sample.output / "run.log").read_text()


def test_route_sample_removes_a_stage_it_cannot_write_to(route_sample):
    from pathlib import Path
    finished = route_sample.run("chmod -R a-w \"$CARLA_SERVER_ROOT\"", stage=route_sample.carla_tar("CarlaUE4.sh"))
    assert finished.returncode == 0, finished.stderr
    assert not route_sample.stages() and Path("/tmp").is_dir()


def test_route_sample_removes_the_stage_when_a_route_fails(route_sample):
    finished = route_sample.run("exit 1", stage=route_sample.carla_tar("CarlaUE4.sh"))
    assert finished.returncode == 1 and not route_sample.stages()


def test_route_sample_refuses_a_tar_without_the_server_at_its_top_level(route_sample):
    finished = route_sample.run(stage=route_sample.carla_tar("Engine"))
    assert finished.returncode == 2 and "no CarlaUE4.sh" in finished.stderr
    assert not route_sample.output.exists() and not route_sample.stages()


def test_route_sample_removes_the_stage_when_the_job_is_cancelled(route_sample):
    import contextlib
    import os
    import signal
    import time

    route_sample.fake_python("touch results/savio/1/route-7/server-ready; exec sleep 60")
    job = subprocess.Popen(route_sample.command, env={**route_sample.environment, **route_sample.carla_tar("CarlaUE4.sh")},
                           start_new_session=True)
    try:
        deadline = time.monotonic() + 20
        while not (route_sample.output / "server-ready").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert route_sample.stages()
        job.terminate()
        assert job.wait(timeout=20) != 0
        assert not route_sample.stages()
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(job.pid, signal.SIGKILL)
