"""j24 reads only the frames file, ignores any label field, gives the same axes on a rerun, and groups routes by the
direction the shared dynamics did not predict."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
ALLOWED_KEYS = ("route_id", "meta", "layers", "site", "frames", "n_frames")

spec = importlib.util.spec_from_file_location("j24_ar", SPRINT_DIR / "j24_ar.py")
j24 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j24)


def _routes(seed: int = 0, n: int = 40, t_len: int = 30, width: int = 24) -> tuple[np.ndarray, np.ndarray]:
    """Every route follows one damped rotation; odd routes get a late kick along one fixed direction."""
    rng = np.random.default_rng(seed)
    basis = np.linalg.qr(rng.normal(size=(width, width)))[0]
    kick = basis[:, 0] * 4.0
    rotation = 0.95 * basis @ np.diag(np.where(np.arange(width) % 2, 0.9, 0.8)) @ basis.T
    frames = np.empty((n, t_len, width))
    for i in range(n):
        x = rng.normal(size=width)
        for t in range(t_len):
            x = rotation @ x + rng.normal(scale=0.1, size=width)
            if i % 2 and t >= t_len - 8:
                x = x + kick
            frames[i, t] = x
    return frames, np.arange(n) % 4 != 3


def _save(path: Path, frames: np.ndarray, failing: np.ndarray, meta_extra: dict | None = None) -> None:
    n, t_len, _ = frames.shape
    meta = [json.dumps({"success": not bool(f), **(meta_extra or {})}) for f in failing]
    np.savez(path, route_id=np.array([f"r{i:03d}" for i in range(n)]), meta=np.array(meta),
             layers=np.array([5, 8, 10, 20]), site=np.array("driving_queries"),
             frames=np.repeat(frames.astype(np.float16)[:, None], 4, axis=1),
             n_frames=np.full(n, t_len, dtype=np.int64))


def _run(cache: Path, out: Path, monkeypatch) -> dict:
    monkeypatch.setattr(sys, "argv", ["j24", str(cache), "--output", str(out)])
    j24.main()
    return json.loads(out.read_text())


def test_cli_reads_only_frame_keys_ignores_labels_and_is_deterministic(tmp_path, monkeypatch):
    frames, failing = _routes()
    _save(tmp_path / "plain.npz", frames, failing)
    _save(tmp_path / "labelled.npz", frames, failing, {"scenario": "Wall", "category": "F2D_Wall", "town": "T13"})
    with np.load(tmp_path / "plain.npz") as cache:
        assert set(cache.files) == set(ALLOWED_KEYS)
    plain = _run(tmp_path / "plain.npz", tmp_path / "a.json", monkeypatch)
    again = _run(tmp_path / "plain.npz", tmp_path / "b.json", monkeypatch)
    labelled = _run(tmp_path / "labelled.npz", tmp_path / "c.json", monkeypatch)
    assert plain["axes"] == again["axes"] == labelled["axes"]
    assert 0 < len(plain["axes"]) <= 10


def test_lagged_pairs_each_frame_with_its_two_predecessors():
    seq = np.arange(10, dtype=float).reshape(5, 2)
    inputs, targets = j24.lagged(seq)
    assert np.array_equal(targets, seq[2:])
    assert np.array_equal(inputs[0], np.concatenate([seq[1], seq[0]]))
    assert np.array_equal(inputs[-1], np.concatenate([seq[3], seq[2]]))


def test_first_cut_splits_kicked_from_unkicked_failing_routes():
    frames, failing = _routes()
    ids = [f"r{i:03d}" for i in range(len(frames))]
    axes = j24.j24_axes(frames, np.full(len(frames), frames.shape[1]), failing, ids, "j24")
    kicked = frozenset(ids[i] for i in range(len(ids)) if i % 2 and failing[i])
    calm = frozenset(ids[i] for i in range(len(ids)) if not i % 2 and failing[i])
    assert {frozenset(axes[0]["rollouts"]), frozenset(axes[1]["rollouts"])} == {kicked, calm}
