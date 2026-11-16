"""j13 removes the tangent of the k nearest passing routes from j05's residual."""
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


j13 = _load("j13_knntangent")
j05 = _load("j05_knnresid")


def _both(x, failing, tangent_dims, k=10, pre_dims=6, seed=0):
    got = j13.embed_knn_tangent(
        x, failing, pre_dims=pre_dims, k=k, tangent_dims=tangent_dims, seed=seed)
    base = j05.embed_knn_residual(x, failing, pre_dims=pre_dims, k=k, seed=seed)
    return got, base


def _far_background() -> np.ndarray:
    """Passing routes far from the origin, so a local patch stays the k nearest."""
    return np.column_stack([
        np.full(12, 100.0),
        np.linspace(-1.0, 1.0, 12),
        np.linspace(-0.5, 0.5, 12),
    ])


def _dominant_patch() -> np.ndarray:
    """Ten points. The long axis is x; a real but smaller axis is y."""
    xs = np.linspace(-5.0, 5.0, 5)
    ys = np.array([-0.25, 0.25])
    return np.array([[x, y, 0.0] for x in xs for y in ys], dtype=np.float64)


def _plane_patch() -> np.ndarray:
    """Ten points in the xy plane, rank 2, both axes well above the cutoff."""
    xs = np.linspace(-1.0, 1.0, 5)
    ys = np.array([-1.0, 1.0])
    return np.array([[x, y, 0.0] for x in xs for y in ys], dtype=np.float64)


def _with_failure(passing: np.ndarray, failed: np.ndarray, background: np.ndarray | None):
    parts = [passing] if background is None else [background, passing]
    x = np.vstack(parts + [failed])
    failing = np.zeros(x.shape[0], dtype=bool)
    failing[-failed.shape[0]:] = True
    return x, failing


def test_tangent_dims_zero_equals_j05() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(36, 5))
    failing = np.array([False] * 20 + [True] * 16)
    got, base = _both(x, failing, tangent_dims=0, k=6, pre_dims=8, seed=3)
    assert np.array_equal(got, base)

    # k larger than the passing count: j05 averages every passing route.
    few = rng.normal(size=(15, 20))
    failing_few = np.array([False] * 4 + [True] * 11)
    got, base = _both(few, failing_few, tangent_dims=0, k=100, pre_dims=8, seed=0)
    assert np.array_equal(got, base)

    cloud = rng.normal(size=(12, 5))
    all_fail = np.ones(12, dtype=bool)
    assert np.array_equal(
        j13.embed_knn_tangent(cloud, all_fail, pre_dims=4, k=10, tangent_dims=0, seed=2),
        j05.embed_knn_residual(cloud, all_fail, pre_dims=4, k=10, seed=2),
    )
    block = rng.normal(size=(10, 6))
    none_failing = np.zeros(10, dtype=bool)
    assert np.array_equal(
        j13.embed_knn_tangent(block, none_failing, pre_dims=3, k=10, tangent_dims=0, seed=1),
        j05.embed_knn_residual(block, none_failing, pre_dims=3, k=10, seed=1),
    )


def test_one_neighbour_matches_j05_because_there_is_no_tangent() -> None:
    rng = np.random.default_rng(2)
    x = rng.normal(size=(18, 7))
    failing = np.array([False] * 9 + [True] * 9)
    got = j13.embed_knn_tangent(x, failing, pre_dims=5, k=1, tangent_dims=2, seed=0)
    base = j05.embed_knn_residual(x, failing, pre_dims=5, k=1, seed=0)
    assert np.array_equal(got, base)


def test_tangent_dims_clamp_to_k_minus_one() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(22, 8))
    failing = np.array([False] * 14 + [True] * 8)
    capped = j13.embed_knn_tangent(x, failing, pre_dims=6, k=4, tangent_dims=9, seed=1)
    exact = j13.embed_knn_tangent(x, failing, pre_dims=6, k=4, tangent_dims=3, seed=1)
    narrow = j13.embed_knn_tangent(x, failing, pre_dims=6, k=4, tangent_dims=1, seed=1)
    assert np.array_equal(capped, exact)
    assert not np.allclose(capped, narrow)


def test_displacement_along_the_dominant_direction_is_removed() -> None:
    failed = np.array([[1.0, 0.0, 0.0]])
    patch = _dominant_patch()
    cases = (
        _with_failure(patch, failed, background=None),
        _with_failure(patch, failed, background=_far_background()),
    )
    for x, failing in cases:
        for tangent_dims in (1, 2):
            got, base = _both(x, failing, tangent_dims=tangent_dims)
            base_norm = float(np.linalg.norm(base[failing]))
            ratio = float(np.linalg.norm(got[failing]) / base_norm)
            assert base_norm > 1e-2, base_norm
            assert ratio < 1e-6, (tangent_dims, ratio, x.shape)
            assert np.all(got[~failing] == 0.0)


def test_orthogonal_displacement_keeps_the_full_residual() -> None:
    failed = np.array([[0.0, 0.0, 1.3]])
    patch = _plane_patch()
    cases = (
        _with_failure(patch, failed, background=None),
        _with_failure(patch, failed, background=_far_background()),
    )
    for x, failing in cases:
        got, base = _both(x, failing, tangent_dims=2)
        assert float(np.linalg.norm(base[failing])) > 0.1
        assert np.allclose(got[failing], base[failing], atol=1e-8)
        assert np.all(got[~failing] == 0.0)


def test_residual_is_orthogonal_to_the_removed_directions() -> None:
    mixed = np.array([[0.3, -0.2, 0.9]])
    patch = _plane_patch()
    for background in (None, _far_background()):
        x, failing = _with_failure(patch, mixed, background)
        got, base = _both(x, failing, tangent_dims=2)
        removed = base[failing] - got[failing]
        assert float(np.linalg.norm(removed)) > 1e-3
        assert float(np.linalg.norm(got[failing])) > 1e-3
        dots = np.sum(got[failing] * removed, axis=1)
        assert np.allclose(dots, 0.0, atol=1e-8), dots

    rng = np.random.default_rng(0)
    x = rng.normal(size=(48, 16))
    failing = np.array([False] * 30 + [True] * 18)
    got, base = _both(x, failing, tangent_dims=2, k=10, pre_dims=8, seed=1)
    removed = base[failing] - got[failing]
    assert float(np.linalg.norm(removed)) > 1e-3
    dots = np.sum(got[failing] * removed, axis=1)
    assert np.allclose(dots, 0.0, atol=1e-8), float(np.max(np.abs(dots)))
    energy = np.sum(got[failing] ** 2, axis=1) + np.sum(removed ** 2, axis=1)
    assert np.allclose(energy, np.sum(base[failing] ** 2, axis=1), atol=1e-8)


def _rectangle(scale: float) -> np.ndarray:
    """Four centred corners. x and y are uncorrelated, so the singular-value ratio is scale."""
    xs = np.array([-1.0, -1.0, 1.0, 1.0])
    ys = np.array([-1.0, 1.0, -1.0, 1.0])
    return np.column_stack([xs, scale * ys, np.zeros(4)])


def test_singular_value_cutoff_drops_a_tiny_direction_and_keeps_a_larger_one() -> None:
    # Strictly above 1e-12 times the largest singular value. 1e-12 itself is not used.
    dropped = j13._tangent_basis(_rectangle(1e-13), t=2)
    border = j13._tangent_basis(_rectangle(1e-12), t=2)
    kept = j13._tangent_basis(_rectangle(1e-11), t=2)
    assert dropped.shape == (1, 3)
    assert border.shape == (1, 3)
    assert kept.shape == (2, 3)
    along_weak = np.array([0.0, 4.0, 0.0])
    leftover = along_weak - dropped.T @ (dropped @ along_weak)
    assert np.linalg.norm(leftover - along_weak) < 1e-8


def test_output_shape_and_passing_rows_are_zero() -> None:
    rng = np.random.default_rng(4)
    n_pass, n_fail, width, pre_dims = 12, 6, 10, 8
    x = rng.normal(size=(n_pass + n_fail, width))
    x[n_pass:] += np.array([3.0, -2.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    failing = np.array([False] * n_pass + [True] * n_fail)
    features = j13.embed_knn_tangent(x, failing, pre_dims=pre_dims, k=100, tangent_dims=2, seed=0)
    assert features.shape == (n_pass + n_fail, pre_dims)
    assert np.all(features[~failing] == 0.0)
    assert np.count_nonzero(features[failing]) > 0
    assert np.isfinite(features).all()


def test_deterministic_for_a_fixed_seed() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(30, 9))
    failing = np.array([False] * 18 + [True] * 12)
    first = j13.embed_knn_tangent(x, failing, pre_dims=6, k=7, tangent_dims=2, seed=5)
    second = j13.embed_knn_tangent(x, failing, pre_dims=6, k=7, tangent_dims=2, seed=5)
    assert np.array_equal(first, second)


def test_no_passing_routes_fall_back_to_pca_scores() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(12, 5))
    failing = np.ones(12, dtype=bool)
    features = j13.embed_knn_tangent(x, failing, pre_dims=4, k=10, tangent_dims=2, seed=2)
    assert np.array_equal(features, j05._scores(x, 4, 2))
    assert np.array_equal(features, j05.embed_knn_residual(x, failing, pre_dims=4, k=10, seed=2))


def test_no_failing_routes_are_zero() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(10, 6))
    failing = np.zeros(10, dtype=bool)
    features = j13.embed_knn_tangent(x, failing, pre_dims=4, k=10, tangent_dims=2, seed=0)
    assert features.shape == (10, 4)
    assert np.all(features == 0.0)
    assert np.array_equal(features, j05.embed_knn_residual(x, failing, pre_dims=4, k=10, seed=0))


def test_cli_records_k_tangent_dims_pre_dims_seed_and_layers(tmp_path, monkeypatch) -> None:
    n = 24
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 6, 4))
    meta = np.array([json.dumps({"success": i < 16}) for i in range(n)])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", ["j13_knntangent.py", str(cache), "--output", str(out)])
    j13.main()
    payload = json.loads(out.read_text())
    assert payload["method"] == "j13-driving_queries-L1+2+4-window"
    assert payload["settings"]["k"] == 10
    assert payload["settings"]["tangent_dims"] == 2
    assert payload["settings"]["pre_dims"] == 32
    assert payload["settings"]["seed"] == 0
    assert payload["settings"]["layer"] == [1, 2, 4]
    assert payload["settings"]["summary"] == "window"
    assert payload["settings"]["site"] == "driving_queries"
    assert len(payload["axes"]) == 10
    failing_ids = {f"r{i}" for i in range(16, n)}
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) <= failing_ids
