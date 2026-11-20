"""j16 reads only the frames file, ignores any label field, and gives the same axes on a rerun."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
ALLOWED_KEYS = ("route_id", "meta", "layers", "site", "frames", "n_frames")

spec = importlib.util.spec_from_file_location("j16_change", SPRINT_DIR / "j16_change.py")
j16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j16)


def _routes(seed: int = 0, n: int = 40, t_len: int = 30, width: int = 24) -> tuple[np.ndarray, np.ndarray]:
    """Half the routes drift smoothly, half jump between two points; both halves share one mean."""
    rng = np.random.default_rng(seed)
    centre = rng.normal(size=width)
    frames = np.empty((n, t_len, width))
    for i in range(n):
        offset = rng.normal(scale=0.05, size=width)
        if i % 2:
            sign = np.where(np.arange(t_len) % 2, 1.0, -1.0)[:, None]
            frames[i] = centre + offset + sign * rng.normal(size=width)
        else:
            frames[i] = centre + offset + np.linspace(-0.2, 0.2, t_len)[:, None] * rng.normal(size=width)
    return frames, np.arange(n) % 4 != 3


def _save(path: Path, frames: np.ndarray, failing: np.ndarray, meta_extra: dict | None = None) -> None:
    n, t_len, _ = frames.shape
    meta = [json.dumps({"success": not bool(f), **(meta_extra or {})}) for f in failing]
    np.savez(path, route_id=np.array([f"r{i:03d}" for i in range(n)]), meta=np.array(meta),
             layers=np.array([5, 8, 10, 20]), site=np.array("driving_queries"),
             frames=np.repeat(frames.astype(np.float16)[:, None], 4, axis=1),
             n_frames=np.full(n, t_len, dtype=np.int64))


def _run(cache: Path, out: Path, monkeypatch) -> dict:
    monkeypatch.setattr(sys, "argv", ["j16", str(cache), "--output", str(out)])
    j16.main()
    return json.loads(out.read_text())


def test_cli_reads_only_frame_keys_and_ignores_labels(tmp_path, monkeypatch):
    frames, failing = _routes()
    _save(tmp_path / "plain.npz", frames, failing)
    _save(tmp_path / "labelled.npz", frames, failing, {"scenario": "Wall", "category": "F2D_Wall", "town": "T13"})
    with np.load(tmp_path / "plain.npz") as cache:
        assert set(cache.files) == set(ALLOWED_KEYS)
    plain = _run(tmp_path / "plain.npz", tmp_path / "a.json", monkeypatch)
    labelled = _run(tmp_path / "labelled.npz", tmp_path / "b.json", monkeypatch)
    assert plain["axes"] == labelled["axes"]
    assert 0 < len(plain["axes"]) <= 10


def test_deterministic_for_fixed_seed(tmp_path, monkeypatch):
    frames, failing = _routes()
    _save(tmp_path / "c.npz", frames, failing)
    first = _run(tmp_path / "c.npz", tmp_path / "1.json", monkeypatch)
    second = _run(tmp_path / "c.npz", tmp_path / "2.json", monkeypatch)
    assert first["axes"] == second["axes"]


def test_first_cut_splits_jumpy_from_smooth_routes():
    frames, failing = _routes()
    ids = [f"r{i:03d}" for i in range(len(frames))]
    axes = j16.j16_axes(frames, np.full(len(frames), frames.shape[1]), failing, ids, "j16")
    jumpy = {ids[i] for i in range(len(ids)) if i % 2 and failing[i]}
    smooth = {ids[i] for i in range(len(ids)) if not i % 2 and failing[i]}
    assert {frozenset(axes[0]["rollouts"]), frozenset(axes[1]["rollouts"])} == {frozenset(jumpy), frozenset(smooth)}


def test_change_features_use_pool_percentile_and_straightness():
    line = np.cumsum(np.ones((11, 2)), axis=0)
    still_then_jump = np.zeros((11, 2))
    still_then_jump[-1] = 5.0
    feats = j16.change_features([line, still_then_jump])
    assert np.isclose(feats[0, 5], 1.0)
    assert np.isclose(feats[1, 3], 0.1)
    assert np.isclose(feats[0, 3], 0.0)


def test_j17_direction_separates_opposite_moves_that_j16_cannot():
    rng = np.random.default_rng(1)
    t_len, width, n = 20, 24, 24
    base = rng.normal(size=width)
    frames = np.empty((n, t_len, width))
    for i in range(n):
        sign = 1.0 if i % 2 else -1.0
        frames[i] = rng.normal(size=width) + sign * np.linspace(0, 3, t_len)[:, None] * base
        frames[i] += rng.normal(scale=0.01, size=(t_len, width))
    failing = np.ones(n, dtype=bool)
    ids = [f"r{i:03d}" for i in range(n)]
    up = frozenset(ids[i] for i in range(n) if i % 2)
    first_cut = lambda axes: {frozenset(axes[0]["rollouts"]), frozenset(axes[1]["rollouts"])}
    assert up in first_cut(j16.j16_axes(frames, np.full(n, t_len), failing, ids, "j17", direction=True))
    assert up not in first_cut(j16.j16_axes(frames, np.full(n, t_len), failing, ids, "j16"))
