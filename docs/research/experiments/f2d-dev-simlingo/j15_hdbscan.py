#!/usr/bin/env python3
"""j15: HDBSCAN condensed-tree clusters on j05 residuals, ranked by stability.

j05 subtracts each failure's nearest passing routes, then cuts a Ward tree.
Ward puts every failure in a cluster. j15 keeps those residuals and lets
points fall out of a cluster, which is what the condensed tree is for.

Features match j05. The site is driving_queries and the summary is the
approach window. Layers default to fractions 5/23, 8/23 and 20/23 of the
tensor depth. Only failing rows are clustered, in cache order. Passing rows
of the residual are dropped.

Core distance is the Euclidean distance to the min_samples-th nearest point,
counting the point itself. min_samples=5 is therefore the 4th nearest other
point. Mutual reachability of a pair is the max of the two core distances and
the Euclidean distance. A dense Prim tree is built on that matrix. Edges are
sorted by weight, and equal weights keep Prim's order. The single-linkage
dendrogram labels merge i as node n+i. The two children stay in the order the
edge was stored.

Condensing follows Campello, Moulavi and Sander (2013), the same walk as the
hdbscan library. Lambda is 1/distance, and infinite when the distance is 0.
From the root, a split whose two children both have at least min_cluster_size
points births both as clusters. One large child keeps the parent's label and
the small child's points fall out. Two small children fall out entirely.
Cluster ids are assigned breadth-first from the root. The root's birth lambda
is 0. Its id is n, the number of failing routes.

Stability of a cluster is the excess of mass. Each point that falls out of it
directly contributes lambda_out minus the cluster's birth lambda. Each child
cluster contributes its size times the gap from the parent's birth to the
child's birth.

Every non-root cluster is an axis. Members are the points under it at birth.
Axes are ranked by stability descending, then by larger membership, then by
lower cluster id. The first 10 are written.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j15_hdbscan.py CACHE \
        --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

MIN_SAMPLES = 5
MIN_CLUSTER_SIZE = 5
AXIS_LIMIT = 10


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j04 = _load("j04_bgmoment")
j05 = _load("j05_knnresid")
embed_knn_residual = j05.embed_knn_residual
resolve_layers = j05.resolve_layers
layer_matrix = j05.layer_matrix
SUMMARY = j04.SUMMARY


def pairwise_euclidean(points: np.ndarray) -> np.ndarray:
    """Dense Euclidean distances. The diagonal is exactly zero."""
    data = np.asarray(points, dtype=np.float64)
    square = np.einsum("ij,ij->i", data, data)
    gram = data @ data.T
    squared = square[:, None] + square[None, :] - 2.0 * gram
    np.maximum(squared, 0.0, out=squared)
    np.fill_diagonal(squared, 0.0)
    return np.sqrt(squared)


def core_distances(points: np.ndarray, min_samples: int, distances: np.ndarray | None = None) -> np.ndarray:
    """Distance to the min_samples-th neighbour, counting the point itself.

    The nearest neighbour is the point, at distance 0. min_samples=5 is the
    4th nearest other point. If min_samples exceeds the number of points, the
    farthest neighbour is used.
    """
    if int(min_samples) < 1:
        raise ValueError("min_samples must be positive")
    if distances is None:
        distances = pairwise_euclidean(points)
    n = int(distances.shape[0])
    if n == 0:
        return np.zeros(0, dtype=np.float64)
    kth = min(int(min_samples), n) - 1
    return np.partition(distances, kth, axis=1)[:, kth]


def mutual_reachability(distances: np.ndarray, core: np.ndarray) -> np.ndarray:
    """max(core[a], core[b], d(a, b)), with a zero diagonal."""
    reached = np.maximum(distances, core[:, None])
    np.maximum(reached, core[None, :], out=reached)
    np.fill_diagonal(reached, 0.0)
    return reached


def prim_mst(distances: np.ndarray) -> list[tuple[int, int, float]]:
    """Dense Prim. Each edge is (parent, new node, weight), in the order added.

    The tree starts at point 0. Ties while choosing the next node keep the
    smaller index. An equal update keeps the parent already recorded.
    """
    dist = np.asarray(distances, dtype=np.float64)
    n = int(dist.shape[0])
    if n < 2:
        return []
    in_tree = np.zeros(n, dtype=bool)
    best = dist[0].copy()
    parent = np.zeros(n, dtype=np.intp)
    in_tree[0] = True
    edges: list[tuple[int, int, float]] = []
    for _ in range(n - 1):
        outside = np.where(in_tree, np.inf, best)
        node = int(np.argmin(outside))
        edges.append((int(parent[node]), node, float(best[node])))
        in_tree[node] = True
        row = dist[node]
        better = (~in_tree) & (row < best)
        parent[better] = node
        best[better] = row[better]
    return edges


def sort_mst(edges: list[tuple[int, int, float]]) -> list[tuple[int, int, float]]:
    """Ascending weight. Equal weights keep the Prim order."""
    if not edges:
        return []
    weight = np.array([edge[2] for edge in edges], dtype=np.float64)
    born = np.arange(len(edges))
    order = np.lexsort((born, weight))
    return [edges[int(index)] for index in order]


def linkage_from_mst(edges: list[tuple[int, int, float]], n: int) -> np.ndarray:
    """Single linkage. Merge i creates node n+i. Children stay in edge order.

    Returns the scipy layout: child, child, distance, size. One row per merge.
    """
    parent = np.full(2 * n - 1, -1, dtype=np.intp)
    size = np.ones(2 * n - 1, dtype=np.intp)
    size[n:] = 0
    next_label = n

    def find(node: int) -> int:
        root = int(node)
        while parent[root] != -1:
            root = int(parent[root])
        cursor = int(node)
        while parent[cursor] != -1:
            nxt = int(parent[cursor])
            parent[cursor] = root
            cursor = nxt
        return root

    link = np.zeros((n - 1, 4), dtype=np.float64)
    for index, (left, right, weight) in enumerate(edges):
        left_root = find(left)
        right_root = find(right)
        link[index, 0] = left_root
        link[index, 1] = right_root
        link[index, 2] = weight
        link[index, 3] = size[left_root] + size[right_root]
        parent[left_root] = next_label
        parent[right_root] = next_label
        size[next_label] = size[left_root] + size[right_root]
        next_label += 1
    return link


def _bfs_nodes(hierarchy: np.ndarray, root: int, n_samples: int) -> list[int]:
    """Breadth-first node ids. hierarchy[i] is the node n_samples + i."""
    level = [int(root)]
    order: list[int] = []
    while level:
        order.extend(level)
        children: list[int] = []
        for node in level:
            if node < n_samples:
                continue
            row = hierarchy[node - n_samples]
            children.append(int(row[0]))
            children.append(int(row[1]))
        level = children
    return order


def condense_tree(hierarchy: np.ndarray, min_cluster_size: int) -> list[tuple[int, int, float, int]]:
    """Parent, child, lambda, child size. The hdbscan condense walk.

    The root label is n. A child cluster receives the next id when it is
    visited, left child then right child, parents before children.
    """
    if int(min_cluster_size) < 2:
        raise ValueError("min_cluster_size must be at least 2")
    n_merges = int(hierarchy.shape[0])
    if n_merges < 1:
        return []
    n_samples = n_merges + 1
    root = 2 * n_merges
    next_label = n_samples + 1
    relabel = np.empty(root + 1, dtype=np.intp)
    relabel[root] = n_samples
    ignore = np.zeros(root + 1, dtype=bool)
    condensed: list[tuple[int, int, float, int]] = []

    def fall_out(subtree: int, parent_label: int, lambda_value: float) -> None:
        for sub_node in _bfs_nodes(hierarchy, subtree, n_samples):
            if sub_node < n_samples:
                condensed.append((parent_label, sub_node, lambda_value, 1))
            ignore[sub_node] = True

    for node in _bfs_nodes(hierarchy, root, n_samples):
        if ignore[node] or node < n_samples:
            continue
        row = hierarchy[node - n_samples]
        left = int(row[0])
        right = int(row[1])
        distance = float(row[2])
        lambda_value = 1.0 / distance if distance > 0.0 else float(np.inf)
        left_count = int(hierarchy[left - n_samples, 3]) if left >= n_samples else 1
        right_count = int(hierarchy[right - n_samples, 3]) if right >= n_samples else 1
        parent_label = int(relabel[node])
        if left_count >= min_cluster_size and right_count >= min_cluster_size:
            relabel[left] = next_label
            next_label += 1
            condensed.append((parent_label, int(relabel[left]), lambda_value, left_count))
            relabel[right] = next_label
            next_label += 1
            condensed.append((parent_label, int(relabel[right]), lambda_value, right_count))
        elif left_count < min_cluster_size and right_count < min_cluster_size:
            fall_out(left, parent_label, lambda_value)
            fall_out(right, parent_label, lambda_value)
        elif left_count < min_cluster_size:
            relabel[right] = parent_label
            fall_out(left, parent_label, lambda_value)
        else:
            relabel[left] = parent_label
            fall_out(right, parent_label, lambda_value)
    return condensed


def _births_and_stability(condensed: list[tuple[int, int, float, int]]) -> dict[int, float]:
    """Excess of mass. The root, the smallest parent id, is born at lambda 0."""
    if not condensed:
        return {}
    root = min(parent for parent, _child, _lam, _size in condensed)
    largest = root
    for parent, child, _lam, _size in condensed:
        largest = max(largest, parent, child)
    births = np.full(largest + 1, np.nan, dtype=np.float64)
    for _parent, child, lam, _size in condensed:
        births[child] = lam
    births[root] = 0.0
    stability = {root: 0.0}
    for parent, _child, lam, size in condensed:
        stability[parent] = stability.get(parent, 0.0) + (lam - births[parent]) * size
    return {cluster: float(value) for cluster, value in stability.items()}


def _members(condensed: list[tuple[int, int, float, int]], n_samples: int) -> dict[int, list[int]]:
    """Points under each cluster at birth, walking the condensed edges."""
    children: dict[int, list[int]] = {}
    for parent, child, _lam, _size in condensed:
        children.setdefault(parent, []).append(child)
    cache: dict[int, list[int]] = {}

    def walk(node: int) -> list[int]:
        saved = cache.get(node)
        if saved is not None:
            return saved
        if node < n_samples:
            return [node]
        points: list[int] = []
        for child in children.get(node, []):
            if child < n_samples:
                points.append(child)
            else:
                points.extend(walk(child))
        cache[node] = points
        return points

    return {cluster: walk(cluster) for cluster in children}


def _rank_key(record: dict) -> tuple[float, int, int]:
    """Stability descending, then larger membership, then lower cluster id."""
    return (-float(record["stability"]), -len(record["members"]), int(record["id"]))


def hdbscan_clusters(points: np.ndarray, min_samples: int = MIN_SAMPLES,
                     min_cluster_size: int = MIN_CLUSTER_SIZE) -> list[dict]:
    """Non-root condensed clusters, ranked.

    Each record has id, stability, and members (indices into `points`, the
    points under the cluster when it was born). Rank is stability descending,
    then larger membership, then lower cluster id.
    """
    data = np.asarray(points, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError(f"j15 expected a point-by-feature matrix, got shape {data.shape}")
    n = int(data.shape[0])
    if n < 2:
        return []
    distances = pairwise_euclidean(data)
    core = core_distances(data, min_samples, distances)
    edges = sort_mst(prim_mst(mutual_reachability(distances, core)))
    condensed = condense_tree(linkage_from_mst(edges, n), min_cluster_size)
    stability = _births_and_stability(condensed)
    members = _members(condensed, n)
    root = n
    records = []
    for cluster, pts in members.items():
        if cluster == root:
            continue
        records.append({"id": int(cluster), "stability": float(stability[cluster]), "members": pts})
    records.sort(key=_rank_key)
    return records


def axes_from_clusters(clusters: list[dict], ids: list[str], name: str, limit: int = AXIS_LIMIT) -> list[dict]:
    """First `limit` clusters as j05-style axes. Rollouts are sorted route ids."""
    axes = []
    for record in clusters[:limit]:
        axes.append({
            "name": f"{name} cluster {record['id']} stab {record['stability']:.4g}",
            "rollouts": sorted(ids[index] for index in record["members"]),
        })
    return axes


def _json_number(value: float):
    number = float(value)
    if np.isnan(number):
        return None
    if np.isposinf(number):
        return "inf"
    if np.isneginf(number):
        return "-inf"
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    parser.add_argument("--summary", choices=tuple(SUMMARY), default="window")
    parser.add_argument("--pre-dims", type=int, default=j05.PRE_DIMS,
                        help="unwhitened PCA width on all routes; neighbour distances are Euclidean in that space")
    parser.add_argument("--k", type=int, default=j05.K,
                        help="passing neighbours subtracted from each failing route; clamped to how many pass")
    parser.add_argument("--min-samples", type=int, default=MIN_SAMPLES,
                        help="neighbours counted for the core distance, including the point itself")
    parser.add_argument("--min-cluster-size", type=int, default=MIN_CLUSTER_SIZE)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        if args.site not in cache.files:
            raise SystemExit(f"j15: cache has no site {args.site}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = cache["meta"]
        failing = np.array([not json.loads(item)["success"] for item in meta])
        block = cache[args.site][:, SUMMARY[args.summary]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = resolve_layers(n_layers, args.layer)
        residual = embed_knn_residual(
            layer_matrix(cache, args.site, layers, args.summary), failing,
            pre_dims=args.pre_dims, k=args.k, seed=args.seed)
        points = np.asarray(residual[failing], dtype=np.float64)
        fail_ids = [ids[index] for index in np.flatnonzero(failing)]
    name = f"j15-{args.site}-L{'+'.join(map(str, layers))}-{args.summary}"
    clusters = hdbscan_clusters(points, min_samples=args.min_samples, min_cluster_size=args.min_cluster_size)
    axes = axes_from_clusters(clusters, fail_ids, name)
    payload = {
        "method": name,
        "settings": {
            "cache": str(args.cache),
            "site": args.site,
            "layer": layers,
            "summary": args.summary,
            "pre_dims": args.pre_dims,
            "k": args.k,
            "min_samples": args.min_samples,
            "min_cluster_size": args.min_cluster_size,
            "seed": args.seed,
        },
        "axes": axes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({
        "method": name,
        "layer": layers,
        "n_clusters": len(clusters),
        "axes": [len(axis["rollouts"]) for axis in axes],
        "stabilities": [_json_number(record["stability"]) for record in clusters[:AXIS_LIMIT]],
    }))


if __name__ == "__main__":
    main()
