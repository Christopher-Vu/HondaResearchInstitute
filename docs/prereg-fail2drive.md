# Pre-registration — Fail2Drive track (F2)

**Status:** approved by Chris on 2026-11-06 and tagged `f2d-prereg-v1`. The first draft (`06dc9f2`) was written on
2026-11-05, before any outcome from either full screen had been read.

The tag came before anyone read the full screens (SimLingo array 40950230, TransFuser++ array 40954768) and before the
test pool (F3). Changes after the tag go in a dated "amendment" section, labelled post hoc where they follow data.

Chris's framing: the aim now is results. Presentation is worked out after the first run.

Scope is `docs/prd-fail2drive.md`. Terms used here:

- A **type** is one of Fail2Drive's 17 scenario types.
- Its **slice** is its generalization routes, and its **neighbourhood** is their base twins.
- **Failure** is the harness's existing outcome label.
- A **unit** is one (model, type) pair.

## 1. Pools and selection

**Screens are descriptive.** The one-seed screens (SimLingo: F0 and F1; TransFuser++: F6) are reported in full. They
select nothing.

**Test pool.**
- Every type, every pair, for each model.
- Six traffic seeds, 101 to 106, disjoint from the screens' seed 24.
- Route ids are `seed * 100000 + id`, so each seed's copy is scored separately (`adapters/simlingo/fail2drive_pairs.py`).
- No routes were authored for this round: the minimum viable pool is Fail2Drive's own pairs. Toolbox-authored pairs
  come later, if credibility needs them, under rules fixed before they are driven.

**Classification per unit, on the test pool only**, in this order:
1. **Gap:** passes `PRD.md` §9.1. That is at least 30 slice runs, uplift at least 20 points, ratio at least 2×, and
   Fisher p < 0.01. The paired McNemar test is reported beside it.
2. **Ceiling:** a gap whose slice fails at least 95% and whose neighbourhood fails at most 20%. Scored as
   `T0_control`.
3. **Decoy:** C31 holds, meaning |uplift| ≤ 10 points and McNemar p > 0.2.
4. **Background:** every other unit. It stays in the pool and is never scored as a gap or decoy.

The count of types tested (17 per model) is reported beside every p value.

## 2. The B4 split

**What B4 is.** `configs/baselines/b4_factors_v1.yaml`, tagged `b4-factors-v1` on 2026-10-15, is our enumerated
factor list. It has 12 factors whose levels are rules on the logged state.

**The rule.** A gap is **B4-unnamed** if no single B4 level's failing rollouts have Jaccard of at least 0.4 with the
gap's failing rollouts, on that model's test pool. It is **B4-named** otherwise.
- It is computed from states and outcomes, before any method's directive is scored.
- B4's pairwise conjunctions are reported as secondary and do not decide the split.

**Tiers in `src/harness/schema.py`:**

| Gap | Tier |
|---|---|
| Ceiling | `T0_control` |
| B4-named | `T1_enumerable` |
| B4-unnamed | `T2_interactional` |

In the paper the tier is named "B4-unnamed", never "interactional".

**Prediction, from reading the level definitions** (the measured rule decides):
- *Named:* Animals, CustomObstacles, PassableObstacles, Wall, FullyBlocked, ConstructionPedestrian,
  ConstructionPermutations, OppositeConstruction, RightConstruction, PedestriansOnRoad, PedestrianCrowd,
  PedestrianOtherBlocker, HardBrake.
- *Unnamed:* BadParking, ImageOnObject, ObscuredStop, RightOfWay.

## 3. Methods, labels and freezing

**Label hiding.**
- Methods and baselines see shards from `adapters/simlingo/export_activations.py` with these fields removed:
  `scenario`, `practice_gaps`, `role`, `neighbourhood_of`, `base_id`, `pair`, `seed`, `source`, and the route id.
- Routes are renamed by a salted hash, and the salt stays with the scorer.

**Activation sites, per model.** Each model's sites and layers are chosen by failure-versus-success probe AUROC
(area under the ROC curve) on that model's *screen* rollouts. That is the Step 4 rule, applied before the test pool
is read, and it uses outcomes but never scenario labels. Dictionary sizes come from `PRD.md` §12.2. The axis budget M
is 10.

**Methods compared:** contrastive, SAE (sparse autoencoder) and probe residual, against random, B4, B3, B7 and B2-state
(`PRD.md` §9.2–9.3). B2 with labels runs once, as an oracle ceiling only.

**Freezing.** Methods and settings are frozen and tagged `f2d-methods-v1` before any method reads a test pool. Scoring
runs once per model.

**Contamination.**
- A synonym list for each type is fixed in this file before `f2d-methods-v1`. It is a hand-written list, expanded once
  by a language model, then frozen.
- Every method or gate step that calls a language or vision model is first run with no rollout data.
- Any axis whose description matches a type's list is flagged in every table. Matching is mechanical.

## 4. Analysis

**Primary.**
- Mean best Jaccard on B4-unnamed gaps: the best activation method minus the best non-oracle baseline.
- Pooled over every B4-unnamed unit of both models, each unit weighted equally.
- 95% interval from `src/harness/bootstrap.py`, resampling Fail2Drive pairs jointly across models and seeds (models
  share routes). The "best" selections are re-made in every replicate.
- Bar: margin ≥ 0.15, with the interval excluding 0.

**Always reported beside it.**
- Results by model.
- Results by tier (ceiling, B4-named, B4-unnamed).
- Results per gap.
- Recall at threshold 0.5 and budget M.
- Decoy hit rate.
- Best and median across dictionaries, with "the best axis is chosen using the key" stated beside them (C34).

## 5. Migration bar

The project migrates to this track if all three hold:

1. At least 2 B4-unnamed units are confirmed, covering at least 2 distinct types.
2. The primary margin meets its bar.
3. Nothing was trained on Fail2Drive data.

What is reported if it fails is decided after the first run, and labelled as such.

## 6. Running order

1. SimLingo's test pool (`configs/rollout/f2d-test-simlingo-s101.yaml` to `s106`) runs first, on Chris's go of
   2026-11-06.
2. TransFuser++'s test pool runs after its screen is read.
3. Lost routes are rerun once, then listed and excluded.
