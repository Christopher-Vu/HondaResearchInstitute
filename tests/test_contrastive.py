
import numpy as np

from src.discovery.contrastive import standardized_mean_difference


def test_standardized_mean_difference():
    successes = np.array([
        [1.0, 2.0],
        [2.0, 2.0],
        [3.0, 2.0],
    ])

    failures = np.array([
        [5.0, 2.0],
        [6.0, 2.0],
        [7.0, 2.0],
    ])

    scores = standardized_mean_difference(failures, successes)

    assert scores[0] > 0
    assert scores[1] == 0


from src.discovery.contrastive import firing_rate_log_odds


def test_firing_rate_log_odds():
    successes = np.array([
        [0.0, 1.0],
        [0.0, 1.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ])

    failures = np.array([
        [1.0, 1.0],
        [1.0, 1.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ])

    scores = firing_rate_log_odds(failures, successes)

    assert scores[0] > 0
    assert scores[1] == 0


from src.discovery.contrastive import select_significant_features


def test_select_significant_features():
    p_values = np.array([
        0.001,
        0.01,
        0.20,
        0.80,
    ])

    selected = select_significant_features(p_values)

    assert selected.tolist() == [
        True,
        True,
        False,
        False,
    ]


def test_reject_invalid_p_values():
    import pytest

    with pytest.raises(ValueError):
        select_significant_features(np.array([0.01, 1.5]))


from src.discovery.contrastive import rollout_level_pvalues


def test_rollout_level_pvalues():
    rng = np.random.default_rng(42)

    successes = [
        rng.normal(0, 1, size=(10, 3))
        for _ in range(30)
    ]

    failures = [
        rng.normal([3, 0, 0], 1, size=(10, 3))
        for _ in range(30)
    ]

    p_values = rollout_level_pvalues(failures, successes)
    selected = select_significant_features(p_values)

    assert p_values.shape == (3,)
    assert selected[0]
    assert not selected[1]
    assert not selected[2]


from src.discovery.contrastive import (
    feature_rollout_support,
    apply_support_filter,
)


def test_feature_rollout_support():
    rollouts = [
        np.array([[1.0, 0.0], [2.0, 0.0]]),
        np.array([[3.0, 0.0], [0.0, 0.0]]),
        np.array([[0.0, 1.0], [0.0, 2.0]]),
    ]

    support = feature_rollout_support(rollouts)

    assert support.tolist() == [2, 1]


def test_apply_support_filter():
    significant = np.array([True, True, False])
    support = np.array([25, 10, 30])

    selected = apply_support_filter(
        significant,
        support,
        min_rollouts=20,
    )

    assert selected.tolist() == [True, False, False]


from src.discovery.contrastive import group_cofiring_features


def test_group_cofiring_features():
    activations = np.array([
        [1.0, 2.0, 5.0],
        [2.0, 4.0, 3.0],
        [3.0, 6.0, 5.0],
        [4.0, 8.0, 3.0],
        [5.0, 10.0, 5.0],
    ])

    selected = np.array([True, True, True])

    groups = group_cofiring_features(
        activations,
        selected,
        correlation_threshold=0.9,
    )

    assert [0, 1] in groups
    assert [2] in groups


from src.discovery.contrastive import rank_candidate_axes


def test_rank_candidate_axes():
    groups = [[0, 1], [2]]

    effect_sizes = np.array([2.0, 3.0, 1.0])
    support = np.array([25, 30, 20])

    ranked = rank_candidate_axes(
        groups,
        effect_sizes,
        support,
    )

    assert len(ranked) == 2
    assert ranked[0]["features"] == [0, 1]
    assert ranked[0]["score"] == 75.0
    assert ranked[1]["score"] == 20.0


from src.discovery.contrastive import build_directive


def test_build_directive():
    candidates = [
        {"features": [0, 1], "score": 75.0},
        {"features": [2], "score": 20.0},
    ]

    # Illustrative descriptions for synthetic test data only.
    descriptions = {
        0: ("Synthetic axis A", "A synthetic feature group for testing."),
        1: ("Synthetic axis B", "Another synthetic feature group."),
    }

    directive = build_directive(
        candidates,
        descriptions,
        budget_m=2,
    )

    assert len(directive.axes) == 2
    assert directive.axes[0].rank == 1
    assert directive.axes[0].score == 75.0
    assert directive.axes[0].method == "contrastive"
    assert directive.axes[1].rank == 2


from src.discovery.contrastive import discover_candidate_axes


def test_discover_candidate_axes():
    rng = np.random.default_rng(42)

    successes = [
        rng.normal(0, 1, size=(20, 3))
        for _ in range(30)
    ]

    failures = [
        rng.normal([3, 3, 0], 1, size=(20, 3))
        for _ in range(30)
    ]

    candidates = discover_candidate_axes(
        failures,
        successes,
        min_rollouts=20,
    )

    assert len(candidates) >= 1

    discovered_features = {
        feature
        for candidate in candidates
        for feature in candidate["features"]
    }

    assert 0 in discovered_features
    assert 1 in discovered_features
    assert 2 not in discovered_features


from src.discovery.contrastive import axis_rollout_support


def test_axis_rollout_support():
    rollouts = [
        np.array([[1.0, 0.0, 0.0]]),
        np.array([[0.0, 1.0, 0.0]]),
        np.array([[0.0, 0.0, 1.0]]),
        np.array([[1.0, 1.0, 0.0]]),
    ]

    groups = [[0, 1], [2]]

    support = axis_rollout_support(rollouts, groups)

    assert support == [3, 1]

def test_rank_axes_with_axis_support():
    groups = [[0, 1], [2]]
    effects = np.array([2.0, 3.0, 1.0])
    feature_support = np.array([10, 12, 20])
    group_support = [18, 20]

    ranked = rank_candidate_axes(
        groups,
        effects,
        feature_support,
        axis_support=group_support,
    )

    assert ranked[0]["features"] == [0, 1]
    assert ranked[0]["support"] == 18
    assert ranked[0]["score"] == 45.0
    assert ranked[1]["score"] == 20.0

def test_constant_features_not_discovered():
    rng = np.random.default_rng(123)

    successes = [
        np.column_stack([
            rng.normal(0, 1, 20),
            np.ones(20),
        ])
        for _ in range(30)
    ]

    failures = [
        np.column_stack([
            rng.normal(3, 1, 20),
            np.ones(20),
        ])
        for _ in range(30)
    ]

    candidates = discover_candidate_axes(
        failures,
        successes,
        min_rollouts=20,
    )

    discovered = {
        feature
        for candidate in candidates
        for feature in candidate["features"]
    }

    assert 0 in discovered
    assert 1 not in discovered
