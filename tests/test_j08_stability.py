"""j08 ranks multi-view Ward candidates by bootstrap clusterwise Jaccard."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from harness.scoring import jaccard

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j08 = _load("j08_stability")


def _plant(seed: int, structured: str):
    """60 routes, 45 failing in three groups of 15. One view holds the groups; the other is noise.

    Group centres sit at the origin, 100 along the first coordinate, and 400 along the second,
    with within-group noise of scale 1. The structured view's Ward cut at k = 3 recovers each
    group exactly. Passing routes stay in the initial noise and are not members of the groups.
    """
    rng = np.random.default_rng(seed)
    n_pass, n_per, width = 15, 15, 8
    n = n_pass + 3 * n_per
    failing = np.zeros(n, dtype=bool)
    failing[n_pass:] = True
    ids = [f"r{i:03d}" for i in range(n)]
    groups = [{ids[i] for i in range(n_pass + g * n_per, n_pass + (g + 1) * n_per)} for g in range(3)]
    behaviour = rng.normal(0.0, 1.0, size=(n, 4))
    activations = rng.normal(0.0, 1.0, size=(n, width))
    if structured == "kin":
        centers = np.array([
            [0.0, 0.0, 0.0, 0.0],
            [100.0, 0.0, 0.0, 0.0],
            [0.0, 400.0, 0.0, 0.0],
        ])
        for group_index in range(3):
            start = n_pass + group_index * n_per
            behaviour[start:start + n_per] = centers[group_index] + rng.normal(0.0, 1.0, size=(n_per, 4))
    else:
        centers = np.zeros((3, width))
        centers[1, 0] = 100.0
        centers[2, 1] = 400.0
        for group_index in range(3):
            start = n_pass + group_index * n_per
            activations[start:start + n_per] = centers[group_index] + rng.normal(0.0, 1.0, size=(n_per, width))
    return activations, behaviour, failing, ids, groups


def _save(path: Path, ids: list[str], activations: np.ndarray, behaviour: np.ndarray, failing: np.ndarray,
          meta_extra: dict | None = None, extra_arrays: dict | None = None) -> None:
    frames = np.zeros((len(ids), 3, 1, activations.shape[1]), dtype=np.float64)
    frames[:, 1, 0, :] = activations
    meta = []
    for flag in failing:
        item = {"success": not bool(flag)}
        if meta_extra:
            item.update(meta_extra)
        meta.append(json.dumps(item))
    payload = {
        "route_id": np.array(ids),
        "meta": np.array(meta),
        "driving_queries": frames,
        "kin": np.asarray(behaviour, dtype=np.float64),
    }
    if extra_arrays:
        payload.update(extra_arrays)
    np.savez(path, **payload)


def _run(monkeypatch, cache: Path, output: Path, extra: list[str] | None = None) -> dict:
    monkeypatch.setattr(sys, "argv", ["j08_stability.py", str(cache), *(extra or []), "--output", str(output)])
    j08.main()
    return json.loads(output.read_text())


def _comparable(payload: dict) -> dict:
    settings = dict(payload["settings"])
    settings.pop("cache", None)
    settings.pop("output", None)
    return {"method": payload["method"], "settings": settings, "axes": payload["axes"]}


def _assert_size_and_dedup(payload: dict, n_fail: int) -> None:
    axes = payload["axes"]
    assert payload["method"].startswith("j08")
    assert 1 <= len(axes) <= 10
    limit = n_fail // 2
    for axis in axes:
        assert {"name", "rollouts", "view", "cut", "size", "stability"} <= set(axis)
        assert axis["size"] == len(axis["rollouts"])
        assert 3 <= axis["size"] <= limit
        assert axis["cut"] in (2, 3, 5)
        assert 0.0 <= axis["stability"] <= 1.0
    for index, first in enumerate(axes):
        for second in axes[index + 1:]:
            overlap = jaccard(set(first["rollouts"]), set(second["rollouts"]))
            assert overlap <= 0.5, overlap


def _assert_groups(payload: dict, groups: list[set[str]], view) -> None:
    top = payload["axes"][:3]
    found = {frozenset(axis["rollouts"]) for axis in top}
    expect = {frozenset(group) for group in groups}
    summary = [
        (axis["view"], axis["cut"], axis["size"], axis["stability"])
        for axis in payload["axes"]
    ]
    assert len(top) == 3, summary
    assert all(axis["view"] == view for axis in top), summary
    assert found == expect, summary
    for group in groups:
        hits = [axis for axis in payload["axes"] if jaccard(set(axis["rollouts"]), group) == 1.0]
        assert hits, summary
        assert all(axis["view"] == view for axis in hits), summary
    others = [axis for axis in payload["axes"] if axis["view"] != view]
    if others:
        assert min(axis["stability"] for axis in top) > max(axis["stability"] for axis in others)


def test_kin_groups_beat_activation_noise(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, groups = _plant(0, "kin")
    cache = tmp_path / "cache.npz"
    _save(cache, ids, activations, behaviour, failing)
    payload = _run(monkeypatch, cache, tmp_path / "j08.json")
    assert payload["settings"]["behaviour"] == "kin"
    assert payload["settings"]["layer"] == [0]
    assert payload["settings"]["views"] == ["kin", 0]
    assert payload["settings"]["subsamples"] == 100
    assert payload["settings"]["frac"] == 0.8
    assert payload["settings"]["seed"] == 0
    _assert_groups(payload, groups, "kin")
    _assert_size_and_dedup(payload, int(failing.sum()))


def test_activation_groups_beat_kin_noise(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, groups = _plant(1, "act")
    cache = tmp_path / "cache.npz"
    _save(cache, ids, activations, behaviour, failing)
    payload = _run(monkeypatch, cache, tmp_path / "j08.json")
    assert payload["settings"]["layer"] == [0]
    _assert_groups(payload, groups, 0)
    _assert_size_and_dedup(payload, int(failing.sum()))


def test_fixed_seed_is_deterministic(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, _groups = _plant(0, "kin")
    cache = tmp_path / "cache.npz"
    _save(cache, ids, activations, behaviour, failing)
    first = _run(monkeypatch, cache, tmp_path / "a.json")
    second = _run(monkeypatch, cache, tmp_path / "b.json")
    assert _comparable(first) == _comparable(second)


def test_size_filter_and_dedup(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, groups = _plant(0, "kin")
    cache = tmp_path / "cache.npz"
    _save(cache, ids, activations, behaviour, failing)
    payload = _run(monkeypatch, cache, tmp_path / "j08.json")
    n_fail = int(failing.sum())
    _assert_size_and_dedup(payload, n_fail)
    merged = groups[0] | groups[1]
    assert len(merged) > n_fail // 2
    for axis in payload["axes"]:
        assert set(axis["rollouts"]) != merged


def test_scenario_fields_are_unread(tmp_path, monkeypatch) -> None:
    activations, behaviour, failing, ids, _groups = _plant(0, "kin")
    rich = tmp_path / "rich.npz"
    plain = tmp_path / "plain.npz"
    extra = {
        "scenario": "follow_lead",
        "category": "vehicle",
        "gap": "none",
        "town": "Town01",
        "failure_step": 40,
        "infractions": {"collision": 1},
    }
    _save(rich, ids, activations, behaviour, failing, meta_extra=extra,
          extra_arrays={"scenario": np.arange(len(ids), dtype=np.float64)})
    _save(plain, ids, activations, behaviour, failing)
    with np.load(rich) as cache:
        rich_meta = json.loads(str(cache["meta"][0]))
    with np.load(plain) as cache:
        plain_meta = json.loads(str(cache["meta"][0]))
    assert "scenario" in rich_meta and "gap" in rich_meta and "category" in rich_meta
    assert set(plain_meta) == {"success"}
    rich_out = _run(monkeypatch, rich, tmp_path / "rich.json")
    plain_out = _run(monkeypatch, plain, tmp_path / "plain.json")
    assert _comparable(rich_out) == _comparable(plain_out)
