"""j10 clusters where frames sit inside a shared HMM state.

j09 and a window mean both miss a shift that cancels across two regimes.
The Fisher score of the emission means keeps it. The plant is synthetic.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

import numpy as np
from scipy.stats import spearmanr

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"

# 0.9 times the per-frame noise std along the planted basis direction.
# At 0.5 the whitened score is lost among the other coordinates. At 1.25 the
# HMM starts to spend a state on the shift and j09 recovers the groups.
D_RATIO = 0.9


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_j09_tests():
    path = Path(__file__).with_name("test_j09_hmm.py")
    spec = importlib.util.spec_from_file_location("j09_order_plant", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load("cache_methods")
j01 = _load("j01_unwhite")
j09 = _load("j09_hmm")
j10 = _load("j10_hmmfisher")
j09_tests = _load_j09_tests()


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def _best(axes: list[dict], group: set[str]) -> float:
    return max(_jaccard(set(axis["rollouts"]), group) for axis in axes)


def _save_cache(path: Path, frames: np.ndarray, n_frames: np.ndarray, failing: np.ndarray,
                ids: list[str], meta_for, layers: tuple[int, ...] = (5, 8, 10, 20),
                site: str = "driving_queries") -> None:
    """frames is (routes, F, width), right-aligned. Stored float16, once per layer."""
    n_routes, t_len, _width = frames.shape
    stored = np.repeat(np.asarray(frames, dtype=np.float16)[:, None, :, :], len(layers), axis=1)
    meta = [json.dumps(meta_for(index, bool(failing[index]))) for index in range(n_routes)]
    np.savez(
        path,
        route_id=np.array(ids),
        meta=np.array(meta),
        layers=np.asarray(layers, dtype=np.int64),
        site=np.array(site),
        frames=stored,
        n_frames=np.asarray(n_frames, dtype=np.int64),
        ego_speed=np.zeros((n_routes, t_len), dtype=np.float32),
    )


def _full_meta(index: int, failed: bool) -> dict:
    return {
        "success": (not failed),
        "failure_step": 80 if failed else None,
        "n_steps": 120,
        "infractions": {"stop": 1} if failed else {},
        "scenario": f"scenario-{index % 7}",
        "town": f"town-{index % 5}",
        "category": f"category-{index % 3}",
        "route_config": f"config-{index % 4}",
    }


def _fisher_plant(seed: int, d_ratio: float = D_RATIO):
    """600 routes, 30-50 frames, width 128. One shared 2-regime chain.

    Noise eigenvalues are 1/k on a random orthonormal basis, k = 1..128.
    Regime means differ by 4 along basis direction 0. Stay probability is 0.9.
    Of 160 failures, three groups of 40 are shifted inside the regimes and 40
    are not. Group shifts cancel across the two regimes, so the window mean
    does not move, and every route has the same chain, so occupancy does not
    mark the group.
    """
    rng = np.random.default_rng(seed)
    n_routes, width, max_t = 600, 128, 50
    n_fail, group = 160, 40
    basis, _r = np.linalg.qr(rng.normal(size=(width, width)))
    stds = 1.0 / np.sqrt(np.arange(1, width + 1, dtype=np.float64))
    d_dir = {axis: float(d_ratio * stds[axis]) for axis in (2, 3, 4)}
    lengths = rng.integers(30, 51, size=n_routes)
    frames = np.zeros((n_routes, max_t, width), dtype=np.float64)
    for index in range(n_routes):
        t_len = int(lengths[index])
        regimes = np.empty(t_len, dtype=np.int64)
        state = int(rng.integers(0, 2))
        for t in range(t_len):
            regimes[t] = state
            if rng.random() >= 0.9:
                state = 1 - state
        coords = rng.normal(0.0, 1.0, size=(t_len, width)) * stds
        coords[regimes == 1, 0] += 4.0
        if index < group:
            coords[regimes == 0, 2] += d_dir[2]
            coords[regimes == 1, 2] -= d_dir[2]
        elif index < 2 * group:
            coords[regimes == 0, 3] += d_dir[3]
            coords[regimes == 1, 3] -= d_dir[3]
        elif index < 3 * group:
            coords[regimes == 0, 4] -= d_dir[4]
            coords[regimes == 1, 4] += d_dir[4]
        frames[index, max_t - t_len:] = coords @ basis.T
    ids = [f"r{index:04d}" for index in range(n_routes)]
    failing = np.zeros(n_routes, dtype=bool)
    failing[:n_fail] = True
    groups = [set(ids[start:start + group]) for start in (0, group, 2 * group)]
    order = rng.permutation(n_routes)
    frames = frames[order]
    lengths = lengths[order]
    failing = failing[order]
    ids = [ids[index] for index in order]
    return frames, lengths.astype(np.int64), failing, ids, groups, d_dir, stds


_PLANT_CACHE: dict[int, dict] = {}
_MEASURED = Path("/tmp/ar-j10/measured.jsonl")


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _record(kind: str, payload: dict) -> None:
    _MEASURED.parent.mkdir(parents=True, exist_ok=True)
    row = _jsonable({"kind": kind, **payload})
    with _MEASURED.open("a") as handle:
        handle.write(json.dumps(row) + "\n")


def _score_fisher_plant(seed: int, d_ratio: float = D_RATIO) -> dict:
    cached = _PLANT_CACHE.get(seed)
    if cached is not None and cached["d_ratio"] == d_ratio:
        return cached
    started = time.perf_counter()
    frames, n_frames, failing, ids, groups, d_dir, stds = _fisher_plant(seed, d_ratio)
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "plant.npz"
        _save_cache(cache, frames, n_frames, failing, ids, _full_meta)
        result = j10.evaluate(cache)
    assert [len(seq) for seq in result["sequences"]] == [int(n) for n in result["n_frames"]]
    axes10 = result["axes"]
    feat09 = j09.embed_failing(result["sequences"], result["failing"], result["model"])
    axes09 = cache_methods.axes_from(
        feat09, result["failing"], result["ids"], "j09", "ward", (2, 3, 5), seed=0
    )[:10]
    means = np.stack([
        result["block"][index, result["block"].shape[1] - int(result["n_frames"][index]):].mean(axis=0)
        for index in range(result["block"].shape[0])
    ])
    scores = j01.embed_unwhitened(means, 16, seed=0)
    axes_mean = cache_methods.axes_from(
        scores, result["failing"], result["ids"], "mean", "ward", (2, 3, 5), seed=0
    )[:10]
    fail_at = np.flatnonzero(result["failing"])
    norms = np.linalg.norm(result["features"][fail_at], axis=1)
    rho = float(spearmanr(norms, result["n_frames"][fail_at]).correlation)
    row = {
        "d_ratio": d_ratio,
        "d_dir": d_dir,
        "stds": {axis: float(stds[axis]) for axis in (0, 2, 3, 4)},
        "seed": seed,
        "j10": [_best(axes10, group) for group in groups],
        "j09": [_best(axes09, group) for group in groups],
        "mean": [_best(axes_mean, group) for group in groups],
        "rho": rho,
        "S": int(result["chosen"]),
        "bic": {str(state): float(value) for state, value in result["bics"].items()},
        "loglik": {str(state): float(value) for state, value in result["logliks"].items()},
        "method": result["method"],
        "seconds": time.perf_counter() - started,
        "n_axes": len(axes10),
    }
    row["j10_mean"] = float(np.mean(row["j10"]))
    row["j09_mean"] = float(np.mean(row["j09"]))
    row["base_mean"] = float(np.mean(row["mean"]))
    _PLANT_CACHE[seed] = row
    return row


def _hand_fisher(sequences, failing, model) -> np.ndarray:
    """The definition, as a loop, independent of embed_failing's reductions."""
    means = np.asarray(model["means"], dtype=np.float64)
    variances = np.asarray(model["variances"], dtype=np.float64)
    n_states, dim = means.shape
    gammas = []
    sum_gamma = np.zeros(n_states)
    total = 0
    for seq in sequences:
        _ll, gamma, _xi = j09.forward_backward(
            seq, model["startprob"], model["transmat"], means, variances
        )
        gammas.append(gamma)
        sum_gamma += gamma.sum(axis=0)
        total += len(seq)
    w = sum_gamma / total
    features = np.zeros((len(sequences), n_states * dim))
    for index, (seq, gamma) in enumerate(zip(sequences, gammas)):
        if not failing[index]:
            continue
        blocks = []
        for state in range(n_states):
            acc = np.zeros(dim)
            scale = np.sqrt(variances[state])
            for t in range(len(seq)):
                step = np.zeros(dim)
                live = scale > 0.0
                step[live] = (seq[t, live] - means[state, live]) / scale[live]
                acc += gamma[t, state] * step
            if w[state] > 0.0:
                acc = acc / (len(seq) * np.sqrt(w[state]))
            else:
                acc = np.zeros(dim)
            blocks.append(acc)
        features[index] = np.concatenate(blocks)
    return features


def test_score_matches_definition() -> None:
    rng = np.random.default_rng(0)
    sequences = [
        rng.normal(size=(5, 2)),
        rng.normal(size=(5, 2)),
        rng.normal(size=(1, 2)),
        rng.normal(size=(4, 2)),
    ]
    failing = np.array([True, False, True, True])
    model = {
        "startprob": np.array([0.55, 0.45]),
        "transmat": np.array([[0.8, 0.2], [0.35, 0.65]]),
        "means": np.array([[0.0, 0.2], [1.4, -0.7]]),
        "variances": np.array([[0.4, 0.9], [0.3, 0.5]]),
    }
    got = j10.embed_failing(sequences, failing, model)
    expected = _hand_fisher(sequences, failing, model)
    assert np.allclose(got, expected, atol=1e-8, rtol=1e-6)
    assert np.all(got[1] == 0.0)


def test_fisher_groups_where_occupancy_and_means_fail() -> None:
    rows = [_score_fisher_plant(seed) for seed in (0, 1, 2)]
    print("seed j10_A j10_B j10_C j10_mean j09_A j09_B j09_C j09_mean mean_A mean_B mean_C mean_mean rho S seconds")
    for row in rows:
        print(
            f"{row['seed']} "
            + " ".join(f"{value:.4f}" for value in row["j10"])
            + f" {row['j10_mean']:.4f} "
            + " ".join(f"{value:.4f}" for value in row["j09"])
            + f" {row['j09_mean']:.4f} "
            + " ".join(f"{value:.4f}" for value in row["mean"])
            + f" {row['base_mean']:.4f} {row['rho']:.4f} {row['S']} {row['seconds']:.2f}"
        )
        print(f"  d_dir={row['d_dir']} stds={row['stds']} bic={row['bic']}")
        _record("fisher", {key: row[key] for key in (
            "seed", "d_ratio", "d_dir", "stds", "j10", "j09", "mean",
            "j10_mean", "j09_mean", "base_mean", "rho", "S", "bic", "loglik", "seconds", "method",
        )})
        assert row["method"] == "j10-driving_queries-L8-fisher"
        assert row["n_axes"] <= 10
        assert row["j10_mean"] >= 0.8, row
        assert row["j09_mean"] <= 0.5, row
        assert row["base_mean"] <= 0.5, row


def test_length_norm_is_weakly_related_to_T() -> None:
    for seed in (0, 1, 2):
        row = _score_fisher_plant(seed)
        print(f"seed {seed} spearman ||features|| vs T = {row['rho']:.4f}")
        assert abs(row["rho"]) < 0.3, row


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_order_plant_documents_complementarity(seed, tmp_path, monkeypatch) -> None:
    """j09's order plant. No success threshold: j10 is not an order embedding."""
    frames, failing, ids, group_a, group_b = j09_tests._order_plant(seed)
    n_frames = np.full(frames.shape[0], frames.shape[1], dtype=np.int64)
    cache = tmp_path / f"order-{seed}.npz"
    out = tmp_path / f"order-{seed}.json"
    _save_cache(cache, frames, n_frames, failing, ids, _full_meta)
    monkeypatch.setattr(sys, "argv", ["j10_hmmfisher.py", str(cache), "--output", str(out)])
    started = time.perf_counter()
    j10.main()
    elapsed = time.perf_counter() - started
    payload = json.loads(out.read_text())
    score_a = _best(payload["axes"], group_a)
    score_b = _best(payload["axes"], group_b)
    print(f"seed {seed} j10_A {score_a:.4f} j10_B {score_b:.4f} S {payload['settings']['S']} {elapsed:.2f}s")
    _record("order", {
        "seed": seed,
        "j10_A": score_a,
        "j10_B": score_b,
        "S": payload["settings"]["S"],
        "seconds": elapsed,
    })
    assert payload["method"] == "j10-driving_queries-L8-fisher"
    assert "S" in payload["settings"] and "bic" in payload["settings"] and "loglik" in payload["settings"]
    assert len(payload["axes"]) <= 10


def test_meta_fields_other_than_success_do_not_change_output(tmp_path, monkeypatch) -> None:
    rng = np.random.default_rng(1)
    n_routes, t_len, width = 18, 8, 16
    frames = rng.normal(size=(n_routes, t_len, width))
    n_frames = np.full(n_routes, t_len, dtype=np.int64)
    failing = np.zeros(n_routes, dtype=bool)
    failing[:8] = True
    ids = [f"r{index:04d}" for index in range(n_routes)]

    def _scrambled(index: int, failed: bool) -> dict:
        return {
            "town": f"other-{index % 2}",
            "success": (not failed),
            "scenario": f"other-scenario-{9 - index}",
            "failure_step": 3 if failed else 11,
            "n_steps": 40 + index,
            "category": "swapped",
            "infractions": {"lane": index},
            "route_config": "none",
        }

    def _only_success(index: int, failed: bool) -> dict:
        return {"success": (not failed)}

    payloads = []
    for label, meta_for in (("full", _full_meta), ("stripped", _only_success), ("scrambled", _scrambled)):
        cache = tmp_path / f"{label}.npz"
        out = tmp_path / f"{label}.json"
        _save_cache(cache, frames, n_frames, failing, ids, meta_for)
        monkeypatch.setattr(sys, "argv", ["j10_hmmfisher.py", str(cache), "--output", str(out)])
        j10.main()
        payload = json.loads(out.read_text())
        payload["settings"].pop("cache")
        payload["settings"].pop("output")
        payloads.append(payload)
    assert payloads[0] == payloads[1]
    assert payloads[0] == payloads[2]


def test_cache_format_smoke(tmp_path, monkeypatch) -> None:
    """frames_pool layout: (routes, layers, F, width) float16, NaN-padded, plus ego_speed."""
    rng = np.random.default_rng(2)
    n_routes, t_len, width = 12, 7, 16
    layers = (5, 8, 10, 20)
    frames = rng.normal(size=(n_routes, t_len, width))
    n_frames = np.full(n_routes, t_len, dtype=np.int64)
    n_frames[0] = 4
    n_frames[1] = 6
    failing = np.zeros(n_routes, dtype=bool)
    failing[:8] = True
    ids = [f"r{index:04d}" for index in range(n_routes)]
    cache = tmp_path / "smoke.npz"
    out = tmp_path / "smoke.json"
    _save_cache(cache, frames, n_frames, failing, ids, _full_meta, layers=layers)
    with np.load(cache) as archive:
        stored = np.array(archive["frames"])
        speeds = np.array(archive["ego_speed"])
        meta = np.array(archive["meta"])
    for index, count in enumerate(n_frames):
        if int(count) < t_len:
            stored[index, :, :t_len - int(count), :] = np.nan
            speeds[index, :t_len - int(count)] = np.nan
    np.savez(
        cache,
        route_id=np.array(ids),
        meta=meta,
        layers=np.asarray(layers, dtype=np.int64),
        site=np.array("driving_queries"),
        frames=stored,
        n_frames=n_frames,
        ego_speed=speeds,
    )
    monkeypatch.setattr(sys, "argv", ["j10_hmmfisher.py", str(cache), "--output", str(out)])
    j10.main()
    payload = json.loads(out.read_text())
    assert payload["method"] == "j10-driving_queries-L8-fisher"
    assert set(payload) == {"method", "settings", "axes"}
    assert payload["settings"]["S"] in (4, 6, 8)
    assert set(payload["settings"]["bic"]) == {"4", "6", "8"}
    assert set(payload["settings"]["loglik"]) == {"4", "6", "8"}
    assert payload["axes"]
    assert len(payload["axes"]) <= 10
