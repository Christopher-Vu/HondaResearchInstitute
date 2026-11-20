# j24 and j25: autoregressive surprise (exploratory, dev, H21b only)

Laptop worker 20261120-055958-30070, 2026-11-20. These are dev numbers. None of them can enter the UniAD read (`docs/prereg-views.md`, tag `views-prereg-v1`). No number here is significant, confirmed or a finding. Every score is measured on this laptop. Rows are in `VARIANTS.md` under "Exploratory, H21b pool, laptop j24-j25 (2026-11-20)".

## What the methods do

- **Shared start.** The method takes the last 50 frames of layer 8 from `frames.npz` (21 to 50 valid frames per route). It scales them by one root-mean-square and projects them with unwhitened PCA 16 over every frame of every route. This is j09's projection.
- **The model.** One ridge vector autoregression of order 2 (VAR(2)) is fit on all 593 routes' frames, with no labels. It predicts each frame from the two frames before it (sklearn `Ridge`, alpha 1.0, intercept not penalised). The residual at a frame is the observed frame minus the predicted one. It is the part of the move that the shared dynamics did not expect.
- **j24.** Each route gets two blocks. The first is the mean residual vector over its last 10 frames (16 numbers, the direction of surprise). The second is the residual size profile: mean size, maximum size, and the mean of the last 10 sizes minus the mean of the first 10. Each block is standardised over all routes and divided by the square root of its width, as m06 does. Ward clusters the failing routes at cuts 2, 3 and 5, in `axes_from` order. The result is pooled with whole-route L8 (m03), whole-route first.
- **j25.** It uses the same model and keeps only the direction. The late mean residual vector stays in the PCA space, with no per-dimension scaling and no centring, and is scaled to unit length. Ward then groups routes by where the surprise points, not by how large it is. It is pooled the same way.
- **How this differs from earlier temporal rows.** j16 and j17 measured step sizes and net displacement. j09 measured which hidden states a route occupies. m30 fit a per-route trend. j24 and j25 instead describe a route by what a learned predictive model of all driving got wrong.

## Scores

Measured, 2,000 replicates. `pair` is stripped of its `-sNN` suffix (`results/h21/j18/manifest-pair-fixed.json`), so the bootstrap resamples 100 Fail2Drive pairs. There are 593 routes and 174 of them fail.

| row | score | CustomObstacles | Wall | PedestriansOnRoad | vs B3-behaviour | vs B3-infraction | tried |
|---|---:|---:|---:|---:|---|---|---|
| j24 | 0.269 | 0.210 | 0.529 | 0.068 | +0.117 [−0.003, +0.287], p 0.029 | −0.018 [−0.157, +0.167], p 0.50 | 224 + 1 |
| j25 | 0.272 | 0.210 | 0.529 | 0.077 | +0.120 [−0.009, +0.283], p 0.035 | −0.015 [−0.165, +0.165], p 0.52 | 224 + 2 |
| m23 (recorded, not rescored here) | 0.395 | 0.210 | 0.529 | 0.444 | | | |
| B3-behaviour | 0.152 | 0.191 | 0.165 | 0.101 | | | |
| B3-infraction | 0.287 | 0.394 | 0.200 | 0.267 | | | |

Failing-only chance is 0.122 for j24 and 0.123 for j25. Recall at Jaccard 0.5 is 0.33 for both, and both have 0 decoy hits.

**Ridge alpha robustness for j24 (not tries, 200 replicates).** Alpha 0.3 and alpha 3.0 give the same axes as alpha 1.0, so the score is 0.269 at all three, with a spread of 0.000 (measured). The fit has about 27,000 frame pairs against 33 inputs, so a penalty of this size barely moves the coefficients.

## Reading

- The autoregression predicts the next projected frame well. One-step R² is 0.896 over all frames (measured, in-sample).
- The residual size rises over the last frames of failing routes and stays flat on passing routes. In the last 12 frames the mean size goes from 2.39 to 3.29 on failing routes and stays between 2.24 and 2.45 on passing ones (measured). Surprise does carry a failure signal, but this signal is about pass or fail, not about which gap.
- Both rows sit below m23 by about 0.12, and neither is separated from B3-infraction. CustomObstacles and Wall equal m23's values. Five of each pooled top 10 come from the whole-route view, which probably supplies those two gaps. No per-axis attribution was run, so this is unverified.
- PedestriansOnRoad stays near chance (0.068 and 0.077), where m23's window view reaches 0.444. This is the same pattern as j16 and j17.
- **Why j25 was tried.** j24's first Ward split (89 / 85 failing routes) was carried by the 3-number size block. That block's between-split share was 0.459, against 0.010 for the 16-number direction block (measured, label-free). So j24 split by how much surprise there was. j25 tested the direction alone and moved PedestriansOnRoad by 0.009. A shared direction of surprise does not pick out these gaps on this pool.
- The temporal lane keeps j09 (0.298) as its best on H21b. Two kinds of temporal summary have now fallen short of where the state sits in the window: change rates (j16, j17) and prediction residuals (j24, j25).

## Checks

- `route-L8`, `b3_behaviour` and `b3_infraction` were rebuilt here from `results/savio/f2d-h21b/pool/`. Their axes equal `results/h21/h21b/axes/` exactly.
- After the edit that added `--direction-only`, `j24_ar.py` at its defaults gives j24's axes exactly.
- A second full run of `commands.sh` reproduced `report-j24.json` and `report-j25.json` byte for byte.
- `tests/test_j24_ar.py` has 4 tests. They cover reading only the frame keys, ignoring label fields, determinism, the lag construction, a toy where j24 splits kicked from unkicked routes, and a toy where j25 splits by direction while j24 splits by size.

## Files

- `commands.sh` holds the exact commands, including the label-free diagnostic behind j25.
- `axes/` holds the method, pool and rival axes.
- `report-j24.json` and `report-j25.json` are the scorer's reports.
- `alpha/` holds the ridge alpha check.
