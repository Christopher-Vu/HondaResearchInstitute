"""H22's scorer on synthetic Fail2Drive pairs: failing sets, the guarded pair reading, B2 kept out, and the rule."""
import importlib.util
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.schema import AxisCard, Directive, SupportingEpisode  # noqa: E402
from harness.scoring_run import Emitted  # noqa: E402

PATH = Path(__file__).resolve().parents[1] / "docs/research/experiments/h22-f2d-frozen-eval/score.py"
spec = importlib.util.spec_from_file_location("h22_score", PATH)
score = importlib.util.module_from_spec(spec)
sys.modules["h22_score"] = score
spec.loader.exec_module(score)

WALL = "F2D_Wall"


def manifest():
    """Five Wall pairs: slices s0..s4 with twins t0..t4, plus one pair from an unscreened category."""
    entries = []
    for i in range(5):
        entries.append({"id": f"s{i}", "base_id": f"b{i}", "role": "pilot_slice", "practice_gaps": [WALL]})
        entries.append({"id": f"t{i}", "base_id": f"b{i}", "role": "pilot_neighbourhood", "practice_gaps": []})
    entries.append({"id": "x", "base_id": "bx", "role": "pilot_slice", "practice_gaps": ["F2D_Animals"]})
    entries.append({"id": "y", "base_id": "bx", "role": "pilot_neighbourhood", "practice_gaps": []})
    return entries


FAILED = {"s0": True, "s1": True, "s2": True, "s3": False, "s4": True, "t0": False, "t1": False, "t2": False,
          "t3": False, "t4": True, "x": True, "y": False}


def emitted(family, axes, dictionary=None, counts=True):
    cards = [AxisCard(axis_id=f"a{i}", name="n", description="d", rank=i + 1, score=1.0, method="M1_contrastive",
                      supporting_episodes=[SupportingEpisode(r, 1.0, (0, 1)) for r in sorted(members)])
             for i, members in enumerate(axes)]
    label = f"{family}@{dictionary}"
    return Emitted(label, family, "activation", dictionary, counts, Directive(method="M1_contrastive", axes=cards))


def test_failing_set_is_the_category_slices_that_failed():
    sets = score.category_sets(manifest(), FAILED)
    assert sets[WALL] == {"s0", "s1", "s2", "s4"}
    assert sets["F2D_CustomObstacles"] == set()


def test_slice_only_pairs_drop_pairs_whose_twin_also_failed():
    assert score.slice_only_pairs(manifest(), FAILED)[WALL] == [("s0", "t0"), ("s1", "t1"), ("s2", "t2")]


def test_pair_hit_needs_slice_without_twin_and_the_jaccard_floor():
    pairs = [("s0", "t0"), ("s1", "t1"), ("s2", "t2")]
    failing = {"s0", "s1", "s2", "s4"}
    good = emitted("M1_raw", [{"s0", "s1"}])
    with_twin = emitted("M1_raw", [{"s0", "s1", "t0"}])
    too_broad = emitted("M1_raw", [{"s0"} | {f"z{i}" for i in range(20)}])
    assert score.pair_hits(good, pairs, failing) == 2
    assert score.pair_hits(with_twin, pairs, failing) == 1
    assert score.pair_hits(too_broad, pairs, failing) == 0


def test_delta_repicks_best_method_and_rival_and_ignores_b2():
    rows = {"m": np.array([0.8, 0.1, 0.1]), "c": np.array([0.1, 0.8, 0.1]), "r": np.array([0.3, 0.3, 0.3]),
            "b2": np.array([1.0, 1.0, 1.0])}
    families = {"m": ("M1_raw", "d0"), "c": ("M1_capped", "d0"), "r": ("B1_random", None)}
    assert score.dictionary_deltas(rows, families, ["d0"], np.array([1.0, 0.0, 0.0])) == [0.8 - 0.3]
    assert score.dictionary_deltas(rows, families, ["d0"], np.array([0.0, 1.0, 0.0])) == [0.8 - 0.3]
    assert abs(score.dictionary_deltas(rows, families, ["d0"], np.ones(3))[0] - (1 / 3 - 0.3)) < 1e-12


def test_rule_needs_margin_and_positive_lower_bound_and_enough_dictionaries():
    full = {f: 18 for f in ("M1_raw", "M1_capped", "B7_pool")}
    assert score.outcome(full, {"median_delta": 0.2, "interval": [0.01, 0.4]}) == "ahead"
    assert score.outcome(full, {"median_delta": 0.2, "interval": [-0.01, 0.4]}) == "not_ahead"
    assert score.outcome(full, {"median_delta": 0.1, "interval": [0.05, 0.4]}) == "not_ahead"
    assert score.outcome({**full, "B7_pool": 11}, {"median_delta": 0.9, "interval": [0.5, 1]}) == "untested"
    assert score.outcome(full, None) == "untested"
