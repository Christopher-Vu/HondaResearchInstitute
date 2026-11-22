"""view_score.py's partial order (prereg-views.md decision rule): row A ranks above row B only if the paired rank-averaged
interval of A minus B lies above 0. `pairwise` stores each pair once under the row order given, so `ranks_above` has to
read the key both ways; these tests pin that it does, and that the order is the same whichever way the rows are listed."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/research/experiments/f2d-unpooled/view_score.py"
PAIRS = 24


def write_pool(tmp_path: Path) -> dict[str, Path]:
    manifest, routes = [], []
    for p in range(PAIRS):
        slice_id, twin_id = str(1000 + p), str(p)
        manifest += [{"id": slice_id, "pair": f"f2d-{p}", "role": "pilot_slice", "practice_gaps": ["F2D_X"],
                      "neighbourhood_of": []},
                     {"id": twin_id, "pair": f"f2d-{p}", "role": "pilot_neighbourhood", "practice_gaps": [],
                      "neighbourhood_of": ["F2D_X"]}]
        routes += [{"id": slice_id, "success": p >= 16}, {"id": twin_id, "success": p < 16}]
    gap = [str(1000 + p) for p in range(16)]
    noise = [str(p) for p in range(16, PAIRS)]
    axes = {"exact": [gap], "half": [gap[:8] + noise[:4]], "noise": [noise]}
    paths = {"manifest": tmp_path / "manifest.json", "routes": tmp_path / "routes.jsonl"}
    paths["manifest"].write_text(json.dumps(manifest))
    paths["routes"].write_text("".join(json.dumps(r) + "\n" for r in routes))
    for name, rows in axes.items():
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(json.dumps({"method": name, "axes": [{"name": f"a{i}", "rollouts": a}
                                                                     for i, a in enumerate(rows)]}))
    return paths


def score(paths: dict[str, Path], order: list[str], output: Path) -> dict:
    rows = [arg for name in order for arg in ("--row", name, f"sim={paths[name]}")]
    subprocess.run([sys.executable, str(SCRIPT), "--manifest", str(paths["manifest"]), "--model", "sim",
                    str(paths["routes"]), "--gaps", "sim:F2D_X", *rows, "--primary-rival", "noise",
                    "--replicates", "300", "--label", "test", "--output", str(output)],
                   check=True, capture_output=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    return json.loads(output.read_text())


def above_from_intervals(report: dict) -> dict[str, list[str]]:
    above = {n: [] for n in report["rows"]}
    for key, value in report["pairwise"].items():
        a, b = key.split(" - ")
        low, high = value["rabm"]["interval"]
        if low > 0:
            above[a].append(b)
        if high < 0:
            above[b].append(a)
    return {n: sorted(v) for n, v in above.items()}


def test_ranks_above_reads_both_key_orders(tmp_path):
    paths = write_pool(tmp_path)
    forward = score(paths, ["exact", "half", "noise"], tmp_path / "forward.json")
    backward = score(paths, ["noise", "half", "exact"], tmp_path / "backward.json")
    assert "exact - noise" in forward["pairwise"] and "noise - exact" in backward["pairwise"]
    for report in (forward, backward):
        assert report["ranks_above"] == above_from_intervals(report)
        assert "noise" in report["ranks_above"]["exact"]
        assert report["ranks_above"]["noise"] == []
    assert forward["ranks_above"] == backward["ranks_above"]


def test_pairwise_is_antisymmetric_across_row_orders(tmp_path):
    paths = write_pool(tmp_path)
    forward = score(paths, ["exact", "half", "noise"], tmp_path / "forward.json")
    backward = score(paths, ["noise", "half", "exact"], tmp_path / "backward.json")
    for key, value in forward["pairwise"].items():
        a, b = key.split(" - ")
        other = backward["pairwise"][f"{b} - {a}"]
        for metric in ("rabm", "best"):
            low, high = value[metric]["interval"]
            assert abs(value[metric]["delta"] + other[metric]["delta"]) < 1e-12
            assert abs(low + other[metric]["interval"][1]) < 1e-12 and abs(high + other[metric]["interval"][0]) < 1e-12
