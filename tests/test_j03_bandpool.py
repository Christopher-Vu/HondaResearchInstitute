"""j03 band pooling on synthetic sets. Does not read or score a real pool."""
from __future__ import annotations

import importlib.util
from itertools import zip_longest
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


j03 = _load("j03_bandpool")
cache_methods = _load("cache_methods")


def test_fractional_layers_follow_depth_not_a_fixed_decoder() -> None:
    fracs = (5 / 23, 8 / 23, 20 / 23)
    assert j03.fractional_layers(24, fracs) == [5, 8, 20]
    assert j03.fractional_layers(6, fracs) == [1, 2, 4]
    assert j03.fractional_layers(3, fracs) == [0, 1, 2]
    assert j03.fractional_layers(6, (1 / 23,)) == [0]
    assert j03.fractional_layers(1, fracs) == [0]


def _naive_round_robin(sources: list[list[set[str]]], limit: int = 10) -> list[set[str]]:
    kept: list[set[str]] = []
    for layer in zip_longest(*sources):
        for item in layer:
            if item is not None and len(kept) < limit:
                kept.append(item)
    return kept


def test_pool_sources_reaches_band_sets_that_late_round_robin_misses() -> None:
    planted = [{f"{letter}{i}" for i in range(20)} for letter in "abcd"]
    sources: list[list[set[str]]] = []
    for source, plant in enumerate(planted):
        big = [{f"b{source}-{k}-{i}" for i in range(40)} for k in range(5)]
        assert plant.isdisjoint(set().union(*big))
        # Size 20 is the only set inside (12, 30). The five big sets come first.
        sources.append(big + [plant])

    naive = _naive_round_robin(sources, limit=10)
    assert len(naive) == 10
    for plant in planted:
        assert max(jaccard(plant, axis) for axis in naive) == 0.0

    reordered = []
    for groups in sources:
        head = [g for g in groups if 12 < len(g) < 30]
        tail = [g for g in groups if not 12 < len(g) < 30]
        assert len(head) == 1 and len(head[0]) == 20
        reordered.append(head + tail)
    pooled = j03.pool_sources(reordered)
    assert len(pooled) == 10
    for plant in planted:
        assert max(jaccard(plant, axis) for axis in pooled) == 1.0


def test_band_axes_keeps_the_tight_cluster_coarse_cuts_split() -> None:
    # 80 diffuse points make 100 failures, and size_band(100) is (5, 12), so the
    # size-20 mode those cuts do find is thrown away. 140 diffuse points make
    # size_band (5, 20), which includes that mode. Same geometry otherwise.
    rng = np.random.default_rng(0)
    n_diffuse, n_tight = 140, 20
    diffuse = np.column_stack([rng.uniform(-20, 20, n_diffuse), rng.normal(0, 0.5, n_diffuse)])
    tight = np.column_stack([rng.normal(0, 0.1, n_tight), np.full(n_tight, 6.0)])
    features = np.vstack([diffuse, tight])
    n = n_diffuse + n_tight
    ids = [f"r{i}" for i in range(n)]
    failing = np.ones(n, dtype=bool)
    planted = {f"r{i}" for i in range(n_diffuse, n)}
    lo, hi = j03.size_band(n)
    assert lo <= n_tight <= hi

    coarse = cache_methods.axes_from(features, failing, ids, "coarse", cuts=(2, 3, 5))
    coarse_best = max(jaccard(set(axis["rollouts"]), planted) for axis in coarse)
    assert coarse_best < 0.7

    ranked = j03.band_axes(features, failing, ids)
    first = jaccard(set(ranked[0]["rollouts"]), planted)
    assert first == 1.0, {
        "coarse_best": coarse_best,
        "first": first,
        "size": ranked[0]["size"],
        "cohesion": ranked[0]["cohesion"],
        "band": j03.size_band(int(failing.sum())),
    }


def test_equal_cohesion_orders_by_size_not_by_route_ids() -> None:
    """Two zero-radius clusters tie on cohesion. The smaller one's ids sort first.

    size_band(48) is (5, 6), so both sizes are kept. Sorting the route-id lists
    would have emitted the size-5 cluster first.
    """
    n_small, n_large, n_noise = 5, 6, 37
    n = n_small + n_large + n_noise
    features = np.zeros((n, 2), dtype=np.float64)
    features[n_small:n_small + n_large, 0] = 200.0
    grid = np.arange(n_noise, dtype=np.float64)
    features[n_small + n_large:, 0] = 1000.0 + (grid % 10) * 5.0
    features[n_small + n_large:, 1] = 1000.0 + (grid // 10) * 5.0
    ids = (
        [f"a{i:02d}" for i in range(n_small)]
        + [f"z{i:02d}" for i in range(n_large)]
        + [f"n{i:02d}" for i in range(n_noise)]
    )
    failing = np.ones(n, dtype=bool)
    small_ids = sorted(ids[:n_small])
    large_ids = sorted(ids[n_small:n_small + n_large])
    assert small_ids < large_ids
    lo, hi = j03.size_band(n)
    assert lo <= n_small < n_large <= hi
    ranked = j03.band_axes(features, failing, ids)
    assert ranked[0]["rollouts"] == large_ids
    assert ranked[0]["size"] == n_large
    small_axes = [axis for axis in ranked if axis["rollouts"] == small_ids]
    assert small_axes
    assert small_axes[0]["cohesion"] == ranked[0]["cohesion"]
    assert ranked.index(small_axes[0]) > 0
