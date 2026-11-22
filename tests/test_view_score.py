"""view_score.py's decision-rule outputs (prereg-views.md): ranks_above follows the A - B interval whichever way
the pairwise key is ordered, A - B and B - A intervals are mirror images, and a runs: row scores as the median run."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/research/experiments/f2d-unpooled/view_score.py"
PAIRS = 8
SLICES = [f"s{i}" for i in range(PAIRS)]


def write_pool(tmp: Path) -> dict[str, Path]:
    manifest, routes = [], []
    for i in range(PAIRS):
        manifest.append({"id": f"s{i}", "base_id": f"f2d-{i}", "pair": f"f2d-{i}", "role": "pilot_slice",
                         "practice_gaps": ["F2D_X"], "neighbourhood_of": []})
        manifest.append({"id": f"t{i}", "base_id": f"f2d-{i}", "pair": f"f2d-{i}", "role": "pilot_neighbourhood",
                         "practice_gaps": [], "neighbourhood_of": ["F2D_X"]})
        routes += [{"id": f"s{i}", "success": False}, {"id": f"t{i}", "success": i != 0}]
    paths = {"manifest": tmp / "manifest.json", "routes": tmp / "routes.jsonl"}
    paths["manifest"].write_text(json.dumps(manifest))
    paths["routes"].write_text("".join(json.dumps(r) + "\n" for r in routes))
    axes = {"good": [SLICES], "half": [SLICES[: PAIRS // 2]], "bad": [["t0"]]}
    for name, sets in axes.items():
        paths[name] = tmp / f"{name}.json"
        paths[name].write_text(json.dumps({"method": name, "axes": [{"rollouts": s} for s in sets]}))
    paths["runs"] = tmp / "runs.json"
    paths["runs"].write_text(json.dumps({"c": [{"run": r, "axes": a} for r, a in
                                               enumerate([[SLICES], [["t0"]], [["t0"]]])]}))
    return paths


def run(tmp: Path, paths: dict[str, Path], order: list[str], name: str) -> dict:
    rows = [arg for row in order for arg in ("--row", row, f"m={paths[row] if row != 'runs' else 'runs:' + str(paths[row])}")]
    out = tmp / f"{name}.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    subprocess.run([sys.executable, str(SCRIPT), "--manifest", str(paths["manifest"]), "--model", "m", str(paths["routes"]),
                    "--gaps", "m:F2D_X", *rows, "--primary-rival", "bad", "--replicates", "200", "--label", name,
                    "--output", str(out)], check=True, env=env, capture_output=True)
    return json.loads(out.read_text())


def test_ranks_above_and_antisymmetry_hold_in_both_row_orders(tmp_path):
    paths = write_pool(tmp_path)
    forward = run(tmp_path, paths, ["good", "half", "bad"], "forward")
    reverse = run(tmp_path, paths, ["bad", "half", "good"], "reverse")
    for report in (forward, reverse):
        assert report["ranks_above"] == {"good": ["bad", "half"], "half": ["bad"], "bad": []}
    for key, value in forward["pairwise"].items():
        a, b = key.split(" - ")
        lo, hi = value["rabm"]["interval"]
        mirror_lo, mirror_hi = reverse["pairwise"][f"{b} - {a}"]["rabm"]["interval"]
        assert abs(lo + mirror_hi) < 1e-12 and abs(hi + mirror_lo) < 1e-12


def test_runs_row_scores_as_median_run(tmp_path):
    paths = write_pool(tmp_path)
    report = run(tmp_path, paths, ["good", "runs", "bad"], "runs")
    assert report["rows"]["runs"]["runs"] == 3
    assert report["rows"]["runs"]["rabm"] == 0.0
    assert report["rows"]["good"]["rabm"] == 1.0
