"""j04 keeps tight off-manifold failure modes that pooled whitening and cPCA miss."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j04 = _load("j04_bgmoment")
j02 = _load("j02_cpca")
cache_methods = _load("cache_methods")


def _best(axes: list[dict], group: set[str]) -> float:
    def jaccard(left: set[str], right: set[str]) -> float:
        union = left | right
        return len(left & right) / len(union) if union else 0.0

    return max(jaccard(set(axis["rollouts"]), group) for axis in axes)


def _opposite(seed: int = 1):
    """Two tight groups on opposite sides of a low-variance direction.

    Sixteen driving directions have sd 6, 96 noise directions have sd 1, and
    the signal direction has passing-route sd 0.25. Groups sit at +3 and -3.
    Seed 1 was measured: j04 Jaccard 1 and 1, pooled whitening 0.70 and 0.77,
    spectral-gap cPCA 0.43 and 0.44.
    """
    rng = np.random.default_rng(seed)
    n_pass, n_group = 200, 20
    n = n_pass + 2 * n_group
    x = np.zeros((n, 16 + 96 + 2))
    x[:, :16] = rng.normal(0, 6.0, (n, 16))
    x[:, 16:112] = rng.normal(0, 1.0, (n, 96))
    x[:, 112:] = rng.normal(0, 0.25, (n, 2))
    x[n_pass:n_pass + n_group, 112] = 3.0
    x[n_pass + n_group:, 112] = -3.0
    failing = np.array([False] * n_pass + [True] * (2 * n_group))
    ids = [f"r{i}" for i in range(n)]
    group_a = set(ids[n_pass:n_pass + n_group])
    group_b = set(ids[n_pass + n_group:])
    return x, failing, ids, group_a, group_b


def _scores(features, failing, ids, label: str):
    return cache_methods.axes_from(features, failing, ids, label, "ward", (2, 3, 5), 0)[:10]


def test_fractional_layers_follow_depth() -> None:
    assert j04.fractional_layers(24) == [5, 8, 20]
    assert j04.fractional_layers(6) == [1, 2, 4]
    assert j04.fractional_layers(3) == [0, 1, 2]
    assert j04.fractional_layers(1) == [0]


def test_background_moment_recovers_opposite_groups() -> None:
    x, failing, ids, group_a, group_b = _opposite()
    recovered = _scores(j04.embed_bg_moment(x, failing, dims=8, ridge_frac=0.02, seed=0), failing, ids, "j04")
    pooled = PCA(n_components=32, random_state=0).fit_transform(cache_methods.standardise(x))
    whitened = _scores(cache_methods.standardise(pooled), failing, ids, "m03")
    contrastive, _info = j02.embed_cpca(x, failing, dims=4, seed=0)
    contrastive_axes = _scores(contrastive, failing, ids, "j02")

    assert _best(recovered, group_a) >= 0.95
    assert _best(recovered, group_b) >= 0.95
    assert _best(whitened, group_a) <= 0.85
    assert _best(whitened, group_b) <= 0.85
    assert _best(contrastive_axes, group_a) <= 0.60
    assert _best(contrastive_axes, group_b) <= 0.60


def test_cli_recovers_the_same_groups_and_names_no_gap(tmp_path, monkeypatch) -> None:
    x, failing, ids, group_a, group_b = _opposite()
    frames = np.zeros((len(ids), 3, 24, x.shape[1]), dtype=np.float64)
    frames[:, 1, 0, :] = x
    meta = np.array([json.dumps({"success": not bool(flag), "failure_step": None, "n_steps": 1,
                                 "infractions": {}}) for flag in failing])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array(ids), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", ["j04_bgmoment.py", str(cache), "--layer", "0", "--output", str(out)])
    j04.main()
    text = out.read_text()
    payload = json.loads(text)
    assert payload["method"].startswith("j04")
    assert payload["settings"]["layer"] == [0]
    assert len(payload["axes"]) <= 10
    assert "PedestriansOnRoad" not in text
    assert _best(payload["axes"], group_a) >= 0.95
    assert _best(payload["axes"], group_b) >= 0.95
