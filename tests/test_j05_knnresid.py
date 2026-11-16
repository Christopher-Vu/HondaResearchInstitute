"""j05 subtracts a local passing background. On clustered scenes that beats plain PCA."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from harness.scoring import jaccard

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
CUTS = (2, 3, 5)
# Largest shift on the stress2 G1 grid whose j01 score is below 0.3. See the test comment.
SHIFT = 4.0


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j05 = _load("j05_knnresid")
j01 = _load("j01_unwhite")
j04 = _load("j04_bgmoment")
cache_methods = _load("cache_methods")


def _rng(*parts: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(list(parts)))


def _g1(shift: float, seed: int = 0):
    """600 routes, 180 failing, width 256. Eight clusters, three modes of 24, 20 and 17.

    Same construction as stress2's G1: spectrum 1/(1+i), Haar basis, cluster-mean
    lengths uniform on [3, 6], mode directions in population components 0:50.
    """
    n, n_fail, width = 600, 180, 256
    mode_sizes = (24, 20, 17)
    n_clusters, top = 8, 50
    rotation_rng = _rng(seed, 11)
    raw = rotation_rng.standard_normal((width, width))
    q, r = np.linalg.qr(raw)
    signs = np.sign(np.diag(r))
    signs[signs == 0.0] = 1.0
    rotation = q * signs

    rng = _rng(seed, 12)
    assign = rng.integers(0, n_clusters, size=n)
    norms = rng.uniform(3.0, 6.0, size=n_clusters)
    means = rng.standard_normal((width, n_clusters))
    means /= np.linalg.norm(means, axis=0, keepdims=True)
    means *= norms
    spectrum = 1.0 / (1.0 + np.arange(width))
    eigen = rng.standard_normal((n, width)) * np.sqrt(spectrum)
    eigen += means[:, assign].T

    dir_rng = _rng(seed, 13)
    coeff = dir_rng.standard_normal((top, len(mode_sizes)))
    directions, _ = np.linalg.qr(coeff)
    population = np.zeros((width, len(mode_sizes)))
    population[:top, :] = directions[:, : len(mode_sizes)]

    ambient = eigen @ rotation
    ambient_dirs = rotation.T @ population
    x = ambient.copy()
    n_pass = n - n_fail
    failing = np.zeros(n, dtype=bool)
    failing[n_pass:] = True
    groups = []
    offset = n_pass
    for size in mode_sizes:
        groups.append(np.arange(offset, offset + size))
        offset += size
    for mode, index in enumerate(groups):
        x[index] += shift * ambient_dirs[:, mode]
    ids = [f"r{i}" for i in range(n)]
    group_sets = [{ids[i] for i in index} for index in groups]
    return x, failing, ids, group_sets


def _mean_best(features, failing, ids, group_sets) -> float:
    axes = cache_methods.axes_from(features, failing, ids, "j05", "ward", CUTS, 0)[:10]
    axis_sets = [set(axis["rollouts"]) for axis in axes]
    per_mode = [max(jaccard(group, axis) for axis in axis_sets) for group in group_sets]
    return float(np.mean(per_mode))


def _axis_keys(features, failing, ids) -> list[tuple[str, ...]]:
    axes = cache_methods.axes_from(features, failing, ids, "j05", "ward", CUTS, 0)[:10]
    return sorted(tuple(sorted(axis["rollouts"])) for axis in axes)


def test_g1_residual_beats_j01_below_0_3() -> None:
    x, failing, ids, group_sets = _g1(SHIFT)
    j01_score = _mean_best(j01.embed_unwhitened(x, 32, seed=0), failing, ids, group_sets)
    j05_score = _mean_best(j05.embed_knn_residual(x, failing, pre_dims=32, k=10, seed=0), failing, ids, group_sets)
    # Seed 0, shift 4. j01's mean best Jaccard on this draw is 0.11857661378121737.
    # j05's is 1.0. The shift is the largest stress2 G1-grid point with j01 below 0.3:
    # s=1, 1.5, 2, 3 and 4 all scored 0.11857661378121737, and s=6 and s=8 scored 1.0.
    # Those j01 numbers were read before j05 was scored.
    assert j01_score < 0.3, j01_score
    assert j05_score >= 0.9, (j01_score, j05_score)


def test_permuting_route_order_keeps_the_axis_sets() -> None:
    x, failing, ids, group_sets = _g1(SHIFT)
    features = j05.embed_knn_residual(x, failing, pre_dims=32, k=10, seed=0)
    assert _mean_best(features, failing, ids, group_sets) >= 0.9
    perm = np.random.default_rng(123).permutation(x.shape[0])
    assert not np.array_equal(perm, np.arange(x.shape[0]))
    permuted = j05.embed_knn_residual(x[perm], failing[perm], pre_dims=32, k=10, seed=0)
    ids_permuted = [ids[i] for i in perm]
    assert _axis_keys(features, failing, ids) == _axis_keys(permuted, failing[perm], ids_permuted)


def test_k_larger_than_the_passing_count_runs() -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(size=(15, 20))
    failing = np.array([False] * 4 + [True] * 11)
    out = j05.embed_knn_residual(x, failing, pre_dims=8, k=100, seed=0)
    assert out.shape == (15, 8)
    assert np.isfinite(out).all()
    scores = j04._unwhitened(x, 8, seed=0)
    expected = scores[failing] - scores[~failing].mean(axis=0)
    assert np.allclose(out[failing], expected)
    assert np.count_nonzero(out[~failing]) == 0


def test_no_passing_routes_fall_back_to_pca_scores() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(20, 16))
    failing = np.ones(20, dtype=bool)
    out = j05.embed_knn_residual(x, failing, pre_dims=8, k=10, seed=2)
    scores = j04._unwhitened(x, 8, seed=2)
    assert out.shape == (20, 8)
    assert np.allclose(out, scores)


def test_cli_records_k_pre_dims_and_default_layers(tmp_path, monkeypatch) -> None:
    n = 24
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 6, 8))
    meta = np.array([json.dumps({"success": i < 16}) for i in range(n)])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", ["j05_knnresid.py", str(cache), "--output", str(out)])
    j05.main()
    payload = json.loads(out.read_text())
    assert payload["method"] == "j05-driving_queries-L1+2+4-window"
    assert payload["settings"]["k"] == 10
    assert payload["settings"]["pre_dims"] == 32
    assert payload["settings"]["layer"] == [1, 2, 4]
    assert len(payload["axes"]) == 10
    failing_ids = {f"r{i}" for i in range(16, n)}
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) <= failing_ids
