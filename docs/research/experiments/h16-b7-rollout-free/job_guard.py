"""H16: what a job checks before it spends. Exits non-zero, with the reason, on the first refusal.

    python docs/research/experiments/h16-b7-rollout-free/job_guard.py {check,capture,score}

Every mode: the job's name and time limit, the SU its job name has committed, and the size of the training output. Score
also refuses a rule that differs from its lock. No Slurm answer is a refusal. The ledger reads this user's jobs only.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent.relative_to(REPO_ROOT)
LOCK_FILE = HERE / "rule-lock.txt"
LOCKED_FILES = (HERE / "protocol.md", HERE / "read_rule.py", HERE / "score.py", Path("src/baselines/b7_variant_a.py"))
TRAINING_OUTPUT = Path("results/savio/h16/training")
MAX_TRAINING_BYTES = 2 * 1024 ** 3
SU_PER_HOUR = 29
FIRST_POSSIBLE_JOB = "2026-11-04"


@dataclass(frozen=True)
class Mode:
    job_name: str
    max_minutes: int
    cap_su: float


MODES = {"check": Mode("h16-check", 30, 15), "capture": Mode("h16-capture", 210, 609), "score": Mode("h16-score", 120, 58)}


def limit_minutes(limit: str) -> int:
    """Minutes from squeue's limit: `D-HH:MM:SS`, `HH:MM:SS` or `MM:SS`. Raises on UNLIMITED."""
    days, _, clock = limit.strip().rpartition("-")
    parts = [int(part) for part in clock.split(":")]
    hours, minutes, seconds = [0] * (3 - len(parts)) + parts
    return int(days or 0) * 1440 + hours * 60 + minutes + (seconds > 0)


def committed_su(sacct_rows: str) -> float:
    """From `State|ElapsedRaw|TimelimitRaw` rows: a running job counts its whole limit, a finished one what it used."""
    seconds = 0
    for row in sacct_rows.splitlines():
        state, elapsed, limit_in_minutes = row.split("|")
        if state.startswith("PENDING"):
            continue
        seconds += int(limit_in_minutes) * 60 if state.startswith("RUNNING") else int(elapsed)
    return seconds / 3600 * SU_PER_HOUR


def refusal(mode: Mode, job_name: str, minutes: int, spent_su: float, training_bytes: int) -> str | None:
    if job_name != mode.job_name:
        return f"job name is {job_name}; this mode runs as {mode.job_name}, or the SU ledger cannot count it"
    if minutes > mode.max_minutes:
        return f"time limit {minutes} min is over this mode's {mode.max_minutes} min"
    if spent_su > mode.cap_su:
        return f"{spent_su:.1f} SU committed under {job_name}, over the cap of {mode.cap_su}: ask Jerry"
    if training_bytes > MAX_TRAINING_BYTES:
        return f"{TRAINING_OUTPUT} holds {training_bytes} bytes, over {MAX_TRAINING_BYTES}"
    return None


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def locked_commit(root: Path) -> str:
    """The lock commit, once each locked file exists in it and the checkout does not differ from it."""
    if not (root / LOCK_FILE).exists():
        raise ValueError(f"{LOCK_FILE} does not exist: the rule is not locked")
    commit = (root / LOCK_FILE).read_text().strip()
    for path in LOCKED_FILES:
        if git(root, "cat-file", "-e", f"{commit}:{path.as_posix()}").returncode != 0:
            raise ValueError(f"{path} is not in lock commit {commit}")
        if git(root, "diff", "--quiet", commit, "--", path.as_posix()).returncode != 0:
            raise ValueError(f"{path} differs from lock commit {commit}")
    return commit


def slurm_output(*command: str) -> str:
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def folder_bytes(folder: Path) -> int:
    return sum(path.stat().st_size for path in folder.iterdir()) if folder.is_dir() else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=sorted(MODES))
    mode_name = parser.parse_args().mode
    mode = MODES[mode_name]
    minutes = limit_minutes(slurm_output("squeue", "-h", "-j", os.environ["SLURM_JOB_ID"], "-o", "%l"))
    rows = slurm_output("sacct", "-X", "-n", "-P", f"--name={mode.job_name}", f"--starttime={FIRST_POSSIBLE_JOB}",
                        "--format=State,ElapsedRaw,TimelimitRaw")
    spent = committed_su(rows)
    reason = refusal(mode, os.environ["SLURM_JOB_NAME"], minutes, spent, folder_bytes(REPO_ROOT / TRAINING_OUTPUT))
    if reason:
        raise SystemExit(f"refused: {reason}")
    if mode_name == "score":
        print(f"rule locked at {locked_commit(REPO_ROOT)}")
    print(f"{mode_name}: limit {minutes} min, {spent:.1f} of {mode.cap_su} SU committed")


if __name__ == "__main__":
    main()
