# Unpooled activations: is the information averaged away?

**Status:** protocol, grid and decision rule fixed 2026-11-18, before any score. Chris's request, 2026-11-18 (voice).
Every row below is a try and counts toward the total (202 before this experiment).

## Question

All 202 tries used activations mean-pooled within each frame, then over frames, and the probe diagnostic
(`../f2d-dev-simlingo/probe-diagnostic.md`) used the same pooled features. Does patch-level information that pooling
averages away separate the Fail2Drive gaps better than pooled activations and than fleet-observable behaviour?

## Data

- **SimLingo test pool** (1,188 scored routes, `results/savio/f2d-test-simlingo/shards`). **Its outcomes were
  already read** (it was round 1 and 2's dev pool); every result on it is labelled that way. Only UniAD is blind.
- **Frames:** every route saved the model's own input every 10 steps (`capture/inputs/<step>.pt`; checked
  2026-11-18: 1,188 of 1,188 routes, saved/expected frames min 0.97, median 0.99). The VARIANTS.md note of
  2026-11-14 ("no camera frames were saved") looked at the shards only and is corrected there.
- **Replay** (`replay_unpooled.py`): the saved input is run again offline in bfloat16. Replay is deterministic
  (Step 3); every frame's per-layer mean is checked against the logged one and a route is refused above 0.05 absolute.
- **Dev:** a few routes are replayed first for bug-catching only. No setting below is chosen on any score.

## The grid (fixed now): 3 sites × 3 aggregations = 9 rows

Sites:
- `vit`: InternVL's vision tokens entering the projector (2 tiles × 256 tokens, width 4096).
- `llm10`: the same 512 image tokens in the language model's layer 10 output (width 896).
- `dq`: the driving-query tokens at layer 10, unpooled (from the closed-loop log).

Aggregations, over the approach window: the last 25 saved frames before the failure step, or the route's last
25 for a passing route. That is 12.5 s, the same span as the w50 window of the earlier rows.
- `max`: the maximum over tokens and window frames.
- `topk`: in each frame, the mean of the k tokens farthest (L2) from the route's own baseline. The baseline is the
  per-position mean of its first 4 saved frames. Then the mean over window frames. k = 16, or 4 for `dq`, which has
  only 11 tokens.
- `codebook`: every token of the last 8 saved frames before the failure step, projected to 256 dimensions by a fixed
  Gaussian matrix (seed 0). Then k-means with k = 64 (seed 0), fit on up to 200,000 tokens sampled evenly from all
  routes with frames. The route's feature is its normalised histogram over the 64 codes.

**Discovery** is the same for every row: m03, the round-1 base pipeline in `cache_methods.py`. Standardise, PCA to
32 over all routes, Ward clustering of the failing routes, A2 distinct axes, top 10. Everything before clustering is
label-free and fit on all routes of the pool, as m03's PCA is. So no fold is needed, and "within each fold" in the
plan applies only to the probe ceiling.

## Reference rows

- `vit` and `llm10` with `mean` aggregation: the matched pooled rows. They are new views and count as tries.
- `dq-mean`: equivalent to the earlier window mean at layer 10. Re-run, not counted.
- **DINOv2-base on the same two tiles**, the image-model ceiling: the 3 aggregations above on its patch tokens. These
  are 3 tries.
- **B3-behaviour** and **m23** as already defined (rivals, not tries).
- **Probe ceiling:** `probe_diagnostic.py`'s logistic probe (folds by pair, AUROC) on each row's route features. It is
  label-reading, not a try, and is reported only.

Tries in this experiment: 9 + 2 + 3 = **14**. The running total becomes 216.

## Units and metrics

- **Units:**
  - SimLingo's 3 pre-registered gaps (PedestriansOnRoad, FullyBlocked, BadParking).
  - Every other Fail2Drive type whose generalisation failure rate is at least 1.5× its base twins' rate, with at least
    5 failing generalisation routes (`units_rule.py`).
  - Amended 2026-11-18, before any score: the rule reads the scored pool's own outcomes, not the seed-24 screen. The
    screen has about 6 routes per type, so "at least 5 failing" could almost never be met there. The rule reads
    outcomes only, never a method's axes or score, and on UniAD it runs inside the one blind read.
  - Both the named subset and all units are reported.
- **Primary metric:** per-gap rank-averaged best match, the average-precision analogue for set-valued axes. For a
  gap, it is the mean over k = 1..10 of the best Jaccard among the method's top-k axes. Then the mean over units, each
  weighted equally. It rewards a method that ranks the matching axis early, and moves smoothly where top-10 Jaccard is
  a step.
- **Secondary:** top-10 best-match Jaccard, the sprint metric, reported beside it.
- **Intervals:** a pair bootstrap, 2,000 draws, resampling Fail2Drive pairs. Contrasts are paired on the same draws.
  The pooled interval is a fixed mean over units, with no random effect.

## Decision rule (committed before any score)

- **Unpooled works** if the best of the 9 grid rows beats both comparators on the test pool. Comparators: its own
  site's `mean` row, and B3-behaviour. "Beats" means the pooled pair-bootstrap 95% interval of the paired difference
  in rank-averaged best match lies above 0. The best row is re-selected inside every bootstrap draw, the max over the
  9, so the interval pays for the selection.
- **The image model separates gaps** if the best of the 3 DINOv2 rows, re-selected in every draw, beats B3-behaviour
  in the same sense.
- **Reading:**
  - Unpooled works: pooling was the bottleneck, and the best unpooled row becomes the headline method.
  - The image model separates gaps and unpooled does not: a clean negative about what the policy's internals carry.
  - Neither: a sample-size limit, documented with the probe ceiling.
- Whatever the reading, the full grid is reported with the try count, and the settled row enters the views
  pre-registration (`docs/prereg-views.md`) as a named row before the one UniAD read.

## Other models (for the views pre-registration)

- **TransFuser++:** re-driven Fail2Drive pairs that contain a failure, with input capture. A pair is used only where
  its failure reproduces (same status, same first infraction type), and the match rate is reported. Sites: the image
  backbone's output grid and the decoder-join tokens.
- **UniAD:** routes driven after its unpooled capture landed. Sites: the coarsest FPN level per camera, the last BEV
  encoder grid (4×4 pooled to 50×50), and the track queries.
- On both models every preparation step (PCA, codebook, baseline) is fit only on routes that have the capture. The
  reference rows are re-scored on the same routes, so contrasts stay paired. Coverage (routes, pairs, failing per gap)
  is stated beside every row.
