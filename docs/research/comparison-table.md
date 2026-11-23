# Comparison table: which view finds a driving model's Fail2Drive gaps

Built 2026-11-22 from the scored reports (paths at the end). The UniAD column is the **interim** blind read (routes
driven by Sat 2026-11-21 09:00 PT); the final read (job 41710304) replaces it. Rules: `docs/prereg-views.md`.

**How to read a cell.** Score = rank-averaged best match (for each gap, the best Jaccard overlap between the gap's
failing routes and any of a method's first k axes, averaged over k = 1..10; then the mean over units). Below it, the
row minus B3-behaviour with its 95% pair-bootstrap interval (2,000 draws, Fail2Drive pairs resampled). **Bold** = the
interval lies above 0, i.e. the row ranks above what a fleet already sees.

## Primary units (rule units without Wall)

| Row | SimLingo alone¹ | TF++ alone¹ | UniAD alone (blind, interim) | Pooled, 3 models (interim) |
|---|---|---|---|---|
| **caption** (frames → descriptions → grouping) | 0.169<br>**+0.038 [0.006, 0.077]** | 0.169<br>**+0.103 [0.033, 0.143]** | 0.076<br>**+0.038 [0.005, 0.081]** | 0.152<br>**+0.062 [0.029, 0.090]** |
| `query-mean` (query tokens, window mean) | pending² | 0.046<br>−0.019 [−0.052, −0.004] | 0.208<br>**+0.169 [0.047, 0.206]** | 0.125<br>+0.036 [−0.000, 0.064] |
| `img-mean` (image tokens, window mean) | pending² | 0.063<br>−0.002 [−0.046, 0.038] | 0.112<br>+0.073 [−0.019, 0.123] | 0.098<br>+0.008 [−0.022, 0.033] |
| m23 (frozen activation finalist) | 0.150<br>+0.019 [−0.036, 0.089] | 0.062<br>−0.003 [−0.042, 0.032] | 0.037<br>−0.002 [−0.031, 0.010] | 0.096<br>+0.007 [−0.026, 0.038] |
| m40 (second finalist) | 0.154<br>+0.023 [−0.049, 0.097] | 0.045<br>−0.020 [−0.055, −0.005] | 0.041<br>+0.002 [−0.027, 0.016] | 0.092<br>+0.003 [−0.034, 0.035] |
| B3-infraction (rival: infraction log) | 0.147<br>+0.016 [−0.011, 0.051] | 0.106<br>**+0.040 [0.013, 0.076]** | 0.060<br>**+0.021 [0.003, 0.047]** | 0.115<br>**+0.026 [0.009, 0.048]** |
| B7-pool (rival: sparse dictionary on queries) | 0.076<br>−0.055 [−0.106, 0.001] | 0.022<br>−0.044 [−0.086, −0.019] | 0.015<br>−0.024 [−0.062, −0.003] | 0.044<br>−0.045 [−0.074, −0.022] |
| **B3-behaviour** (primary rival: speed/behaviour) | 0.131 | 0.066 | 0.039 | 0.089 |
| B2 oracle (uses labels; ceiling only) | 0.312 | — | — | — |
| Coverage | 1,185 routes, 357 failing | 1,071 routes, 230 failing³ | 869 routes, 552 failing | 3,125 routes |
| Units | 7 | 6 | 3 | 16 |

¹ Outcomes already read before these rows were scored (labelled so). UniAD is the only blind read.
² SimLingo-alone `img-mean` / `query-mean` are being scored now (job 41710326); they are in the pooled column already.
³ TF++ frames come from a re-drive; only pairs whose failure reproduced are kept (172 of 257 pairs; route match 423/524).

**Partial order (A ranks above B only if A − B's interval lies above 0):**
- **Pooled:** caption ranks above B3-behaviour, B3-infraction, B7, `img-mean`, m23, m40; it **ties** `query-mean`.
  Best new view re-selected per draw: caption in 87% of draws, +0.062 [0.033, 0.090] vs B3-behaviour.
- **UniAD alone:** `query-mean` ranks above every row including caption (+0.131 [0.033, 0.174]); selected in 96% of
  draws, +0.169 [0.075, 0.206]. Caption ranks above B3-behaviour, B7, m23, m40.
- **TF++ alone:** caption ranks above every row except B3-infraction (tie). Selected in 100% of draws.
- **SimLingo alone:** caption is the only row whose interval clears B3-behaviour.

## Other unit sets

| Row minus B3-behaviour | SimLingo, all rule | SimLingo, named | TF++, all rule | TF++, named | UniAD, all rule | Pooled, all rule | Pooled, named |
|---|---|---|---|---|---|---|---|
| caption | **+0.041 [0.009, 0.080]** | +0.069 [−0.000, 0.146] | **+0.098 [0.033, 0.149]** | **+0.193 [0.023, 0.337]** | **+0.048 [0.019, 0.085]** | **+0.064 [0.030, 0.098]** | **+0.118 [0.026, 0.208]** |
| `query-mean` | pending | pending | −0.029 [−0.059, −0.011] | −0.023 [−0.088, 0.000] | **+0.120 [0.030, 0.150]** | +0.021 [−0.008, 0.046] | +0.035 [−0.046, 0.123] |
| `img-mean` | pending | pending | −0.010 [−0.050, 0.025] | −0.002 [−0.078, 0.091] | +0.047 [−0.022, 0.089] | −0.000 [−0.027, 0.021] | +0.015 [−0.043, 0.086] |
| m23 | **+0.055 [0.002, 0.118]** | +0.093 [−0.036, 0.247] | **+0.082 [0.038, 0.116]** | +0.023 [−0.062, 0.131] | −0.010 [−0.032, 0.004] | **+0.051 [0.019, 0.081]** | +0.065 [−0.033, 0.172] |
| m40 | +0.060 [−0.019, 0.142] | +0.130 [−0.027, 0.291] | **+0.064 [0.025, 0.083]** | −0.016 [−0.081, 0.010] | −0.004 [−0.027, 0.008] | **+0.048 [0.008, 0.083]** | +0.072 [−0.036, 0.173] |
| B3-infraction | +0.018 [−0.006, 0.048] | +0.027 [−0.021, 0.084] | **+0.038 [0.010, 0.070]** | +0.040 [−0.006, 0.131] | **+0.029 [0.008, 0.055]** | **+0.028 [0.010, 0.048]** | +0.033 [−0.007, 0.093] |

UniAD's named class is empty in the interim (no named gap passed the rule there), so it has no named column.
m23/m40 gain on "all rule" units mostly through Wall, which is why Wall is out of the primary set.

## Where the leads come from (per unit, primary units)

| Model | Row | Per-unit score |
|---|---|---|
| UniAD | `query-mean` | FullyBlocked 0.08 · **PedestriansOnRoad 0.42** · RightConstruction 0.13 |
| UniAD | caption | FullyBlocked 0.05 · PedestriansOnRoad 0.13 · RightConstruction 0.04 |
| UniAD | B3-behaviour | 0.04 · 0.05 · 0.02 |
| TF++ | caption | Animals 0.20 · BadParking 0.16 · FullyBlocked 0.29 · OppositeConstr. 0.06 · PedOnRoad 0.22 · RightConstr. 0.07 |
| TF++ | B3-behaviour | 0.12 · 0.05 · 0.07 · 0.04 · 0.08 · 0.03 |
| SimLingo | caption | BadParking 0.11 · CustomObstacles 0.32 · FullyBlocked 0.14 · Crowd 0.09 · OtherBlocker 0.07 · PedOnRoad 0.36 · RightConstr. 0.09 |
| SimLingo | B3-behaviour | 0.18 · 0.17 · 0.07 · 0.13 · 0.05 · 0.16 · 0.17 |

- UniAD `query-mean`'s lead is mostly one axis that is exactly PedestriansOnRoad's 14 failing routes (track queries
  fill with pedestrians). Plausible, but one unit carries it; check before quoting it as general.
- Caption's lead is spread across types on TF++ and SimLingo. Its mode names match Fail2Drive's type words often (the
  inserted object is in view), so axes are flagged as expected by the prereg; per-type scores sit beside B2's ceiling.

## Caveats to state with the table
- 219 tries in total across the project (prereg count); the views are 3 of them. Selection is corrected by
  re-selecting the best new view in every bootstrap draw.
- SimLingo and TF++ outcomes were read before these rows were scored; only UniAD is blind.
- Units are small (4–46 failing routes per gap; UniAD primary has 3 units), so intervals are wide and per-unit swings
  are large.
- The caption row uses an external language model (Claude Opus 5.5) on camera frames: it is a strong
  "describe what's in view" baseline, not a readout of the driving model's internals.

## Sources
- SimLingo: `hri-tfpp/results/savio/f2d-views/caption-c/score-{nowall,rule,named}.json`
- TF++: `hri-tfpp/results/savio/f2d-views/caption-d/score-{nowall,rule,named}.json`
- UniAD and pooled (interim): `hri-dev/results/savio/f2d-views/uniad-test-interim-20261122-0332/caption/*.json`
- Scorer: `docs/research/experiments/f2d-unpooled/view_score.py`
