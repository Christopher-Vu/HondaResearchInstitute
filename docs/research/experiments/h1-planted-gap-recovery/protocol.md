# H1: do the discovery methods recover failures we planted on purpose?

**Locked 2026-10-31, before any run on this corpus.** Dev only (`PRD.md` §9.2): it guides the project and is not a
result. Extends `docs/steps/dev-eval-pooled.md` (pre-registered 2026-10-22 for P4 alone) to the three planted gaps
that now pass efficacy. Where this file differs from that one, this file is the extension and says so.

## Question

Three failure causes were planted on purpose and each verified to cause failures (full pilots, PRD 9.1):

| Gap | What we did to the car | Slice failures (measured) |
|---|---|---|
| P4 camera occlusion | black patch over the middle of the camera | 43 of 60 |
| P7 camera freeze | camera image stalls 2 s of every 3 s | 53 of 56 |
| P8 camera latency | every image is 1 s old | 58 of 58 |

Mixed into a pool with background rollouts that fail for ordinary reasons, can a method that reads only the
policy's internal activations hand back a group of failing rollouts that matches each planted gap, and does it
beat methods that read only behaviour or metadata?

## Corpus

Every shard with a driving outcome (`success` not null) from:

- `share/dev-pool-wave1-shards`, `share/dev-pool-wave2-shards` (Step 4 background, random stock weather)
- `share/p4-main-shards` (P4 full pilot)
- `results/savio/step5-pilot-p7-main/shards`, `results/savio/step5-pilot-p8-main/shards`

Counts are recorded at load time in the results file and quoted from there, not from this table.

**Answer key for gap g:** the rollouts whose sidecar `practice_gaps` lists g and whose outcome is a failure. Only
the scoring step reads it. Neighbourhood routes of a pilot (same road, no fault) stay in the pool as background.

## Representation (fixed)

Tier 1 uses `driving_queries` frame means at **layer 10** for every rollout (the only representation every shard
has); layer 14 is a second run reported beside it. No per-token data in Tier 1.

## Methods

Activation methods (may read activations, state, infractions; never the key, never `sensor`/`practice_gaps`):

- **M1 contrastive**, over each SAE in `share/sae-sweep` at the run's layer, raw and with the catch-all cap 0.5.
  An SAE whose explained variance on these frame means is below 0.8 is reported but does not count.
- **M2 probe-residual** (M3a) on layer-10 frame means.

Baselines:

- **B1 random**: 200 draws, axis sizes from M1's axes.
- **B2 taxonomy**: scenario, weather, town, ability only.
- **B3 behavioural**: kinematics, state list and infractions in the 3 s before failure.
- **B7-pool**: activation statistics, pool variant.

## Metric

Per gap, a method's **best Jaccard**: the highest Jaccard between any of its axes and the gap's key. Catch-all
reference for gap g: |key(g)| / |all failures|, what an axis holding every failure scores.

## Claims and the rule (fixed before the run)

**Claim A, recovery.** For each planted gap, at least one activation method has an axis with best Jaccard
≥ 0.5 (`harness.scoring.MATCH_THRESHOLD`) that holds at most 50% of all failures.

**Claim B, activation advantage** (the pre-registered rule, applied to each gap separately):
1. Margin: the best activation method's best Jaccard exceeds both the best baseline's and the catch-all reference
   by at least 0.15, and the 95% base-route bootstrap interval (2,000 replicates, both "best" choices re-made in
   every replicate) of the difference from the best baseline excludes zero.
2. Not a catch-all: the winning axis holds at most 50% of all failures.
3. Stable: for SAE-based methods, at least 4 of the 6 seeds at the chosen layer and k beat the best baseline.

## Predictions (written before the run)

- Claim A holds for P7 and P8: a stale or late image changes what the vision tokens carry, so layer-10 means
  should separate those rollouts strongly. Less sure for P4 (it already failed to separate when it was 70%).
- Claim B is uncertain: P7/P8 cars also behave differently (late braking, collisions), so B3 may match them too.
  If B3 matches every activation method, that is the §13.1 early warning, reported as such.

## What would make this experiment wrong

- The methods find "is a pilot route" (ClearNoon, same roads) rather than the fault. Audit: compare each winning
  axis's overlap with the pilot neighbourhood routes; a fault axis should hold the slice and not the
  neighbourhood.
- The three camera faults share one signature, so one axis matches all three weakly. Audit: Hungarian assignment
  in `harness.scoring.score` credits an axis to one gap only.

## Clarifications made before the run (2026-10-31 22:42, no H1 data opened yet)

Points the protocol left open, settled while building `src/discovery/dev_eval.py`:

1. An SAE with explained variance below 0.8 on the frame means does not count for M1 or for B7-pool.
2. "Best activation method" is the maximum over every counting M1 run at the layer (all k and seeds, raw and
   capped) and M2. B7-pool from every counting run joins the baselines. The bootstrap re-takes both maxima in
   each replicate, so the interval covers that selection.
3. Rule 3 applies only when an SAE method wins. For an M2 winner it is not applicable and does not block Claim B.
   For an SAE winner, only runs of the same variant (raw or capped) at the same layer and k count. A run beats the
   baseline when it is strictly above the best baseline's point Jaccard.
4. "The interval excludes zero" means its lower bound is above 0. The 0.15 margins carry a 1e-9 float tolerance.
5. B1 runs once per SAE run, sized from that run's M1 raw axes. With no SAE, its axes are failures // 10.
6. The slice and neighbourhood audit counts members by sidecar `role`. `in_key` is recorded beside it.
7. Duplicate route ids across shard directories stop the run rather than overwrite.
