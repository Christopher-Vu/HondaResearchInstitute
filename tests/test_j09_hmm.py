"""j09 clusters frame order. A window mean of the same frames cannot."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
ALLOWED_KEYS = {"route_id", "meta", "layers", "site", "frames", "n_frames"}


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load("cache_methods")
j01 = _load("j01_unwhite")
j09 = _load("j09_hmm")


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def _best(axes: list[dict], group: set[str]) -> float:
    return max(_jaccard(set(axis["rollouts"]), group) for axis in axes)


def _save_cache(path: Path, frames: np.ndarray, failing: np.ndarray, ids: list[str],
                layers: tuple[int, ...] = (5, 8, 10, 20), extras: dict | None = None) -> None:
    """Per-frame cache. frames is (routes, F, width) float64; stored float16, repeated per layer."""
    n_routes, t_len, _width = frames.shape
    stored = np.repeat(np.asarray(frames, dtype=np.float16)[:, None, :, :], len(layers), axis=1)
    meta = [
        json.dumps({
            "success": (not bool(flag)),
            "failure_step": 80 if flag else None,
            "n_steps": 120,
            "infractions": {},
        })
        for flag in failing
    ]
    payload = {
        "route_id": np.array(ids),
        "meta": np.array(meta),
        "layers": np.asarray(layers, dtype=np.int64),
        "site": np.array("driving_queries"),
        "frames": stored,
        "n_frames": np.full(n_routes, t_len, dtype=np.int64),
        "ego_speed": np.zeros((n_routes, t_len), dtype=np.float32),
    }
    if extras:
        payload.update(extras)
    np.savez(path, **payload)


def _brute(obs, startprob, transmat, means, variances):
    """Sum over every state path. Independent of j09's recursion."""
    t_len = obs.shape[0]
    n_states = len(startprob)
    log_b = np.empty((t_len, n_states))
    for t in range(t_len):
        for state in range(n_states):
            var = variances[state]
            log_b[t, state] = -0.5 * np.sum(
                np.log(2.0 * np.pi * var) + (obs[t] - means[state]) ** 2 / var
            )
    n_paths = n_states ** t_len
    log_joint = np.empty(n_paths)
    states = np.empty((n_paths, t_len), dtype=np.int64)
    for path in range(n_paths):
        cursor = path
        total = 0.0
        prev = None
        for t in range(t_len):
            state = cursor % n_states
            cursor //= n_states
            states[path, t] = state
            total += log_b[t, state]
            total += np.log(startprob[state] if prev is None else transmat[prev, state])
            prev = state
        log_joint[path] = total
    log_lik = float(logsumexp(log_joint))
    gamma = np.zeros((t_len, n_states))
    xi = np.zeros((max(t_len - 1, 0), n_states, n_states))
    for path in range(n_paths):
        weight = np.exp(log_joint[path] - log_lik)
        for t in range(t_len):
            gamma[t, states[path, t]] += weight
        for t in range(t_len - 1):
            xi[t, states[path, t], states[path, t + 1]] += weight
    return log_lik, gamma, xi


def _known_hmm():
    startprob = np.array([0.5, 0.3, 0.2])
    transmat = np.array([
        [0.6, 0.25, 0.15],
        [0.2, 0.55, 0.25],
        [0.25, 0.25, 0.5],
    ])
    means = np.array([
        [0.0, 0.0],
        [1.5, -0.5],
        [-1.0, 1.2],
    ])
    variances = np.array([
        [0.4, 0.5],
        [0.3, 0.6],
        [0.5, 0.35],
    ])
    return startprob, transmat, means, variances


def _sample_hmm(seed: int, t_len: int):
    startprob, transmat, means, variances = _known_hmm()
    rng = np.random.default_rng(seed)
    n_states = len(startprob)
    states = np.empty(t_len, dtype=int)
    states[0] = rng.choice(n_states, p=startprob)
    for t in range(1, t_len):
        states[t] = rng.choice(n_states, p=transmat[states[t - 1]])
    obs = np.empty((t_len, means.shape[1]))
    for t, state in enumerate(states):
        obs[t] = rng.normal(means[state], np.sqrt(variances[state]))
    return obs, startprob, transmat, means, variances


def test_forward_matches_brute_force_on_a_sampled_hmm() -> None:
    """T=5, 3 states, 2 dims: every path is enumerable. Also a one-frame sequence."""
    for seed in (0, 1, 2):
        obs, startprob, transmat, means, variances = _sample_hmm(seed, 5)
        got_ll, got_gamma, got_xi = j09.forward_backward(obs, startprob, transmat, means, variances)
        brute_ll, brute_gamma, brute_xi = _brute(obs, startprob, transmat, means, variances)
        assert abs(got_ll - brute_ll) < 1e-6, (seed, got_ll, brute_ll)
        assert np.allclose(got_gamma.sum(axis=1), 1.0, atol=1e-8)
        assert np.allclose(got_gamma, brute_gamma, atol=1e-6)
        assert np.allclose(got_xi, brute_xi, atol=1e-6)
    obs, startprob, transmat, means, variances = _sample_hmm(0, 1)
    got_ll, got_gamma, got_xi = j09.forward_backward(obs, startprob, transmat, means, variances)
    brute_ll, brute_gamma, brute_xi = _brute(obs, startprob, transmat, means, variances)
    assert abs(got_ll - brute_ll) < 1e-6
    assert np.allclose(got_gamma.sum(axis=1), 1.0, atol=1e-8)
    assert np.allclose(got_gamma, brute_gamma, atol=1e-6)
    assert got_xi.shape[0] == 0 and brute_xi.shape[0] == 0


def _order_plant(seed: int):
    """600 routes, 50 frames, width 64.

    Regime P then Q versus Q then P. Both use 25 frames of each, so the window
    mean matches. Background routes, including the other 40 failures, visit P
    and Q in a random order with the same 25/25 counts.
    """
    rng = np.random.default_rng(seed)
    n_routes, n_fail, n_a, n_b = 600, 160, 60, 60
    t_len, width = 50, 64
    scale, noise = 8.0, 0.05
    centers = np.zeros((2, width))
    centers[0, 0] = scale
    centers[1, 1] = scale
    blocked = np.array([0] * 25 + [1] * 25)
    frames = np.empty((n_routes, t_len, width))
    for index in range(n_routes):
        if index < n_a:
            order = blocked
        elif index < n_a + n_b:
            order = blocked[::-1]
        else:
            order = rng.permutation(blocked)
        frames[index] = centers[order] + rng.normal(0.0, noise, size=(t_len, width))
    ids = [f"r{index:04d}" for index in range(n_routes)]
    failing = np.zeros(n_routes, dtype=bool)
    failing[:n_fail] = True
    group_a = set(ids[:n_a])
    group_b = set(ids[n_a:n_a + n_b])
    return frames, failing, ids, group_a, group_b


def _mean_baseline(block: np.ndarray, n_frames: np.ndarray, failing: np.ndarray, ids: list[str]):
    """j01-style: mean of the valid frames, RMS, unwhitened PCA, Ward cuts 2/3/5."""
    means = np.stack([
        block[index, block.shape[1] - int(n_frames[index]):].mean(axis=0)
        for index in range(block.shape[0])
    ])
    rms = float(np.sqrt(np.mean(means * means)))
    if rms > 0.0:
        means = means / rms
    scores = j01.embed_unwhitened(means, 32, seed=0)
    return cache_methods.axes_from(scores, failing, ids, "mean", "ward", (2, 3, 5), seed=0)[:10]


def test_order_groups_recovered_when_window_means_match(tmp_path, monkeypatch) -> None:
    rows = []
    for seed in range(5):
        frames, failing, ids, group_a, group_b = _order_plant(seed)
        cache = tmp_path / f"plant-{seed}.npz"
        out = tmp_path / f"plant-{seed}.json"
        _save_cache(cache, frames, failing, ids)
        monkeypatch.setattr(sys, "argv", ["j09_hmm.py", str(cache), "--output", str(out)])
        j09.main()
        payload = json.loads(out.read_text())
        assert payload["method"] == "j09-driving_queries-L8-hmm"
        assert len(payload["axes"]) <= 10
        with np.load(cache) as archive:
            position = int(np.flatnonzero(np.asarray(archive["layers"]) == 8)[0])
            block = np.asarray(archive["frames"][:, position], dtype=np.float64)
            n_frames = np.asarray(archive["n_frames"])
        base_axes = _mean_baseline(block, n_frames, failing, ids)
        score = {
            "seed": seed,
            "j09_A": _best(payload["axes"], group_a),
            "j09_B": _best(payload["axes"], group_b),
            "mean_A": _best(base_axes, group_a),
            "mean_B": _best(base_axes, group_b),
            "S": payload["settings"]["S"],
        }
        rows.append(score)
        assert score["j09_A"] >= 0.8, score
        assert score["j09_B"] >= 0.8, score
        assert score["mean_A"] <= 0.5, score
        assert score["mean_B"] <= 0.5, score
    print("seed j09_A j09_B mean_A mean_B S")
    for score in rows:
        print(
            f"{score['seed']} {score['j09_A']:.4f} {score['j09_B']:.4f} "
            f"{score['mean_A']:.4f} {score['mean_B']:.4f} {score['S']}"
        )


def _four_state_plant(seed: int = 1):
    """100 routes, 30 frames, width 16, drawn from a sticky 4-state diagonal HMM."""
    rng = np.random.default_rng(seed)
    n_routes, t_len, width, n_states = 100, 30, 16, 4
    means = np.zeros((n_states, width))
    for state in range(n_states):
        means[state, state] = 6.0
    variances = np.full(width, 0.25)
    startprob = np.full(n_states, 1.0 / n_states)
    transmat = np.full((n_states, n_states), 0.1 / (n_states - 1))
    np.fill_diagonal(transmat, 0.9)
    frames = np.empty((n_routes, t_len, width))
    for index in range(n_routes):
        state = int(rng.choice(n_states, p=startprob))
        for t in range(t_len):
            frames[index, t] = rng.normal(means[state], np.sqrt(variances))
            state = int(rng.choice(n_states, p=transmat[state]))
    ids = [f"r{index:04d}" for index in range(n_routes)]
    failing = np.zeros(n_routes, dtype=bool)
    failing[:40] = True
    return frames, failing, ids


def test_bic_picks_four_states(tmp_path, monkeypatch) -> None:
    frames, failing, ids = _four_state_plant()
    cache = tmp_path / "bic.npz"
    out = tmp_path / "bic.json"
    _save_cache(cache, frames, failing, ids)
    monkeypatch.setattr(sys, "argv", ["j09_hmm.py", str(cache), "--output", str(out)])
    j09.main()
    payload = json.loads(out.read_text())
    chosen = payload["settings"]["S"]
    bics = payload["settings"]["bic"]
    print(f"bic chosen S={chosen} bic={bics} loglik={payload['settings']['loglik']}")
    assert chosen == 4, payload["settings"]
    assert float(bics["4"]) <= float(bics["6"])
    assert float(bics["4"]) <= float(bics["8"])


class _RecordingNpz:
    def __init__(self, inner, reads: list[str]):
        self._inner = inner
        self._reads = reads

    def __getitem__(self, key):
        self._reads.append(str(key))
        return self._inner[key]

    def __enter__(self):
        self._inner.__enter__()
        return self

    def __exit__(self, *exc):
        return self._inner.__exit__(*exc)

    def close(self):
        self._inner.close()

    def __getattr__(self, name):
        return getattr(self._inner, name)


def test_reads_no_label_keys(tmp_path, monkeypatch) -> None:
    rng = np.random.default_rng(0)
    n_routes, t_len, width = 30, 12, 16
    frames = rng.normal(size=(n_routes, t_len, width))
    failing = np.zeros(n_routes, dtype=bool)
    failing[:12] = True
    ids = [f"r{index:04d}" for index in range(n_routes)]
    cache = tmp_path / "labels.npz"
    out = tmp_path / "labels.json"
    _save_cache(cache, frames, failing, ids, layers=(8,), extras={
        "scenario": np.array(["hidden"] * n_routes),
        "town": np.array(["hidden"] * n_routes),
        "category": np.array(["hidden"] * n_routes),
        "route_config": np.array(["hidden"] * n_routes),
    })
    reads: list[str] = []
    real_load = j09.np.load

    def _load_recording(path, *args, **kwargs):
        return _RecordingNpz(real_load(path, *args, **kwargs), reads)

    monkeypatch.setattr(j09.np, "load", _load_recording)
    monkeypatch.setattr(sys, "argv", ["j09_hmm.py", str(cache), "--output", str(out)])
    j09.main()
    assert set(reads) <= ALLOWED_KEYS, reads
    assert ALLOWED_KEYS <= set(reads)
    assert "ego_speed" not in reads
    assert "scenario" not in reads


def test_missing_layer_exits(tmp_path, monkeypatch) -> None:
    frames = np.zeros((4, 2, 4))
    failing = np.array([True, True, False, False])
    ids = [f"r{index}" for index in range(4)]
    cache = tmp_path / "missing.npz"
    out = tmp_path / "missing.json"
    _save_cache(cache, frames, failing, ids, layers=(5, 10, 20))
    monkeypatch.setattr(sys, "argv", ["j09_hmm.py", str(cache), "--output", str(out)])
    try:
        j09.main()
    except SystemExit as exc:
        assert "layer 8" in str(exc)
    else:
        raise AssertionError("expected SystemExit for the default layer")
    monkeypatch.setattr(sys, "argv", ["j09_hmm.py", str(cache), "--layer", "7", "--output", str(out)])
    try:
        j09.main()
    except SystemExit as exc:
        assert "layer 7" in str(exc)
    else:
        raise AssertionError("expected SystemExit for --layer 7")
