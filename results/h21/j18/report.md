# j18 and j19: a Gaussian mixture over all routes (exploratory, dev, H21b only)

Laptop worker 20261120-000900-16273, 2026-11-20. These are dev numbers. None of them can enter the UniAD read (`docs/prereg-views.md`, tag `views-prereg-v1`). No number here is significant, confirmed or a finding. Every score is measured on this laptop. Rows are in `VARIANTS.md` under "Exploratory, H21b pool, laptop j18-j19 (2026-11-20)".

## What the methods do

- **Prior mixture work.** m49 fit a diagonal mixture to the failing routes only (PCA 16) and ranked its components by size. m50 pooled m49 with the window view first. m49 turned out to be seed-fragile.
- **j18.** It uses m15's features: layer 8, the 50-frame window, PCA 32 fit on all routes, with standardised scores. A Gaussian mixture is fit to all 593 routes and never sees pass or fail. The grid is K in {4, 6, 8, 12} times diag or full covariance, `random_state` 0, `n_init` 3, and the lowest BIC wins. The components are ranked by the mean log density of all their routes, most atypical first. Each axis is the failing routes of one component. The result is pooled with whole-route L8 (m03), with the whole-route view first.
- **j19.** It uses the same mixture. It ranks the components by the share of their routes that fail.
- **The fit.** BIC chose full covariance with K 12 (measured), which is the top of the grid.

## Scores

Measured, 2,000 replicates, `pair` stripped of its `-sNN` suffix, so 100 Fail2Drive pairs are resampled. There are 593 routes and 174 of them fail.

| row | score | CustomObstacles | Wall | PedestriansOnRoad | vs B3-behaviour | vs B3-infraction | tried |
|---|---:|---:|---:|---:|---|---|---|
| j18 | 0.315 | 0.210 | 0.529 | 0.206 | +0.163 [+0.026, +0.319], p 0.006 | +0.028 [−0.122, +0.203], p 0.33 | 219 + 1 |
| j19 | 0.315 | 0.210 | 0.529 | 0.206 | +0.163 [+0.031, +0.315], p 0.004 | +0.028 [−0.117, +0.199], p 0.34 | 219 + 2 |
| m23 (reference, not a try) | 0.395 | 0.210 | 0.529 | 0.444 | +0.242 [+0.034, +0.451], p 0.007 | — | — |
| B3-behaviour | 0.152 | 0.191 | 0.165 | 0.101 | | | |
| B3-infraction | 0.287 | 0.394 | 0.200 | 0.267 | | | |

For j18 the failing-only chance is 0.126 and for j19 it is 0.128. Recall at Jaccard 0.5 is 0.33 for both, and both have 0 decoy hits.

**Mixture seed robustness for j18 (not tries, 200 replicates).** Seed 0 scores 0.315. Seeds 1 to 5 score 0.294, 0.316, 0.302, 0.300 and 0.300. Seed 2's BIC picked K 8; every other seed picked K 12.

## Reading

- Both rows sit below m23. Neither is separated from B3-infraction.
- The mixture view loses the pedestrian group. PedestriansOnRoad drops from m23's 0.444 to 0.206. CustomObstacles and Wall equal m23's values. Those two gaps are probably matched by the shared whole-route source, but no per-axis attribution was run, so this is unverified.
- Changing the ranking changed nothing. The mixture's components are not the right groups, so their order does not matter.
- The all-route mixture is stable across seeds, which m49's failing-only mixture was not.

## Checks

- `route-L8`, `b3_behaviour` and `b3_infraction` were rebuilt here from `results/savio/savio/f2d-h21b/pool/`. Their axes match `results/h21/h21/h21b/axes/` exactly.
- The stripped-pair manifest gives 100 distinct pairs among the cache routes.
- m23 rescored with `sprint_score.py` on this manifest gives an interval within 0.007 of the independent scorer's recorded interval, [+0.041, +0.450]. The two scorers draw different random numbers.
- After the `--rank` option was added, `j18_gmm.py` at its defaults reproduces j18's axes exactly.

## Path note

On this clone the shared inputs sit one directory deeper than the task text says. `results/savio/f2d-h21b/pool/` is at `results/savio/savio/f2d-h21b/pool/`, and `results/h21/h21b/` is at `results/h21/h21/h21b/`.

## Files

- `commands.sh` holds the exact commands.
- `axes/` holds the method, pool and rival axes.
- `report-j18.json` and `report-j19.json` are the scorer's reports.
- `check-m23.json` is the m23 check.
- `seeds/` holds the seed check.
- `manifest-pair-fixed.json` is the manifest with the seed suffix stripped from `pair`.
