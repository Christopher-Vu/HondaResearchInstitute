"""j07 stratifies failing routes by behaviour, then clusters activations within each stratum."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

from harness.scoring import jaccard

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
# Orthogonal to the behaviour map. Above within-stratum noise, below the moving-route
# activation spread, so a top-level cut of every failing route does not isolate it.
SHIFT = 12.0
MOVING_SPREAD = 150.0
_AXIS_NAME = re.compile(r"stratum (\d+) cut (\d+) group (\d+)$")


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j07 = _load("j07_stratify")
j06 = _load("j06_kinresid")
j01 = _load("j01_unwhite")


def _best(axes: list[dict], group: set[str]) -> float:
    return max(jaccard(set(axis["rollouts"]), group) for axis in axes)


def _null_directions(rng: np.random.Generator, basis: np.ndarray, count: int, dim: int) -> np.ndarray:
    """Rows orthogonal to ``basis`` and to each other."""
    span = basis
    rows = []
    for _ in range(count):
        direction = rng.normal(size=dim)
        direction -= span @ (span.T @ direction)
        direction /= np.linalg.norm(direction)
        rows.append(direction)
        span = np.column_stack([span, direction])
    return np.stack(rows, axis=0)


def _speed_plant(seed: int = 0):
    """400 routes, 120 failing, d=256. Two speed clusters; a weak split inside the stopped one.

    Failing routes 280:360 are stopped (speed near 0) and 360:400 are moving (speed near 10).
    The two planted groups are the two halves of the stopped cluster, separated along a
    direction orthogonal to the behaviour map. Moving routes are spread much farther in
    other directions, so that spread, not the planted shift, is what a top-level clustering
    of all failing routes cuts first.
    """
    rng = np.random.default_rng(seed)
    n, n_fail, d, p = 400, 120, 256, 4
    n_pass = n - n_fail
    stopped = np.arange(n_pass, n_pass + 80)
    moving = np.arange(n_pass + 80, n)
    speed = rng.normal(0.0, 1.0, n)
    speed[stopped] = rng.normal(0.0, 0.02, stopped.size)
    speed[moving] = rng.normal(10.0, 0.02, moving.size)
    behaviour = np.column_stack([
        speed,
        speed + rng.normal(0.0, 0.02, n),
        0.7 * speed + rng.normal(0.0, 0.02, n),
        speed + rng.normal(0.0, 0.05, n),
    ])
    weights = rng.normal(0.0, 4.0, size=(p, d))
    basis, _ = np.linalg.qr(weights.T, mode="reduced")
    directions = _null_directions(rng, basis, 5, d)
    plant, hetero = directions[0], directions[1:]
    activations = behaviour @ weights + rng.normal(0.0, 1.0, size=(n, d))
    activations[moving] += rng.normal(0.0, MOVING_SPREAD, size=(moving.size, hetero.shape[0])) @ hetero
    group_a_idx = stopped[:40]
    group_b_idx = stopped[40:]
    activations[group_a_idx] += SHIFT * plant
    activations[group_b_idx] -= SHIFT * plant
    failing = np.zeros(n, dtype=bool)
    failing[n_pass:] = True
    ids = [f"r{i}" for i in range(n)]
    return activations, behaviour, failing, ids, {ids[i] for i in group_a_idx}, {ids[i] for i in group_b_idx}


def _save_kin_cache(path: Path, ids: list[str], activations: np.ndarray, behaviour: np.ndarray,
                    failing: np.ndarray) -> None:
    frames = np.zeros((len(ids), 3, 1, activations.shape[1]), dtype=np.float64)
    frames[:, 1, 0, :] = activations
    meta = np.array([json.dumps({"success": not bool(flag)}) for flag in failing])
    np.savez(path, route_id=np.array(ids), meta=meta, driving_queries=frames,
             kin=np.asarray(behaviour, dtype=np.float64))


def _run(monkeypatch, module, script: str, cache: Path, output: Path, extra: list[str] | None = None) -> dict:
    monkeypatch.setattr(sys, "argv", [script, str(cache), "--layer", "0", "--dims", "32", "--seed", "0",
                                      *(extra or []), "--output", str(output)])
    module.main()
    return json.loads(output.read_text())


def _kin_strata(behaviour: np.ndarray, failing: np.ndarray, ids: list[str], n_strata: int = 2) -> list[set[str]]:
    block = np.asarray(behaviour, dtype=np.float64)
    scale = np.where(block.std(0) > 0, block.std(0), 1.0)
    standardised = (block - block.mean(0)) / scale
    rows = np.flatnonzero(failing)
    labels = fcluster(linkage(standardised[rows], method="ward"), t=n_strata, criterion="maxclust")
    groups = []
    for label in set(labels.tolist()):
        groups.append({ids[rows[j]] for j in np.flatnonzero(labels == label)})
    groups.sort(key=lambda group: (-len(group), min(group)))
    return groups


def _cut_unions(axes: list[dict], cut: int) -> list[set[str]]:
    found: dict[int, set[str]] = {}
    for axis in axes:
        match = _AXIS_NAME.search(axis["name"])
        assert match is not None, axis["name"]
        stratum, this_cut = int(match.group(1)), int(match.group(2))
        if this_cut == cut:
            found.setdefault(stratum, set()).update(axis["rollouts"])
    return [found[index] for index in sorted(found)]


def test_planted_groups_survive_inside_the_stopped_stratum(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, group_a, group_b = _speed_plant()
    assert len(group_a) == 40 and len(group_b) == 40 and not group_a & group_b
    cache = tmp_path / "cache.npz"
    _save_kin_cache(cache, ids, activations, behaviour, failing)
    payload = _run(monkeypatch, j07, "j07_stratify.py", cache, tmp_path / "j07.json")
    plain = _run(monkeypatch, j01, "j01_unwhite.py", cache, tmp_path / "j01.json")
    residual = _run(monkeypatch, j06, "j06_kinresid.py", cache, tmp_path / "j06.json")
    assert payload["settings"]["behaviour"] == "kin"
    assert payload["method"].startswith("j07")
    assert len(payload["axes"]) <= 10
    assert payload["settings"]["strata_sizes"] == [80, 40]
    j07_a, j07_b = _best(payload["axes"], group_a), _best(payload["axes"], group_b)
    j01_a, j01_b = _best(plain["axes"], group_a), _best(plain["axes"], group_b)
    j06_a, j06_b = _best(residual["axes"], group_a), _best(residual["axes"], group_b)
    print(f"j07 best Jaccard group_a={j07_a:.10f} group_b={j07_b:.10f}")
    print(f"j01 best Jaccard group_a={j01_a:.10f} group_b={j01_b:.10f}")
    print(f"j06 best Jaccard group_a={j06_a:.10f} group_b={j06_b:.10f}")
    assert j07_a >= 0.8, j07_a
    assert j07_b >= 0.8, j07_b


def test_strata_match_kin_ward_cut2_on_random_data(tmp_path, monkeypatch) -> None:
    rng = np.random.default_rng(0)
    n, d = 90, 12
    behaviour = rng.normal(size=(n, 4))
    activations = rng.normal(size=(n, d))
    failing = np.zeros(n, dtype=bool)
    failing[30:] = True
    ids = [f"r{i}" for i in range(n)]
    cache = tmp_path / "cache.npz"
    _save_kin_cache(cache, ids, activations, behaviour, failing)
    payload = _run(monkeypatch, j07, "j07_stratify.py", cache, tmp_path / "j07.json")
    expected = _kin_strata(behaviour, failing, ids)
    assert min(len(group) for group in expected) >= 3
    assert payload["settings"]["strata_sizes"] == [len(group) for group in expected]
    assert _cut_unions(payload["axes"], cut=2) == expected
    assert len(payload["axes"]) <= 10


def test_stratum_of_size_two_is_skipped(tmp_path, monkeypatch) -> None:
    rng = np.random.default_rng(1)
    n = 18
    behaviour = rng.normal(0.0, 0.01, size=(n, 4))
    behaviour[:2, 0] = 40.0
    behaviour[2:, 0] = 0.0
    failing = np.zeros(n, dtype=bool)
    failing[:14] = True
    activations = rng.normal(size=(n, 8))
    ids = [f"r{i}" for i in range(n)]
    cache = tmp_path / "cache.npz"
    _save_kin_cache(cache, ids, activations, behaviour, failing)
    payload = _run(monkeypatch, j07, "j07_stratify.py", cache, tmp_path / "j07.json")
    assert payload["settings"]["strata_sizes"] == [12, 2]
    assert len(payload["axes"]) <= 10
    small = {"r0", "r1"}
    for axis in payload["axes"]:
        assert small.isdisjoint(axis["rollouts"])


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
    out = tmp_path / "j07.json"
    np.savez(
        cache,
        route_id=np.array([f"r{i}" for i in range(n)]),
        meta=meta,
        ego_speed=speed,
        step=step,
        driving_queries=rng.normal(size=(n, 3, 24, width)),
    )
    monkeypatch.setattr(sys, "argv", ["j07_stratify.py", str(cache), "--output", str(out)])
    j07.main()
    payload = json.loads(out.read_text())
    assert payload["method"].startswith("j07")
    assert payload["settings"]["behaviour"] == "b3_kinematics"
    assert "strata_sizes" in payload["settings"]
    assert len(payload["axes"]) <= 10
    failing_ids = {f"r{i}" for i in range(n) if failing[i]}
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) <= failing_ids
