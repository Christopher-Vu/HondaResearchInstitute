"""The activation-advantage test of PRD 13.1, condition 2, with the base-route bootstrap of PRD 10.3 and C13.

Point estimates on the scoring pool, and a cluster bootstrap whose unit is the base route: each replicate draws
base routes with replacement, every rollout carries its base route's draw count as a weight, and Jaccard is taken
on weighted sets. Methods are not re-run; their axes are fixed. Both "best" selections are re-made inside every
replicate (C13), so the interval covers the selection as well as the sampling.

Pinned here, pending sign-off with the preregistration draft:
1. Weighted Jaccard = sum of weights over the intersection / sum over the union; a zero union scores 0, as
   harness.scoring.jaccard does for two empty sets.
2. Delta = max over activation methods of interactional mean best Jaccard - max over baselines of the same. Both
   maxima are re-taken in every replicate.
3. Recall (condition 2a) is the point estimate on the full pool: the best activation method's interactional recall
   must be strictly greater than every baseline's. Ties fail.
4. The interval is the percentile interval at 2.5 and 97.5; condition 2b needs delta >= 0.15 and a lower bound > 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .schema import Directive, Gap
from .scoring import MATCH_THRESHOLD, jaccard, score

INTERACTIONAL = "T2_interactional"
MARGIN = 0.15


def weighted_jaccard(a: set[str], b: set[str], weight: Mapping[str, float]) -> float:
    union = sum(weight.get(r, 0.0) for r in a | b)
    if union == 0:
        return 0.0
    return sum(weight.get(r, 0.0) for r in a & b) / union


def mean_best_jaccard(directive: Directive, gaps: Sequence[Gap], weight: Mapping[str, float] | None = None) -> float:
    """Mean over `gaps` of the best Jaccard between the gap's failing rollouts and any axis; 0 with no axes."""
    if not gaps:
        return 0.0
    best = []
    for gap in gaps:
        scores = [jaccard(gap.failing_rollouts, axis.rollouts) if weight is None
                  else weighted_jaccard(gap.failing_rollouts, axis.rollouts, weight) for axis in directive.axes]
        best.append(max(scores, default=0.0))
    return sum(best) / len(gaps)


def interactional_recall(directive: Directive, gaps: Sequence[Gap]) -> float:
    return score(directive, gaps, threshold=MATCH_THRESHOLD).recall_by_tier.get(INTERACTIONAL, 0.0)


@dataclass
class AdvantageReport:
    best_activation_by_recall: str
    activation_recall: float
    best_baseline_recall: float
    recall_condition: bool
    delta: float
    interval: tuple[float, float]
    margin_condition: bool
    replicates: int

    @property
    def holds(self) -> bool:
        return self.recall_condition and self.margin_condition


def _delta(activation: Mapping[str, Directive], baselines: Mapping[str, Directive], gaps: Sequence[Gap],
           weight: Mapping[str, float] | None) -> float:
    best_activation = max(mean_best_jaccard(d, gaps, weight) for d in activation.values())
    best_baseline = max(mean_best_jaccard(d, gaps, weight) for d in baselines.values())
    return best_activation - best_baseline


def advantage(activation: Mapping[str, Directive], baselines: Mapping[str, Directive], gaps: Sequence[Gap],
              base_of: Mapping[str, str], *, replicates: int = 10_000, seed: int = 20261016) -> AdvantageReport:
    """PRD 13.1 condition 2 over the real (non-decoy) gaps; base_of maps every scored rollout id to its base route."""
    if not activation or not baselines:
        raise ValueError("need at least one activation method and one baseline")
    real = [g for g in gaps if not g.is_decoy]
    t2 = [g for g in real if g.tier == INTERACTIONAL]
    if not t2:
        raise ValueError("no interactional gaps: condition 2 is undefined")

    recall = {name: interactional_recall(d, real) for name, d in activation.items()}
    tie_break = {name: mean_best_jaccard(d, t2) for name, d in activation.items()}
    best = max(sorted(recall), key=lambda n: (recall[n], tie_break[n]))
    best_baseline_recall = max(interactional_recall(d, real) for d in baselines.values())

    bases = sorted(set(base_of.values()))
    rollouts_of: dict[str, list[str]] = {}
    for rollout, base in base_of.items():
        rollouts_of.setdefault(base, []).append(rollout)
    rng = np.random.default_rng(seed)
    deltas = np.empty(replicates)
    for i in range(replicates):
        counts = np.bincount(rng.integers(0, len(bases), len(bases)), minlength=len(bases))
        weight = {r: float(c) for base, c in zip(bases, counts) if c for r in rollouts_of[base]}
        deltas[i] = _delta(activation, baselines, t2, weight)
    low, high = (float(v) for v in np.percentile(deltas, [2.5, 97.5]))
    delta = _delta(activation, baselines, t2, None)
    return AdvantageReport(
        best_activation_by_recall=best, activation_recall=recall[best],
        best_baseline_recall=best_baseline_recall, recall_condition=recall[best] > best_baseline_recall,
        delta=delta, interval=(low, high), margin_condition=delta >= MARGIN and low > 0, replicates=replicates,
    )
