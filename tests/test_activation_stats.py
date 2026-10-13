"""B7 activation-statistics tests, on small synthetic latent arrays."""
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from baselines.activation_stats import (  # noqa: E402
    ActivationStatsConfig, activation_stats_directive, latent_scores,
)
from harness.schema import Gap  # noqa: E402
from harness.scoring import score  # noqa: E402

FRAMES = 20
N_LATENTS = 8


def episodes(n, fires: dict[int, list[int]], *, prefix="e", strength=0.9,
             frames=FRAMES):
    """n episodes of quiet noise; fires maps latent -> episode indices where it
    spikes for 2 frames (or for `frames` frames if given as a long run)."""
    out = {}
    for i in range(n):
        acts = np.full((frames, N_LATENTS), 0.01)
        for latent, eps in fires.items():
            if i in eps:
                acts[5:7, latent] = strength
        out["%s%02d" % (prefix, i)] = acts
    return out


def cfg(**kw):
    return ActivationStatsConfig(**kw)


def test_planted_brief_strong_rare_latent_ranks_first():
    stat = episodes(20, {0: [0, 1, 2, 3]})
    for i in range(8):
        stat["e%02d" % i][8:16, 1] = 0.2
    stat["e00"][2:4, 2] = 0.3
    stat["e09"][2:4, 2] = 0.3
    stat["e10"][2:4, 2] = 0.3
    scores = latent_scores(stat, cfg())
    assert scores.latent_ids[0] == 0
    assert set(scores.latent_ids) == {0, 1, 2}
    assert list(scores.kappa) == sorted(scores.kappa, reverse=True)


def test_latent_on_in_most_episodes_is_excluded():
    stat = episodes(10, {0: list(range(6)), 1: [0, 1, 2]})
    assert 0 not in latent_scores(stat, cfg()).latent_ids
    assert 1 in latent_scores(stat, cfg()).latent_ids


def test_coverage_exactly_at_ceiling_is_kept():
    stat = episodes(10, {0: list(range(5)), 1: [0, 1, 2]})
    assert 0 in latent_scores(stat, cfg()).latent_ids


def test_latent_in_fewer_than_min_episodes_is_excluded():
    stat = episodes(20, {0: [0, 1], 1: [0, 1, 2]})
    ids = latent_scores(stat, cfg()).latent_ids
    assert 0 not in ids and 1 in ids


def test_onset_at_frame_zero_counts():
    stat = episodes(10, {})
    for i in range(3):
        stat["e%02d" % i][0, 2] = 0.9
    assert 2 in latent_scores(stat, cfg()).latent_ids


def test_firing_threshold_is_strict():
    stat = episodes(10, {})
    for i in range(3):
        stat["e%02d" % i][3, 4] = 0.1
    assert 4 not in latent_scores(stat, cfg()).latent_ids


def test_single_survivor_scores_zero_not_nan():
    stat = episodes(10, {3: [0, 1, 2]})
    scores = latent_scores(stat, cfg())
    assert list(scores.latent_ids) == [3]
    assert scores.kappa[0] == 0.0


def test_statistics_function_takes_no_labels():
    params = inspect.signature(latent_scores).parameters
    assert list(params) == ["stat_episodes", "cfg"]


def test_scores_identical_whatever_the_failing_set():
    stat = episodes(20, {0: [0, 1, 2, 3], 1: [4, 5, 6]})
    test = episodes(20, {0: [0, 1, 2, 3], 1: [4, 5, 6]}, prefix="t")
    a = activation_stats_directive(stat, test, set(), cfg())
    b = activation_stats_directive(stat, test, {"t00", "t05"}, cfg())
    assert [x.score for x in a.axes] == [x.score for x in b.axes]
    assert [x.description for x in a.axes] == [x.description for x in b.axes]


def test_near_identical_fire_sets_merge_and_disjoint_starts_new_axis():
    stat = episodes(30, {0: [0, 1, 2, 3, 4], 1: [0, 1, 2, 3, 4],
                         2: [10, 11, 12, 13, 14]})
    test = episodes(30, {0: [0, 1, 2, 3, 4], 1: [0, 1, 2, 3, 4, 5],
                         2: [10, 11, 12, 13, 14]}, prefix="t")
    failing = {"t00", "t03", "t10", "t12", "t20"}
    d = activation_stats_directive(stat, test, failing, cfg())
    assert len(d.axes) == 2
    merged = next(a for a in d.axes if "0, 1" in a.description
                  or "1, 0" in a.description)
    assert merged.rollouts == {"t00", "t03"}
    other = next(a for a in d.axes if a is not merged)
    assert other.rollouts == {"t10", "t12"}


def test_budget_stops_the_walk():
    fires = {i: [3 * i, 3 * i + 1, 3 * i + 2] for i in range(N_LATENTS)}
    stat = episodes(30, fires)
    test = episodes(30, fires, prefix="t")
    failing = set(test)
    d = activation_stats_directive(stat, test, failing, cfg(budget_m=3))
    assert len(d.axes) == 3
    assert [a.rank for a in d.axes] == [1, 2, 3]


def test_latent_that_never_fires_in_test_pool_is_skipped():
    stat = episodes(20, {0: [0, 1, 2], 1: [3, 4, 5]})
    test = episodes(20, {1: [3, 4, 5]}, prefix="t")
    d = activation_stats_directive(stat, test, set(test), cfg())
    assert len(d.axes) == 1
    assert "[1]" in d.axes[0].description


def test_members_are_failing_rollouts_only_with_span_and_peak():
    stat = episodes(20, {0: [0, 1, 2, 3]})
    test = episodes(20, {0: [0, 1, 2, 3]}, prefix="t")
    test["t01"][9, 0] = 1.5
    d = activation_stats_directive(stat, test, {"t01", "t02", "t15"}, cfg())
    axis = d.axes[0]
    assert axis.rollouts == {"t01", "t02"}
    by_id = {e.episode_id: e for e in axis.supporting_episodes}
    assert by_id["t01"].timesteps == (5, 9)
    assert by_id["t01"].activation == pytest.approx(1.5)
    assert by_id["t02"].timesteps == (5, 6)


def test_card_fields_follow_the_spec():
    stat = episodes(20, {0: [0, 1, 2, 3]})
    test = episodes(20, {0: [0, 1, 2, 3]}, prefix="t")
    d = activation_stats_directive(stat, test, {"t00"}, cfg(variant="B"))
    card = d.axes[0]
    assert d.method == "B7_actstats" and card.method == "B7_actstats"
    assert card.name == "B7 latent group 1"
    assert "variant B" in card.description
    assert "not describability-gated" in card.description
    assert card.causal == {"verdict": "untested"}


def test_failing_ids_unknown_to_test_pool_are_rejected():
    stat = episodes(20, {0: [0, 1, 2]})
    test = episodes(20, {0: [0, 1, 2]}, prefix="t")
    with pytest.raises(ValueError):
        activation_stats_directive(stat, test, {"nope"}, cfg())


def test_bad_config_and_shapes_are_rejected():
    with pytest.raises(ValueError):
        cfg(variant="C").validate()
    with pytest.raises(ValueError):
        latent_scores({}, cfg())
    with pytest.raises(ValueError):
        latent_scores({"a": np.zeros(5)}, cfg())


def test_directive_validates_and_scores_against_a_gap():
    stat = episodes(30, {0: [0, 1, 2, 3, 4], 1: [10, 11, 12, 13]})
    test = episodes(30, {0: [0, 1, 2, 3, 4], 1: [10, 11, 12, 13]}, prefix="t")
    failing = {"t00", "t01", "t02", "t03", "t04", "t10", "t11"}
    d = activation_stats_directive(stat, test, failing, cfg())
    d.validate()
    gap = Gap(gap_id="g1", tier="T1_enumerable",
              failing_rollouts={"t00", "t01", "t02", "t03", "t04"},
              slice_rollouts={"t00", "t01", "t02", "t03", "t04"},
              efficacy={"fail_rate_in": 0.58, "fail_rate_neighbourhood": 0.21,
                        "fisher_p": 0.0004, "n_in": 41})
    report = score(d, [gap])
    assert report.mean_best_jaccard == pytest.approx(1.0)
