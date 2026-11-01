# H4: a lag probe finds a delayed camera

**Locked 2026-11-01 00:43. EXPLORATORY**: designed after the H2 diagnostic found that a ridge probe from
layer-10 activations to the logged lead distance fits best 20 policy steps (1 s) in the past on P8 slice rollouts
and at lag 0 on their twins.

## Method (no answer key; reads activations and logged world state, as M2 does)

1. Fit ridge probes from layer-10 frame means (64 PCA components) to each continuous logged state that tracks the
   world moving (lead distance; also lead relative speed and junction distance where present), on **successful
   background rollouts only** (waves 1 and 2).
2. For every failing rollout, find the lag L in 0 to 6 logged frames (0 to 1.5 s) that minimises the probe's error
   when its prediction at frame t is compared with the true state at frame t - L, using frames where the ego moves
   (speed above 1 m/s at both ends). Skip rollouts with fewer than 10 such frames.
3. One axis: failing rollouts whose best lag is at least 3 logged frames (0.75 s) on the majority of their usable
   states. The threshold is fixed here, before scoring.

## Metric and rule

Jaccard of that axis with each gap's key, and its share of failures, slice/neighbourhood audit as in H1.
**Success:** Jaccard with P8 at least 0.5, holding at most 50% of failures. Report what it does to P4 and P7 too.

## Prediction

P8 recovered above 0.5; P7 partly caught (frozen frames are also late); P4 and background mostly absent.
