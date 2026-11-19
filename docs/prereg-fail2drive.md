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

## 7. Amendment A1: the discovery sprint (post hoc, 2026-11-14)

**Post hoc.** Written after v1 and v2 had been scored on SimLingo's test pool, and before any sprint method is scored.
It governs `docs/prd-discovery-sprint.md`, and `CONFLICTS.md` C39 records why. TransFuser++'s test-pool shards are
still unread by any method. Tagged `f2d-sprint-a1`.

**Rivals.**
- **B3-behaviour** replaces full B3. Full B3 read the simulator's distances to objects, which no fleet logs.
  - Features and grouping are fixed in `docs/research/experiments/f2d-dev-simlingo/b3_behaviour.py` at the tag.
  - It uses ego speed and its derivatives (whole route and the 3 s before the failure) and infraction counts.
  - It excludes distances, scenario and route fields, and expert action error (Chris: out). Steering and braking are
    not logged in these shards.
- **B7 and B7-pool** use one dictionary: the primary dictionary `L10_k64_s0` on the plain preparation. Taking the
  best of 18 would flatter them.
- **B4** is unchanged; it is still the factor list that decides the gap split.
- **B1** is random axes of the same sizes as the method's own, averaged over 50 draws.
- **B2 with labels** is reported as an oracle ceiling only, never as a rival.
- **H25 and the other caption methods** are dropped: neither test pool saved camera frames.

**Scoring.** `docs/research/experiments/f2d-dev-simlingo/sprint_score.py`.
- Every method and rival ranks its own axes, and only its first M = 10 count.
- Primary: mean over gaps of the best Jaccard among those 10.
- Beside it: recall at Jaccard 0.5 under one Hungarian assignment, decoy hit rate, and the B1 chance level.

**Statistics.** No pass/fail bar.
- Every comparison reports the delta (effect size), a 95% percentile interval and a one-sided p.
- These come from a paired bootstrap of 2,000 replicates that resamples Fail2Drive pairs, each carrying all its seeds.
- The primary comparison is against **B3-behaviour**. The comparison against the best rival, re-taken in every
  replicate, is secondary.
- Dev p values are exploratory, and every dev table states how many methods have been tried.

**Held-out confirmation.**
- At most 3 finalists are frozen, tagged and scored once on each held-out model.
- One of them is declared **primary** in the freeze tag, so the headline needs no correction for multiple
  comparisons. The other two are reported with the count stated.
- The headline test pools TransFuser++ and the third model into one bootstrap: gaps weighted equally, pairs resampled
  jointly across models. Per-model and per-gap results are always reported beside it.
- Before the freeze, the held-out pools may get more traffic seeds. Gap classification stays as measured on seeds
  101–106. Added seeds only add routes to the same units.

## 8. Amendment A2: distinct axes and the infraction rival (post hoc, 2026-11-16)

**Post hoc.** Written after 134 dev configurations had been scored on SimLingo's test pool and on H21, at Chris's
decision (2026-11-16) on two proposals from Jerry's side and ours. TransFuser++'s and UniAD's test pools are still
unread by any method. No new method is scored until this is tagged `f2d-sprint-a2`.

**Distinct axes.** Everything else in A1's scoring stands.
- A method's top 10 counts only distinct axes. An axis identical to one listed earlier is dropped before the top 10
  is taken. This applies in `sprint_score.py` to every method and rival.
- Clustering by cuts (`cache_methods.axes_from`, which B3-behaviour and most m and j methods use) lists a group once.
  A cut that does not split a group adds no axis.
- When the scheduled cuts give fewer than 10 distinct axes, the cuts continue one at a time after the last scheduled
  one (for Ward 2/3/5: 6, 7, ...) until there are 10.
- Under A1, Ward 2/3/5 repeated a group whenever a later cut left it whole, so most methods had 7 or 8 distinct axes
  in their top 10 (found by Jerry's agent).

**B3-infraction is a reported rival.**
- It groups failing routes by the infraction type they incurred, one axis per type
  (`docs/research/experiments/f2d-dev-simlingo/b3_infractions.py`).
- Every method is compared with it: delta, 95% interval and one-sided p, beside B3-behaviour and B7-pool.
- It has no pass bar and is not part of the "best rival" comparison. Nothing is required to beat it.

**Rescore.**
- Every logged method, m and j, is rescored under A2 on both dev pools: SimLingo's test pool and H21.
- A1 scores stay in `VARIANTS.md` beside the A2 scores.
- A rescore is not a new try, so the tried total does not change.

**Finalists.** No hard bar is added. Finalists are chosen after the search on the full record:
- the score on this pool;
- the H21 replication, reported as context and not used as a gate;
- stability under resampling;
- whether the method is ready to run on the held-out models.

## 9. Amendment A3: the freeze (2026-11-17)

**Status.** Written after the SimLingo search ended (188 methods tried in total on SimLingo's test pool and H21) and
before any method has read TransFuser++'s or UniAD's test-pool data. Tagged `f2d-freeze-1`. From this tag, the
finalists, rivals and transfer rules below do not change for round 1.

**Rival fix (post hoc, found by Jerry's agent).**
- `cache_pool.py` kept ego speed and step for only the first 100 frames of each route. So B3-behaviour's approach
  window ended about 10 s before the failure on over half of SimLingo's routes (`docs/WHAT_BROKE.md`, 2026-11-16).
- `cache_pool.py` now keeps every frame. B3-behaviour's features and grouping are unchanged.
- Its window is its last 6 captured frames, about 1.5 s, not "3 s" as A1 says. The 6 frames are what A1 tagged in
  code, so they stand.
- B3-behaviour is rescored on SimLingo dev with the fix and reported beside the old score. Jerry's diagnostic gave
  0.225, against 0.189 before (measured). The rescore is not a try.

**Finalists.** Two, chosen by Chris on the full dev record (A2's list):
- **m23, primary.** The L8 50-frame approach window (PCA 32, Ward) pooled with the whole-route L8 view.
  `VARIANTS.md` batch 4.
- **m40, secondary.** The L8 50-frame window at PCA 64 pooled with the whole-route L20 view. `VARIANTS.md` batch 4
  pools.

On each held-out model, the comparison against B3-behaviour is the primary test. m40 is reported with the count of
finalists (2) stated.

**Transfer.** `docs/research/experiments/f2d-dev-simlingo/transfer-spec.md` as it stands at this tag.
- It fixes the site, the layers by relative depth, the windows in frames and the per-model rivals.
- One choice was made at the freeze: B7's dictionary on a held-out model keeps SimLingo's sparsity, not its k. On
  SimLingo, k = 64 active features out of 896 is 7%; on a 256-wide model the same 7% is k = 18. TransFuser++'s
  B7-pool is therefore `L2_k18_s0`. This rule was fixed blind to every held-out score.

**Order.**
1. **TransFuser++ is scored first, alone,** once both finalists and all rivals are run on its pool. Its per-model,
   per-gap result is reported when it lands, labelled interim.
2. **UniAD** is scored when its pool and gap classification are done, with the same frozen methods.
3. The headline is A1's: one bootstrap pooled across both models. A two-model scorer for it is written and tested
   before any UniAD outcome is read.

**UniAD's rival, if fields are missing.** If UniAD's shards lack ego speed or step, B3-behaviour uses the features
that can be computed from what is logged: infraction counts, plus the route's step count from its outcome record. This
is stated beside every UniAD result. B3-behaviour stays the primary rival.

**Round 2, fixed now.**
- **Trigger:** m23's 95% interval against B3-behaviour on TransFuser++ includes zero.
- **What happens:**
  - TransFuser++ becomes a second dev pool beside SimLingo, and the search may continue on both.
  - At most 3 new finalists are frozen under a new tag before any UniAD outcome is read.
  - They are confirmed on UniAD alone.
- **Reporting:** round 1's result, on TransFuser++ and pooled with UniAD, is reported in full whatever round 2 finds.
  Both rounds are reported, with the total tried count.

## 10. Amendment A4: round 2 closed (post hoc, 2026-11-18)

Chris's decision, 2026-11-18, after 12 round-2 tries:
- **The search stops.** No round-2 finalist beat m23 on the pooled dev score (m23 0.270 against B3-behaviour 0.163,
  p 0.11), so nothing new is frozen and no further try is made in the clustering family.
- **UniAD scores round 1's frozen methods,** m23 (primary) and m40, as their second held-out model, under §9's rules.
- **Reporting:** both rounds are reported in full with the total tried count, 202 at the stop.
- This is post hoc: it is decided after round 2's dev scores were read, but before any UniAD outcome is read.

**The UniAD read is shared.** A new comparison of failure-discovery views is being pre-registered
(`docs/prereg-views.md`, after the unpooled experiment in `docs/research/experiments/f2d-unpooled/protocol.md`).
- UniAD's outcomes are read once, after that pre-registration is tagged. That one read scores m23 and m40 under §9,
  plus every pre-registered row.
- m23's UniAD number therefore waits for the tag, but is otherwise unchanged by it.
