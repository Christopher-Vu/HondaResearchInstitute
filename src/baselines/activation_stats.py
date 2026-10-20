"""B7: rollout-free activation statistics. docs/steps/b7-gap-signal.md, steps 3-8.

Ranks SAE latents by a fixed concentration score kappa (rare, about one onset
per episode, strong, brief), merges latents that fire in the same test rollouts
into axes, and attaches the failing rollouts each axis fires in. Inputs are plain
arrays of raw latent activations, one (frames, n_latents) array per episode; the
SAE that produces them is a Step 7 deliverable.

Outcome labels enter only in build_axes (step 8). latent_scores and the merge in
step 7 never see them.

Firing follows Dr. VLA (App. C.1, Eqs. 7-12; CONFLICTS.md C18, signed off by Chris
2026-10-16): a hysteresis, and an active-episode set E+ of episodes where the latent
is ever > 0. Numbers produced before this change are labelled pre-correction.

Interpretations, pending sign-off (the spec is frozen and silent on these):
1. Firing is a hysteresis (Eq. 7): on[t, f] is true when activation > tau_on, false
   when activation is exactly 0, and otherwise keeps on[t-1, f]; before frame 0 the
   state is off.
2. An onset is an off-to-on transition; the frame before frame 0 counts as off,
   so a latent on at frame 0 has an onset there.
3. E+ for a latent is the episodes where its activation is ever > 0. Coverage = |E+| /
   all stat episodes. Onset count, peak and relative run length ((on frames / onsets)
   / episode length, 0 in an episode with no onset) are averaged over E+.
4. Exclusion drops a latent with |E+| below min_episodes, coverage strictly greater
   than max_coverage, or no onset in any stat episode (it never switches on, so its
   onset term is undefined).
5. kappa = z(-log c) + z(-|log o|) + z(a) + z(-l_r); z-scores across surviving
   latents with population std; a term with std 0 contributes 0.
6. Latents are ranked by kappa descending (ties: lower latent index first). A
   latent's fire set is the test rollouts where it is on at least one frame. It
   merges into the existing axis whose fire set (union of member fire sets) has
   the highest Jaccard with it if that is >= merge_jaccard, and the axis fire set
   becomes the union. Otherwise it starts a new axis, unless budget_m axes exist,
   in which case the walk stops. Latents with an empty test fire set are skipped.
7. An axis's supporting episodes are the failing test rollouts in its fire set;
   timesteps = (first, last) frame on for any member latent, activation = max
   member activation there. Axis score = kappa of the founding latent; rank is
   creation order from 1.
8. Every Jaccard is harness.scoring.jaccard, so two empty sets score 0.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from harness.schema import AxisCard, Directive, SupportingEpisode
from harness.scoring import jaccard

METHOD = "B7_actstats"
VARIANTS = ("A", "B")

Episodes = Mapping[str, np.ndarray]


@dataclass
class ActivationStatsConfig:
    """Fixed by the frozen spec. Committed and hashed at Step 6."""

    tau_on: float = 0.1
    min_episodes: int = 3
    max_coverage: float = 0.5
    merge_jaccard: float = 0.5
    budget_m: int = 10
    variant: str = "A"

    def validate(self) -> None:
        if self.variant not in VARIANTS:
            raise ValueError("variant must be one of %s, got %r"
                             % (VARIANTS, self.variant))
        if self.min_episodes < 1:
            raise ValueError("min_episodes must be at least 1")
        if not 0.0 < self.max_coverage <= 1.0:
            raise ValueError("max_coverage must be in (0, 1]")
        if not 0.0 < self.merge_jaccard <= 1.0:
            raise ValueError("merge_jaccard must be in (0, 1]")
        if self.budget_m <= 0:
            raise ValueError("budget_m must be positive")


@dataclass(frozen=True)
class LatentScores:
    """Surviving latents, best first. latent_ids[i] has concentration kappa[i]."""

    latent_ids: np.ndarray
    kappa: np.ndarray


def _check_episodes(episodes: Episodes, name: str) -> int:
    if not episodes:
        raise ValueError("%s is empty" % name)
    widths = set()
    for ep_id, acts in episodes.items():
        if acts.ndim != 2 or acts.shape[0] == 0:
            raise ValueError("%s[%r] must be a non-empty (frames, n_latents) array"
                             % (name, ep_id))
        widths.add(acts.shape[1])
    if len(widths) != 1:
        raise ValueError("%s: episodes disagree on n_latents: %s"
                         % (name, sorted(widths)))
    return widths.pop()


def on_state(acts: np.ndarray, tau_on: float) -> np.ndarray:
    """Eq. 7's hysteresis: on above tau_on, off at exactly 0, otherwise unchanged."""
    on = np.zeros(acts.shape, dtype=bool)
    previous = np.zeros(acts.shape[1], dtype=bool)
    for t in range(acts.shape[0]):
        previous = (acts[t] > tau_on) | (previous & (acts[t] != 0))
        on[t] = previous
    return on


def _onset_counts(on: np.ndarray) -> np.ndarray:
    rising = on[1:] & ~on[:-1]
    return on[0].astype(int) + rising.sum(axis=0)


def _per_episode_totals(episodes: Episodes, tau_on: float, n_latents: int
                        ) -> dict[str, np.ndarray]:
    totals = {k: np.zeros(n_latents) for k in
              ("episodes_on", "onsets", "peak", "run")}
    for acts in episodes.values():
        on = on_state(acts, tau_on)
        onsets = _onset_counts(on)
        active = (acts > 0).any(axis=0)                     # E+ membership
        safe_onsets = np.where(onsets > 0, onsets, 1)
        run = np.where(onsets > 0, on.sum(axis=0) / safe_onsets / acts.shape[0], 0.0)
        totals["episodes_on"] += active
        totals["onsets"] += np.where(active, onsets, 0)
        totals["peak"] += np.where(active, acts.max(axis=0), 0.0)
        totals["run"] += np.where(active, run, 0.0)
    return totals


def _zscore(values: np.ndarray) -> np.ndarray:
    std = values.std()
    if std == 0:
        return np.zeros_like(values)
    return (values - values.mean()) / std


def latent_scores(stat_episodes: Episodes, cfg: ActivationStatsConfig
                  ) -> LatentScores:
    """Steps 3-6: statistics, exclusions, kappa. Takes no outcome labels."""
    cfg.validate()
    n_latents = _check_episodes(stat_episodes, "stat_episodes")
    totals = _per_episode_totals(stat_episodes, cfg.tau_on, n_latents)
    n_on = totals["episodes_on"]
    coverage = n_on / len(stat_episodes)
    keep = (n_on >= cfg.min_episodes) & (coverage <= cfg.max_coverage) & (totals["onsets"] > 0)
    ids = np.flatnonzero(keep)
    if ids.size == 0:
        return LatentScores(ids, np.zeros(0))

    denom = n_on[ids]
    mean_onsets = totals["onsets"][ids] / denom
    mean_peak = totals["peak"][ids] / denom
    mean_run = totals["run"][ids] / denom
    kappa = (_zscore(-np.log(coverage[ids])) + _zscore(-np.abs(np.log(mean_onsets)))
             + _zscore(mean_peak) + _zscore(-mean_run))
    order = np.lexsort((ids, -kappa))
    return LatentScores(ids[order], kappa[order])


@dataclass
class _Axis:
    founder_kappa: float
    latents: list[int]
    fire_set: set[str]


def _fire_sets(test_episodes: Episodes, tau_on: float) -> dict[int, set[str]]:
    fired: dict[int, set[str]] = {}
    for ep_id, acts in test_episodes.items():
        for latent in np.flatnonzero(on_state(acts, tau_on).any(axis=0)):
            fired.setdefault(int(latent), set()).add(ep_id)
    return fired


def _best_axis(axes: list[_Axis], fire_set: set[str], threshold: float
               ) -> _Axis | None:
    best, best_j = None, 0.0
    for axis in axes:
        j = jaccard(axis.fire_set, fire_set)
        if j > best_j:
            best, best_j = axis, j
    return best if best is not None and best_j >= threshold else None


def merge_latents(scores: LatentScores, test_episodes: Episodes,
                  cfg: ActivationStatsConfig) -> list[_Axis]:
    """Step 7: walk latents by kappa, merge by fire-set Jaccard, stop at budget."""
    fired = _fire_sets(test_episodes, cfg.tau_on)
    axes: list[_Axis] = []
    for latent, kappa in zip(scores.latent_ids.tolist(), scores.kappa.tolist()):
        fire_set = fired.get(latent)
        if not fire_set:
            continue
        target = _best_axis(axes, fire_set, cfg.merge_jaccard)
        if target is not None:
            target.latents.append(latent)
            target.fire_set |= fire_set
        elif len(axes) < cfg.budget_m:
            axes.append(_Axis(kappa, [latent], set(fire_set)))
        else:
            break
    return axes


def _supporting_episode(ep_id: str, acts: np.ndarray, latents: list[int],
                        tau_on: float) -> SupportingEpisode:
    member = acts[:, latents]
    frames = np.flatnonzero(on_state(member, tau_on).any(axis=1))
    return SupportingEpisode(ep_id, float(member.max()),
                             (int(frames[0]), int(frames[-1])))


def _axis_card(rank: int, axis: _Axis, test_episodes: Episodes,
               failing: set[str], cfg: ActivationStatsConfig) -> AxisCard:
    members = sorted(axis.fire_set & failing)
    support = [_supporting_episode(e, test_episodes[e], axis.latents, cfg.tau_on)
               for e in members]
    return AxisCard(
        axis_id="B7-%s-a%d" % (cfg.variant, rank),
        name="B7 latent group %d" % rank,
        description="variant %s; latents %s, ranked by the concentration score; "
                    "not describability-gated" % (cfg.variant, axis.latents),
        rank=rank,
        score=axis.founder_kappa,
        method=METHOD,
        supporting_episodes=support,
        preprocessing=[],
        causal={"verdict": "untested"},
    )


def build_axes(axes: list[_Axis], test_episodes: Episodes, failing: set[str],
               cfg: ActivationStatsConfig) -> list[AxisCard]:
    """Step 8: the only place outcomes enter."""
    unknown = failing - set(test_episodes)
    if unknown:
        raise ValueError("failing rollouts missing from test_episodes: %s"
                         % sorted(unknown)[:5])
    return [_axis_card(i + 1, a, test_episodes, failing, cfg)
            for i, a in enumerate(axes)]


def activation_stats_directive(stat_episodes: Episodes, test_episodes: Episodes,
                               failing: set[str], cfg: ActivationStatsConfig
                               ) -> Directive:
    """B7 end to end: latent_scores, merge_latents, build_axes."""
    cfg.validate()
    n_stat = _check_episodes(stat_episodes, "stat_episodes")
    n_test = _check_episodes(test_episodes, "test_episodes")
    if n_stat != n_test:
        raise ValueError("stat and test episodes disagree on n_latents: %d vs %d"
                         % (n_stat, n_test))
    scores = latent_scores(stat_episodes, cfg)
    axes = merge_latents(scores, test_episodes, cfg)
    directive = Directive(method=METHOD,
                          axes=build_axes(axes, test_episodes, set(failing), cfg),
                          budget_m=cfg.budget_m)
    directive.validate()
    return directive
