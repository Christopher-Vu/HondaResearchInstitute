"""Layer sweep on the dev pool (PRD 9.2, docs/steps/04-dev-pool-and-layer-sweep.md): which site and
decoder layer to log at scale.

    python -m src.discovery.layer_sweep SHARD_DIR --output OUT.json

SHARD_DIR holds the shards written by adapters/simlingo/export_activations.py. Every (site, layer) pair is
scored on three kinds of metric. Cross-validation is grouped by `base_id`, so variants of one base route
never sit on both sides of a split, and uses the same folds for every pair.

    failure_auroc  Episode-mean activations of every episode with an outcome, standardised, L2 logistic
                   regression (C=1). AUROC of out-of-fold scores, StratifiedGroupKFold with
                   min(5, smallest class, number of base routes) folds. Skipped below 5 episodes per class.
    state probes   Frames of successful episodes only (PRD 9.2), at most 200 per episode. Ridge regression,
                   alpha from RidgeCV over [1, 10, 100, 1000] inside each training fold, out-of-fold R2 for
                   the continuous states; logistic regression, out-of-fold AUROC for red_light and occluded.
                   A state is skipped when too few frames have a value (see the MIN_ constants).
    gap recovery   For each practice gap id listed by any shard, failing episodes only: standardised
                   episode means, PCA to min(20, n-1) dimensions, KMeans for k in 2..8. The score is the
                   best Jaccard between a cluster and the gap's failing episodes (harness.scoring.jaccard),
                   maximised over k; the k that reached it is reported. Skipped below 3 failing episodes.

The vision bridge is one extra pair, scored the same way, when every shard has it.

Selection rule (pre-registered, fixed before any sweep is run):
  1. For each metric, rank all pairs, rank 1 = highest value, tied values share their mean rank.
  2. A family's rank is the mean of its metrics' ranks. The families are failure_auroc, state_probes (all
     state metrics) and practice_gap_recovery (all gaps). Families that were skipped do not exist.
  3. A pair's combined rank is the mean of its family ranks; lower is better. Ties break on site order
     (all_tokens, driving_queries, vision_bridge), then on lower layer.
  4. Choose the two pairs with the best combined rank, then add the pair with the best practice_gap_recovery
     rank if it is not already chosen: two or three pairs.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable

import numpy as np
from scipy.stats import rankdata
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.harness.scoring import jaccard

FRAME_SITES = ("all_tokens", "driving_queries")
VISION_SITE = "vision_bridge"
SITE_ORDER = {site: index for index, site in enumerate((*FRAME_SITES, VISION_SITE))}
CONTINUOUS_STATES = ("ego_speed", "lead_distance", "lead_relative_speed", "pedestrian_distance",
                     "junction_distance", "time_to_junction")
BINARY_STATES = ("red_light", "occluded")
FAMILY_OF_KIND = {"failure_auroc": "failure_auroc", "state_r2": "state_probes",
                  "state_auroc": "state_probes", "gap_jaccard": "practice_gap_recovery"}
GAP_FAMILY = "practice_gap_recovery"

MAX_FOLDS = 5
MIN_CLASS_EPISODES = 5
MAX_FRAMES_PER_EPISODE = 200
MIN_STATE_FRAMES = 100
MIN_STATE_GROUPS = 5
MIN_GAP_FAILURES = 3
PCA_DIMENSIONS = 20
MAX_CLUSTERS = 8
RIDGE_ALPHAS = (1.0, 10.0, 100.0, 1000.0)
SEED = 0

Folds = list[tuple[np.ndarray, np.ndarray]]


class Skip(Exception):
    """A metric that cannot be computed on this data; the message is the recorded reason."""


@dataclass
class Shards:
    meta: list[dict[str, Any]]
    means: dict[str, np.ndarray]
    frames: dict[str, np.ndarray]
    frame_episode: np.ndarray
    frame_states: dict[str, np.ndarray]
    excluded_no_outcome: int

    @cached_property
    def success(self) -> np.ndarray:
        return np.array([meta["success"] for meta in self.meta], dtype=bool)

    @cached_property
    def route_ids(self) -> np.ndarray:
        return np.array([meta["route_id"] for meta in self.meta])

    @cached_property
    def base_ids(self) -> np.ndarray:
        return np.array([meta["base_id"] for meta in self.meta])


@dataclass
class FailurePlan:
    labels: np.ndarray
    folds: Folds


@dataclass
class StatePlan:
    name: str
    kind: str
    rows: np.ndarray
    target: np.ndarray
    folds: Folds


@dataclass
class GapPlan:
    gap_id: str
    failing: np.ndarray
    failing_ids: list[str]
    members: set[str]


@dataclass
class Plans:
    failure: FailurePlan | None = None
    states: list[StatePlan] = field(default_factory=list)
    gaps: list[GapPlan] = field(default_factory=list)


def frame_rows(frame_count: int) -> np.ndarray:
    if frame_count <= MAX_FRAMES_PER_EPISODE:
        return np.arange(frame_count)
    return np.linspace(0, frame_count - 1, MAX_FRAMES_PER_EPISODE).round().astype(int)


def site_names(archive: Any) -> list[str]:
    return [site for site in (*FRAME_SITES, VISION_SITE)
            if site in archive.files and f"{site}_episode_mean" in archive.files]


def load_shards(shard_dir: Path) -> Shards:
    metas, excluded = [], 0
    means: dict[str, list[np.ndarray]] = defaultdict(list)
    frames: dict[str, list[np.ndarray]] = defaultdict(list)
    states: dict[str, list[np.ndarray]] = defaultdict(list)
    frame_episode: list[np.ndarray] = []
    for sidecar in sorted(shard_dir.glob("*.json")):
        meta = json.loads(sidecar.read_text())
        if meta["success"] is None:
            excluded += 1
            continue
        with np.load(sidecar.with_suffix(".npz")) as archive:
            for site in site_names(archive):
                mean_array = archive[f"{site}_episode_mean"]
                means[site].append(mean_array.reshape(-1, mean_array.shape[-1]))
            if meta["success"]:
                read_frames(archive, len(metas), frames, states, frame_episode)
        metas.append(meta)
    if not metas:
        raise ValueError(f"no shard with an outcome in {shard_dir}")
    return Shards(
        meta=metas,
        means={site: np.stack(items) for site, items in means.items() if len(items) == len(metas)},
        frames={site: np.concatenate(items) for site, items in frames.items() if len(items) == len(frame_episode)},
        frame_episode=np.concatenate(frame_episode) if frame_episode else np.zeros(0, dtype=int),
        frame_states={name: np.concatenate(items) for name, items in states.items()},
        excluded_no_outcome=excluded)


def read_frames(archive: Any, episode: int, frames: dict[str, list[np.ndarray]],
                states: dict[str, list[np.ndarray]], frame_episode: list[np.ndarray]) -> None:
    rows = frame_rows(len(archive["step"]))
    for site in site_names(archive):
        values = archive[site][rows]
        frames[site].append(values.reshape(len(rows), -1, values.shape[-1]))
    for name in (*CONTINUOUS_STATES, *BINARY_STATES):
        states[name].append(archive[name][rows] if name in archive.files else np.full(len(rows), np.nan, np.float32))
    frame_episode.append(np.full(len(rows), episode))


def grouped_folds(groups: np.ndarray, labels: np.ndarray, n_splits: int) -> Folds:
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    folds = [(train, test) for train, test in splitter.split(np.zeros(len(labels)), labels, groups)]
    if any(len(np.unique(labels[train])) < 2 for train, _ in folds):
        raise Skip("the grouped split left a training fold with a single class")
    return folds


def plan_failure(shards: Shards, min_class_episodes: int) -> FailurePlan:
    labels = (~shards.success).astype(int)
    counts = np.bincount(labels, minlength=2)
    if counts.min() < min_class_episodes:
        raise Skip(f"{counts[1]} failing and {counts[0]} succeeding episodes; "
                   f"each class needs at least {min_class_episodes}")
    n_splits = min(MAX_FOLDS, int(counts.min()), len(set(shards.base_ids)))
    return FailurePlan(labels, grouped_folds(shards.base_ids, labels, n_splits))


def class_group_counts(groups: np.ndarray, target: np.ndarray) -> list[int]:
    return [len(np.unique(groups[target == value])) for value in (0, 1)]


def plan_state(name: str, shards: Shards) -> StatePlan:
    values = shards.frame_states.get(name, np.zeros(0))
    rows = np.flatnonzero(~np.isnan(values))
    if len(rows) < MIN_STATE_FRAMES:
        raise Skip(f"{len(rows)} success frames have a value; need {MIN_STATE_FRAMES}")
    groups = shards.base_ids[shards.frame_episode[rows]]
    if len(set(groups)) < MIN_STATE_GROUPS:
        raise Skip(f"values come from {len(set(groups))} base routes; need {MIN_STATE_GROUPS}")
    if name not in BINARY_STATES:
        return StatePlan(name, "r2", rows, values[rows], list(GroupKFold(MAX_FOLDS).split(rows, groups=groups)))
    target = (values[rows] > 0.5).astype(int)
    if min(class_group_counts(groups, target)) < MIN_STATE_GROUPS:
        raise Skip(f"a class appears in fewer than {MIN_STATE_GROUPS} base routes")
    return StatePlan(name, "auroc", rows, target, grouped_folds(groups, target, MAX_FOLDS))


def plan_gap(gap_id: str, shards: Shards) -> GapPlan:
    failing = np.flatnonzero(~shards.success)
    ids = [str(shards.route_ids[index]) for index in failing]
    members = {route for route, index in zip(ids, failing) if gap_id in shards.meta[index]["practice_gaps"]}
    if len(members) < MIN_GAP_FAILURES:
        raise Skip(f"{len(members)} failing episodes in the gap; need {MIN_GAP_FAILURES}")
    return GapPlan(gap_id, failing, ids, members)


def build_plans(shards: Shards, min_class_episodes: int) -> tuple[Plans, list[dict[str, str]]]:
    skipped: list[dict[str, str]] = []

    def attempt(metric: str, build: Callable[[], Any]) -> Any:
        try:
            return build()
        except Skip as reason:
            skipped.append({"metric": metric, "reason": str(reason)})
            return None

    plans = Plans(failure=attempt("failure_auroc", lambda: plan_failure(shards, min_class_episodes)))
    for name in (*CONTINUOUS_STATES, *BINARY_STATES):
        plan = attempt(f"state:{name}", lambda name=name: plan_state(name, shards))
        plans.states += [plan] if plan else []
    gap_ids = sorted({gap for meta in shards.meta for gap in meta["practice_gaps"]})
    if not gap_ids:
        skipped.append({"metric": "gap_jaccard", "reason": "no shard lists a practice gap"})
    for gap_id in gap_ids:
        plan = attempt(f"gap:{gap_id}", lambda gap_id=gap_id: plan_gap(gap_id, shards))
        plans.gaps += [plan] if plan else []
    return plans, skipped


def logistic_probe() -> Any:
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))


def ridge_probe() -> Any:
    return make_pipeline(StandardScaler(), RidgeCV(alphas=RIDGE_ALPHAS))


PROBES = {"r2": (ridge_probe, "predict", r2_score),
          "auroc": (logistic_probe, "decision_function", roc_auc_score)}


def out_of_fold(estimator: Any, response: str, features: np.ndarray, target: np.ndarray, folds: Folds) -> np.ndarray:
    scores = np.empty(len(target))
    for train, test in folds:
        fitted = clone(estimator).fit(features[train], target[train])
        scores[test] = getattr(fitted, response)(features[test])
    return scores


def failure_auroc(episode_means: np.ndarray, plan: FailurePlan) -> float:
    scores = out_of_fold(logistic_probe(), "decision_function", episode_means, plan.labels, plan.folds)
    return float(roc_auc_score(plan.labels, scores))


def state_score(layer_frames: np.ndarray, plan: StatePlan) -> float:
    make_probe, response, metric = PROBES[plan.kind]
    scores = out_of_fold(make_probe(), response, layer_frames[plan.rows].astype(np.float32), plan.target, plan.folds)
    return float(metric(plan.target, scores))


def gap_recovery(episode_means: np.ndarray, plan: GapPlan) -> tuple[float, int]:
    standardised = StandardScaler().fit_transform(episode_means[plan.failing])
    dimensions = min(PCA_DIMENSIONS, len(standardised) - 1, standardised.shape[1])
    embedded = PCA(dimensions, random_state=SEED).fit_transform(standardised)
    best_by_k = {}
    for k in range(2, min(MAX_CLUSTERS, len(embedded)) + 1):
        assignment = KMeans(k, n_init=10, random_state=SEED).fit_predict(embedded)
        best_by_k[k] = max(jaccard({plan.failing_ids[i] for i in np.flatnonzero(assignment == cluster)}, plan.members)
                           for cluster in range(k))
    best_k = max(best_by_k, key=lambda k: (best_by_k[k], -k))
    return float(best_by_k[best_k]), best_k


def evaluate_pair(site: str, layer: int, shards: Shards, plans: Plans) -> dict[str, Any]:
    episode_means = shards.means[site][:, layer, :]
    metrics: dict[str, float] = {}
    best_k: dict[str, int] = {}
    if plans.failure:
        metrics["failure_auroc"] = failure_auroc(episode_means, plans.failure)
    if plans.states:
        layer_frames = shards.frames[site][:, layer, :]
        metrics |= {f"state_{plan.kind}:{plan.name}": state_score(layer_frames, plan) for plan in plans.states}
    for plan in plans.gaps:
        metrics[f"gap_jaccard:{plan.gap_id}"], best_k[plan.gap_id] = gap_recovery(episode_means, plan)
    return {"site": site, "layer": layer, "metrics": metrics, "gap_best_k": best_k}


def pairs_of(shards: Shards) -> list[tuple[str, int]]:
    return [(site, layer) for site, array in shards.means.items() for layer in range(array.shape[1])]


def family_of(metric: str) -> str:
    return FAMILY_OF_KIND[metric.split(":")[0]]


def add_ranks(rows: list[dict[str, Any]]) -> None:
    metric_names = sorted(rows[0]["metrics"]) if rows else []
    for row in rows:
        row["ranks"], row["family_ranks"] = {}, {}
    for name in metric_names:
        ranks = rankdata(-np.array([row["metrics"][name] for row in rows]), method="average")
        for row, rank in zip(rows, ranks):
            row["ranks"][name] = float(rank)
    for row in rows:
        by_family: dict[str, list[float]] = defaultdict(list)
        for name, rank in row["ranks"].items():
            by_family[family_of(name)].append(rank)
        row["family_ranks"] = {family: mean(ranks) for family, ranks in by_family.items()}
        row["combined_rank"] = mean(row["family_ranks"].values()) if by_family else None


def best_first(rows: Iterable[dict[str, Any]], rank_of: Callable[[dict[str, Any]], float]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (rank_of(row), SITE_ORDER[row["site"]], row["layer"]))


def choose(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = [row for row in rows if row["combined_rank"] is not None]
    chosen = [{"site": row["site"], "layer": row["layer"], "reason": "best combined rank",
               "combined_rank": row["combined_rank"]}
              for row in best_first(ranked, lambda row: row["combined_rank"])[:2]]
    with_gaps = [row for row in ranked if GAP_FAMILY in row["family_ranks"]]
    if not with_gaps:
        return chosen
    top = best_first(with_gaps, lambda row: row["family_ranks"][GAP_FAMILY])[0]
    if (top["site"], top["layer"]) not in {(pick["site"], pick["layer"]) for pick in chosen}:
        chosen.append({"site": top["site"], "layer": top["layer"], "reason": "best practice-gap recovery",
                       "combined_rank": top["combined_rank"]})
    return chosen


def run_sweep(shard_dir: Path, min_class_episodes: int = MIN_CLASS_EPISODES) -> dict[str, Any]:
    shards = load_shards(shard_dir)
    plans, skipped = build_plans(shards, min_class_episodes)
    rows = [evaluate_pair(site, layer, shards, plans) for site, layer in pairs_of(shards)]
    add_ranks(rows)
    failures = int((~shards.success).sum())
    layers, hidden = next(iter(shards.means.values())).shape[1:]
    return {
        "shards": len(shards.meta) + shards.excluded_no_outcome,
        "episodes": {"success": len(shards.meta) - failures, "failure": failures,
                     "excluded_no_outcome": shards.excluded_no_outcome},
        "input_dtypes": sorted({meta["dtype"] for meta in shards.meta}),
        "layers": layers, "hidden": hidden, "sites": list(shards.means),
        "frames_used": {plan.name: int(len(plan.rows)) for plan in plans.states},
        "families_used": sorted({family_of(name) for name in rows[0]["metrics"]}) if rows else [],
        "skipped": skipped, "chosen": choose(rows), "pairs": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, help="directory written by export_activations.py")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-class-episodes", type=int, default=MIN_CLASS_EPISODES,
                        help="fewest episodes per outcome class for failure_auroc (pre-registered: 5)")
    args = parser.parse_args()
    started = time.monotonic()
    report = run_sweep(args.shards, args.min_class_episodes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['episodes']} in {time.monotonic() - started:.1f}s")
    print("chosen:", [(pick["site"], pick["layer"], pick["reason"]) for pick in report["chosen"]])
    for skip in report["skipped"]:
        print(f"skipped {skip['metric']}: {skip['reason']}")


if __name__ == "__main__":
    main()
