# H21b robustness rescores (work item 2)

Laptop worker 20261120-001011-21046, 2026-11-20. Dev data only. Nothing here can enter the UniAD read
(`docs/prereg-views.md`, tag `views-prereg-v1`). These are rescores of methods already logged, so the count of methods
tried stays 219. Every number below is **measured**: it was read from a report JSON in this folder. No number here is
a target or an estimate. The rows were written into `VARIANTS.md` (commit `75042ba`) before any score was read.

## Answer

- **Point scores (measured):** m23 scores above both rivals in every single-seed pool and in every leave-one-seed-out
  pool. Its smallest margins are in seed 25: +0.022 over B3-behaviour and +0.012 over B3-infraction.
- **Intervals (measured):** the m23 lead over B3-behaviour has a 95% interval above 0 only on the full pool and on
  the two-seed pools without seed 25 or without seed 26. This holds at all three bootstrap seeds. The interval
  includes 0 in each single seed and in the pool without seed 24. In s26 and no24 the lower end falls just below 0,
  between −0.016 and −0.002. **So the interval-backed lead over B3-behaviour does not hold in every seed or in every
  leave-one-out pool.**
- **Against B3-infraction (measured):** the 95% interval includes 0 in every pool at every bootstrap seed. The reading
  is unchanged: m23 is not separated from B3-infraction.
- **m23 does not rank first in every pool (measured):** j09 scores higher in s25 (0.420 against 0.349), and m40
  scores higher in s26 (0.385 against 0.330) and in no24 (0.356 against 0.352).
- **A small pool flatters B3-behaviour (measured):** refit on one seed, it scores 0.318 on s24 and 0.327 on s25,
  against 0.152 on the full pool. Each gap holds only 2 to 10 failing routes per seed, so one best-matching axis can
  move a gap's Jaccard by a lot.

## How it was run

- **Manifest:** `manifest.json` is the H21b manifest with `pair` = `base_id` minus its `-sNN` seed suffix (prereg A1).
  It has 600 entries and 100 pairs. With it, each bootstrap replicate resamples Fail2Drive pairs, and each pair
  carries its routes from every seed.
- **Pools:** rows of the pooled `cache.npz`, `cache-w50.npz` and `frames.npz`, selected by seed and kept in the
  pooled salted order (`pool_inputs.py subset`). `routes.jsonl` and the manifest were cut to the same routes. The
  pool was not rebuilt.
- **Refits:** every method was refit on its own pool's rows: m15-source, route-L8, m39-source and route-L20
  (`cache_methods.py`), j09, B3-behaviour, B3-infraction, and the two pooled lists m23 and m40. They must be refit,
  because PCA, standardisation, Ward clustering and the HMM all fit on the rows they cluster. B3-infraction has no
  fit, so on a subset it gives the same rule over fewer routes.
- **Scorer:** `sprint_score.py` under A2/A1, unchanged. Gaps, decoys and rivals are as in `results/h21/h21b/commands.sh`.
  Each method ranks its own axes and is scored on its own top 10. Each pool's rivals were refit on that pool.
- **Step 5:** m23's report was run with `--seed` 0, 1 and 2 (2,000 replicates each). The seed also drives the
  chance draws, which happen before the bootstrap. That is why seed 0 here gives [+0.034, +0.451] p 0.007 for
  m23 − B3-behaviour, while the independent scorer in `results/h21/repro/` gave [+0.041, +0.450] p 0.005. Same unit,
  different random stream.
- **Checks:** `commands.sh` ran end to end with exit 0. The per-seed route and failing counts match the
  H21b SUMMARY (measured): s24 200/52, s25 198/56, s26 195/66. s26 has 99 pairs, because pair f2d-59 has neither of its seed-26 routes in the pool. Those are among the
  7 failed drive tasks.

## Step 2: reproduction on the full pool, corrected manifest

All nine rebuilt axis files (m15-source, route-L8, m39-source, route-L20, j09, b3_behaviour, b3_infraction, m23, m40)
equal the recorded `results/h21/h21b/axes/` files.

| row | recorded | reproduced | equal | tag |
|---|---:|---:|---|---|
| m23 | 0.39464674758792406 | 0.39464674758792406 | yes | measured |
| B3-behaviour | 0.15227800692172758 | 0.15227800692172758 | yes | measured |
| B3-infraction | 0.2868686868686869 | 0.2868686868686869 | yes | measured |

m40 0.310 and j09 0.298 also equal their recorded scores (measured).

## Step 3: one seed at a time

Score = mean over the three gaps of the best Jaccard among the method's own top 10. CO = CustomObstacles,
W = Wall, PoR = PedestriansOnRoad. The full pool is repeated for reference.

| pool (seeds) | routes failing in gaps (CO / W / PoR) | m23 | m40 | j09 | B3-behaviour | B3-infraction | tag |
|---|---|---:|---:|---:|---:|---:|---|
| full (24+25+26) | 28 / 14 / 9 | 0.395 | 0.310 | 0.298 | 0.152 | 0.287 | measured |
| s24 (24) | 8 / 5 / 3 | 0.364 | 0.306 | 0.331 | 0.318 | 0.308 | measured |
| s25 (25) | 10 / 5 / 4 | 0.349 | 0.295 | 0.420 | 0.327 | 0.337 | measured |
| s26 (26) | 10 / 4 / 2 | 0.330 | 0.385 | 0.197 | 0.124 | 0.216 | measured |

## Step 4: leave one seed out

| pool (seeds) | routes failing in gaps (CO / W / PoR) | m23 | m40 | j09 | B3-behaviour | B3-infraction | tag |
|---|---|---:|---:|---:|---:|---:|---|
| full (24+25+26) | 28 / 14 / 9 | 0.395 | 0.310 | 0.298 | 0.152 | 0.287 | measured |
| no24 (25+26) | 20 / 9 / 6 | 0.352 | 0.356 | 0.246 | 0.162 | 0.278 | measured |
| no25 (24+26) | 18 / 9 / 5 | 0.348 | 0.308 | 0.275 | 0.126 | 0.261 | measured |
| no26 (24+25) | 18 / 10 / 7 | 0.447 | 0.259 | 0.330 | 0.250 | 0.321 | measured |

## Step 5: m23 against each rival, every pool

Delta, 95% percentile interval and one-sided p, from a paired bootstrap that resamples Fail2Drive pairs with all
their seeds. 2,000 replicates.

| pool | bootstrap seed | pairs | m23 − B3-behaviour | m23 − B3-infraction | tag |
|---|---:|---:|---|---|---|
| full | 0 | 100 | +0.242 [+0.034, +0.451] p 0.007 | +0.108 [-0.093, +0.336] p 0.173 | measured |
| full | 1 | 100 | +0.242 [+0.041, +0.452] p 0.007 | +0.108 [-0.090, +0.335] p 0.172 | measured |
| full | 2 | 100 | +0.242 [+0.038, +0.459] p 0.007 | +0.108 [-0.091, +0.335] p 0.182 | measured |
| s24 | 0 | 100 | +0.046 [-0.164, +0.368] p 0.387 | +0.056 [-0.148, +0.384] p 0.333 | measured |
| s24 | 1 | 100 | +0.046 [-0.159, +0.350] p 0.374 | +0.056 [-0.156, +0.373] p 0.335 | measured |
| s24 | 2 | 100 | +0.046 [-0.159, +0.362] p 0.382 | +0.056 [-0.161, +0.374] p 0.342 | measured |
| s25 | 0 | 100 | +0.022 [-0.195, +0.301] p 0.443 | +0.012 [-0.190, +0.302] p 0.443 | measured |
| s25 | 1 | 100 | +0.022 [-0.189, +0.306] p 0.451 | +0.012 [-0.177, +0.293] p 0.438 | measured |
| s25 | 2 | 100 | +0.022 [-0.196, +0.293] p 0.461 | +0.012 [-0.195, +0.290] p 0.458 | measured |
| s26 | 0 | 99 | +0.205 [-0.002, +0.477] p 0.028 | +0.114 [-0.071, +0.370] p 0.126 | measured |
| s26 | 1 | 99 | +0.205 [-0.016, +0.460] p 0.032 | +0.114 [-0.071, +0.353] p 0.137 | measured |
| s26 | 2 | 99 | +0.205 [-0.011, +0.467] p 0.032 | +0.114 [-0.079, +0.363] p 0.141 | measured |
| no24 | 0 | 100 | +0.190 [-0.012, +0.422] p 0.035 | +0.074 [-0.101, +0.339] p 0.250 | measured |
| no24 | 1 | 100 | +0.190 [-0.010, +0.431] p 0.036 | +0.074 [-0.107, +0.336] p 0.249 | measured |
| no24 | 2 | 100 | +0.190 [-0.009, +0.419] p 0.035 | +0.074 [-0.103, +0.331] p 0.261 | measured |
| no25 | 0 | 100 | +0.222 [+0.035, +0.468] p 0.005 | +0.087 [-0.098, +0.351] p 0.223 | measured |
| no25 | 1 | 100 | +0.222 [+0.028, +0.463] p 0.009 | +0.087 [-0.102, +0.340] p 0.224 | measured |
| no25 | 2 | 100 | +0.222 [+0.032, +0.463] p 0.007 | +0.087 [-0.098, +0.342] p 0.236 | measured |
| no26 | 0 | 100 | +0.197 [+0.031, +0.454] p 0.010 | +0.125 [-0.051, +0.394] p 0.086 | measured |
| no26 | 1 | 100 | +0.197 [+0.020, +0.440] p 0.013 | +0.125 [-0.062, +0.368] p 0.099 | measured |
| no26 | 2 | 100 | +0.197 [+0.022, +0.429] p 0.011 | +0.125 [-0.051, +0.361] p 0.083 | measured |

## Step 6: m23 sensitivity (exploratory)

Full pool, with one setting changed at a time. The rivals keep their recorded top 10. W is the number of last frames
from `frames.npz` averaged into the window slot. The W = 50 rebuild equals `cache-w50.npz` byte for byte (measured).
M is m23's own budget. M = 5 is the first 5 of the pooled list. M = 15 is the same round-robin with the cap raised
to 15, scored with the scorer's M = 15. Only 14 distinct axes survive the Jaccard-0.8 filter. The four extra axes
match no gap better than the first 10, so the score is unchanged.

| setting | m23 axes scored | m23 score | CO / W / PoR | m23 − B3-behaviour | m23 − B3-infraction | tag |
|---|---:|---:|---|---|---|---|
| W 50, M 10 (recorded setting) | 10 | 0.395 | 0.210 / 0.529 / 0.444 | +0.242 [+0.034, +0.451] p 0.007 | +0.108 [-0.093, +0.336] p 0.173 | measured |
| W 20, M 10 | 10 | 0.308 | 0.210 / 0.529 / 0.185 | +0.156 [+0.007, +0.321] p 0.019 | +0.021 [-0.137, +0.203] p 0.388 | measured, exploratory |
| W 50, M 5 | 5 | 0.343 | 0.168 / 0.529 / 0.333 | +0.191 [+0.005, +0.407] p 0.021 | +0.057 [-0.135, +0.277] p 0.301 | measured, exploratory |
| W 50, M 15 | 14 | 0.395 | 0.210 / 0.529 / 0.444 | +0.242 [+0.054, +0.462] p 0.003 | +0.108 [-0.085, +0.350] p 0.160 | measured, exploratory |
| W 100, M 10 | — | not computable: frames.npz stores at most 50 frames | — | — | — | — |

**W = 100 was not run.** `frames.npz` stores at most 50 frames per route (`n_frames` is 21 to 50). A last-100 slice
would return the W = 50 window and repeat that row.

## Per-gap detail (all pools)

| pool | method | CustomObstacles | Wall | PedestriansOnRoad | tag |
|---|---|---:|---:|---:|---|
| full | m23 | 0.210 | 0.529 | 0.444 | measured |
| full | m40 | 0.169 | 0.429 | 0.333 | measured |
| full | j09 | 0.194 | 0.440 | 0.261 | measured |
| full | B3-behaviour | 0.191 | 0.165 | 0.101 | measured |
| full | B3-infraction | 0.394 | 0.200 | 0.267 | measured |
| s24 | m23 | 0.188 | 0.571 | 0.333 | measured |
| s24 | m40 | 0.186 | 0.400 | 0.333 | measured |
| s24 | j09 | 0.308 | 0.400 | 0.286 | measured |
| s24 | B3-behaviour | 0.300 | 0.278 | 0.375 | measured |
| s24 | B3-infraction | 0.364 | 0.227 | 0.333 | measured |
| s25 | m23 | 0.213 | 0.333 | 0.500 | measured |
| s25 | m40 | 0.185 | 0.200 | 0.500 | measured |
| s25 | j09 | 0.176 | 0.333 | 0.750 | measured |
| s25 | B3-behaviour | 0.231 | 0.417 | 0.333 | measured |
| s25 | B3-infraction | 0.400 | 0.278 | 0.333 | measured |
| s26 | m23 | 0.156 | 0.500 | 0.333 | measured |
| s26 | m40 | 0.156 | 0.500 | 0.500 | measured |
| s26 | j09 | 0.174 | 0.250 | 0.167 | measured |
| s26 | B3-behaviour | 0.222 | 0.111 | 0.040 | measured |
| s26 | B3-infraction | 0.417 | 0.120 | 0.111 | measured |
| no24 | m23 | 0.191 | 0.364 | 0.500 | measured |
| no24 | m40 | 0.169 | 0.400 | 0.500 | measured |
| no24 | j09 | 0.145 | 0.259 | 0.333 | measured |
| no24 | B3-behaviour | 0.207 | 0.196 | 0.083 | measured |
| no24 | B3-infraction | 0.409 | 0.186 | 0.238 | measured |
| no25 | m23 | 0.182 | 0.462 | 0.400 | measured |
| no25 | m40 | 0.161 | 0.364 | 0.400 | measured |
| no25 | j09 | 0.256 | 0.368 | 0.200 | measured |
| no25 | B3-behaviour | 0.191 | 0.125 | 0.062 | measured |
| no25 | B3-infraction | 0.391 | 0.170 | 0.222 | measured |
| no26 | m23 | 0.184 | 0.727 | 0.429 | measured |
| no26 | m40 | 0.176 | 0.400 | 0.200 | measured |
| no26 | j09 | 0.294 | 0.364 | 0.333 | measured |
| no26 | B3-behaviour | 0.242 | 0.156 | 0.350 | measured |
| no26 | B3-infraction | 0.381 | 0.250 | 0.333 | measured |

## Not verified

- Whether the per-seed and leave-one-out numbers would match a pool rebuilt from each seed's own cache
  (`results/savio/f2d-h21b/s24..s26/`). Subsetting rows of the pooled archives keeps each seed's NaN padding to width
  1,492. B3-behaviour drops NaN frames, so the padding should not matter, but nobody has checked it here.
- The sensitivity rows cover one pool and one change at a time. They are exploratory and select nothing.

## Files

`commands.sh` reproduces everything from a clean clone. Set `POOL`, `H21B`, `WORK` and `PY` if your paths differ.
It calls `pool_inputs.py` (corrected manifest, subsets, window caches, round-robin with a cap) and `summarize.py`
(the step-2 gate and the tables in `tables.md`). Reports are in `<pool>/report-*.json`, with the m23 reports at
bootstrap seeds 0, 1 and 2 as `report-m23-seed{0,1,2}.json`. Axes are in `<pool>/axes/`, and the sensitivity
reports are in `sensitivity/`.
