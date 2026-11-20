"""Paired row-vs-row contrasts emitted by the views scorer."""
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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


def test_report_includes_paired_contrasts_for_every_pair_of_rows(tmp_path, monkeypatch):
    ids = ["r1", "r2", "r3", "r4"]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([
        {"id": route, "pair": f"p{index // 2}", "role": "pilot_slice", "practice_gaps": ["G"]}
        for index, route in enumerate(ids)
    ]))
    routes = tmp_path / "routes.jsonl"
    routes.write_text("\n".join(json.dumps({"id": route, "success": False}) for route in ids) + "\n")
    perfect, empty = tmp_path / "perfect.json", tmp_path / "empty.json"
    write_method(perfect, "new", [ids])
    write_method(empty, "other", [[]])
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "view_score.py", "--manifest", str(manifest), "--model", "simlingo", str(routes),
        "--gaps", "simlingo:G", "--row", "new", f"simlingo={perfect}",
        "--row", "other", f"simlingo={empty}", "--replicates", "20",
        "--label", "synthetic", "--output", str(output),
    ])

    view_score.main()

    rows = json.loads(output.read_text())["rows"]
    assert rows["new"]["vs_rows"]["other"]["rabm"]["delta"] == 1.0
    assert rows["other"]["vs_rows"]["new"]["rabm"]["delta"] == -1.0
