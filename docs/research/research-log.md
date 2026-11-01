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
