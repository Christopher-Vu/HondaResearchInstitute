# PRD — Fail2Drive track: failure-axis discovery on a public benchmark

**Status:** parallel track, owner Chris, opened 2026-11-05. `PRD.md` stays the authority for the main study; this
document governs only the Fail2Drive track. If the track meets its bar (§8), the project migrates to it, and that
migration is recorded in `CONFLICTS.md` as an amendment to `PRD.md` §5, §9.1, §10.3 and §13.

**Public only.** Everything here is about Fail2Drive's published routes and scenarios. Nothing from `gaps/sealed/`
appears in or is used by this track.

---

## 1. One paragraph

The main study plants data gaps and seals them in an answer key. This track finds failure axes for a published
benchmark's documented failure modes instead. Fail2Drive (Gerstenecker, Geiger, Renz, IROS 2026; `PRD.md` §4.7) pairs
each of 100 routes with an in-distribution twin that differs only in one unseen scenario. Its scenario labels are a
ground truth fixed by its authors before we ran anything. We hide those labels from every method, run discovery on the
policy's activations, and score the axes against them with the main study's scoring code. The harness, methods,
baselines, output schema and metrics are unchanged.

**End result, if it works.**
1. On Fail2Drive, activation-based discovery recovers SimLingo's failure modes without labels. That includes the
   failure types that our factor list, committed before this track existed, does not name.
2. The same holds on TransFuser++, which is not a VLA (vision-language-action model). That makes the claim model-agnostic.
3. Training data we author along one discovered axis lowers that failure on Fail2Drive's held-out routes, without
   lowering Bench2Drive scores.

## 2. Why this track

- **Real failures, fixed ground truth.** The failures are documented on a published benchmark and the labels predate
  us, so the key cannot be fit to our results. The main study's 12 sealed candidates, at about 6,000 SU, gave 0
  interactional gaps passing (`STATUS.md`, 2026-11-04).
- **Measured on our harness (`results/savio/f2d-repro-screen/`, one seed, 2026-11-05).** SimLingo fails these
  scenarios much more often than on their twins.
  - PedestriansOnRoad: 4/5 against 1/5.
  - Wall: 5/5 against 0/5.
  - CustomObstacles: 9/10 against 3/10.
  - Uplift is 60–100 points and the ratio at least 3. That clears `PRD.md` §9.1's 20-point and 2× bars. Only the
    §9.1 sample size (30 or more slice runs) is short.
- **Scales across models.** Fail2Drive's labels hold for any policy. Its repo ships TransFuser++ code
  (`team_code/sensor_agent.py`) and a checkpoint (README: `huggingface.co/SimonGer/TFv5`). The paper also evaluates
  HiP-AD, Orion, PlanT2 and the Bench2DriveZoo models.

## 3. What stays and what changes

**Stays:** the adapter and harness (`adapters/simlingo/`, `simulator.benchmark: fail2drive`), activation capture, the
discovery methods (contrastive, SAE, probe residual), the baselines, the §8.3 schema, Hungarian matching on
failing-rollout Jaccard at a fixed axis budget, the §10.2 metrics, and the §9.4 closed-loop recipe.

**Changes:**

1. **Gaps.** A gap is one Fail2Drive scenario type. Its slice is the type's generalization routes, and its
   neighbourhood is their base twins (`adapters/simlingo/fail2drive_pairs.py`). Failure is the harness's existing
   label.
2. **Tiers become the B4 split.** Fail2Drive's types are mostly single factors, so the "enumeration misses it"
   argument moves from interactional gaps to this split. `configs/baselines/b4_factors_v1.yaml`, tagged
   `b4-factors-v1` on 2026-10-15 before this track existed, names some types and not others.
   - *B4-named:* the type is matched by one of B4's levels: animal, unusual_obstacle (including construction),
     pedestrian_near, hard_brake.
   - *B4-unnamed:* no level matches.
   - The assignment of each type is fixed in the pre-registration (F2), by reading the level definitions, before any
     method runs.
   - The headline compares methods on B4-unnamed recall. B4 is expected to do well on B4-named types, and that is
     reported, not hidden.
3. **Decoys.** Decoys are types that SimLingo handles. That means a slice failure rate within 5 points of its twins
   on the F1 screen, which is the `PRD.md` §9.1 decoy definition. They are visually or behaviourally novel and do not
   cause failures.
4. **Labels are hidden.** Methods and baselines see rollouts, states and activations. They never see the scenario
   type, route file name or route id.
   - B2 (`PRD.md` §9.3) is therefore restricted to observable state strata.
   - B2 run *with* the scenario label recovers each gap by construction. It is reported as an oracle ceiling, never as
     a baseline.
5. **The seal becomes a pre-registration.** The key is public, so credibility comes from these commitments, timestamped
   in git:
   - The gap and decoy selection rule, the B4 split, the metrics and the analysis are tagged `f2d-prereg-v1` before the
     test pool runs.
   - Methods are frozen and tagged before any of them reads test-pool outcomes.
   - Scoring runs once.
6. **Contamination check.** Any method or gate step that uses a language or vision model is also run once with no
   rollout data, only the prompt. Fail2Drive scenario names it produces that way are reported. An axis that matches
   such a name is flagged.
7. **Sample size.** Most types have 5 pairs. Some (Animals, BadParking, CustomObstacles) have 10.
   - Reaching §9.1's 30 slice runs takes 6 traffic seeds on 5 routes.
   - Bootstrap intervals resample routes, so per-type intervals stay wide. Every result is reported per gap.

## 4. The Fail2Drive rule and the closed loop

Fail2Drive §3.2 forbids training on its routes, scenario definitions or assets (`PRD.md` §4.7). The closed loop
(`PRD.md` §9.4) follows that rule like this:

- Take one discovered axis, preferably from a B4-unnamed type.
- Parameterize a scenario family along the axis, using our own definitions and stock CARLA assets, on Bench2Drive
  roads.
- Validate solvability with PDM-Lite (privileged rule-based expert).
- Generate expert data, then fine-tune with LoRA (low-rank adaptation) on SimLingo's recipe, vision encoder frozen.
- Evaluate on Fail2Drive's routes of that type, which stay held out. Also check other types, plus the
  no-degradation test on Bench2Drive-220.
- Controls are the same as §9.4.

"Repair transfers to a held-out benchmark" is the result. Nothing in Fail2Drive is trained on, and Step 10's
done-condition already checks that.

## 5. Steps

Each step starts as soon as the one before it allows. None waits on a calendar.

- **F0 — Bring-up. Done.** Fail2Drive runs on the harness (commits `5242137`, `8e27d9a`). The 3-type reproduction
  screen is scored (`results/savio/f2d-repro-screen/`).
- **F1 — Full screen.** The other 14 types, every pair, one seed (`configs/rollout/f2d-screen-full.yaml`, 160
  routes, about 560 SU, estimate). *Done when every type has a scored slice and neighbourhood failure rate.*
- **F2 — Pre-registration.** Selection rule, B4 split, decoy rule, test-pool design, metrics, contamination check,
  migration bar (§8). Written before F1 is read, then tagged `f2d-prereg-v1`. *Done when the tag exists.*
- **F3 — Test pool.** The selected gap and decoy types, plus every remaining type as background, with 6 traffic seeds
  and activation capture (about 1,500–2,000 SU, estimate). *Done when every route has an outcome or is listed as
  lost.*
- **F4 — Freeze and score.** All methods and baselines run on the pool under the §5.4 label rule, frozen and tagged
  first, and scored once. *Done when the scoring report exists and the tags are in order.*
- **F5 — Closed loop.** §4 on one axis. *Done when one cycle has run with the no-degradation check reported.*
- **F6 — TransFuser++.** An adapter and activation hooks for Fail2Drive's TransFuser++. Then F1, F3 and F4 on it.
  This runs alongside F2–F5. *Done when its scoring report exists.*
- **F7 — Migration decision.** Read against §8.

## 6. Compute (estimates; 3.5 SU a route measured on array 40883276)

| Step | Routes | SU |
|---|---|---|
| F0 | 40 | ~90 (spent) |
| F1 | 160 | ~560 |
| F3 | ~1,200 (100 pairs × 6 seeds, trimmed to selected types) | ~1,500–2,000 |
| F4 | CPU and short GPU | ~50 |
| F5 | data generation, LoRA and evaluation | needs its own estimate before it runs |
| F6 | F1 + F3 again on TransFuser++ (a smaller model, cheaper per route, unmeasured) | ~1,500 |

Cap: 2,500 SU for F1–F4 on SimLingo (Chris, 2026-11-05). F5 and F6 runs need a separate go. The total budget left is
unconfirmed.

## 7. Risks

- **Wide intervals with 5 routes per type.** Per-gap results are noisy, so the headline pools gaps by tier.
- **B4 beats the methods on B4-named types.** Expected. The claim rests on B4-unnamed types.
- **Too few B4-unnamed types fail.** If F1 shows fewer than 2, the track's main claim has no target. That is read at
  F2 and reported.
- **Contamination.** Bounded by §3.6. It cannot be ruled out, only measured.
- **Background failures.** SimLingo also fails some base twins (3 of 10 on CustomObstacles). Those failures are the
  natural-failure background the main study already faces.
- **TransFuser++ bring-up cost.** It is a new adapter and new hooks, and its checkpoint provenance should be checked
  against the paper's reported scores.

## 8. Migration bar

The bar is fixed here, before F1 is read. The project migrates to this track if all three hold:

1. At least 2 B4-unnamed types pass `PRD.md` §9.1 on the test pool.
2. The best activation method's mean best Jaccard on B4-unnamed types beats every non-oracle baseline's by at least
   0.15, with a 95% route-bootstrap interval that excludes zero. This mirrors `PRD.md` §13.1.
3. No step used Fail2Drive data for training.

Otherwise, the track is reported as a measured comparison on a public benchmark, alongside the main study.
