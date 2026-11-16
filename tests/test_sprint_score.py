"""Regression tests for the discovery sprint's development-only scorer."""
import importlib.util
import json
import sys
import types
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# The scorer's pool loader imports SciPy. This test supplies a tiny synthetic
# pool directly, so the candidate-pool rule stays testable without SciPy.
scoring_run = types.ModuleType("harness.scoring_run")
scoring_run.load_pool = lambda *_: None
sys.modules["harness.scoring_run"] = scoring_run

PATH = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo/sprint_score.py"
spec = importlib.util.spec_from_file_location("sprint_score", PATH)
score = importlib.util.module_from_spec(spec)
sys.modules["sprint_score"] = score
spec.loader.exec_module(score)
del sys.modules["harness.scoring_run"]


def test_chance_baseline_draws_only_from_failed_routes(tmp_path, monkeypatch):
    """The chance control must match the population that a method can describe."""
    method = tmp_path / "method.json"
    method.write_text(json.dumps({"method": "m", "axes": [{"name": "a", "rollouts": ["failed"]}]}))
    output = tmp_path / "report.json"
    manifest = [
        {"id": "failed", "role": "pilot_slice", "practice_gaps": ["G"], "pair": "a"},
        {"id": "passed", "role": "pilot_neighbourhood", "practice_gaps": [], "pair": "b"},
    ]
    monkeypatch.setattr(score, "load_pool", lambda *_: (manifest, {"failed": True, "passed": False}))
    monkeypatch.setattr(sys, "argv", ["sprint_score.py", "--method", str(method), "--manifest", "unused", "--routes", "unused",
                                       "--gaps", "G", "--tried", "1", "--replicates", "10", "--output", str(output)])

    score.main()

    # With only one failed route, every size-matched B1 draw must recover it.
    assert json.loads(output.read_text())["rows"]["m"]["chance_B1"] == 1.0
