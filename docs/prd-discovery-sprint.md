# PRD — Discovery sprint: a fast, honest eval loop and a method that wins on held-out models

**Status:** draft, owner Chris, 2026-11-14. Governs one sprint (about 7 days) on the Fail2Drive track.
`docs/prd-fail2drive.md` and `docs/prereg-fail2drive.md` remain the base; where this file departs from them, the
departure is recorded as a dated, **post hoc** amendment in `docs/prereg-fail2drive.md` and as a new entry in
`CONFLICTS.md`. Nothing here touches `gaps/sealed/`.

**Why now.** Chris's research-talk round (date unknown, at least 7 days away) will be mainly about this work. The
talk needs (1) a discovery result on held-out models, and (2) evidence that the path from a working harness to a
working discovery method takes real engineering, which our logs already document.

---

## 1. Goal

Find a failure-discovery method that recovers Fail2Drive's failure groups from a driving policy's internals, without
labels, better than the honest rivals, and show that it does so **on models it was not tuned on**.

What counts as done:
1. 10 to 15 methods tried on SimLingo (dev), every one logged.
2. The finalists (1 to 3), frozen, scored once on TransFuser++ and, if it is ready, on a third model.
3. A results table and a list of engineering lessons ready for the talk.

**Out of scope for this sprint:** the closed repair loop (F5). Discovery comes first: its axes are what a repair
loop would start from, and a real team would collect data along the axes, not generate it. F5 can run later on
whichever axis wins.

## 2. What we are measuring, stated plainly

The eval measures **recovery of known failure groups** (Fail2Drive's scenario types, hidden from every method), as a
proxy for finding unknown ones. That proxy is fair and standard (the literature review finds no published method
tested this way on a driving policy), but the talk must say it out loud.

Data per model: the 1,200-route test pool (100 pairs × 6 seeds, 101–106) with activations and logged state.
Gaps, per the pre-registered classification (measured, all B4-unnamed):

| Model | Role | Gaps |
|---|---|---|
| SimLingo (VLA) | dev, iterate freely | PedestriansOnRoad, FullyBlocked, BadParking |
| TransFuser++ (camera + LiDAR) | held out, scored once | FullyBlocked, PedestriansOnRoad |
| UniAD or VAD (modular, camera only) | held out, stretch | measured by the pre-registered rule once its pool is driven |

Wall stays a ceiling control and CustomObstacles stays background, as now.

**Note on independence.** TransFuser++'s gaps are the same two types as two of SimLingo's. So it tests whether a
method carries across **models**, not across failure types. The third model is the only pool that no method has
seen at all, which is why it is worth the effort.

## 3. Rivals

| Rival | Role | Change from now |
|---|---|---|
| B1 random, matched sizes | chance floor | none |
| **B3-behaviour** | the main rival | **new.** See §3.1 |
| B4 enumerated factors | the committed factor list | none |
| B7 and B7-pool | activation statistics, no rollouts | none |
| H25 caption-then-cluster | strongest earlier non-activation method | run under the new scoring rule if frames exist (§5) |
| B2 with labels | oracle ceiling only | never a rival: a route field names the type (1.000 on PedestriansOnRoad) |

**Full B3 is retired** as a rival and not reported. It reads the simulator's exact distances to nearby objects,
which no deployed robot has.

### 3.1 B3-behaviour

Built from signals a real fleet logs: the ego car's speed, acceleration, braking and steering over the last 3 s
before the route ends, and the infraction types it incurred. **Excluded:** distances to objects, any field of the
scenario or route config, and action error against the PDM-Lite expert (also privileged: a fleet has no expert
running beside the car).

The features, clustering and settings are written into the amendment and tagged **before any new method is scored**,
so the target cannot drift. If the agent thinks expert action error belongs in, it raises that with Chris before the
tag rather than after.

For context only: H24's speed-only mixture scored 0.343 against full B3's 0.471 on H21's pool, so most of B3's lead
likely came from the distances. That was a different method, so it does not predict B3-behaviour's score.

## 4. Scoring and statistics (the amendment)

These rules replace the current dev scoring for this sprint. They are tagged with B3-behaviour, before the loop starts.

1. **No picking the best axis with the key.** Each method ranks its own axes. The score uses its top M = 10, in its
   own order:
   - **primary:** mean over gaps of the best Jaccard among its top 10 axes, with Hungarian matching as now;
   - **beside it:** recall at Jaccard 0.5 within the top 10, and decoy hit rate.
   v1 and v2 used key-chosen best axes, so they are rescored under this rule before comparison.
2. **No pass/fail bar.** Every method is logged with its score and a one-sided p value for beating **each** rival
   and the best rival, from a route bootstrap (`src/harness/bootstrap.py`, Fail2Drive pairs resampled jointly
   across seeds, the "best" choices re-made in each replicate).
3. **Dev p values are exploratory.** Every SimLingo table states how many methods have been tried so far. A method
   that looks significant on dev after 15 tries is a candidate, not a result.
4. **The held-out score is the result.** The finalists (at most 3, chosen on SimLingo) are frozen and tagged, then
   scored once on TransFuser++ and once on the third model. Those p values, with the number of finalists stated, are
   what the talk reports. No method reads either held-out pool's outcomes before its freeze tag exists.
5. **Label hiding as now** (prereg §3): salted route names, the listed fields stripped. Any method that orders,
   batches or prompts by route must use the salted names, since raw route ids sort by category (the H25 leak).
6. **Contamination check as now** for any method that calls a language or vision model.

## 5. Checks before the loop starts

The agent confirms each of these and writes the answer at the top of the variant log:

1. **What is cached for each test pool:** activation shards (which sites and layers), the logged state B3-behaviour
   needs, and whether **camera frames** were saved. The caption method and any hybrid need frames. If they are
   missing, say so: re-driving to save them is a rollout cost.
2. **Route markers.** Whether the test pools were driven with `--debug 2`, which draws route and scenario trigger
   points into the world (C35, H14). If so, frames and activations may carry markers placed by scenario, which could
   leak the type to caption methods in particular. Report it and check whether marker density differs by type.
3. **TransFuser++ is still unread** by any method: no method or score has touched its activations.
4. **Fast scoring loop.** One command that takes a method, scores it on SimLingo's pool and writes a variant-log row,
   in about 30 minutes. Dictionary-based methods train 2 or 3 dictionaries for dev, and the full grid of 18 only for
   finalists (v1's 64 SU was almost all dictionary training).

## 6. The method loop

Claude proposes and implements methods; Chris reads each proposal before it is submitted. Each run adds a row to
`docs/research/experiments/f2d-dev-simlingo/VARIANTS.md` (id, date, change, job, SU, score, p values, methods tried
so far), including failures and cancelled runs.

Starting candidates, roughly most promising first (any can be dropped, others added):

- **Error-aware B7.** B7 already leads B3 on FullyBlocked (0.458 vs 0.188) and BadParking (0.269 vs 0.188) under the
  old scoring. Let the failure label shape the grouping, as Domino, FACTS and InfEmbed do.
- **Approach-window activations.** Activations from the seconds before the failure, instead of route averages.
- **Hybrid:** activations plus frame captions (if frames exist). Activations found the camera patch; captions found
  Fail2Drive's inserted objects. Each input wins where it carries the answer.
- **H24 variants:** the activation mixture with better features or other layers.
- **Layer and site sweep** for the best method so far.
- **Image-embedding grouping of frames** (B5, Domino's original form), as a check on whether the policy's internals
  add anything over any image embedding.

**Not in the headline:** contrasting each unseen route with its own twin. Real robot data has no twins. It may be
logged as a diagnostic.

Budget: 10 to 15 methods in 5 days, about 30 minutes of compute each plus debugging.

## 7. Third model (parallel)

- The agent picks **UniAD or VAD** from Bench2DriveZoo, whichever is easier to bring up on Fail2Drive, and checks
  its checkpoint against the scores in Fail2Drive's paper.
- Work: adapter, activation hooks, then a one-seed screen. Then the full 6-seed pool if the screen works and time
  allows.
- Rollouts run on Savio whenever method jobs are not running, including overnight and weekends. Savio runs all week
  apart from scheduled maintenance; the A40 queue can be long, so submit early. A rented A100 is the fallback for
  method runs.
- Gaps on this model are classified by the pre-registered rule (prereg §1–2) on its own pool, before any method reads
  it.

## 8. Timeline

| Day | Work |
|---|---|
| 0–1 | §5 checks; B3-behaviour built; amendment and scoring rules tagged; v1 and v2 rescored; third-model bring-up starts |
| 1–5 | method loop on SimLingo; third model screened, then full pool queued |
| 5–6 | finalists frozen and tagged; scored once on TransFuser++ (and the third model if ready) |
| 6–7 | results table and talk material |

## 9. Deliverables for the talk

1. **Results table:** every method on SimLingo (dev, with the count tried), finalists on the held-out models, all
   rivals beside them, and the B2 oracle ceiling.
2. **Variant log**, complete, failures included.
3. **Engineering lessons**, each with its evidence in the repo:
   - route ids sorted by category and would have leaked the answer to a grouping agent (H25 lock review);
   - a route field let B2 score a perfect 1.000 (v1);
   - a group floor of 20 made small gaps impossible to find (H22);
   - full B3 won by reading simulator ground truth, which motivated B3-behaviour;
   - choosing the best axis with the key flatters every method, which motivated the §4 scoring;
   - route markers drawn into the world (C35), if §5.2 finds them on these pools.
4. **Framing:** a principled eval that matches what a deployed team can observe, plus a logged search over methods,
   judged on models the search never saw. That is the work Chris would do at Atoms.

## 10. Open questions for Chris

- Expert action error in B3-behaviour (§3.1): in or out? Default: out.
- If frames are missing on the test pools, is re-driving to save them worth the rollouts?
