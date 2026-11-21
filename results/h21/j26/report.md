# j26 and j27: clustering failing routes by probe attribution (exploratory, dev, H21b only)

Laptop worker 20261120-155431-29349, 2026-11-20. These are dev numbers. None of them can enter the UniAD read (`docs/prereg-views.md`, tag `views-prereg-v1`). No number here is significant, confirmed or a finding. Every number is measured on this laptop unless marked otherwise. Rows are in `VARIANTS.md` under "Exploratory, H21b pool, laptop j26-j27 (2026-11-20)".

## What the methods do

- **Idea.** InfEmbed and Domino cluster per-example explanations instead of raw features. If routes fail for the same reason, a pass/fail probe should lean on the same input directions to call them failing, even when their raw activations differ.
- **Input.** Each route's mean of layer 8 over its 50-frame window (`frames.npz`), standardised over all routes, then PCA 32 fit on all routes. This is m15's input.
- **Position removal.** This handles the m19 confound. A passing route's window ends at the route end and a failing route's window ends at the failure. Each window frame gets two positions from the cache's `step` array: log(step since start) and log(1 + steps to the route's end). Each route then takes the mean over its window. Directions that predict a position within either outcome are removed one at a time (iterative nullspace projection), until no position has cross-fitted ridge R² above 0.05. That took 13 of the 32 directions.
- **Probe.** An MLP (19 → 64 → 64 → 1) is trained with 5 folds over the salted row order. Every route is explained by a fold model that never saw it.
- **Attribution.** Each held-out route gets the logit's input gradient times its input, divided by its fold's attribution RMS. The columns are not standardised, for the toy reason in `VARIANTS.md`.
- **Axes.** Ward clusters the 174 failing routes at cuts 2, 3 and 5, in `axes_from` order. The result is pooled with whole-route L8 (m03), whole-route first.
- **j27.** It averages attribution over 10 probes per fold instead of 1.

## Why the window had to be fixed

The cache arrays have no window that sits at the same place for both outcomes and also covers the failure:

- `frames.npz` and the `cache-w50.npz` window both end at the failure or the route end.
- The whole-route summary runs past the failure on failing routes.
- The early window is at the same place for every route, but a logistic probe on it reaches pass/fail AUROC (area under the ROC curve) of only 0.679.

So j26 removes position from the approach window instead.

## Position-confound check

Label-free: this check reads only pass/fail and no gap key. It ran before the j26 row was committed. Output: `position-check.json`.

| | before removal | after removal (j26) |
|---|---:|---:|
| directions removed | 0 | 13 |
| failing routes: R² of log window-end step from probe inputs, ridge | 0.786 | 0.126 |
| same, boosted trees (nonlinear) | 0.795 | 0.588 |
| MLP out-of-fold pass/fail AUROC | 0.931 | 0.929 |
| share of log failure-step variance explained by failing clusters, cuts 2 / 3 / 5 | 0.052 / 0.070 / 0.224 | 0.008 / 0.044 / 0.057 |

For reference, m15's raw-window clusters explain 0.142 / 0.148 / 0.276 of that variance. Window-end step alone gives a pass/fail AUROC of 0.733.

- After removal, the clusters no longer sort routes by when they failed.
- The probe still separates pass from fail, so its signal was not mainly absolute position.
- Nonlinear position information remains (boosted R² 0.588). How much the MLP uses it is unverified.
- The binary "this window ends at the route end" cue cannot be removed without removing the outcome itself. That part of the m19 confound stays open.

## Scores

Measured, 2,000 replicates. The manifest is `results/h21/j18/manifest-pair-fixed.json`, which resamples 100 Fail2Drive pairs. The pool has 593 routes and 174 of them fail.

| row | score | CustomObstacles | Wall | PedestriansOnRoad | vs B3-behaviour | vs B3-infraction | tried |
|---|---:|---:|---:|---:|---|---|---|
| j26 | 0.280 | 0.232 | 0.529 | 0.079 | +0.128 [+0.011, +0.298], p 0.014 | −0.007 [−0.144, +0.187], p 0.45 | 230 + 1 |
| j27 | 0.269 | 0.210 | 0.529 | 0.068 | +0.117 [−0.011, +0.280], p 0.046 | −0.018 [−0.167, +0.161], p 0.53 | 230 + 2 |
| m23 (recorded, not rescored here) | 0.395 | 0.210 | 0.529 | 0.444 | | | |
| B3-behaviour | 0.152 | 0.191 | 0.165 | 0.101 | | | |
| B3-infraction | 0.287 | 0.394 | 0.200 | 0.267 | | | |

Failing-only chance is 0.124 for both rows. Recall at Jaccard 0.5 is 0.33 for both, and both have 0 decoy hits.

**Probe-seed spread for j26.** These are robustness reruns, not tries, at 200 replicates:

| probe seed | score | PedestriansOnRoad |
|---:|---:|---:|
| 0 (the j26 score) | 0.280 | 0.079 |
| 1 | 0.273 | 0.079 |
| 2 | 0.313 | 0.188 |
| 3 | 0.269 | 0.068 |

Seeds 0 to 3 span 0.269 to 0.313, a spread of 0.044. No seed reaches m23.

## Reading

- **j27's reason.** It is label-free and stored in `j27-reason.json`. j26's source axes shift with the probe seed: the mean best-match Jaccard between seeds is 0.57 to 0.69. The first Ward split is 25 / 149, 52 / 122, 58 / 116 and 72 / 102 for seeds 0 to 3. Averaging 10 probes per fold gave a 69 / 105 split. That tree matches the single-probe trees no better than they match each other (0.55 to 0.67), and it scored lower. Whether two 10-probe ensembles agree with each other was not run (unverified).
- **What the probe learns.** Both rows sit about 0.12 below m23 and are level with B3-infraction. The probe separates pass from fail well (AUROC 0.929), but what it uses does not split the failing routes by gap. PedestriansOnRoad stays near chance, where m23's raw window view reaches 0.444. On this pool, clustering by explanation loses the gap structure that clustering by activation keeps.
- **Where Wall and CustomObstacles come from.** Wall and most of CustomObstacles probably come from the whole-route source, as in j20 to j25. No per-axis attribution was run (unverified).

## Checks

- `route-L8`, `b3_behaviour` and `b3_infraction` were rebuilt here. Their axes equal `results/h21/h21b/axes/` exactly.
- After `--ensemble` was added, `j26_attr.py` at its defaults gives j26's axes exactly.
- `tests/test_j26_attr.py` has 5 tests:
  - the program reads only the frame and step keys;
  - it ignores label fields;
  - it gives the same output on a rerun;
  - it follows the cache-pool window rule;
  - it removes planted position directions;
  - on a toy, attributions recover the failure reasons where raw Ward splits on a nuisance, and standardised attributions do worse;
  - an ensemble of 1 equals the single probe.
- `scripts/check_sealed_imports.py` is clean.

## Files

- `commands.sh` holds every command, in order, including both label-free diagnostics.
- `axes/` holds the method, pool and rival axes.
- `seeds/` holds the probe-seed reruns.
- `report-j26.json` and `report-j27.json` are the scorer's reports.
- `position-check.json` and `j27-reason.json` hold the diagnostics.
