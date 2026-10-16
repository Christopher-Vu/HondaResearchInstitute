# Step 4 — Ablation over hook sites and layers

**Owner:** Chris (analysis), for a joint decision with Jerry. **Extends:**
`docs/steps/04-dev-pool-and-layer-sweep.md`, whose selection rule picked
driving queries at layer 10 and all-tokens at layer 18 (2026-10-15). **Status:**
fixed 2026-10-15 evening, before any result below exists. **Budget:** at most
1,000 SU, shared with one infra investigation.

## Why

The sweep ranks layer-site pairs on what can be *read* from them: failure
AUROC, state probes, practice-gap recovery. Two questions it leaves open:

1. **Is the choice robust?** The stability check changed the chosen set in 4 of
   5 resamples, it flips with the scikit-learn version, and every input came
   from one dev pool. Only layer 10 is well separated.
2. **Does the policy use what is read there?** A layer can encode a state that
   the driving head never consults. Discovery methods (SAE, contrastive,
   probe-residual) emit axes from the chosen site; an axis read from a site the
   policy ignores cannot pass the Step 7 causal check.

## Part A — Robustness of the selection (no GPU)

Data: the Step 2 rerun (array 39967810: 220 nominal Bench2Drive routes, a
different corpus from the dev pool, captured with all 24 layers at both sites
plus the vision bridge). No practice gap is in it, so gap recovery does not
apply; failure AUROC and state probes do. Sealed-pilot outputs are never used.

1. The sweep, unchanged (`src/discovery/layer_sweep.py`), on the rerun's shards.
2. **Resampling over base routes:** 50 resamples, each dropping a random fifth
   of the base routes (seeds 1000–1049), sweep rerun on each; report each pair's
   median position, its 5–95% range, and how often it is in the top 2 and top 3.
   (Amended before any result: drawing with replacement would duplicate shards,
   which the sweep's loader cannot do; this is its stability check, repeated.
   Cut from 100 to 50, also before any result: one sweep takes about 25 minutes
   and the shared CPU queue was a day long, so 100 would have cost about 42
   single-stream hours; 50 still resolves top-k shares to 2%.)
3. **Per family:** the same resamples ranked on failure AUROC alone and on state
   probes alone, since the combined rank averages families that can disagree.

## Part B — Causal knock-out, open loop (GPU, no simulator)

Data: saved model inputs from the Step 2 rerun (every 10th step). Draw 4
frames per scored route, seed 0: about 850 frames. Each frame is replayed in
bfloat16, as logged, once intact and once per condition.

**Knock-out.** For decoder layer L and a set of token positions P, replace the
layer's update at P (its output minus its input) with that update's mean over
a calibration set (100 frames from different routes, seed 1, excluded from
scoring). Mean rather than zero, so the residual stream stays in distribution.

| Site | Positions P |
|---|---|
| driving_queries | the 30 driving-query tokens (the last positions) |
| context | every other position: image and text tokens |
| all_tokens | every position |
| vision_bridge | one condition: the projector output replaced by its mean (layer-free) |

That is 24 × 3 + 1 = 73 conditions.

**Effect.** For each frame, the mean distance between the intact and the
knocked-out route waypoints (m), and the same for the speed waypoints (m).
Report the median and the 90th percentile over frames per condition, and the
share of frames whose route-waypoint shift exceeds 1 m.

**Reading, fixed now.** A layer is **live** at a site when its median route
shift is at or above the median over the 24 layers at that site. The profile
across layers shows where driving information enters the queries and where
the plan is set.

## Part C — Closed-loop check of a shortlist (GPU, simulator)

Open-loop shifts are a proxy. Three conditions, chosen from Part B by rule:

1. driving queries at the recommended layer (below);
2. the condition with the largest open-loop effect, if different, else the next;
3. a control: the driving-query layer with the smallest open-loop effect.

Each runs the knock-out live in the agent on the same 40 routes, drawn with
seed 0 from the Step 2 rerun's scored routes, same config otherwise. Compared
with the rerun's outcomes on those routes: driving score, failure count, paired
McNemar. About 120 routes, roughly 500 SU. If Part B already uses most of the
budget, Part C drops condition 3 first.

## Recommendation rule, fixed now

Recommend for logging the pairs that are, in order of priority:

1. in the top 3 by combined rank in Part A1, **and** chosen by the dev-pool
   sweep at some point (driving queries at 10, or 7, 9, 11, 12 in its
   stability resamples; all-tokens at 18). The full dev-pool ranks are in
   Jerry's Savio scratch, not in the repo, so only its choices can be compared;
2. in the top 3 in at least half of Part A2's resamples;
3. live in Part B.

A pair that passes 1 and 2 but not 3 is reported as "readable but not used".
If no pair passes all three, the recommendation is the one with the best Part
A2 median rank among live pairs, flagged as weak. The recommendation is input
for Chris and Jerry; it does not change the config by itself.

## Out of scope

Practice-gap recovery on a new corpus (needs a passing gap's rollouts in this
account), per-token pooling beyond layers 10 and 14, and any rerun of the
dev pool.

## Results (measured; interim section written 2026-10-15 22:50, final below)

**Part A1, the sweep on the Step 2 rerun** (212 nominal rollouts, 61 failing;
`04-ablation/partA1-sweep.json`). It chose **driving queries at layer 10**
(combined rank 6.3; failure AUROC 0.764, best of all 49 pairs) and layer 9
(8.6). The top six pairs are all driving-query layers 7 to 13. So the dev
pool's first pick replicates on a corpus it never saw. All-tokens layer 18,
picked in the dev pool for P4 recovery, ranks 27th of 49 here, where there is
no gap to recover.

**Part B, open-loop knock-out** (848 frames × 74 conditions, job 40012263;
`04-ablation/partB-summary.json`). Rerunning the intact model gives exactly 0 m
shift, so every non-zero effect is real. As a check, removing the last layer's
update at context tokens has no effect, because nothing downstream reads them.
Median route-waypoint shift:

| Knock-out | Effect |
|---|---|
| Any single middle layer (3–19), any site | 2–7 cm |
| Driving queries, layers 20–23 | route 5–34 cm; **speed 2.5–3.8 m** (the speed plan is set here) |
| Driving queries, layer 2 | speed 3.3 m |
| Context or all tokens, layer 0 | 93 cm (the first pass over image tokens) |
| Vision bridge (all image tokens to their mean) | 21 cm; 20% of frames over 1 m |

Under the pre-registered rule, live driving-query layers are 2, 9, 11, 14, 15,
16, 17, 18 and 20–23. **Layer 10 misses by 2.5 mm** (2.54 cm against a site
median of 2.79 cm). All-tokens layer 18 is not live (3.8 cm against 6.2 cm).

**How to read this.** Knocking out one layer's update measures that layer's own
computation, not whether information present at that layer is used later. The
middle layers each add little, and the plan is set late. That fits layer 10
being where failure-relevant state is most *readable* (Part A) while not itself
deciding much. The 2.5 mm miss is small next to the spread across
driving-query layers (1.1 to 34 cm), and no interval was put on these medians,
so "live" is a coarse filter here, not a verdict.

**Part A2, 50 resamples** (each dropping a fifth of the base routes;
`04-ablation/partA2-resamples.json`). Only two pairs are stable: driving queries
at **layer 11** (top 3 in 72% of resamples, median position 2.0) and **layer
10** (70%, 2.5). Next are layers 12 (38%) and 9 (36%). Layer 14, the second
per-token capture layer since Step 5, is top 3 in 16%.

**The rule's recommendation** (`04-ablation/recommendation.json`): driving
queries at layer 11, which passes all three criteria. Layer 10 is labelled
"readable but not used" because it misses the live line by 2.5 mm. In
practice 10 and 11 are tied.

**Part C, closed loop** (40 routes drawn with seed 0 from the Step 2 rerun, each
knock-out applied live; paired against the intact rerun on the same routes).
For scale, Jerry's intact Step 2 run against the rerun is the run-to-run
reference: same 9 failures, but 3 routes failed only in one run and 3 only in
the other.

| Knock-out (array) | Failures, of 40 | Only here / only intact | McNemar p | Mean DS |
|---|---|---|---|---|
| Intact, Jerry's Step 2 run (reference) | 9 | 3 / 3 | 1.0 | 91.3 |
| Intact, the rerun (baseline) | 9 | — | — | 91.7 |
| All tokens, layer 0, largest open-loop effect (40023867) | **31** | 24 / 2 | < 0.001 | **53.6** |
| Driving queries, layer 1, smallest open-loop effect (40023871) | 14 | 6 / 1 | 0.125 | 83.4 |
| Driving queries, layer 11, recommended (40027190 + 40028509) | 11 | 6 / 4 | 0.754 | 90.2 |

Five layer-11 routes first failed on infrastructure (agent set-up and
simulator timeouts, mostly on node n0217). They were rerun on other nodes;
the other two arrays lost none.

## What this means for the layer choice

1. **The readable layer is robust.** Driving queries at layers 10 and 11 come
   first on two unrelated corpora (the dev pool, and 212 nominal Step 2 routes)
   and under resampling. Nothing else is close. Recommendation: **keep driving
   queries at layer 10 as the logged site, and capture layer 11 per token
   instead of layer 14.** Layer 14 is rarely in the top three, and 10 and 11 are
   interchangeable on every measure here.
2. **No single middle layer is needed to drive.** Removing layer 11's own update
   changes nothing measurable in closed loop (11 against 9 failures, within the
   run-to-run reference). Removing the first layer's pass over all tokens
   collapses driving (31 of 40 fail), so the open-loop measure does find what
   matters when the effect is large. At 40 routes it cannot order small effects:
   the layer-1 control, the smallest open-loop effect, did slightly worse than
   layer 11.
3. **For Step 7's causal checks.** An axis read at layer 10 or 11 sits where
   failure-relevant state is most readable, but its single layer is not
   necessary, and the plan is set in layers 20 to 23. So a causal test that
   removes one mid-layer update will look null. Interventions should edit the
   residual stream along the discovered direction (steering), and closed-loop
   checks need more than 40 routes per arm to see effects of this size.
4. **All-tokens layer 18** was chosen in the dev pool only for recovering P4,
   and ranks 27th of 49 without a gap. Keep it only as the perceptual-gap site.

Cost: about 800 SU for the whole ablation plus the left-crossing work (per-job
accounting; closed-loop routes 658 of it), within the 1,000 cap.

