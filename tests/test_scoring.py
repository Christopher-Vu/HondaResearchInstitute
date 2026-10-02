"""Tests for the planted-gap scoring layer.

These run with no GPU, no cluster and no rollouts, which is the point: the
headline metric of the paper is verified on synthetic data before any real
rollout exists. If the arithmetic is wrong, we find out now rather than after
burning the allowance.

    python -m pytest tests/ -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.schema import (  # noqa: E402
    AxisCard, Directive, Gap, SchemaError, SupportingEpisode,
)
from harness.scoring import (  # noqa: E402
    harness_is_valid, jaccard, score, validated_precision,
)


def axis(axis_id, rollouts, *, rank=1, method="sae", score_=1.0):
    return AxisCard(
        axis_id=axis_id, name="named " + axis_id, description="desc",
        rank=rank, score=score_, method=method,
        supporting_episodes=[
            SupportingEpisode(r, 1.0, (0, 1)) for r in rollouts
        ],
    )


def gap(gap_id, tier, failing, slice_=None, *, decoy=False, efficacious=True):
    eff = ({"fail_rate_in": 0.58, "fail_rate_neighbourhood": 0.21,
            "fisher_p": 0.0004, "n_in": 41} if efficacious else
           {"fail_rate_in": 0.25, "fail_rate_neighbourhood": 0.21,
            "fisher_p": 0.4, "n_in": 12})
    return Gap(gap_id=gap_id, tier=tier, failing_rollouts=set(failing),
               slice_rollouts=set(slice_ if slice_ is not None else failing),
               efficacy=eff, is_decoy=decoy)


# --------------------------------------------------------------------------
# jaccard
# --------------------------------------------------------------------------

def test_jaccard_basic():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a", "b"}, {"c"}) == 0.0
    assert jaccard({"a", "b", "c", "d"}, {"a", "b"}) == 0.5


def test_jaccard_both_empty_is_zero_not_one():
    """An axis claiming nothing has not recovered a gap containing nothing.
    Returning 1.0 here would let a method score perfectly by emitting nothing."""
    assert jaccard(set(), set()) == 0.0


# --------------------------------------------------------------------------
# matching
# --------------------------------------------------------------------------

def test_perfect_recovery():
    g = [gap("g1", "T2_interactional", ["r1", "r2", "r3"])]
    d = Directive("sae", [axis("a1", ["r1", "r2", "r3"])])
    rep = score(d, g)
    assert rep.recall_by_tier["T2_interactional"] == 1.0
    assert rep.matches[0].jaccard == 1.0
    assert rep.precision_at_m == pytest.approx(0.1)  # 1 match / M=10


def test_below_threshold_is_not_a_match():
    """Jaccard 0.4 < theta 0.5. Partial overlap is reported, not credited."""
    g = [gap("g1", "T2_interactional", ["r1", "r2", "r3", "r4"])]
    d = Directive("sae", [axis("a1", ["r1", "r2"])])
    rep = score(d, g)
    assert rep.matches[0].jaccard == pytest.approx(0.5)
    assert rep.matches[0].matched is True
    # now push it under
    d2 = Directive("sae", [axis("a1", ["r1", "r5", "r6"])])
    rep2 = score(d2, g)
    assert rep2.matches[0].matched is False


def test_one_axis_cannot_be_credited_for_two_gaps():
    """The core reason we use a single Hungarian assignment rather than greedy
    per-gap best match: a broad axis overlapping two gaps must be charged to
    only one of them."""
    g = [gap("g1", "T2_interactional", ["r1", "r2"]),
         gap("g2", "T2_interactional", ["r3", "r4"])]
    broad = axis("broad", ["r1", "r2", "r3", "r4"])
    rep = score(Directive("sae", [broad]), g)
    credited = [m for m in rep.matches if m.axis_id == "broad"]
    assert len(credited) == 1, "same axis matched to both gaps"
    assert sum(m.matched for m in rep.matches) <= 1


def test_assignment_is_globally_optimal_not_greedy():
    """Greedy would take the locally best pair first and strand the other gap.
    g1 overlaps a_both slightly more than g2 does, but assigning a_both to g1
    leaves g2 with nothing, so the optimal total takes the other arrangement."""
    g = [gap("g1", "T2_interactional", ["r1", "r2", "r3", "r4"]),
         gap("g2", "T2_interactional", ["r5", "r6"])]
    a_both = axis("a_both", ["r1", "r2", "r5", "r6"])
    a_g1 = axis("a_g1", ["r1", "r2", "r3", "r4"])
    rep = score(Directive("sae", [a_both, a_g1]), g)
    by_gap = {m.gap_id: m for m in rep.matches}
    assert by_gap["g1"].axis_id == "a_g1"
    assert by_gap["g2"].axis_id == "a_both"
    assert all(m.matched for m in rep.matches)


def test_precision_divides_by_budget_not_axis_count():
    """PRD 10.2. A method emitting 1 perfect axis must not score precision 1.0;
    otherwise emitting a single safe axis beats a full directive."""
    g = [gap("g1", "T2_interactional", ["r1", "r2"])]
    rep = score(Directive("sae", [axis("a1", ["r1", "r2"])], budget_m=10), g)
    assert rep.precision_at_m == pytest.approx(0.1)
    rep5 = score(Directive("sae", [axis("a1", ["r1", "r2"])], budget_m=5), g)
    assert rep5.precision_at_m == pytest.approx(0.2)


def test_recall_is_reported_per_tier():
    g = [gap("c1", "T0_control", ["r1", "r2"]),
         gap("e1", "T1_enumerable", ["r3", "r4"]),
         gap("i1", "T2_interactional", ["r5", "r6"]),
         gap("i2", "T2_interactional", ["r7", "r8"])]
    d = Directive("sae", [axis("a1", ["r1", "r2"]), axis("a2", ["r5", "r6"])])
    rep = score(d, g)
    assert rep.recall_by_tier["T0_control"] == 1.0
    assert rep.recall_by_tier["T1_enumerable"] == 0.0
    assert rep.recall_by_tier["T2_interactional"] == 0.5


def test_mean_best_jaccard_ignores_the_assignment():
    """PRD 10.3 reports it unconstrained, so it can exceed what the assignment
    credits."""
    g = [gap("g1", "T2_interactional", ["r1", "r2"]),
         gap("g2", "T2_interactional", ["r1", "r2"])]
    rep = score(Directive("sae", [axis("a1", ["r1", "r2"])]), g)
    assert rep.mean_best_jaccard == pytest.approx(1.0)
    assert sum(m.matched for m in rep.matches) == 1


def test_empty_directive_scores_zero_without_crashing():
    g = [gap("g1", "T2_interactional", ["r1", "r2"])]
    rep = score(Directive("B1_random", []), g)
    assert rep.precision_at_m == 0.0
    assert rep.recall_by_tier["T2_interactional"] == 0.0
    assert rep.mean_best_jaccard == 0.0


# --------------------------------------------------------------------------
# decoys
# --------------------------------------------------------------------------

def test_decoys_are_not_scored_as_gaps_but_are_counted_as_hits():
    """A decoy is a trap, not a target: it must not appear in recall, and an
    axis that lands in it must be flagged (PRD 9.1, 10.3)."""
    g = [gap("g1", "T2_interactional", ["r1", "r2"]),
         gap("d1", "T1_enumerable", ["r8", "r9"], decoy=True, efficacious=False)]
    d = Directive("sae", [axis("a1", ["r1", "r2"]), axis("a_trap", ["r8", "r9"])])
    rep = score(d, g)
    assert [m.gap_id for m in rep.matches] == ["g1"]
    assert rep.decoy_hit_rate == pytest.approx(0.5)


# --------------------------------------------------------------------------
# efficacy
# --------------------------------------------------------------------------

def test_efficacy_requires_all_four_conditions():
    good = gap("g1", "T2_interactional", ["r1"])
    assert good.passes_efficacy() is True
    weak = gap("g2", "T2_interactional", ["r1"], efficacious=False)
    assert weak.passes_efficacy() is False


def test_efficacy_rejects_high_uplift_with_too_few_rollouts():
    """n_in < 30 fails even on a large effect: the winner's curse is the whole
    reason the threshold exists (PRD 9.1)."""
    g = Gap("g", "T2_interactional", {"r1"}, {"r1"},
            {"fail_rate_in": 0.9, "fail_rate_neighbourhood": 0.1,
             "fisher_p": 0.001, "n_in": 12})
    assert g.passes_efficacy() is False


def test_efficacy_rejects_ratio_below_two_even_with_large_uplift():
    """55% vs 30% is +25pp but only 1.83x, so it fails the ratio arm."""
    g = Gap("g", "T2_interactional", {"r1"}, {"r1"},
            {"fail_rate_in": 0.55, "fail_rate_neighbourhood": 0.30,
             "fisher_p": 0.001, "n_in": 100})
    assert g.passes_efficacy() is False


def test_attributable_share():
    g = gap("g1", "T2_interactional", ["r1"])
    assert g.attributable_share == pytest.approx(1 - 0.21 / 0.58, abs=1e-6)


def test_incomplete_efficacy_stats_raise():
    g = Gap("g", "T2_interactional", {"r1"}, {"r1"}, {"fail_rate_in": 0.5})
    with pytest.raises(SchemaError):
        g.passes_efficacy()


# --------------------------------------------------------------------------
# harness validity (PRD 13.1 condition 1)
# --------------------------------------------------------------------------

def test_harness_invalid_without_t0_recovery():
    g = [gap("c1", "T0_control", ["r1", "r2"]),
         gap("i1", "T2_interactional", ["r5", "r6"]),
         gap("i2", "T2_interactional", ["r7", "r8"])]
    reports = {"sae": score(Directive("sae", [axis("a1", ["r5", "r6"])]), g)}
    ok, why = harness_is_valid(reports, g)
    assert ok is False and "T0" in why


def test_harness_invalid_with_too_few_efficacious_t2():
    g = [gap("c1", "T0_control", ["r1", "r2"]),
         gap("i1", "T2_interactional", ["r5", "r6"], efficacious=False)]
    reports = {"sae": score(Directive("sae", [axis("a1", ["r1", "r2"])]), g)}
    ok, why = harness_is_valid(reports, g)
    assert ok is False and "T2" in why


def test_harness_valid_when_both_conditions_hold():
    g = [gap("c1", "T0_control", ["r1", "r2"]),
         gap("i1", "T2_interactional", ["r5", "r6"]),
         gap("i2", "T2_interactional", ["r7", "r8"])]
    reports = {"sae": score(Directive("sae", [axis("a1", ["r1", "r2"])]), g)}
    ok, why = harness_is_valid(reports, g)
    assert ok is True, why


# --------------------------------------------------------------------------
# validated precision
# --------------------------------------------------------------------------

def test_validated_precision_credits_reproducing_unmatched_axes():
    """PRD 9.4: an axis matching no planted gap but reproducing under test is a
    validated natural axis, not an error."""
    g = [gap("g1", "T2_interactional", ["r1", "r2"])]
    d = Directive("sae", [axis("a1", ["r1", "r2"]), axis("a_nat", ["r9"])])
    rep = score(d, g)
    assert rep.precision_at_m == pytest.approx(0.1)
    assert validated_precision(rep, ["a_nat"]) == pytest.approx(0.2)


def test_validated_precision_does_not_double_count_matched_axes():
    g = [gap("g1", "T2_interactional", ["r1", "r2"])]
    rep = score(Directive("sae", [axis("a1", ["r1", "r2"])]), g)
    assert validated_precision(rep, ["a1"]) == pytest.approx(0.1)


# --------------------------------------------------------------------------
# schema contracts
# --------------------------------------------------------------------------

def test_axis_without_name_is_rejected():
    with pytest.raises(SchemaError, match="cluster, not a discovery"):
        AxisCard("a", "   ", "desc", 1, 1.0, "sae").validate()


def test_directive_over_budget_is_rejected():
    axes = [axis("a%d" % i, ["r%d" % i], rank=i + 1) for i in range(11)]
    with pytest.raises(SchemaError, match="exceeds budget"):
        Directive("sae", axes, budget_m=10).validate()


def test_unknown_method_is_rejected():
    with pytest.raises(SchemaError, match="unknown method"):
        AxisCard("a", "n", "d", 1, 1.0, "handwave").validate()


def test_gap_failing_rollouts_must_subset_slice():
    g = Gap("g", "T2_interactional", {"r1", "r99"}, {"r1", "r2"})
    with pytest.raises(SchemaError, match="not a subset"):
        g.validate()


def test_axis_from_dict_roundtrip():
    card = AxisCard.from_dict({
        "axis_id": "M2-L14-latent-5531", "name": "occluded oncoming",
        "description": "oncoming vehicle occluded during unprotected left",
        "rank": 1, "score": 0.37,
        "supporting_episodes": [
            {"episode_id": "test-000812", "activation": 0.9, "timesteps": [40, 61]},
        ],
        "provenance": {"method": "sae", "config_hash": "deadbeef",
                       "layer": "14", "aggregation": "mean",
                       "preprocessing": ["P-std", "P-resid"]},
        "causal": {"verdict": "causal", "ablation_delta": 0.92},
        "gate": {"auroc": 0.81, "shuffle_auroc": 0.52, "passed": True},
    })
    assert card.rollouts == {"test-000812"}
    assert card.preprocessing == ["P-std", "P-resid"]
    assert card.causal["verdict"] == "causal"


def test_bad_causal_verdict_is_rejected():
    with pytest.raises(SchemaError, match="causal.verdict"):
        AxisCard("a", "n", "d", 1, 1.0, "sae", causal={"verdict": "probably"}).validate()
