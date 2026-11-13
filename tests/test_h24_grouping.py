"""H24's error-aware mixture and the shared set scorer on synthetic pools."""
import importlib.util
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.scoring import jaccard  # noqa: E402

EXPERIMENT = Path(__file__).resolve().parents[1] / "docs/research/experiments/h24-error-aware-grouping"


def load(name):
    spec = importlib.util.spec_from_file_location(f"h24_{name}", EXPERIMENT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"h24_{name}"] = module
    spec.loader.exec_module(module)
    return module


mixture = load("mixture")
score_sets = load("score_sets")


def planted_pool(seed=0):
    """200 routes; 8 failures sit in their own region of feature space, 40 more failures are scattered."""
    rng = np.random.default_rng(seed)
    act = rng.normal(size=(200, 64))
    act[:8] += 6.0
    failed = np.zeros(200, bool)
    failed[:8] = True
    failed[rng.choice(np.arange(8, 200), 40, replace=False)] = True
    return np.array([f"r{i}" for i in range(200)]), failed, act


def test_mixture_recovers_a_planted_group_of_failures():
    ids, failed, act = planted_pool()
    z = mixture.embed({"act": act}, ("act",))
    groups = mixture.axes(ids, failed, mixture.fit(z, failed, 0))
    target = {f"r{i}" for i in range(8)}
    assert max(jaccard(set(g), target) for g in groups) >= 0.8
    assert len(groups) <= mixture.BUDGET
    assert all(set(g) <= set(ids[failed]) for g in groups)


def test_mixture_is_deterministic_per_seed():
    ids, failed, act = planted_pool()
    z = mixture.embed({"act": act}, ("act",))
    assert mixture.axes(ids, failed, mixture.fit(z, failed, 3)) == mixture.axes(ids, failed, mixture.fit(z, failed, 3))


def test_blocks_weigh_equally_after_scaling():
    rng = np.random.default_rng(1)
    z = mixture.embed({"a": rng.normal(size=(50, 40)), "b": rng.normal(size=(50, 4))}, ("a", "b"))
    assert abs(z[:, :32].var(axis=0).sum() - 1) < 1e-9 and abs(z[:, 32:].var(axis=0).sum() - 1) < 1e-9


def test_random_control_is_a_seeded_partition_of_matched_sizes():
    draws = score_sets.random_draws([5, 10], 50, 7)
    assert len(draws) == score_sets.RANDOM_DRAWS
    assert all(list(d.sum(axis=1)) == [5, 10] and not (d[0] & d[1]).any() for d in draws)
    again = score_sets.random_draws([5, 10], 50, 7)
    assert all(np.array_equal(a, b) for a, b in zip(draws, again))


def test_weighted_best_scores_match_plain_jaccard_at_unit_weight():
    index = {f"f{i}": i for i in range(6)}
    axes = score_sets.matrix([["f0", "f1"], ["f2", "f3", "f4"]], index)
    targets = score_sets.matrix([["f0", "f1", "f2"]], index)
    assert np.allclose(score_sets.best_scores(axes, targets, np.ones(6)), [2 / 3])
    weight = np.array([2.0, 0, 1, 1, 1, 1])
    assert np.allclose(score_sets.best_scores(axes, targets, weight), [2 / 3])
    assert np.allclose(score_sets.best_scores(np.zeros((0, 6), bool), targets, np.ones(6)), [0])


def test_rule_needs_margin_every_category_and_the_route_bootstrap():
    assert score_sets.outcome(0.2, [0.1, 0.3, 0.2], 0.01, 18, 12) == "ahead"
    assert score_sets.outcome(0.2, [0.1, 0.3, -0.01], 0.01, 18, 12) == "not_ahead"
    assert score_sets.outcome(0.2, [0.1, 0.3, 0.2], -0.01, 18, 12) == "not_ahead"
    assert score_sets.outcome(0.1, [0.1, 0.3, 0.2], 0.05, 18, 12) == "not_ahead"
    assert score_sets.outcome(0.5, [0.5, 0.5, 0.5], 0.3, 11, 12) == "untested"


def test_a_misspelt_category_stops_the_run():
    manifest = [{"id": "s1", "base_id": "b1", "role": "pilot_slice", "practice_gaps": ["F2D_Wall"]}]
    try:
        score_sets.category_sets(manifest, {"s1": True}, ["Wall"])
    except ValueError:
        return
    raise AssertionError("an empty category must raise")


def test_a_perfect_method_is_ahead_and_a_random_one_is_not():
    index = {f"f{i}": i for i in range(60)}
    target_sets = [[f"f{i}" for i in range(0, 8)], [f"f{i}" for i in range(8, 13)], [f"f{i}" for i in range(13, 16)]]
    targets = score_sets.matrix(target_sets, index)
    b3 = score_sets.matrix([[f"f{i}" for i in range(0, 30)]], index)
    perfect = [{"run": r, "axes": target_sets} for r in range(12)]
    report = score_sets.method_report(perfect, index, targets, ["a", "b", "c"], b3, None, 12, 1)
    assert report["outcome"] == "ahead"
    rng = np.random.default_rng(0)
    noise = [{"run": r, "axes": [list(rng.choice(list(index), 8, replace=False))]} for r in range(12)]
    assert score_sets.method_report(noise, index, targets, ["a", "b", "c"], b3, None, 12, 1)["outcome"] == "not_ahead"


def test_pairs_need_a_failed_slice_and_a_clean_twin():
    manifest = [{"id": "s1", "base_id": "b1", "role": "pilot_slice", "practice_gaps": ["C"]},
                {"id": "t1", "base_id": "b1", "role": "pilot_neighbourhood", "practice_gaps": []},
                {"id": "s2", "base_id": "b2", "role": "pilot_slice", "practice_gaps": ["C"]},
                {"id": "t2", "base_id": "b2", "role": "pilot_neighbourhood", "practice_gaps": []}]
    failed = {"s1": True, "t1": False, "s2": True, "t2": True}
    assert score_sets.slice_only_pairs(manifest, failed, "C") == [("s1", "t1")]


def small_groups_pool(seed, shift=3.0):
    """200 routes; groups of 8, 5 and 3 failures each shifted on their own 8 dimensions, plus 36 scattered failures."""
    rng = np.random.default_rng(seed)
    act = rng.normal(size=(200, 64))
    groups = [range(0, 8), range(8, 13), range(13, 16)]
    for group, dims in zip(groups, [slice(0, 8), slice(8, 16), slice(16, 24)]):
        for i in group:
            act[i, dims] += shift
    failed = np.zeros(200, bool)
    failed[:16] = True
    failed[rng.choice(np.arange(16, 200), 36, replace=False)] = True
    return np.array([f"r{i}" for i in range(200)]), failed, act, [{f"r{i}" for i in g} for g in groups]


def test_primary_gamma_recovers_small_groups_like_the_real_pools():
    means = []
    for seed in range(6):
        ids, failed, act, targets = small_groups_pool(seed)
        z = mixture.embed({"act": act}, ("act",))
        groups = mixture.axes(ids, failed, mixture.fit(z, failed, seed))
        means.append(np.mean([max(jaccard(set(g), t) for g in groups) for t in targets]))
    assert np.median(means) >= 0.9


def test_primary_gamma_spreads_failures_on_an_unstructured_pool():
    rng = np.random.default_rng(0)
    ids = np.array([f"r{i}" for i in range(200)])
    failed = np.zeros(200, bool)
    failed[rng.choice(200, 44, replace=False)] = True
    z = mixture.embed({"act": rng.normal(size=(200, 64))}, ("act",))
    assert len(mixture.axes(ids, failed, mixture.fit(z, failed, 0))) >= 5
