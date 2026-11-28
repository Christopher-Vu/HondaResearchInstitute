"""Behaviour the final UniAD read relies on (docs/prereg-views.md) that no other test pins: the units rule at the
counts the table states, repeated --restrict (47f26b4), each model's median over its own runs (N1), reported-only
rows outside the partial order, the per-draw selection dominating its members, and uniad_read.sh refusing a cutoff
on a final read."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "docs/research/experiments/f2d-unpooled"
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value))
    return path


def write_routes(path: Path, failed: dict[str, bool]) -> Path:
    path.write_text("".join(json.dumps({"id": r, "success": not f}) + "\n" for r, f in failed.items()))
    return path


def units_rule(tmp: Path, counts: dict[str, tuple[int, int]], total: int = 30) -> dict:
    manifest, failed = [], {}
    for t, (slice_fail, twin_fail) in counts.items():
        for i in range(total):
            s, w = f"{t}-s{i}", f"{t}-t{i}"
            manifest += [{"id": s, "pair": f"{t}-{i}", "role": "pilot_slice", "practice_gaps": [t], "neighbourhood_of": []},
                         {"id": w, "pair": f"{t}-{i}", "role": "pilot_neighbourhood", "practice_gaps": [],
                          "neighbourhood_of": [t]}]
            failed |= {s: i < slice_fail, w: i < twin_fail}
    out = subprocess.run([sys.executable, str(E / "units_rule.py"), str(write_json(tmp / "m.json", manifest)),
                          str(write_routes(tmp / "r.jsonl", failed)), "--model", "uniad"],
                         check=True, env=ENV, capture_output=True, text=True).stdout.splitlines()
    return {"types": {(d := json.loads(line))["type"]: d for line in out[:-1]}, "units": out[-1].split()}


def test_units_rule_at_the_final_reads_stated_counts(tmp_path):
    report = units_rule(tmp_path, {"F2D_PedestriansOnRoad": (16, 0), "F2D_RightConstruction": (11, 6),
                                   "F2D_FullyBlocked": (30, 21), "F2D_Wall": (30, 1)})
    assert report["units"] == ["uniad:F2D_PedestriansOnRoad", "uniad:F2D_RightConstruction", "uniad:F2D_Wall"]
    assert report["types"]["F2D_FullyBlocked"]["ratio"] == 1.43
    assert report["types"]["F2D_PedestriansOnRoad"]["ratio"] is None


def test_units_rule_needs_five_failing_slices_even_with_clean_twins(tmp_path):
    assert units_rule(tmp_path, {"F2D_A": (4, 0), "F2D_B": (5, 0)})["units"] == ["uniad:F2D_B"]


@pytest.mark.xfail(strict=True, reason="rs >= 1.5 * rt in floating point: 9/30 vs 6/30 is exactly 1.5x but rejected")
def test_units_rule_admits_exactly_one_and_a_half_times(tmp_path):
    assert units_rule(tmp_path, {"F2D_A": (9, 6)})["units"] == ["uniad:F2D_A"]


PAIRS = 8
SLICES = [f"s{i}" for i in range(PAIRS)]


def two_model_pool(tmp: Path) -> dict[str, Path]:
    manifest = []
    for i in range(PAIRS):
        manifest += [{"id": f"s{i}", "pair": f"f2d-{i}", "role": "pilot_slice", "practice_gaps": ["F2D_X"],
                      "neighbourhood_of": []},
                     {"id": f"t{i}", "pair": f"f2d-{i}", "role": "pilot_neighbourhood", "practice_gaps": [],
                      "neighbourhood_of": ["F2D_X"]}]
    failed = {f"s{i}": True for i in range(PAIRS)} | {f"t{i}": i == 0 for i in range(PAIRS)}
    return {"manifest": write_json(tmp / "manifest.json", manifest),
            "a": write_routes(tmp / "a.jsonl", failed), "b": write_routes(tmp / "b.jsonl", failed),
            "bad": write_json(tmp / "bad.json", {"method": "bad", "axes": [{"rollouts": ["t0"]}]})}


def view_score(tmp: Path, args: list[str], name: str) -> dict:
    out = tmp / f"{name}.json"
    subprocess.run([sys.executable, str(E / "view_score.py"), *args, "--replicates", "200", "--label", name,
                    "--output", str(out)], check=True, env=ENV, capture_output=True)
    return json.loads(out.read_text())


def test_repeated_restrict_applies_every_restriction(tmp_path):
    p = two_model_pool(tmp_path)
    (tmp_path / "keep-a.txt").write_text("\n".join(SLICES[4:] + [f"t{i}" for i in range(PAIRS)]))
    (tmp_path / "keep-b.txt").write_text("\n".join(SLICES[2:] + [f"t{i}" for i in range(PAIRS)]))
    report = view_score(tmp_path, ["--manifest", str(p["manifest"]), "--model", "a", str(p["a"]), "--model", "b",
                                   str(p["b"]), "--restrict", f"a={tmp_path / 'keep-a.txt'}",
                                   "--restrict", f"b={tmp_path / 'keep-b.txt'}", "--gaps", "a:F2D_X", "b:F2D_X",
                                   "--row", "bad", f"a={p['bad']}", f"b={p['bad']}", "--primary-rival", "bad"], "restrict")
    assert report["units"] == {"a:F2D_X": 4, "b:F2D_X": 6}
    assert report["failing"] == {"a": 5, "b": 7}


def test_multi_run_row_takes_each_models_median_over_its_own_runs(tmp_path):
    p = two_model_pool(tmp_path)
    good, bad = [SLICES], [["t0"]]
    runs = {"caption": [{"run": 0, "axes": {"a": good, "b": good}}, {"run": 1, "axes": {"a": good, "b": bad}},
                        {"run": 2, "axes": {"a": bad, "b": good}}]}
    for m in ("a", "b"):
        write_json(tmp_path / f"runs-{m}.json", {"caption": [{"run": r["run"], "axes": r["axes"][m]} for r in runs["caption"]]})
    report = view_score(tmp_path, ["--manifest", str(p["manifest"]), "--model", "a", str(p["a"]), "--model", "b",
                                   str(p["b"]), "--gaps", "a:F2D_X", "b:F2D_X",
                                   "--row", "caption", f"a=runs:{tmp_path / 'runs-a.json'}",
                                   f"b=runs:{tmp_path / 'runs-b.json'}",
                                   "--row", "bad", f"a={p['bad']}", f"b={p['bad']}", "--primary-rival", "bad"], "n1")
    # per model: a scores 1, 1, 0 and b 1, 0, 1, so both medians are 1; pairing run r across models would give 0.5
    assert report["rows"]["caption"]["rabm"] == 1.0
    assert report["rows"]["caption"]["vs_primary"]["rabm"]["interval"] == [1.0, 1.0]


GAP = [str(1000 + p) for p in range(16)]
NOISE = [str(p) for p in range(16, 24)]


def one_model_pool(tmp: Path) -> dict[str, Path]:
    manifest, failed = [], {}
    for p in range(24):
        manifest += [{"id": str(1000 + p), "pair": f"f2d-{p}", "role": "pilot_slice", "practice_gaps": ["F2D_X"],
                      "neighbourhood_of": []},
                     {"id": str(p), "pair": f"f2d-{p}", "role": "pilot_neighbourhood", "practice_gaps": [],
                      "neighbourhood_of": ["F2D_X"]}]
        failed |= {str(1000 + p): p < 16, str(p): p >= 16}
    axes = {"exact": GAP, "half": GAP[:8] + NOISE[:4], "half_b": GAP[8:] + NOISE[4:], "noise": NOISE}
    return {"manifest": write_json(tmp / "manifest.json", manifest), "routes": write_routes(tmp / "r.jsonl", failed),
            **{n: write_json(tmp / f"{n}.json", {"method": n, "axes": [{"rollouts": a}]}) for n, a in axes.items()}}


def one_model_args(p: dict[str, Path], rows: list[str]) -> list[str]:
    return ["--manifest", str(p["manifest"]), "--model", "sim", str(p["routes"]), "--gaps", "sim:F2D_X",
            *[a for n in rows for a in ("--row", n, f"sim={p[n]}")], "--primary-rival", "noise"]


def test_reported_only_rows_are_scored_but_left_out_of_the_order(tmp_path):
    p = one_model_pool(tmp_path)
    report = view_score(tmp_path, one_model_args(p, ["exact", "half", "noise"]) + ["--reported-only", "half"], "ro")
    assert "half" in report["rows"] and "vs_primary" in report["rows"]["half"]
    assert report["ranks_above"] == {"exact": ["noise"], "noise": []}


def test_selection_dominates_each_member_and_quotes_the_point_choice(tmp_path):
    p = one_model_pool(tmp_path)
    report = view_score(tmp_path, one_model_args(p, ["half", "half_b", "noise"]) +
                        ["--select", "best", "half", "half_b", "--select-vs", "noise"], "sel")
    sel = report["selections"]["best"]
    assert 0 < sel["draw_choice_share"]["half"] < 1
    for member in sel["members"]:
        own = report["rows"][member]["vs_primary"]["rabm"]["interval"]
        assert sel["vs_noise"]["interval"][0] >= own[0] - 1e-12 and sel["vs_noise"]["interval"][1] >= own[1] - 1e-12
    assert sel["vs_noise"]["delta"] == report["rows"][sel["point_choice"]]["vs_primary"]["rabm"]["delta"]


def read_script(tmp: Path, mode: str, read: str, cutoff: str | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CUTOFF"} | ({"CUTOFF": cutoff} if cutoff is not None else {})
    return subprocess.run(["bash", str(E / "uniad_read.sh"), mode, read], cwd=tmp, env=env, capture_output=True, text=True)


def test_final_read_refuses_a_cutoff_before_doing_anything(tmp_path):
    refused = read_script(tmp_path, "test", "final", "2026-11-21 09:00 PST")
    assert refused.returncode == 2 and "CUTOFF is for the late interim only" in refused.stdout
    assert list(tmp_path.iterdir()) == []
    for read, cutoff in (("final", None), ("final", ""), ("interim", "2026-11-21 09:00 PST")):
        passed = read_script(tmp_path, "neither", read, cutoff)
        assert passed.returncode == 2 and "MODE is dev or test" in passed.stdout
