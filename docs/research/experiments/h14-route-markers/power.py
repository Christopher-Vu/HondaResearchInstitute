"""H14 sample size: how often the effect rule reads a given true change on paired routes. Simulated, no rollouts.

    python docs/research/experiments/h14-route-markers/power.py --discordance 0.15 0.20 0.24

A pair is discordant when exactly one arm fails. Repeat-run noise splits discordant pairs evenly; a true change of
`delta` adds that share of pairs to one side. Thresholds sit at Holm's first step across three metrics, with one
metric carrying the effect. That is conservative for Real effect only: No effect needs all three metrics, so its
shares here are upper bounds.
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, norm

STAGE_1_PAIRS, ALL_PAIRS = 80, 213
STAGE_1_ALPHA, FINAL_ALPHA = 0.005 / 3, 0.045 / 3
MARGIN = 0.08
Z_90 = float(norm.ppf(0.95))
DELTAS = (0.0, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30)
DRAWS = 20_000
OUTPUT = Path(__file__).resolve().parents[2] / "data/h14_power.json"


@lru_cache(maxsize=None)
def mcnemar_p(only_a: int, only_b: int) -> float:
    return binomtest(only_a, only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0


def p_values(only_a: np.ndarray, only_b: np.ndarray) -> np.ndarray:
    return np.array([mcnemar_p(int(a), int(b)) for a, b in zip(only_a, only_b)])


def inside_margin(only_a: np.ndarray, only_b: np.ndarray, pairs: int) -> np.ndarray:
    """Agresti-Min 90% interval for a paired difference (0.5 added to each of the four cells) sits inside the margin."""
    a, b, total = only_a + 0.5, only_b + 0.5, pairs + 2.0
    centre = (a - b) / total
    half_width = Z_90 * np.sqrt((a + b) - (a - b) ** 2 / total) / total
    return (centre - half_width > -MARGIN) & (centre + half_width < MARGIN)


def discordant_counts(rng: np.random.Generator, pairs: int, discordance: float, delta: float) -> tuple[np.ndarray, np.ndarray]:
    draws = rng.multinomial(pairs, [discordance / 2 + delta, discordance / 2, 1 - discordance - delta], size=DRAWS)
    return draws[:, 0], draws[:, 1]


def rule_outcomes(rng: np.random.Generator, discordance: float, delta: float) -> dict[str, float]:
    """Shares of runs reaching each verdict: stop after Stage 1 on p, else read all pairs."""
    first_a, first_b = discordant_counts(rng, STAGE_1_PAIRS, discordance, delta)
    rest_a, rest_b = discordant_counts(rng, ALL_PAIRS - STAGE_1_PAIRS, discordance, delta)
    stopped = p_values(first_a, first_b) < STAGE_1_ALPHA
    final_a, final_b = first_a + rest_a, first_b + rest_b
    real = stopped | (p_values(final_a, final_b) < FINAL_ALPHA)
    inside = inside_margin(final_a, final_b, ALL_PAIRS)
    return {"stopped_at_stage_1": float(stopped.mean()), "real_effect": float((real & ~inside).mean()),
            "real_smaller_than_margin": float((real & inside).mean()),
            "no_effect_as_large_as_margin": float((~real & inside).mean()), "unresolved": float((~real & ~inside).mean())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--discordance", type=float, nargs="+", default=[0.15, 0.20, 0.24])
    args = parser.parse_args()
    rng = np.random.default_rng(14)
    report = {"pairs": [STAGE_1_PAIRS, ALL_PAIRS], "alpha_at_holm_first_step": [STAGE_1_ALPHA, FINAL_ALPHA],
              "margin": MARGIN, "draws": DRAWS, "by_discordance": {}}
    for discordance in args.discordance:
        report["by_discordance"][str(discordance)] = {
            "half_width_points": {pairs: round(100 * Z_90 * (discordance / pairs) ** 0.5, 1) for pairs in report["pairs"]},
            "two_stage_rule_by_true_change": {str(delta): rule_outcomes(rng, discordance, delta) for delta in DELTAS},
        }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
