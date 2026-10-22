"""Probe-residual discovery, M3a (PRD 9.2; docs/steps/probe-residual.md).

Linear probes decode a pre-registered state list from frame activations, fitted on successful rollouts. On the
3 s before each failure, the standardized decode errors (decoded - true) say what the policy mis-represents there;
HDBSCAN groups those error vectors, and each group of failing rollouts becomes an axis.

Interpretations, pending sign-off (the spec is silent on these):
1. Window rows are the logged (strided) steps with end - 60 <= step < end; a window with no logged step uses the
   last logged step, as the contrastive method does.
2. sigma is the population standard deviation of the state over the success frames used to fit its probe; a state
   with sigma 0 or fewer than 2 success frames gets no probe and contributes 0 everywhere.
3. A rollout whose modal cluster ties with another takes the lower cluster label; HDBSCAN noise (-1) never counts
   as a cluster, but noise frames count toward the window size in the "at least half" rule.
4. Effect is the mean L2 norm of the residual vectors of the member rollouts' window frames that fall in the
   cluster. Ties in effect x support go to the lower cluster label.
5. A supporting episode's activation is the share of its window frames in the cluster; timesteps are the window's
   first and last logged step.
6. Fewer window frames than min_cluster_size: no clustering, empty directive.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from harness.failure_time import failure_step
from harness.schema import AxisCard, Directive, SupportingEpisode

METHOD = "probe_residual"
STEPS_PER_SECOND = 20
STATES = ("lead_distance", "lead_relative_speed", "pedestrian_distance", "red_light", "time_to_junction",
          "occluded")
RIDGE_ALPHAS = (1.0, 10.0, 100.0, 1000.0)


@dataclass
class ProbeResidualConfig:
    budget_m: int = 10
    window_s: float = 3.0
    min_cluster_size: int = 60
    min_support: int = 20

    def validate(self) -> None:
        if self.budget_m <= 0 or self.min_cluster_size < 2 or self.min_support < 1:
            raise ValueError("budget_m, min_cluster_size and min_support must be positive (min_cluster_size >= 2)")


@dataclass
class Rollout:
    """One rollout: logged steps, frame activations (T, d) at one layer and site, the state list, the outcome."""

    rollout_id: str
    steps: np.ndarray
    activations: np.ndarray
    states: dict[str, np.ndarray]
    failed: bool
    failure_step: int | None = None


def load_shard(sidecar: Path, site: str, layer: int) -> Rollout | None:
    """A rollout from export_activations.py's output at `site` (e.g. driving_queries) and decoder `layer`."""
    meta = json.loads(Path(sidecar).read_text())
    if meta.get("success") is None:
        return None
    with np.load(Path(sidecar).with_suffix(".npz")) as archive:
        steps = archive["step"].astype(np.int64)
        activations = archive[site][:, layer].astype(np.float64)
        states = {name: archive[name].astype(np.float64) for name in STATES if name in archive.files}
        failed_at = failure_step(meta, archive)
    return Rollout(str(meta["route_id"]), steps, activations, states, not meta["success"], failed_at)


def window_rows(rollout: Rollout, config: ProbeResidualConfig) -> np.ndarray:
    span = int(config.window_s * STEPS_PER_SECOND)
    end = rollout.failure_step if rollout.failure_step is not None else int(rollout.steps[-1]) + 1
    rows = np.flatnonzero((rollout.steps >= end - span) & (rollout.steps < end))
    return rows if len(rows) else np.array([len(rollout.steps) - 1])


def _state(rollout: Rollout, name: str) -> np.ndarray:
    values = rollout.states.get(name)
    return np.full(len(rollout.steps), np.nan) if values is None else values


@dataclass
class Probe:
    model: object
    sigma: float


def fit_probes(successes: list[Rollout]) -> dict[str, Probe]:
    """One ridge probe per state that has enough varying values on success frames."""
    probes: dict[str, Probe] = {}
    if not successes:
        return probes
    features = np.concatenate([r.activations for r in successes])
    for name in STATES:
        target = np.concatenate([_state(r, name) for r in successes])
        known = ~np.isnan(target)
        if known.sum() < 2 or target[known].std() == 0:
            continue
        model = make_pipeline(StandardScaler(), RidgeCV(alphas=RIDGE_ALPHAS)).fit(features[known], target[known])
        probes[name] = Probe(model, float(target[known].std()))
    return probes


def residuals(rollout: Rollout, rows: np.ndarray, probes: dict[str, Probe]) -> np.ndarray:
    """(len(rows), len(STATES)) standardized decode errors; 0 where a state has no value or no probe."""
    out = np.zeros((len(rows), len(STATES)))
    for j, name in enumerate(STATES):
        probe = probes.get(name)
        if probe is None:
            continue
        true = _state(rollout, name)[rows]
        decoded = probe.model.predict(rollout.activations[rows])
        error = (decoded - true) / probe.sigma
        out[:, j] = np.where(np.isnan(true), 0.0, error)
    return out


def _name(mean_residual: np.ndarray) -> str:
    top = np.argsort(-np.abs(mean_residual), kind="stable")[:2]
    return ", ".join(("over-estimates " if mean_residual[j] > 0 else "under-estimates ") + STATES[j] for j in top)


def probe_residual_directive(rollouts: list[Rollout], config: ProbeResidualConfig) -> Directive:
    """M3a: cluster failing rollouts by what their activations mis-represent before the failure."""
    config.validate()
    rollouts = sorted(rollouts, key=lambda r: r.rollout_id)
    probes = fit_probes([r for r in rollouts if not r.failed])
    failing = [r for r in rollouts if r.failed]
    windows = [window_rows(r, config) for r in failing]
    blocks = [residuals(r, rows, probes) for r, rows in zip(failing, windows)]
    empty = Directive(method=METHOD, axes=[], budget_m=config.budget_m)
    if sum(len(b) for b in blocks) < config.min_cluster_size:
        return empty
    vectors = np.concatenate(blocks)
    labels = HDBSCAN(min_cluster_size=config.min_cluster_size, copy=False).fit_predict(vectors)
    owner = np.concatenate([np.full(len(b), i) for i, b in enumerate(blocks)])

    members: dict[int, list[tuple[int, float]]] = {}
    for i in range(len(failing)):
        own = labels[owner == i]
        clustered = own[own >= 0]
        if not len(clustered):
            continue
        counts = np.bincount(clustered)
        label = int(np.argmax(counts))
        if counts[label] * 2 >= len(own):
            members.setdefault(label, []).append((i, counts[label] / len(own)))

    ranked = []
    for label, rows in members.items():
        if len(rows) < config.min_support:
            continue
        frames = np.concatenate([blocks[i][labels[owner == i] == label] for i, _ in rows])
        effect = float(np.linalg.norm(frames, axis=1).mean())
        ranked.append((effect * len(rows), label, rows, frames.mean(axis=0), effect))
    ranked.sort(key=lambda t: (-t[0], t[1]))

    axes = []
    for rank, (score, _, rows, mean_residual, effect) in enumerate(ranked[:config.budget_m], start=1):
        episodes = []
        for i, share in rows:
            window = failing[i].steps[windows[i]]
            episodes.append(SupportingEpisode(failing[i].rollout_id, float(share), (int(window[0]), int(window[-1]))))
        axes.append(AxisCard(
            axis_id="PR-a%d" % rank, name=_name(mean_residual),
            description="%d failing rollouts whose activations mis-represent the state alike before failing "
                        "(mean standardized error %s; effect %.3g)"
                        % (len(rows), ", ".join("%s %+.2f" % (s, v) for s, v in zip(STATES, mean_residual)), effect),
            rank=rank, score=score, method=METHOD, supporting_episodes=episodes, causal={"verdict": "untested"},
        ))
    directive = Directive(method=METHOD, axes=axes, budget_m=config.budget_m)
    directive.validate()
    return directive
