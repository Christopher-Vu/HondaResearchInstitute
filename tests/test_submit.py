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


def test_a40_profile_excludes_its_bad_nodes_and_merges_a_passed_exclude(tmp_path):
    argv = submit(tmp_path, "gpu_a40", "--exclude=n9999.savio3", "--time=0-01:00:00", "scripts/step1.sbatch")[1:]
    excludes = [arg for arg in argv if arg.startswith("--exclude=")]
    assert excludes == ["--exclude=n0214.savio3,n0215.savio3,n0262.savio3,n9999.savio3"]
    assert "--time=0-01:00:00" in argv


def test_a5000_profile_excludes_nothing_unless_asked(tmp_path):
    argv = submit(tmp_path, "gpu", "scripts/step1.sbatch")[1:]
    assert not any(arg.startswith("--exclude") for arg in argv)
