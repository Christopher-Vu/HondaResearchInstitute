import numpy as np

from discovery.contrastive import Rollout
from discovery.contrastive_stability import (
    resample_by_base,
    evaluate_stability,
    axis_similarity,
    summarize_stability,
)


# ============================================================
# TEST 1: Resampling keeps related rollouts together
# ============================================================

def test_resampling_keeps_related_rollouts_together():
    rollout_ids = ["a1", "a2", "b1", "b2", "c1", "c2"]

    base_ids = {
        "a1": "a",
        "a2": "a",
        "b1": "b",
        "b2": "b",
        "c1": "c",
        "c2": "c",
    }

    selected = resample_by_base(
        rollout_ids,
        base_ids,
        seed=42,
        keep_fraction=0.67,
    )

    for base in ["a", "b", "c"]:
        members = {r for r in rollout_ids if base_ids[r] == base}
        assert members.issubset(selected) or members.isdisjoint(selected)


# ============================================================
# TEST 2: Resampling is reproducible
# ============================================================

def test_resampling_is_reproducible():
    rollout_ids = ["a", "b", "c", "d", "e"]
    base_ids = {r: r for r in rollout_ids}

    first = resample_by_base(rollout_ids, base_ids, seed=123)
    second = resample_by_base(rollout_ids, base_ids, seed=123)

    assert first == second


# ============================================================
# HELPER: Generate synthetic driving rollouts
# ============================================================

def make_rollouts(n=40, seed=42):
    rng = np.random.default_rng(seed)
    steps = np.arange(0, 200, 5)

    rollouts = []

    for i in range(n):
        failed = i < n // 2
        latents = rng.uniform(0, 0.05, size=(40, 12))

        if failed:
            latents[20:30, 3] = 1.0

        rollouts.append(
            Rollout(
                f"r{i}",
                latents,
                steps,
                failed,
                150 if failed else None,
            )
        )

    base_ids = {f"r{i}": f"base{i}" for i in range(n)}

    return rollouts, base_ids


# ============================================================
# TEST 3: Evaluation runs both methods
# ============================================================

def test_stability_evaluation_runs_both_methods():
    rollouts, base_ids = make_rollouts()

    results = evaluate_stability(
        rollouts,
        base_ids,
        seeds=range(3),
    )

    assert len(results) == 6

    assert {r["method"] for r in results} == {
        "uncapped",
        "capped",
    }

    assert all(
        0 <= r["largest_axis_share"] <= 1
        for r in results
    )


# ============================================================
# TEST 4: Identical axes have perfect similarity
# ============================================================

def test_identical_axes_have_perfect_similarity():
    axes = [{"r1", "r2"}, {"r3", "r4"}]
    shared = {"r1", "r2", "r3", "r4"}

    assert axis_similarity(axes, axes, shared) == 1.0


# ============================================================
# TEST 5: Disjoint axes have zero similarity
# ============================================================

def test_disjoint_axes_have_zero_similarity():
    a = [{"r1", "r2"}]
    b = [{"r3", "r4"}]
    shared = {"r1", "r2", "r3", "r4"}

    assert axis_similarity(a, b, shared) == 0.0


# ============================================================
# TEST 6: Ignore unshared rollouts
# ============================================================

def test_similarity_ignores_unshared_rollouts():
    a = [{"r1", "r2", "r3"}]
    b = [{"r1", "r2", "r4"}]
    shared = {"r1", "r2"}

    assert axis_similarity(a, b, shared) == 1.0


# ============================================================
# TEST 7: Stability values are valid
# ============================================================

def test_stability_is_reported_after_first_seed():
    rollouts, base_ids = make_rollouts(n=60, seed=7)

    results = evaluate_stability(
        rollouts,
        base_ids,
        seeds=range(3),
    )

    assert len(results) == 6

    for method in ("uncapped", "capped"):
        rows = [
            r for r in results
            if r["method"] == method
        ]

        assert len(rows) == 3

        assert all(
            r["stability"] is None
            or 0 <= r["stability"] <= 1
            for r in rows
        )


# ============================================================
# TEST 8: Summary aggregates both methods
# ============================================================

def test_summary_aggregates_both_methods():
    results = [
        {
            "method": "uncapped",
            "stability": None,
            "n_axes": 2,
            "largest_axis_share": 0.9,
        },
        {
            "method": "uncapped",
            "stability": 0.8,
            "n_axes": 2,
            "largest_axis_share": 0.8,
        },
        {
            "method": "capped",
            "stability": None,
            "n_axes": 1,
            "largest_axis_share": 0.5,
        },
        {
            "method": "capped",
            "stability": 0.6,
            "n_axes": 0,
            "largest_axis_share": 0.0,
        },
    ]

    summary = summarize_stability(results)

    assert summary["uncapped"]["mean_stability"] == 0.8
    assert summary["uncapped"]["mean_axes"] == 2.0
    assert summary["capped"]["empty_axis_frequency"] == 0.5


# ============================================================
# TEST 9: All-pairs stability is order-independent
# ============================================================

def test_all_pairs_stability_is_order_independent():
    rollouts, base_ids = make_rollouts(n=40, seed=42)

    forward = evaluate_stability(
        rollouts,
        base_ids,
        seeds=range(3),
    )

    reverse = evaluate_stability(
        rollouts,
        base_ids,
        seeds=range(2, -1, -1),
    )

    for method in ("uncapped", "capped"):
        forward_values = sorted(
            r["stability"]
            for r in forward
            if r["method"] == method
            and r["stability"] is not None
        )

        reverse_values = sorted(
            r["stability"]
            for r in reverse
            if r["method"] == method
            and r["stability"] is not None
        )

        assert np.allclose(
            forward_values,
            reverse_values,
        )