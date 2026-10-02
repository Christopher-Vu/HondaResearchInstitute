"""Planted-gap scoring. PRD 10.2, 10.3 and Appendix B of the handoff.

Pure arithmetic over rollout-id sets: no GPU, no cluster, no policy. That is
deliberate, because it means the headline metric can be unit-tested on synthetic
data long before any rollout exists, and the scoring code can be frozen and
hash-committed before the test pool is generated (PRD 9.1).

One scoring run. Later re-runs are post hoc and must be labelled (PRD 9.1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .schema import TIERS, Directive, Gap

MATCH_THRESHOLD = 0.5  # theta, PRD 10.2


def jaccard(a: set[str], b: set[str]) -> float:
    """|a and b| / |a or b|. Two empty sets score 0, not 1: an axis that claims
    nothing has not recovered a gap that contains nothing."""
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _hungarian(matrix: list[list[float]]) -> list[tuple[int, int]]:
    """Maximise total similarity. Uses scipy when available; falls back to an
    exact Jonker-Volgenant-free brute force for the tiny sizes we actually have
    (K <= 8 gaps, M <= 10 axes), so the module has no hard scipy dependency."""
    n_rows, n_cols = len(matrix), len(matrix[0]) if matrix else 0
    if not n_rows or not n_cols:
        return []
    try:
        from scipy.optimize import linear_sum_assignment  # type: ignore
        import numpy as np  # type: ignore

        rows, cols = linear_sum_assignment(np.asarray(matrix), maximize=True)
        return list(zip(rows.tolist(), cols.tolist()))
    except ImportError:
        pass

    # Exact fallback: permutations of the smaller dimension.
    from itertools import permutations

    best_score, best_pairs = -1.0, []
    if n_rows <= n_cols:
        for combo in permutations(range(n_cols), n_rows):
            s = sum(matrix[r][c] for r, c in enumerate(combo))
            if s > best_score:
                best_score, best_pairs = s, list(enumerate(combo))
    else:
        for combo in permutations(range(n_rows), n_cols):
            s = sum(matrix[r][c] for c, r in enumerate(combo))
            if s > best_score:
                best_score, best_pairs = s, [(r, c) for c, r in enumerate(combo)]
    return best_pairs


@dataclass
class Match:
    gap_id: str
    tier: str
    axis_id: str | None
    jaccard: float
    matched: bool


@dataclass
class ScoringReport:
    """What PRD 9.1 step 4 publishes: per-tier metrics and which axes matched
    which gaps. Deliberately carries no predicates and no salt."""

    method: str
    budget_m: int
    matches: list[Match] = field(default_factory=list)
    recall_by_tier: dict[str, float] = field(default_factory=dict)
    precision_at_m: float = 0.0
    mean_best_jaccard: float = 0.0
    decoy_hit_rate: float = 0.0
    n_axes: int = 0

    def summary(self) -> str:
        lines = ["method=%s  M=%d  axes=%d" % (self.method, self.budget_m, self.n_axes)]
        for tier in TIERS:
            if tier in self.recall_by_tier:
                lines.append("  recall[%s] = %.3f" % (tier, self.recall_by_tier[tier]))
        lines.append("  precision@M     = %.3f" % self.precision_at_m)
        lines.append("  mean best Jacc  = %.3f" % self.mean_best_jaccard)
        lines.append("  decoy hit rate  = %.3f" % self.decoy_hit_rate)
        return "\n".join(lines)


def score(directive: Directive, gaps: Sequence[Gap], *,
          threshold: float = MATCH_THRESHOLD) -> ScoringReport:
    """Score one directive against the sealed gaps.

    One Hungarian assignment over ALL real gaps at once (PRD 10.2) rather than
    greedy per-gap best-match, so an axis cannot be credited for two gaps.
    Decoys are excluded from the assignment and scored separately: they are not
    gaps to be found, they are traps.
    """
    directive.validate()
    real = [g for g in gaps if not g.is_decoy]
    decoys = [g for g in gaps if g.is_decoy]
    for g in gaps:
        g.validate()

    axes = directive.axes
    rep = ScoringReport(method=directive.method, budget_m=directive.budget_m,
                        n_axes=len(axes))

    if not real:
        return rep

    jac = [[jaccard(g.failing_rollouts, a.rollouts) for a in axes] for g in real]

    # Mean best Jaccard is unconstrained by the assignment (PRD 10.3).
    if axes:
        rep.mean_best_jaccard = sum(max(row) for row in jac) / len(real)

    assignment = _hungarian(jac) if axes else []
    assigned = {r: c for r, c in assignment}

    for i, g in enumerate(real):
        col = assigned.get(i)
        j = jac[i][col] if col is not None else 0.0
        rep.matches.append(Match(
            gap_id=g.gap_id, tier=g.tier,
            axis_id=axes[col].axis_id if col is not None else None,
            jaccard=j, matched=j >= threshold,
        ))

    for tier in TIERS:
        in_tier = [m for m in rep.matches if m.tier == tier]
        if in_tier:
            rep.recall_by_tier[tier] = sum(m.matched for m in in_tier) / len(in_tier)

    # Precision always divides by the budget M, never by len(axes) (PRD 10.2).
    rep.precision_at_m = sum(m.matched for m in rep.matches) / directive.budget_m

    if decoys and axes:
        hits = 0
        for a in axes:
            if not a.rollouts:
                continue
            for d in decoys:
                inside = len(a.rollouts & (d.slice_rollouts or d.failing_rollouts))
                if inside / len(a.rollouts) >= 0.5:
                    hits += 1
                    break
        rep.decoy_hit_rate = hits / len(axes)

    return rep


def validated_precision(rep: ScoringReport, reproducing_axis_ids: Iterable[str],
                        ) -> float:
    """(matched + validated-natural) / M. PRD 9.4, 10.3.

    An axis that matches no planted gap but reproduces under test is a real
    finding, not an error. Secondary metric, computed after reproduction tests.
    """
    matched = {m.axis_id for m in rep.matches if m.matched and m.axis_id}
    extra = set(reproducing_axis_ids) - matched
    return (len(matched) + len(extra)) / rep.budget_m


def harness_is_valid(reports_by_method: dict[str, ScoringReport],
                     gaps: Sequence[Gap], *,
                     threshold: float = MATCH_THRESHOLD) -> tuple[bool, str]:
    """PRD 13.1 condition 1: at least one T0 control gap recovered by at least
    one method, and at least two T2 gaps re-confirming efficacy on the test pool.

    Returns (verdict, human-readable reason). This is the check that decides
    whether we have a measuring instrument at all.
    """
    t0_found = any(
        m.matched and m.tier == "T0_control"
        for rep in reports_by_method.values() for m in rep.matches
    )
    t2_efficacious = sum(
        1 for g in gaps
        if not g.is_decoy and g.tier == "T2_interactional" and g.efficacy
        and g.passes_efficacy()
    )
    if not t0_found:
        return False, ("no T0 control gap recovered by any method: the harness "
                       "is broken, not the methods (PRD 9.1)")
    if t2_efficacious < 2:
        return False, ("only %d T2 gap(s) re-confirm efficacy on the test pool; "
                       "need >= 2 (PRD 13.1)" % t2_efficacious)
    return True, "T0 recovered and %d T2 gaps efficacious" % t2_efficacious
