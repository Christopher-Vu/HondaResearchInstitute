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

