# Research log

Decision timeline for the planted-gap recovery goal. Newest entry at the bottom. Times are Pacific.

## 2026-10-31 22:40 — bootstrap

**Goal (from Jerry):** prove the discovery SDK finds failures we planted in CARLA, explain how, keep an extensive
log, end with an explainer video; 6,000 SU allowed.

**Where we start (measured earlier today):** three planted camera faults pass their full pilots: P4 occlusion
(43/60 slice failures vs 12/60), P7 freeze (53/56 vs 15/60), P8 latency (58/58 vs 12/60). Shards with layer means
exist for all of them and for 384 background rollouts.

**Why the earlier attempt failed:** the first dev evaluation (2026-10-15) had P4 as 70% of failures, so an axis of
every failure scored 0.70 and no method could beat that. With P7, P8 and both background waves pooled, each planted
gap is roughly a fifth of the failures, so a catch-all scores about 0.2 and real recovery can show.

**Decision:** lock H1's protocol before touching data (`experiments/h1-planted-gap-recovery/protocol.md`), then
build the mechanical code the 2026-10-22 spec listed as missing. Savio's login dropped at about 22:30, so the run
waits for the user; code and tests go first.

## 2026-10-31 22:55 — code and the Tier 2 corpus, while Savio is down

- **Protocol locked** in `10b02ce` before any data was opened.
- **Evaluation code** delegated to a Sonnet subagent (single module, clear spec): `src/discovery/dev_eval.py` gets
  layer-mean input, M2 probe-residual, B3, the 0.5 cap, per-gap best Jaccard with a slice-vs-neighbourhood audit,
  and a per-gap base-route bootstrap.
- **Tier 2 corpus prepared** (`cf268d3`): background wave 3, 200 routes with per-token capture at layers 10 and
  11, so the per-token SAE can read background and pilots alike. `dev_routes.py` gained a `background_role`
  option because the background-only path hard-coded wave 2's id offset (a third wave would have reused its ids).
  Expected cost about 820 SU at 4.1 SU per route (unmeasured for this wave). Submit when Savio is back.

## 2026-10-31 22:40 (Savio clock) — Savio back, wave 3 submitted, corpus counted

- Wave 3 submitted as array 40715498 (100 tasks, 200 routes). SU baseline for this goal: **6,595.83** used by
  imhaohao at 2026-11-01 05:35 UTC, read with `check_usage.sh` just before the submission. Ceiling: 12,596.
- Tier 1 corpus, counted from the sidecars (measured):

| Source | Rollouts with an outcome | Failures | Key |
|---|---|---|---|
| wave 1 | 189 | 29 | (P1, P2 slices count as background) |
| wave 2 | 195 | 56 | |
| P4 pilot | 120 | 55 | P4: 43 |
| P7 pilot | 116 | 68 | P7: 53 |
| P8 pilot | 118 | 70 | P8: 58 |
| **Pool** | **738** | **278** | |

  Catch-all references (an axis holding every failure): P4 43/278 = 0.155, P7 53/278 = 0.191, P8 58/278 = 0.209.
  Each planted gap is 15 to 21% of failures: far closer to PRD §9.1's assumed 4 to 8% than the old 70%.
- 36 SAE runs are available in `share/sae-sweep` (layers 10 and 14, k 32/48/64, seeds 0 to 5).

## 2026-10-31 23:10 — H1 Tier 1, layer 10: the activation methods were not actually tested

First run (40715529/31) failed: Savio's policy venv had no scikit-learn (B3 and M2 need it). Added
scikit-learn 1.5.2 with uv, pinned numpy 1.26.4 and scipy 1.15.3; a dry run showed only four new packages and no
changes, so wave 3's running CARLA jobs were not touched. Rerun as 40715554 (layer 10), 40715555 (layer 14).

**Layer 10 result (measured, confirmatory per the locked protocol):** Claim A no and Claim B no for all three gaps.
But the audit says this is not a verdict on the methods:

| Gap | Catch-all | B2 taxonomy | B3 behaviour | M2 probe-residual | M1 (exploratory, does not count) |
|---|---|---|---|---|---|
| P4 | 0.155 | 0.219 | 0.176 | 0 (no axes) | 0.551 |
| P7 | 0.191 | 0.270 | 0.176 | 0 (no axes) | 0.206 |
| P8 | 0.209 | 0.296 | 0.200 | 0 (no axes) | 0.242 |

- **Flaw 1, representation.** All 18 layer-10 SAEs score explained variance about -0.5 on frame means (worse than
  predicting the mean). They were trained on single driving-query tokens; a frame mean over 30 tokens is a
  different input. By the protocol they do not count, so M1 and B7 sat out. Even so, the best of 18 M1 runs found a
  P4 axis at Jaccard 0.55 (exploratory; selected over 18 runs, so optimistic).
- **Flaw 2, M2 emitted no axes at all.** Cause unknown; being audited.
- **B2's best axis is a 196-rollout stratum holding 71% of failures** (the pilot routes' shared metadata); it beats
  the catch-all only because the pilot pairs are failure-dense.

**Decision:** the Tier 1 rule cannot test activation methods while the only SAEs do not fit the shared input.
Two fixes, both pre-registered before running: H1b (exploratory) trains SAEs on the pooled frame means themselves;
Tier 2 (confirmatory, per the protocol) waits for wave 3's per-token data. M2's empty output goes to an audit agent.
A slim copy of the 750 shards (layer means and state only, 6.5 GB) is being copied to the laptop so agents can work
without competing for Savio's single session.

## 2026-10-31 23:30 — layer 14 matches layer 10; frame-mean SAEs fit

- **Layer 14 Tier 1 (40715555), measured:** identical baseline numbers to layer 10, M2 empty, token SAEs misfit.
  The Tier 1 verdict stays "activation methods not tested".
- **H1b SAEs:** `sae.py` gained `--frame-means` (`c92d31c`). One run, L10 k48 seed 0, trained on 170,822 frames of
  all 750 shards (labels never read) in 3.4 min on the laptop CPU: **held-out explained variance 0.922**, dead
  fraction 0, 5% of latents never fired on held-out frames. The other 35 runs are training, four at a time.
- **M2 audit** handed to a Sonnet agent working on the local slim shards.
- Wave 3: 9 of 100 tasks done after about 70 minutes, 6 running.

## 2026-10-31 23:40 — M2 audit: a valid null, not a bug

Sonnet audit agent, on the local slim shards (measured):

- Data and integration are sound: 738 rollouts (460 successes, 278 failures), every state array present, no NaN
  activations. All six probes fit on 58,518 success frames.
- Failing windows give 3,276 residual frames, real and varied. **Every frame is HDBSCAN noise** at the
  pre-registered `min_cluster_size` 60 (whose default `min_samples` also becomes 60): the residuals form one
  dense blob with heavy tails, and HDBSCAN never selects a single cluster by default. So M2 emits no axes.
- **There is a signal, but it is shared:** standardised residual RMS on held-out success frames vs failing
  windows: lead distance 0.45 vs 0.89, lead relative speed 0.59 vs 1.12, pedestrian distance 0.42 vs 1.00,
  occlusion 0.75 vs 1.12, red light 0.54 vs 0.86, time to junction 0.37 vs 0.35. Before a failure the policy
  mis-reads its surroundings about twice as much, but every failure looks alike to these probes.
- Tuning (`min_samples` 5) still gives 0 axes: the best cluster has 2 rollouts against the support floor of 20.

**Decision:** report M2 as "no axes under the pre-registered settings". No tuning: it would be exploratory, and
the probes' state list (lead, pedestrian, light, junction, occlusion) does not name camera staleness or a blacked-out
centre, so M2 is the wrong tool for these three gaps by construction. Logged as a finding.

## 2026-11-01 00:20 — H1b layer 10: P4 recovered; P7 and P8 found together, not apart (EXPLORATORY)

18 frame-mean SAEs at layer 10, held-out explained variance 0.904 to 0.93 (all count). Run locally in 1 min 48 s.
Output: `docs/research/data/h1b_layer10.json`. Measured:

| Gap | Catch-all | Best baseline | Best M1 | Winning axis | Claim A | Claim B |
|---|---|---|---|---|---|---|
| P4 occlusion | 0.155 | B2 0.219 | **0.574** (capped, L10 k32 s4) | 31 rollouts: 27 in key, 31 slice, 0 neighbourhood | yes | yes: delta +0.355 [+0.264, +0.520], stable |
| P7 freeze | 0.191 | B7 0.278 | 0.207 (a 77% catch-all) | | no | no |
| P8 latency | 0.209 | B7 **0.444** | 0.276 | B7: 59 rollouts, 58 slice, 36 in key, 0 neighbourhood | no | no |

Audit:
- The P4 axis is clean: precision 27/31 = 0.87, recall 27/43 = 0.63, no P4 neighbourhood rollout. A latent fires on
  the blacked-out camera image, which is exactly the planted cause.
- B7's P8 axis holds 58 pilot slice rollouts but only 36 are P8 failures. The other 22 are slice failures of the
  other pilots (P7 is the obvious candidate; to be checked). So B7 found a shared "stale camera" signature, and
  merging two gaps caps its Jaccard with either.
- M1's P7 axes are catch-alls.

**Mechanism hypothesis (H2):** P4 changes what is in the image, so a per-frame latent can fire on it. P7 and P8
show a real, normal-looking image, only at the wrong time. M1 scores frames one by one, so it is blind to timing;
B7 counts onsets over the whole rollout, which is why it partly sees them. A temporal signal (how much the
activations change from frame to frame) should expose P7 (identical activations for 40 steps out of 60) and
perhaps P8. Diagnostic sent to a research agent before any new method is built.

## 2026-11-01 00:40 — H2 diagnostic: timing faults need timing features (EXPLORATORY, oracle numbers)

Sonnet research agent, local slim shards, layer 10, d_t = relative change of the frame mean between consecutive
logged frames (5 policy steps apart). Measured:

- **P7 freeze has a clean, label-free signature.** Exact-zero changes (d_t < 1e-3) occur in 52 of 60 P7 slice
  rollouts and in 0 of the other 698. They happen when the car is stopped and the image is frozen: the activations
  are bitwise identical. Best oracle Jaccard with P7's key: 0.906 for "any exact-zero step" (48 of 48 predicted are
  P7 failures). While the car moves, frozen frames only lower d_t (0.128 vs 0.188 median), because the speed input
  still changes. The 5 missed P7 failures are short crashes with the car moving throughout.
- **P8 latency has no such signature.** Every cheap statistic that separates P8 slice from its twins (median d_t,
  autocorrelation, length) tracks "the car is stuck": P7 and P8 slice rollouts last a median of 484 and 489 logged
  frames against 85 to 92 for their neighbourhoods, at 0.5 m/s mean speed against 4.6 to 5.1.
- **A latency-specific signal exists, but it needs a probe.** A ridge probe from layer-10 activations to the
  logged lead distance, fitted on background rollouts, fits best at a lag of 4 logged frames (exactly 20 steps,
  1 s) in 21 of 42 P8 slice rollouts and at lag 0 in 38 of 49 neighbourhood rollouts.
- **Confound flagged:** stuck-ness. B7's mixed P7/P8 group may be partly "stuck failures". Any P7/P8 claim must
  beat rollout length (oracle Jaccard 0.628 for P7 ∪ P8) and mean speed (0.605).

## 2026-11-01 00:45 — outer loop: where this stands and what proves it

What we know: the SDK found P4 from activations alone, in a realistic mix, beating every baseline (exploratory).
Timing faults are a blind spot of per-frame methods, explained mechanistically (a stale image is a normal image).

What is missing for "prove": every positive so far is exploratory. The SAE recipe and the evaluation were settled
after seeing H1's data, and the same P4 rollouts were used to see the result. A proof needs **fresh planted
rollouts** evaluated by a **pipeline fixed before they are opened**.

**Decision: DEEPEN and CONFIRM in parallel.**
- **H3, confirmatory:** fresh P4 and P7 pilots (new base draws, new traffic seeds, new route ids), pooled with
  wave 3's background; the pipeline is fixed in H3's protocol before any H3 rollout is read. Submitted now so the
  GPU time overlaps with method work.
- **H2, exploratory:** add one label-free temporal latent (stale frame: the activations did not change since the
  last logged frame) to contrastive diffing, and test it on the H1 pool. If it recovers P7 without hurting P4, it
  joins H3's fixed pipeline before H3's data are opened. P8's lag probe is noted, not built yet.
