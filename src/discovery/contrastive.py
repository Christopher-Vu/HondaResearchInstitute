"""Contrastive diffing over SAE latents (PRD 9.2): features that fire more before failures than in success.

For each latent, compare failure windows with success windows across rollouts: the standardised mean difference of
the window-mean activation, and the log-odds of firing at least once in the window. Keep latents with Benjamini-
Hochberg q < 0.05 (Welch's t-test on window means), a positive difference, and support from at least 20 failing
rollouts. Merge latents whose failing-rollout firing sets overlap into axes, and rank axes by effect x support.

Interpretations, pending sign-off (PRD 9.2 is silent on these):
1. Frames come from the shards' strided steps; a frame's latent is the maximum over its 30 driving-query tokens.
2. A failing rollout's window is the 3 s (60 steps at 20 Hz) before its first collision, else its last 3 s. A
   successful rollout's window is 3 s at a position drawn with the seed. Rollouts without an outcome are left out.
3. Firing is activation > 0.1, as B7's tau_on. Support counts failing rollouts whose window has the latent firing.
4. Effect is the standardised mean difference (pooled standard deviation); an axis is ranked by its founding latent's
   effect x support.
5. Merging: walk kept latents by effect x support and join the axis whose failing firing set has the highest
   Jaccard >= 0.5 with the latent's, else start an axis, up to the budget M. Members are the failing rollouts in the
   axis's firing set (union of its latents').
"""
from __future__ import annotations

import random
from dataclasses import dataclass
import numpy as np
from scipy.stats import false_discovery_control, ttest_ind

from harness.schema import AxisCard, Directive, SupportingEpisode
from harness.scoring import jaccard

METHOD = "contrastive"
STEPS_PER_SECOND = 20


@dataclass
class ContrastiveConfig:
    window_s: float = 3.0
    tau_on: float = 0.1
    max_q: float = 0.05
    min_support: int = 20
    merge_jaccard: float = 0.5
    budget_m: int = 10
    seed: int = 0


@dataclass
class Rollout:
    """One rollout's per-frame latents, (frames, latents), with the step of each frame."""
    rollout_id: str
    latents: np.ndarray
    steps: np.ndarray
    failed: bool
    failure_step: int | None = None


def window_rows(rollout: Rollout, config: ContrastiveConfig, rng: random.Random) -> np.ndarray:
    span = int(config.window_s * STEPS_PER_SECOND)
    if rollout.failed:
        end = rollout.failure_step if rollout.failure_step is not None else int(rollout.steps[-1]) + 1
    else:
        first, last = int(rollout.steps[0]), int(rollout.steps[-1]) + 1
        end = rng.randint(min(first + span, last), last)
    rows = np.flatnonzero((rollout.steps >= end - span) & (rollout.steps < end))
    return rows if len(rows) else np.array([len(rollout.steps) - 1])


@dataclass
class Windows:
    means: np.ndarray
    fired: np.ndarray
    failed: np.ndarray
    ids: list[str]


def windows(rollouts: list[Rollout], config: ContrastiveConfig) -> Windows:
    rng = random.Random(config.seed)
    picked = [rollout.latents[window_rows(rollout, config, rng)] for rollout in rollouts]
    return Windows(np.stack([frames.mean(axis=0) for frames in picked]),
                   np.stack([(frames > config.tau_on).any(axis=0) for frames in picked]),
                   np.array([rollout.failed for rollout in rollouts]), [rollout.rollout_id for rollout in rollouts])


def latent_effects(found: Windows, config: ContrastiveConfig) -> dict[str, np.ndarray]:
    fail, succeed = found.means[found.failed], found.means[~found.failed]
    pooled = np.sqrt((fail.var(axis=0, ddof=1) + succeed.var(axis=0, ddof=1)) / 2)
    smd = np.where(pooled > 0, (fail.mean(axis=0) - succeed.mean(axis=0)) / np.where(pooled > 0, pooled, 1), 0.0)
    p = np.nan_to_num(ttest_ind(fail, succeed, equal_var=False).pvalue, nan=1.0)
    rate_fail = (found.fired[found.failed].sum(axis=0) + 0.5) / (found.failed.sum() + 1)
    rate_succeed = (found.fired[~found.failed].sum(axis=0) + 0.5) / ((~found.failed).sum() + 1)
    log_odds = np.log(rate_fail / (1 - rate_fail)) - np.log(rate_succeed / (1 - rate_succeed))
    return {"smd": smd, "q": false_discovery_control(p), "log_odds": log_odds,
            "support": found.fired[found.failed].sum(axis=0)}


@dataclass
class _Axis:
    founder: int
    score: float
    latents: list[int]
    members: set[str]


def merge(found: Windows, effects: dict[str, np.ndarray], config: ContrastiveConfig) -> list[_Axis]:
    keep = ((effects["q"] < config.max_q) & (effects["smd"] > 0) & (effects["support"] >= config.min_support))
    score = effects["smd"] * effects["support"]
    failing_ids = np.array(found.ids)[found.failed]
    axes: list[_Axis] = []
    for latent in sorted(np.flatnonzero(keep), key=lambda index: (-score[index], index)):
        members = set(failing_ids[found.fired[found.failed, latent]])
        overlaps = [(jaccard(axis.members, members), position) for position, axis in enumerate(axes)]
        best = max(overlaps, default=(0.0, -1))
        if best[0] >= config.merge_jaccard:
            axes[best[1]].latents.append(int(latent))
            axes[best[1]].members |= members
        elif len(axes) < config.budget_m:
            axes.append(_Axis(int(latent), float(score[latent]), [int(latent)], members))
    return axes


def contrastive_directive(rollouts: list[Rollout], config: ContrastiveConfig,
                          layer: str = "") -> tuple[Directive, dict[str, np.ndarray]]:
    found = windows(rollouts, config)
    effects = latent_effects(found, config)
    cards = [AxisCard(
        axis_id=f"contrastive-a{rank}", name=f"contrastive latent group {rank}",
        description=f"latents {axis.latents}; founder SMD {effects['smd'][axis.founder]:.2f}, "
                    f"support {int(effects['support'][axis.founder])}; not describability-gated",
        rank=rank, score=axis.score, method=METHOD, layer=layer,
        supporting_episodes=[SupportingEpisode(member, 0.0, (0, 0)) for member in sorted(axis.members)],
        causal={"verdict": "untested"})
        for rank, axis in enumerate(merge(found, effects, config), start=1)]
    directive = Directive(method=METHOD, axes=cards, budget_m=config.budget_m)
    directive.validate()
    return directive, effects


def frame_latents(token_latents: np.ndarray) -> np.ndarray:
    """(frames, tokens, latents) to (frames, latents): a latent's frame value is its maximum over tokens."""
    return token_latents.max(axis=1)
