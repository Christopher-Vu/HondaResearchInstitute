"""Per-frame cache: salted order, pre-failure right-alignment, layer fractions."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from harness.failure_time import failure_step

REPO = Path(__file__).resolve().parents[1]
SPRINT_DIR = REPO / "docs/research/experiments/f2d-dev-simlingo"
F = 50
WINDOW = 6
FRACTIONS = (5 / 23, 8 / 23, 10 / 23, 20 / 23)
SCENARIOS = ("PedestriansOnRoad", "BadParking", "FullyBlocked")
KEYS = {"route_id", "meta", "layers", "site", "frames", "n_frames", "ego_speed"}


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_pool = _load("cache_pool")
frames_pool = _load("frames_pool")


def _run(script: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SPRINT_DIR / script), *args],
        cwd=REPO,
        env={"PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )


def _strings(array: np.ndarray) -> list[str]:
    return [str(item) for item in np.asarray(array).tolist()]


def _expected_indices(steps: np.ndarray, failed_at: int | None, n_keep: int) -> np.ndarray:
    """The spec's slice: steps < failure, else frame 0; all frames when failure is None."""
    if failed_at is None:
        idx = np.arange(len(steps))
    else:
        idx = np.flatnonzero(np.asarray(steps) < failed_at)
        if len(idx) == 0:
            idx = np.arange(min(1, len(steps)), dtype=np.int64)
    return np.asarray(idx[-n_keep:], dtype=np.int64)


def _fraction_layers(depth: int, fractions=FRACTIONS) -> list[int]:
    last = depth - 1
    return [min(max(int(round(float(frac) * last)), 0), last) for frac in fractions]


def _write_route(directory: Path, route_id: str, *, success, n: int, depth: int, width: int,
                 scenario: str, collision: int | None, rng: np.random.Generator) -> dict:
    steps = np.arange(n, dtype=np.int32) * 5
    speed = steps.astype(np.float32) + np.float32(0.5)
    activations = rng.standard_normal((n, depth, width)).astype(np.float16)
    info = {
        "route_id": route_id,
        "base_id": f"b-{route_id}",
        "scenario": scenario,
        "town": "Town12",
        "route_config": f"RouteScenario_{scenario}_{route_id}",
        "category": scenario,
        "practice_gaps": [f"F2D_{scenario}"],
        "role": "pilot_slice",
        "success": success,
        "first_collision_step": collision,
        "infractions": {"collisions_vehicle": ["hit"]} if success is False else {},
        "n_steps": int(n),
    }
    (directory / f"{route_id}.json").write_text(json.dumps(info))
    np.savez(directory / f"{route_id}.npz", driving_queries=activations, step=steps, ego_speed=speed)
    failed_at = None if success is None else failure_step(info, {"step": steps, "ego_speed": speed})
    return {
        "route_id": route_id,
        "success": success,
        "steps": steps,
        "speed": speed,
        "frames": activations,
        "failed_at": None if failed_at is None else int(failed_at),
    }


def _depth24_specs() -> list[dict]:
    specs = []
    for i in range(12):
        n = 30 + (i * 5) % 51  # 30..80, including both sides of F=50
        if i == 0:
            success, n_before = False, 0
        elif i == 3:
            success, n_before = False, 10
        elif i == 6:
            success, n_before = False, 55
        elif i == 9:
            success, n_before = False, 40
        else:
            success, n_before = True, None
        specs.append({
            "route_id": f"r{i:02d}{SCENARIOS[i % 3]}",
            "scenario": SCENARIOS[i % 3],
            "n": n,
            "success": success,
            "n_before": n_before,
        })
    specs.append({
        "route_id": "skip-me",
        "scenario": "DoNotLeak",
        "n": 4,
        "success": None,
        "n_before": None,
    })
    return specs


def _collision_step(steps: np.ndarray, n_before: int | None, success) -> int | None:
    if success is not False:
        return None
    if n_before == 0:
        return int(steps[0])
    return int(steps[n_before])


@pytest.fixture(scope="module")
def pool(tmp_path_factory):
    root = tmp_path_factory.mktemp("frames-pool")
    shards = root / "shards"
    shards.mkdir()
    rng = np.random.default_rng(0)
    written = []
    for spec in _depth24_specs():
        # Steps are 0, 5, 10, ... so a bug that slices by row index instead of step value fails.
        steps = np.arange(spec["n"], dtype=np.int32) * 5
        collision = _collision_step(steps, spec["n_before"], spec["success"])
        written.append(_write_route(
            shards, spec["route_id"], success=spec["success"], n=spec["n"], depth=24, width=8,
            scenario=spec["scenario"], collision=collision, rng=rng))
    frame_path = root / "frames.npz"
    pool_path = root / "cache.npz"
    framed = _run("frames_pool.py", [str(shards), "--output", str(frame_path)])
    assert framed.returncode == 0, framed.stderr
    pooled = _run("cache_pool.py", [str(shards), "--output", str(pool_path)])
    assert pooled.returncode == 0, pooled.stderr
    included = [row for row in written if row["success"] is not None]
    included.sort(key=lambda row: cache_pool.order_key(row["route_id"]))
    return SimpleNamespace(shards=shards, frame_path=frame_path, pool_path=pool_path, routes=included)


def test_row_order_and_route_id_match_cache_pool(pool) -> None:
    source = (SPRINT_DIR / "frames_pool.py").read_text()
    assert "importlib" in source
    assert "f2d-cache-v1" not in source
    assert frames_pool.SALT == cache_pool.SALT
    assert frames_pool.order_key("abc") == cache_pool.order_key("abc")

    with np.load(pool.frame_path) as framed, np.load(pool.pool_path) as pooled:
        ids = _strings(framed["route_id"])
        assert ids == _strings(pooled["route_id"])
        assert _strings(framed["meta"]) == _strings(pooled["meta"])
    assert ids == [row["route_id"] for row in pool.routes]
    assert ids == sorted(ids, key=cache_pool.order_key)
    assert ids != sorted(ids)
    assert "skip-me" not in ids
    assert len(ids) == 12


def test_failing_route_is_right_aligned_before_the_failure_step(pool) -> None:
    with np.load(pool.frame_path) as framed:
        frames = framed["frames"]
        speeds = framed["ego_speed"]
        counts = framed["n_frames"]
        layers = [int(layer) for layer in framed["layers"].tolist()]
        assert frames.dtype == np.float16
        assert speeds.dtype == np.float32
        assert frames.shape == (len(pool.routes), len(layers), F, 8)
        saw_strict = False
        saw_pad = False
        saw_full = False
        for i, route in enumerate(pool.routes):
            idx = _expected_indices(route["steps"], route["failed_at"], F)
            k = int(len(idx))
            assert int(counts[i]) == k
            assert k <= F
            if k:
                expect = np.stack([route["frames"][idx, layer, :] for layer in layers], axis=0)
                np.testing.assert_array_equal(frames[i, :, -k:, :], expect)
                np.testing.assert_allclose(speeds[i, -k:], route["speed"][idx])
            if k < F:
                assert np.isnan(frames[i, :, : F - k, :]).all()
                assert np.isnan(speeds[i, : F - k]).all()
                saw_pad = True
            else:
                saw_full = True
            if route["failed_at"] is None:
                continue
            pre = np.flatnonzero(route["steps"] < route["failed_at"])
            if len(pre) == 0:
                assert k == 1
                fallback = np.stack([route["frames"][0, layer, :] for layer in layers], axis=0)
                np.testing.assert_array_equal(frames[i, :, -1, :], fallback)
                continue
            saw_strict = True
            last = np.stack([route["frames"][pre[-1], layer, :] for layer in layers], axis=0)
            np.testing.assert_array_equal(frames[i, :, -1, :], last)
            assert int(route["steps"][pre[-1]]) < route["failed_at"]
    assert saw_strict and saw_pad and saw_full


def test_last_six_valid_frames_match_cache_pool_window(pool) -> None:
    assert cache_pool.WINDOW == WINDOW
    eps = float(np.finfo(np.float16).eps)
    with np.load(pool.frame_path) as framed, np.load(pool.pool_path) as pooled:
        frames = framed["frames"]
        counts = framed["n_frames"]
        layers = [int(layer) for layer in framed["layers"].tolist()]
        window = pooled["driving_queries"][:, 1]
        for i in range(len(pool.routes)):
            k = int(counts[i])
            take = min(WINDOW, k)
            assert take >= 1
            for slot, layer in enumerate(layers):
                ours = frames[i, slot, -take:].astype(np.float64).mean(axis=0)
                theirs = window[i, layer].astype(np.float64)
                np.testing.assert_allclose(ours, theirs, rtol=2 * eps, atol=eps)


def test_output_has_only_the_listed_keys(pool) -> None:
    with np.load(pool.frame_path) as framed:
        assert set(framed.files) == KEYS
        assert framed["site"].shape == ()
        assert framed["site"].item() == "driving_queries"
        assert framed["frames"].dtype == np.float16
        assert framed["ego_speed"].dtype == np.float32
        assert np.issubdtype(framed["layers"].dtype, np.integer)
        assert np.issubdtype(framed["n_frames"].dtype, np.integer)
        meta_blob = "\n".join(_strings(framed["meta"]))
        for raw in _strings(framed["meta"]):
            assert set(json.loads(raw)) == {"success", "failure_step", "n_steps", "infractions"}
        assert "Town12" not in meta_blob
        assert "RouteScenario" not in meta_blob
        assert "practice_gaps" not in meta_blob
        assert "pilot_slice" not in meta_blob


def test_layer_fractions_at_depth_24_and_in_range_at_depth_6(pool, tmp_path: Path) -> None:
    assert _fraction_layers(24) == [5, 8, 10, 20]
    assert frames_pool.layer_indices(24) == [5, 8, 10, 20]
    with np.load(pool.frame_path) as framed:
        assert [int(layer) for layer in framed["layers"].tolist()] == [5, 8, 10, 20]

    expected6 = _fraction_layers(6)
    assert expected6 == [1, 2, 2, 4]
    assert all(0 <= layer < 6 for layer in expected6)
    assert frames_pool.layer_indices(6) == expected6

    shards = tmp_path / "shards"
    shards.mkdir()
    rng = np.random.default_rng(1)
    for i, success in enumerate((False, True)):
        steps = np.arange(10, dtype=np.int32) * 5
        collision = int(steps[4]) if success is False else None
        _write_route(shards, f"d6-{i}", success=success, n=10, depth=6, width=4,
                     scenario=SCENARIOS[i], collision=collision, rng=rng)
    out = tmp_path / "frames.npz"
    res = _run("frames_pool.py", [str(shards), "--output", str(out)])
    assert res.returncode == 0, res.stderr
    with np.load(out) as framed:
        got = [int(layer) for layer in framed["layers"].tolist()]
        assert got == expected6
        assert all(0 <= layer < 6 for layer in got)
        assert framed["frames"].shape[1] == len(got)

    chosen = tmp_path / "chosen.npz"
    res = _run("frames_pool.py", [str(shards), "--output", str(chosen), "--layer", "0", "4"])
    assert res.returncode == 0, res.stderr
    with np.load(chosen) as framed:
        assert [int(layer) for layer in framed["layers"].tolist()] == [0, 4]

    missing = tmp_path / "missing.npz"
    res = _run("frames_pool.py", [str(shards), "--output", str(missing), "--layer", "8"])
    assert res.returncode != 0
    assert "outside" in res.stderr
    assert not missing.exists()
