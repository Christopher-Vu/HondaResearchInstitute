# Dev report v0

Written 2026-11-04 and updated 2026-11-06 from stored files. Every number below is dev data. A number with no data file says so.

## Plain answer

1. Three planted camera faults make SimLingo fail far more often: P4, P7 and P8 pass PRD 9.1 with uplifts of [51.7](../../results/savio/step5-pilot-p4-main/efficacy.json), [69.6](../../results/savio/step5-pilot-p7-main/efficacy.json) and [80.0](../../results/savio/step5-pilot-p8-main/efficacy.json) points, and P4 and P7 pass again on fresh drives ([62.7](../../results/savio/step5-confirm-p4/efficacy.json) and [61.4](../../results/savio/step5-confirm-p7/efficacy.json)).
2. One interactional gap, P19, passes PRD 9.1 with [42 of 53 failures against 7 of 48](../../results/savio/step5-pilot-p19-main/efficacy.json), but it fails Step 5's single-factor condition because a list of scenario names scores Jaccard [0.857](data/h12_layer10_plain.json) against a limit of 0.4, so no public interactional gap met Step 5 on dev.
3. Contrastive diffing (M1) reaches 0.5 on P19 in 5 of 18 dictionaries on the [H12 pool](data/h12_layer10_plain.json) (best 0.705, median 0.375). On P4 it reaches 0.5 in 3 of 18 in [H3](data/h3_layer10_plain.json) (best 0.557, median 0.405) and in none on the H12 pool (best 0.490, median 0.387). The best axis is chosen using the key. These are plain-variant scores, and they move with preprocessing the PRD does not fix. On the H12 pool, H18's variance-matched control puts M1 raw on P4 at best 0.672, median 0.500 (10 of 18), and vision residualization lifts its P19 median to 0.540 (13 of 18). See [H18, H20 and C37](#dry-run-and-rehearsal). All of this is exploratory and dev only.
4. A frozen-input signal read from activations, added post hoc to B7-pool, finds P7 at [0.889](data/h12_layer10_stale.json) in every dictionary (best and median 0.889), and that signal is a detector for one fault. No method has recovered P8. Plain B7-pool gives best [0.444](data/h1b_layer10.json), median 0.235 (H1b, exploratory, beside H1's confirmatory verdict below). With vision residualized it gives best 0.483, median 0.395, and removing only the mean moves its median by +0.149 ([H20](data/h20_result.json)). Both axes are chosen using the key.
5. These results cover [20 public candidates](research-log.md), all on dev data, and Chris reports 9 sealed candidates and 3 decoys on top of them. Every SimLingo drive in this report had route markers in its camera with an effect [nobody has measured](../WHAT_BROKE.md).

No answer key is committed in this repo and no test pool exists, so the PRD 13.1 test was not run.

| End state ([C34](../../CONFLICTS.md)) | Where it stands |
|---|---|
| A, the dev-only report | P20 is read, and the route-marker effect is stated here as unmeasured, which A allows. The study does not close here, because Chris asked that it not close at A on his counts ([issue 8](https://github.com/Christopher-Vu/HondaResearchInstitute/issues/8)) and more sealed candidates are coming. |
| B, A plus a blind pool | Not reached. No key is committed in this repo, no test pool exists, and of the frozen tags only `b4-factors-v1` exists. The [preregistration](../../harness/PREREGISTRATION.md) is an unsigned draft. |

This report claims no 13.1 branch, including the negative one. 13.1 is decided on the test pool, and [PRD 9.1](../../PRD.md) excludes any predicate in a shared document from the sealed key, so the public count toward 13.1's two interactional gaps is 0 by construction.

## Terms

| Term | Meaning |
|---|---|
| Gap | A region of driving conditions planted on purpose in the hope that the policy fails inside it. |
| Slice, neighbourhood | The slice is the routes inside the gap. The neighbourhood is the same roads just outside it. |
| Pair | One base road with a scored outcome in both arms. |
| PRD 9.1 | A gap passes with uplift of at least 20 points, a ratio of at least 2, Fisher exact p under 0.01 and at least 30 slice rollouts. |
| Uplift, ratio | Uplift is the slice failure rate minus the neighbourhood failure rate, in percentage points. Ratio is one rate divided by the other. |
| Screen | A first stage of about 10 pairs. It passes when slice-only failures exceed neighbourhood-only failures by at least 3 (the excess). A screen pass is not a 9.1 verdict. |
| Tier | T0 is a control gap that any method should find. T1 is a single factor any list would name. T2 is interactional: a conjunction or sub-range no standard list names. |
| Key | The rollouts that count as a gap's failures. On these public gaps it is the failing slice rollouts. |
| Axis | A group of failing rollouts that a method returns. |
| Jaccard | Shared rollouts divided by all rollouts in either group, for an axis against a key. 1 means identical and 0 means no overlap. |
| Catch-all | An axis holding every failure. Its Jaccard is the key's share of failures, which sets the bar. |
| Dictionary | One trained sparse autoencoder, a small model that rewrites activations as a few active features. Each pool has 18 (k of 32, 48 and 64, seeds 0 to 5). |
| M1 | Contrastive diffing, which compares features in the 3 s before failures with successes. The capped version drops features firing in over half of the failures. |
| M2 | Probe-residual, which clusters what probes fail to predict from activations. With its default settings it returned no axes on every real pool. In H19, no setting of 16 grouped a planted 25-failure group, so that zero says little about whether the gaps are there. |
| B2, B3 | B2 groups failures by human factor names such as the scenario name. B3 groups them by the car's behaviour. |
| B7, B7-pool | An activation-statistics baseline that counts feature onsets over a whole rollout. B7 proper (variant A) reads SimLingo's training data and has not run. B7-pool (variant B) reads the rollout pool, and every B7 number here is B7-pool. |
| Frozen-input signal | One extra feature added to B7-pool (`--stale-latent`). It fires when activations do not change between logged frames, and it does not depend on the dictionary. It is a post hoc change to the frozen B7 definition, because H2 added it after the activations were opened. |
| Check | A manipulation check, fixed before a run, that the planted condition happened (C24). |
| C23 | A [CONFLICTS](../../CONFLICTS.md) entry, pending review, that proposes a paired test (McNemar's) with a floor of 60 pairs. |
| H1 to H20 | Numbered experiments in the [research log](research-log.md). Each has a protocol under `experiments/`. |
| Claims A, A′, B | A: an activation method has an axis with Jaccard at least 0.5 holding at most 50% of failures. A′: the same, with B7-pool allowed. B: the best activation method beats the best baseline and the catch-all by at least 0.15, the margin's interval is above 0, and at least 4 of 6 seeds agree. |

## Public gaps

Measured means a full pilot or the Step 4 pilot. Screen means a first stage on about 10 pairs, which is also measured but is weak evidence. A value marked (d) is not in a data file: this report derived it from the stored counts with the formula in [`src/harness/efficacy.py`](../../src/harness/efficacy.py). Read every p value here beside the candidate count: 20 public candidates were tried, and Chris reports 9 sealed candidates and 3 decoys on top of them.

| Gap | Tier | Run | Evidence | Verdict | Slice failed | Neighbourhood failed | Uplift (points) | Ratio | Fisher p (20 public candidates tried) | Pairs | Data |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| P1 dust storm at night | T0 | Step 4 pilot | measured, 30 and 29 scored | Fails 9.1. On Savio it tested a very dark night, because [the dust renders as darkness](../WHAT_BROKE.md) (entry of 2026-10-09). | 7 of 30 | 5 of 29 | 6.1 (d) | 1.35 (d) | 0.75 | not in file | [sweep.json](../../results/savio/step4-dev-pool/sweep.json) |
| P2 pedestrian behind a container, night | T2 | Step 4 pilot | measured, 30 per arm | Fails 9.1 | 2 of 30 | 0 of 30 | 6.7 (d) | undefined, 0 neighbourhood failures | 0.49 | not in file | [sweep.json](../../results/savio/step4-dev-pool/sweep.json) |
| P3 dense fog at noon | T0 | Full pilot | measured, full pilot | Fails 9.1. Its check [was overridden](../WHAT_BROKE.md) (entry of 2026-10-13). | 15 of 59 | 18 of 60 | -4.6 | 0.85 | 0.68 | 59 | [efficacy.json](../../results/savio/step5-pilot-p3/efficacy.json) |
| P4 camera occlusion | T0 | Screen | screen | Passes screen, excess 4 of 3 | 8 of 10 | 4 of 10 | 40.0 (d) | 2.00 (d) | 0.17 (d) | 10 | No data file. Counts from [STATUS](../STATUS.md), entry of 2026-10-14. |
| P4 camera occlusion | T0 | Full pilot | measured, full pilot | Passes 9.1 | 43 of 60 | 12 of 60 | 51.7 | 3.58 | 1.9e-8 | 60 | [efficacy.json](../../results/savio/step5-pilot-p4-main/efficacy.json) |
| P4 camera occlusion | T0 | Confirm pilot, fresh drives | measured, full pilot | Passes 9.1 | 46 of 59 | 9 of 59 | 62.7 | 5.11 | 5.7e-12 | 58 | [efficacy.json](../../results/savio/step5-confirm-p4/efficacy.json) |
| P5 pedestrians in the ego lane | T2 | Screen | screen | Fails screen, excess 1 of 3 | 2 of 8 | 1 of 9 | 13.9 (d) | 2.25 (d) | 0.58 (d) | not recorded | No data file. Counts from [WHAT_BROKE](../WHAT_BROKE.md), entry of 2026-10-14. |
| P6 animal crossing | T1 | Screen | screen | Fails screen. No base route failed only with the animal. | 1 of 9 | 2 of 10 | -8.9 (d) | 0.56 (d) | 1.00 (d) | not recorded | No data file. Counts from [WHAT_BROKE](../WHAT_BROKE.md), entry of 2026-10-15. |
| P7 camera freeze | T0 | Screen | screen | Passes screen, excess 6 of 3 | 10 of 10 | 4 of 10 | 60.0 | 2.50 | 0.011 | 10 | [efficacy.json](../../results/savio/step5-pilot-p7-screen/efficacy.json) |
| P7 camera freeze | T0 | Full pilot | measured, full pilot | Passes 9.1 | 53 of 56 | 15 of 60 | 69.6 | 3.79 | 1.6e-15 | 56 | [efficacy.json](../../results/savio/step5-pilot-p7-main/efficacy.json) |
| P7 camera freeze | T0 | Confirm pilot, fresh drives | measured, full pilot | Passes 9.1 | 54 of 58 | 19 of 60 | 61.4 | 2.94 | 1.1e-12 | 58 | [efficacy.json](../../results/savio/step5-confirm-p7/efficacy.json) |
| P8 camera latency | T0 | Screen | screen | Passes screen, excess 5 of 3 | 10 of 10 | 4 of 9 | 55.6 | 2.25 | 0.011 | 9 | [efficacy.json](../../results/savio/step5-pilot-p8-screen/efficacy.json) |
| P8 camera latency | T0 | Full pilot | measured, full pilot | Passes 9.1 | 58 of 58 | 12 of 60 | 80.0 | 5.00 | 4.6e-22 | 58 | [efficacy.json](../../results/savio/step5-pilot-p8-main/efficacy.json) |
| P9 traffic-light glare | T1 | Screen | screen | Fails screen, excess -1 of 3 | 3 of 9 | 4 of 10 | -6.7 | 0.83 | 1.00 | 9 | [efficacy.json](../../results/savio/step5-pilot-p9-screen/efficacy.json) |
| P10 late fast crossing | T2 | Screen | screen | Untested: [check](data/h5_manipulation.json) 3 of 5, 4 needed. Excess 2 of 3. | 4 of 9 | 2 of 9 | 22.2 | 2.00 | 0.62 | 9 | [efficacy.json](../../results/savio/step5-pilot-p10-screen/efficacy.json) |
| P11 blind-side crossing | T2 | Screen | screen | Fails screen, excess 2 of 3. [Check](data/h5_manipulation.json) holds. | 6 of 10 | 4 of 10 | 20.0 | 1.50 | 0.66 | 10 | [efficacy.json](../../results/savio/step5-pilot-p11-screen/efficacy.json) |
| P12 walkers at speed | T2 | Screen | screen | Untested: [check](data/h5_manipulation.json) 3 of 5, 4 needed. Excess 2 of 3. | 4 of 10 | 2 of 10 | 20.0 | 2.00 | 0.63 | 10 | [efficacy.json](../../results/savio/step5-pilot-p12-screen/efficacy.json) |
| P13 later fast crossing | T2 | Screen | screen | Fails screen, excess 0 of 3. [Check](data/h6_check.json) holds. | 3 of 10 | 3 of 10 | 0.0 | 1.00 | 1.00 | 10 | [efficacy.json](../../results/savio/step5-pilot-p13-screen/efficacy.json) |
| P14 fast flow to join | T2 | Screen | screen | Passes screen, excess 4 of 3. [Check](data/h7_check.json) holds. | 8 of 10 | 3 of 9 | 46.7 | 2.40 | 0.070 | 9 | [efficacy.json](../../results/savio/step5-pilot-p14-screen/efficacy.json) |
| P14 fast flow to join | T2 | Full pilot | measured, full pilot | Fails 9.1. [Check](data/h9_h10_check.json) holds. | 30 of 58 | 21 of 58 | 15.5 | 1.43 | 0.13 | 56 | [efficacy.json](../../results/savio/step5-pilot-p14-main/efficacy.json) |
| P15 fast flow on a left turn | T2 | Screen | screen | Fails screen, excess 0 of 3. [Check](data/h7_check.json) holds. | 5 of 9 | 6 of 10 | -4.4 | 0.93 | 1.00 | 9 | [efficacy.json](../../results/savio/step5-pilot-p15-screen/efficacy.json) |
| P16 dense oncoming overtake | T2 | Screen | screen | Fails screen, excess 1 of 3. [Check](data/h7_check.json) holds. | 4 of 8 | 4 of 10 | 10.0 | 1.25 | 1.00 | 8 | [efficacy.json](../../results/savio/step5-pilot-p16-screen/efficacy.json) |
| P17 late static cut-in | T2 | Screen | screen | Fails screen, excess 0 of 3. [Check](data/h9_h10_check.json) holds. | 5 of 9 | 5 of 10 | 5.6 | 1.11 | 1.00 | 9 | [efficacy.json](../../results/savio/step5-pilot-p17-screen/efficacy.json) |
| P18 close emergency vehicle | T1 | Screen | screen | Fails screen, excess 1 of 3. [Check](data/h9_h10_check.json) holds. | 8 of 10 | 6 of 9 | 13.3 | 1.20 | 0.63 | 9 | [efficacy.json](../../results/savio/step5-pilot-p18-screen/efficacy.json) |
| P19 wide invading turn | T2 | Screen | screen | Passes screen, excess 4 of 3. [Check](data/h9_h10_check.json) holds. | 7 of 10 | 3 of 10 | 40.0 | 2.33 | 0.18 | 10 | [efficacy.json](../../results/savio/step5-pilot-p19-screen/efficacy.json) |
| P19 wide invading turn | T2 | Full pilot | measured, full pilot | Passes 9.1, fails Step 5's single-factor condition. [Check](data/h11_p19_main.json) holds. | 42 of 53 | 7 of 48 | 64.7 | 5.43 | 4.0e-11 | 46 | [efficacy.json](../../results/savio/step5-pilot-p19-main/efficacy.json) |
| P20 oncoming traffic hidden | T2 | Amended screen | screen | P20 fails its screen: 0 against 4 on 10 pairs. [Check](data/h13_p20_amended_check.json) holds. | 3 of 10 | 7 of 10 | -40.0 | 0.43 | 0.18 | 10 | [efficacy](data/h13_p20_amended_efficacy.json) |

Tiers come from [`practice_v1.yaml`](../../gaps/practice/practice_v1.yaml), [`practice_v2.yaml`](../../gaps/practice/practice_v2.yaml) and [`practice_v3.yaml`](../../gaps/practice/practice_v3.yaml). The tier field inside `docs/research/data/*.json` reads T0 for every gap, including P19, so this report does not use it.

| Count | Gaps |
|---|---|
| Pass 9.1 on a full pilot, T0 | P4, P7, P8 |
| Pass 9.1 on a full pilot, T1 | None |
| Pass 9.1 on a full pilot, T2 | P19, which fails Step 5's single-factor condition |
| T2 gaps meeting Step 5 on dev | 0 |
| Marked as a decoy in `gaps/practice/` | None |
| Reached C23's floor of 60 pairs | P4's full pilot only, at [60 pairs](../../results/savio/step5-pilot-p4-main/efficacy.json). C23 is pending review, and PRD 9.1 stays the verdict of record. |

Infractions in P20's screen were 4 vehicle collisions, 2 layout, 1 outside lanes and 1 scenario timeout in the slice, and 5 vehicle collisions, 4 stop and 1 outside lanes in the neighbourhood. With no slice-only failure, 0 include a collision and 0 are timeouts only. P20's failure is not read as SimLingo coping without sight of oncoming traffic, because by arithmetic its patch covers an oncoming car only in the last 16 to 32 m of a straight road. The reversal, 7 of 10 in the neighbourhood against 3 of 10 in the slice, is not read as an effect either: the protocol noted before the read that the mirror patch can cover the hazard, and 10 pairs cannot separate that from chance (McNemar p 0.125).

Screens can mislead in both directions. P14 went from [8 of 10 against 3 of 9](../../results/savio/step5-pilot-p14-screen/efficacy.json) to [30 of 58 against 21 of 58](../../results/savio/step5-pilot-p14-main/efficacy.json), and P19 went from [7 of 10 against 3 of 10](../../results/savio/step5-pilot-p19-screen/efficacy.json) to [42 of 53 against 7 of 48](../../results/savio/step5-pilot-p19-main/efficacy.json).

## Methods

### H1's confirmatory test

H1 Tier 1 ran under its locked protocol on the 738-rollout pool, and its verdict is Claim A no and Claim B no for all three gaps at both layers (measured, [log](research-log.md) only, entries of 2026-10-31 22:59 and 23:24, no data file). The log reads this as "activation methods not tested". All 18 layer-10 token-trained dictionaries scored explained variance about -0.5 on frame means, so by the protocol M1 and B7 sat out, and M2 emitted no axes. **The best axis is chosen using the key** for M1 here too, and the log holds no median for it.

| Gap | Catch-all | B2 | B3 | M2 | M1, best of 18, which did not count |
|---|---:|---:|---:|---:|---:|
| P4 | 0.155 | 0.219 | 0.176 | 0, no axes | 0.551 |
| P7 | 0.191 | 0.270 | 0.176 | 0, no axes | 0.206 |
| P8 | 0.209 | 0.296 | 0.200 | 0, no axes | 0.242 |

Layer 14 gave identical baseline numbers, an empty M2 and the same misfit. Tier 2, the per-token run that the [H1b protocol](experiments/h1b-frame-mean-sae/protocol.md) names as the confirmatory test of M1, [never ran](research-log.md). The M1 results below are exploratory or dev-data results, and they sit beside this verdict and do not replace it.

The first dev evaluation of 2026-10-15 ([`results/savio/dev-eval/`](../../results/savio/dev-eval/)) came before all of this and was inconclusive, because 51 of its 73 failures were P4's, so an axis holding every failure tied almost every method ([WHAT_BROKE](../WHAT_BROKE.md)). Its contrastive numbers also predate the correction to contrastive diffing's firing rule ([journal](../JOURNAL.md), entry of 2026-10-20), and this report does not use them.

### How to read the best scores

**The best axis is chosen using the key.** Every best score below picks the highest-scoring axis with the answer in hand, so a user without a key would still have to inspect the top groups. A best score is an upper bound on what a user without a key would get, and the median shows what a typical dictionary gives.

### Activation methods without the frozen-input signal

| Run | Status | Gap | Key, of pool failures | Catch-all | M1 raw, best / median | M1 capped, best / median | Dictionaries reaching 0.5, raw / capped | B7-pool, best / median | Best baseline | Margin, best activation minus best baseline [interval] | Claim A | Claim B | Data |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| H1b, layer 10 | exploratory | P4 | 43 of 278 | 0.155 | 0.553 / 0.405 | 0.574 / 0.432 | 3 / 4 | 0.091 / 0.042 | B2 0.219 | +0.355 [+0.264, +0.520] | holds | holds | [h1b_layer10.json](data/h1b_layer10.json) |
| H1b, layer 10 | exploratory | P7 | 53 of 278 | 0.191 | 0.207 / 0.195 | 0.200 / 0.170 | 0 / 0 | 0.278 / 0.209 | B7-pool 0.278 | -0.071 [-0.146, -0.007] | fails | fails | [h1b_layer10.json](data/h1b_layer10.json) |
| H1b, layer 10 | exploratory | P8 | 58 of 278 | 0.209 | 0.276 / 0.208 | 0.276 / 0.197 | 0 / 0 | 0.444 / 0.235 | B7-pool 0.444 | -0.169 [-0.267, -0.049] | fails | fails | [h1b_layer10.json](data/h1b_layer10.json) |
| H1b, layer 14 | exploratory | P4 | 43 of 278 | 0.155 | 0.435 / 0.330 | 0.435 / 0.330 | 0 / 0 | 0.111 / 0.054 | B2 0.219 | +0.216 [+0.162, +0.320] | fails | holds | [h1b_layer14.json](data/h1b_layer14.json) |
| H1b, layer 14 | exploratory | P7 | 53 of 278 | 0.191 | 0.227 / 0.190 | 0.227 / 0.170 | 0 / 0 | 0.250 / 0.104 | B2 0.270 | -0.043 [-0.107, +0.017] | fails | fails | [h1b_layer14.json](data/h1b_layer14.json) |
| H1b, layer 14 | exploratory | P8 | 58 of 278 | 0.209 | 0.231 / 0.206 | 0.231 / 0.205 | 0 / 0 | 0.395 / 0.130 | B7-pool 0.395 | -0.165 [-0.232, -0.054] | fails | fails | [h1b_layer14.json](data/h1b_layer14.json) |
| H3, layer 10 | confirmatory, frozen pipeline, dev data | P4 | 46 of 180 | 0.256 | 0.557 / 0.405 | 0.557 / 0.400 | 3 / 3 | 0.116 / 0.056 | B2 0.354 | +0.204 [+0.108, +0.350] | holds | holds | [h3_layer10_plain.json](data/h3_layer10_plain.json) |
| H3, layer 10 | confirmatory, frozen pipeline, dev data | P7 | 54 of 180 | 0.300 | 0.330 / 0.306 | 0.340 / 0.230 | 0 / 0 | 0.541 / 0.093 | B7-pool 0.541 | -0.201 [-0.317, -0.073] | fails | fails | [h3_layer10_plain.json](data/h3_layer10_plain.json) |
| H12, layer 10 | locked protocol, dev data | P19 | 42 of 229 | 0.183 | 0.705 / 0.375 | 0.705 / 0.368 | 5 / 5 | 0.500 / 0.372 | B2 0.857 | -0.153 [-0.296, -0.019] | holds | fails | [h12_layer10_plain.json](data/h12_layer10_plain.json) |
| H12, layer 10 | locked protocol, dev data | P4 | 46 of 229 | 0.201 | 0.490 / 0.387 | 0.490 / 0.387 | 0 / 0 | 0.091 / 0.037 | B2 0.257 | +0.233 [+0.157, +0.385] | fails | holds | [h12_layer10_plain.json](data/h12_layer10_plain.json) |
| H12, layer 10 | locked protocol, dev data | P7 | 54 of 229 | 0.236 | 0.275 / 0.231 | 0.275 / 0.208 | 0 / 0 | 0.339 / 0.065 | B3 0.500 | -0.225 [-0.333, -0.081] | fails | fails | [h12_layer10_plain.json](data/h12_layer10_plain.json) |

| Reading (exploratory) | Evidence |
|---|---|
| H12 is why C34 demands medians: P19's best is 0.705 and its median is 0.375. | [`h12_layer10_plain.json`](data/h12_layer10_plain.json) |
| P4's best moves with the dictionaries and the pool, from 0.557 (median 0.405) in H3 to 0.490 (median 0.387) in H12, so Claim A misses by 0.010 in H12 while Claim B holds. Under H18's variance-matched control on the H12 pool it reads best 0.672, median 0.500. | [`h3_layer10_plain.json`](data/h3_layer10_plain.json), [`h12_layer10_plain.json`](data/h12_layer10_plain.json) |
| B2 beats M1 on P19, by a margin of -0.153. | [`h12_layer10_plain.json`](data/h12_layer10_plain.json) |
| Under plain preprocessing, B7-pool scores above M1 on P7 and P8 in every run above, and M1 scores above B7-pool on P4 and P19. Under H18's shuffle control, which removes about the mean, B7-pool scores above M1 on P19 (median 0.666 against 0.447), so the ordering depends on the mean step ([C37](../../CONFLICTS.md)). | The four files above |

### The frozen-input signal

This table is a different method from the table above. **The best axis is chosen using the key** here too, but the frozen-input axis is the same in all 18 dictionaries, so its best and median agree on P7. M1's scores do not change when the signal is on. H2 chose the signal on the old pool and it was then fixed for H3, so H3 is its only test on drives opened after the choice, and H12 reuses H3's P7 rollouts. H2 added it after the activations were opened, so [the B7 spec](../steps/b7-gap-signal.md) labels it a post hoc change to the frozen definition, and that label applies to every row of this table, including H3's. The column for other gaps' slices counts failing slice rollouts of a pilot other than the one scored, so each row adds up to its rollouts. On P8 that column is the mixing with P7.

| Run | Status | Gap | Key, of pool failures | Frozen-input signal in B7-pool, best | Median across dictionaries | Dictionaries reaching 0.5 | Best axis, rollouts | In key | Other gaps' slices | Neighbourhood | Other | Share of failures | Data |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H2, layer 10 | exploratory | P4 | 43 of 278 | 0.091 | 0.023 | 0 | 17 | 5 | 2 | 4 | 6 | 0.061 | [h2_layer10.json](data/h2_layer10.json) |
| H2, layer 10 | exploratory | P7 | 53 of 278 | 0.906 | 0.906 | 18 | 48 | 48 | 0 | 0 | 0 | 0.173 | [h2_layer10.json](data/h2_layer10.json) |
| H2, layer 10 | exploratory | P8 | 58 of 278 | 0.350 | 0.090 | 0 | 50 | 28 | 22 | 0 | 0 | 0.180 | [h2_layer10.json](data/h2_layer10.json) |
| H2, layer 14 | exploratory | P4 | 43 of 278 | 0.075 | 0.023 | 0 | 14 | 4 | 1 | 4 | 5 | 0.050 | [h2_layer14.json](data/h2_layer14.json) |
| H2, layer 14 | exploratory | P7 | 53 of 278 | 0.906 | 0.906 | 18 | 48 | 48 | 0 | 0 | 0 | 0.173 | [h2_layer14.json](data/h2_layer14.json) |
| H2, layer 14 | exploratory | P8 | 58 of 278 | 0.291 | 0.017 | 0 | 44 | 23 | 19 | 0 | 2 | 0.158 | [h2_layer14.json](data/h2_layer14.json) |
| H3, layer 10 | confirmatory, frozen pipeline, dev data | P4 | 46 of 180 | 0.065 | 0.021 | 0 | 20 | 4 | 5 | 3 | 8 | 0.111 | [h3_layer10_stale.json](data/h3_layer10_stale.json) |
| H3, layer 10 | confirmatory, frozen pipeline, dev data | P7 | 54 of 180 | 0.889 | 0.889 | 18 | 48 | 48 | 0 | 0 | 0 | 0.267 | [h3_layer10_stale.json](data/h3_layer10_stale.json) |
| H12, layer 10 | locked protocol, dev data | P19 | 42 of 229 | 0.417 | 0.162 | 0 | 26 | 20 | 0 | 5 | 1 | 0.114 | [h12_layer10_stale.json](data/h12_layer10_stale.json) |
| H12, layer 10 | locked protocol, dev data | P4 | 46 of 229 | 0.031 | 0.016 | 0 | 20 | 2 | 12 | 3 | 3 | 0.087 | [h12_layer10_stale.json](data/h12_layer10_stale.json) |
| H12, layer 10 | locked protocol, dev data | P7 | 54 of 229 | 0.889 | 0.889 | 18 | 48 | 48 | 0 | 0 | 0 | 0.210 | [h12_layer10_stale.json](data/h12_layer10_stale.json) |

| Reading | Evidence |
|---|---|
| Claim A′ holds for P7 through this signal in H3. Claims A and B do not, because B7-pool counts as a baseline for those two. | [Research log](research-log.md), entry of 2026-11-01 09:29 |
| The axis misses the 6 P7 failures whose frames never repeat exactly, and H2's own rule that M1 reach 0.5 on P7 failed. | [Research log](research-log.md), entries of 2026-11-01 00:20 and 09:29 |
| P8 was left out of H3 and H12, so its only scores are exploratory. | [H3 protocol](experiments/h3-confirm-fresh-pilots/protocol.md), [H12 protocol](experiments/h12-methods-on-p19/protocol.md) |

### Numbers held only in the research log

| Audit | Value | Status of the number |
|---|---|---|
| Length audit, the N longest failures against the key, H3 | P7 0.48, P4 0.26 | [Log](research-log.md) only. No script or output is stored. |
| Length audit, H12 | P19 0.327, P4 0.203, P7 0.324 | [Log](research-log.md) only. No script or output is stored. |
| Chance of the best axis under random draws, H3 P4 and H12 P19 | About 3e-15 and 1e-26 | [Log](research-log.md). This report recomputed them from the axis counts with a hypergeometric test and got 2.8e-15 and 9.8e-27. |
| Lag probe on P8, H4 | Jaccard 0.342, where its rule needed 0.5 | [Log](research-log.md). The [per-rollout table](data/h4_lag_probe_table.csv) has no key columns, so it does not hold the score. |

The length audit matters because plain B7-pool's best of 0.541 on P7 in H3 (median 0.093, and the best axis is chosen using the key) sits close to a stopwatch's 0.48, so that score does not count as a recovery.

## Candidate count

**20 public candidates have been tried, P1 to P20** ([research log](research-log.md)). Chris reports 9 sealed candidates and 3 decoys on top of these, at about 6,000 SU ([issue 8](https://github.com/Christopher-Vu/HondaResearchInstitute/issues/8)), and one of them overlaps P20's region and is counted there as tried and not passed. The public count alone is therefore a lower bound on what PRD 9.1 means by candidates tried.

P20 entered the count when it failed its screen, as C34 fixed before the read. The 20 includes P10 and P12 although they read as untested after failed checks, because the log counted them and a higher count is the cautious direction.

**Selection warning from C34: every gap's p value is read with the candidate count beside it.** The table shows the p values of the runs that pass 9.1 next to that count. Multiplying by the count is the crude correction the log used for P19. It is an illustration and not a PRD rule, and 20 counts gaps, while the stored and logged efficacy runs number 27 (22 `efficacy.json` files, 2 entries in `sweep.json` and 3 screens with no file).

| Gap and run | Fisher p | Fisher p times 20 (public candidates only) | Data |
|---|---:|---:|---|
| P4 full pilot | 1.9e-8 | 3.8e-7 (d) | [efficacy.json](../../results/savio/step5-pilot-p4-main/efficacy.json) |
| P4 confirm pilot | 5.7e-12 | 1.1e-10 (d) | [efficacy.json](../../results/savio/step5-confirm-p4/efficacy.json) |
| P7 full pilot | 1.6e-15 | 3.2e-14 (d) | [efficacy.json](../../results/savio/step5-pilot-p7-main/efficacy.json) |
| P7 confirm pilot | 1.1e-12 | 2.2e-11 (d) | [efficacy.json](../../results/savio/step5-confirm-p7/efficacy.json) |
| P8 full pilot | 4.6e-22 | 9.2e-21 (d) | [efficacy.json](../../results/savio/step5-pilot-p8-main/efficacy.json) |
| P19 full pilot | 4.0e-11 | 8.0e-10 (d) | [efficacy.json](../../results/savio/step5-pilot-p19-main/efficacy.json) |

Two further limits apply. The 9 lost routes of P19's pilot still pass in the [worst case](research-log.md), at uplift 50.9 and ratio 3.0 (log only). PRD 9.1 also requires efficacy to be re-confirmed on the scoring pool because pilot estimates are subject to the winner's curse, and that has not run.

## Disclosures

| Item | What is known | Effect on these results | Source |
|---|---|---|---|
| Route markers | `route_run.py` has passed `--debug 2` on every SimLingo route, which draws route points and scenario trigger points into the world, and by our reading of the code and frames the policy camera films them. C35 dates the flag to 2026-10-02, and the WHAT_BROKE entry first said 2026-10-05. Expert runs use `--debug 0`. | **Unmeasured.** Every SimLingo row in this report carries the markers. Arms of one pilot share them, except on bends where a patch can hide them on one side. Absolute failure rates and comparison with published scores are in doubt. [H14](experiments/h14-route-markers/protocol.md) is locked, its offline test stopped at the mask check, and its driving stage waits on Chris. | [WHAT_BROKE](../WHAT_BROKE.md), [C35](../../CONFLICTS.md) |
| Cut-route truncation | A cut route can end before its hazard, because `cut_routes.py` measured its tail from the trigger and a scenario's hazard sits `distance` metres past the trigger. | P19's full pilot reads [42 of 53 against 7 of 48](../../results/savio/step5-pilot-p19-main/efficacy.json). Without the 8 flagged pairs of 55 it reads 40 of 45 against 7 of 42, with uplift 72.2 (d), ratio 5.33 (d) and Fisher p 3.6e-12 (d) (exploratory). The flagged pairs failed 2 of 8 and 0 of 6. Truncation hid effect, and the verdict holds. | No data file. [WHAT_BROKE](../WHAT_BROKE.md) records it. This report reproduced the totals from the [route file](../../configs/rollout/step5-pilot-p19-main.xml) and [outcomes](../../results/savio/step5-pilot-p19-main/routes.jsonl) by flagging a pair when `distance` exceeds the straight line from trigger to last waypoint minus 10 m, because a route ends within 10 m of its last point. The entry's split into 4 ending before and 4 undecided is held only there. |
| Truncation in other cuts | P14's scenarios have no `distance`, and P18's `distance` is how far behind the emergency vehicle starts. | The same rule (exploratory, this report, no data file) flags 3 of 10 pairs in [P19's screen](../../configs/rollout/step5-pilot-p19-screen.xml), which failed 2 of 3 and 0 of 3, and 1 of 10 in [P17's screen](../../configs/rollout/step5-pilot-p17-screen.xml), which failed 0 of 1 and 0 of 1. It also flags the injected crossing in three more screens: 2 of 10 pairs in P10's (one lost, and the other failed only in the slice), 1 of 10 in P11's (failed only in the slice) and 2 of 10 in P13's (no failures). These are not `cut_routes.py` cuts, and each is flagged only through the 10 m margin. Removing them lowers P10's and P11's excess from 2 to 1 and leaves P13's at 0, so no verdict changes. The rule flags nothing in the T0 pilots and screens (P3, P4, P7, P8), which supports the headline results. P20's three affected pairs were replaced before any outcome was read. | [WHAT_BROKE](../WHAT_BROKE.md), [H13 amendment](experiments/h13-cross-family-gap/protocol.md) |
| B2 on P19 | B2's `InvadingTurn` stratum holds 42 slice and 7 neighbourhood failures and scores [0.857](data/h12_layer10_plain.json). Step 5 bars a single-factor stratum at 0.4 or above for an interactional gap. | P19 counts as "passes 9.1, fails Step 5's single-factor condition". 9.1's ratio limits neighbourhood failures to half the key, so B2 stays under 0.4 only if the family holds more failures outside the pilot than the key itself (arithmetic). P19 would need more than 56 failures outside the pilot, about 370 routes at the measured 15% ([log](research-log.md)), or about 1,500 to 3,100 SU (estimate, at 4.1 to 8.5 SU a route). Whether such a pool is sensible is for Jerry and Chris to judge. The H13 simulation gives [0.801](data/h13_b2_precheck.json) for P19's real rates (simulated). | [Research log](research-log.md), [C34](../../CONFLICTS.md) |
| Public predicates | PRD 9.1 excludes any predicate written in a shared document from the sealed key. P1 to P20 are all in `gaps/practice/`. | None of these gaps can enter the key, so their public count toward 13.1 is 0 by construction, whatever their verdicts. A blind pool needs new predicates recorded only in `gaps/sealed/`. | [PRD 9.1](../../PRD.md), [C34](../../CONFLICTS.md) |
| Slow disk in the P20 run | CARLA took over 300 s to start, against about 18 s on 2026-11-02, and the first array lost 19 of 20 routes. On one node its port opened in 127 s from scratch and 4 s from node-local disk, `import torch` took 158 s, and a metadata lookup took 20 ms. Slow scratch metadata is the likely cause and is not confirmed. | About 69 SU were lost. Six later routes were stopped by the slow guard at 0.05 to 3.55 simulated seconds and went to rerun without being scored, and the guard was then fixed. Six re-cut routes first attempted 2026-11-04 01:20 to 01:47 (array 40858449) were lost to CARLA startup and evaluator silence before any drive. Whether the slow disk changed any route that did drive is unmeasured. | [WHAT_BROKE](../WHAT_BROKE.md), [research log](research-log.md). No data file. |
| Arm order in the P20 run | The first array placed all of one arm in one task for some tasks, so role can line up with a node there. | The amendment drove each new pair on one GPU. The four discordant pairs all split across tasks and nodes: their neighbourhood routes ran on n0211 twice, n0264 and n0275, and their slice routes on n0217, n0279, n0211 and n0212. Task 3 on n0211 held only neighbourhood routes and both failed, so role and node cannot be separated there. No failure was slice-only, so this changes no verdict. | [WHAT_BROKE](../WHAT_BROKE.md), [H13 amendment](experiments/h13-cross-family-gap/protocol.md) |
| C24's traffic clause | The "another vehicle within 50 m" clause has held on [332 of 332 stored rows](../WHAT_BROKE.md) and counts parked hazards. | The clause does not show oncoming traffic, so it adds little to the P14 to P19 checks. | [WHAT_BROKE](../WHAT_BROKE.md). The count comes from [`h7_check.json`](data/h7_check.json), [`h9_h10_check.json`](data/h9_h10_check.json) and [`h11_p19_main.json`](data/h11_p19_main.json). |
| P19's offset and expert | P19 uses a 1.2 m offset, outside the routes' 0.15 to 0.6 m. The expert PDM-Lite had no vehicle collision on [9 of 9 slice routes](data/h11_expert_p19.json), but it reads the exact offset. | The result may be mainly an out-of-range failure. No camera-only driver has been shown to avoid this traffic, and no dose-response was measured. | [Research log](research-log.md), entries of 2026-11-02 |
| Explained variance labels | `explained_variance` in the data files is measured on the pool's own frames and reads 0.953 to 0.973. The log's 0.904 to 0.93 at layer 10 and 0.900 to 0.937 at layer 14 (H1b) and 0.875 to 0.922 (H3) are held-out values. H12's log line calls its 0.96 to 0.97 held-out, and that range matches the pool value. | All clear the 0.8 floor on either measure, so no dictionary changes status. | [`dev_eval.py`](../../src/discovery/dev_eval.py), [research log](research-log.md) |
| P3's check | P3's manipulation check failed 3 of 5, the frames showed the fog plainly, and the run resumed before any driving outcome was read. P10 and P12 kept their failed checks, so they read as untested. | P3 fails 9.1 either way. | [WHAT_BROKE](../WHAT_BROKE.md), entry of 2026-10-13 |

## Dry run and rehearsal

H15 and H17 ran on 2026-11-04 under protocols locked in `fb7b815`. H18, H19 and H20 ran on 2026-11-06 under the locks named in their entries. All five ran on dev data with a public key, and none is a verdict.

**H15, scoring path.** The scoring path ran end to end on a throwaway key of public gaps and found 0 bugs ([check and spread](data/h15_dry_run.json)). This is the first time real activations reached PRD 13.1's two conditions. Condition 1 reads invalid and condition 2 is not evaluated, both as the [protocol](experiments/h15-scoring-dry-run/protocol.md) expected: no activation axis reaches 0.5 on P4 or P7, and B4, B4p, B5 and B6 have no directive. Neither is a 13.1 reading.

The run also gave the first scores for action residualization. It fits the action-query states on `vision_bridge`, the visual features, and subtracts what that linear fit predicts before the dictionary is trained, so what stays is the part vision does not explain. Chris still has to confirm `vision_bridge` as the visual pool. These rows are exploratory. The best axis is chosen using the key, and each row covers 18 dictionaries.

| Method and variant | P19 best | P19 median | P19 at 0.5 or above | P4 best | P4 median | P7 best | P7 median |
|---|---:|---:|---:|---:|---:|---:|---:|
| M1 raw, plain | 0.705 | 0.375 | 5 of 18 | 0.490 | 0.387 | 0.275 | 0.231 |
| M1 raw, residualized | 0.689 | 0.540 | 13 of 18 | 0.316 | 0.201 | 0.250 | 0.236 |
| B7-pool, plain | 0.500 | 0.372 | 1 of 18 | 0.091 | 0.037 | 0.339 | 0.065 |
| B7-pool, residualized | 0.620 | 0.278 | 3 of 18 | 0.104 | 0.029 | 0.438 | 0.071 |

On P19, residualizing moves M1's median above B7-pool's by 0.262, where the plain medians differ by 0.003. It also lowers M1 on P4, as PRD 9.2 expects. B2's list of scenario names still scores 0.857 on P19, so this does not change P19's standing, and one gap cannot show that the change holds in general. Separately, B7-pool already reads T2 `fires` under [H16's stop rule](experiments/h16-b7-rollout-free/protocol.md) on the plain P19 row above. That reading rests on one dictionary at exactly 0.5, C34's pending median clause and P19's pending label. H16's rule was written on the plain variant, so this table does not settle it. Jerry and Chris decide it, and H16 is held until they do.

**H18, controls for the residualization gain.** Locked in `a4e1860`, job 40967052, 16 SU (measured). The fixed sentence is: "On P19, neither control reaches halfway to the residualization gain, so the gain needs the visual fit." ([result](data/h18_result.json), [protocol](experiments/h18-residual-controls/protocol.md)). The rule is binary, and the numbers beside it qualify it.

| M1 raw on P19 | Best | Median | At 0.5 or above | What it removes |
|---|---:|---:|---:|---|
| Plain | 0.705 | 0.375 | 5 of 18 | Nothing |
| Residualized on vision | 0.689 | 0.540 | 13 of 18 | What `vision_bridge` predicts, 0.808 of the variance |
| Shuffle control | 0.649 | 0.447 | 8 of 18 | Almost only the mean (fit explains 0.008) |
| Variance-matched control | 0.661 | 0.436 | 5 of 18 | 15 leading components, 0.814 of the variance |

- **Part of the gain needs no vision.** The shuffle control removes little more than the average activation, yet it recovers 0.072 of the 0.165 gain (44%). It misses the halfway line by 0.011. Both controls stay below the real residual: the median-minus-real intervals are -0.197 to -0.019 (shuffle) and -0.218 to -0.021 (variance-matched).
- **Removing the mean lifts the baseline more than the method.** Under the shuffle control, B7-pool on P19 reads best 0.812, median 0.666, with 17 of 18 dictionaries at 0.5 or above. That is above every M1 row in this report. It bears on H16's stop rule, which Jerry and Chris still have to decide.
- **Removing the top variance helps P4.** Under the variance-matched control, M1 on P4 reads best 0.672, median 0.500, with 10 of 18 at 0.5 or above. Plain gives 0.490 and 0.387, and the real residual gives 0.316 and 0.201.

So the plain variant's scores move a lot with the dataset mean and the leading directions, and neither is fixed by the PRD. Every row here is exploratory and dev only, and the best axis is chosen using the key. B2 still scores 0.857 on P19. This needs Chris before any preprocessing is frozen.

**H19, why M2 finds no axes.** Locked in `8e05103`, amended in `f9bcbb0` after the first plant failed (see below), jobs 40967092 (first plant, withdrawn), 40967692 (plant check) and 40967739, 6.4 SU in all (measured). The fixed sentence is: "No tried setting recovers a planted group of 25 failures, so M2's zero on real pools says little about whether the gaps are there." ([result](data/h19_result.json), [protocol](experiments/h19-m2-settings/protocol.md)).

- **Defaults:** M2's default settings again give 0 axes on H12's pool. No setting of the 16 reaches 0.5 on P4, P7 or P19. The best is 0.397 on P19, and those settings were chosen using the key.
- **Plant:** the plant shifted the lead-distance error by 2.3 standard deviations for 25 failures, each knowing the state on 67% to 100% of its window frames. It moved them out of the large catch-all cluster, which shrank from 221 failures to 169, but no setting grouped them: their best Jaccard is 0.0 under every setting.
- **What this means:** M2 as configured cannot find a strong single-state group on this pool, so its zero is not evidence that the gaps are absent from its residuals.
- **The first plant was invalid.** Lead distance is blank when no car is ahead, so most of the shift never reached a residual ([WHAT_BROKE](../WHAT_BROKE.md), 2026-11-06). Its reading was withdrawn before the rerun.

**H20, mean removal on a second pool.** Locked in `4811f76`, amended in `bf8c810` to score per gap because its key has no interactional gap, jobs 40967835 and 40968012, 25 SU (measured). The fixed sentence is: "On H1's pool, removing only the mean moves a method's median Jaccard on a planted gap by at least 0.1, so method readings depend on a preprocessing step the PRD does not fix." ([result](data/h20_result.json), [protocol](experiments/h20-centring-second-pool/protocol.md)). One cell of 9 moved: B7-pool on P8.

| Median (best) over 18 dictionaries | Plain | Mean removed | Vision residualized |
|---|---:|---:|---:|
| M1 raw on P4 | 0.353 (0.644) | 0.265 (0.382) | 0.155 (0.205) |
| M1 raw on P7 | 0.191 (0.208) | 0.208 (0.236) | 0.191 (0.217) |
| M1 raw on P8 | 0.213 (0.292) | 0.227 (0.250) | 0.221 (0.264) |
| M1 capped on P4 | 0.366 (0.644) | 0.302 (0.667) | 0.139 (0.205) |
| M1 capped on P7 | 0.171 (0.211) | 0.203 (0.236) | 0.159 (0.217) |
| M1 capped on P8 | 0.200 (0.292) | 0.227 (0.250) | 0.221 (0.264) |
| B7-pool on P4 | 0.042 (0.077) | 0.081 (0.147) | 0.044 (0.133) |
| B7-pool on P7 | 0.206 (0.287) | 0.230 (0.270) | 0.217 (0.254) |
| B7-pool on P8 | 0.215 (0.430) | 0.364 (0.479) | 0.395 (0.483) |

The same pattern shows on both pools. Removing the mean lifts B7-pool, by 0.149 on P8 here and 0.294 on P19 in H18, and it lowers M1 on P4, by 0.088 here and 0.074 in H18. Vision residualization lowers M1 on P4 further, to a median of 0.155, as PRD 9.2 expects for a perceptual gap. No cell here reaches 0.5 in its median. H20's plain column retrains H1b's grid on the same pool and reads differently from it, for example M1 raw on P4 at 0.644 and 0.353 against H1b's 0.553 and 0.405, so a retrain alone moves these cells. The vision fit's `explained_on_fit` is 0.786. All of this is exploratory, and the best axis is chosen using the key. [C37](../../CONFLICTS.md) proposes what to fix before the methods are frozen.

**H17, causal rehearsal on P4's axis.** The fixed sentence is: "In replay, removing the axis moves the plan more than random edits of equal size. H17 could not show that it moves the plan more on failing frames than on their clean twins. Its mean shift does not exceed the 95th percentile of other latents of the same dictionary at that size." ([result](data/h17_result.json)). All five checks held, on 37 pairs and 421 frames.

| Outcome | Axis shift (m) | Floor (m) | Random 95th percentile (m) | Excess interval (m) | Failing minus control interval (m) | Other latents' 95th percentile (m) |
|---|---:|---:|---:|---:|---:|---:|
| Speed | 0.121 | 0.06 | 0.105 | 0.001 to 0.029 | -0.016 to 0.016 | 0.150 |
| Route | 0.028 | 0.03 | 0.029 | -0.004 to 0.002 | -0.006 to 0.003 | 0.039 |

Speed clears the rule and route stops at both its floor and its interval. The excess over random on clean frames is 0.017 m on speed, close to the 0.016 m on failing frames. Beside the rule, with no bearing on it: the axis's raw shift on failing frames against clean twins is 0.121 and 0.069 m on speed and 0.028 and 0.013 m on route, the founder latent alone gives 0.121 and 0.028 m, and pairs whose rollout is in the axis shift 0.135 m on speed against 0.105 m for the rest. The twins have no patch, so that raw comparison is confounded, and the rule reads excess over random in each arm. The random control is an equal-length translation, where PRD 9.2 names removal along a random direction. This is a dev rehearsal in offline replay on an axis at P4 best 0.490, median 0.387 across 18 dictionaries, chosen using the key. It is not Step 9's verdict, and every axis card keeps `causal: untested`.

**H14 offline, marker replay.** Untested. Its mask failed the check before any replay (72% of dots caught against a limit of 90%, and a ring on a vehicle in 13 of 50 frames against a limit of 0, [data](data/h14_mask_check.json)). The route-marker effect stays unmeasured.

## PRD checks that never ran

Sources are [`progress.yaml`](../steps/progress.yaml), [PRD section 13](../../PRD.md) and a search of the code on 2026-11-04, with rows 6 and 7 rechecked on 2026-11-06.

| Step | Check | `progress.yaml` | State | What the repo shows |
|---|---|---|---|---|
| 3 | Savio replay within 1e-3 m of the log, in bfloat16 (a 16-bit number format) | Open | Ran, not met | Replays of 331 frames sit 1 to 3 rounding steps (median 1 to 3 cm) from the log, and three replays agree to 0.0 m. C22 proposes replay against replay and is pending. Numbers are in [STATUS](../STATUS.md), and jobs 39784216 and 39784287 have no file in the repo. |
| 4 | None open | All done | Done | The chosen site is driving queries at layer 10. |
| 5 | 4 to 6 gaps plus 2 decoys pass 9.1 | Open | Not met | Four public gaps pass, and no practice gap is marked as a decoy. Chris reports control 1, enumerable 1 and interactional 0 passing among 9 sealed candidates, and visually novel 1 and kinematic 0 among decoys passing C31 ([issue 8](https://github.com/Christopher-Vu/HondaResearchInstitute/issues/8)). His kinematic decoy screen ran and is read privately. |
| 5 | No single-factor stratum at 0.4 with any interactional gap | Open | Ran once, failed | It was measured on P19 only, at [0.857](data/h12_layer10_plain.json). |
| 5 | Efficacy re-confirmed on the scoring pool | Not listed | Never ran | No scoring pool exists. |
| 6 | B7 variant A, the rollout-free statistics | Open | Never ran | The code accepts variant A ([`activation_stats.py`](../../src/baselines/activation_stats.py)) and [the spec](../steps/b7-gap-signal.md) drew its sample on 2026-10-15. Every stored B7 result is variant B. |
| 6 | The stop-and-re-plan rule if B7 matches our methods | Not listed | Read on stored data, undecided | [The spec](../steps/b7-gap-signal.md) fires this rule if either variant recovers the practice gaps as well as our methods do. On stored H12 data B7-pool reads T2 `fires` under H16's rule: P19 best 0.500 on 1 of 18 dictionaries, median 0.372, against M1 0.705 and 0.375. It rests on one dictionary at exactly 0.5, C34's pending median clause and P19's pending label. Under H18's shuffle control, which removes little more than the mean, B7-pool on P19 reads best 0.812, median 0.666, with 17 of 18 at 0.5 or above, above every M1 row (exploratory, best axis chosen using the key). C37 proposes freezing B7 with the same preprocessing as the method it is compared against. Jerry and Chris decide it before a test pool is built. |
| 7 | Probe-residual emits directives | Open | Ran, no axes | M2 scores 0 on every real pool in the data files. The [log's audit](research-log.md) of 2026-10-31 23:26 calls this a valid null. H19 found that no tried setting recovers a planted group, so the zero says little about whether the gaps are there. |
| 7 | Describability gate with its shuffle control | Open | Never ran | `src/gate/` holds only `__init__.py`. [The spec](../steps/describability-gate.md) waits on model pins. |
| 7 | Residualized preprocessing | Not listed | Ran on two pools, dev only | H15 and H18 on H12's pool, H20 on H1's pool, using `vision_bridge` as the visual pool pending Chris. |
| 7 | Dataset-mean step named before the methods freeze | Not listed | Open, C37 proposed | Removing only the success-frame mean moved B7-pool's P8 median by +0.149 (H20), and H18's shuffle control moved its P19 median by +0.294. |
| 7 | Nuisance-projected preprocessing | Not listed | Never ran | A search of `src/` finds no code for it. |
| 7 | SAE waypoint error with reconstructions spliced back | Not listed | Never ran | [`sae.py`](../../src/discovery/sae.py) says it is not done there. |
| 7 | Naming the primary method (D3) | Not listed | Open | [CONFLICTS D3](../../CONFLICTS.md) closes at this step and is still open. |
| 8 | Preregistration of the 13.1 rule | Not listed | Drafted, unsigned | [`harness/PREREGISTRATION.md`](../../harness/PREREGISTRATION.md) is a draft with an empty signature table. It takes effect only when Chris and Jerry sign it and `prereg-v1` tags it. |
| 8 | Key sealed and hashed | Open | Never ran | [`seal.py`](../../src/harness/seal.py) and its tests exist. `KEY_COMMITMENT.txt` does not exist, and this checkout has no `gaps/sealed/` folder. |
| 8 | Frozen tags in order | Not listed | Never ran | `git tag` lists only `b4-factors-v1`. |
| 8 | Test pool generated | Open | Never ran | No test-pool config exists under `configs/rollout/`. |
| 8 | Scored once | Open | Never ran | No test pool exists to score. |
| 8 | Three evaluation seeds, paired by route (PRD 12.4) | Not listed | Never ran | Each stored pilot lists every route once per arm. |
| 8 | Sealed-key guard in CI, the automatic checks on each push | Not listed | Off | CI runs only by hand under [C33](../../CONFLICTS.md), and C33 asks for it back before sealing. |
| 9 | Causal verdict for every top axis | Open | Never ran | Directives carry `causal: untested`. H17 rehearsed the removal on one axis in replay, which is not Step 9's verdict, and no module writes a verdict onto a card. |
| 9 | Go or no-go under 13.1 | Open | Never ran | The harness-validity check and route bootstrap exist in [`scoring.py`](../../src/harness/scoring.py) and [`bootstrap.py`](../../src/harness/bootstrap.py), and neither has seen a test pool. |
| 10 | One full generate and fine-tune cycle | Open | Never ran | Only [the spec](../steps/10-closed-loop.md) exists. A search of `src/` and `scripts/` finds no LoRA or fine-tuning code. |
| 10 | No-degradation check | Open | Never ran | It depends on the cycle above. |
| 10 | Solvability of authored scenarios | Not listed | Never ran | Expert checks ran on practice gaps only ([P14](data/h8_expert_p14.json), [P19](data/h11_expert_p19.json)). |
| 11 | Stub adapter runs end to end | Open | Partly | [`stub_adapter.py`](../../adapters/stub/stub_adapter.py) exists and [its test](../../tests/test_stub_adapter.py) passed 4 of 4 on 2026-11-04 when this report ran it. It covers probe-residual and B3 ([adapters README](../../adapters/README.md)). The refactor of SimLingo's adapter and the check on a second real policy have not run. |
| 12 | Paper draft | Open | Never started | The repo holds no `.tex` file outside `upstream-99p/`. |

## Cost

SU is Savio's service unit. The research log is the only record of these figures, and no data file holds them. From the goal's start the log measures CPU time from `sacct`, Savio's accounting command, times 3.67.

| Stage | SU | Running total for the goal | Source |
|---|---:|---:|---|
| All work before the goal, on the imhaohao account | 6595.83, not split by stage in the log | Baseline, not counted | [Log](research-log.md), 2026-10-31 22:35, read with `check_usage.sh` |
| H1 to H4, including H3's wave 3, P4-confirm and P7-confirm rollouts | 2237 | 2237 | [Log](research-log.md), 2026-11-01 09:37 |
| H5 screens, P10 to P12 | 343 | 2580 | [Log](research-log.md), 2026-11-01 12:15 |
| H6 screen, P13 | 52.6 | 2632 | [Log](research-log.md), 2026-11-02 02:14 |
| H7 screens, P14 to P16 | 241 | 2873 | [Log](research-log.md), 2026-11-02 03:34 |
| H8 expert check, P14 | About 81 | 2954 | [Log](research-log.md), 2026-11-02 06:41 |
| H9 P14 pilot and H10 screens, P17 to P19 | About 1024 | 3978 | [Log](research-log.md), 2026-11-02 11:09 |
| H11 expert check, P19 | 101 (d), by difference | 4079 | [Log](research-log.md), 2026-11-02 12:22 |
| H11 full pilot, P19 | About 864 | 4943 | [Log](research-log.md), 2026-11-02 19:40 |
| H12 methods on P19 | About 16 | 4959 | [Log](research-log.md), 2026-11-03 |
| H13 pre-check | 0 | 4959 | [Log](research-log.md), 2026-11-03 |
| First P20 screen lost to CARLA start, with probes | 70 (d), by difference | 5029 | [Log](research-log.md), 2026-11-03. [WHAT_BROKE](../WHAT_BROKE.md) says about 69. |
| Failed probe and empty scoring | 4 (d), by difference | 5033 | [Log](research-log.md), 2026-11-03 |
| P20 screen driving and same-node disk tests | About 167 (d), by difference | About 5200 | [STATUS](../STATUS.md), 2026-11-03 21:00. The log has no figure. |
| P20 rerun and amended pairs | About 144 (d), by difference | 5344 | `sacct` CPU time at 3.67 SU per core hour, 2026-11-04 20:55. Includes about 37 SU lost in array 40858449. |
| H15 and H17 | 61 (d), 12 and 49 | 5405 | `sacct` CPU time at 3.67 SU per core hour, 2026-11-04 22:49. |
| H18, H19 and H20 | 47.7 (d): 16.3, 6.4 and 25.0 | 5453 | `sacct` CPU time of the study's named jobs, 2026-11-06 03:30. Jerry's other jobs on the account are left out. |
| Sealed work | About 6,000, Chris's figure ([issue 8](https://github.com/Christopher-Vu/HondaResearchInstitute/issues/8)) | Not in this table | Chris holds the figure ([ask](chris-ask.md)). |

The goal's budget was 6000 SU and Jerry raised it to 10000 ([STATUS](../STATUS.md), 2026-11-03 19:30). The log puts H6 at 2.6 SU a route and H7 at about 4 SU a route, and [H13's protocol](experiments/h13-cross-family-gap/protocol.md) uses about 8.5 SU a route for P19's pilot, which is 864 SU over 101 scored routes, or 7.85 over 110 listed.

## Citations

Each entry is in the evidence ledger named beside it. Publication venues are given as those ledgers state them, and this report rechecked nothing online.

| Work | Used here for | Ledger |
|---|---|---|
| Renz, Chen, Arani, Sinavski. SimLingo. CVPR 2025, arXiv:2503.09594. | The policy under test. | [`CITATION_AUDIT.md`](../../upstream-99p/docs/CITATION_AUDIT.md), `simlingo`; [findings A3](../step0-trackA-findings.md) |
| Jia, Yang, Li, Zhang, Yan. Bench2Drive. NeurIPS 2024 Datasets and Benchmarks Track, arXiv:2406.03877. | Routes, failure label and scoring. | [`CITATION_AUDIT.md`](../../upstream-99p/docs/CITATION_AUDIT.md), `bench2drive-dataset-protocol` |
| Dr. VLA, arXiv:2603.19183. CoRL 2026 as stated on 2026-10-01; unverified since. | The activation-statistics baseline B7. | [findings A1](../step0-trackA-findings.md) |
| Fail2Drive, arXiv:2604.08535. IROS 2026 as stated on 2026-10-01; unverified since. | P5 and P6's assets, and the 87% collision figure P5 was compared with. | [findings A2](../step0-trackA-findings.md) |

## Venue dates

These dates come from [PRD section 15](../../PRD.md), which last checked them on 2026-10-06. **All are unverified since 2026-10-06**, and they are older than the two-week limit in `CLAUDE.md`. This report does not pick a venue.

| Venue | Stated date |
|---|---|
| CVPR 2027 | Registration 10 November 2026 and paper 16 November 2026, anywhere on Earth |
| IEEE IV 2027 | Papers 15 November 2026 |
| RSS 2027 Stage 1 | 4 December 2026, anywhere on Earth |
| IROS 2027 | Papers 1 March 2027 |
