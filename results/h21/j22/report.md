# j22 and j23: a per-frame sparse dictionary read late versus early (exploratory, dev, H21b only)

Laptop worker 20261120-055955-27931, 2026-11-20. These are dev numbers. None of them can enter the UniAD read (`docs/prereg-views.md`, tag `views-prereg-v1`). No number here is significant, confirmed or a finding. Every score is measured on this laptop. Rows are in `VARIANTS.md` under "Exploratory, H21b pool, laptop j22-j23 (2026-11-20)".

## What the methods do

- **Prior dictionary work.** m14 trained a top-64 dictionary on 6-frame windows and read it with B7's statistics. It scored 0.000, because those statistics fail on short episodes. j22 does not use B7's statistics or B7-pool.
- **j22.** It reads `frames.npz`, layer 8, using every valid frame of every route (21 to 50 frames per route, right-aligned).
  - Each unit is standardised over all frames. PCA 32 is fit on all frames, and the scores are divided by their global root-mean-square.
  - `MiniBatchDictionaryLearning` learns 64 atoms with alpha 1.0, batch 256, 20 epochs and `random_state` 0. The codes come from lasso_lars at alpha 1.0.
  - Two statistics are computed per route and atom. The first is the mean absolute code over the last 10 frames minus the mean over the earlier frames. The second is the share of the last 10 frames where the atom is active.
  - The 128 columns are standardised over all routes. The failing routes are Ward-clustered at cuts 2/3/5, ranked by cut and then by size (m15's label-free order), and the top 10 are kept.
  - The result is pooled with whole-route L8 (m03), with the whole-route view first.
- **j23.** It is j22 with the 64 active-share columns dropped (`--columns change`).
- **The fit (measured, label-free).** The codes use 3.48 atoms per frame on average over 29,279 frames. No frame has an empty code, and every atom is used. Training takes 12 s on CPU.

## Scores

Measured, 2,000 replicates, `pair` stripped of its `-sNN` suffix, so 100 Fail2Drive pairs are resampled. There are 593 routes and 174 of them fail.

| row | score | CustomObstacles | Wall | PedestriansOnRoad | vs B3-behaviour | vs B3-infraction | tried |
|---|---:|---:|---:|---:|---|---|---|
| j22 | 0.286 | 0.210 | 0.529 | 0.120 | +0.134 [+0.006, +0.297], p 0.019 | −0.000 [−0.146, +0.172], p 0.46 | 224 + 1 |
| j23 | 0.269 | 0.210 | 0.529 | 0.068 | +0.117 [−0.015, +0.283], p 0.047 | −0.018 [−0.167, +0.165], p 0.54 | 224 + 2 |
| m23 (recorded, not rescored here) | 0.395 | 0.210 | 0.529 | 0.444 | | | |
| B3-behaviour | 0.152 | 0.191 | 0.165 | 0.101 | | | |
| B3-infraction | 0.287 | 0.394 | 0.200 | 0.267 | | | |

The failing-only chance is 0.125 for j22 and 0.122 for j23. Recall at Jaccard 0.5 is 0.33 for both. j22 has a decoy hit rate of 0, and j23 has 0.1.

**Dictionary seed robustness for j22 (not tries, 200 replicates).** Seed 0 scores 0.286. Seeds 1, 2 and 3 score 0.304, 0.289 and 0.301, so the spread over seeds 0 to 3 is 0.286 to 0.304. CustomObstacles stays at 0.210 to 0.218 and Wall at 0.529. PedestriansOnRoad moves between 0.120 and 0.171. Against B3-infraction, p is 0.42 to 0.48 for every seed.

## Reading

- Both rows sit below m23 and are level with B3-infraction.
- CustomObstacles and Wall equal m23's values. These two gaps are probably matched by the shared whole-route source. No per-axis attribution was run, so this is unverified.
- The dictionary view does not find the pedestrian group: 0.120 here against m23's window view at 0.444.
- **Why j23 was tried (from j22's outputs, no key read).** j22's cuts sort the failing routes by speed over the last 10 frames. At cut 2, the 40-route group has a mean late speed of 16.7 and the 134-route group 7.1. The leading principal component of the share block correlates with late speed at r 0.53, and the change block's at r 0.17. Speed is what B3-behaviour already reads.
- Dropping the share columns made things worse. The change columns alone split the failing routes 149 against 25 at the first cut, so they give mostly large groups.

## Checks

- `route-L8`, `b3_behaviour` and `b3_infraction` were rebuilt here from `results/savio/f2d-h21b/pool/`. Their axes equal the recorded ones (`results/h21/h21b/axes/route-L8.json`, `results/h21/j18/axes/b3_*.json`).
- The stripped-pair manifest is a copy of `results/h21/j18/manifest-pair-fixed.json`, which has 100 distinct pairs.
- After `--columns` was added, `j22_dict.py` at its defaults reproduces j22's axes exactly.
- `bash results/h21/j22/commands.sh all` was rerun from scratch. All five reports came out byte-identical to the first run.

## Files

- `commands.sh` holds the exact commands, in the parts `inputs`, `j22`, `seeds` and `j23`. Run it with bash, not zsh, because zsh does not split the option variables.
- `axes/` holds the method, source, pool and rival axes.
- `report-j22.json` and `report-j23.json` are the scorer's reports.
- `seeds/` holds the seed check.
- `manifest-pair-fixed.json` is the manifest with the seed suffix stripped from `pair`.
