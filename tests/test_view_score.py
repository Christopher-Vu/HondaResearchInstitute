"""The views scorer must keep multi-run caption rows selection-safe."""
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# The scorer needs only this tiny loader contract.  Keeping the test independent
# of scipy lets it run in the repository's lightweight dashboard/test setup.
scoring_run = ModuleType("harness.scoring_run")


def load_pool(manifests, routes):
    manifest = [entry for path in manifests for entry in json.loads(Path(path).read_text())]
    outcome = {str(row["id"]): not row["success"] for path in routes
               for row in map(json.loads, Path(path).read_text().splitlines()) if row.get("success") is not None}
    return manifest, outcome


scoring_run.load_pool = load_pool
sys.modules["harness.scoring_run"] = scoring_run
spec = importlib.util.spec_from_file_location(
    "view_score", ROOT / "docs/research/experiments/f2d-unpooled/view_score.py"
)
view_score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view_score)


def write_method(path, name, axes):
    path.write_text(json.dumps({"method": name, "axes": [{"rollouts": axis} for axis in axes]}))


def test_multi_run_row_scores_the_median_run_in_every_bootstrap_draw(tmp_path, monkeypatch):
    """One unusually good caption run cannot become the reported row by itself."""
    ids = ["r1", "r2", "r3", "r4"]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([
        {"id": route, "pair": f"p{index // 2}", "role": "pilot_slice", "practice_gaps": ["G"]}
        for index, route in enumerate(ids)
    ]))
    routes = tmp_path / "routes.jsonl"
    routes.write_text("\n".join(json.dumps({"id": route, "success": False}) for route in ids) + "\n")

    runs = tmp_path / "caption-runs.json"
    runs.write_text(json.dumps({"runs": [
        {"axes": [ids]},       # one lucky run is a perfect match
        {"axes": [[]]},
        {"axes": [[]]},
    ]}))
    rival = tmp_path / "b3.json"
    write_method(rival, "B3_behaviour", [ids])
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "view_score.py", "--manifest", str(manifest), "--model", "simlingo", str(routes),
        "--gaps", "simlingo:G", "--row", "caption", f"simlingo=runs:{runs}",
        "--row", "B3_behaviour", f"simlingo={rival}", "--primary-rival", "B3_behaviour",
        "--replicates", "20", "--label", "synthetic", "--output", str(output),
    ])

    view_score.main()

    row = json.loads(output.read_text())["rows"]["caption"]
    assert row["runs"] == 3
    assert row["rabm"] == 0.0
    assert row["per_unit_rabm"]["simlingo:G"] == 0.0
