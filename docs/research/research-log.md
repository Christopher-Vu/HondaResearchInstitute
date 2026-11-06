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

## 2026-11-01 10:29 PST — H5 protocol: three interactional gaps to screen

Jerry asked to start screening interactional gaps, the kind the go/no-go rule is decided on. Locked in
`docs/research/experiments/h5-interactional-screen/protocol.md` before any route ran; gaps in
`gaps/practice/practice_v3.yaml`. Insight from re-reading P5 and P6: both met a car starting from rest, so "at speed" was never
tested. P10 is a faster walker seen later, P11 a crossing from the camera's blind side against the mirror-image patch, P12 walkers at
Fail2Drive's distance. One small code change: `crossing-timing.patch` makes the walker's speed and start time parameters, stock defaults
kept. Screens only; a full pilot is Jerry's call.

## 2026-11-01 12:15 PST — H5 result: no interactional gap passes its screen

All jobs ended by 12:07 PST. 58 of 60 routes scored. Measured, screens only, dev data. The per-route table is
`docs/research/data/h5_manipulation.json`, made by `experiments/h5-interactional-screen/manipulation_check.py`.

| Gap | Pairs | C24 check, first 5 slice routes (4 needed) | Slice-only | Neighbourhood-only | Excess (3 needed) | Fails: slice, neighbourhood | Walker struck: slice, neighbourhood |
|---|---|---|---:|---:|---:|---|---|
| P10 late fast crossing | 9 | 3, fails, so **untested** | 2 | 0 | 2 | 4 of 9, 2 of 9 | 2, 0 |
| P11 blind-side crossing | 10 | 4, holds | 4 | 2 | 2 | 6 of 10, 4 of 10 | 2, 1 |
| P12 walkers at speed | 10 | 3, fails, so **untested** | 3 | 1 | 2 | 4 of 10, 2 of 10 | 2, 0 |

**Verdict under the locked rule:** P11 was tested and fails. P10 and P12 are reported as untested. Two predictions failed: P12
did not pass, and neither did my 60% guess that one of the three would. The P11 prediction held: it failed with both arms failing.

**The check I wrote is flawed, and I did not override it.** It asks for a walker within 15 m while the car is above 4 m/s. A
car that sees the walkers and brakes early fails that, so the measure counts good driving as "the hazard did not happen". Across all
P10 and P12 slice routes there are 6 misses: 3 are the car slowing below 4 m/s first, and in 3 no walker ever came within 15 m. Read
afterwards (exploratory), the car was above 4 m/s when a walker first came within 30 m in 7 of 9 P10 slice routes and 9 of 10 P12
slice routes. Waiving the check changes nothing, because both gaps still reach only 2 of the 3 excess failures required.
Distances are sampled every 0.5 s.

**What the failures were.**
- **P10:** the slice routes struck 2 walkers and the neighbourhood struck none. Only one of the two slice-only failures is the walker
  (26406). In the other (26408) the car moved for only 3.4 s between 15 s and 215 s, never came near a walker, then hit a vehicle. That is the
  stall I flagged at 10:55. Same-seed runs do not reproduce (`docs/WHAT_BROKE.md`, 2026-10-06), so it is noise, not the gap. Base route
  28154 lost both arms because the crossing could not be placed. Both failed array tasks (0 and 6) are from that base.
- **P11:** the black box was at least 99% black in every saved frame of all 20 routes. Most failures do not involve the walker: 4 of
  6 slice failures and 3 of 4 neighbourhood failures. So the patch, on either side, appears to cause most of them. This is what the
  protocol said to look for. No unpatched arm exists here, so that cause is inferred.
- **P12:** 2 of 10 routes struck walkers, close to P5's 2 of 8 and far from Fail2Drive's 87%. Speed does not close that gap in this
  screen. Our setup may differ from theirs in other ways (not checked). Neighbourhood route 2433382 has a walker at 8.3 m with none
  injected, so "no walkers" means none planted.

**Exploratory, not a verdict.** Pooled across P10 and P11, which have a walker in both arms, slice routes struck 4 walkers in 19 and
neighbourhood routes 1 in 19. If the same failure rates held at 60 pairs, Fisher's test would give p 0.011 for P10, 0.028 for P12 and
0.044 for P11 against PRD 9.1's 0.01, and P11's ratio of 1.5 is under the required 2.0. Rates from 10 pairs are rough. A full pilot on
these gaps as written looks unlikely to pass.

**Mechanics.** The patch was in the tree the runs used: `Bench2Drive/scenario_runner` was changed at 10:27, before the arrays were
submitted. The walker's real speed was not measured from logs. Spend: 2580 of 6000 SU, so H5 cost 343 SU for 58 scored routes. No jobs
are left on Savio.

Stopping here as the protocol says: a full pilot is Jerry's call.

## 2026-11-02 01:41 — H6 protocol: screen P10 with a later walker

Jerry chose to screen a harder P10 after H5. Measured first, on H5's crash-free routes: SimLingo stops from 10 to 12 m/s in 7 to 8 m, which
is 8 to 10 m/s² on average. That rules out the 1.0 s I proposed: its two measured stops would end at or past the walker's line, so a strike
would measure physics. The new gap P13 starts the walker at 1.2 s, and the rest matches P10. The hazard check now reads the car's speed at the trigger point, before the
walker is placed. Protocol: `docs/research/experiments/h6-later-crossing/protocol.md`. Prediction: no pass, about 70% (a guess).

## 2026-11-02 01:50 — H7 protocol: traffic pressure, after reading which families fail

Jerry asked to keep going until the results are NeurIPS-ready. All planted interactional gaps so far used a walker or an animal, and SimLingo rarely fails those:
2 of 65 unplanted crossing routes. Over 601 unplanted routes, the families that fail most involve moving vehicles. On signalized right turns, base routes with
13 to 14 m/s traffic failed 8 of 8 and those with 10 to 12 m/s failed 0 of 5 (exploratory, 5 bases). H7 varies traffic on fixed roads through three new gaps: P14, P15, P16.
`pilot_routes.py` can now override the base scenario's parameters. Main was merged (823932c) for Chris's speed-up.
Protocol: `docs/research/experiments/h7-traffic-pressure/protocol.md`. Prediction: at least one passes, about 70% (a guess).

## 2026-11-02 02:14 — H6 result: a later walker changes nothing; H7 submitted

P13 (walker at 3.5 m/s, 1.2 s) fails its screen, as predicted (measured, screen, dev data; 20 of 20 routes scored). The new check holds: 9 of 10 slice routes reached the trigger
above 4 m/s. Slice-only failures 1, neighbourhood-only 1, excess 0 of the 3 required; 3 of 10 fail in each arm. A walker was struck once in each arm (356173 with the condition, 324883 at stock timing).
Both other failures in each arm are shared by the pair (bases 1825 and 2509) and involve no walker.

Four slice routes that stopped did so 4.3 to 7.8 m from the crossing point, measured from the car's centre, which is more room than the arithmetic in the protocol predicted. These walker-start times are estimates from
the car's position, and no log records them. Taking 0.4 s from stock timing to 1.2 s does not visibly raise strikes, and 1.0 s would test physics, so I stop varying walker timing. Data: `docs/research/data/h6_check.json`.

Cost: 52.6 SU, 2.6 SU per route, under half the estimate. Goal spend is 2632 of 6000 SU. H7 arrays submitted on abe1831 with main's speed-up, three routes per A40: P14 40750508, P15 40750511, P16 40750513; scoring jobs 40750509, 40750512, 40750515.

## 2026-11-02 03:34 — H7 result: P14 passes its screen, the first interactional gap to do so

Measured, screens only, dev data. Every gap's check held. 56 of 60 routes scored in pairs; four routes were lost to one CARLA start crash, two 600-second simulator timeouts and one other crash (not yet diagnosed), and are not rerun, as locked.

| Gap | Pairs | Check | Slice-only | Neighbourhood-only | Excess (3 needed) | Fails, slice and neighbourhood |
|---|---:|---:|---:|---:|---:|---|
| P14 fast flow to join | 9 | 10 of 10 | 5 | 1 | **4** | 8 of 10, 3 of 9 |
| P15 fast flow on a left turn | 9 | 9 of 9 | 2 | 2 | 0 | 5 of 9, 6 of 10 |
| P16 dense oncoming overtake | 8 | 8 of 8 | 2 | 1 | 1 | 4 of 8, 4 of 10 |

Predictions: P14's held; P15's and P16's did not. **A screen pass means worth a further look and is not a verdict:** PRD 9.1's thresholds need far more pairs. McNemar p on these 9 pairs is 0.22, against the 0.01 required.

All of P14's failures are vehicle collisions. Base routes 4937 and 26956 failed at 15 m/s and passed at 7 m/s here, and also passed unplanted at 10 to 12 m/s, which supports a causal reading on the same road. Against that, 26966 and 2050 fail at 7 m/s too, so speed is not the whole story.

**The main threat is fairness.** The car enters at 8 to 10 m/s and does not wait. In 2750674, 2695674 and 367674 its speed jumps at the collision, so a flow vehicle probably hit it from behind. The spacing is unchanged across arms, so 15 m/s leaves about 1.7 s between vehicles on 2050, against 3.5 s at 7 m/s. If a careful driver cannot join either, these failures are not model weakness. The locked protocol requires an expert driver check before any full pilot.

P15's neighbourhood fails 6 of 10, so it had little room to show an effect. P16's failures mix collisions and timeouts. Data: `docs/research/data/h7_check.json`. Spend 2873 of 6000 SU; H7 cost 241 SU, about 4 SU per route, with long stalls on P15 and P16.

## 2026-11-02 06:41 — H8 result: the expert can drive P14's fast traffic, so P14 counts as solvable

Measured on 19 of 20 routes (1171574 lost to a CARLA timeout, not rerun). By the locked rule P14 is solvable. PDM-Lite had no vehicle collision on 8 of 9 scored slice routes (70% needed) and on 4 of the 5 roads where SimLingo failed only with fast traffic (4 needed). The prediction was 50%.

| On P14's roads | SimLingo slice | Expert slice | SimLingo neighbourhood | Expert neighbourhood |
|---|---:|---:|---:|---:|
| Vehicle collision | 8 of 10 | 1 of 9 | 3 of 9 | 0 of 10 |
| Fails the project's success label | 8 of 10 | 4 of 9 | 3 of 9 | 1 of 10 |

**The rule's limit:** it counts waiting as clean, and two expert slice routes (26966, 3676) wait until a scenario timeout, which the project's label calls a failure. So fast traffic is harder for the expert too. The expert also sees true positions, so this is an upper bound on what a careful driver could do. On the 5 roads, the expert finished 26956, 27506 and 4937 with no such failure, waited out 3676 and collided on 2201.

The expert's run also rules out my worry in its simplest form: a stream vehicle does not always hit a car that joins. Data: `docs/research/data/h8_expert_p14.json`. Spend 2954 of 6000 SU; H8 cost about 81 SU, including the failed tests.

## 2026-11-02 11:09 — H9: P14 fails its full pilot. H10: P19 passes its screen

**H9, P14 full pilot (measured, dev data).** The check holds, 53 of 58. PRD 9.1, the verdict of record, **fails**: 30 of 58 against 21 of 58, uplift 15.5 points (20 needed), ratio 1.43 (2 needed), Fisher p 0.13 (0.01 needed). C23 on 56 pairs: 17 slice-only against 8 neighbourhood-only, McNemar p 0.11. Four routes lost and not rerun. My prediction (pass, about 55%) was wrong. All 17 slice-only failures are vehicle collisions, so an effect may exist, but it is far smaller than the screen's 78% against 33%. The screen was the best of three on 9 pairs, and the winner's curse I named in the protocol appears to have applied. This pilot also ran almost only right turns on longer roads. I will not slice these numbers by family to rescue it.

**H10, screens (measured, dev data).** Every check holds.

| Gap | Pairs | Check | Slice-only | Neighbourhood-only | Excess (3 needed) | Fails, slice and neighbourhood |
|---|---:|---:|---:|---:|---:|---|
| P17 late static cut-in | 9 | 8 of 9 | 2 | 2 | 0 | 5 of 9, 5 of 10 |
| P18 close emergency vehicle | 9 | 7 of 10 | 1 | 0 | 1 | 8 of 10, 6 of 9 |
| P19 wide invading turn | 10 | 10 of 10 | 4 | 0 | **4** | 7 of 10, 3 of 10 |

Predictions: P19's pass was given about 35%, P17's about 40% and P18's about 70%. P18's failures do not depend on the distance: starting 140 m behind still fails 6 of 9, so the family fails whatever this knob does, and this neighbourhood cannot show it. **P19 is a screen pass, on the same small evidence that misled me on P14.** All 7 of its slice failures include a vehicle collision, and 2 of its 3 neighbourhood failures do. It uses a value outside the routes' range (1.2 m against 0.15 to 0.6 m), so it may be impossible to avoid.

Data: `docs/research/data/h9_h10_check.json`. Spend 3978 of 6000 SU; H9 and H10 cost about 1024 SU. Candidates tried: 19. Interactional gaps passing PRD 9.1 on this branch: 0.

## 2026-11-02 12:22 — H11 step 1: the expert drives P19, so its full pilot runs

Measured on 18 of 20 routes (base 63032's two routes hit the 1 h job limit and are not rerun). PDM-Lite had no vehicle collision on 9 of 9 slice routes (70% needed) and on all 4 of SimLingo's slice-only roads (3 needed), with no scenario timeouts. By the locked rule, P19 is solvable. The prediction was about 55%. Nothing was skipped in the expert's logs, and its `invading_turn.py` matches Bench2Drive's.

**This expert has an unusually large advantage here.** PDM-Lite reads the scenario's exact offset and shifts its route for it (`privileged_route_planner.shift_route_for_invading_turn`), so its driving proves there is room on the road. It does not prove a camera-only driver could see the need in time. Bench2Drive's expert is the one that wrote SimLingo's training data, which is why it is the stated test.

P19's pilot was submitted at this point. Data: `docs/research/data/h11_expert_p19.json`. Spend 4079 of 6000 SU.

## 2026-11-02 19:40 — H11 step 2: P19 passes PRD 9.1, the first interactional gap on this branch to do so

Measured on dev data, on 46 complete pairs and 101 of 110 routes. The check came first and holds, 48 of 53 scored slice routes. The screen's roads were excluded, so this pilot does not reuse the data that selected P19.

| Rule | Measured | Needed |
|---|---:|---:|
| Fails, slice (1.2 m) | 42 of 53, 79% | |
| Fails, neighbourhood (0.2 m) | 7 of 48, 15% | |
| Uplift | 64.7 points | 20 |
| Ratio | 5.43 | 2 |
| Fisher p | 4e-11 | 0.01 |
| Slice rollouts | 53 | 30 |

**PRD 9.1, the verdict of record, passes.** C23 on 46 pairs gives 32 slice-only against 0 neighbourhood-only, McNemar p 5e-10. `efficacy.json` marks C23 as not passing only because 46 pairs is under its floor of 60; P7 (56) and P8 (58) sit under the same floor. The locked read: all 32 slice-only failures include a vehicle collision, 14 of them also a scenario timeout, and the other 18 have no timeout. The prediction was a pass at about 40%, and the effect is larger than the screen's 70% against 30%, unlike P14.

**Checks I ran on this result because it is so large (exploratory).**

- Lost routes: 9 routes have no outcome, 7 neighbourhood and 2 slice. Counting every lost neighbourhood route as a failure and every lost slice route as a success gives 42 of 55 against 14 of 55, uplift 50.9, ratio 3.0, Fisher p 1e-7, which still passes.
- Candidates tried: 19. Multiplying p by 19 gives 8e-10. The pilot used new roads, so the screen that selected P19 does not inflate this number.
- Nothing was skipped by the scenario runner in either arm, and both arms ran the same two towns.

**What this does not show.**

- It is one gap on dev data. PRD 13.1 needs two interactional gaps on the test pool, and practice gaps do not count there (PRD 9.2).
- 1.2 m lies outside the 0.15 to 0.6 m used in the route sets, so this may be mainly an out-of-range failure. Whether failure rises gradually with offset has not been measured.
- The expert that drove these roads reads the exact offset (H11 step 1). No camera-only driver has been shown to avoid this traffic.
- Why the car hits the traffic, for example whether it holds its line or moves over too late, has not been read from the frames.

Data: `results/savio/step5-pilot-p19-main/`, `docs/research/data/h11_p19_main.json`. Spend 4943 of 6000 SU; the pilot cost about 864 SU. Interactional gaps passing PRD 9.1 on this branch: 1.


## 2026-11-03 — H12: the methods find P19 in some dictionaries, B2 beats them, and P19 breaks a Step 5 condition

Measured, dev data. Job 40793572 ran the locked pipeline on 2026-11-02 (about 16 SU); its output was read on 2026-11-03. Pool: 536 rollouts, 229 failures. All 18 SAEs count (held-out explained variance 0.96 to 0.97).

| Gap | Key | Catch-all | Best activation (M1) | Median of 18 | Reach 0.5 | Best baseline | Length audit | Claim A | Claim B |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| P19 | 42 | 0.183 | 0.705 | 0.375 | 5 of 18 | 0.857 B2 | 0.327 | holds | fails, margin -0.153 [-0.296, -0.019], 0 of 6 seeds |
| P4 | 46 | 0.201 | 0.490 | 0.387 | 0 of 18 | 0.257 B2 | 0.203 | fails | holds, margin +0.233 [+0.157, +0.385], 6 of 6 seeds |
| P7 | 54 | 0.236 | 0.275 | 0.231 | 0 of 18 | 0.500 B3 | 0.324 | fails | fails |

- **P19: Claims A and A' hold, Claim B fails, as predicted.** The best axis has 33 rollouts: 31 of P19's 42 key failures and 2 from a neighbourhood. It holds 14% of failures and no background or other-gap rollouts. A random 33 of the 229 failures would hold 31 or more of the key with probability about 1e-26, and a stopwatch reaches only 0.327. So no factor list was needed to find this group.
- **That is the best of 18 dictionaries.** The median is 0.375, and only k = 32 and k = 48 reach 0.5 (5 runs). Seeds disagree widely: at k = 32 the range is 0.218 to 0.705.
- **B2 wins with 0.857:** the `InvadingTurn` stratum, 42 slice and 7 neighbourhood failures. M1's axis has higher precision (94% against 86%) and lower recall (74% against 100%). The axis's 2 neighbourhood rollouts could be from any pilot, because the output does not record which, so at most 2 of P19's 7 neighbourhood failures are in it. On that small sample, M1 may separate 1.2 m from 0.2 m where B2 cannot; this is exploratory and not shown.
- **P4 misses Claim A by 0.010 on this pool** (0.490, against 0.557 in H3 with different dictionaries and pool). Claim B holds. This shows how much the headline depends on the dictionaries.
- **P7:** the stale latent gives 0.889 again (48 rollouts, all in the key), and it is independent of the SAE, as in H3. Plain M1 misses it. M2 returns no axes again.
- **Predictions:** four of five held. Wrong: P4's M1 reaching 0.5 (about 60%).

**A problem I did not see when P19 was chosen.** PRD §13 Step 5 requires that no single-factor stratum has expected Jaccard at least 0.4 with any interactional gap. B2's 0.857 breaks that on this pool. The cause is structural: P19's whole pilot is one scenario family with a low neighbourhood failure rate, so the family nearly is the gap. Only 5 of the pool's other rollouts are `InvadingTurn`, and none failed. To bring B2 below 0.4 the stratum would need more than 56 extra failures, which at the measured 15% is about 370 more `InvadingTurn` routes at ordinary offsets; Bench2Drive-220 holds 5 per family. **So on any realistic pool P19 behaves as an enumerable gap, and it does not count toward PRD 13.1's two interactional gaps as they are defined.** It still counts as a gap that fails. Any gap built by changing one parameter inside one family and having low neighbourhood failures has the same problem. This needs Chris and Jerry; no entry in CONFLICTS.md yet.

Data: `docs/research/data/h12_layer10_plain.json`, `h12_layer10_stale.json`; on Savio `results/savio/h12/`. Spend 4959 of 6000 SU (`sacct`, the measure above).

## 2026-11-03 — H13 pre-check: B2 can be beaten by spreading a gap; the patch alone is the risk

Jerry asked for a B2 pre-check before the last full pilot goes anywhere. No rollouts and no SU: `docs/research/experiments/h13-cross-family-gap/b2_precheck.py` runs B2's own strata on H12's pool without P19, plus simulated pairs on real roads cut from the leaderboard routes.

**Single-family gaps cannot pass (arithmetic).** PRD 9.1 needs a ratio of 2, so neighbourhood failures N are at most K/2 for K key failures. B2's family stratum scores K / (K + N + B), with B the family's failures outside the pilot, so getting under 0.4 needs B above K. With K near 40 and 5 routes per family, that is out of reach. This corrects the second half of what H12 suggested: a family that fails often does not rescue a gap, and `YieldToEmergencyVehicle` at 94% could not pass the ratio anyway.

| Candidate, 40 pairs | Roads | Expected B2 | Top stratum |
|---|---:|---:|---|
| Eight oncoming-traffic families | 430 | 0.19 to 0.26 | `ability = Overtaking` |
| Five low-baseline families, four in Overtaking | 280 | 0.24 to 0.33 | `ability = Overtaking` |
| Four families across three abilities | 222 | 0.25 to 0.28 | `scenario = InvadingTurn` |

Ranges cover slice rates 0.5 to 0.8 and added neighbourhood rates 0 to 0.24. Validation: on P19's real rates the simulation gives 0.801 against the measured 0.857, so it reads low by about 0.06. All candidates stay under 0.4 with that error added. These are simulated, and failures concentrated in one family would raise them, so the real B2 must be measured after any pilot.

**B2 is not the hard part now.** P20's mirror patch fails on its own: P11's left-patch arm failed 4 of 10 roads where those families' unplanted rates predict about 1.6 (measured, small). If that holds, chance of passing PRD 9.1 is 38% even at a true slice rate of 0.80 for the five low-baseline families, and 5% for the eight families. A clean neighbourhood would pass easily but would only show that a patch hurts, which is P4 again. So the five-family set goes in the draft, at about 12% overall (a guess).

Draft, not locked: `docs/research/experiments/h13-cross-family-gap/protocol.md`. Data: `docs/research/data/h13_b2_precheck.json`. Spend unchanged at 4959 of 6000 SU.

## 2026-11-03: H13 locked; first P20 screen lost to CARLA startup

No outcome exists. Array 40829006 timed out starting CARLA (300 s against about 18 s on 2026-11-02). Probe 40829691 gates a rerun of the same screen as 40829692. Spend 5029 of 6000 SU. See `docs/WHAT_BROKE.md`.

Probe 40829691 failed at 14:17 (not ready after 150 s), so the screen did not run. Scoring 40829693 ran under `afterany` and produced an empty report with 0 pairs, which is not an outcome. Probe 40831451 repeats from 16:38, 5 attempts at most, and submits the screen on success. Spend 5033 of 6000 SU.

Screen array 40843139 started at 19:48 from the repeating probe (port open in 120 s). Same-node disk test 40841695 on n0275: port open in 127 s from scratch, 4 s from node-local disk, `import torch` 158 s from scratch, 20 ms per metadata lookup (measured). Six routes stopped by the slow guard at 0.05 to 3.55 simulated seconds and listed for rerun. A review before reading found 3 of 10 pairs end before their hazard and route markers in the policy camera since 2026-10-05 (`docs/WHAT_BROKE.md`). No outcome read.

## 2026-11-04 01:30 — H14 drafted: what the route markers do to driving

Draft, not locked: `docs/research/experiments/h14-route-markers/protocol.md`. No rollouts and no SU; the sample-size table is simulated (`power.py`, `docs/research/data/h14_power.json`). Repeat-run discordance on `--debug 2` is 6 of 40 with the same seed and weather, and 40 of 199 and 17 of 70 with other seeds and weather (measured). Spend unchanged by this entry. Waits on Jerry and Chris; C35 is the draft for any change to `--debug`.

## 2026-11-04 21:00 — P20 fails its screen

Check first, from `docs/research/data/h13_p20_amended_check.json`: the box is black on the first 5 slices and 10 of 10 scored slices met traffic, with no scenario dropped. Then the rule: **0 slice-only against 4 neighbourhood-only failures on 10 pairs, exit 3** (measured). Slice failed 3 of 10, neighbourhood 7 of 10, McNemar p 0.125, Fisher p 0.18. Candidate count becomes 20. Per C34 this is not read as SimLingo coping without sight of oncoming traffic, because the patch covers an oncoming car only in the last 16 to 32 m of a straight road. The reversal is not read as an effect either: the protocol noted before the read that the mirror patch can cover the hazard.

Reported with the rule, as H13's amendment requires. Infractions, slice: 4 vehicle collisions, 2 layout, 1 outside lanes, 1 scenario timeout. Neighbourhood: 5 vehicle collisions, 4 stop, 1 outside lanes. Slice-only failures: 0, so 0 with a collision and 0 timeouts only. Discordant pairs by slice and neighbourhood task and node: 64145 task 4 n0217, task 3 n0211; 64181 task 5 n0279, task 3 n0211; 64237 task 6 n0211, rerun task 0 n0275; 64257 task 0 n0212, task 1 n0264. Borderline 64145 is one of the four: its neighbourhood failed on a stop infraction alone. 25854, flagged at the screen's review, passed in both arms.

Deleted the superseded shards 6415539 and 6415549 from the amended folder, unread. Spend 5344 of 10000 SU (measured). P20's full pilot does not run. H15 and H17 locked in `fb7b815` and submitted as 40906511 and 40906512.

## 2026-11-04 21:20 — H14 offline stops at its mask check

`sheets` ran on the login node. Two model viewers per panel, not a person, with panels 03 and 30 spot-checked by the lead: 85 of 118 coloured dots caught (72%, limit 90%), 13 of 50 frames with a ring on a vehicle by both viewers, 14 by one (limit 0). So `replay` was not submitted, as the protocol says, and the offline test is untested at 0 SU. `docs/research/data/h14_mask_check.json`. No re-tune: the frames are now seen, and whether H14 goes on at all is Chris's decision (issue 8).

## 2026-11-04 22:50 — H15 finds no bug; H17 reads above random, failing frames not shown larger

H15 (job 40906511, 12 SU): DEV DRY RUN, NOT A VERDICT. 0 bugs, all 11 checks clean, first run. Exploratory, with the best axis chosen using the key: action residualization (action-query states minus what vision predicts) puts M1 at or above 0.5 on P19 in 13 of 18 dictionaries, best 0.689, median 0.540, against 5 of 18, best 0.705, median 0.375 plain; B7-pool residualized reads best 0.620, median 0.278. My guess of "at least one dictionary, about 30%" was too low. P4 falls to best 0.316, median 0.201. B2 stays at 0.857 on P19. `docs/research/data/h15_dry_run.json`.

H17 (job 40906512, 49 SU): `above_random_failing_not_shown_larger`, with the fixed sentence in the dev report. Speed clears (0.121 m, excess interval 0.001 to 0.029 m); route does not. Failing minus control is about 0, and the axis does not beat other latents. `docs/research/data/h17_result.json`. Spend 5405 of 10000 SU (measured).

H15 found nothing to fix. The key format change it rests on still needs to reach Chris.

## 2026-11-06 02:30 — H18: the gain needs the visual fit, but mean removal alone gets 44% of it

Job 40967052, 16 SU. Rule outcome `needs_vision`: shuffle median 0.447 and variance-matched 0.436, against halfway 0.4575 (plain 0.375, real residual 0.540; M1 raw on P19 over 18 dictionaries; best axis chosen using the key; DEV DRY RUN). Shuffle explains 0.008, so it removes about the mean, and it misses halfway by 0.011. Beside the rule: under shuffle, B7-pool on P19 reads best 0.812, median 0.666, 17 of 18 at or above 0.5; under the variance-matched control (15 components, 0.814 against the real 0.808), M1 on P4 reads median 0.500. Preprocessing moves these scores a lot. `docs/research/data/h18_result.json`.

H19 first run (job 40967092, 3 SU): default 0 axes again, and no setting reaches 0.5 on a key gap. Its planted control was invalid (WHAT_BROKE 2026-11-06), so its reading is withdrawn. The amended plant runs as job 40967739.

## 2026-11-06 02:35 — H19: M2 cannot recover a planted group under any tried setting

Amended job 40967739, 3 SU. `planted_not_recovered`. 25 planted failures (known share 0.67 to 1.0) left the catch-all cluster (221 to 169) but formed no cluster; planted Jaccard 0.0 under all 16 settings. Real runs: default 0 axes; best gap Jaccard 0.397 on P19 (chosen using the key). M2's zero on real pools is uninformative about the gaps. Changing M2 is a method decision for Chris; no setting changed here. `docs/research/data/h19_result.json`.

## 2026-11-06 03:30 — H20: mean removal moves scores on H1's pool too

Jobs 40967835 (stopped at scoring, since `scoring_run` needs a T2 gap; nothing read) and 40968012, 25 SU together. `replicates`: B7-pool on P8 +0.149 (0.215 to 0.364); M1 raw on P4 −0.088 (0.353 to 0.265); 7 other cells within 0.064. Vision residual: M1 raw P4 0.155. Same direction as H18 on both B7 and M1-P4. Wrote C37 (pending Chris): name the mean step at `methods-frozen-v1`, freeze B7 with matched preprocessing, and fix or label M2. Spend 5453 of 10000 SU, measured by study job name. `docs/research/data/h20_result.json`.

