"""B3: behavioral stratification. docs/steps/b3-behavioral.md, PRD 9.3.

Clusters failing rollouts on what the car visibly did in the 3 s before it failed (kinematics and the logged state
list) plus which infractions it committed, and emits one axis per cluster, largest first. No activations, no
scenario metadata. The rollouts log no expert action, so the PRD's "action error versus the expert" is absent
(spec, Deviation).

Interpretations, pending sign-off (the spec is silent on these):
1. Window rows are the logged (strided) steps with end - 60 <= step < end; a window with no logged step uses the
   last logged step alone, as the contrastive method does.
2. "Fraction occluded" and "fraction at a red light" are NaN-ignoring means over window frames; a frame with no
   value counts as missing, not as 0. Captures from before the actor-class fields (349d7ef) have them all missing:
   distances become the far cap and the vehicle count 0, constant columns that z-score to 0.
3. lead_relative_speed with no lead is missing, then 0 after step 4 (no lead: no closing speed), not a far cap.
4. Rollouts are sorted by id before clustering, so the result does not depend on input order.
5. Ranking ties (equal size) go to the cluster whose smallest member id sorts first.
6. A supporting episode's activation is the negative distance to its centroid in z-space (higher = more typical);
   timesteps are the window's first and last logged step.
7. With fewer than 2 failing rollouts no clustering runs: one rollout gives one axis, none gives an empty directive.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans

from harness.schema import AxisCard, Directive, SupportingEpisode

METHOD = "B3_behavioral"
STEPS_PER_SECOND = 20

# Copy of adapters/simlingo/sweep_local.PENALIZED; src/ does not import from adapters/.
PENALIZED = ("collisions_layout", "collisions_pedestrian", "collisions_vehicle", "red_light",
             "stop_infraction", "outside_route_lanes", "yield_emergency_vehicle_infractions",
             "scenario_timeouts", "route_dev", "vehicle_blocked", "route_timeout")
DISTANCES = ("lead_distance", "pedestrian_distance", "junction_distance", "two_wheeler_distance",
             "animal_distance", "obstacle_distance")
WINDOW_FEATURES = ("ego_speed_mean", "ego_speed_min", "ego_speed_max", "lead_distance_min",
                   "lead_relative_speed_mean", "pedestrian_distance_min", "junction_distance_min",
                   "time_to_junction_min", "red_light_frac", "occluded_frac", "vehicles_50m_mean",
                   "two_wheeler_distance_min", "animal_distance_min", "obstacle_distance_min")
FEATURES = WINDOW_FEATURES + ("stationary_frac",) + tuple("infraction_" + name for name in PENALIZED)


@dataclass
class BehavioralConfig:
    """Committed and hashed before the gaps are finalised (PRD 9.3 fairness rule)."""

    budget_m: int = 10
    window_s: float = 3.0
    stall_speed: float = 0.1
    far_distance: float = 100.0
    far_time: float = 10.0
    n_init: int = 10
    seed: int = 0

    def validate(self) -> None:
        if self.budget_m <= 0:
            raise ValueError("budget_m must be positive")
        if self.window_s <= 0:
            raise ValueError("window_s must be positive")


@dataclass
class Rollout:
    """One failing or successful rollout: logged steps, the state list at those steps, and its outcome."""

    rollout_id: str
    steps: np.ndarray
    states: dict[str, np.ndarray]
    failed: bool
    infractions: dict[str, int]
    failure_step: int | None = None


def load_shard(sidecar: Path) -> Rollout | None:
    """A rollout from export_activations.py's json sidecar and npz; None when it has no valid outcome."""
    meta = json.loads(Path(sidecar).read_text())
    if meta.get("success") is None:
        return None
    names = ("ego_speed", "lead_distance", "lead_relative_speed", "pedestrian_distance", "junction_distance",
             "time_to_junction", "red_light", "occluded", "vehicles_50m", "two_wheeler_distance", "animal_distance",
             "obstacle_distance")
    with np.load(Path(sidecar).with_suffix(".npz")) as archive:
        steps = archive["step"].astype(np.int64)
        states = {name: archive[name].astype(np.float64) for name in names if name in archive.files}
    return Rollout(str(meta["route_id"]), steps, states, not meta["success"],
                   dict(meta.get("infractions") or {}), meta.get("first_collision_step"))


def window_rows(rollout: Rollout, config: BehavioralConfig) -> np.ndarray:
    span = int(config.window_s * STEPS_PER_SECOND)
    end = rollout.failure_step if rollout.failure_step is not None else int(rollout.steps[-1]) + 1
    rows = np.flatnonzero((rollout.steps >= end - span) & (rollout.steps < end))
    return rows if len(rows) else np.array([len(rollout.steps) - 1])


def _state(rollout: Rollout, name: str, rows: np.ndarray) -> np.ndarray:
    values = rollout.states.get(name)
    return np.full(len(rows), np.nan) if values is None else values[rows]


def _reduce(values: np.ndarray, how: str) -> float:
    if np.all(np.isnan(values)):
        return np.nan
    return float({"mean": np.nanmean, "min": np.nanmin, "max": np.nanmax}[how](values))


def features(rollout: Rollout, config: BehavioralConfig) -> np.ndarray:
    """The raw feature row (spec step 3), with spec step 4's missing-value rule applied."""
    rows = window_rows(rollout, config)
    speed = _state(rollout, "ego_speed", rows)
    window = {
        "ego_speed_mean": _reduce(speed, "mean"), "ego_speed_min": _reduce(speed, "min"),
        "ego_speed_max": _reduce(speed, "max"),
        "lead_distance_min": _reduce(_state(rollout, "lead_distance", rows), "min"),
        "lead_relative_speed_mean": _reduce(_state(rollout, "lead_relative_speed", rows), "mean"),
        "pedestrian_distance_min": _reduce(_state(rollout, "pedestrian_distance", rows), "min"),
        "junction_distance_min": _reduce(_state(rollout, "junction_distance", rows), "min"),
        "time_to_junction_min": _reduce(_state(rollout, "time_to_junction", rows), "min"),
        "red_light_frac": _reduce(_state(rollout, "red_light", rows), "mean"),
        "occluded_frac": _reduce(_state(rollout, "occluded", rows), "mean"),
        "vehicles_50m_mean": _reduce(_state(rollout, "vehicles_50m", rows), "mean"),
        "two_wheeler_distance_min": _reduce(_state(rollout, "two_wheeler_distance", rows), "min"),
        "animal_distance_min": _reduce(_state(rollout, "animal_distance", rows), "min"),
        "obstacle_distance_min": _reduce(_state(rollout, "obstacle_distance", rows), "min"),
    }
    for name in window:
        if np.isnan(window[name]):
            if name.removesuffix("_min") in DISTANCES:
                window[name] = config.far_distance
            elif name == "time_to_junction_min":
                window[name] = config.far_time
            else:
                window[name] = 0.0
    all_speed = rollout.states.get("ego_speed", np.array([]))
    known = all_speed[~np.isnan(all_speed)]
    stationary = float(np.mean(known < config.stall_speed)) if len(known) else 0.0
    infractions = [1.0 if rollout.infractions.get(name, 0) else 0.0 for name in PENALIZED]
    return np.array([window[name] for name in WINDOW_FEATURES] + [stationary] + infractions)


def zscore(matrix: np.ndarray) -> np.ndarray:
    std = matrix.std(axis=0)
    centred = matrix - matrix.mean(axis=0)
    return np.divide(centred, std, out=np.zeros_like(centred), where=std > 0)


def _name(centroid: np.ndarray) -> str:
    top = np.argsort(-np.abs(centroid), kind="stable")[:2]
    parts = []
    for index in top:
        feature = FEATURES[index]
        if feature.startswith("infraction_"):
            parts.append(feature.removeprefix("infraction_") if centroid[index] > 0
                         else "no " + feature.removeprefix("infraction_"))
        else:
            parts.append(("high " if centroid[index] > 0 else "low ") + feature)
    return ", ".join(parts)


def _description(raw: np.ndarray, centroid: np.ndarray, n_failing: int) -> str:
    top = np.argsort(-np.abs(centroid), kind="stable")[:2]
    means = "; ".join("%s mean %.3g" % (FEATURES[i], raw[:, i].mean()) for i in top)
    return "%d of %d failing rollouts behave alike in the 3 s before failing: %s" % (len(raw), n_failing, means)


def behavioral_directive(rollouts: list[Rollout], config: BehavioralConfig) -> Directive:
    """B3: k-means over failing rollouts' behavior, one axis per cluster, largest first."""
    config.validate()
    failing = sorted((r for r in rollouts if r.failed), key=lambda r: r.rollout_id)
    if not failing:
        return Directive(method=METHOD, axes=[], budget_m=config.budget_m)
    raw = np.stack([features(r, config) for r in failing])
    scaled = zscore(raw)
    k = min(config.budget_m, len(failing))
    if k == 1:
        labels = np.zeros(len(failing), dtype=int)
        centroids = scaled.mean(axis=0, keepdims=True)
    else:
        model = KMeans(n_clusters=k, n_init=config.n_init, random_state=config.seed).fit(scaled)
        labels, centroids = model.labels_, model.cluster_centers_
    clusters = [np.flatnonzero(labels == c) for c in range(len(centroids))]
    order = sorted((c for c in range(len(clusters)) if len(clusters[c])),
                   key=lambda c: (-len(clusters[c]), failing[clusters[c][0]].rollout_id))
    axes = []
    for rank, c in enumerate(order, start=1):
        members = clusters[c]
        distance = np.linalg.norm(scaled[members] - centroids[c], axis=1)
        episodes = []
        for index, d in zip(members, distance):
            rollout = failing[index]
            window = rollout.steps[window_rows(rollout, config)]
            episodes.append(SupportingEpisode(rollout.rollout_id, -float(d), (int(window[0]), int(window[-1]))))
        axes.append(AxisCard(
            axis_id="B3-a%d" % rank, name=_name(centroids[c]),
            description=_description(raw[members], centroids[c], len(failing)),
            rank=rank, score=len(members) / len(failing), method=METHOD,
            supporting_episodes=episodes, causal={"verdict": "untested"},
        ))
    directive = Directive(method=METHOD, axes=axes, budget_m=config.budget_m)
    directive.validate()
    return directive
