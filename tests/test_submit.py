"""submit.sh must hand sbatch options to sbatch, not to the job script."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def submit(tmp_path, *args):
    fake = tmp_path / "sbatch"
    fake.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@"\n')
    fake.chmod(0o755)
    environment = os.environ | {"PATH": f"{tmp_path}:{os.environ['PATH']}"}
    return subprocess.run(["bash", "scripts/submit.sh", *args], cwd=ROOT, env=environment,
                          capture_output=True, text=True, check=True).stdout.splitlines()


def test_dependency_reaches_sbatch_before_the_script(tmp_path):
    argv = submit(tmp_path, "gpu", "--dependency=afterok:123", "scripts/route_sample.sbatch", "extra")[1:]
    assert argv.index("--dependency=afterok:123") < argv.index("scripts/route_sample.sbatch")
    assert argv[-1] == "extra"


def test_plain_submission_is_unchanged(tmp_path):
    argv = submit(tmp_path, "gpu", "scripts/step1.sbatch")[1:]
    assert argv[-1] == "scripts/step1.sbatch"
    assert not any(arg.startswith("--dependency") for arg in argv)


def test_a40_profile_reads_its_own_partition_and_cpus(tmp_path):
    argv = submit(tmp_path, "gpu_a40", "scripts/step1.sbatch")[1:]
    assert "--partition=savio3_gpu" in argv and "--gres=gpu:A40:1" in argv
    assert "--qos=a40_gpu3_ica" in argv and "--cpus-per-task=8" in argv


def test_cpu_profile_requests_no_gpu(tmp_path):
    argv = submit(tmp_path, "cpu", "scripts/step1.sbatch")[1:]
    assert not any(arg.startswith("--gres") for arg in argv)
