"""j18 fits a mixture to every route and lists the most atypical components first."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
SPEC = importlib.util.spec_from_file_location("j18_gmm", SPRINT_DIR / "j18_gmm.py")
j18 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(j18)


def _dense_and_sparse(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dense = rng.normal(scale=0.1, size=(80, 2))
    sparse = rng.normal(scale=2.0, size=(20, 2)) + np.array([30.0, 0.0])
    return np.vstack([dense, sparse])


def test_the_spread_out_component_ranks_first() -> None:
    z = _dense_and_sparse()
    model, bic = j18.fit_mixture(z, [2], seed=0)
    assert set(bic) == {"diag-2", "full-2"}
    labels, order = j18.rank_components(model, z)
    first = order[0][0]
    assert set(np.flatnonzero(labels == first)) == set(range(80, 100))
    assert order[0][1] < order[1][1]


def test_axes_keep_failing_routes_only_and_skip_components_without_one() -> None:
    labels = np.array([0, 0, 1, 1, 2, 2])
    failing = np.array([True, False, False, False, True, True])
    ids = [f"r{i}" for i in range(6)]
    axes = j18.axes_from_components(labels, [(2, -5.0), (1, -3.0), (0, -1.0)], failing, ids, "j18")
    assert [a["rollouts"] for a in axes] == [["r4", "r5"], ["r0"]]


def _write_cache(path: Path, success: list[bool]) -> None:
    rng = np.random.default_rng(0)
    n = len(success)
    np.savez(path, route_id=np.array([f"r{i}" for i in range(n)]),
             meta=np.array([json.dumps({"success": s}) for s in success]),
             driving_queries=rng.normal(size=(n, 3, 10, 6)).astype(np.float16))


def _run(tmp_path: Path, monkeypatch, success: list[bool], tag: str) -> dict:
    cache, out = tmp_path / f"cache-{tag}.npz", tmp_path / f"out-{tag}.json"
    _write_cache(cache, success)
    monkeypatch.setattr(sys, "argv", ["j18_gmm.py", str(cache), "--dims", "3", "--components", "2", "3",
                                      "--output", str(out)])
    j18.main()
    return json.loads(out.read_text())


def test_deterministic_and_the_mixture_never_reads_pass_fail(tmp_path, monkeypatch) -> None:
    first = _run(tmp_path, monkeypatch, [i % 3 != 0 for i in range(40)], "a")
    again = _run(tmp_path, monkeypatch, [i % 3 != 0 for i in range(40)], "b")
    flipped = _run(tmp_path, monkeypatch, [i % 2 != 0 for i in range(40)], "c")
    assert first["axes"] == again["axes"]
    assert first["settings"]["component_order"] == again["settings"]["component_order"]
    order = lambda run: [(c["component"], c["mean_log_density"], c["routes"]) for c in run["settings"]["component_order"]]
    assert order(first) == order(flipped)
    assert first["settings"]["bic"] == flipped["settings"]["bic"]
    failing = {f"r{i}" for i in range(40) if i % 3 == 0}
    assert all(set(a["rollouts"]) <= failing for a in first["axes"])


def test_failure_rate_ranking_puts_the_most_failing_component_first() -> None:
    labels = np.array([0, 0, 0, 0, 1, 1, 2, 2, 2, 2])
    failing = np.array([True, False, False, False, True, True, True, True, False, False])
    order = [(0, -3.0), (1, 5.0), (2, 1.0)]
    ranked = j18.rank_by_failure_rate(labels, order, failing)
    assert [c for c, _ in ranked] == [1, 2, 0]
    assert dict(ranked) == dict(order)
