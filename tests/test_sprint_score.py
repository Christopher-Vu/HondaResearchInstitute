"""Regression tests for the discovery sprint's public development scorer."""
import importlib.util
import sys
import types
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# This unit test exercises the B1 candidate-pool rule, not route-file parsing.
# Avoid importing scoring_run's optional SciPy-backed efficacy reader.
scoring_run = types.ModuleType("harness.scoring_run")
scoring_run.load_pool = lambda *_: None
sys.modules["harness.scoring_run"] = scoring_run

PATH = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo/sprint_score.py"
spec = importlib.util.spec_from_file_location("sprint_score", PATH)
score = importlib.util.module_from_spec(spec)
sys.modules["sprint_score"] = score
spec.loader.exec_module(score)
del sys.modules["harness.scoring_run"]


def test_chance_baseline_samples_only_failed_routes():
    """Methods describe failed routes, so B1 must use that same candidate pool."""
    failed = {"failed-b": True, "passed": False, "failed-a": True}
    assert score.failing_ids(failed) == ["failed-a", "failed-b"]
