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

Queued: m05 (m03 at all 24 layers of `driving_queries` and `all_tokens`, plus `vision_bridge`: 49 configurations, so the
count of tried methods goes to 55; job 41325979) and m01 and m02 on `L10_k64_s0` and `L10_k32_s0` (job 41325980).
