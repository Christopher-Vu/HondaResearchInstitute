# H3: does the SDK find planted failures in rollouts nobody has looked at?

**Locked 2026-11-01 00:15, before any H3 rollout exists. CONFIRMATORY.** Dev only (PRD §9.2); this is the
project's first test of a fixed discovery pipeline on fresh planted data.

## Why

Everything found so far (P4 recovered in H1b) is exploratory: the SAE recipe was chosen after H1's data were seen,
and the same rollouts were used to judge it. H3 runs the same kinds of faults on new rollouts and judges a
pipeline that is frozen before those rollouts are opened.

## Fresh data

| Pool part | Config | What is new |
|---|---|---|
| P4 occlusion, 60 pairs | `configs/rollout/step5-confirm-p4.yaml` | base draw (generator seed 7), traffic seed 11, id offset 5 |
| P7 freeze, 60 pairs | `configs/rollout/step5-confirm-p7.yaml` | base draw (generator seed 8), traffic seed 12, id offset 7 |
| Background, 200 routes | `configs/rollout/step5-background-wave3.yaml` | already running (array 40715498) |

The fault definitions are unchanged (`gaps/practice/practice_v2.yaml`). Base routes may coincide with H1's (the
draws are independent), but every rollout is new. P8 is left out: H2 found no label-free signature for it.

**Answer key:** failing slice rollouts of each pilot, read only by scoring. Rollouts without an outcome are dropped,
with no reruns (a route that crashes is lost, as in deployment).

## The fixed pipeline

1. Train TopK SAEs on the `driving_queries` frame means of every H3 shard at layer 10 (`sae.py --frame-means`),
   k in {32, 48, 64}, seeds 0 to 5. No labels.
2. M1: contrastive diffing over those latents, raw and capped at 0.5 (`dev_eval.py`, as in H1b).
3. **H2's stale-frame latent joins M1 only if** H2 (run on the H1 pool, before any H3 rollout is opened) shows it
   recovers P7 with Jaccard ≥ 0.5 without lowering P4's best Jaccard. That decision is committed to this file
   before H3's evaluation runs; otherwise M1 runs without it.
4. Baselines as in H1: B1, B2, B3, B7-pool. M2 is run and reported.

## Claims (as H1, applied to P4 and P7 separately)

- **Claim A:** an activation method has an axis with Jaccard ≥ 0.5 holding at most 50% of failures.
- **Claim B:** the best activation method beats the best baseline and the catch-all by ≥ 0.15, the base-route
  bootstrap interval of the margin is above 0, and at least 4 of 6 seeds agree.

## Predictions

- P4: Claims A and B hold (H1b gave 0.574 with margin +0.355).
- P7: without the stale-frame latent, Claim A fails (H1b gave 0.207). With it, Claim A holds.
- Stuck-ness confound: a P7 axis must beat rollout length; its slice/neighbourhood audit is reported.

## Cost

About 240 pilot routes. P7 routes stall and run long; the H1 pilots cost about 1,000 SU each with reruns
(measured from usage). Expected under 2,000 SU, within the 6,000 SU budget.

## Amendment (2026-11-01 00:20, before any H3 rollout was opened)

H2's rule failed for M1 (`docs/research/research-log.md`, 00:20), so M1 runs without the stale latent as stated
above. In addition, the whole evaluation runs a second time with `--stale-latent` and is reported beside the first.

- **Claim A′ (SDK level):** for each gap, at least one label-free activation-reading method (M1 raw or capped, or
  B7-pool) has an axis with Jaccard ≥ 0.5 holding at most 50% of failures. Claims A and B are unchanged, with B7
  still a baseline.
- **Predictions:** without the stale latent, Claim A′ holds for P4 only. With it, Claim A′ holds for P4 and P7,
  P7 through B7.
