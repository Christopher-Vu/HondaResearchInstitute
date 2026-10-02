"""B1 random baseline tests.

The point of a chance floor is that it behaves like chance. If B1 scores well on
a planted gap, either the gap is too prevalent to be discriminating or the
scoring is wrong, and we want to learn that here rather than from a reviewer.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from baselines.random_baseline import (  # noqa: E402
    RandomBaselineConfig, draw_directive, score_averaged,
)
from harness.schema import Gap, SchemaError  # noqa: E402
from harness.scoring import score  # noqa: E402


def gap(gap_id, tier, failing, slice_=None, *, decoy=False):
    return Gap(gap_id=gap_id, tier=tier, failing_rollouts=set(failing),
               slice_rollouts=set(slice_ if slice_ is not None else failing),
               efficacy={"fail_rate_in": 0.58, "fail_rate_neighbourhood": 0.21,
                         "fisher_p": 0.0004, "n_in": 41},
               is_decoy=decoy)


POOL = ["r%03d" % i for i in range(200)]


def test_draw_emits_a_valid_directive_at_budget():
    cfg = RandomBaselineConfig(axis_sizes=[10, 20], budget_m=10, seed=1)
    d = draw_directive(POOL, cfg)
    d.validate()
    assert len(d.axes) == 10
    assert d.method == "B1_random"
    assert [a.rank for a in d.axes] == list(range(1, 11))


def test_axis_sizes_are_matched_to_config():
    """PRD 9.3: B1 draws its set sizes from the primary method's axis sizes, so
    it cannot be beaten on set size alone."""
    cfg = RandomBaselineConfig(axis_sizes=[5, 50], budget_m=4, seed=1)
    d = draw_directive(POOL, cfg)
    assert [len(a.rollouts) for a in d.axes] == [5, 50, 5, 50]


def test_sizes_clamp_to_pool_size():
    cfg = RandomBaselineConfig(axis_sizes=[500], budget_m=2, seed=1)
    d = draw_directive(["r1", "r2", "r3"], cfg)
    assert all(len(a.rollouts) == 3 for a in d.axes)


def test_draws_are_deterministic_given_seed_and_index():
    cfg = RandomBaselineConfig(axis_sizes=[10], budget_m=3, seed=7)
    a = draw_directive(POOL, cfg, draw_index=2)
    b = draw_directive(POOL, cfg, draw_index=2)
    assert [sorted(x.rollouts) for x in a.axes] == [sorted(x.rollouts) for x in b.axes]


def test_different_draw_indices_differ():
    cfg = RandomBaselineConfig(axis_sizes=[10], budget_m=3, seed=7)
    a = draw_directive(POOL, cfg, draw_index=0)
    b = draw_directive(POOL, cfg, draw_index=1)
    assert [sorted(x.rollouts) for x in a.axes] != [sorted(x.rollouts) for x in b.axes]


def test_samples_without_replacement():
    cfg = RandomBaselineConfig(axis_sizes=[20], budget_m=5, seed=3)
    for a in draw_directive(POOL, cfg).axes:
        ids = [e.episode_id for e in a.supporting_episodes]
        assert len(ids) == len(set(ids))


def test_empty_pool_yields_empty_directive_not_a_crash():
    cfg = RandomBaselineConfig(axis_sizes=[10], budget_m=5)
    d = draw_directive([], cfg)
    assert d.axes == []
    d.validate()


def test_empty_axis_sizes_is_rejected():
    with pytest.raises(ValueError, match="size-matched"):
        draw_directive(POOL, RandomBaselineConfig(axis_sizes=[]))


def test_b1_rarely_recovers_a_small_gap_in_a_large_pool():
    """The actual contract of a chance floor.

    A 6-rollout gap inside a 200-rollout pool should essentially never be
    recovered at Jaccard >= 0.5 by random subsets. If this starts passing, the
    gap is too prevalent to discriminate between methods (PRD 10.1's
    background-failure warning) or scoring is broken.
    """
    g = [gap("g1", "T2_interactional", POOL[:6])]
    cfg = RandomBaselineConfig(axis_sizes=[6], budget_m=10, n_draws=200, seed=11)
    summary, _ = score_averaged(POOL, g, cfg)
    assert summary["recall_by_tier"]["T2_interactional"] < 0.05


def test_b1_trivially_recovers_a_gap_that_is_most_of_the_pool():
    """The complement, and a warning about prevalence.

    If a gap covers nearly the whole failing pool, random subsets hit it by
    construction. This is why PRD 9.1 caps injected slices at 40% and sizes
    prevalence with a power analysis.
    """
    small_pool = POOL[:10]
    g = [gap("g1", "T2_interactional", small_pool[:9])]
    cfg = RandomBaselineConfig(axis_sizes=[9], budget_m=10, n_draws=100, seed=5)
    summary, _ = score_averaged(small_pool, g, cfg)
    assert summary["recall_by_tier"]["T2_interactional"] > 0.5


def test_averaged_summary_reports_spread():
    g = [gap("g1", "T2_interactional", POOL[:6])]
    cfg = RandomBaselineConfig(axis_sizes=[6], budget_m=10, n_draws=50, seed=2)
    summary, reports = score_averaged(POOL, g, cfg)
    assert len(reports) == 50
    assert summary["n_draws"] == 50
    # max >= mean, so a lucky draw is visible rather than averaged away
    for tier, mean_val in summary["recall_by_tier"].items():
        assert summary["recall_by_tier_max"][tier] >= mean_val


def test_b1_axes_declare_they_are_not_describable():
    """PRD 9.2 uses B1 as the gate's incoherent-axis control, so its axes must
    not claim semantic content they do not have."""
    cfg = RandomBaselineConfig(axis_sizes=[10], budget_m=3, seed=1)
    for a in draw_directive(POOL, cfg).axes:
        assert "random" in a.name.lower()
        assert "no semantic content" in a.description


def test_b1_integrates_with_the_scoring_path():
    """End to end through the real scorer, not a fixture."""
    g = [gap("c1", "T0_control", POOL[:20]),
         gap("d1", "T1_enumerable", POOL[150:160], decoy=True)]
    cfg = RandomBaselineConfig(axis_sizes=[20], budget_m=10, seed=4)
    rep = score(draw_directive(POOL, cfg), g)
    assert rep.method == "B1_random"
    assert rep.n_axes == 10
    assert 0.0 <= rep.precision_at_m <= 1.0
    assert 0.0 <= rep.decoy_hit_rate <= 1.0
