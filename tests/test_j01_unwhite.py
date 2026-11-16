"""j01 keeps PCA eigenvalue scale. Column-standardising first hides two planted groups."""
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


cache_methods = _load("cache_methods")
j01 = _load("j01_unwhite")


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def _best(axes: list[dict], group: set[str]) -> float:
    return max(_jaccard(set(axis["rollouts"]), group) for axis in axes)


def _planted():
    """Seed 2. Column 0 holds two tight groups; the other 255 columns are noise."""
    n_pass, n_a, n_b = 200, 20, 20
    rng = np.random.default_rng(2)
    x = rng.normal(0, 1.0, (n_pass + n_a + n_b, 256))
    x[:n_pass, 0] = rng.normal(0, 0.5, n_pass)
    x[n_pass:n_pass + n_a, 0] = 4.0
    x[n_pass + n_a:, 0] = -4.0
    failing = np.array([False] * n_pass + [True] * (n_a + n_b))
    ids = [f"r{i}" for i in range(n_pass + n_a + n_b)]
    group_a = {f"r{i}" for i in range(n_pass, n_pass + n_a)}
    group_b = {f"r{i}" for i in range(n_pass + n_a, n_pass + n_a + n_b)}
    return x, failing, ids, group_a, group_b


def test_unwhitened_scores_recover_groups_column_standardising_hides() -> None:
    x, failing, ids, group_a, group_b = _planted()
    # Column 0 has variance about 2.9 and the noise columns have variance 1, so the
    # leading score's std is only about 1.34 times the 32nd. A 10x gap cannot happen
    # on this generator. What hides the groups is column-standardising before PCA.
    whitened = cache_methods.standardise(
        PCA(n_components=32, random_state=0).fit_transform(cache_methods.standardise(x))
    )
    column_then_pca = PCA(n_components=32, random_state=0).fit_transform(cache_methods.standardise(x))
    unwhitened = j01.embed_unwhitened(x, 32, seed=0)
    cuts = (2, 3, 5)
    axes_u = cache_methods.axes_from(unwhitened, failing, ids, "j01", "ward", cuts)[:10]
    axes_w = cache_methods.axes_from(whitened, failing, ids, "whitened", "ward", cuts)[:10]
    axes_c = cache_methods.axes_from(column_then_pca, failing, ids, "column", "ward", cuts)[:10]

    best_u_a, best_u_b = _best(axes_u, group_a), _best(axes_u, group_b)
    best_w_a, best_w_b = _best(axes_w, group_a), _best(axes_w, group_b)
    best_c_a, best_c_b = _best(axes_c, group_a), _best(axes_c, group_b)
    ratio_u = float(unwhitened.std(0)[0] / unwhitened.std(0)[-1])
    ratio_w = float(whitened.std(0)[0] / whitened.std(0)[-1])

    assert best_u_a >= 0.95 and best_u_b >= 0.95
    assert best_w_a <= 0.55 and best_w_b <= 0.55
    assert best_c_a <= 0.55 and best_c_b <= 0.55
    assert ratio_u > 1.2, ratio_u
    assert ratio_w < 1.05, ratio_w


def test_cli_recovers_the_planted_groups(tmp_path, monkeypatch) -> None:
    x, failing, ids, group_a, group_b = _planted()
    frames = np.zeros((len(ids), 3, 1, x.shape[1]), dtype=np.float64)
    frames[:, 1, 0, :] = x
    meta = np.array([json.dumps({"success": not bool(flag), "failure_step": None, "n_steps": 1,
                                 "infractions": {}}) for flag in failing])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array(ids), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", ["j01_unwhite.py", str(cache), "--layer", "0", "--output", str(out)])
    j01.main()
    payload = json.loads(out.read_text())
    assert payload["method"].startswith("j01")
    assert len(payload["axes"]) <= 10
    assert _best(payload["axes"], group_a) >= 0.95
    assert _best(payload["axes"], group_b) >= 0.95


def test_default_layers_name_depth_six(tmp_path, monkeypatch) -> None:
    """No --layer on a 6-layer tensor. Fractions 5/23, 8/23, 20/23 land on 1, 2 and 4."""
    j02 = _load("j02_cpca")
    n = 8
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 6, 8))
    meta = np.array([json.dumps({"success": i >= 3}) for i in range(n)])
    cache = tmp_path / "cache.npz"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    for module, script in ((j01, "j01_unwhite.py"), (j02, "j02_cpca.py")):
        out = tmp_path / f"{script}.json"
        monkeypatch.setattr(sys, "argv", [script, str(cache), "--output", str(out)])
        module.main()
        payload = json.loads(out.read_text())
        assert "L1+2+4" in payload["method"], payload["method"]
