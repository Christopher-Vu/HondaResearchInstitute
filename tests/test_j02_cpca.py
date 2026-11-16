"""Spectral-gap contrastive PCA recovers two buried failure groups; unwhitened PCA does not."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j02 = _load("j02_cpca")
cache_methods = _load("cache_methods")


def _best_jaccard(axes: list[dict], group: set[str]) -> float:
    def jaccard(left: set[str], right: set[str]) -> float:
        union = left | right
        return len(left & right) / len(union) if union else 0.0

    return max(jaccard(set(axis["rollouts"]), group) for axis in axes)


def test_spectral_gap_cpca_recovers_both_buried_groups() -> None:
    rng = np.random.default_rng(0)
    n_pass, n_a, n_b = 180, 20, 20
    d = 96
    n_shared, shared, sep, signal_dim = 40, 4, 6, 90
    x = rng.normal(0, 1, (n_pass + n_a + n_b, d))
    x[:, :n_shared] *= shared
    x[:n_pass, signal_dim] *= 0.3
    x[n_pass:n_pass + n_a, signal_dim] += sep
    x[n_pass + n_a:, signal_dim] -= sep
    failing = np.array([False] * n_pass + [True] * (n_a + n_b))
    ids = [f"r{i}" for i in range(n_pass + n_a + n_b)]
    group_a = {f"r{i}" for i in range(180, 200)}
    group_b = {f"r{i}" for i in range(200, 220)}

    scores, info = j02.embed_cpca(x, failing, dims=4, seed=0)
    assert "fallback" not in info
    assert info["alpha"] in (10, 30, 100)
    assert all(not isinstance(value, str) for value in info.values())
    axes = cache_methods.axes_from(scores, failing, ids, "j02", "ward", (2, 3, 5), 0)[:10]
    jaccard_a = _best_jaccard(axes, group_a)
    jaccard_b = _best_jaccard(axes, group_b)
    assert jaccard_a >= 0.95
    assert jaccard_b >= 0.95

    pca_scores = PCA(n_components=32, random_state=0).fit_transform(x)
    pca_axes = cache_methods.axes_from(pca_scores, failing, ids, "pca", "ward", (2, 3, 5), 0)[:10]
    pca_a = _best_jaccard(pca_axes, group_a)
    pca_b = _best_jaccard(pca_axes, group_b)
    assert pca_a <= 0.75
    assert pca_b <= 0.75
