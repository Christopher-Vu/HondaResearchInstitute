# H21: all of Fail2Drive on our harness

**Locked by the commit that adds it, before any route drives.** Dev only. Fail2Drive's routes are public, so none of them can enter the sealed key (`PRD.md` §9.1), and no `PRD.md` 13.1 branch can be claimed from this run (`CONFLICTS.md` C34). Jerry asked for the run on 2026-11-07. Chris was asked on issue 9 whether his 67-task array of 2026-11-05 already covers it. He had not answered, and Jerry chose to go ahead.

Every number is tagged: measured, estimate, or guess.

## Why

Every gap that has passed so far is a camera fault, and the one interactional gap that passed (P19) fails Step 5's single-factor condition. Fail2Drive (arXiv 2604.08535) is a published benchmark of 100 route pairs, where each generalization route adds one unseen scenario or object to its base twin's road. Its paper reports large SimLingo drops in several categories, and these routes have never been driven on our harness as a full set. The run does two things:

1. It measures, on our harness, which of Fail2Drive's 17 categories make SimLingo fail more than on the base twin. That shows where real gaps are that we did not plant.
2. It captures activations on all 200 routes, so a frozen-method evaluation on Fail2Drive pairs could later run without driving again. That structure was suggested on 2026-11-06 and is not decided. It needs a `CONFLICTS.md` entry first.

## What runs

| Item | Value |
|---|---|
| Config | `configs/rollout/f2d-all.yaml`, routes and manifest from `adapters/simlingo/fail2drive_pairs.py` over every name in `fail2drive_split` |
| Routes | 200: 100 generalization routes (slice) and 100 base twins (neighbourhood), in 17 categories of 5 or 10 pairs |
| Benchmark | Fail2Drive's evaluator and scenario runner at `bceb18af`, with `fail2drive-compat.patch`, on Fail2Drive's CARLA build |
| Route markers | Off (`debug_level: 0`), the benchmark's default, unlike every Step 5 pilot |
| Capture | Every 10 steps, token layers 10 and 11, as in `f2d-repro-screen.yaml` |
| Packing | 3 routes per A40, 67 tasks, at most 20 at once, with CARLA and the venv staged on node-local disk |
| Scoring | `score_routes.py` and `export_activations.py` through `scripts/step5_pilot.sbatch`, then `src/harness/efficacy.py` once per `F2D_<name>` gap |

Routes stopped before any driving outcome are rerun once by `ROUTE_IDS`. A rerun cannot replace an outcome, because the scorer keeps a route's first driving outcome.

## What is read, fixed before any result

**Pooled across all 100 pairs** (the primary reading): slice failures against neighbourhood failures, and slice-only against neighbourhood-only failures with McNemar's test.

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | Fewer than 80 pairs with an outcome in both arms | "H21 is untested: fewer than 80 Fail2Drive pairs drove in both arms." |
| `reproduces` | Slice-only exceeds neighbourhood-only, with McNemar p below 0.01 | "On our harness, SimLingo fails Fail2Drive's generalization routes more often than their base twins." |
| `not_reproduced` | Otherwise | "On our harness, SimLingo's failures on Fail2Drive's generalization routes are not shown to exceed those on their base twins." |

**Per category:** each `F2D_<name>` gap's paired counts, failure rates, uplift and McNemar p, from `efficacy.py`. With 5 or 10 pairs per category, these are screens and not PRD 9.1 verdicts. A category counts as a candidate gap only if it has at least 3 excess slice-only failures, which is the screen rule used for P10 to P20. No category is called a gap from this run alone.

Reported beside the readings, with no bearing on them: infractions per arm; collisions against timeouts; driving score per arm; routes lost and rerun; and a comparison with the paper's per-category results, where the paper states them.

## What this cannot show

- These routes differ from Fail2Drive's own runs in packing and node, and our harness has a measured slow-disk history (`docs/WHAT_BROKE.md`). A mismatch with the paper may come from the harness.
- A reproduced drop shows a gap exists for SimLingo. It does not show that our methods can find it.
- Fail2Drive forbids training on these routes. Nothing here trains on them.

## Cost

About 700 SU (estimate). Chris's one measured pair drove in 14 minutes on one A40, about 3.5 SU a route. 200 routes at 3.5 SU is 700 SU, and reruns add more. Spend before this run is 5453 of Jerry's 10000 SU (measured).

## Predictions (guesses)

`reproduces`, 75%. `not_reproduced`, 15%. `untested`, 10%. At least 3 categories reach 3 excess slice-only failures, 60%.
