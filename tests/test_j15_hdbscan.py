"""j15 builds an HDBSCAN condensed tree on residuals and ranks clusters by stability."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import linkage
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.spatial.distance import squareform

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"


def _load(name: str):
    path = SPRINT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j15 = _load("j15_hdbscan")


def _assert_axes(clusters: list[dict], axes: list[dict], ids: list[str], min_cluster_size: int = 5) -> None:
    assert len(axes) <= 10
    assert len(axes) == min(len(clusters), 10)
    stabilities = [cluster["stability"] for cluster in clusters]
    assert stabilities == sorted(stabilities, reverse=True)
    seen = []
    for cluster, axis in zip(clusters, axes):
        assert len(cluster["members"]) >= min_cluster_size
        assert axis["rollouts"] == sorted(ids[index] for index in cluster["members"])
        assert axis["rollouts"] == sorted(axis["rollouts"])
        assert len(axis["rollouts"]) >= min_cluster_size
        frozen = frozenset(axis["rollouts"])
        assert frozen not in seen
        seen.append(frozen)
        assert axis["name"] == f"j15 cluster {cluster['id']} stab {cluster['stability']:.4g}"


def test_core_distance_counts_the_point_itself() -> None:
    # Six points on a line. The 5th neighbour, counting the point, is the 4th other point.
    points = np.arange(6, dtype=np.float64).reshape(-1, 1)
    core = j15.core_distances(points, 5)
    assert core.tolist() == [4.0, 3.0, 2.0, 2.0, 3.0, 4.0]
    # min_samples=1 is the point itself.
    assert np.all(j15.core_distances(points, 1) == 0.0)
    # Three points, min_samples=2: nearest other point, not the one after it.
    trio = np.array([[0.0], [1.0], [3.0]])
    assert j15.core_distances(trio, 2).tolist() == [1.0, 1.0, 2.0]


def test_two_separated_blobs_are_the_clusters() -> None:
    # Seed 0, scale 0.4, centres 40 apart. This draw has no split that clears
    # min_cluster_size inside either blob, so the condensed tree has two clusters.
    rng = np.random.default_rng(0)
    blob_a = rng.normal(loc=(0.0, 0.0), scale=0.4, size=(20, 2))
    blob_b = rng.normal(loc=(40.0, 0.0), scale=0.4, size=(20, 2))
    points = np.vstack([blob_a, blob_b])
    ids = [f"a{i:02d}" for i in range(20)] + [f"b{i:02d}" for i in range(20)]
    clusters = j15.hdbscan_clusters(points, min_samples=5, min_cluster_size=5)
    axes = j15.axes_from_clusters(clusters, ids, "j15")
    assert len(clusters) == 2
    assert {frozenset(axis["rollouts"]) for axis in axes} == {frozenset(ids[:20]), frozenset(ids[20:])}
    _assert_axes(clusters, axes, ids)


def test_nested_blobs_rank_the_pair_above_its_split() -> None:
    # Far blob at 0, close pair centred 5 apart at 80. Scale 0.8, seed 0.
    # The far gap births the far blob and the pair; the pair then splits.
    rng = np.random.default_rng(0)
    scale = 0.8
    far = rng.normal(loc=(0.0, 0.0), scale=scale, size=(20, 2))
    close_p = rng.normal(loc=(80.0, 0.0), scale=scale, size=(20, 2))
    close_q = rng.normal(loc=(85.0, 0.0), scale=scale, size=(20, 2))
    points = np.vstack([far, close_p, close_q])
    ids = [f"f{i:02d}" for i in range(20)] + [f"p{i:02d}" for i in range(20)] + [f"q{i:02d}" for i in range(20)]
    clusters = j15.hdbscan_clusters(points, min_samples=5, min_cluster_size=5)
    axes = j15.axes_from_clusters(clusters, ids, "j15")
    groups = [set(axis["rollouts"]) for axis in axes]
    far_ids = set(ids[:20])
    pair_ids = set(ids[20:])
    left_ids = set(ids[20:40])
    right_ids = set(ids[40:])
    far_at = groups.index(far_ids)
    pair_at = groups.index(pair_ids)
    left_at = groups.index(left_ids)
    right_at = groups.index(right_ids)
    assert far_at < left_at and far_at < right_at
    assert pair_at < left_at and pair_at < right_at
    _assert_axes(clusters, axes, ids)


def test_axes_are_capped_distinct_and_ranked() -> None:
    rng = np.random.default_rng(0)
    blobs = [rng.normal(loc=(index * 100.0, 0.0), scale=0.2, size=(6, 2)) for index in range(12)]
    points = np.vstack(blobs)
    ids = [f"b{blob}-{point}" for blob in range(12) for point in range(6)]
    clusters = j15.hdbscan_clusters(points, min_samples=5, min_cluster_size=5)
    axes = j15.axes_from_clusters(clusters, ids, "j15")
    assert len(clusters) > 10
    assert len(axes) == 10
    _assert_axes(clusters, axes, ids)


def test_equal_stability_keeps_the_lower_cluster_id() -> None:
    # Two pairs, internal distance 1, gap 9. Both distances are exact in float64.
    # Stabilities match, sizes match, so the smaller condensed id comes first.
    points = np.array([[0.0], [1.0], [10.0], [11.0]])
    clusters = j15.hdbscan_clusters(points, min_samples=2, min_cluster_size=2)
    assert [set(cluster["members"]) for cluster in clusters] == [{0, 1}, {2, 3}]
    assert [cluster["id"] for cluster in clusters] == [5, 6]
    assert clusters[0]["stability"] == clusters[1]["stability"]
    # Larger membership beats a lower id when stability is tied.
    tied = [
        {"stability": 1.0, "members": list(range(5)), "id": 3},
        {"stability": 1.0, "members": list(range(7)), "id": 9},
        {"stability": 2.0, "members": list(range(5)), "id": 8},
        {"stability": 1.0, "members": list(range(7)), "id": 4},
    ]
    assert [record["id"] for record in sorted(tied, key=j15._rank_key)] == [8, 4, 9, 3]


def test_mst_and_linkage_match_scipy() -> None:
    rng = np.random.default_rng(1)
    points = rng.normal(size=(25, 2))
    distances = j15.pairwise_euclidean(points)
    core = j15.core_distances(points, 5, distances)
    reached = j15.mutual_reachability(distances, core)
    edges = j15.prim_mst(reached)
    scipy_weights = np.sort(minimum_spanning_tree(reached).data)
    assert np.allclose(scipy_weights, np.sort([edge[2] for edge in edges]))
    link = j15.linkage_from_mst(j15.sort_mst(edges), len(points))
    scipy_link = linkage(squareform(reached, checks=False), method="single")
    assert np.allclose(link[:, 2], scipy_link[:, 2])
    assert np.array_equal(link[:, 3], scipy_link[:, 3])
    for row, scipy_row in zip(link, scipy_link):
        assert set(row[:2].tolist()) == set(scipy_row[:2].tolist())


def test_cli_records_hdbscan_settings(tmp_path, monkeypatch) -> None:
    n = 40
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 3, 6, 8))
    meta = np.array([json.dumps({"success": index < 24}) for index in range(n)])
    cache = tmp_path / "cache.npz"
    out = tmp_path / "out.json"
    np.savez(cache, route_id=np.array([f"r{i}" for i in range(n)]), meta=meta, driving_queries=frames)
    monkeypatch.setattr(sys, "argv", ["j15_hdbscan.py", str(cache), "--output", str(out)])
    j15.main()
    payload = json.loads(out.read_text())
    assert payload["method"] == "j15-driving_queries-L1+2+4-window"
    assert payload["settings"]["cache"] == str(cache)
    assert payload["settings"]["site"] == "driving_queries"
    assert payload["settings"]["layer"] == [1, 2, 4]
    assert payload["settings"]["summary"] == "window"
    assert payload["settings"]["pre_dims"] == 32
    assert payload["settings"]["k"] == 10
    assert payload["settings"]["min_samples"] == 5
    assert payload["settings"]["min_cluster_size"] == 5
    assert payload["settings"]["seed"] == 0
    failing_ids = {f"r{i}" for i in range(24, n)}
    assert len(payload["axes"]) <= 10
    seen = []
    for axis in payload["axes"]:
        assert axis["rollouts"] == sorted(axis["rollouts"])
        assert set(axis["rollouts"]) <= failing_ids
        assert len(axis["rollouts"]) >= 5
        frozen = frozenset(axis["rollouts"])
        assert frozen not in seen
        seen.append(frozen)
