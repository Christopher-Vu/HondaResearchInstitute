# j16 and j17: frame-to-frame change on the H21b pool

Exploratory, dev, H21b only (593 routes, 174 failing). Never enters the UniAD read. Every number is measured unless
marked otherwise. Rows: `docs/research/experiments/f2d-dev-simlingo/VARIANTS.md`, section "Exploratory, H21b pool,
laptop j16-j17 (2026-11-20)". Commands: `commands.sh` here.

## Method

From `frames.npz` (L8, last 50 frames, the rows j09 reads), every valid frame is scaled by one root-mean-square and
projected with unwhitened PCA 16 fitted on all frames (j09's projection). Each route gives a sequence of step sizes,
the norm of the difference between consecutive projected frames.

- **j16:** six statistics of the step sizes (mean, SD, max, share above the pool's 90th-percentile step, mean of the
  last 10 steps, straightness), standardised over all routes, Ward 2/3/5 on the failing routes, top 10.
- **j17:** j16 plus the 16-dim net displacement (last projected frame minus first), each block standardised and
  divided by the square root of its width. Written after j16 scored.
- **Pooled:** `pool_axes.py`, whole-route L8 (m03) first, then the method (r11 order).

Pass/fail comes from the cache's `meta.success`, as in every cache method. No other label field is read.

## Scores

`sprint_score.py` under A2, top 10, 2,000 bootstrap replicates over 100 Fail2Drive pairs (manifest copy with the
`-sNN` suffix stripped from `pair`).

| row | tried | score | CustomObstacles / Wall / PedestriansOnRoad | chance | vs B3-behaviour | vs B3-infraction |
|---|---|---|---|---|---|---|
| j16 | 220 | 0.135 | 0.184 / 0.143 / 0.078 | 0.125 | -0.017 [-0.050, +0.071], p 0.51 | -0.152 [-0.219, -0.035], p 0.995 |
| j16+route | 221 | 0.272 | 0.210 / 0.529 / 0.078 | 0.123 | +0.120 [-0.008, +0.287], p 0.040 | -0.014 [-0.162, +0.166], p 0.51 |
| j17+route | 222 | 0.279 | 0.210 / 0.529 / 0.098 | 0.126 | +0.127 [+0.001, +0.291], p 0.024 | -0.008 [-0.150, +0.168], p 0.49 |
| m23 (rescore, not a try) | — | 0.395 | 0.210 / 0.529 / 0.444 | 0.120 | +0.242 [+0.034, +0.451], p 0.007 | +0.108 [-0.093, +0.336], p 0.17 |
| B3-behaviour | — | 0.152 | 0.191 / 0.165 / 0.101 | | | |
| B3-infraction | — | 0.287 | 0.394 / 0.200 / 0.267 | | | |

## Reading

j16 alone sits at failing-only chance. In both pooled rows the whole-route view supplies CustomObstacles and Wall,
exactly as in m23, and the change features add nothing on PedestriansOnRoad, where m23's 50-frame window mean reaches
0.444. Adding direction (j17) moved PedestriansOnRoad by 0.020. Both pooled rows sit about 0.12 below m23 and are not
separated from B3-infraction. On this pool, how fast the L8 state moves in the last 50 frames carries less of the
gap structure than where it sits. j09 (0.298) stays the best temporal method.

## Checks

- m23's recorded axes rescored here: 0.395 and +0.242 [+0.034, +0.451], matching the corrected-unit figures.
- `route-L8` rebuilt here has the same axes as `results/h21/h21/h21b/axes/route-L8.json`.
- A second run of `j16_change.py` gave identical axes.

## Unverified

- Whether the change features would do better at another layer or a longer window was not tried. Sweeping them on
  this pool would be tuning on the answer.
- The input paths in this clone are `results/savio/savio/f2d-h21b/pool/` and `results/h21/h21/h21b/`, one level
  deeper than the brief's paths. They were assumed to be the same files; the m23 rescore matching is the evidence.
