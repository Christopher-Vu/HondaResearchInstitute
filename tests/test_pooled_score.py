"""The held-out pooled scorer is locally testable without the optional SciPy reporting dependency."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


SCRIPT = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo/pooled_score.py"


def load_pooled_score(monkeypatch):
    # sprint_score only needs load_pool for its CLI path; the pure pooled test below supplies Model objects directly.
    scoring_run = ModuleType("harness.scoring_run")
    scoring_run.load_pool = lambda *_args: ([], {})
    monkeypatch.setitem(sys.modules, "harness.scoring_run", scoring_run)
    spec = importlib.util.spec_from_file_location("test_pooled_score_module", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pooled_score_weights_model_gap_units_and_resamples_shared_pairs(monkeypatch) -> None:
    pooled_score = load_pooled_score(monkeypatch)
    pairs = {"s1": "p1", "s2": "p2"}
    alpha = pooled_score.Model("alpha", {"G1": {"s1", "s2"}}, {"m23": [{"s1", "s2"}]},
                               {"B3_behaviour": [{"s1"}]}, pairs)
    beta = pooled_score.Model("beta", {"G1": {"s1", "s2"}}, {"m23": [{"s1"}]},
                              {"B3_behaviour": [{"s2"}]}, pairs)

    report = pooled_score.pooled([alpha, beta], replicates=50, seed=3)

    assert report["models"] == ["alpha", "beta"]
    assert report["weights"] == "each model-gap unit equally; Fail2Drive pairs jointly resampled across models"
    assert report["rows"]["m23"]["mean_best"] == 0.75
    assert report["headline_best_method_vs_best_rival"]["delta"] == 0.25
    assert len(report["headline_best_method_vs_best_rival"]["interval"]) == 2
    assert report["per_model"]["alpha"]["per_gap"]["G1"]["m23"] == 1.0
    assert report["per_model"]["beta"]["per_gap"]["G1"]["m23"] == 0.5
