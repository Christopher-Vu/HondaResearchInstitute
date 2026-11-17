# Fail2Drive dev search on SimLingo: every variant tried

Chris, 2026-11-12: iterate freely on SimLingo's Fail2Drive test pool, log every variant here as it is submitted,
report what we have at any point. The working target is (b): an activation method beats B3 (behavioural) on the
B4-unnamed gaps. TransFuser++'s test pool is the held-out confirmation, scored once after the method is frozen.
Budget 800 SU.

Pool: `results/savio/f2d-test-simlingo/` (1,188 scored routes). Gaps (pre-registered classification,
`docs/prereg-fail2drive.md`): PedestriansOnRoad, FullyBlocked, BadParking, all B4-unnamed (`b4-split.json`).
CustomObstacles (background, open post hoc decision) and Wall (ceiling) are scored beside them for reference.
Scores choose the best axis using the gap's failing set (as H22).

| id | date | change from H22 | job | SU | result |
|---|---|---|---|---|---|
| v1 | 2026-11-12 | none but the pool: H22's pipeline, layer 10, plain/centre/vision, 18 dictionaries; M1 floor 20 (H22) and 5 (as H23's direction) | 41303112 (41302236 cancelled: our venv lacked sklearn, and per-dictionary reloads were too slow) | | ~64 (plus ~18 for the cancelled run) | `not_ahead` (measured). M1 mean best 0.158 plain, 0.134 centre, 0.135 vision against B3 0.317; the floor changed nothing. B7 (activation statistics) beats B3 on FullyBlocked (0.458 plain vs 0.188) and BadParking (0.269 vision vs 0.188), near B3 on PedestriansOnRoad (0.545 centre vs 0.564). B2 scores 1.000 on PedestriansOnRoad: a route field names the type, so B2 is not a fair comparator here |
| v2 | 2026-11-14 | H24's error-aware Gaussian mixture on layer-10 activations (Jerry's code unchanged), on our pool's larger gaps (17 to 24 failing routes, against H21's 3 to 8); CPU export (`h24_export.sbatch`), mixture and scoring on a laptop, B3 from v1 | 41303096 (41302252 failed: no sklearn) | ~2 | `not_ahead` on every arm (measured): H24_act median delta -0.074; best per gap 0.25 / 0.13 / 0.15 on PedestriansOnRoad / FullyBlocked / BadParking |

## Discovery sprint (`docs/prd-discovery-sprint.md`), from 2026-11-14

Rows above v1 and v2 use the old scoring (best axis chosen with the key). From here every row is scored by the sprint
rule (§4 of the sprint PRD): each method ranks its own axes, its top 10 are scored, p values from the route bootstrap
against each rival. v1 and v2 are rescored under it before comparison.

### Checks before the loop (sprint PRD §5), 2026-11-14

1. **Cached per test pool** (measured, Savio): `results/savio/f2d-test-simlingo/shards` and `f2d-test-tfpp/shards`
   (2,400 files each side, a json and an npz per route). SimLingo's npz holds, per captured frame (every 10 steps, up
   to 100 frames): `all_tokens` and `driving_queries` mean-pooled at **all 24 layers**, `vision_bridge`, the layer 10
   and 11 driving-query tokens, ego speed and position, and simulator distances (privileged, never a method input).
   The json holds status, infractions and first collision step. **No camera frames were saved on either pool**, so
   caption methods, the caption hybrid and image-embedding grouping (B5) are dropped for now (Chris, 2026-11-14).
   Steering and braking are not in the shards; whether B3-behaviour can get them is checked when it is built.
2. **Route markers:** every SimLingo and TF++ test config sets `debug_level: 0`, so no route or trigger markers were
   drawn. No marker check is needed.
3. **TransFuser++ unread:** no method or score has read `f2d-test-tfpp/shards`. Its `routes.jsonl` was read once, for
   the pre-registered gap classification only.
4. **Fast loop:** one CPU pass writes per-route summaries (route mean, approach-window mean, early-route mean, for
   every layer and site) to a single cache file, so a method reads about 0.6 GB instead of 44 GB. Dictionary methods
   train 2 or 3 dictionaries on dev; the full grid of 18 is for finalists only.

### Approved batch 1 (Chris, 2026-11-14: "lets approve the next 7 methods")

Approach window: the last 6 captured frames (about 3 s) before the first collision step, or before the route ends
when there is none. Using the failure time uses the pass/fail outcome, which a fleet has; the failure type stays hidden.

| id | method | rivals compared |
|---|---|---|
| m01 | error-aware B7: B7's latents ranked by kappa times their enrichment in failing routes, axes from failing fire sets; layer 10, 2 dictionaries | B1, B3-behaviour, B4, B7, B7-pool |
| m02 | m01 on approach-window frames only | same |
| m03 | failing-route clustering of approach-window activations: PCA fitted on all routes, failing routes clustered (agglomerative and HDBSCAN), clusters ranked by size times cohesion; no dictionary | same |
| m04 | error-aware embedding (Domino-style): a pass/fail probe on window activations picks the components that separate failure, failing routes clustered in that subspace | same |
| m05 | layer and site sweep of the best of m01 to m04 over 24 layers of `all_tokens` and `driving_queries`, plus `vision_bridge` | same |
| m06 | best so far plus fleet-observable kinematics (the B3-behaviour features) as extra inputs | same |
| m07 | change before failure: window mean minus the route's own early mean, then m03's clustering | same |

| id | date | job | SU | score (top-10 mean best Jaccard) | p vs B3-behaviour / best rival | methods tried |
|---|---|---|---|---|---|---|
| v1 rescored | 2026-11-14 | 41325904 | <0.1 | M1 (capped and raw, `L10_k64_s0`) 0.077; M2 0.000 | vs B3-behaviour: M1 −0.016 [−0.105, 0.082], p 0.59 | 3 |
| m03 | 2026-11-14 | 41325929 | <0.1 | **0.180** (PedestriansOnRoad 0.242, FullyBlocked 0.132, BadParking 0.167) | **+0.087 [0.030, 0.152], p 0.0005** / vs best rival (B7-pool) −0.007 [−0.164, 0.114], p 0.47 | 6 |
| m04 | 2026-11-14 | 41325929 | (same job) | 0.120 (0.140 / 0.092 / 0.129) | +0.027 [−0.010, 0.093], p 0.099 / −0.067, p 0.81 | 6 |
| m07 | 2026-11-14 | 41325929 | (same job) | 0.134 (0.143 / 0.122 / 0.137) | +0.041 [−0.008, 0.148], p 0.048 / −0.053, p 0.63 | 6 |
| m06 (m03 + kinematics) | 2026-11-14 | 41325929 | (same job) | 0.145 (0.196 / 0.088 / 0.149) | +0.051 [−0.003, 0.115], p 0.035 / −0.043, p 0.64 | 6 |

Rivals under the sprint rule (measured, same pool): **B3-behaviour 0.093** (0.082 / 0.054 / 0.143); **B7-pool
`L10_k64_s0` 0.187** (0.200 / 0.333 / 0.028). All dev numbers. m03 to m07 use layer 10 of `driving_queries`, the
approach-window summary, PCA to 32 dimensions and Ward cuts 2, 3 and 5. The cache (job 41320891, 13 min on 4 CPUs,
about 1 SU) holds 1,185 routes, 357 failing. B3-behaviour ran in job 41325903.

| m05 | 2026-11-14 | 41325979 | <0.5 | m03 at 49 site and layer settings. Best: `driving_queries` L7 and L8 **0.253** (PedestriansOnRoad 0.59, FullyBlocked 0.07, BadParking 0.09); most even: L20 0.209 (0.31 / 0.14 / 0.18) and L5 0.189 (0.23 / 0.16 / 0.18); best on FullyBlocked: `all_tokens` L1 0.195 (0.14 / **0.35** / 0.10) | L8 vs B3-behaviour p 0.048; L20 p 0.002; L5 p 0.0005 (exploratory, 55 tried) | 55 |
| m01 | 2026-11-14 | 41325980 | ~0.7 | `L10_k64_s0` 0.187 (0.200 / 0.333 / 0.026), the same axes as B7-pool in effect: enrichment did not reorder the latents that matter; `L10_k32_s0` 0.109 | k64: +0.093 [−0.073, 0.236], p 0.16 | 59 |
| m02 | 2026-11-14 | 41325980 | (same job) | `L10_k64_s0` 0.010; `L10_k32_s0` 0.070. B7's firing statistics need whole routes; 6 frames are too few | k64: p 1.0 | 59 |

Batch 1 is finished and scored (measured, dev, 59 configurations tried). Different layers carry different gaps, so
batch 2 starts from combining layers.

### Approved batch 2 (Chris, 2026-11-14: "move onto the 2nd batch if it wont hog gpu space"), all on CPU

| id | date | job | SU | score (top-10 mean best Jaccard; PedestriansOnRoad / FullyBlocked / BadParking) | p vs B3-behaviour / delta and p vs best rival | methods tried |
|---|---|---|---|---|---|---|
| m08 | 2026-11-14 | 41326946 | <0.1 | `driving_queries` L5+L8+L20 concatenated: **0.306** (0.59 / 0.15 / 0.18); L1+L5+L8+L20: 0.157 (0.15 / 0.13 / 0.19) | L5+8+20: p 0.004 / **+0.119, p 0.13** | 71 |
| m09 | 2026-11-14 | 41326946 | (same job) | axes pooled round-robin from m03 at L8, L20, L5 and `all_tokens` L1: 0.212 (0.38 / 0.07 / 0.18) | p 0.022 / +0.025, p 0.36 | 71 |
| m10 | 2026-11-14 | 41326946 | (same job) | m03 L8 and B7-pool pooled: 0.203 (0.38 / 0.13 / 0.09) | p 0.031 / +0.016, p 0.39 | 71 |
| m12 | 2026-11-14 | 41326946 | (same job) | clustering in place of Ward. L10: average 0.132, complete 0.163, spectral 0.151. L8: average **0.301** (0.59 / 0.05 / 0.26), complete 0.236 (0.27 / 0.21 / 0.22, the most even so far), spectral 0.146 | L8 average: p 0.035 / +0.114, p 0.17; L8 complete: p 0.073 / +0.049, p 0.28 | 71 |
| m13 | 2026-11-14 | 41326946 | (same job) | Ward cuts at L10: 4+6 0.180; 10 0.200 (0.27 / 0.14 / 0.18) | cuts 10: p <0.001 / +0.013, p 0.21 | 71 |
| m11 | 2026-11-14 | 41326947 | ~1.6 (three cache passes) | approach window of 3, 10 or 20 frames (6 before). L10: 3 → 0.183, 10 → 0.246, 20 → **0.310** (0.59 / 0.10 / 0.24). L8: 3 → 0.163, 10 → 0.295, 20 → 0.304 (0.59 / 0.09 / 0.23). Longer windows help | w20 L10: p 0.0005 / +0.123, p 0.13; w20 L8: p 0.0005 / +0.117, p 0.12 | 77 |
| m14 | 2026-11-14 | 41326948 | ~0.6 | a top-64 dictionary trained on 6-frame window frames, then B7-pool and the error-aware ranking: **0.000** for both. B7's statistics fail on 6-frame episodes, as m02 did | p 1.0 | 79 |

Batch 2 finished (measured, dev, 79 configurations tried). Leads: m11 w20 L10 0.310, m08 L5+8+20 0.306, m12 L8
average linkage 0.301. Every lead's margin comes from PedestriansOnRoad (0.59); no method is ahead of B7-pool on
FullyBlocked (0.333). `chance_B1` in reports before 2026-11-15 drew from all routes and read too low (Jerry's agent);
deltas and p values never used it.

### Approved batch 3 (Chris, 2026-11-15: "go on batch 3"), all on CPU

Every row is also compared with **B3-infraction** (m21, below), a proposed second fleet rival. Window `wN` is the last N
captured frames before the failure step.

| id | date | job | SU | score (PedestriansOnRoad / FullyBlocked / BadParking) | p vs B3-behaviour / delta and p vs B3-infraction / vs best rival | methods tried |
|---|---|---|---|---|---|---|
| m21 | 2026-11-15 | 41370706 | <0.1 | **B3-infraction** (rival): one axis per infraction type, failing routes only, largest first: **0.192** (0.35 / 0.06 / 0.16). Twice B3-behaviour's 0.093, level with B7-pool's 0.187 | — | 80 |
| m15 | 2026-11-15 | 41370706, 41370707 | ~1.2 (two cache passes) | L10: w30 0.282, w50 0.272; **L8 w50 0.312** (0.59 / 0.17 / 0.17), w30 0.265. Whole route: L10 0.126, L8 0.227 (0.08 / **0.35** / 0.25) | L8 w50: p 0.014 / +0.119, p 0.14 / p 0.19 | 86 |
| m16 | 2026-11-15 | 41370706, 41370707, 41371173 | <0.1 | L5+8+20: w10 0.247, w20 **0.304** (0.59 / 0.09 / 0.23), w30 0.280, w50 0.259 | w20: p <0.001 / +0.111, p 0.15 / p 0.15 | 90 |
| m17 | 2026-11-15 | 41370706 | (same job) | on w20: Ward cuts 10 0.310 (same as m11 w20); average linkage 0.061, complete 0.078, L5+8+20 average 0.061. Average linkage helped at w6 L8 (m12) and hurts at w20 | cuts 10: p <0.001 / +0.118, p 0.069 / p 0.11 | 94 |
| m18 | 2026-11-15 | 41370706, 41370708 | ~0.4 | for FullyBlocked, on w20: `all_tokens` L0 0.278 (0.59 / 0.13 / 0.11), L1–L3 and `vision_bridge` 0.254 each; B7-pool on w20 0.063 and w50 0.101 (0.07 / 0.20 / 0.03). Nothing beats B7-pool's 0.333 on FullyBlocked except the whole-route L8 summary (m15, 0.35) | `all_tokens` L0: p 0.028 / +0.086, p 0.22 | 101 |
| m19 | 2026-11-15 | 41370706 | (same job) | three layers chosen by pass/fail probe AUROC: `driving_queries` L10, L22, L23 → 0.277; `all_tokens` L14, L15, L17 → 0.254. The AUROCs are ~0.99 because a passing route's window ends at the route's end and a failing route's at the failure, so the probe reads window position, not anything useful; the layer choice is uninformative | 0.277: p 0.010 / +0.084, p 0.19 | 103 |
| m20 | 2026-11-15 | 41370706 | (same job) | pooled round-robin: m11 w20 L10 with `all_tokens` L1 0.310 (unchanged from m11); with B7-pool 0.289 (0.59 / 0.13 / 0.14) | first: p <0.001 / +0.118, p 0.093 | 104 |

Batch 3 finished (measured, dev, 104 configurations tried). The leads stand at about 0.31 (m15 L8 w50 0.312, m11 w20
L10 0.310, m16 w20 0.304). **Against B3-infraction, the stronger fleet rival, every lead is ahead by about +0.11 to
+0.12, p 0.07 to 0.15: not separated on dev.** All of it is PedestriansOnRoad: the leads' pedestrian axis is 13
routes, every one from the gap (Jaccard 0.591, 13 of the gap's 22). A failure-timing check rules out the obvious
artefact: grouping failures by how early they happened scores Jaccard 0.05 or less on every gap (diagnostic,
scoring side). In the first batch 3 report two earlier leads shared names with new runs and one overwrote the other;
m16 w20 was rescored on its own (41371173).


### Jerry's explore loop (`j` methods), H21 pool (2026-11-15)

Second SimLingo dev pool: Jerry's H21 run, all 100 Fail2Drive pairs, seed 24, 200 routes, 52 failing. One layer
only (`driving_queries` L10, approach-window mean, from `results/savio/h24-h25/f2d-features.npz`), so every
fractional layer lands on it. Gaps F2D_CustomObstacles (8 failing), F2D_Wall (5), F2D_PedestriansOnRoad (3); decoys as
batch 1. Its categories were already read by H22 to H25. It can rank and kill methods; on its own it cannot make a
candidate. Cache and kin-only B3-behaviour stand-in from `h21_cache.py`. Rivals: B3-behaviour (kin only), m03 at L10
(Chris's m08 reduced to the one layer available). Rows are written before the scores are read.

| id | date | pool | settings | score (top-10 mean best Jaccard; CustomObstacles / Wall / PedestriansOnRoad) | p vs B3-kin / vs best rival | methods tried (all pools) |
|---|---|---|---|---|---|---|
| j01 | 2026-11-15 | H21 | unwhitened PCA 32, Ward 2/3/5, commit `b8a3e5a` | 0.231 (0.31 / 0.27 / 0.11); chance 0.077 | -0.095 [-0.204, +0.067], p 0.84 / -0.095, p 0.89 | 75 |
| j02 | 2026-11-15 | H21 | cPCA, pre-dims 32, dims 8, alpha picked 0.1, Ward 2/3/5 | 0.297 (0.30 / 0.36 / 0.22); chance 0.079 | -0.029 [-0.136, +0.102], p 0.65 / -0.029, p 0.71 | 75 |
| j03 | 2026-11-15 | H21 | m03 embedding, Ward 8/12/16, size band (5, 6): 2 axes only | 0.108 (0.18 / 0.00 / 0.14); chance 0.028 | -0.217 [-0.413, -0.047], p 0.99 / -0.217, p 0.99 | 75 |
| j04 | 2026-11-15 | H21 | passing-covariance whitening, pre-dims 32, dims 8, ridge 0.02, Ward 2/3/5 | 0.193 (0.24 / 0.14 / 0.20); chance 0.090 | -0.132 [-0.270, +0.043], p 0.92 / -0.132, p 0.97 | 75 |

Rivals on H21 under the sprint rule (measured): **B3-behaviour (kin only) 0.326** (0.46 / 0.33 / 0.18); m03 L10 0.242 (0.23 / 0.17 / 0.33). 4 `j` methods scored on H21; 75 tried in total. No `j` method leads. One route in a 3-route gap moves its Jaccard by about 0.1: j01 and j02 differ by 0 to 5 routes on 8 of their 10 axes and score 0.231 against 0.297. Report `results/h21/report-round5.json`.

B1 drawn from failing routes only, as `src/baselines/random_baseline.py` defines it, is 0.17 to 0.18 for every 10-axis method on H21, not the 0.03 to 0.09 in the chance column above (measured; see `docs/WHAT_BROKE.md`, 2026-11-15). Only B3-kin and j02 are clearly above it.

| id | date | pool | settings | score (top-10 mean best Jaccard; CustomObstacles / Wall / PedestriansOnRoad) | p vs B3-kin / vs best rival | methods tried (all pools) |
|---|---|---|---|---|---|---|
| j05 | 2026-11-15 | H21 | unwhitened PCA 32 on all routes, minus the mean of the 10 nearest passing routes, Ward 2/3/5, commit `675c706` | 0.183 (0.23 / 0.17 / 0.14); chance 0.073, failing-only 0.187 | -0.143 [-0.278, -0.005], p 0.98 / -0.143, p 1.00 | 76 |
| j06 | 2026-11-15 | H21 | j01 after removing the OLS prediction of the activations from the 4 standardised `kin` columns (fit on all routes, no failure label); unwhitened PCA 32, Ward 2/3/5, commit `fa37c30` | 0.246 (0.36 / 0.25 / 0.13); chance 0.082, failing-only 0.181 | -0.079 [-0.194, +0.061], p 0.84 / -0.079, p 0.90 | 77 |
| j07 | 2026-11-15 | H21 | failing routes Ward-cut into 2 strata on standardised `kin` (the B3-kin cut-2 groups, 39 / 13), then j01's unwhitened PCA 32 (all routes) Ward-clustered within each stratum at cuts 2 and 3; 10 axes, stratum 1 first, commit `3046624` | 0.241 (0.31 / 0.27 / 0.14); chance 0.083, failing-only 0.192 | -0.084 [-0.214, +0.143], p 0.72 / -0.084, p 0.75 | 78 |

On H21's one layer (L10), every activation method so far, `j` or m03, scores between failing-only chance (0.18) and 0.30, and the four-number kin rival scores 0.326 (measured, 6 `j` methods scored on H21, 77 tried in total; j06 removes the speed-linear part first and still scores 0.246). L10 was a middling layer on Chris's pool too (m05 sweep), so H21 at L10 is a weak test of an activation method.

j07 (stratify on kin, then cluster activations within each stratum) scores 0.241, the same per category as j01 within noise (0.31 / 0.27 / 0.14 against 0.31 / 0.27 / 0.11), and below B3-kin (measured, 7 `j` methods scored on H21, 78 tried in total). Linear (j06) and hard nonlinear (j07) conditioning on speed both leave L10 activation clusters at 0.24 to 0.25, about 0.05 above failing-only chance.

### Jerry's explore loop (`j` methods), Chris's sprint pool (2026-11-16)

Chris's SimLingo sprint cache (`cache.npz`, 6-frame window, 1185 routes), gaps PedestriansOnRoad, FullyBlocked,
BadParking, decoys as batch 1, scored with `sprint_score.py` under amendment a1 against B3-behaviour, B7-pool, m08 and
B3-infraction. Run by `~/autoresearch/queue/queue.sh` from commit `db3b0a0`, each method at its file's defaults
(`driving_queries`, layers at fractions 5/23, 8/23, 20/23 of depth = L5, L8, L20, window summary). j06 and j07 run
only if the kin diagnostic's max R² is at least 0.25; otherwise they are not tried here. Rows are written before the
scores are read.

| id | date | pool | settings | score (PedestriansOnRoad / FullyBlocked / BadParking) | p vs B3-behaviour / B7-pool / m08 / B3-infraction | methods tried |
|---|---|---|---|---|---|---|
| j04 | 2026-11-16 | sprint | passing-covariance whitening, pre-dims 32, dims 8, ridge default, Ward 2/3/5 | 0.194 (0.24 / 0.16 / 0.18); failing-only chance 0.081 | +0.101, p <0.001 / not scored / -0.112, p 0.91 / +0.002, p 0.50 | 112 |
| j02 | 2026-11-16 | sprint | cPCA, pre-dims 32, dims 8, alpha by eigengap, Ward 2/3/5 | 0.198 (0.27 / 0.15 / 0.17); chance 0.081 | +0.105, p <0.001 / not scored / -0.108, p 0.87 / +0.006, p 0.43 | 113 |
| j03 | 2026-11-16 | sprint | m03 embedding at L5, L8, L20 and `all_tokens` L1, Ward 8/12/16, size band, ranked by cohesion, round-robin | 0.052 (0.03 / 0.00 / 0.13); chance 0.078 | -0.041, p 0.82 / not scored / -0.255, p 0.99 / -0.141, p 0.99 | 114 |
| j05 | 2026-11-16 | sprint | unwhitened PCA 32, minus mean of 10 nearest passing routes, Ward 2/3/5 | **0.284** (0.45 / **0.23** / 0.16); chance 0.078 | +0.191 [+0.062, +0.318], p <0.001 / not scored / -0.022 [-0.192, +0.102], p 0.59 / +0.091 [-0.051, +0.232], p 0.12 | 115 |
| j06 | 2026-11-16 | sprint | gate passed (max kin R² 0.269 at L5): OLS residual on behaviour features, then j01 | 0.165 (0.30 / 0.08 / 0.12); chance 0.083 | +0.072, p 0.015 / not scored / -0.141, p 0.95 / -0.027, p 0.59 | 116 |
| j07 | 2026-11-16 | sprint | gate passed (max kin R² 0.269 at L5): 2 behaviour strata, then j01 within each, cuts 2/3 | 0.196 (0.32 / 0.11 / 0.16); chance 0.083; strata 263 / 94 | +0.102, p <0.001 / not scored / -0.111, p 0.86 / +0.003, p 0.28 | 117 |

Scored 2026-11-16 (measured, dev, 117 tried in total: 104 Chris + 13 `j` tries across both pools). The B7-pool directives
directory was not in the copy, so B7-pool is not a rival in these reports (Chris's B7-pool: 0.187, FullyBlocked
0.333). The rebuilt rivals match Chris's numbers: B3-behaviour 0.093, m08 0.306, B3-infraction 0.192. **No `j` method
leads m08.** j05 is closest (0.284, -0.022 vs m08, p 0.59). Its FullyBlocked best (0.234) is above m08's (0.149)
and m15 L8 w50's (0.17), below `all_tokens` L1 (m05, 0.35) and B7-pool (0.333); it gives up PedestriansOnRoad (0.45
against 0.59). Its result reproduces exactly on a second run. Report and log:
`results/savio/f2d-dev/simlingo/sprint/queue/`, `queue.log`.

j11 (row written before scoring): j05 with each failing route's residual scaled to unit length before Ward, so
clusters form on the direction a failure leaves its local passing neighbours, not on how far. Reason: on the sprint
pool j05 is the closest `j` method to m08, and residual length mixes scene density with failure kind. Same defaults
as j05 (k 10, pre-dims 32, L5+8+20 window; L10 on H21). One change from j05, no other setting tried.

| id | date | pool | settings | score | p vs rivals | methods tried |
|---|---|---|---|---|---|---|
| j11 | 2026-11-16 | sprint | j05 residuals scaled to unit length, Ward 2/3/5, commit `3a0a57f` | 0.187 (0.31 / 0.14 / 0.11); chance 0.082 | B3-behaviour +0.093, p 0.002 / m08 -0.120, p 0.91 / B3-infraction -0.006, p 0.47 | 118 |
| j11 | 2026-11-16 | H21 | same, L10 (CustomObstacles / Wall / PedestriansOnRoad) | 0.261 (0.46 / 0.23 / 0.09); failing-only chance 0.184 | B3-kin -0.064, p 0.73 / m03 L10 +0.019, p 0.30 | 119 |

j11 is worse than j05 on the sprint pool (0.187 against 0.284) and better on H21 (0.261 against 0.183), below the
best rival on both (measured, dev, 119 tried in total). Residual length carries signal on the sprint pool; j11 is
dropped. Grok's j11 and an independent reimplementation (own kNN via scikit-learn) give the same 10 route sets on both
pools.

j12 (rows written before scoring; density/mixture lane): a background model of passing routes only. One unwhitened
PCA 32 on all routes (as j05). A Gaussian mixture (full covariance, `reg_covar` 1e-3 times the mean passing score
variance, 5 inits, seed 0) is fit on passing routes' scores alone, with the component count picked by BIC over 1 to 6
on those passing routes; no failure kind is read. Each failing route's residual is its score minus the
responsibility-weighted mean of the components, not whitened (j04's global whitening and j11's unit length both lost
to j05's raw residual, so residual size is kept). Ward 2/3/5. Reason: tests whether j05's gain comes from a local
background (10 nearest passing routes) or from any background-mode subtraction; if BIC picks 1 component, j12 is a
translation of j01 and Ward gives j01's axes. Same layers as j05 (L5+8+20 window; L10 on H21). One setting, no sweep.

| id | date | pool | settings | score | p vs rivals | methods tried |
|---|---|---|---|---|---|---|
| j12 | 2026-11-16 | sprint | passing-only GMM (BIC 1-6, picked K 5) responsibility-mean residual, PCA 32, Ward 2/3/5, commit `bd3db40` | 0.182 (0.17 / 0.21 / 0.16); failing-only chance 0.081 | B3-behaviour +0.089, p <0.001 / m08 -0.125, p 0.89 / B3-infraction -0.011, p 0.54 | 120 |
| j12 | 2026-11-16 | H21 | same, L10 (picked K 3) (CustomObstacles / Wall / PedestriansOnRoad) | 0.209 (0.29 / 0.25 / 0.09); failing-only chance 0.189 | B3-kin -0.117, p 0.85 / m03 L10 -0.033, p 0.42 | 121 |

j12 is below the best rival on both pools (measured, dev, 121 tried in total: 104 Chris + 17 `j`). On the sprint pool
it keeps j05's FullyBlocked (0.21 against 0.23) but loses PedestriansOnRoad (0.17 against 0.45): a few global
background modes do not do what j05's 10 nearest passing routes do, so j05's gain needs a local background. j12 is
dropped. Grok's j12 and Gemini's independent reimplementation (own PCA and mixture code) give the same K and the same
10 ordered route sets on both pools. A no-try check: j05's axes at k 5 and 20 match its k 10 axes with mean best-match
Jaccard 0.87 / 0.86 (sprint) and 0.94 / 0.89 (H21) (measured, route ids only), so k 10 is not a fragile choice.

j13 (rows written before scoring; density lane, builds on j05): local tangent residual. Same unwhitened PCA 32 on all
routes and the same 10 nearest passing routes per failing route as j05 (k 10, Euclidean in score space). j05's residual
(score minus the neighbours' mean) then has its projection on the top 2 principal directions of those 10 neighbours
(centred on their own mean, SVD) removed, so what is left is the deviation off the local passing manifold rather than
along it. Not whitened, not normalised (residual size kept, as j11 and j12 showed it matters). Ward 2/3/5. Reason:
j12 showed j05's gain needs a local background; local tangent-space methods (Zhang and Zha 2004, LTSA, SIAM J. Sci.
Comput. 26:313-338, verified via Crossref) model the passing neighbourhood as a low-dimensional tangent plane, and
movement along that plane is ordinary scene variation. Kill rule fixed now: dropped if its sprint PedestriansOnRoad is
below j05's 0.45. Same layers as j05 (L5+8+20 window; L10 on H21). One setting (2 directions), no sweep.

| id | date | pool | settings | score | p vs rivals | methods tried |
|---|---|---|---|---|---|---|
| j13 | 2026-11-16 | sprint | j05 residual minus its projection on the top 2 local PCs of its 10 nearest passing routes, PCA 32, Ward 2/3/5, commit `8984004` | 0.218 (0.27 / 0.21 / 0.17); failing-only chance 0.080 | B3-behaviour +0.125, p 0.001 / m08 -0.088, p 0.84 / B3-infraction +0.026, p 0.44 | 122 |
| j13 | 2026-11-16 | H21 | same, L10 (CustomObstacles / Wall / PedestriansOnRoad) | 0.207 (0.24 / 0.18 / 0.20); failing-only chance 0.177 | B3-kin -0.119, p 0.92 / m03 L10 -0.035, p 0.62 | 123 |

j13 is below the best rival on both pools (measured, dev, 123 tried in total: 104 Chris + 19 `j`), and its fixed kill
rule fires: sprint PedestriansOnRoad 0.27 against j05's 0.45. Dropped. The tangent step removes on average 29% of the
residual length (10% of its squared length) on the sprint pool and 36% (15%) on H21 (measured), yet it moves the
sprint cut-3 and cut-5 splits (per-axis Jaccard with j05's axes 0.0 to 0.71 on four of the ten) and costs most of
j05's PedestriansOnRoad. Reading: j05's PedestriansOnRoad gain rests on a Ward split that a small change to the
residual undoes, not on a robust direction. Grok's j13, Gemini's independent reimplementation (scikit-learn
neighbours, its own PCA) and a rerun by the orchestrator give the same 10 ordered route sets on both pools.


j14 (row written before scoring; density/matching lane, builds on j05): matched-control residual. Same layers and
scaling as j05 (L5+8+20, each layer divided by its root-mean-square). Two unwhitened PCA 32 fits on all routes: one on
the approach-window summary (the score space, as j05) and one on the early-route summary (the route's first 6 frames,
before the approach window). Each failing route's 10 nearest passing routes are found in the early-route space, and
their mean window score is subtracted from the failing route's window score. Not whitened, not normalised. Ward
2/3/5. Reason: j05 picks neighbours by the window itself, which already holds the failure, so its neighbours partly
match the failure and subtract some of it; matching on context measured before the failure, as matching estimators
pick controls on pre-treatment covariates (Abadie and Imbens 2006, Econometrica 74:235-267, verified via Crossref),
should remove the scene and keep the failure. Sprint pool only: H21's cache has no early slot (NaN). Kill rule fixed
now: dropped if its sprint score is below j05's 0.284. One setting (k 10), no sweep.

| id | date | pool | settings | score | p vs rivals | methods tried |
|---|---|---|---|---|---|---|
| j14 | 2026-11-16 | sprint | window PCA 32 score minus mean window score of the 10 nearest passing routes in early-route PCA 32, Ward 2/3/5, commit `3f53e08` | 0.133 (0.14 / 0.11 / 0.15); failing-only chance 0.080 | B3-behaviour +0.040, p 0.058 / m08 -0.173, p 0.96 / B3-infraction -0.059, p 0.88 | 124 |

j14 is below every activation rival and its fixed kill rule fires (0.133 against j05's 0.284; measured, dev, 124 tried
in total: 104 Chris + 20 `j`). Dropped. The early-route neighbours share 0.87 of 10 with j05's window neighbours on
average, and subtracting them barely shrinks the residual (mean length 14.9, against 15.3 for the plain distance to
the passing mean and 8.5 for j05; measured). The first 6 frames of a route say little about its approach window, so
j14 is close to plain unwhitened PCA. j05's gain needs neighbours matched on the window itself. Grok's j14 and the
orchestrator's independent reimplementation (scikit-learn neighbours, scipy Ward) give the same 10 ordered route sets.

No-try check (label-free, route ids only, no gap read): refitting on 20 random 80% subsets of the passing routes
(failing routes kept), j05's original top-10 axes are recovered with mean best-match Jaccard 0.90 (share of
axis-resamples at 0.8 or more: 0.89), against m08's 0.78 (0.64) and m11's 0.85 (0.76) (measured, sprint pool; Grok's run and the orchestrator's
independent recompute agree to three decimals for j05 and m08). On H21: j05 0.91 (0.83), m03 L10 0.78 (0.56)
(measured, Grok's run). m08's cut-5 groups move most (mean 0.36 to 0.64 on four axes). So j05's axes are stable to the passing background;
j13's reading above (a fragile Ward split) holds only for changes to the residual itself, not to the background
sample.

j15 (rows written before scoring; density lane, builds on j05): density clusters on j05's residuals in place of Ward.
Same embedding as j05 (unwhitened PCA 32 on all routes, each failing route minus the mean of its 10 nearest passing
routes; L5+8+20 window, L10 on H21). On the failing residuals only: HDBSCAN's hierarchy (Campello, Moulavi and Sander
2013, PAKDD, LNCS 7819:160-172, doi 10.1007/978-3-642-37456-2_14, verified via Crossref) with min_samples 5 (core
distance to the 5th nearest point counting itself) and min_cluster_size 5, Euclidean; single linkage on mutual
reachability, condensed tree, stability of each cluster = sum over its points of (lambda at which the point or its
child cluster leaves) minus (lambda at the cluster's birth). Axes: every non-root cluster of the condensed tree, ranked
by stability (larger size, then lower cluster id, breaks ties), top 10, members = all points of the cluster at its
birth. No Ward, so no repeated axes. Reason: Ward 2/3/5 repeats axes (7 distinct of j05's 10) and forces fixed cut
counts; stability is a label-free own-order ranking under a1. Not Chris's lane: his clustering work is on m08/m11
embeddings; m03 used HDBSCAN on plain PCA ranked by size times cohesion, not on a residual and not by stability. Kill
rule fixed now: dropped if its sprint score is below j05's 0.284. One setting, no sweep.

| id | date | pool | settings | score | p vs rivals | methods tried |
|---|---|---|---|---|---|---|
| j15 | 2026-11-16 | sprint | j05 residual, HDBSCAN condensed tree (min_samples 5, min_cluster_size 5), all clusters ranked by stability, top 10 | 0.063 (0.06 / 0.06 / 0.07); failing-only chance 0.071 | B3-behaviour -0.030, p 0.96 / m08 -0.243, p 1.00 / B3-infraction -0.129, p 1.00 | 125 |
| j15 | 2026-11-16 | H21 | same, L10 (CustomObstacles / Wall / PedestriansOnRoad) | no axes: the tree never splits into two clusters of 5 or more on 52 failing routes; the scorer refuses an empty method (0 by construction) | not scored | 126 |

j15 is below chance and every rival on the sprint pool, and empty on H21 (measured, dev, 126 tried in total: 104 Chris
+ 22 `j`). Its fixed kill rule fires; dropped. The stability ranking picks near-root clusters that single linkage builds
by peeling points off one at a time (316, 339, 295 and 278 of 357 routes) and a few 6-route clusters; nothing at the
20 to 100 route scale where the gaps are. Grok's j15 (own Prim tree and condense walk) and the orchestrator's
independent version (scikit-learn's internal single-linkage and condense code, own stability) find the same 44
clusters with the same stabilities; nine of the ten axes are identical and the tenth differs by one route that sits on
a three-way tie in mutual reachability (both choices valid). Both score 0.063.

No-try check (label-free beyond pass/fail, route ids only; 126 tried in total, unchanged): is j05's residual length a
usable filter? Each passing route's residual against its 10 nearest *other* passing routes (leave-one-out, j05's PCA 32
space) gives a passing reference. Measured: sprint pool, passing median 1.92, 90th percentile 4.18, failing median 8.11,
so 94.4% of failing routes (337 of 357) lie above the passing 90th percentile; H21 (L10), passing 90th percentile 4.62,
failing median 7.62, 100% (52 of 52) above it. The planned j16 (keep only failing routes above the passing 90th
percentile, then j05's Ward) was set to run only if that share fell between 20% and 80%. It does not, so the filter
would drop almost nothing: j16 is not run and costs no try. Reading: almost every failing route sits far from its
passing neighbours, consistent with m19's note that failing windows are told apart from passing ones by where they end,
so residual size marks "failing", not which failure. Script `/tmp/ar-r75/diag.py`; it asserts its failing residual
lengths equal j05's embedding.

j09 and j10 (rows written before scoring; temporal lane, the first `j` methods on the frame sequence rather than a
window mean). The H21 per-frame file `results/savio/f2d-all/frames.npz` landed 2026-11-16 (Savio job 41402579, Jerry's
H21 shards, `frames_pool.py`: `driving_queries`, layers 5/8/10/20, last 50 frames before failure, 200 routes, 52
failing). Both at their defaults, no sweep: layer 8, every valid frame scaled by one root-mean-square, unwhitened PCA 16,
one diagonal Gaussian HMM fit on all routes with S chosen by BIC from {4, 6, 8}. j09 embeds each failing route by the
Hellinger map of its state occupancy and transitions (`j09_hmm.py`); j10 by the emission-mean Fisher score
(Jaakkola and Haussler 1998; `j10_hmmfisher.py`, `080120a`). Both Ward 2/3/5, top 10 in the method's own order.
No-try diagnostic first (`frames_diag.py`, frames file only, label-free beyond pass/fail; measured): BIC picks S 8 (the
top of the grid), largest state share 0.22, longest expected dwell 34 frames, |Spearman rho| of each embedding's
length and first PC against stop length 0.15 to 0.28 (flag at 0.5), so neither is flagged as a stop-length detector.
Rule fixed now: each is carried to the sprint pool when Chris's `frames.npz` lands unless its H21 score is below
failing-only chance; H21 alone cannot make a candidate. Scored with `frames_queue.sh` (POOL h21), rivals B3-kin and
m03 L10.

| id | date | pool | settings | score (top-10 mean best Jaccard; CustomObstacles / Wall / PedestriansOnRoad) | p vs B3-kin / vs m03 L10 / vs m08 L5+8+20 | methods tried (all pools) |
|---|---|---|---|---|---|---|
| j09 | 2026-11-16 | H21 | HMM over the last 50 frames, L8, PCA 16, S 8 by BIC, Hellinger occupancy + transitions, Ward 2/3/5 | **0.331** (0.31 / 0.40 / 0.29); failing-only chance 0.185 | +0.006 [-0.110, +0.148], p 0.45 / +0.089, p 0.17 / +0.110 [-0.174, +0.332], p 0.15 | 127 |
| j10 | 2026-11-16 | H21 | j09's model, emission-mean Fisher score, Ward 2/3/5 | 0.133 (0.18 / 0.14 / 0.08); failing-only chance 0.189 | p 1.00 / p 0.96 / not scored | 128 |

Rivals on H21 now include Chris's m08 at its own layers (L5+8+20, 6-frame window), built from the multi-layer H21 cache
`results/savio/f2d-all/cache.npz` (same Savio job) with `cache_methods.py --method m03 --layer 5 8 20 --name m08`:
0.221 (0.29 / 0.18 / 0.20), below m03 at L10 (0.242) on this pool (measured). j09 is the first `j` method above every
H21 rival, but against B3-kin it is a tie (+0.006, interval spans zero); measured, dev, one seed, 128 tried in total
(104 Chris + 24 `j`). H21 alone cannot make a candidate. j10 is below failing-only chance; its rule drops it. j09 is
carried to the sprint pool as soon as Chris's `frames.npz` exists. No-try check (label-free, route ids only): refitting
j09 with KMeans seeds 1 to 10 gives S 8 every time and recovers the seed-0 axes with mean best-match Jaccard 0.94
(share of axes at 0.8 or more 0.89); seed 0 is in the highest-likelihood basin, shared with seeds 1, 5, 8 and 10. Only
the 10th axis (6 routes) moves much (mean 0.70). Script `/tmp/ar-r89/seedstab.py`; it asserts seed 0 rebuilds the
stored axes. Reports in `results/h21/sprint/frames/` (`j09-report-m08.json` adds the m08 rival; its p values differ from
the queue report's by up to 0.008 from bootstrap draws).
Independent check: a Grok worker wrote j09 again from a written specification without opening `j09_hmm.py`
(`/tmp/ar-j09/grok/j09g.py`, own log-space forward-backward and EM). Rerun by the orchestrator, it gives the same ten
ordered axes and the same BIC values to about 1e-9.
Overlap check (method outputs only, no gap names): mean best-match Jaccard of j09's ten axes against B3-kin's is 0.58,
against m03 L10's 0.43 and against m08's 0.36 (measured). j09's groups sit closer to the behaviour rival's than to the
activation leads', so part of what it reads on H21 is likely how the car moved. The diagnostic's stop-length check
(|rho| 0.15 to 0.28) did not flag this; B3-kin also uses speed and stationary share.
Kin-variance check (no try; reads only `kin`, pass/fail and each method's stored axes): share of the four
standardised kin columns' variance over the 52 failing routes that each method's 5-group Ward cut explains (eta squared;
permuted-label null mean 0.08, 95th percentile 0.15 to 0.16). Measured: B3-kin 0.82, j05 0.65, j09 0.60, m08 0.44,
m03 L10 0.33. j09's ten axes hold 7 distinct groups (the 10-route group repeats three times, the 18-route group
twice, as Ward 2/3/5 nests); the repeated 10-route group is the stopped one (mean speed z -1.34, stationary share z
+1.31) and the 18-route group the fast one (speed z +0.94). So most of j09's split on H21 is a speed split, which fits
its tie with B3-kin. j06 (kin removed before clustering) scored lower on H21 (0.246), so removing behaviour is not the
obvious fix; the open test is whether j09 still beats B3-behaviour on Chris's pool, where B3-behaviour is weak (0.093).
Script `/tmp/ar-r90/kinsplit.py`.

### Replication on H21 (shared plan track C, 2026-11-16)

Every current lead rescored unchanged, at the settings it led with on Chris's sprint pool, on the H21 multi-layer cache
(`results/savio/f2d-all/cache.npz`, Savio job 41402579: 200 routes, 52 failing, 24 layers, 6-frame window). Nothing is
tuned to H21. The 6-frame cache cannot give the 20- and 50-frame windows, so those are rebuilt from the H21 per-frame
file (`results/savio/f2d-all/frames.npz`, last 50 frames before failure, layers 5/8/10/20) as the mean of the last
W frames; rebuilt at W = 6 it matches the cache's own window slot to float16 rounding (max abs difference 0.016 on a
mean magnitude of 0.23, measured), so W = 20 and 50 are the same slice `cache_pool.py --window W` would take. Methods run
by `cache_methods.py` and `j05_knnresid.py` unchanged; script `/tmp/ar-r95/derive.py`. Gaps CustomObstacles / Wall /
PedestriansOnRoad, decoys as batch 1, rivals B3-kin (primary), m03 L10 and m08. H21 limits: one seed, small
categories, categories already read by H22 to H25; it can rank and kill, not make a candidate. Each row counts as a
try. Rows written before the scores are read, except m08, whose score was read in round 89 as a rival without a try.

| id | date | pool | settings | score (CustomObstacles / Wall / PedestriansOnRoad) | p vs B3-kin / m03 L10 / m08 | methods tried |
|---|---|---|---|---|---|---|
| m08 | 2026-11-16 | H21 | m03 on `driving_queries` L5+8+20, 6-frame window, PCA 32, Ward 2/3/5 (scored round 89, counted now) | 0.221 (0.29 / 0.18 / 0.20); failing-only chance 0.181 | -0.104, p 0.84 / -0.021, p 0.47 / — | 129 |
| m15 | 2026-11-16 | H21 | m03 on L8, 50-frame window (rebuilt from frames), PCA 32, Ward 2/3/5 | 0.210 (0.18 / 0.11 / 0.33); failing-only chance 0.185 | -0.116, p 0.86 / -0.032, p 0.99 / -0.012, p 0.61 | 130 |
| m11 | 2026-11-16 | H21 | m03 on L10, 20-frame window (rebuilt from frames), PCA 32, Ward 2/3/5 | 0.247 (0.25 / 0.16 / 0.33); failing-only chance 0.181 | -0.079, p 0.79 / +0.005, p 0.48 / +0.025, p 0.55 | 131 |
| m12 | 2026-11-16 | H21 | m03 on L8, 6-frame window, PCA 32, average linkage 2/3/5 | 0.203 (0.17 / 0.11 / 0.33); failing-only chance 0.163 | -0.122, p 0.88 / -0.039, p 1.00 / -0.018, p 0.62 | 132 |
| m16 | 2026-11-16 | H21 | m03 on L5+8+20, 20-frame window (rebuilt from frames), PCA 32, Ward 2/3/5 | 0.222 (0.21 / 0.13 / 0.33); failing-only chance 0.183 | -0.103, p 0.84 / -0.020, p 0.90 / +0.001, p 0.59 | 133 |
| j05 | 2026-11-16 | H21 | j05 at its file defaults (L5+8+20, 6-frame window, PCA 32, k 10, Ward 2/3/5) | 0.202 (0.25 / 0.16 / 0.20); failing-only chance 0.183 | -0.123, p 0.88 / -0.040, p 0.56 / -0.019, p 0.84 | 134 |

Scored 2026-11-16 by the orchestrator (measured, dev, H21 pool; 134 tried in total: 104 Chris + 30 `j`-loop tries, 19
of them on H21). **No lead replicates on H21.** All six score 0.20 to 0.25, within 0.02 to 0.07 of failing-only chance
(0.16 to 0.19), and all sit 0.08 to 0.12 below the four-number behaviour rival B3-kin (0.326; p 0.79 to 0.88, so not
separable either way with 3 to 8 failures per category). The order among them is not the sprint pool's: m11 (L10 w20)
is highest at 0.247, m15 (the sprint's best single layer, L8 w50) 0.210, m12 0.203. Longer windows do not help on H21
(m16 w20 0.222 against m08 w6 0.221). j09 (0.331, HMM over frames) remains the only method level with B3-kin here.
A structural reading (method outputs only): for the five m leads, Ward or average cut 2 on H21 splits 47 to 51 of
the 52 failing routes from 1 to 5, and later cuts mostly peel off 1 to 4 more, so most of their top 10 is either
near-whole-pool or near-singleton and scores close to failing-only chance by construction. j05 splits more evenly
(35 / 17) and still scores 0.202. Reports `results/h21/sprint/repl/`.


### Amendment A2 (2026-11-16): distinct axes, B3-infraction reported

`docs/prereg-fail2drive.md` §8, `CONFLICTS.md` C40, tag `f2d-sprint-a2`.
- Repeated axes no longer use up the top 10.
- Cut-based clustering continues past its last cut until it has 10 distinct axes.
- B3-infraction is compared with every method, but has no pass bar and is not part of the best rival.
- Every logged method is rescored on this pool by `a2_rescore.sh`, from its own recorded settings. Rescores are not
  tries.
- The H21 rows need H21's caches, which only Jerry's account can read; issue 9 asks Jerry's side to rescore them.

Rescored 2026-11-16 by jobs 41406567 (m) and 41406568 (j), about 0.1 SU, all CPU. Measured, dev, 134 tried in total;
rescores are not tries.

**Rivals under A2.**

| rival | A1 | A2 | PedestriansOnRoad / FullyBlocked / BadParking | distinct axes |
|---|---:|---:|---|---:|
| B3-behaviour | 0.093 | **0.189** | 0.37 / 0.06 / 0.14 | 10 |
| B7-pool | 0.187 | 0.187 | 0.20 / 0.33 / 0.03 | 10 |
| B3-infraction | 0.192 | 0.192 | 0.35 / 0.06 / 0.16 | 8 (8 infraction types) |

- **B3-behaviour doubles.** Its A1 top 10 repeated groups. With distinct axes it finds a 0.37 pedestrian group, so the
  primary rival is now level with B7-pool and B3-infraction.
- **Most leads rise a little.** The biggest gains:
  - m12 (L8, average linkage, w6): 0.301 to **0.370** (0.59 / 0.26 / 0.26).
  - m16 at w30: 0.280 to 0.332.
  - The m05 sweep at L7: 0.253 to 0.303.
  - j06: 0.165 to 0.297.
- **Every lead's margin over B3-behaviour is now about +0.11 to +0.18, at p 0.06 to 0.13.** No dev lead is separated
  from the primary rival. Under A1, the leads were at p ≤ 0.01 against a rival that was penalised by its own
  repeats.

One row per method file. `dir` is under `results/savio/f2d-dev/simlingo/sprint/a2/`. Each comparison column gives the
delta and one-sided p. j rows' A1 scores are from the j section above. batch3-fix's row is the same run as batch3's
m16 w20 row, so it is left out.

| dir | method | A1 | A2 | per gap | distinct axes | vs B3-behaviour | vs B7-pool | vs B3-infraction |
| batch2 | method_m03_layer_8_cluster_average | 0.301 | 0.370 | 0.59 / 0.26 / 0.26 | 10 | +0.181, p 0.081 | +0.183, p 0.035 | +0.178, p 0.087 |
| batch3-w30 | method_m03_layer_5_8_20 | 0.280 | 0.332 | 0.59 / 0.12 / 0.29 | 10 | +0.143, p 0.059 | +0.145, p 0.067 | +0.139, p 0.067 |
| batch2 | method_m03_layer_5_8_20 | 0.306 | 0.325 | 0.59 / 0.20 / 0.18 | 10 | +0.136, p 0.069 | +0.138, p 0.070 | +0.132, p 0.077 |
| batch3-w50 | method_m03_layer_5_8_20 | 0.259 | 0.321 | 0.59 / 0.09 / 0.28 | 10 | +0.132, p 0.093 | +0.134, p 0.082 | +0.129, p 0.100 |
| batch3 | m20-w20L10+B7 | 0.289 | 0.321 | 0.59 / 0.13 / 0.24 | 10 | +0.132, p 0.059 | +0.134, p 0.069 | +0.128, p 0.080 |
| batch3-w30 | method_m03_layer_8 | 0.265 | 0.317 | 0.59 / 0.11 / 0.25 | 10 | +0.128, p 0.104 | +0.130, p 0.098 | +0.125, p 0.116 |
| batch2-w20 | method_m03_layer_8 | 0.304 | 0.316 | 0.59 / 0.11 / 0.25 | 10 | +0.127, p 0.078 | +0.129, p 0.088 | +0.123, p 0.085 |
| batch3-w50 | method_m03_layer_8 | 0.312 | 0.312 | 0.59 / 0.17 / 0.17 | 10 | +0.123, p 0.091 | +0.124, p 0.086 | +0.119, p 0.101 |
| batch2-w20 | method_m03 | 0.310 | 0.310 | 0.59 / 0.10 / 0.24 | 10 | +0.121, p 0.099 | +0.123, p 0.117 | +0.118, p 0.117 |
| batch3 | m20-w20L10+atL1 | 0.310 | 0.310 | 0.59 / 0.10 / 0.24 | 10 | +0.121, p 0.074 | +0.123, p 0.088 | +0.118, p 0.096 |
| batch3 | method_m03_cuts_10 | 0.310 | 0.310 | 0.59 / 0.10 / 0.24 | 10 | +0.121, p 0.056 | +0.123, p 0.062 | +0.118, p 0.075 |
| batch3-w50 | method_m03 | 0.272 | 0.308 | 0.59 / 0.08 / 0.25 | 10 | +0.119, p 0.130 | +0.121, p 0.092 | +0.115, p 0.130 |
| batch3-w30 | method_m03 | 0.282 | 0.306 | 0.59 / 0.09 / 0.24 | 10 | +0.117, p 0.090 | +0.118, p 0.089 | +0.113, p 0.106 |
| batch3 | method_m03_layer_5_8_20 | 0.306 | 0.304 | 0.59 / 0.09 / 0.23 | 10 | +0.115, p 0.074 | +0.117, p 0.074 | +0.111, p 0.092 |
| m05 | method_m03_site_driving_queries_layer_7 | 0.253 | 0.303 | 0.59 / 0.07 / 0.25 | 10 | +0.114, p 0.172 | +0.115, p 0.149 | +0.110, p 0.171 |
| j | j06-driving_queries-L5+8+20-window | 0.165 | 0.297 | 0.65 / 0.08 / 0.16 | 10 | +0.108, p 0.088 | +0.110, p 0.089 | +0.104, p 0.100 |
| batch2-w10 | method_m03_layer_8 | 0.295 | 0.295 | 0.59 / 0.14 / 0.16 | 10 | +0.106, p 0.143 | +0.108, p 0.131 | +0.103, p 0.170 |
| j | j05-driving_queries-L5+8+20-window | 0.284 | 0.284 | 0.45 / 0.23 / 0.16 | 10 | +0.095, p 0.062 | +0.097, p 0.076 | +0.091, p 0.070 |
| batch3 | method_m03_auto-layers_3 | 0.277 | 0.282 | 0.59 / 0.12 / 0.13 | 10 | +0.093, p 0.158 | +0.095, p 0.145 | +0.090, p 0.172 |
| batch3 | method_m03_site_all_tokens_auto-layers_3 | 0.254 | 0.278 | 0.59 / 0.13 / 0.11 | 10 | +0.089, p 0.198 | +0.091, p 0.113 | +0.086, p 0.214 |
| batch3 | method_m03_site_all_tokens_layer_0 | 0.278 | 0.278 | 0.59 / 0.13 / 0.11 | 10 | +0.089, p 0.214 | +0.091, p 0.120 | +0.086, p 0.225 |
| batch3 | method_m03_site_all_tokens_layer_1 | 0.254 | 0.278 | 0.59 / 0.13 / 0.11 | 10 | +0.089, p 0.201 | +0.091, p 0.114 | +0.086, p 0.213 |
| batch3 | method_m03_site_all_tokens_layer_2 | 0.254 | 0.278 | 0.59 / 0.13 / 0.11 | 10 | +0.089, p 0.201 | +0.091, p 0.114 | +0.086, p 0.214 |
| batch3 | method_m03_site_all_tokens_layer_3 | 0.254 | 0.278 | 0.59 / 0.13 / 0.11 | 10 | +0.089, p 0.196 | +0.091, p 0.112 | +0.086, p 0.205 |
| batch3 | method_m03_site_vision_bridge | 0.254 | 0.278 | 0.59 / 0.13 / 0.11 | 10 | +0.089, p 0.204 | +0.091, p 0.117 | +0.086, p 0.217 |
| m05 | method_m03_site_driving_queries_layer_8 | 0.253 | 0.275 | 0.59 / 0.14 / 0.09 | 10 | +0.086, p 0.194 | +0.087, p 0.175 | +0.082, p 0.222 |
| batch3 | method_m03_layer_5_8_20_cluster_average | 0.061 | 0.269 | 0.68 / 0.05 / 0.07 | 10 | +0.080, p 0.217 | +0.081, p 0.162 | +0.076, p 0.233 |
| m05 | method_m03_site_driving_queries_layer_11 | 0.224 | 0.266 | 0.59 / 0.11 / 0.09 | 10 | +0.077, p 0.230 | +0.079, p 0.192 | +0.073, p 0.255 |
| batch3-w10 | method_m03_layer_5_8_20 | 0.247 | 0.263 | 0.59 / 0.08 / 0.11 | 10 | +0.074, p 0.238 | +0.076, p 0.186 | +0.070, p 0.260 |
| batch2-w10 | method_m03 | 0.246 | 0.253 | 0.59 / 0.07 / 0.10 | 10 | +0.064, p 0.300 | +0.066, p 0.238 | +0.060, p 0.322 |
| batch3 | method_m03_cluster_average | 0.061 | 0.240 | 0.59 / 0.05 / 0.07 | 10 | +0.051, p 0.378 | +0.053, p 0.286 | +0.047, p 0.386 |
| batch2 | method_m03_layer_8_cluster_complete | 0.236 | 0.236 | 0.27 / 0.21 / 0.22 | 10 | +0.047, p 0.386 | +0.049, p 0.224 | +0.044, p 0.382 |
| j | j13-driving_queries-L5+8+20-window | 0.218 | 0.236 | 0.27 / 0.21 / 0.23 | 10 | +0.047, p 0.232 | +0.049, p 0.154 | +0.044, p 0.252 |
| m05 | method_m03_site_all_tokens_layer_1 | 0.195 | 0.228 | 0.20 / 0.35 / 0.13 | 10 | +0.039, p 0.406 | +0.041, p 0.236 | +0.036, p 0.409 |
| batch3 | method_m03_summary_route_layer_8 | 0.227 | 0.227 | 0.08 / 0.35 / 0.25 | 10 | +0.038, p 0.420 | +0.040, p 0.289 | +0.035, p 0.422 |
| m05 | method_m03_site_driving_queries_layer_5 | 0.189 | 0.225 | 0.26 / 0.18 / 0.24 | 10 | +0.036, p 0.292 | +0.038, p 0.295 | +0.033, p 0.282 |
| batch2 | m09 | 0.212 | 0.212 | 0.38 / 0.07 / 0.18 | 10 | +0.023, p 0.414 | +0.025, p 0.372 | +0.019, p 0.433 |
| m05 | method_m03_site_driving_queries_layer_9 | 0.195 | 0.209 | 0.25 / 0.22 / 0.16 | 10 | +0.021, p 0.350 | +0.022, p 0.350 | +0.017, p 0.355 |
| m05 | method_m03_site_driving_queries_layer_20 | 0.209 | 0.209 | 0.31 / 0.14 / 0.18 | 10 | +0.020, p 0.371 | +0.022, p 0.357 | +0.017, p 0.370 |
| m05 | method_m03_site_driving_queries_layer_2 | 0.201 | 0.204 | 0.27 / 0.17 / 0.16 | 10 | +0.015, p 0.517 | +0.017, p 0.364 | +0.012, p 0.523 |
| m05 | method_m03_site_all_tokens_layer_15 | 0.102 | 0.203 | 0.15 / 0.35 / 0.11 | 10 | +0.014, p 0.476 | +0.016, p 0.321 | +0.010, p 0.474 |
| batch2 | m10 | 0.203 | 0.203 | 0.38 / 0.13 / 0.09 | 10 | +0.014, p 0.470 | +0.016, p 0.392 | +0.010, p 0.499 |
| m05 | method_m03_site_driving_queries_layer_3 | 0.129 | 0.202 | 0.18 / 0.18 / 0.25 | 10 | +0.013, p 0.496 | +0.015, p 0.415 | +0.010, p 0.482 |
| batch2 | method_m03_cuts_10 | 0.200 | 0.200 | 0.27 / 0.15 / 0.18 | 10 | +0.011, p 0.315 | +0.013, p 0.209 | +0.007, p 0.335 |
| batch2 | method_m03_cuts_4_6 | 0.180 | 0.200 | 0.27 / 0.15 / 0.18 | 10 | +0.011, p 0.401 | +0.013, p 0.315 | +0.007, p 0.425 |
| m05 | method_m03_site_all_tokens_layer_23 | 0.106 | 0.200 | 0.14 / 0.35 / 0.10 | 10 | +0.011, p 0.466 | +0.013, p 0.295 | +0.007, p 0.485 |
| j | j02-driving_queries-L5+8+20-window | 0.198 | 0.198 | 0.27 / 0.15 / 0.17 | 10 | +0.009, p 0.398 | +0.011, p 0.381 | +0.006, p 0.422 |
| m05 | method_m03_site_all_tokens_layer_11 | 0.078 | 0.198 | 0.14 / 0.35 / 0.10 | 10 | +0.009, p 0.488 | +0.011, p 0.338 | +0.005, p 0.498 |
| batch2 | method_m03_layer_1_5_8_20 | 0.157 | 0.198 | 0.27 / 0.13 / 0.19 | 10 | +0.009, p 0.478 | +0.010, p 0.359 | +0.005, p 0.494 |
| m05 | method_m03_site_driving_queries_layer_1 | 0.141 | 0.196 | 0.27 / 0.07 / 0.25 | 10 | +0.008, p 0.501 | +0.009, p 0.403 | +0.004, p 0.507 |
| j | j07-driving_queries-L5+8+20-window | 0.196 | 0.196 | 0.32 / 0.11 / 0.16 | 8 | +0.007, p 0.281 | +0.008, p 0.294 | +0.003, p 0.301 |
| j | j04-driving_queries-L5+8+20-window | 0.194 | 0.194 | 0.24 / 0.16 / 0.18 | 10 | +0.005, p 0.416 | +0.007, p 0.384 | +0.002, p 0.429 |
| m05 | method_m03_site_all_tokens_layer_16 | 0.176 | 0.191 | 0.12 / 0.35 / 0.10 | 10 | +0.002, p 0.459 | +0.004, p 0.284 | -0.002, p 0.459 |
| m05 | method_m03_site_vision_bridge | 0.171 | 0.190 | 0.09 / 0.35 / 0.13 | 10 | +0.001, p 0.499 | +0.002, p 0.388 | -0.003, p 0.513 |
| m05 | method_m03_site_all_tokens_layer_21 | 0.181 | 0.189 | 0.11 / 0.35 / 0.10 | 10 | +0.001, p 0.528 | +0.002, p 0.393 | -0.003, p 0.536 |
| m05 | method_m03_site_all_tokens_layer_18 | 0.175 | 0.189 | 0.10 / 0.35 / 0.11 | 10 | +0.000, p 0.504 | +0.002, p 0.349 | -0.003, p 0.511 |
| m05 | method_m03_site_all_tokens_layer_7 | 0.079 | 0.189 | 0.11 / 0.35 / 0.10 | 10 | +0.000, p 0.505 | +0.002, p 0.364 | -0.003, p 0.514 |
| m05 | method_m03_site_all_tokens_layer_9 | 0.080 | 0.189 | 0.11 / 0.35 / 0.10 | 10 | -0.000, p 0.504 | +0.002, p 0.361 | -0.004, p 0.514 |
| m05 | method_m03_site_all_tokens_layer_19 | 0.094 | 0.189 | 0.12 / 0.35 / 0.09 | 10 | -0.000, p 0.533 | +0.002, p 0.422 | -0.004, p 0.541 |
| b7 | m01-L10_k64_s0 | 0.187 | 0.187 | 0.20 / 0.33 / 0.03 | 10 | -0.002, p 0.580 | -0.001, p 1.000 | -0.006, p 0.605 |
| j | j11-driving_queries-L5+8+20-window | 0.187 | 0.187 | 0.31 / 0.14 / 0.11 | 10 | -0.002, p 0.442 | -0.001, p 0.400 | -0.006, p 0.461 |
| batch2 | method_m03_cluster_average | 0.132 | 0.186 | 0.27 / 0.05 / 0.23 | 10 | -0.003, p 0.600 | -0.001, p 0.528 | -0.006, p 0.618 |
| m05 | method_m03_site_all_tokens_layer_0 | 0.081 | 0.185 | 0.10 / 0.35 / 0.10 | 10 | -0.004, p 0.508 | -0.002, p 0.384 | -0.007, p 0.518 |
| m05 | method_m03_site_all_tokens_layer_6 | 0.080 | 0.185 | 0.10 / 0.35 / 0.10 | 10 | -0.004, p 0.515 | -0.002, p 0.395 | -0.007, p 0.524 |
| batch2-w3 | method_m03 | 0.183 | 0.183 | 0.23 / 0.14 / 0.18 | 10 | -0.005, p 0.613 | -0.004, p 0.495 | -0.009, p 0.614 |
| m05 | method_m03_site_driving_queries_layer_17 | 0.183 | 0.183 | 0.24 / 0.14 / 0.16 | 10 | -0.006, p 0.622 | -0.004, p 0.471 | -0.010, p 0.620 |
| m05 | method_m03_site_all_tokens_layer_14 | 0.169 | 0.183 | 0.09 / 0.35 / 0.11 | 10 | -0.006, p 0.547 | -0.005, p 0.433 | -0.010, p 0.552 |
| m05 | method_m03_site_all_tokens_layer_22 | 0.081 | 0.182 | 0.10 / 0.35 / 0.09 | 10 | -0.007, p 0.516 | -0.005, p 0.385 | -0.010, p 0.521 |
| j | j12-driving_queries-L5+8+20-window | 0.182 | 0.182 | 0.17 / 0.21 / 0.16 | 10 | -0.007, p 0.439 | -0.005, p 0.393 | -0.011, p 0.466 |
| batch1 | m07 | 0.134 | 0.181 | 0.23 / 0.16 / 0.16 | 10 | -0.008, p 0.517 | -0.006, p 0.404 | -0.011, p 0.537 |
| batch1 | m03 | 0.180 | 0.180 | 0.24 / 0.13 / 0.17 | 10 | -0.008, p 0.622 | -0.007, p 0.464 | -0.012, p 0.629 |
| m05 | method_m03_site_driving_queries_layer_10 | 0.180 | 0.180 | 0.24 / 0.13 / 0.17 | 10 | -0.008, p 0.625 | -0.007, p 0.499 | -0.012, p 0.637 |
| m05 | method_m03_site_all_tokens_layer_2 | 0.077 | 0.180 | 0.09 / 0.35 / 0.10 | 10 | -0.009, p 0.529 | -0.007, p 0.416 | -0.013, p 0.537 |
| m05 | method_m03_site_all_tokens_layer_3 | 0.078 | 0.180 | 0.09 / 0.35 / 0.10 | 10 | -0.009, p 0.527 | -0.007, p 0.415 | -0.013, p 0.537 |
| m05 | method_m03_site_all_tokens_layer_12 | 0.083 | 0.180 | 0.08 / 0.35 / 0.11 | 10 | -0.009, p 0.536 | -0.007, p 0.420 | -0.013, p 0.545 |
| m05 | method_m03_site_all_tokens_layer_17 | 0.176 | 0.180 | 0.09 / 0.35 / 0.10 | 10 | -0.009, p 0.535 | -0.008, p 0.430 | -0.013, p 0.548 |
| m05 | method_m03_site_driving_queries_layer_6 | 0.150 | 0.179 | 0.27 / 0.16 / 0.11 | 10 | -0.010, p 0.538 | -0.008, p 0.394 | -0.013, p 0.554 |
| batch3 | method_m03_summary_route | 0.126 | 0.178 | 0.08 / 0.21 / 0.25 | 10 | -0.011, p 0.486 | -0.010, p 0.416 | -0.015, p 0.482 |
| batch2-w3 | method_m03_layer_8 | 0.163 | 0.175 | 0.17 / 0.10 / 0.26 | 10 | -0.014, p 0.565 | -0.012, p 0.495 | -0.017, p 0.601 |
| m05 | method_m03_site_driving_queries_layer_21 | 0.148 | 0.171 | 0.24 / 0.11 / 0.16 | 10 | -0.018, p 0.701 | -0.016, p 0.533 | -0.022, p 0.701 |
| m05 | method_m03_site_driving_queries_layer_18 | 0.169 | 0.169 | 0.24 / 0.11 / 0.16 | 10 | -0.020, p 0.769 | -0.018, p 0.560 | -0.024, p 0.760 |
| m05 | method_m03_site_driving_queries_layer_19 | 0.167 | 0.167 | 0.22 / 0.13 / 0.15 | 10 | -0.021, p 0.756 | -0.020, p 0.558 | -0.025, p 0.748 |
| m05 | method_m03_site_driving_queries_layer_13 | 0.142 | 0.167 | 0.17 / 0.16 / 0.17 | 10 | -0.022, p 0.729 | -0.020, p 0.575 | -0.025, p 0.781 |
| batch2 | method_m03_cluster_complete | 0.163 | 0.165 | 0.27 / 0.06 / 0.16 | 10 | -0.024, p 0.684 | -0.023, p 0.601 | -0.028, p 0.711 |
| m05 | method_m03_site_driving_queries_layer_12 | 0.163 | 0.163 | 0.20 / 0.14 / 0.15 | 10 | -0.025, p 0.778 | -0.024, p 0.580 | -0.029, p 0.771 |
| m05 | method_m03_site_all_tokens_layer_20 | 0.160 | 0.160 | 0.21 / 0.13 / 0.13 | 10 | -0.029, p 0.469 | -0.027, p 0.392 | -0.032, p 0.476 |
| batch2 | method_m03_cluster_spectral | 0.151 | 0.151 | 0.19 / 0.12 / 0.15 | 10 | -0.038, p 0.847 | -0.036, p 0.610 | -0.041, p 0.846 |
| batch2 | method_m03_layer_8_cluster_spectral | 0.146 | 0.151 | 0.19 / 0.12 / 0.15 | 10 | -0.038, p 0.811 | -0.036, p 0.596 | -0.041, p 0.815 |
| m05 | method_m03_site_driving_queries_layer_0 | 0.125 | 0.150 | 0.27 / 0.08 / 0.09 | 10 | -0.039, p 0.762 | -0.037, p 0.707 | -0.043, p 0.768 |
| batch1 | m04 | 0.120 | 0.147 | 0.17 / 0.09 / 0.18 | 10 | -0.042, p 0.762 | -0.040, p 0.564 | -0.046, p 0.805 |
| m05 | method_m03_site_all_tokens_layer_5 | 0.134 | 0.146 | 0.19 / 0.13 / 0.11 | 10 | -0.043, p 0.700 | -0.041, p 0.614 | -0.047, p 0.715 |
| m05 | method_m03_site_driving_queries_layer_14 | 0.114 | 0.145 | 0.13 / 0.13 / 0.18 | 10 | -0.044, p 0.709 | -0.042, p 0.546 | -0.047, p 0.716 |
| batch1 | m06-m03 | 0.145 | 0.145 | 0.20 / 0.09 / 0.15 | 10 | -0.044, p 0.906 | -0.043, p 0.617 | -0.048, p 0.970 |
| m05 | method_m03_site_all_tokens_layer_8 | 0.086 | 0.140 | 0.18 / 0.13 / 0.11 | 10 | -0.049, p 0.686 | -0.047, p 0.579 | -0.052, p 0.705 |
| m05 | method_m03_site_driving_queries_layer_15 | 0.139 | 0.139 | 0.14 / 0.11 / 0.17 | 10 | -0.050, p 0.820 | -0.048, p 0.634 | -0.054, p 0.832 |
| m05 | method_m03_site_all_tokens_layer_10 | 0.138 | 0.138 | 0.17 / 0.13 / 0.11 | 10 | -0.051, p 0.714 | -0.049, p 0.638 | -0.054, p 0.726 |
| m05 | method_m03_site_driving_queries_layer_4 | 0.134 | 0.137 | 0.09 / 0.07 / 0.25 | 10 | -0.052, p 0.807 | -0.050, p 0.695 | -0.055, p 0.837 |
| m05 | method_m03_site_driving_queries_layer_16 | 0.135 | 0.135 | 0.15 / 0.13 / 0.12 | 10 | -0.054, p 0.951 | -0.053, p 0.749 | -0.058, p 0.948 |
| j | j14-driving_queries-L5+8+20-earlymatch | 0.133 | 0.133 | 0.14 / 0.11 / 0.15 | 10 | -0.056, p 0.824 | -0.054, p 0.665 | -0.059, p 0.829 |
| m05 | method_m03_site_all_tokens_layer_13 | 0.097 | 0.118 | 0.11 / 0.14 / 0.11 | 10 | -0.071, p 0.863 | -0.069, p 0.802 | -0.075, p 0.873 |
| m05 | method_m03_site_all_tokens_layer_4 | 0.078 | 0.116 | 0.09 / 0.13 / 0.13 | 10 | -0.073, p 0.799 | -0.071, p 0.718 | -0.076, p 0.814 |
| m05 | method_m03_site_driving_queries_layer_22 | 0.105 | 0.115 | 0.09 / 0.07 / 0.18 | 10 | -0.074, p 0.951 | -0.072, p 0.786 | -0.077, p 0.980 |
| b7 | m01-L10_k32_s0 | 0.109 | 0.109 | 0.10 / 0.14 / 0.09 | 10 | -0.080, p 0.868 | -0.078, p 0.860 | -0.083, p 0.886 |
| m05 | method_m03_site_driving_queries_layer_23 | 0.101 | 0.107 | 0.10 / 0.08 / 0.14 | 10 | -0.082, p 0.944 | -0.080, p 0.851 | -0.086, p 0.958 |
| b7 | m18-B7pool-w50-L10_k64_s0 | 0.101 | 0.101 | 0.07 / 0.20 / 0.03 | 10 | -0.088, p 0.927 | -0.086, p 0.838 | -0.091, p 0.944 |
| batch3 | method_m03_cluster_complete | 0.078 | 0.090 | 0.09 / 0.09 / 0.10 | 10 | -0.099, p 0.904 | -0.097, p 0.722 | -0.102, p 0.908 |
| b7 | m02-L10_k32_s0 | 0.070 | 0.070 | 0.09 / 0.12 / 0.00 | 10 | -0.119, p 0.916 | -0.118, p 0.906 | -0.123, p 0.919 |
| j | j15-driving_queries-L5+8+20-window | 0.063 | 0.063 | 0.06 / 0.06 / 0.07 | 10 | -0.126, p 1.000 | -0.124, p 0.953 | -0.129, p 1.000 |
| b7 | m18-B7pool-w20-L10_k64_s0 | 0.063 | 0.063 | 0.05 / 0.12 / 0.01 | 10 | -0.126, p 0.987 | -0.124, p 0.999 | -0.129, p 0.992 |
| j | j03 | 0.052 | 0.052 | 0.03 / 0.00 / 0.13 | 10 | -0.137, p 0.986 | -0.135, p 0.946 | -0.141, p 0.991 |
| b7 | m02-L10_k64_s0 | 0.010 | 0.010 | 0.03 / 0.00 / 0.00 | 10 | -0.179, p 1.000 | -0.177, p 1.000 | -0.182, p 1.000 |
| b7 | m14-B7pool-win-k64 | 0.000 | 0.000 | 0.00 / 0.00 / 0.00 | 9 | -0.189, p 1.000 | -0.187, p 1.000 | -0.192, p 1.000 |
| b7 | m14-erraware-win-k64 | 0.000 | 0.000 | 0.00 / 0.00 / 0.00 | 10 | -0.189, p 1.000 | -0.187, p 1.000 | -0.192, p 1.000 |


### Approved overnight batch 4 (Chris, 2026-11-16: "20 to 30 new methods"), all on CPU, scored under A2

Rows are written before any score is read, and each row counts as tries. The windows (`wN`) are as in batch 3.
- **Priorities:** FullyBlocked, frame-based windows and layers, and building on j09.
- **Per-frame file:** `frames.npz`, built by `frames_pool.py` (Jerry's script, read before running) on this pool's
  shards. It holds `driving_queries` layers 5, 8, 10 and 20, last 50 frames before the failure step.
- **Rivals:** B3-behaviour (A2, primary), B7-pool, and B3-infraction (reported).
- **Scripts:** `batch4.sh` parts `fast`, `w100` and `frames`; `frames_methods.py`.

| id | idea | settings | methods tried after |
|---|---|---|---|
| j09 | Jerry's HMM over frames, first time on this pool, run by us at its defaults | L8, PCA 16, S by BIC from {4, 6, 8}, Hellinger occupancy and transitions, Ward | 135 |
| m22 | pedestrian view plus FullyBlocked view in one embedding | L8, w50 window mean and whole-route mean concatenated | 136 |
| m23 | pool the two views' axes | round-robin of m15 (L8 w50) and whole-route L8, A2 axes | 137 |
| m24 | longer approach windows | w100 at L8; w100 at L5+8+20 | 139 |
| m25 | where FullyBlocked lives in whole-route summaries | whole route at L5, L10, L20, L5+8+20, and `all_tokens` L1 | 144 |
| m26 | what changes in the run-up, against the route's own mean | window minus whole-route mean: w50 L8; w20 L10 | 146 |
| m27 | two sites | `driving_queries` L8 plus `all_tokens` L1, w50 | 147 |
| m28 | three-way pool | m15, whole-route L8, B7-pool, round-robin | 148 |
| m29 | several time scales at once | per-frame file, L8: means of the last 5, 20 and 50 frames | 149 |
| m30 | direction of travel in activation space | per-frame, L8: PCA 16 mean and slope over time | 150 |
| m31 | stopped frames apart from moving ones (FullyBlocked) | per-frame, L8: mean while below 0.5 m/s, mean while moving, stopped share | 151 |
| m32 | how much the activations move | per-frame, L8: mean and standard deviation over frames | 152 |
| m33 | j09 at another layer | j09 at L10 | 153 |
| m34 | j09 at another layer | j09 at L20 | 154 |
| m35 | j09 plus the window mean | j09's embedding beside the w50 mean's PCA 32, equal weight | 155 |
| m36 | j09 on several layers | j09's pipeline on L5+8+20 per frame | 156 |
| m38 | j05's background subtraction on our best window | j05 (10 nearest passing routes) on w50 L8 | 157 |
| m39 | PCA width for m15 | L8 w50 at 16 and 64 components | 159 |

m37 is not used. j09 and m33 to m36 run whatever j09 scores here, so the rule cannot be bent after the score is seen.
The reported tried count for the whole batch is 159.

Batch 4 scored 2026-11-16 by jobs 41406570, 41406571 and 41406572 (and 41406569 for `frames.npz`), about 0.2 SU, all
CPU. Measured, dev, **159 tried in total**. Rivals: B3-behaviour 0.189, B7-pool 0.187, B3-infraction 0.192. Reports are
in `sprint/batch4*/report.json`. Each comparison column gives the delta, 95% interval and one-sided p.

| id | score (PedestriansOnRoad / FullyBlocked / BadParking) | vs B3-behaviour | vs B7-pool | vs B3-infraction (reported) | vs best rival p |
|---|---|---|---|---|---|
| m23 (pool: L8 w50 with whole-route L8) | **0.372** (0.59 / **0.35** / 0.17) | +0.183 [−0.035, +0.513], p 0.056 | +0.185 [−0.006, +0.487], p 0.028 | +0.179, p 0.061 | 0.067 |
| m39 (L8 w50, PCA 64) | 0.368 (0.59 / 0.26 / 0.25) | +0.179 [−0.050, +0.472], p 0.073 | +0.181, p 0.099 | +0.176, p 0.079 | 0.126 |
| m39 (L8 w50, PCA 16) | 0.321 (0.59 / 0.10 / 0.27) | +0.132, p 0.058 | +0.134, p 0.072 | +0.129, p 0.076 | 0.110 |
| m27 (L8 plus `all_tokens` L1, w50) | 0.328 (0.59 / 0.14 / 0.26) | +0.139 [−0.017, +0.388], p 0.043 | +0.140, p 0.048 | +0.135, p 0.053 | 0.079 |
| m29 (frames: 5/20/50-frame means, L8) | 0.327 (0.59 / 0.11 / 0.28) | +0.138 [−0.013, +0.358], p 0.044 | +0.140, p 0.074 | +0.134, p 0.058 | 0.096 |
| m32 (frames: mean and spread, L8) | 0.322 (**0.67** / 0.12 / 0.18) | +0.133 [−0.006, +0.288], p 0.034 | +0.135, p 0.068 | +0.130, p 0.048 | 0.084 |
| m24 (w100, L5+8+20) | 0.320 (0.59 / 0.12 / 0.25) | +0.131, p 0.071 | +0.133, p 0.080 | +0.128, p 0.078 | 0.115 |
| m24 (w100, L8) | 0.307 (0.59 / 0.08 / 0.25) | +0.118, p 0.075 | +0.120, p 0.064 | +0.115, p 0.080 | 0.111 |
| m33 (j09 at L10) | 0.306 (0.67 / 0.11 / 0.14) | +0.117, p 0.062 | +0.119, p 0.084 | +0.113, p 0.086 | 0.118 |
| m22 (L8 w50 and whole route, concatenated) | 0.306 (0.59 / 0.08 / 0.25) | +0.117, p 0.153 | +0.119, p 0.139 | +0.113, p 0.154 | 0.216 |
| m31 (frames: stopped and moving means) | 0.296 (0.59 / 0.09 / 0.21) | +0.107, p 0.084 | +0.109, p 0.106 | +0.104, p 0.096 | 0.149 |
| m30 (frames: PCA trend) | 0.296 (0.59 / 0.12 / 0.18) | +0.107, p 0.110 | +0.109, p 0.111 | +0.104, p 0.128 | 0.173 |
| m38 (j05 residual on L8 w50) | 0.295 (0.59 / 0.11 / 0.19) | +0.106, p 0.081 | +0.108, p 0.100 | +0.103, p 0.098 | 0.148 |
| m34 (j09 at L20) | 0.291 (0.54 / 0.18 / 0.15) | +0.102, p 0.128 | +0.104, p 0.136 | +0.098, p 0.144 | 0.208 |
| m28 (pool: L8 w50, whole-route L8, B7-pool) | 0.272 (0.59 / 0.13 / 0.09) | +0.083, p 0.220 | +0.085, p 0.151 | +0.079, p 0.232 | 0.289 |
| m25 (whole route, L20) | 0.252 (0.10 / **0.35** / **0.31**) | +0.063, p 0.393 | +0.065, p 0.279 | +0.060, p 0.401 | 0.485 |
| **j09** (HMM, L8, our pool, run by us) | 0.222 (0.44 / 0.08 / 0.14) | +0.033 [−0.057, +0.167], p 0.221 | +0.035, p 0.235 | +0.030, p 0.241 | 0.386 |
| m36 (j09 on L5+8+20) | 0.221 (0.39 / 0.13 / 0.14) | +0.032, p 0.227 | +0.034, p 0.257 | +0.029, p 0.251 | 0.405 |
| m25 (whole route, `all_tokens` L1) | 0.196 (0.11 / 0.35 / 0.13) | +0.007, p 0.445 | +0.009, p 0.302 | +0.003, p 0.449 | 0.541 |
| m25 (whole route, L5) | 0.186 (0.08 / 0.35 / 0.13) | −0.003, p 0.586 | −0.001, p 0.528 | −0.007, p 0.591 | 0.699 |
| m25 (whole route, L10) | 0.178 (0.08 / 0.21 / 0.25) | −0.011, p 0.485 | −0.010, p 0.405 | −0.015, p 0.482 | 0.603 |
| m26 (w50 L8 minus whole route) | 0.168 (0.07 / 0.35 / 0.08) | −0.021, p 0.653 | −0.019, p 0.657 | −0.024, p 0.662 | 0.775 |
| m26 (w20 L10 minus whole route) | 0.158 (0.08 / 0.32 / 0.08) | −0.031, p 0.678 | −0.029, p 0.669 | −0.035, p 0.694 | 0.795 |
| m35 (j09 beside the w50 mean) | 0.126 (0.14 / 0.14 / 0.11) | −0.063, p 0.900 | −0.061, p 0.741 | −0.067, p 0.898 | 0.977 |
| m25 (whole route, L5+8+20) | 0.084 (0.07 / 0.07 / 0.11) | −0.105, p 0.953 | −0.103, p 0.864 | −0.108, p 0.963 | 0.992 |

**Reading (dev, 159 tried).**
- **m23 is the first method that covers two gaps at once.** It pools the pedestrian view (L8 w50) with the whole-route
  view (L8) and scores 0.372. It matches B7-pool on FullyBlocked (0.35 against 0.33) and keeps the 0.59 pedestrian
  axis. It is ahead of every rival at p 0.03 to 0.06, but no interval excludes zero.
- **Whole-route summaries carry FullyBlocked:**
  - 0.35 at L5, L8, L20 and `all_tokens` L1.
  - L20 also scores 0.31 on BadParking, the best on that gap.
  - None of them finds the pedestrian group alone.
- **j09 does not carry to this pool:** 0.222, against 0.331 on H21. At L10 (m33) it scores 0.306, all on PedestriansOnRoad
  (0.67).
- **Frame summaries** (m29, m32) reach 0.32 to 0.33. m32's 0.67 on PedestriansOnRoad is the best on that gap.
- Every remaining tie with a rival is within its interval.

**Batch 4 pools** (rows written 2026-11-16 after batch 4's scores and before these five are scored; they bring the
batch to 30, the top of Chris's 20 to 30). m23 shows that pooling a pedestrian view with a whole-route view covers two
gaps. Whole-route L20 scored 0.35 on FullyBlocked and 0.31 on BadParking, so each row below pools a pedestrian view
with it, round-robin, skipping near-repeats (`pool_axes.py`). Script: `batch4.sh pools`.

| id | pooled sources | methods tried after |
|---|---|---|
| m40 | m39 (L8 w50, PCA 64) and whole-route L20 | 160 |
| m41 | m12 (L8 w6, average linkage, A2) and whole-route L20 | 161 |
| m42 | m32 (frames: mean and spread, L8) and whole-route L20 | 162 |
| m43 | L8 w50, whole-route L8 and whole-route L20 | 163 |
| m44 | L8 w50 and whole-route L20 | 164 |
