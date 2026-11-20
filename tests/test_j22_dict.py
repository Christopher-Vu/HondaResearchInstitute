"""j22 reads only the frames file, ignores any label field, gives the same axes on a rerun, and its statistic is
late-minus-early per route."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
ALLOWED_KEYS = ("route_id", "meta", "layers", "site", "frames", "n_frames")

spec = importlib.util.spec_from_file_location("j22_dict", SPRINT_DIR / "j22_dict.py")
j22 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j22)


def _save(path: Path, meta_extra: dict | None = None, n: int = 30, t_len: int = 24, width: int = 20) -> None:
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, t_len, width))
    frames[::2, -6:, :3] += 4.0
    failing = np.arange(n) % 3 != 2
    n_frames = np.where(np.arange(n) % 4 == 0, t_len - 6, t_len)
    meta = [json.dumps({"success": not bool(f), **(meta_extra or {})}) for f in failing]
    np.savez(path, route_id=np.array([f"r{i:03d}" for i in range(n)]), meta=np.array(meta),
             layers=np.array([5, 8, 10, 20]), site=np.array("driving_queries"),
             frames=np.repeat(frames.astype(np.float16)[:, None], 4, axis=1), n_frames=n_frames)


def _run(cache: Path, out: Path, monkeypatch, columns: str = "both") -> dict:
    monkeypatch.setattr(sys, "argv", ["j22", str(cache), "--output", str(out), "--dims", "8", "--atoms", "6",
                                      "--alpha", "0.5", "--epochs", "3", "--late", "4", "--columns", columns])
    j22.main()
    return json.loads(out.read_text())


@pytest.mark.parametrize("columns", ["both", "change"])
def test_cli_reads_only_frame_keys_ignores_labels_and_is_deterministic(tmp_path, monkeypatch, columns):
    _save(tmp_path / "plain.npz")
    _save(tmp_path / "labelled.npz", {"scenario": "Wall", "category": "F2D_Wall", "town": "T13"})
    with np.load(tmp_path / "plain.npz") as cache:
        assert set(cache.files) == set(ALLOWED_KEYS)
    first = _run(tmp_path / "plain.npz", tmp_path / "a.json", monkeypatch, columns)
    again = _run(tmp_path / "plain.npz", tmp_path / "b.json", monkeypatch, columns)
    labelled = _run(tmp_path / "labelled.npz", tmp_path / "c.json", monkeypatch, columns)
    assert first["axes"] == again["axes"] == labelled["axes"]
    assert 0 < len(first["axes"]) <= 10


def test_statistic_is_late_minus_early_per_route():
    codes = np.zeros((7, 2))
    codes[1, 0] = 2.0
    codes[2, 0] = -4.0
    codes[6, 1] = 1.0
    stats = j22.late_early_statistics(codes, [3, 4], late=1)
    assert np.allclose(stats[0], [4.0 - 1.0, 0.0, 1.0, 0.0])
    assert np.allclose(stats[1], [0.0, 1.0, 0.0, 1.0])
