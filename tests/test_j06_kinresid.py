"""j06 removes a linear behaviour prediction, then clusters like j01."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from harness.scoring import jaccard

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
# One coordinate each. Large next to unit noise, small next to B @ W (W scale 4).
SHIFT = 12.0


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j06 = _load("j06_kinresid")
j01 = _load("j01_unwhite")


def _best(axes: list[dict], group: set[str]) -> float:
    return max(jaccard(set(axis["rollouts"]), group) for axis in axes)


def _design(behaviour: np.ndarray) -> np.ndarray:
    """[1, B] as specified: standardised columns, std 0 set to 0, intercept prepended."""
    block = np.asarray(behaviour, dtype=np.float64)
    centred = block - block.mean(axis=0)
    sd = block.std(axis=0)
    scaled = np.zeros_like(centred)
    keep = sd > 0
    scaled[:, keep] = centred[:, keep] / sd[keep]
    return np.column_stack([np.ones(len(block)), scaled])


def test_residual_is_orthogonal_to_behaviour() -> None:
    rng = np.random.default_rng(1)
    n, d, p = 60, 24, 5
    behaviour = rng.normal(size=(n, p))
    behaviour[:, 2] = 4.0
    weights = rng.normal(size=(p, d))
    activations = behaviour @ weights + rng.normal(scale=0.1, size=(n, d))
    residual = j06.residualise(activations, behaviour)
    design = _design(behaviour)
    gram = design.T @ residual
    scale = float(np.linalg.norm(design) * np.linalg.norm(activations))
    assert scale > 0
    assert np.max(np.abs(gram)) < 1e-8 * scale
    assert np.all(design[:, 3] == 0.0)


def _speed_plant(seed: int = 0):
    """400 routes, 120 failing, d=256. Two speed clusters, two weaker failure groups.

    Failing routes 0:60 sit near speed +8 and 60:120 near speed -8. Each planted
    group takes every fourth route from both clusters (15 + 15), so membership
    is not a linear function of the behaviour block.
    """
    rng = np.random.default_rng(seed)
    n, n_fail, d, p = 400, 120, 256, 4
    n_pass = n - n_fail
    speed = rng.normal(0, 1, n)
    speed[n_pass:n_pass + 60] = rng.normal(8.0, 0.4, 60)
    speed[n_pass + 60:] = rng.normal(-8.0, 0.4, 60)
    behaviour = np.column_stack([
        speed,
        speed + rng.normal(0, 0.3, n),
        0.7 * speed + rng.normal(0, 0.5, n),
        speed + rng.normal(0, 0.8, n),
    ])
    weights = rng.normal(0, 4.0, size=(p, d))
    activations = behaviour @ weights + rng.normal(0, 1.0, size=(n, d))
    high = np.arange(n_pass, n_pass + 60)
    low = np.arange(n_pass + 60, n)
    group_a_idx = np.concatenate([high[0::4], low[0::4]])
    group_b_idx = np.concatenate([high[1::4], low[1::4]])
    activations[group_a_idx, 0] += SHIFT
    activations[group_b_idx, 1] += SHIFT
    failing = np.zeros(n, dtype=bool)
    failing[n_pass:] = True
    ids = [f"r{i}" for i in range(n)]
    group_a = {ids[i] for i in group_a_idx}
    group_b = {ids[i] for i in group_b_idx}
    return activations, behaviour, failing, ids, group_a, group_b


def test_planted_groups_survive_speed_and_j01_is_printed(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, group_a, group_b = _speed_plant()
    assert len(group_a) == 30 and len(group_b) == 30 and not group_a & group_b
    frames = np.zeros((len(ids), 3, 1, activations.shape[1]), dtype=np.float64)
    frames[:, 1, 0, :] = activations
    meta = np.array([json.dumps({"success": not bool(flag)}) for flag in failing])
    cache = tmp_path / "cache.npz"
    np.savez(cache, route_id=np.array(ids), meta=meta, driving_queries=frames,
             kin=np.asarray(behaviour, dtype=np.float64))
    j06_out = tmp_path / "j06.json"
    j01_out = tmp_path / "j01.json"
    monkeypatch.setattr(sys, "argv", [
        "j06_kinresid.py", str(cache), "--layer", "0", "--dims", "32", "--seed", "0",
        "--output", str(j06_out),
    ])
    j06.main()
    monkeypatch.setattr(sys, "argv", [
        "j01_unwhite.py", str(cache), "--layer", "0", "--dims", "32", "--seed", "0",
        "--output", str(j01_out),
    ])
    j01.main()
    payload = json.loads(j06_out.read_text())
    plain = json.loads(j01_out.read_text())
    assert payload["settings"]["behaviour"] == "kin"
    assert payload["method"].startswith("j06")
    assert len(payload["axes"]) <= 10
    j01_a, j01_b = _best(plain["axes"], group_a), _best(plain["axes"], group_b)
    j06_a, j06_b = _best(payload["axes"], group_a), _best(payload["axes"], group_b)
    print(f"j01 best Jaccard group_a={j01_a:.10f} group_b={j01_b:.10f}")
    assert j06_a >= 0.8, j06_a
    assert j06_b >= 0.8, j06_b


def test_b3_kinematics_path_writes_json(tmp_path, monkeypatch) -> None:
    n, frames, width = 8, 5, 16
    rng = np.random.default_rng(0)
    speed = np.full((n, frames + 1), np.nan, dtype=np.float64)
    step = np.full((n, frames + 1), np.nan, dtype=np.float64)
    observed = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
    for i in range(n):
        speed[i, :frames] = np.linspace(8.0, 1.0, frames) + 0.05 * i
        step[i, :frames] = observed
    failing = np.array([i >= 3 for i in range(n)])
    meta = np.array([
        json.dumps({"success": not bool(flag), "failure_step": 40 if flag else None})
        for flag in failing
    ])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "j06.json"
    np.savez(
        cache,
        route_id=np.array([f"r{i}" for i in range(n)]),
        meta=meta,
        ego_speed=speed,
        step=step,
        driving_queries=rng.normal(size=(n, 3, 24, width)),
    )
    monkeypatch.setattr(sys, "argv", ["j06_kinresid.py", str(cache), "--output", str(out)])
    j06.main()
    payload = json.loads(out.read_text())
    assert payload["method"].startswith("j06")
    assert payload["settings"]["behaviour"] == "b3_kinematics"
    assert len(payload["axes"]) <= 10
    failing_ids = {f"r{i}" for i in range(n) if failing[i]}
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) <= failing_ids
