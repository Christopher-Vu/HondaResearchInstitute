"""B1: the random baseline. PRD 9.3.

The chance floor. Draws M random subsets of failing rollouts, with sizes taken
from the primary activation method's axis sizes so that it is matched on support
and cannot be beaten on set-size alone.

This is the only baseline implementable with no policy, no activations and no
GPU, which is why it is first: it exercises the whole scoring path with a real
method rather than a test fixture.

PRD 10.3: B1 is averaged over many draws (default 1000), not run once, because a
single draw of a chance baseline is noise.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from harness.schema import AxisCard, Directive, SupportingEpisode


@dataclass
class RandomBaselineConfig:
    """Committed and hashed before the gaps are finalised (PRD 9.3 fairness rule).

    axis_sizes comes from the primary activation method's axes. Declaring it in
    the config rather than computing it at scoring time keeps the provenance
    auditable.
    """

    axis_sizes: Sequence[int]
    budget_m: int = 10
    n_draws: int = 1000
    seed: int = 0

    def validate(self) -> None:
        if not self.axis_sizes:
            raise ValueError("axis_sizes is empty: B1 must be size-matched to the "
                             "primary method (PRD 9.3)")
        if any(s <= 0 for s in self.axis_sizes):
            raise ValueError("axis_sizes must all be positive")
        if self.budget_m <= 0:
            raise ValueError("budget_m must be positive")
        if self.n_draws <= 0:
            raise ValueError("n_draws must be positive")


def draw_directive(failing_rollouts: Sequence[str], cfg: RandomBaselineConfig,
                   *, draw_index: int = 0) -> Directive:
    """One draw: M axes of random failing rollouts, sized from the config.

    Sampling is from failing rollouts only, matching what score() compares
    against (F(g) is a set of failing rollouts), so B1 is not handicapped by
    wasting its budget on successes.
    """
    cfg.validate()
    if not failing_rollouts:
        return Directive(method="B1_random", axes=[], budget_m=cfg.budget_m)

    rng = random.Random((cfg.seed, draw_index).__hash__())
    pool = list(failing_rollouts)
    axes: list[AxisCard] = []

    for i in range(cfg.budget_m):
        size = cfg.axis_sizes[i % len(cfg.axis_sizes)]
        size = min(size, len(pool))
        chosen = rng.sample(pool, size)
        axes.append(AxisCard(
            axis_id="B1-d%d-a%d" % (draw_index, i),
            # B1's axes are deliberately not describable. The name says so
            # rather than pretending otherwise: PRD 9.2 uses B0/B1 as the
            # gate's incoherent-axis control.
            name="random subset %d" % i,
            description="uniform random sample of %d failing rollouts; "
                        "no semantic content by construction" % size,
            rank=i + 1,
            score=1.0 / (i + 1),
            method="B1_random",
            supporting_episodes=[SupportingEpisode(r, 0.0, (0, 0)) for r in chosen],
            preprocessing=[],
            causal={"verdict": "untested"},
        ))

    d = Directive(method="B1_random", axes=axes, budget_m=cfg.budget_m)
    d.validate()
    return d


def score_averaged(failing_rollouts: Sequence[str], gaps, cfg: RandomBaselineConfig):
    """Run B1 over n_draws and average the metrics (PRD 10.3).

    Returns (mean_report_dict, per_draw_reports). The mean dict is what goes in
    the results table; the per-draw list is kept so the spread can be reported,
    since a chance floor with no spread is not informative.
    """
    from harness.scoring import score  # local import: keeps module import cheap

    cfg.validate()
    reports = [score(draw_directive(failing_rollouts, cfg, draw_index=i), gaps)
               for i in range(cfg.n_draws)]

    tiers: dict[str, list[float]] = {}
    for rep in reports:
        for tier, val in rep.recall_by_tier.items():
            tiers.setdefault(tier, []).append(val)

    summary = {
        "method": "B1_random",
        "n_draws": cfg.n_draws,
        "recall_by_tier": {t: mean(v) for t, v in tiers.items()},
        "recall_by_tier_max": {t: max(v) for t, v in tiers.items()},
        "precision_at_m": mean(r.precision_at_m for r in reports),
        "mean_best_jaccard": mean(r.mean_best_jaccard for r in reports),
        "decoy_hit_rate": mean(r.decoy_hit_rate for r in reports),
    }
    return summary, reports
