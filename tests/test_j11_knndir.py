"""j11 clusters the direction of a kNN residual, not its length."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from harness.scoring import jaccard


SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j11 = _load("j11_knndir")
j05 = _load("j05_knnresid")
cache_methods = _load("cache_methods")


def test_failing_rows_are_unit_and_passing_rows_are_zero() -> None:
    rng = np.random.default_rng(0)
    n_pass, n_fail, width = 25, 12, 10
    passing = rng.normal(scale=0.1, size=(n_pass, width))
    shift = np.linspace(2.0, 8.0, n_fail)[:, None]
    failing_rows = rng.normal(size=(n_fail, width)) + shift
    x = np.vstack([passing, failing_rows])
    failing = np.zeros(n_pass + n_fail, dtype=bool)
    failing[n_pass:] = True
    residual = j05.embed_knn_residual(x, failing, pre_dims=32, k=10, seed=0)
    assert np.all(np.linalg.norm(residual[failing], axis=1) > 1e-6)
    out = j11.embed_knn_direction(x, failing, pre_dims=32, k=10, seed=0)
    assert out.shape == (n_pass + n_fail, 32)
    assert np.all(out[~failing] == 0.0)
    norms = np.linalg.norm(out[failing], axis=1)
    assert np.allclose(norms, 1.0)
    # Dividing by the norm keeps the residual's direction: the dot product
    # equals the residual length.
    dots = np.sum(out[failing] * residual[failing], axis=1)
    assert np.allclose(dots, np.linalg.norm(residual[failing], axis=1))


def test_zero_residual_row_stays_zero() -> None:
    rng = np.random.default_rng(2)
    passing = rng.normal(size=(9, 6))
    copied = passing[0].copy()
    others = rng.normal(size=(4, 6)) + 3.0
    x = np.vstack([passing, copied[None, :], others])
    failing = np.array([False] * 9 + [True] * 5)
    residual = j05.embed_knn_residual(x, failing, pre_dims=8, k=1, seed=0)
    assert np.linalg.norm(residual[9]) < 1e-12
    out = j11.embed_knn_direction(x, failing, pre_dims=8, k=1, seed=0)
    assert np.all(out[9] == 0.0)
    assert np.all(out[~failing] == 0.0)
    assert np.allclose(np.linalg.norm(out[10:], axis=1), 1.0)


def test_ward_cut_2_separates_directions_when_lengths_vary() -> None:
    """Two directions off local passing neighbours. Lengths differ by scene.

    Scene centers are far apart, so each failure's k nearest passing routes
    stay in its own scene. Kind A steps along one axis and kind B along
    another. The step length is 0.5, 20 or 400 depending on the scene, with
    a little jitter, so the same kind is short in one scene and long in
    another. Ward cut 2 should follow the direction.
    """
    rng = np.random.default_rng(0)
    n_scenes, n_pass, n_each, width = 3, 12, 8, 6
    scene_gap = 20_000.0
    scene_lengths = np.array([0.5, 20.0, 400.0])
    dir_a = np.zeros(width)
    dir_b = np.zeros(width)
    dir_a[2] = 1.0
    dir_b[3] = 1.0
    rows = []
    failing_flags = []
    ids: list[str] = []
    groups = {"a": set(), "b": set()}
    for scene in range(n_scenes):
        center = np.zeros(width)
        center[0] = scene * scene_gap
        for index in range(n_pass):
            rows.append(center + rng.normal(scale=0.02, size=width))
            failing_flags.append(False)
            ids.append(f"p{scene}_{index}")
        for kind, direction in (("a", dir_a), ("b", dir_b)):
            for index in range(n_each):
                length = float(scene_lengths[scene] * rng.uniform(0.7, 1.3))
                rows.append(center + length * direction + rng.normal(scale=0.01, size=width))
                failing_flags.append(True)
                ident = f"{kind}{scene}_{index}"
                ids.append(ident)
                groups[kind].add(ident)
    x = np.vstack(rows)
    failing = np.array(failing_flags, dtype=bool)
    features = j11.embed_knn_direction(x, failing, pre_dims=32, k=10, seed=0)
    axes = cache_methods.axes_from(features, failing, ids, "j11", "ward", cache_methods.CUTS, 0)[:10]
    cut2 = [set(axis["rollouts"]) for axis in axes if " cut 2 group " in axis["name"]]
    assert len(cut2) == 2
    scores = {kind: max(jaccard(group, axis) for axis in cut2) for kind, group in groups.items()}
    assert scores["a"] >= 0.9, scores
    assert scores["b"] >= 0.9, scores
