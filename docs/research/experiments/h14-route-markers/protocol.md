# H14: how much the route markers change SimLingo's driving

**Draft, not locked. Nothing has run and no SU has been spent. Jerry and Chris approve before anything is submitted, and the protocol locks only then.** Dev only (PRD §9.2).

Every number below is tagged: measured, simulated, estimate, read from the code, or guess. None of the margins or predictions is a result.

## Why

`adapters/simlingo/route_run.py:165` passes `--debug 2` to the evaluator, so route points are drawn into the world and the policy camera films them (`docs/WHAT_BROKE.md`, 2026-11-03). The evaluator's default is 0. Their effect on driving is unmeasured, and they sit in every SimLingo route and every captured activation.

The flag is older than the WHAT_BROKE entry says. `cb474a7` (2026-10-02) added it and `a134c93` only moved it. The first complete Mac run I could find, 2026-10-02 16:09, shows the same dot (`results/local-mac/20261002-160934/frames/000180.png`, by eye), so I found no marker-free SimLingo run to compare against.

SimLingo's own launchers do not draw them (read from the pinned source). `start_eval_simlingo.py` passes no `--debug`, and `collect_dataset_slurm.py:28` passes `--debug=0`. So the training images probably have no markers and the published scores probably ran without them. That the published runs used these launchers is inferred, not verified.

## What the flag changes

Read from the code, not tested. All paths are under `.runtime/simlingo/Bench2Drive/leaderboard/leaderboard/`.

| Level | Effect | Where |
|---|---|---|
| Above 0 | Draws every 10th route point, the start and the end for the whole route. Each scenario adds a red trigger point and its name as it is built. | `scenarios/route_scenario.py:93-94`, `241-269`, `330-338` |
| Above 1 | Recomputes route statistics and rewrites `live.txt` every tick. | `scenarios/scenario_manager.py:205-220` |
| Above 2 | Prints the behaviour tree every tick. We never ran this. | `scenarios/scenario_manager.py:222-225` |

- Point colour follows the road option: green for lane follow, yellow for left, cyan for right, grey for straight. So a marker shows the route's next move, and the red point shows where a scenario triggers.
- `--debug 1` still draws. Only 0 removes the markers.
- The agent receives the flag (`leaderboard_evaluator.py:368`), and neither `AutonomousAgent` nor `LingoAgent` uses it. Drawing uses no random numbers. So the flag reaches the car only through the camera.
- The dot ahead in `results/local-ui-check/frames/000180.png` covers about 40 of 524,288 pixels and sits on the road in the car's lane (measured, one frame).

## Main test: paired routes

**Arms.** `--debug 2`, as in every earlier run, against `--debug 0`. Everything else copies `configs/rollout/step2-bench2drive220.yaml`: seed 0, chain-of-thought off, Epic quality and `capture_every: 10` with no token layers. Both arms use `timeout_seconds: 600`, because 60 lost one Step 2 route's setup. Each route has its own CARLA server (`scripts/route_sample.sbatch`), so markers cannot carry from one arm to the other.

**Same seed does not mean same drive.** Closed loop does not reproduce (`docs/WHAT_BROKE.md`, 2026-10-06). A pair controls for how hard the road is and leaves repeat-run noise in the data. That noise adds discordant pairs evenly to both sides, so it costs power without biasing McNemar's test.

**Pool.** The 213 Bench2Drive-220 routes whose scenario ran in Step 2. All were driven at `--debug 2` by Step 2, and the rerun has a 212-route set. Left out because Step 2 skipped their scenario: 23700, 23901, 23910, 23918, 23930, 24078, 24098.

**Draw.** No outcome enters it, and the seed is the hypothesis number.

```python
import random, yaml
routes = yaml.safe_load(open("configs/rollout/step2-bench2drive220.yaml"))["routes"]
skipped = {"23700", "23901", "23910", "23918", "23930", "24078", "24098"}
draw = sorted((str(r) for r in routes if str(r) not in skipped), key=int)
random.Random(14).shuffle(draw)
```

**Stages.** Stage 1 is the first 80 ids. Stage 2 is the other 133 and needs its own approval.

```text
25358 2664 26418 2082 24092 3144 28093 25424 3670 3708 25955 28229 24294 2201 18252 17655
28243 24330 24258 26405 26393 1773 1852 3378 27532 3813 11715 24841 25968 3800 28241 28330
14194 3572 23659 2204 27506 4669 2715 18311 20920 24252 17563 3564 24071 3184 2084 4183
2606 3876 23708 2943 26435 25845 28035 23670 28111 2115 2129 2086 2143 28198 24340 25857
28210 25928 2373 10857 3697 2127 3666 26458 28087 2643 3255 3476 1711 1792 2709 3712
```

**Run layout.**

- Use two arrays, one per arm, with `ROUTE_IDS` in the draw's order, so task *i* holds the same routes in both.
- Submit both together from one commit, with the same throttle, at 3 routes per A40, excluding n0214 and n0215.
- Run CARLA from the same disk in both arms. Node-local disk opened its port in 4 s against 127 s from scratch (measured, same node), but no launcher supports it yet.
- Start only after the P20 arrays finish, because array tasks read the checkout when each task starts.

**Pairs.** A pair counts when both arms have a driving outcome and the scenario ran. Lost routes rerun from the scorer's `rerun` list, decided before any outcome is read, and the scorer keeps the first attempt with an outcome. If a route has no outcome after two reruns, its pair is dropped, and in Stage 1 the next id in the draw replaces it. Drops are counted by arm. If over 10% of pairs drop, the verdict is Unresolved.

**Checks, before any outcome is read.**

1. Each `readiness.json` names its arm, and `live.txt` exists only at `--debug 2`.
2. Someone views 20 seeded saved frames per arm. One marker in the `--debug 0` arm voids the run, and so does a `--debug 2` arm with none.
3. The guard check below passes.

**Bridge, read with the outcomes.** The new `--debug 2` arm against Step 2 on the same routes costs nothing. A McNemar p under 0.05 means the pipeline has drifted since 2026-10-08. H14's verdict would then hold for today's pipeline and carry to earlier runs only with that caveat.

## Effect rule

Differences are `--debug 0` minus `--debug 2`, and both directions count.

| Metric | Per route | Test | 90% interval | Margin | Why this margin |
|---|---|---|---|---|---|
| Success | The scorer's `success` | Exact McNemar | Agresti-Min | ±8 points | Step 2's 72.7 minus the published 64.84 is 7.9. A change this size could explain that whole gap. |
| Any collision | `collisions_vehicle`, `collisions_pedestrian` or `collisions_layout` in `infractions` | Exact McNemar | Agresti-Min | ±8 points | 42 of 213 Step 2 routes collided (19.7%, measured), so 8 points is a change of about two-fifths. |
| Route completion | `score_route` | Sign-flip, 10,000 flips, seed 14 | Route bootstrap, 10,000 draws, seed 14 | ±3 points | Step 2 averages 99.15, with 207 of 213 complete (measured). 3 points would triple the shortfall. |

**Threshold.** Holm across the three metrics at 0.005 after Stage 1 and at 0.045 at the final read, so the two looks together stay under 0.05. If Stage 2 is not approved, the final read uses the 80 pairs at 0.045.

| Holm test | 90% interval | Verdict for that metric |
|---|---|---|
| Passes | Reaches past the margin | **Real effect** |
| Passes | Inside the margin | **Real, smaller than the margin** |
| Fails | Inside the margin | **No effect as large as the margin** |
| Fails | Reaches past the margin | **Unresolved** |

The overall verdict is Real effect if any metric reaches it, else Unresolved if any metric is unresolved, else Real and smaller if any metric is, else No effect as large as the margin. A stop at Stage 1 ends the run as Real effect, and its size is overstated because only a large early estimate can stop it.

**Reported, never part of the verdict.** Driving score against the 4.2-point gap to the published 84.41. Success by ability. The success interval from a bootstrap over the 44 scenario families. Arm by node. Wall seconds per step by arm. Nothing is sliced after the fact to rescue a verdict.

## Sample size

**Repeat-run noise** is the share of routes where exactly one of two runs fails. All runs are at `--debug 2`.

| Runs compared | Pairs | One run failed | Share |
|---|---|---|---|
| Step 2 against the rerun, same seed and weather, on Step 4's 40 routes | 40 | 6 | 15.0% (exact 95% interval 5.7 to 29.8) |
| Step 2 against wave 3 background, seed 10 with drawn weather and parameters | 199 | 40 | 20.1% |
| Step 2 against dev pool background, seed 1 with drawn weather and parameters | 70 | 17 | 24.3% |

The first row comes from `docs/steps/04-layer-site-ablation.md`. I counted the other two on 2026-11-04 from the local `routes.jsonl` files. Those two change more than the seed, so they bracket the true figure from above. Paired route-completion differences are almost all zero, with a standard deviation near 8 points (measured, same two comparisons).

**What the rule then does.** Simulated in `power.py`, data in `docs/research/data/h14_power.json`, with 20,000 draws for each cell. Ranges span discordance 15% to 24%. The simulation assumes one metric carries the effect, at Holm's first step, which is the conservative case. Final Real effect includes the runs that stopped early.

| True change (points) | Stops at Stage 1 | Final: Real effect | Final: No effect as large as the margin | Final: Unresolved |
|---|---|---|---|---|
| 0 | 0% | 1% | 54 to 83% | 16 to 45% |
| 5 | 0 to 1% | 11 to 16% | 18 to 26% | 57 to 71% |
| 8 | 2 to 3% | 32 to 46% | 5% | 49 to 64% |
| 10 | 3 to 6% | 49 to 65% | 1% | 33 to 50% |
| 15 | 12 to 20% | 85 to 94% | 0% | 6 to 15% |
| 20 | 28 to 42% | 98 to 100% | 0% | 0 to 2% |
| 30 | 70 to 84% | 100% | 0% | 0% |

The 90% interval's half width is 7.1 to 9.0 points at 80 pairs and 4.4 to 5.5 at 213.

- **213 pairs** is the whole pool, and even so the "no effect" verdict is only likely, at 54 to 83%, when the true change is zero. More pairs would need a second seed on the same roads, which doubles the cost and adds no new road.
- **80 pairs** puts the half width near the margin. Stage 1 can catch a very large change and it proves the pipeline. It cannot show that the markers are harmless.
- **A change under about 8 points will usually not be called real.** The second verdict row is unreachable for success and collisions at this size (simulated, 0% in every cell), because a passing test needs an estimate of at least about 6.5 points and the interval then reaches past 8.

## Offline option

Replay saved frames with the markers present and painted out, then compare the policy's outputs frame by frame. This costs far less than the pairs, and it answers a smaller question.

**Data.** The Step 2 rerun's `capture/inputs/*.pt` (every 10th step) and `frames/*.png` (every 20th) on the first 40 ids of the draw. Whether they survive on Chris's scratch is unchecked.

**Mask.** Colour alone fails. A threshold on `results/local-ui-check/frames/000180.png` finds the two real green dots and also four green traffic lights and parts of a yellow car (measured, one frame). The rule therefore needs a marker colour, a place below the horizon and a small blob on low-saturation surroundings. Grey straight-road points cannot be told from the road by colour. They stay in the painted frame, so the test understates the effect near those points. Check first: on 50 seeded frames viewed by eye, the mask must catch at least 90% of visible coloured dots and touch no traffic light or vehicle. If it fails, the offline work stops.

**Paint.** Inpaint the PNG with `cv2.inpaint`, on the mask grown by 2 pixels, before the agent's own JPEG step (`team_code/agent_simlingo.py:377-379`). Then run the agent's preprocessing, taking the non-image inputs from the saved `.pt`. The unpainted PNG must reproduce the saved `pixel_values` exactly. Frames that do not are dropped, and over 5% dropped stops the work.

**Placebo.** Each painted frame also gets the same mask shape on empty road at a seeded spot, which measures what painting does alone.

**Measure.** Replay in bfloat16, the dtype the rollouts logged. Report route-waypoint and speed-waypoint shift against the intact frame, as in Step 4 Part B, and the shift in layer 10's driving-query mean. Give the median and 90th percentile with a route-level bootstrap, for painted and placebo frames and by marker colour.

**Reading, fixed now.** Take the painted median minus the placebo median, on route waypoints, against Step 4's measured scale.

| Excess | Reading |
|---|---|
| Under 2 cm | No sign per frame. This clears nothing. |
| 2 to 7 cm | The size of removing one middle layer. Removing driving queries at layer 11 or layer 1 gave 11 and 14 failures of 40 against 9 intact, neither significant. |
| Over 7 cm | Larger than any middle layer. Run Stage 1 first. For scale, the vision bridge gives 21 cm, and all tokens at layer 0 gives 93 cm with 31 of 40 failing. |

**What it can show.** Whether the markers move the plan on the frame the policy saw, which colours and distances matter, and how far the markers shift activations. No driving verdict can reach that last one.

**What it cannot show.**

- It says nothing about success, collisions, completion or PRD 10.1.
- It misses anything that builds up over a drive, and every frame comes from a drive that had markers.
- Open-loop size does not order small closed-loop effects. Step 4's smallest open-loop effect, layer 1, did slightly worse in closed loop than layer 11 (measured).
- A painted frame is not a frame rendered without markers, because JPEG, inpainting and render state all differ.

So it sets priority and cannot replace the pairs.

## SilenceGuard at `--debug 0`

The guard needs no change (read from the code; not yet run at 0 with the policy).

- `run_evaluator` calls `guard.heard()` on every stdout line (`route_run.py:332-333`).
- The step line comes from our agent, not from the flag. `visible_agent.py:103-104` prints `SimLingo step N` on every `run_step`, and `CaptureAgent` calls through it (`capture_agent.py:85`).
- The leaderboard prints per tick only above 2 (`scenario_manager.py:222`), a level we never ran, so moving from 2 to 0 removes no line the guard hears.
- `SlowGuard` reads `controls.jsonl`, which the agent writes whatever the flag.

Going to 0 changes three smaller things.

- The traceback after `Skipping scenario` disappears. The line itself stays, so `summarize`'s check at `route_run.py:360` still fires, and `Ignoring scenario` is also unconditional.
- `live.txt` is no longer written, and nothing in the repo reads it.
- Per-tick statistics stop, so steps may run slightly faster. That is why wall seconds are reported by arm.

**Check.** In both arms, each route's count of `SimLingo step` lines must equal its rows in `controls.jsonl`, and guard stops are reported by arm. The expert already runs at `--debug 0` under the same `run_evaluator` (`run_savio.py:208`), but it prints its own lines, so that proves nothing for the policy.

**Code needed after approval, not written now.** `evaluator_command` reads `config["simulator"].get("debug", 2)`, with one test that the value reaches the command, plus two configs and the analysis, which is written before any outcome is read. The new key changes only the new configs' hashes.

## Cost (estimates)

Rates, all measured:

| Run | SU per route | Conditions |
|---|---|---|
| Step 2 | 4.1 (910 for 220) | Same routes and capture setting, 2 per A40, before the per-step PNG fix |
| Step 4 Part C | 5.3 (658 for about 125) | Same pool, 2 per A40 |
| H6 | 2.6 (52.6 for 20) | Other routes, 2 per A40, after the PNG fix |

P19's 8.5 does not apply. Its routes average 172.5 simulated seconds against 42.5 here (measured), and it captured tokens.

| Piece | Routes | SU at 4.1 | SU at 2.6 to 5.3 |
|---|---|---|---|
| Offline: one A40, 1-hour limit at 29 SU/h | 0 | at most 29 | at most 29 |
| Stage 1 | 160 | 660 | 420 to 850 |
| Stage 2 | 266 | 1,090 | 690 to 1,410 |
| All | 426 | 1,780 | 1,140 to 2,290 |

About 4,830 of 10,000 SU remain (re-measure before locking). Stage 1 takes about 14% of that and everything about 37%. Step 8's worked blind pool, about 6,200 SU, already exceeds what is left, so approving Stage 2 is also a decision about that pool.

The `--debug 0` arm is half the spend. Once both stages have run, it is also a one-seed Step 2 at the default setting with activations captured. Disk is about 210 to 430 GB on scratch, at the 0.5 to 1 GB per route seen on the Mac.

**Proposed order, for Jerry and Chris to change.** Offline first, then Stage 1, then Stage 2 only if the case for it holds.

## What each outcome means

**Under every verdict:**

- Past results stay as measured and are labelled "with markers".
- H14 tests nominal routes, so it does not test markers under a camera fault. A patch can hide markers in one arm only (P4, P11, P20), and frozen or delayed frames show old ones (P7, P8).
- A driving verdict does not clear the activations. The layer choice, the dictionaries, H3 and H12 all read frames with markers, and an axis could be tracking a marker's colour or the trigger point (unmeasured). Only the offline layer-10 shift speaks to this.
- PRD 10.1 asks for three seeds. H14 gives one at `--debug 0`, so it supports no reproduction claim.

| Verdict | Earlier driving numbers | PRD 10.1: Step 2's DS 88.60 and SR 72.7 against published 84.41 ± 1.76 and 64.84 ± 2.42 | Gaps and new runs |
|---|---|---|---|
| **Real effect** | Absolute rates describe SimLingo with markers, not default SimLingo. Say so wherever they are quoted. | The comparison no longer holds. If markers help, some or all of the 7.9-point excess is an artefact. If they hurt, the default does better still. The `--debug 0` arm replaces Step 2 as the one-seed figure once Stage 2 has run, and the DS 75 bar is rechecked on it. Below 75 means debugging. | PRD 9.1 passes (P4, P7, P8, P19) need reconfirming at `--debug 0` before they count, at about 680 to 860 SU per full pilot, so Jerry and Chris choose which. Recapture activations before any blind pool. |
| **Real, smaller than the margin** | Absolute rates carry the measured shift. | Markers cannot explain the whole gap, and the rest stays open. | Gaps stand with the label. C35 sets the setting for new pools. |
| **No effect as large as the margin** | Numbers stand with the label and the measured interval. This does not show the markers have no effect. | Markers cannot explain the whole gap. One seed against three and other differences stay open, with no cause claimed. | Gaps stand with the label. Activations stay open until the offline measure reads. |
| **Unresolved** | No claim either way. The effect is known only as far as the interval reaches. | The comparison stays in doubt, as WHAT_BROKE says. | Nothing is reconfirmed on this evidence. More spending is Jerry and Chris's decision. |

## Before locking

1. Chris has not been told. Jerry and Chris read this, and approve or change the margins and the stages.
2. Read Step 2 against the rerun on all 212 routes from Chris's scratch (read only, 0 SU) and rerun `power.py` with that discordance. The 6 of 40 figure is too loose to size on.
3. Confirm the rerun's `frames/` and `capture/inputs/` still exist.
4. Review CONFLICTS C35.

## Predictions (guesses)

Offline excess under 2 cm 35%, 2 to 7 cm 40%, over 7 cm 25%. Stage 1 stops about 5% of the time. If Stage 2 runs: No effect as large as the margin 50%, Unresolved 30%, Real effect 20%.
