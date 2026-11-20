"""Regression tests for preflight checks in the blind UniAD read command."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/research/experiments/f2d-unpooled/uniad_read.sh"


def test_uniad_read_names_missing_job_directories_before_running(tmp_path: Path) -> None:
    """A partial Savio sync must be actionable, rather than failing silently in bash."""
    script = tmp_path / "uniad_read.sh"
    shutil.copy2(SCRIPT, script)
    (tmp_path / "results/savio/present").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "test"],
        cwd=tmp_path,
        check=True,
    )
    env = os.environ | {"JOBS": "present missing"}

    result = subprocess.run(
        ["bash", str(script), "dev"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "missing UniAD job directory or directories: missing" in result.stderr


def test_uniad_read_requests_selection_adjusted_image_query_summary() -> None:
    """The one-command report must resample its numeric-view selection."""
    text = SCRIPT.read_text()
    assert "--select best_img_or_query img-mean query-mean --select-vs B3_behaviour" in text
