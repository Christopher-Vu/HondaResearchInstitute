# Preregistration v1

**DRAFT. This takes effect only when Chris and Jerry sign it and `prereg-v1` tags it.** Until then it binds nobody and may change. After signing it is not edited, and any change is a new version reported as one (`PRD.md` 13.1).

Drafted 2026-11-04 from `PRD.md` 9.1 and 13.1, `CONFLICTS.md` C23, C31 and C34, and `docs/steps/08-seal-generate-score.md`. No test pool exists and no test-pool number has been seen. This file holds no gap predicate, and every P-numbered gap is public and excluded from the key (`PRD.md` 9.1).

| Signature | Name | Date | Commit |
|---|---|---|---|
| Required | Chris | | |
| Required by Step 8's spec | Jerry | | |

## 1. The go/no-go rule

Read at Step 9. Verbatim from `PRD.md` 13.1:

> 1. **Harness validity.** At least one control gap recovered by at least one
>    method using the non-residualized variant, **and** at least two interactional
>    gaps re-confirming efficacy on the test pool.
> 2. **Activation advantage.** The best activation method beats *every* baseline on
>    interactional-gap recall, and its mean best Jaccard is at least 0.15 above the
>    best baseline's with a 95% interval excluding zero, bootstrapped over routes
>    with both "best" selections re-made in every replicate.
>
> If both hold, go to the closed loop. If validity holds but advantage does not, the
> paper is the comparative study — honest, real, and on a benchmark nobody has
> built. If validity fails, the paper is the negative result about planting gaps,
> and the remaining time goes to fixing the harness.

How those words are computed:

| Term | Meaning |
|---|---|
| Recovered | Matched by one Hungarian assignment over the real gaps at failing-rollout Jaccard at least 0.5 (`scoring.py`), with an axis budget of 10 for every method. `PRD.md` 10.2 asks for a fixed budget, and 10 is the `budget_m` default in `schema.py`. Decoys stay out of the assignment and are scored as decoy hit rate. |
| Re-confirming efficacy | On the test pool: uplift at least 20 points, ratio at least 2, McNemar exact p < 0.01, at least 60 complete pairs from at least 30 base routes (C23, Step 8's spec). Fisher is reported beside it. This rule applies only if C23 is accepted (open item 9). Until then C23 itself says `PRD.md` 9.1's Fisher rule stands. |
| Enters the key | Before sealing: uplift at least 20 points, ratio at least 2, Fisher p < 0.01, at least 30 slice rollouts, with failed candidates replaced and the number tried reported (`PRD.md` 9.1). Public predicates are excluded. |
| Decoy passes | Absolute uplift at most 10 points and McNemar p > 0.2 on its paired 60-pair pilot (C31). The decoy judged before 2026-10-18 is reported under both rules. |
| Activation method | One frozen config that emits one directive. B7 and B7-pool count as baselines. |
| Baselines | B1 to B7, plus B8 if C25 is accepted. B3 runs without expert action error, because the rollouts log no expert action (C29), and that weakens the B3 that condition 2 must beat (open item 10). If a required baseline has not run, condition 2 is reported as not evaluated (open item 8). |

**Five code gaps to close before `scoring-frozen-v1`.**

1. `harness_is_valid` counts any method's match, so it must receive only non-residualized reports for condition 1. Which variant counts as non-residualized, with or without the dataset-mean step, is open (C37, pending), because H18 and H20 measured median shifts of up to +0.294 from the mean step alone (dev, best axis chosen using the key).
2. `harness_is_valid` reads efficacy through `Gap.passes_efficacy`, which is Fisher, so it must read C23's rule if C23 is accepted.
3. C31's decoy rule is not coded under `src/`, `scripts/` or `adapters/`.
4. `outcome_pairs` in `efficacy.py` keys on `base_id`, so a second pair on one base overwrites the first, and `paired` sets `base_routes` equal to the pair count. A slice built as 60 pairs on 30 bases would score as 30 pairs and fail. Either the code changes or each slice uses at least 60 distinct bases, and section 5 assumes the second.
5. Each directive carries its own `budget_m`, so the code does not hold every method to 10. The scoring run must refuse a directive whose `budget_m` is not 10.

**A gap with fewer than 60 complete pairs after one rerun does not count as re-confirming.** Its statistics are still reported. P7's 56 pairs show that this can happen, which is why section 5 draws 66.

## 2. The bootstrap

Pinned in `src/harness/bootstrap.py`, function `advantage`:

| Item | Value |
|---|---|
| Resampling unit | Base route, with replacement, so a slice rollout and its twin move together |
| Weights | Each rollout carries its base route's draw count |
| Replicates and seed | 10,000 and 20261016 |
| Refitting | None. Methods are not re-run, and their axes stay fixed |
| Weighted Jaccard | Weight of the intersection over weight of the union, and 0 for an empty union |
| Delta | Best activation method's interactional mean best Jaccard minus the best baseline's, with both maxima re-taken in each replicate |
| Interval | Percentile, 2.5 to 97.5 |
| Margin condition | Point delta at least 0.15 and lower bound above 0 |
| Recall condition | Point estimate on the full pool: strictly above every baseline, and ties fail |

The code takes delta's best method separately from recall's best method, while the PRD says "its". Signing this file accepts the code's reading.

## 3. What is frozen, in order

Each tag lands in git in this order, with its timestamp, except tag 3, which already exists (open item 11).

| # | Tag | Frozen | Precondition |
|---|---|---|---|
| 1 | `scoring-frozen-v1` | `src/harness/scoring.py`, `bootstrap.py`, `efficacy.py` | Tests pass, and section 1's code gaps are closed |
| 2 | `prereg-v1` | This file | Chris and Jerry sign, and section 4's first row is filled in |
| 3 | `b4-factors-v1` | `configs/baselines/b4_factors_v1.yaml` and its sha256 | Already exists at `dc84f8b`, ahead of tags 1 and 2. Its rule was to precede any sealed candidate, and the report states the actual timestamps |
| 4 | `baselines-frozen-v1` | B1 to B8 configs, hashed | Before gaps are finalised |
| 5 | `key-v1` | `KEY_COMMITMENT.txt` = sha256(key ‖ salt) | 4 to 6 gaps and 2 decoys passed. No single-factor stratum has expected Jaccard at least 0.4 with an interactional gap. The sealed-key guard runs in CI or a hook (C33) |
| 6 | `pool-v1` | Test-pool manifest and generation config | After `key-v1`, with the primary method named (`PRD.md` 16.5) |
| 7 | `methods-frozen-v1` | Discovery code and configs | Before any test-pool outcome is read |
| 8 | `score-v1` | The one scoring run's report | After 6 and 7 |

Score once, and label any later run post hoc. Reveal the key and salt only after causal checks and closed-loop scenario specs are committed (`PRD.md` 9.1). Tag 7 freezes the SAE recipe, since training on unlabeled test activations can only happen after the pool exists and before tag 8.

## 4. What the route-marker decision must fix first

`--debug 2` has been on every SimLingo route since `cb474a7` (2026-10-02). Read from the code, any value above 0 draws route points and each scenario's red trigger point and name into the world, and the camera films them. The effect on driving is unmeasured. C35 is a draft pending review. H14 is locked, its offline test stopped at the mask check, and its driving stage waits on Chris.

| Must be fixed | Before | Why |
|---|---|---|
| The pool's `--debug` value: **\_\_** (C35 proposes 0 under every H14 verdict) | `prereg-v1` | This file must name one value. The runner's default stays 2, so `pool-v1`'s config must set `simulator.debug_level` explicitly. That setting was uncommitted work in `route_run.py` when this was drafted, so confirm it landed. |
| No slice differs from its twin by a marker alone | `key-v1` | Above 0, a slice that adds a scenario its twin lacks also adds a visible trigger point and name. Activation methods could read that and log-based baselines could not, which would favour condition 2. This is inferred from the code and has not been tested. |
| Whether sealed candidates' pilots carry to the pool's value | `key-v1` | Pilots at 2 do not show a gap fails at 0. The choice is to re-screen, at 10 pairs for each of 6 slices, or 120 routes at 316 to 943 SU (estimate), or to let test-pool re-confirmation alone decide. |
| Whether dev-fitted parts carry to the pool's value | `methods-frozen-v1` | The layer choice, standardization, probes and stale latent were all fitted at 2. H14's offline measure stopped untested at its mask check, so a recapture or an amended mask has to support them (C35). |

## 5. The smallest defensible test pool

**The pool has 992 rollouts.** This is a floor derived from the rules below, and no pool has been run.

| Rule | Source | Result |
|---|---|---|
| 1 control, 1 enumerable, 2 interactional, 2 decoys | `PRD.md` 9.1, Step 5 | 6 slices |
| At least 60 complete pairs per slice | `PRD.md` 9.2, C23 | Floor of 60. As coded, that means one pair per base, so 66 draws need 66 distinct bases per slice. Bench2Drive-220 holds 5 routes per scenario family (C23), so a slice needs cut routes or several families. |
| Pilots kept 451 of 475 planned pairs, worst 46 of 55 (measured, eight full pilots). Only P4's main pilot kept all of its pairs. | `efficacy.json` in `results/savio/step5-pilot-p{4,7,8,14,19}-main/`, `step5-confirm-p{4,7}/` and `step5-pilot-p3/` | Draw 66, which gives about 63 complete pairs on average. A slice falls under 60 about 5% of the time at the pooled rate (7% without P3) and about 93% of the time at P19's rate (arithmetic, independent pairs). Drawing 70 lowers those to about 0.1% and 61%, and needs about 1,051 rollouts. |
| Slices with twins | Step 8's spec | 6 x 66 x 2 = 792 |
| All slices under 40% of the pool | `PRD.md` 9.2 | 396 / 0.40 = 990, so at least 991 rollouts and 199 background. This draft applies the limit to the pool as designed, and not to scored rollouts, because two lost background routes would reach 40.0%. |
| Round the background up | | 200, so 792 + 200 = 992 |
| Each slice 4 to 8% of the pool | `PRD.md` 9.2 | 66 / 992 = 6.7%, and all slices 39.9% |

**It would cost about 5,043 SU (estimate), with a range of 2,609 to 7,792.** Rates come from `docs/research/research-log.md`, and from H14's protocol for Step 2 and Step 4, as total SU over routes listed, so lost routes and scoring jobs are included. No logged run is left out. All of these ran with `--debug 2`.

| Measured run | SU / routes | SU per route | x 992 routes | Conditions |
|---|---|---:|---:|---|
| H6, one screen | 52.6 / 20 | 2.63 | 2,609 | Token capture, 2 routes per A40, after the per-step PNG fix |
| H7, three screens | 241 / 60 | 4.02 | 3,985 | Token capture, 3 per A40, with long stalls on P15 and P16 |
| Step 2, Bench2Drive-220 | 910 / 220 | 4.14 | 4,103 | No token layers, 2 per A40, before the PNG fix |
| Goal spend through H3, whose routes were background and two pilots | 2237 / 440 | 5.08, an upper bound | 5,043 | Token capture. The SU is cumulative from the goal's start, so any other Savio job in that window is included. |
| Step 4 Part C | 658 / about 125 | 5.26 | 5,222 | 2 per A40 |
| H9 and H10, one pilot and three screens | 1024 / 180 | 5.69 | 5,643 | Token capture, 3 per A40 |
| H5, three screens | 343 / 60 | 5.72 | 5,671 | Token capture, 2 per A40, 58 routes scored |
| H11, P19's pilot | 864 / 110 | 7.85 | 7,792 | Token capture, 3 per A40, long routes. Over the 101 scored routes the same spend is 8.55, which is the "about 8.5" in H13's and H14's protocols. |

H3 is the central figure because its mix of background and pilots with per-token capture is closest to this pool, though it predates the 2026-11-02 speed-up. Step 8's spec uses 4.1 SU per route, which is Step 2's rate.

**Budget.** 5,453 of Jerry's 10,000 SU are spent (measured 2026-11-06 03:30, study jobs by name), so about 4,547 remain. That allows 4.58 SU per route, so the pool fits at H6's, H7's and Step 2's rates and at none of the other five. H14's first stage (about 660 SU, estimate) would leave about 3,887, or 3.92 SU per route, and only H6's rate still fits. Re-measure before tag 6.

**Not in that figure:**

- B4's native renders, at up to 1,080 rollouts before reuse (18 levels x 30 pairs, C30), or 2,840 to 8,483 SU at the same rates. Pool plus B4 is then 5,449 to 16,275 SU.
- Section 4's re-screens, and expert drives if C29 changes.
- Step 9's causal checks.

**Power at this floor.** `PRD.md` 9.2 asks each slice to meet "the power analysis" as well as 60 rollouts. The only power analysis in the repo is C23's exact calculation, and neither it nor the PRD sets a required power. So the floor meets the 60 half, and this table states the power it gives. The table has exactly 60 pairs per slice and treats rollouts and the two gaps as independent (arithmetic). The passing pilots measured neighbourhoods of 15% to 32%. Pair loss below 60 is the separate risk above, and these figures leave it out. The McNemar columns are the rule section 1 uses if C23 is accepted. The Fisher columns are unpaired, and their 15% row reproduces C23's 64% and 93%. Real pairs share a road's difficulty, which this does not model.

| Neighbourhood | True slice rate | Fisher pass | Both gaps, Fisher | McNemar pass | Both gaps, McNemar |
|---:|---:|---:|---:|---:|---:|
| 15% | 40% | 64% | 41% | 61% | 38% |
| 15% | 50% | 93% | 86% | 92% | 84% |
| 20% | 40% | 36% | 13% | 34% | 12% |
| 20% | 50% | 76% | 57% | 74% | 55% |
| 25% | 40% | 15% | 2% | 14% | 2% |
| 25% | 50% | 49% | 24% | 48% | 23% |

Step 8's worked pool of 1,500 rollouts has more power and would cost 3,945 to 11,782 SU at these rates.

**Share of failures.** Each gap would be about 14% of the pool's failures, so a catch-all axis scores about 0.14 (estimate). That assumes round pilot rates of 75% in gap slices, 25% in decoys and 20% in neighbourhoods, plus wave 3's 52 failures in 200 background routes.

## 6. Reporting

C34 applies. The report says which ending it reached, and no 13.1 branch is claimed from dev data. Every axis score appears as best and median across dictionaries, with "the best axis is chosen using the key" beside it. Every gap's p value appears with the candidate count beside it. Per-gap results always appear next to any aggregate (`PRD.md` 10.3).

## 7. Open before signing

1. **This file's path.** `PRD.md` 13.1 names `harness/`. Step 8's spec and `src/harness/README.md` name `src/harness/`, where `seal.py` also writes the key commitment. Settle one path before tag 2.
2. **Primary method.** `PRD.md` 16.5 names it before the pool is generated, while Step 8's table puts it at tag 7, after the pool's tag. This draft follows the PRD, and the method itself is still unnamed (D3).
3. **One dictionary per activation method.** Proposed: `methods-frozen-v1` names one dictionary for each method, chosen without the test pool, and the verdict uses that one. If each of 18 dictionaries could count as a method, the maximum would decide, and on dev the gap between best and median was 0.705 against 0.375 (measured, H12).
4. **The 60-pair floor.** Section 1 drops a gap that ends under 60 pairs, and section 5 states the chance of that at 66 and at 70 draws. Chris may prefer to accept a smaller count at the same p value, or to draw 70.
5. **Step 8's own questions.** Is G = 4 right? Is 66 drawn per slice acceptable against Step 8's 90, which gives its 1,500 rollouts? Does the camouflage rule stay? Ray or the job array? Section 5 assumes G = 4, 66 and camouflage. Camouflage leaves the rollout count alone, but its sub-gap perturbations can raise neighbourhood failures, which lowers the power in section 5 and changes the failure shares there.
6. **B4's cost.** B4 is one of the baselines condition 2 must beat. Before reuse, its renders and the pool together exceed the remaining budget at every measured rate, at 5,449 SU or more against about 4,547, and the amount reuse saves has not been counted.
7. **The shuffle.** `run_order` left one arm alone in a task in the P20 screen (`docs/WHAT_BROKE.md`), so the key holder checks the pool's layout before `pool-v1`.
8. **Condition 2 when a required baseline did not run.** `PRD.md` 13.1 has three branches, and none covers this case. Item 6 makes it the likely case at the current budget. Proposed wording: the report states validity's outcome and that the advantage test was not evaluated, and no closed loop runs. This stays open until the file is signed.
9. **C23 for re-confirmation.** C23 is pending, so section 1's McNemar rule and its 60-pair rule are conditional on Chris accepting it. If he does not, section 1 has to state `PRD.md` 9.1's Fisher rule before signing.
10. **B3 without expert error.** C29 calls the missing block a reason to add it before the go/no-go read. The default in `docs/research/conflicts-sheet.md` departs from that advice, and it needs Chris's explicit decision. Adding the block costs expert drives beside the pool, which section 5 does not count.
11. **Tag order.** Tag 3 already exists ahead of tags 1 and 2, so Step 8's order cannot hold literally. The repo's precedence rule asks for a `CONFLICTS.md` entry on this divergence, and none exists yet.
