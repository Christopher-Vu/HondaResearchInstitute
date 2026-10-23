# Dev evaluation on a pooled corpus: the pass rule

**Status: draft 2026-10-22, pending review by Chris and Jerry. Nothing has run.** This file fixes what counts
as "methods separate" before anyone sees the numbers, as `b7-gap-signal.md` did for B7. Any change made after
the run is labelled post hoc wherever the result is quoted. Dev only (`PRD.md` §9.2): it guides decisions and
is not a result.

## Why

The first dev evaluation (`docs/WHAT_BROKE.md`, 2026-10-15) could not separate methods. P4 was 51 of its 73
failures, so an axis holding every failure scored Jaccard 0.70, and every method, random included, sat at
0.70 to 0.74 across six SAE seeds. `PRD.md` §9.1 assumes a gap is 4 to 8% of a pool; this evaluation brings
P4 down to a minority without new rollouts.

## Corpus

Tier 1 uses only shards already readable from Jerry's Savio account (checked 2026-10-22). All three were
captured every 10th step, stride 5, bfloat16.

| Shards (`/global/scratch/users/imhaohao/share/`) | Rollouts with an outcome | Failures | P4 failures |
|---|---|---|---|
| `dev-pool-wave1-shards` (Step 4 wave 1) | 189 | 29 | 0 |
| `dev-pool-wave2-shards` (Step 4 wave 2) | 195 | 56 | 0 |
| `p4-main-shards` (P4 full pilot) | 120 | 55 | 43 |
| **Pooled** | **504** | **140** | **43 (30.7%)** |

Wave 1's P1 and P2 slices failed efficacy and count as background. Rollouts with no outcome are dropped.

Tier 2, run only after Chris grants read access: the same evaluation on his Step 2 rerun (array 39967810,
219 routes with per-token capture at layers 10 and 14) plus `p4-main-shards`, using per-token SAE input.
His failure count and whether those routes are exported as shards are not yet checked.

## Fixed choices

1. **One representation for every rollout.** The background waves hold only per-frame layer means, so every
   rollout, P4 included, is encoded from `driving_queries` at layer 10 (and 14 as a second run), never from
   per-token data in Tier 1. Mixing the two would let a method find the capture format instead of the gap.
   The SAEs in `share/sae-sweep` were trained on per-token data; if an SAE's explained variance on the layer
   means is below 0.8, its rows are reported but do not count toward the rule, and only the non-SAE methods
   are read.
2. **Methods:** contrastive diffing (raw and capped), SAE-based contrastive for each of the 36 sweep runs,
   probe-residual (M3a). **Baselines:** B1 random (200 draws, sized from the contrastive axes), B2 taxonomy
   (scenario, weather, town, ability only; it never reads `sensor.camera_fault`), B3 behavioural, B7-pool.
3. **Catch-all cap: 0.5** of all failures per latent and per axis, set now. A perfect P4 axis holds 30.7%.
4. **Bootstrap** over base routes (`base_id`), not rollouts, because P4's slice and neighbourhood share base
   routes. 2,000 replicates; the "best" method and best baseline are re-chosen in every replicate (as
   `PRD.md` §13.1 requires).

## The rule

Reference: an axis of every failure scores best Jaccard with P4 of 43 / 140 = **0.31**.

**Methods separate** only if all three hold:

1. **Margin.** The best activation method's best Jaccard with P4 exceeds both the best baseline's and 0.31 by
   at least **0.15**, and the 95% bootstrap interval of the difference from the best baseline excludes zero.
2. **Not a catch-all.** The axis achieving it holds at most 50% of all failures.
3. **Stable.** For SAE-based methods, at least 4 of the 6 seeds at the chosen layer and k beat the best
   baseline on their own.

## How each outcome is read

| Outcome | Reading | Next |
|---|---|---|
| Rule passes | Methods isolate a planted gap in a realistic mix. Necessary, not sufficient: P4 is the easy perceptual control | Tier 2; build interactional gaps |
| B3 matches or beats every activation method | Early warning for §13.1's go/no-go: internals may add nothing over behaviour | Discuss before more SU on gaps |
| Everything within 0.05 of 0.31 | Methods cannot find even P4 once diluted | Stop and re-plan before more SU |
| Anything else | Inconclusive; report as is | Tier 2 decides |

## Not yet built

`src/discovery/dev_eval.py` reads per-token data only and lacks B3, probe-residual, the 0.5 cap and the
base-route bootstrap. Those changes are mechanical and wait for sign-off of this file.
