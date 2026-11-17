"""Behavioural guarantees for the Fail2Drive discovery-sprint tooling (docs/prd-discovery-sprint.md §4-5)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sprint_score = _load("sprint_score")
cache_pool = _load("cache_pool")


def test_sprint_score_truncates_at_top_10_and_never_uses_rank_11(tmp_path: Path) -> None:
    manifest = [
        {"id": f"s{i}", "pair": f"p{i}", "role": "pilot_slice", "practice_gaps": ["G1"]}
        for i in range(6)
    ] + [
        {"id": f"n{i}", "pair": f"p{i}", "role": "pilot_neighbourhood", "practice_gaps": []}
        for i in range(6)
    ]
    routes = [{"id": f"s{i}", "success": False} for i in range(6)] + [
        {"id": f"n{i}", "success": i >= 2} for i in range(6)
    ]
    manifest_path = tmp_path / "manifest.json"
    routes_path = tmp_path / "routes.jsonl"
    manifest_path.write_text(json.dumps(manifest))
    routes_path.write_text("".join(json.dumps(r) + "\n" for r in routes))

    # First 10 axes are distinct and miss G1; axis 11 is the exact G1 failing set.
    axes = [{"name": f"junk-{k}", "rollouts": ["n0", f"x{k}"]} for k in range(10)] + [
        {"name": "oracle-at-11", "rollouts": [f"s{i}" for i in range(6)]}
    ]
    method_path = tmp_path / "m.json"
    rival_path = tmp_path / "r.json"
    out_path = tmp_path / "report.json"
    method_path.write_text(json.dumps({"method": "m_test", "axes": axes}))
    rival_path.write_text(json.dumps({"method": "B3_behaviour", "axes": [{"name": "r1", "rollouts": ["s0", "s1", "s2"]}]}))

    res = subprocess.run(
        [
            sys.executable,
            str(SPRINT_DIR / "sprint_score.py"),
            "--method", str(method_path),
            "--rival", f"B3_behaviour={rival_path}",
            "--manifest", str(manifest_path),
            "--routes", str(routes_path),
            "--gaps", "G1",
            "--tried", "1",
            "--replicates", "100",
            "--output", str(out_path),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"},
        check=True,
    )
    assert res.returncode == 0
    report = json.loads(out_path.read_text())
    assert report["rows"]["m_test"]["axes"] == 10
    assert report["rows"]["m_test"]["mean_best"] == 0.0
    assert report["rows"]["B3_behaviour"]["mean_best"] == 0.5
    assert report["rows"]["m_test"]["vs"]["B3_behaviour"]["delta"] == -0.5


def test_a2_repeated_axes_do_not_use_up_the_top_10() -> None:
    repeated = [{"n0"}] * 10 + [{"s0", "s1"}]
    assert sprint_score.distinct(repeated) == [{"n0"}, {"s0", "s1"}]


def test_a2_axes_from_lists_no_group_twice_and_fills_10() -> None:
    cache_methods = _load("cache_methods")
    rng = np.random.default_rng(0)
    centres = rng.normal(size=(4, 5)) * 20
    features = np.vstack([c + rng.normal(size=(15, 5)) for c in centres] + [rng.normal(size=(20, 5))])
    failing = np.r_[np.ones(60, bool), np.zeros(20, bool)]
    ids = [f"r{i}" for i in range(80)]
    axes = cache_methods.axes_from(features, failing, ids, "t", "ward", (2, 3, 5))
    sets = [frozenset(a["rollouts"]) for a in axes]
    assert len(sets) == len(set(sets)) >= 10
    assert all(r.startswith("r") and int(r[1:]) < 60 for s in sets for r in s)


def test_transfer_layer_fraction_gives_back_simlingo_layers_and_maps_shallow_stacks() -> None:
    cache_methods = _load("cache_methods")
    assert cache_methods.depth_layers(24, [l / 23 for l in range(24)]) == list(range(24))
    assert cache_methods.depth_layers(6, [8 / 23, 20 / 23]) == [2, 4]
    assert cache_methods.depth_layers(1, [8 / 23]) == [0]


def test_pooled_heldout_score_weights_model_gap_units_and_resamples_shared_pairs(tmp_path: Path) -> None:
    pooled_score = _load("pooled_score")

    def plan(name: str, method_rollouts: list[str], rival_rollouts: list[str]) -> Path:
        directory = tmp_path / name
        directory.mkdir()
        manifest = [
            {"id": "s1", "pair": "p1", "role": "pilot_slice", "practice_gaps": ["G1"]},
            {"id": "n1", "pair": "p1", "role": "pilot_neighbourhood", "practice_gaps": []},
            {"id": "s2", "pair": "p2", "role": "pilot_slice", "practice_gaps": ["G1"]},
            {"id": "n2", "pair": "p2", "role": "pilot_neighbourhood", "practice_gaps": []},
        ]
        (directory / "manifest.json").write_text(json.dumps(manifest))
        (directory / "routes.jsonl").write_text("".join(json.dumps({"id": route, "success": route.startswith("n")}) + "\n"
                                                   for route in ("s1", "n1", "s2", "n2")))
        (directory / "method.json").write_text(json.dumps({"method": "m23", "axes": [{"rollouts": method_rollouts}]}))
        (directory / "rival.json").write_text(json.dumps({"method": "B3_behaviour", "axes": [{"rollouts": rival_rollouts}]}))
        out = directory / "plan.json"
        out.write_text(json.dumps({"name": name, "manifest": "manifest.json", "routes": "routes.jsonl", "gaps": ["G1"],
                                   "methods": {"m23": "method.json"}, "rivals": {"B3_behaviour": "rival.json"}}))
        return out

    # m23 is perfect on alpha and covers half of beta; B3 covers half in both.  The pooled headline is their mean.
    alpha = plan("alpha", ["s1", "s2"], ["s1"])
    beta = plan("beta", ["s1"], ["s2"])
    report = pooled_score.pooled([pooled_score.load_model(alpha), pooled_score.load_model(beta)], replicates=50, seed=3)

    assert report["models"] == ["alpha", "beta"]
    assert report["weights"] == "each model-gap unit equally; Fail2Drive pairs jointly resampled across models"
    assert report["rows"]["m23"]["mean_best"] == 0.75
    assert report["headline_best_method_vs_best_rival"]["delta"] == 0.25
    assert len(report["headline_best_method_vs_best_rival"]["interval"]) == 2


def test_hungarian_recall_does_not_reuse_one_axis_for_two_identical_gaps() -> None:
    gaps = {"G1": {"1", "2", "3", "4"}, "G2": {"1", "2", "3", "4"}}
    axes = [{"1", "2", "3", "4"}, {"9"}]
    assert sprint_score.recall(axes, gaps) == 0.5


def test_decoy_hit_rate_flags_majority_decoy_axes() -> None:
    decoys = {"D1": {"d1", "d2", "d3"}}
    axes = [{"d1", "d2", "x1"}, {"x1", "x2", "d1"}]
    assert sprint_score.decoy_rate(axes, decoys) == 0.5


def test_cache_pool_salts_order_and_strips_scenario_labels(tmp_path: Path) -> None:
    shards = tmp_path / "shards"
    shards.mkdir()
    # Route ids whose lexicographic order would group scenarios if unsalted.
    specs = [
        ("1001", "PedestriansOnRoad", False, 20),
        ("1002", "PedestriansOnRoad", False, 5),
        ("2001", "BadParking", True, None),
        ("2002", "BadParking", True, None),
    ]
    for rid, scenario, success, col_step in specs:
        sidecar = {
            "route_id": rid,
            "base_id": f"b-{rid}",
            "scenario": scenario,
            "town": "Town12",
            "practice_gaps": [f"F2D_{scenario}"],
            "role": "pilot_slice",
            "success": success,
            "first_collision_step": col_step,
            "infractions": {"collisions_pedestrian": [] if success else ["hit"]},
            "n_steps": 4,
        }
        (shards / f"{rid}.json").write_text(json.dumps(sidecar))
        dq = np.full((4, 2, 8), float(rid), dtype=np.float16)
        vb = np.full((4, 8), float(rid), dtype=np.float16)
        np.savez(
            shards / f"{rid}.npz",
            driving_queries=dq,
            all_tokens=dq,
            vision_bridge=vb,
            step=np.array([0, 10, 20, 30], dtype=np.int32),
            ego_speed=np.array([4.0, 3.0, 2.0, 0.0], dtype=np.float32),
        )

    cache_path = tmp_path / "cache.npz"
    subprocess.run(
        [sys.executable, str(SPRINT_DIR / "cache_pool.py"), str(shards), "--window", "2", "--output", str(cache_path)],
        env={"PYTHONPATH": "src"},
        check=True,
    )
    with np.load(cache_path) as cache:
        ids = cache["route_id"].tolist()
        expected = sorted([s[0] for s in specs], key=cache_pool.order_key)
        assert ids == expected
        for raw_meta in cache["meta"]:
            meta = json.loads(raw_meta)
            assert set(meta).issubset({"success", "failure_step", "n_steps", "infractions"})


def test_cache_methods_and_b3_emit_only_failing_routes_with_zero_variance_columns(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    n = 30
    ids = np.array([f"r{i}" for i in range(n)])
    failing_mask = np.array([i < 12 for i in range(n)])
    meta = np.array([
        json.dumps({
            "success": bool(not failing_mask[i]),
            "failure_step": 30 if failing_mask[i] else None,
            "n_steps": 5,
            "infractions": {"collisions_vehicle": 1 if failing_mask[i] else 0},
        })
        for i in range(n)
    ])
    dq = rng.normal(size=(n, 3, 4, 16)).astype(np.float16)
    dq[:, :, 2, :] = 0.0  # simulate an inactive/zeroed layer (e.g. UniAD stage with no queries)
    speed = np.tile(np.array([5.0, 4.0, 3.0, 2.0, np.nan], dtype=np.float32), (n, 1))
    step = np.tile(np.array([0.0, 10.0, 20.0, 30.0, np.nan], dtype=np.float32), (n, 1))
    cache_path = tmp_path / "cache.npz"
    np.savez(cache_path, route_id=ids, meta=meta, driving_queries=dq, ego_speed=speed, step=step)

    m03_out = tmp_path / "m03.json"
    b3_out = tmp_path / "b3.json"
    pooled_out = tmp_path / "pooled.json"
    subprocess.run(
        [
            sys.executable, str(SPRINT_DIR / "cache_methods.py"), str(cache_path),
            "--method", "m03", "--layer", "1", "2", "--dims", "8", "--output", str(m03_out),
        ],
        env={"PYTHONPATH": "src"},
        check=True,
    )
    subprocess.run(
        [sys.executable, str(SPRINT_DIR / "b3_behaviour.py"), str(cache_path), "--output", str(b3_out)],
        env={"PYTHONPATH": "src"},
        check=True,
    )
    subprocess.run(
        [
            sys.executable, str(SPRINT_DIR / "pool_axes.py"),
            "--name", "pool_test", "--source", str(m03_out), "--source", str(b3_out), "--output", str(pooled_out),
        ],
        env={"PYTHONPATH": "src"},
        check=True,
    )

    failing_ids = {f"r{i}" for i in range(12)}
    for path in (m03_out, b3_out, pooled_out):
        payload = json.loads(path.read_text())
        assert 1 <= len(payload["axes"]) <= 10
        for axis in payload["axes"]:
            members = set(axis["rollouts"])
            assert members and members.issubset(failing_ids)
