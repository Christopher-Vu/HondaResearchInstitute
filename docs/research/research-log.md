# Research log

Decision timeline for the planted-gap recovery goal. Newest entry at the bottom. Times are Pacific.

## 2026-10-31 22:30 — bootstrap

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

## 2026-10-31 22:32 — code and the Tier 2 corpus, while Savio is down

- **Protocol locked** in `10b02ce` before any data was opened.
- **Evaluation code** delegated to a Sonnet subagent (single module, clear spec): `src/discovery/dev_eval.py` gets
  layer-mean input, M2 probe-residual, B3, the 0.5 cap, per-gap best Jaccard with a slice-vs-neighbourhood audit,
  and a per-gap base-route bootstrap.
- **Tier 2 corpus prepared** (`cf268d3`): background wave 3, 200 routes with per-token capture at layers 10 and
  11, so the per-token SAE can read background and pilots alike. `dev_routes.py` gained a `background_role`
  option because the background-only path hard-coded wave 2's id offset (a third wave would have reused its ids).
  Expected cost about 820 SU at 4.1 SU per route (unmeasured for this wave). Submit when Savio is back.

## 2026-10-31 22:35 — Savio back, wave 3 submitted, corpus counted

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

## 2026-10-31 22:59 — H1 Tier 1, layer 10: the activation methods were not actually tested

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

## 2026-10-31 23:24 — layer 14 matches layer 10; frame-mean SAEs fit

- **Layer 14 Tier 1 (40715555), measured:** identical baseline numbers to layer 10, M2 empty, token SAEs misfit.
  The Tier 1 verdict stays "activation methods not tested".
- **H1b SAEs:** `sae.py` gained `--frame-means` (`c92d31c`). One run, L10 k48 seed 0, trained on 170,822 frames of
  all 750 shards (labels never read) in 3.4 min on the laptop CPU: **held-out explained variance 0.922**, dead
  fraction 0, 5% of latents never fired on held-out frames. The other 35 runs are training, four at a time.
- **M2 audit** handed to a Sonnet agent working on the local slim shards.
- Wave 3: 9 of 100 tasks done after about 50 minutes, 6 running.

## 2026-10-31 23:26 — M2 audit: a valid null, not a bug

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

## 2026-11-01 00:09 — H1b layer 10: P4 recovered; P7 and P8 found together, not apart (EXPLORATORY)

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

## 2026-11-01 00:14 — H2 diagnostic: timing faults need timing features (EXPLORATORY, oracle numbers)

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

## 2026-11-01 00:14 — outer loop: where this stands and what proves it

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

## 2026-11-01 00:20 — H2: the stale-frame latent finds P7, but through B7, not M1 (EXPLORATORY)

Output `docs/research/data/h2_layer10.json`. Measured, layer 10, same pool as H1b:

| Gap | M1 best | B7-pool best | B7's axis |
|---|---|---|---|
| P4 | 0.574 (unchanged) | 0.091 | |
| P7 | 0.207 (unchanged) | **0.906** | 48 rollouts: 48 P7 slice failures, 0 neighbourhood, 0 other |
| P8 | 0.276 (unchanged) | 0.350 | 50 slice, 0 neighbourhood |

- B7's 0.906 equals the diagnostic's oracle ceiling, reached here with no threshold tuned on the key.
- **Why M1 misses it (diagnosed):** M1 looks at the 3 s before each failure. Only 3 failing rollouts have a stale frame
  inside that window (support 3 against a floor of 20; it fired in 0 of 460 success windows). A P7 car's frozen,
  stopped frames are spread over a long stall that mostly precedes the last 3 s. B7 counts over the whole rollout.
- Widening M1's window to 30 s or the whole rollout does not help (best P7 0.10 to 0.17) and hurts P4 (0.574 to
  0.21 to 0.47): M1 ranks latents by effect × support and merges overlapping ones, so a narrow signal never founds
  its own axis.
- **H2's pre-registered rule** (M1 must reach 0.5 on P7) **fails**. The stale latent does not join H3's M1.

**Reading:** the SDK has two complementary detectors. Contrastive diffing (M1) finds causes visible in what the
model sees just before failing (P4). Whole-rollout activation statistics (B7) find causes that act over time, once
the activations expose timing (P7 with the stale latent). M1's window is a real blind spot for slow failures.

**H3 amendment** (committed before any H3 rollout is opened): run H3's pipeline twice, without and with the stale
latent, and report both. Claims A and B keep B7 as a baseline. A new Claim A′ asks the SDK-level question: does any
label-free activation-reading method, B7 included, return an axis with Jaccard ≥ 0.5 that holds ≤ 50% of failures?

## 2026-11-01 00:28 — correction: timestamps

Headers from 22:30 onward had been written from estimated times, some running up to an hour ahead of the clock.
Each is now the time of the commit that recorded it (`git log`). No content changed.

## 2026-11-01 00:42 — layer 14 replicates the direction, not the strength (EXPLORATORY)

18 layer-14 frame-mean SAEs, held-out explained variance 0.900 to 0.937. Data: `docs/research/data/h1b_layer14.json`,
`h2_layer14.json`. Measured:

| Gap | Layer 10 best activation | Layer 14 best activation | Layer 14 claims |
|---|---|---|---|
| P4 | M1 0.574 | M1 0.435 (79 rollouts, 61 slice, 5 neighbourhood) | A no (below 0.5), **B yes**: delta +0.216 [+0.162, +0.320], stable |
| P7, stale latent | B7 0.906 | B7 0.906 (the same 48 rollouts) | A′ yes |
| P8 | B7 0.444 | B7 0.395 | none |

- P4 is found at both layers and beats every baseline at both, but layer 10 gives the cleaner group. This matches
  Step 4's independent choice of layer 10 as the logged site.
- The stale latent is layer-independent, as expected: a frozen, stopped car repeats its activations at every layer.
- Spare note: the failed P4-confirm task (array 40716226 task 2) lost neighbourhood route 468345 to a CARLA crash at
  start-up (exit 139). H3 allows no reruns, so that pair is lost.

## 2026-11-01 00:45 — H4 lag probe: specific to camera faults, not to P8 (EXPLORATORY, locked rule fails)

Sonnet research agent ran the locked protocol on the local pool. Per-rollout table (no key columns):
`docs/research/data/h4_lag_probe_table.csv`. Probes fitted on 299 successful background rollouts (layer 10, 64 PCA
components): lead distance R² 0.79, lead relative speed 0.55, junction distance 0.79 (in-sample). Measured:

| Gap | Key | In axis and key | Jaccard |
|---|---|---|---|
| P4 | 43 | 6 | 0.071 |
| P7 | 53 | 13 | 0.148 |
| P8 | 58 | 27 | **0.342** (rule needs 0.5: fails) |

- The axis (48 failures, 17% share) is **almost entirely camera faults**: 46 pilot slice rollouts (27 P8, 14 P7,
  6 P4... by source dir: p8 27, p7 14, p4 6), 1 neighbourhood, 1 background. Only 2 of 124 failures outside every
  key landed in it. The probe detects "perception runs late" for any stale or degraded camera, not latency alone.
- Recall is limited by stalling: 18 of 70 P8 failures had too few moving frames to measure a lag at all.
- Post hoc (not the rule): requiring the lag to be exactly 4 (the planted delay) gives Jaccard 0.100; at least 4
  gives 0.278. Neither rescues it.

**Reading:** a delayed camera is the hardest of the three. Its activations look like normal driving shifted in
time, and the cars it breaks mostly stop moving, which erases the one signal that is specific to delay. P8 stays
unrecovered; logged as a limit of the current toolbox, not tuned further.

## 2026-11-01 01:27 — explainer video, first draft

Storyline "One road, three drives" (`video/STORYLINES.md`, `video/SPEC.md`), built with HyperFrames by a Sonnet
subagent: 126 s, 1920x1080, narration -17.1 LUFS, true peak -1.6 dB (measured, not heard). Every number on screen
reads from `video/data.js`; the 896-bar columns are real layer-10 activations from shards 2640642 and 2640638
(the two frozen frames, steps 190 and 195, differ by exactly 0.0). Two claims were caught and fixed in the script
before recording: "278 crashed for ordinary reasons" (154 of the 278 are planted) and "its top suspect" (the P4
axis was the 9th of 10).

Review of the draft: story, data and motion right; heroes too small and parked in corners. Sent back for a layout
pass. The draft narration is macOS's Daniel voice (free); an ElevenLabs take was priced at about 1,912 credits
(about $0.70) and not bought, pending Jerry's OK.

## 2026-11-01 02:05 PST — H3 rollouts, progress check

Measured on Savio: wave 3 at 85 of 100 tasks complete (1 failed), P4-confirm at 36 of 60 (1 failed), P7-confirm
at 8 of 60. Recent tasks take 6 to 20 minutes each and about 6 run at once across the three arrays, so the rest
(about 90 tasks) should finish in roughly 4 hours. SU spent since the goal started: 998 (sacct CPU time x 3.67),
well inside the 6000 budget. Nothing to act on until the arrays finish.

## 2026-11-01 02:27 PST — H3 post-processing queued

Rollout arrays only write raw captures to `results/savio/<array job>/`; shards and scores come from a follow-up job,
which had not been queued for H3. Queued now, each starting when its array ends (`afterany`): wave 3 40719024
(score and export, from a one-off sbatch outside the repo, `../wave3_post.sbatch`, because `step4_wave2.sbatch`
is tied to wave 2's paths), P4-confirm 40719025 and P7-confirm 40719026 (both `scripts/step5_pilot.sbatch`, which also
gives the PRD 9.1 efficacy verdict). Outputs: `results/savio/step5-background-wave3`, `step5-confirm-p4`,
`step5-confirm-p7`. Measured at 02:25: wave 3 96 of 100 tasks, P4-confirm 37 of 60, P7-confirm 8 of 60; 1075 SU spent.
Lost so far, no reruns per protocol: wave 3 task 12, P4-confirm task 2.

## 2026-11-01 03:29 PST — wave 3 background ready

Wave 3 rollouts and export finished (job 40719024): 200 shards, 199 with an outcome (147 fine, 52 failed, 1 without
an outcome), against 56 failures of 195 in wave 2 (measured). Audit: stride 5 and capture_every 10 match waves 1 and
2, the town mix matches, median rollout length 380 steps against 399. The slim copy first read as 409 MB and then
658 MB; both were `du` lag on scratch, and the finished copy is 1.3 GB on the laptop, in line with wave 2.

One thing to carry into H3's reading: the pool is smaller than H1's, so each planted fault will be a bigger share of the
failures (estimated near a quarter to a third, against 15 to 21% in H1). The catch-all reference rises with it, so Claim
B's bar over the catch-all is harder here. The protocol stays as locked.

Measured at 03:25: P4-confirm 51 of 60 tasks, P7-confirm 12 of 60; 1380 SU spent.

## 2026-11-01 04:47 PST — P4-confirm: the planted fault works again on fresh drives

Measured (`results/savio/step5-confirm-p4/efficacy.json`, job 40719025): of 120 routes, 118 have an outcome. Lost and
not rerun, per the protocol: 1171535 and 468345. Slice 46 of 59 failed (78.0%), neighbourhood 9 of 59 (15.3%): uplift
62.7 points, Fisher p 5.7e-12, so the PRD 9.1 verdict of record passes. The paired test (C23) has 37 slice-only
failures against 0 neighbourhood-only, McNemar p 1.5e-11; it reports `passes: false` only because 58 pairs is short
of its minimum of 60. This verdict says the fault breaks driving; it says nothing yet about whether the tool finds it.
P7-confirm is at 22 of 60 tasks; 1654 SU spent.

## 2026-11-01 09:10 PST — P7-confirm: the freeze breaks driving again; all H3 drives are in

Measured (`results/savio/step5-confirm-p7/efficacy.json`, job 40719026): 118 of 120 routes have an outcome; lost and not
rerun: 2365937 and 2585737. Slice 54 of 58 failed (93.1%), neighbourhood 19 of 60 (31.7%): uplift 61.4 points, Fisher p
1.1e-12, so PRD 9.1 passes. Paired: 36 slice-only failures against 0 neighbourhood-only, McNemar p 2.9e-11; C23 reports
`passes: false` only because 58 pairs is under its minimum of 60.

The H3 pool is now complete: 439 shards, 180 failures with an outcome (wave 3 52, P4-confirm 46 + 9, P7-confirm 54 + 19).
The answer keys are therefore 46 (26% of failures) and 54 (30%), so the catch-all reference is about 0.26 and 0.30.
2237 SU spent; all Savio jobs for H3 are done. Next: 36 frame-mean SAEs on this pool, then the locked evaluation.

## 2026-11-01 09:29 PST — H3 result: the frozen pipeline finds both faults on fresh drives (CONFIRMATORY)

Run exactly as locked: 18 frame-mean SAEs at layer 10 on all 439 H3 shards (k 32, 48, 64; seeds 0 to 5), then
`dev_eval.py` without and with `--stale-latent`. Data: `docs/research/data/h3_layer10_plain.json`, `h3_layer10_stale.json`.
`research-state.yaml` said 36 SAEs; that was my mistake, the protocol's grid at one layer is 18.

Sanity: every SAE counts (held-out explained variance 0.875 to 0.922, none skipped). The pool scored is 435 rollouts with
180 failures. I recomputed both answer keys from the shard metadata, separately from `dev_eval.py`: 46 and 54, no overlap.

| Gap | Key | Catch-all | Best M1 | Best baseline | B7-pool, plain | B7-pool, stale |
|---|---|---|---|---|---|---|
| P4 occlusion | 46 | 0.256 | **0.557** (49 rollouts, 34 in key, 4 clean twins) | 0.354 B2 | 0.116 | 0.065 |
| P7 freeze | 54 | 0.300 | 0.340 | 0.415 B2 | 0.541 | **0.889** (48 rollouts, all in key) |

Claims against the locked rules:

- **P4: Claim A holds, Claim B holds.** Margin +0.204 over B2, bootstrap interval +0.108 to +0.350, 5 of 6 seeds.
- **P7: Claim A fails, Claim B fails** (M1 0.340), as predicted; B7 counts as a baseline for those two claims.
- **P7: Claim A′ holds with the stale latent** (B7 0.889, 27% of failures), as predicted.
- **Claim A′ also holds for P4** through M1.
- **One prediction failed:** I predicted that without the stale latent Claim A′ holds for P4 only. B7 reaches 0.541 on
  P7 without it. See the length audit below for why that is weak evidence.

Audits, done because the numbers looked good:

- **Rollout length (the stuck-ness confound the protocol names).** Taking the N longest failing rollouts, the best N
  reaches Jaccard 0.48 on P7 and 0.26 on P4. So plain B7's 0.541 (only 2 of 18 SAEs reach 0.5, median 0.09) barely beats
  a stopwatch, and I do not count it as a real recovery. The stale-latent axis at 0.889 clearly beats length, and it
  holds none of P7's clean twins (the 19 neighbourhood failures), which length-only would pick up.
- **Best-of-18 selection.** 0.557 is the maximum over the dictionaries. Only 3 of 18 reach 0.5 on P4; the median is 0.405
  (range 0.31 to 0.557). The median still beats the best baseline and the catch-all. The rule is what was locked, and
  the honest sentence is "the method finds P4 in some dictionaries, and most seeds at the winning size beat the baselines".
- **Chance.** A random group of 49 of the 180 failures would hold 34 or more of the 46 P4 failures with probability about
  3e-15 (hypergeometric). Even across every axis of every dictionary, chance does not explain it.
- **What the P7 axis is.** All 18 SAEs give the same 0.889 because the winning axis is the stale latent itself, which does
  not depend on the SAE. It is a frozen-input detector read from activations, chosen by H2 on the old pool and then fixed;
  the dictionary adds nothing to it. It misses the 6 P7 failures whose frames never repeat exactly.
- M2 returns no axes again.

**What this means.** H1b and H2 were exploratory. H3 ran the same pipeline, frozen in advance, on drives nobody had opened, and
both results came back close to their earlier values: P4 0.574 to 0.557, P7 0.906 to 0.889. **Limits:** this is dev data
with practice gaps; the choice of "best axis" uses the answer key, as the scoring rule defines, so a user without a key
would still have to look at the top groups; and P8 was left out of H3 because no label-free signature exists for it.
H1's Tier 2 (per-token SAEs on the whole pool) was not run; wave 3 captured the tokens, and it stays possible.

## 2026-11-01 09:37 PST — final video; goal finished

`video/renders/final.mp4`: 130 s, 1920x1080, 30 fps, -17.1 LUFS, true peak -1.6 dB (measured, not heard). The fresh-drive
scene now shows the H3 result (0.56, best of 18 dictionaries with median 0.41; 0.89, 48 drives, none wrong), and the closing
line reads "two of three faults found". The closing card and the description carry https://github.com/trycua/cua. The
voice is macOS Daniel; Jerry chose to keep it over a paid ElevenLabs take.

Final spend for the goal: 2237 of 6000 SU (sacct CPU time x 3.67). No Savio jobs remain. Log headers from 02:05 onward were
corrected to their commit times; I had written estimates again (the H3 entry said 09:50 for a 09:29 commit).

## 2026-11-01 10:45 PST — H5 protocol: three interactional gaps to screen

Jerry asked to start screening interactional gaps, the kind the go/no-go rule is decided on. Locked in
`docs/research/experiments/h5-interactional-screen/protocol.md` before any route ran; gaps in
`gaps/practice/practice_v3.yaml`. Insight from re-reading P5 and P6: both met a car starting from rest, so "at speed" was never
tested. P10 is a faster walker seen later, P11 a crossing from the camera's blind side against the mirror-image patch, P12 walkers at
Fail2Drive's distance. One small code change: `crossing-timing.patch` makes the walker's speed and start time parameters, stock defaults
kept. Screens only; a full pilot is Jerry's call.
