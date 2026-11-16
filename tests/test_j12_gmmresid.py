"""j12 subtracts a Gaussian mixture of the passing scores from each failure."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j12 = _load("j12_gmmresid")
j05 = _load("j05_knnresid")


def _two_modes(seed: int = 0):
    """Two tight passing modes, far apart, and one failure at the left mean."""
    rng = np.random.default_rng(seed)
    n_each = 40
    left = rng.normal(scale=0.05, size=(n_each, 2)) + np.array([-20.0, 0.0])
    right = rng.normal(scale=0.05, size=(n_each, 2)) + np.array([20.0, 0.0])
    at_left_mean = left.mean(axis=0)
    x = np.vstack([left, right, at_left_mean])
    failing = np.zeros(x.shape[0], dtype=bool)
    failing[-1] = True
    return x, failing


def test_bic_picks_two_on_a_two_mode_passing_set() -> None:
    x, failing = _two_modes()
    _features, info = j12.embed_gmm_residual(x, failing, pre_dims=2, seed=0)
    assert info["K"] == 2
    assert set(info["bic"]) == {1, 2, 3, 4, 5, 6}
    for k, bic in info["bic"].items():
        if k != 2:
            assert info["bic"][2] < bic, (k, bic, info["bic"])
    scores = j05._scores(x, 2, 0)
    expected_reg = float(1e-3 * scores[~failing].var(axis=0).mean())
    assert np.isclose(info["reg_covar"], expected_reg)


def test_residual_at_a_component_mean_is_zero() -> None:
    x, failing = _two_modes()
    features, info = j12.embed_gmm_residual(x, failing, pre_dims=2, seed=0)
    assert info["K"] == 2
    assert features.shape == x.shape
    assert np.linalg.norm(features[failing]) < 1e-6
    assert np.all(features[~failing] == 0.0)


def test_k1_residual_is_score_minus_passing_mean() -> None:
    rng = np.random.default_rng(1)
    passing = rng.normal(scale=0.1, size=(60, 2))
    failed = np.array([[5.0, -1.0], [-4.0, 2.0]])
    x = np.vstack([passing, failed])
    failing = np.array([False] * 60 + [True] * 2)
    features, info = j12.embed_gmm_residual(x, failing, pre_dims=2, seed=0)
    assert info["K"] == 1
    assert set(info["bic"]) == {1, 2, 3, 4, 5, 6}
    for k in range(2, 7):
        assert info["bic"][1] < info["bic"][k]
    scores = j05._scores(x, 2, 0)
    expected = scores[failing] - scores[~failing].mean(axis=0)
    assert np.allclose(features[failing], expected, atol=1e-8)
    assert np.all(features[~failing] == 0.0)


def test_output_shape_and_passing_rows_are_zero() -> None:
    rng = np.random.default_rng(4)
    n_pass, n_fail, width, pre_dims = 12, 6, 10, 8
    x = rng.normal(size=(n_pass + n_fail, width))
    x[n_pass:] += np.array([3.0, -2.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    failing = np.array([False] * n_pass + [True] * n_fail)
    features, _info = j12.embed_gmm_residual(x, failing, pre_dims=pre_dims, seed=0)
    assert features.shape == (n_pass + n_fail, pre_dims)
    assert np.all(features[~failing] == 0.0)
    assert np.count_nonzero(features[failing]) > 0
    assert np.isfinite(features).all()


def test_deterministic_for_a_fixed_seed() -> None:
    x, failing = _two_modes()
    first, info_a = j12.embed_gmm_residual(x, failing, pre_dims=2, seed=7)
    second, info_b = j12.embed_gmm_residual(x, failing, pre_dims=2, seed=7)
    assert np.array_equal(first, second)
    assert info_a["K"] == info_b["K"]
    assert info_a["bic"] == info_b["bic"]
    assert info_a["reg_covar"] == info_b["reg_covar"]


def test_no_passing_routes_fall_back_to_pca_scores() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(12, 5))
    failing = np.ones(12, dtype=bool)
    features, info = j12.embed_gmm_residual(x, failing, pre_dims=4, seed=2)
    assert np.allclose(features, j05._scores(x, 4, 2))
    assert info["K"] is None
    assert info["bic"] == {}
    assert info["reg_covar"] is None


def test_no_failing_routes_are_zero() -> None:
    x, failing = _two_modes()
    passed = x[~failing]
    none_failing = np.zeros(passed.shape[0], dtype=bool)
    features, info = j12.embed_gmm_residual(passed, none_failing, pre_dims=2, seed=0)
    assert features.shape == (passed.shape[0], 2)
    assert np.all(features == 0.0)
    assert info["K"] == 2
    assert set(info["bic"]) == {1, 2, 3, 4, 5, 6}


def test_one_passing_route_is_score_minus_that_score() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(5, 4))
    failing = np.array([False, True, True, True, True])
    features, info = j12.embed_gmm_residual(x, failing, pre_dims=3, seed=1)
    scores = j05._scores(x, 3, 1)
    assert info["K"] == 1
    assert info["bic"] == {}
    assert np.allclose(features[failing], scores[failing] - scores[~failing].mean(axis=0))
    assert np.all(features[~failing] == 0.0)


def test_cli_records_chosen_k_bic_reg_covar_and_seed(tmp_path, monkeypatch) -> None:
    n = 24
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 6, 4))
    meta = np.array([json.dumps({"success": i < 16}) for i in range(n)])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", [
        "j12_gmmresid.py", str(cache), "--pre-dims", "2", "--output", str(out),
    ])
    j12.main()
    payload = json.loads(out.read_text())
    assert payload["method"] == "j12-driving_queries-L1+2+4-window"
    assert payload["settings"]["pre_dims"] == 2
    assert payload["settings"]["seed"] == 0
    assert payload["settings"]["layer"] == [1, 2, 4]
    assert payload["settings"]["K"] in range(1, 7)
    assert set(payload["settings"]["bic"]) == {"1", "2", "3", "4", "5", "6"}
    assert isinstance(payload["settings"]["reg_covar"], float)
    assert len(payload["axes"]) == 10
    failing_ids = {f"r{i}" for i in range(16, n)}
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) <= failing_ids
