"""PRD 13.1 condition 2: the activation-advantage test and its base-route bootstrap."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from harness.bootstrap import advantage, mean_best_jaccard, weighted_jaccard  # noqa: E402
from harness.schema import AxisCard, Directive, Gap, SupportingEpisode  # noqa: E402
from harness.scoring import score  # noqa: E402


def directive(method, *rollout_sets):
    axes = [AxisCard("%s-%d" % (method, i), "axis %d" % i, "test axis", i + 1, 1.0, method,
                     supporting_episodes=[SupportingEpisode(r, 1.0, (0, 0)) for r in sorted(s)])
            for i, s in enumerate(rollout_sets)]
    return Directive(method, axes)


def ids(prefix, n, start=0):
    return {"%s%02d" % (prefix, i) for i in range(start, start + n)}


# Two interactional gaps over 40 base routes, one rollout per base route each.
GAP_A, GAP_B = ids("a", 20), ids("b", 20)
GAPS = [Gap("A", "T2_interactional", GAP_A), Gap("B", "T2_interactional", GAP_B)]
BASE_OF = {r: "base-" + r for r in GAP_A | GAP_B | ids("x", 20)}


def test_weighted_jaccard_counts_draws_and_scores_an_empty_union_zero():
    assert weighted_jaccard({"a", "b"}, {"b", "c"}, {"a": 1, "b": 1, "c": 1}) == pytest.approx(1 / 3)
    assert weighted_jaccard({"a", "b"}, {"b", "c"}, {"a": 0, "b": 2, "c": 0}) == 1.0
    assert weighted_jaccard({"a"}, {"b"}, {}) == 0.0


def test_unweighted_mean_best_jaccard_agrees_with_scoring():
    d = directive("contrastive", ids("a", 15), ids("b", 5) | ids("x", 5))
    assert mean_best_jaccard(d, GAPS) == pytest.approx(score(d, GAPS).mean_best_jaccard)


def test_clear_advantage_holds_with_an_interval_above_zero():
    act = {"contrastive": directive("contrastive", GAP_A, GAP_B)}
    base = {"B3_behavioral": directive("B3_behavioral", ids("x", 20))}
    rep = advantage(act, base, GAPS, BASE_OF, replicates=500)
    assert rep.recall_condition and rep.margin_condition and rep.holds
    assert rep.delta == pytest.approx(1.0) and rep.interval[0] > 0


def test_equal_recall_fails_condition_a_even_with_a_jaccard_margin():
    act = {"sae": directive("sae", GAP_A, GAP_B)}
    base = {"B2_taxonomy": directive("B2_taxonomy", GAP_A | ids("x", 3), GAP_B | ids("x", 5, start=3))}
    rep = advantage(act, base, GAPS, BASE_OF, replicates=200)
    assert rep.activation_recall == rep.best_baseline_recall == 1.0
    assert not rep.recall_condition and not rep.holds


def test_small_margin_fails_condition_b():
    act = {"sae": directive("sae", ids("a", 12), ids("b", 12))}
    base = {"B2_taxonomy": directive("B2_taxonomy", ids("a", 11), ids("b", 9))}
    rep = advantage(act, base, GAPS, BASE_OF, replicates=200)
    assert rep.delta < 0.15 and not rep.margin_condition


def test_an_advantage_resting_on_one_base_route_is_not_significant():
    one_base = {r: "only" for r in GAP_A | GAP_B} | {r: "base-" + r for r in ids("x", 20)}
    gaps = [Gap("A", "T2_interactional", GAP_A)]
    act = {"sae": directive("sae", GAP_A)}
    base = {"B1_random": directive("B1_random", ids("x", 20))}
    rep = advantage(act, base, gaps, one_base, replicates=400)
    assert rep.delta == pytest.approx(1.0)
    assert rep.interval[0] == 0.0 and not rep.margin_condition


def test_best_selections_are_remade_so_the_max_baseline_is_used():
    act = {"sae": directive("sae", GAP_A, GAP_B)}
    base = {"weak": directive("B1_random", ids("x", 20)), "strong": directive("B2_taxonomy", GAP_A)}
    rep = advantage(act, base, GAPS, BASE_OF, replicates=200)
    assert rep.delta == pytest.approx(0.5)


def test_decoys_are_ignored_and_the_result_is_seeded():
    gaps = GAPS + [Gap("D", "T2_interactional", ids("x", 20), is_decoy=True)]
    act = {"sae": directive("sae", GAP_A, ids("b", 10))}
    base = {"B1_random": directive("B1_random", ids("x", 20))}
    first = advantage(act, base, gaps, BASE_OF, replicates=300, seed=1)
    second = advantage(act, base, gaps, BASE_OF, replicates=300, seed=1)
    assert first.interval == second.interval and first.delta == pytest.approx(0.75)


def test_no_interactional_gaps_is_an_error_not_a_pass():
    with pytest.raises(ValueError):
        advantage({"sae": directive("sae")}, {"B1_random": directive("B1_random")},
                  [Gap("C", "T0_control", ids("a", 3))], BASE_OF, replicates=10)
