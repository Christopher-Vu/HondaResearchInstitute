"""The H21b reproduction scorer keeps the deliberate subtlety jaccard(empty, empty) == 0."""
import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "results/h21/repro/score_repro.py"
spec = importlib.util.spec_from_file_location("score_repro", PATH)
score_repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_repro)


def test_jaccard_of_two_empty_sets_is_zero():
    assert score_repro.jaccard(frozenset(), frozenset()) == 0.0


def test_empty_axis_scores_zero_under_bootstrap_weights():
    import numpy as np

    axes = np.zeros((1, 3), dtype=bool)
    gaps = np.zeros((1, 3), dtype=bool)
    assert score_repro.weighted_best_jaccard(axes, gaps, np.ones((2, 3))).tolist() == [0.0, 0.0]
