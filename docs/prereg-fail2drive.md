# Pre-registration — Fail2Drive track (F2), DRAFT

**Status:** draft, written 2026-11-05 while the full screen (array 40950230) was still running. No outcome from it
had been read. When Chris approves it, this file is tagged `f2d-prereg-v1` before any F3 drive starts. After the tag,
it is not edited; changes go in a new section headed "amendment" with its date and reason.

Scope is `docs/prd-fail2drive.md`. Terms used here:

- A **type** is one of Fail2Drive's 17 scenario types.
- Its **slice** is its generalization routes, and its **neighbourhood** is their base twins.
- **Failure** is the harness's existing outcome label.
- The **screen** is F0 plus F1: one seed (24) and every pair (`results/savio/f2d-repro-screen/` and the F1 scoring
  output).

## 1. Selection, read once from the screen

**Ceiling.** A type whose slice fails 100% on the screen while its neighbourhood fails at most 20% is a ceiling gap.

**Gap.** A type is a gap candidate if its screen uplift (slice failure rate minus neighbourhood failure rate) is at
least 40 points. That is at least 2 excess failures on 5 pairs, or 4 on 10.

**Decoy.** A type is a decoy candidate if C31's decoy rule holds on the screen: |uplift| ≤ 10 points and McNemar p >
0.2.

**Background.** Every other type is background. It is in the pool if the budget allows (§3), and is never scored as
a gap or decoy.

**Confirmation on the test pool (F3).** Recorded before scoring and never changed by method results:

- A gap candidate becomes a scored gap only if it passes `PRD.md` §9.1: at least 30 slice runs, uplift at least 20
  points, ratio at least 2×, Fisher p < 0.01.
- A decoy candidate becomes a scored decoy only if C31 holds on the test pool.
- Candidates that fail confirmation are reported with their statistics and dropped from scoring.
- The count of types screened (17) is reported beside every p value.

## 2. The B4 split

Fail2Drive's types are mostly single factors. So the "enumeration misses it" argument is carried by `PRD.md` §13
Step 5's single-factor condition, applied to B4, our committed factor list (`configs/baselines/b4_factors_v1.yaml`,
tag `b4-factors-v1`).

- **B4-unnamed.** A scored gap is B4-unnamed if no single B4 level has Jaccard of at least 0.4 with that gap's
  failing rollouts on the test pool. It is B4-named otherwise.
- **When this is read.** It is computed from states and outcomes only, after F3 and before any method's directive is
  scored. It does not depend on any method.

**Tiers in the scoring code** (`src/harness/schema.py` `TIERS`):

| Scored gap | Tier |
|---|---|
| Ceiling | `T0_control` |
| B4-named | `T1_enumerable` |
| B4-unnamed | `T2_interactional` |

`T2_interactional` is the slot the existing bootstrap and §13.1-style test read. The paper names the tier
"B4-unnamed", never "interactional".

**Prediction, written now from the level definitions and checked against the measured rule:**

| Type | Predicted |
|---|---|
| Animals | named (animal) |
| CustomObstacles | named (unusual_obstacle) |
| PassableObstacles | named (unusual_obstacle) |
| Wall | named (unusual_obstacle) |
| FullyBlocked | named (unusual_obstacle) |
| ConstructionPedestrian | named (unusual_obstacle) |
| ConstructionPermutations | named (unusual_obstacle) |
| OppositeConstruction | named (unusual_obstacle) |
| RightConstruction | named (unusual_obstacle) |
| PedestriansOnRoad | named (pedestrian_near) |
| PedestrianCrowd | named (pedestrian_near) |
| PedestrianOtherBlocker | named (pedestrian_near) |
| HardBrake | named (hard_brake) |
| BadParking | unnamed |
| ImageOnObject | unnamed |
| ObscuredStop | unnamed |
| RightOfWay | unnamed |

A named prediction can still measure unnamed, for example when a B4 level also fires on many neighbourhood routes.
Disagreements are reported. The measured rule decides.

## 3. Test pool (F3)

**Content.**

- **Routes:** every pair of each gap candidate and decoy candidate. Background types are added in screen order of
  their uplift, largest first, while the budget allows.
- **Seeds:** six traffic seeds, 101 to 106, none used before. Each route runs once per seed.
- **Capture:** `capture_every: 10` and `capture_token_layers: [10, 11]`, as in the screens.
- **Settings:** Fail2Drive's CARLA build and evaluator, `debug_level: 0`, the pinned SimLingo checkpoint. Everything
  else is copied from `configs/rollout/f2d-screen-full.yaml`.

**Budget.** Planned spend is what remains of the track's 2,500 SU after F0 and F1, at the measured rate per route.

If the candidates alone exceed it, they are kept in this order until it is spent:

1. Ceiling gaps, at most 2. They are needed only as harness checks.
2. Decoys, at most 2.
3. Gaps predicted B4-unnamed.
4. Gaps predicted B4-named, by screen uplift, largest first.

Seeds are never cut below 6 for a kept type.

**Lost routes.** Rerun once. A route still without an outcome is listed and excluded.

## 4. Label hiding and freezing

- **What methods see.** Methods and baselines receive the exported shards (`adapters/simlingo/export_activations.py`)
  with these fields removed: `scenario`, `practice_gaps`, `role`, `neighbourhood_of`, `base_id`, `source`, and the
  route id.
  - Routes are renamed with a salted hash.
  - The salt and mapping stay with the scorer until scoring is done.
- **Freezing.** Methods, their hyperparameters and the axis budget M (10, as B4's `budget_m`) are frozen and tagged
  `f2d-methods-v1` before any method reads the test pool.
- **One scoring run.** Scoring runs once. Any re-run is labelled post hoc.
- **B2.**
  - B2 runs on observable state strata only.
  - "B2 with labels" (scenario type as a stratum) runs once as an oracle ceiling. It is never compared as a baseline.

## 5. Contamination check

Every method or gate step that calls a language or vision model is run once with its prompt and no rollout data.

- Any Fail2Drive type name, or a close paraphrase, that it produces this way is listed.
- An axis that matches a listed type is flagged in every table.
- Close paraphrases are judged by Chris and Jerry together, before scoring.

## 6. Analysis

**Primary.**

- Recall on B4-unnamed gaps per method, from one Hungarian assignment on failing-rollout Jaccard, threshold 0.5,
  budget M (`src/harness/scoring.py`).
- The best activation method's mean best Jaccard on B4-unnamed gaps minus the best non-oracle baseline's, with a 95%
  interval from `src/harness/bootstrap.py`.
  - The bootstrap resamples Fail2Drive pairs, not rollouts.
  - The "best" selections are re-made in every replicate.
- This is the single pre-registered test, with no multiplicity correction.

**Secondary, labelled exploratory.**

- Recall on B4-named and ceiling gaps.
- Decoy hit rate.
- Precision.
- Spearman correlation with severity.
- Every axis score is given as best and median across dictionaries, with "the best axis is chosen using the key"
  beside it (C34).
- Per-gap results for every gap.

## 7. Migration bar

As fixed in `docs/prd-fail2drive.md` §8, before the screen was read. The project migrates if all three hold:

1. At least 2 B4-unnamed gaps pass confirmation.
2. The primary test's margin is at least 0.15, with an interval excluding zero.
3. Nothing was trained on Fail2Drive data.

Otherwise the result is reported as a measured comparison.
