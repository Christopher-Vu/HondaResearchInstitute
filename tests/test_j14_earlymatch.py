"""j14 matches passing controls in the early summary and scores them on the window."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j14 = _load("j14_earlymatch")
j05 = _load("j05_knnresid")


def test_shape_pads_to_pre_dims_and_passing_rows_are_zero() -> None:
    rng = np.random.default_rng(0)
    n = 30
    window = rng.normal(size=(n, 12))
    early = rng.normal(size=(n, 15))
    failing = np.zeros(n, dtype=bool)
    failing[18:] = True
    out = j14.embed_early_match(window, early, failing, pre_dims=32, k=10, seed=0)
    assert out.shape == (n, 32)
    assert np.isfinite(out).all()
    assert np.all(out[~failing] == 0.0)
    assert np.any(out[failing] != 0.0)

    narrow = j14.embed_early_match(window, early, failing, pre_dims=8, k=10, seed=0)
    assert narrow.shape == (n, 8)
    assert np.all(narrow[~failing] == 0.0)


def test_window_equal_to_early_matches_j05_exactly() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(40, 16))
    failing = np.array([False] * 25 + [True] * 15)
    for k, pre_dims, seed in ((10, 32, 0), (3, 8, 1), (100, 8, 2), (1, 4, 7), (0, 8, 4)):
        got = j14.embed_early_match(x, np.array(x, copy=True), failing, pre_dims=pre_dims, k=k, seed=seed)
        expected = j05.embed_knn_residual(x, failing, pre_dims=pre_dims, k=k, seed=seed)
        assert np.array_equal(got, expected)

    all_fail = np.ones(x.shape[0], dtype=bool)
    assert np.array_equal(
        j14.embed_early_match(x, x, all_fail, pre_dims=8, k=10, seed=2),
        j05.embed_knn_residual(x, all_fail, pre_dims=8, k=10, seed=2),
    )
    none_failing = np.zeros(x.shape[0], dtype=bool)
    zeros = j14.embed_early_match(x, x, none_failing, pre_dims=8, k=10, seed=0)
    assert np.array_equal(zeros, j05.embed_knn_residual(x, none_failing, pre_dims=8, k=10, seed=0))
    assert np.all(zeros == 0.0)


def test_k_larger_than_the_passing_count_uses_every_passing_window() -> None:
    rng = np.random.default_rng(1)
    window = rng.normal(size=(15, 20))
    early = rng.normal(size=(15, 20))
    failing = np.array([False] * 4 + [True] * 11)
    out = j14.embed_early_match(window, early, failing, pre_dims=8, k=100, seed=0)
    assert out.shape == (15, 8)
    assert np.isfinite(out).all()
    scores = j14._scores(window, 8, 0)
    expected = scores[failing] - scores[~failing].mean(axis=0)
    assert np.allclose(out[failing], expected)
    assert np.count_nonzero(out[~failing]) == 0
    assert np.array_equal(out, j05.embed_knn_residual(window, failing, pre_dims=8, k=100, seed=0))


def test_no_passing_routes_return_window_scores() -> None:
    rng = np.random.default_rng(0)
    window = rng.normal(size=(18, 10))
    early = rng.normal(size=(18, 10))
    failing = np.ones(18, dtype=bool)
    out = j14.embed_early_match(window, early, failing, pre_dims=6, k=10, seed=3)
    assert not np.array_equal(window, early)
    assert np.array_equal(out, j14._scores(window, 6, 3))
    assert out.shape == (18, 6)


def test_no_failing_routes_are_zeros() -> None:
    rng = np.random.default_rng(1)
    window = rng.normal(size=(14, 9))
    early = rng.normal(size=(14, 7))
    failing = np.zeros(14, dtype=bool)
    out = j14.embed_early_match(window, early, failing, pre_dims=32, k=10, seed=0)
    assert out.shape == (14, 32)
    assert np.all(out == 0.0)


def test_nonfinite_early_raises() -> None:
    rng = np.random.default_rng(0)
    window = rng.normal(size=(12, 5))
    failing = np.array([False] * 8 + [True] * 4)
    early = window.copy()
    early[1, 2] = np.nan
    with pytest.raises(SystemExit, match="non-finite"):
        j14.embed_early_match(window, early, failing, pre_dims=4, k=3, seed=0)
    early[1, 2] = np.inf
    with pytest.raises(SystemExit, match="NaN early"):
        j14.embed_early_match(window, early, failing, pre_dims=4, k=3, seed=0)


def test_neighbours_are_picked_in_early_space_not_window() -> None:
    """Two failures sit on passing group A in the window and on group B early.

    k is 2. Group A is the window neighbourhood, so j05's residual is the
    small step off A. Group B is the early neighbourhood, and B's window
    scores lie far from A, so j14's residual has about that separation.
    """
    window = np.array([
        [0.0, 0.0],
        [0.2, 0.0],
        [80.0, 0.0],
        [80.2, 0.0],
        [0.0, 80.0],
        [0.1, 0.0],
        [0.05, 0.1],
    ])
    early = np.array([
        [80.0, 0.0],
        [80.2, 0.0],
        [0.0, 0.0],
        [0.2, 0.0],
        [0.0, 80.0],
        [0.1, 0.0],
        [0.05, 0.1],
    ])
    failing = np.array([False, False, False, False, False, True, True])
    out = j14.embed_early_match(window, early, failing, pre_dims=4, k=2, seed=0)
    base = j05.embed_knn_residual(window, failing, pre_dims=4, k=2, seed=0)
    assert out.shape == (7, 4)
    assert np.all(out[~failing] == 0.0)
    assert np.all(np.linalg.norm(base[failing], axis=1) < 0.2)
    assert np.all(np.linalg.norm(out[failing], axis=1) > 70.0)
    assert not np.allclose(out[failing], base[failing])

    sw = j14._scores(window, 4, 0)
    se = j14._scores(early, 4, 0)
    early_nn = _nearest(se, failing, 2)
    window_nn = _nearest(sw, failing, 2)
    assert np.array_equal(np.sort(early_nn, axis=1), np.array([[2, 3], [2, 3]]))
    assert np.array_equal(np.sort(window_nn, axis=1), np.array([[0, 1], [0, 1]]))
    expected = sw[failing] - sw[~failing][early_nn].mean(axis=1)
    assert np.allclose(out[failing], expected)


def _nearest(scores: np.ndarray, failing: np.ndarray, k: int) -> np.ndarray:
    passed = scores[~failing]
    failed = scores[failing]
    pass_norm = np.einsum("ij,ij->i", passed, passed)
    fail_norm = np.einsum("ij,ij->i", failed, failed)
    distances = np.maximum(fail_norm[:, None] + pass_norm[None, :] - 2.0 * failed @ passed.T, 0.0)
    return np.argpartition(distances, k - 1, axis=1)[:, :k]


def test_cli_records_early_match_and_window_score(tmp_path, monkeypatch) -> None:
    n = 24
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 6, 8))
    meta = np.array([json.dumps({"success": i < 16}) for i in range(n)])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", ["j14_earlymatch.py", str(cache), "--output", str(out)])
    j14.main()
    payload = json.loads(out.read_text())
    assert payload["method"] == "j14-driving_queries-L1+2+4-earlymatch"
    assert set(payload["settings"]) == {
        "cache", "site", "layer", "summary_match", "summary_score", "pre_dims", "k", "seed"}
    assert payload["settings"]["cache"] == str(cache)
    assert payload["settings"]["site"] == "driving_queries"
    assert payload["settings"]["layer"] == [1, 2, 4]
    assert payload["settings"]["summary_match"] == "early"
    assert payload["settings"]["summary_score"] == "window"
    assert payload["settings"]["k"] == 10
    assert payload["settings"]["pre_dims"] == 32
    assert payload["settings"]["seed"] == 0
    assert len(payload["axes"]) == 10
    failing_ids = {f"r{i}" for i in range(16, n)}
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) <= failing_ids
        assert axis["rollouts"] == sorted(axis["rollouts"])


def test_cli_nan_early_slot_raises(tmp_path, monkeypatch) -> None:
    n = 10
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 4, 6))
    frames[:, 2, 0, 0] = np.nan
    meta = np.array([json.dumps({"success": i < 6}) for i in range(n)])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", [
        "j14_earlymatch.py", str(cache), "--output", str(out), "--layer", "0", "--k", "4", "--pre-dims", "8",
    ])
    with pytest.raises(SystemExit, match="non-finite"):
        j14.main()
    assert not out.exists()
