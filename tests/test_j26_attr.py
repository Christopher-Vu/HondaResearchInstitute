"""j26 reads only frame and step arrays plus pass/fail, ignores label fields, reruns identically, removes a planted
position direction, and groups failing routes by what the probe uses rather than by their raw activations."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.metrics import adjusted_rand_score

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
FRAME_KEYS = ("route_id", "meta", "layers", "site", "frames", "n_frames")
CACHE_KEYS = ("route_id", "step")

spec = importlib.util.spec_from_file_location("j26_attr", SPRINT_DIR / "j26_attr.py")
j26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j26)


def _save(tmp: Path, name: str, meta_extra: dict | None = None, n: int = 60, t_len: int = 20, width: int = 40) -> tuple:
    rng = np.random.default_rng(0)
    failing = np.arange(n) % 3 == 0
    frames = rng.normal(size=(n, t_len, width))
    frames[failing, :, 0] += 2.0
    n_steps = 5 * (t_len + 10 + np.arange(n) % 7)
    step = np.full((n, int(n_steps.max() // 5)), np.nan)
    meta = []
    for i in range(n):
        step[i, :n_steps[i] // 5] = 5 * np.arange(1, n_steps[i] // 5 + 1)
        failure = int(5 * (t_len + 1)) if failing[i] else None
        meta.append(json.dumps({"success": not failing[i], "failure_step": failure, **(meta_extra or {})}))
    ids = np.array([f"r{i:03d}" for i in range(n)])
    frames_path, cache_path = tmp / f"{name}-frames.npz", tmp / f"{name}-cache.npz"
    np.savez(frames_path, route_id=ids, meta=np.array(meta), layers=np.array([5, 8, 10, 20]),
             site=np.array("driving_queries"), frames=np.repeat(frames.astype(np.float16)[:, None], 4, axis=1),
             n_frames=np.full(n, t_len, dtype=np.int64))
    np.savez(cache_path, route_id=ids, step=step.astype(np.float32))
    return frames_path, cache_path


def _run(frames: Path, cache: Path, out: Path, monkeypatch) -> dict:
    monkeypatch.setattr(sys, "argv", ["j26", str(frames), str(cache), "--output", str(out)])
    j26.main()
    return json.loads(out.read_text())


def test_cli_reads_only_frame_and_step_keys_ignores_labels_and_is_deterministic(tmp_path, monkeypatch):
    plain = _save(tmp_path, "plain")
    labelled = _save(tmp_path, "labelled", {"scenario": "Wall", "category": "F2D_Wall", "town": "T13"})
    with np.load(plain[0]) as frames, np.load(plain[1]) as cache:
        assert set(frames.files) == set(FRAME_KEYS) and set(cache.files) == set(CACHE_KEYS)
    first = _run(*plain, tmp_path / "a.json", monkeypatch)
    again = _run(*plain, tmp_path / "b.json", monkeypatch)
    with_labels = _run(*labelled, tmp_path / "c.json", monkeypatch)
    assert first["axes"] == again["axes"] == with_labels["axes"]
    assert 0 < len(first["axes"]) <= 10


def test_window_steps_follow_the_cache_pool_rule():
    steps = np.r_[5.0 * np.arange(1, 11), np.nan, np.nan]
    assert np.array_equal(j26.window_steps(steps, 33, 3), [20.0, 25.0, 30.0])
    assert np.array_equal(j26.window_steps(steps, None, 2), [45.0, 50.0])


def test_position_removal_leaves_no_linear_position_within_either_outcome():
    rng = np.random.default_rng(1)
    n = 400
    outcome = np.arange(n) % 2 == 0
    positions = rng.normal(size=(n, 2))
    z = rng.normal(size=(n, 8))
    z[:, 3] += 3 * positions[:, 0]
    z[outcome, 5] += 3 * positions[outcome, 1]
    removed, history = j26.position_directions(z, positions, outcome)
    assert history[0][0] > 0.5 and max(history[-1]) < j26.TOLERANCE
    residual = z @ j26.complement(removed, 8)
    assert residual.shape[1] == 8 - removed.shape[1]
    for rows, j in ((~outcome, 0), (outcome, 0), (outcome, 1)):
        assert j26.cross_fitted_r2(residual[rows], positions[rows, j]) < j26.TOLERANCE


def test_attributions_group_failing_routes_by_reason_where_raw_activations_split_on_a_nuisance():
    """Failing routes fail along input 0 or input 1; input 2 is a large two-valued nuisance unrelated to failing."""
    rng = np.random.default_rng(2)
    n = 300
    x = np.column_stack([rng.normal(size=(n, 2)), rng.normal(scale=3, size=(n, 4))])
    failing = np.arange(n) % 3 != 0
    reason_b = failing & (np.arange(n) % 2 == 0)
    x[failing & ~reason_b, 0] += 4
    x[reason_b, 1] += 4
    x[:, 2] += np.where(rng.random(n) < 0.5, -8, 8)
    attribution, _ = j26.cross_fitted_attributions(x, failing, 0)
    agreement = lambda f: adjusted_rand_score(reason_b[failing], fcluster(linkage(f[failing], "ward"), 2, "maxclust"))
    assert agreement(x) < 0.1
    assert agreement(attribution) > 0.8
    assert agreement(attribution) > agreement(j26.cache_methods.standardise(attribution)) + 0.3
