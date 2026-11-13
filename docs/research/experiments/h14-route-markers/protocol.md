# H14: how much the route markers change SimLingo's driving

**Locked in two parts on 2026-11-04. No replay or rollout has run.** The offline test stopped at its mask check on 2026-11-04 at 0 SU. Stage 1 waits for Chris's decision on H14 (Christopher-Vu/HondaResearchInstitute#8), and Stage 2 needs its own approval from Jerry and Chris. If Chris changes anything in the paired test, the change is recorded here before any pair is driven. Dev only (PRD §9.2).

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

- Point colour follows the road option: green for lane follow, yellow for left, cyan for right, grey (64, 64, 64) for straight, and a double-size grey (128, 128, 128) for the route end. So a marker shows the route's next move, and the red point shows where a scenario triggers. The grey points should be the opaque near-white blocks on saved frames (Offline test, Mask); that link is inferred and no frame shows which draw call made a block.
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
- Both arms run CARLA and the policy's Python from node-local disk, through `CARLA_LOCAL_TAR` and `POLICY_VENV_LOCAL_TAR` in `scripts/route_sample.sbatch`. CARLA's port opened in 4 s from node-local disk against 127 s from scratch, and a scratch metadata lookup took 20 ms (measured, same node). Each array task unpacks its own copy, so disk speed cannot line up with an arm.
- Start only after the P20 arrays finish, because array tasks read the checkout when each task starts.

**Pairs.** A pair counts when both arms have a driving outcome and the scenario ran, which means no `Skipping scenario` or `Ignoring scenario` line in the evaluator's log. Lost routes rerun from the scorer's `rerun` list, decided before any outcome is read, and the scorer keeps the first attempt with an outcome. If a route has no outcome after two reruns, or its scenario did not run in either arm, or it fails check 1's `readiness.json` test or check 3 below, its pair is dropped, and in Stage 1 the next id in the draw replaces it. Drops are counted by arm. If over 10% of pairs drop, the verdict is Unresolved.

**Checks, before any outcome is read.**

1. Each `readiness.json` names its arm, and `live.txt` exists only at `--debug 2`. A wrong `debug_level` or `live.txt` state in any route voids the whole run, because it points to a mis-submitted arm. A route with no `readiness.json` loses only its pair: `route_run.summarize` writes that file after further checks, so one lost route or a job killed at that moment leaves a driving status without it.
2. Someone views 20 seeded saved frames per arm. One marker in the `--debug 0` arm voids the run, and so does a `--debug 2` arm with none.
3. The guard check below passes. A route that fails it loses only its pair. Step lines equalled control rows on 27 of 27 local routes (measured), so this should be rare.

These rules are fixed now, so a failed route needs no decision after the data exists. `analyze.py checks` runs them and prints no outcome. It reads only the scorer's `rerun`, `not_run` and `scenario_skipped` lists and the route folders, and it hashes the scored files without opening their rows. It also lists the routes still to run and the 20 seeded frames per arm. The person viewing them writes `results/savio/h14-read/frames-viewed.json` with `debug0_frames_with_marker`, `debug2_frames_with_marker`, `frames_viewed_per_arm` (at least 20) and `target_pairs` (the current target, because the seeded frames change with the route set). `analyze.py read` refuses until `checks` has passed for the same number of pairs and on the same scored files.

**Bridge, read with the outcomes.** The new `--debug 2` arm against Step 2 on the same routes costs nothing. A McNemar p under 0.05, on success or on any collision, means the pipeline has drifted since 2026-10-08. H14's verdict would then hold for today's pipeline and carry to earlier runs only with that caveat.

## Effect rule

Differences are `--debug 0` minus `--debug 2`, and both directions count.

| Metric | Per route | Test | 90% interval | Margin | Why this margin |
|---|---|---|---|---|---|
| Success | The scorer's `success` | Exact McNemar | Agresti-Min | ±8 points | Step 2's 72.7 minus the published 64.84 is 7.9. A change this size could explain that whole gap. |
| Any collision | `collisions_vehicle`, `collisions_pedestrian` or `collisions_layout` in `infractions` | Exact McNemar | Agresti-Min | ±8 points | 42 of 213 Step 2 routes collided (19.7%, measured), so 8 points is a change of about two-fifths. |
| Route completion | `score_route` | Sign-flip, 10,000 flips, seed 14 | Route bootstrap, 10,000 draws, seed 14 | ±3 points | Step 2 averages 99.15, with 207 of 213 complete (measured). 3 points would triple the shortfall. |

**Threshold.** Holm across the three metrics at 0.005 after Stage 1 and at 0.045 at the final read, so the two looks together stay under 0.05. If Stage 2 is not approved, the final read uses the 80 pairs at 0.045.

**Three reads are possible, and the choice between the last two is made blind.** After a Stage 1 that does not stop, `read --stage 1` shows only that it did not stop, how often the arms disagreed with no direction, and whether the pipeline drifted. Metrics, intervals and verdicts stay unwritten until Stage 2's decision is on file. A final read at 80 pairs refuses until `stage-2-decision.json` says `stage_2_approved: false`, and once made it rules out a final read at 213. Under the resampled null, false Real effect was 1.6% for the fixed two-look plan and 2.5% for reading 80 at 0.045 and then continuing (simulated, 3,000 draws). The blind rule exists so that the second figure is not reachable by choosing the path after seeing the effect.

| Holm test | 90% interval | Verdict for that metric |
|---|---|---|
| Passes | Reaches past the margin | **Real effect** |
| Passes | Inside the margin | **Real, smaller than the margin** |
| Fails | Inside the margin | **No effect as large as the margin** |
| Fails | Reaches past the margin | **Unresolved** |

An interval that touches the margin counts as reaching past it. The sign-flip p is (extreme flips + 1) / 10,001, so it is never 0, and with no route differing it is 1.

**The completion interval is discrete at 80 pairs, and the rule stays as written.** One lost route among 80 gives p 1.0 and an interval of (-3.75, 0), which reaches past the 3-point margin, so that metric and the overall verdict read Unresolved (hand check). At 213 pairs the same route gives (-1.41, 0), inside the margin. Under the resampled null at 80 pairs, completion is Unresolved 17% of the time and the overall verdict 96.8% (simulated), so skipping the test would rarely change a Stage 1 outcome. Unresolved is the honest reading of one lost route at this size, so no test is skipped. With about 2 non-zero values a percentile bootstrap is not a true 90% interval, and `routes_differing` is reported beside it.

The overall verdict is Real effect if any metric reaches it, else Unresolved if any metric is unresolved, else Real and smaller if any metric is, else No effect as large as the margin. Stage 1 stops the run only when its overall reading is Real effect, and that size is overstated because only a large early estimate can stop it. Any other Stage 1 reading gives no verdict, including a metric that passes Holm with its interval inside the margin.

**Reported, never part of the verdict.** Driving score against the 4.2-point gap to the published 84.41. Success by ability. The success interval from a bootstrap over the 44 scenario families. Arm by node. Wall seconds per step by arm. Nothing is sliced after the fact to rescue a verdict.

## Sample size

**Repeat-run noise** is the share of routes where exactly one of two runs fails. All runs are at `--debug 2`.

| Runs compared | Pairs | One run failed | Share |
|---|---|---|---|
| Step 2 against the rerun, same seed and weather, on Step 4's 40 routes | 40 | 6 | 15.0% (exact 95% interval 5.7 to 29.8) |
| Step 2 against wave 3 background, seed 10 with drawn weather and parameters | 199 | 40 | 20.1% |
| Step 2 against dev pool background, seed 1 with drawn weather and parameters | 70 | 17 | 24.3% |

The first row comes from `docs/steps/04-layer-site-ablation.md`. I counted the other two on 2026-11-04 from the local `routes.jsonl` files. Those two change more than the seed, so they bracket the true figure from above. Paired route-completion differences are almost all zero, with a standard deviation near 8 points (measured, same two comparisons).

**What the rule then does.** Simulated in `power.py`, data in `docs/research/data/h14_power.json`, with 20,000 draws for each cell. Ranges span discordance 15% to 24%. The simulation assumes one metric carries the effect, at Holm's first step, which is the conservative case for Real effect only. Final Real effect includes the runs that stopped early.

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

**The No effect column is an upper bound.** That verdict needs all three metrics inside their margins, and the table models one. Resampling 199 Step 2 against wave 3 pairs with random signs and applying the real rule at 213 pairs gave No effect 61.9% and Unresolved 36.2% (simulated, 1,000 draws), against 66.8% and 32.0% in the one-metric table at 20% discordance. Collision discordance on those pairs is 18.6% (measured), close to success's 20.1%, which is why the joint figure stays close.

**The discordance stays unmeasured on all 212 routes, and this protocol accepts that.** The Step 2 rerun's files sit on Chris's scratch, which is closed to this account, so the 6 of 40 figure stays too loose to size on: its exact interval runs from 5.7 to 29.8%. The table above is therefore a range and not a forecast. Three facts make that acceptable. First, no part of the rule reads the discordance: the margins, the thresholds and the stage sizes stay fixed, and 80 pairs comes from the cost, so a better figure could change only this table. Second, the interval's ends give a half width of 4.4 to 10.0 points at 80 pairs and 2.7 to 6.2 at 213 (arithmetic, not simulated), so the true figure could make Stage 1 more or less decisive and could not bias it. Third, Stage 1 measures the discordance on its own 80 pairs, with `--debug` as the only intended difference between arms. That reading replaces 6 of 40 for any Stage 2 decision.

- **213 pairs** is the whole pool, and even so the "no effect" verdict is only likely, at no more than 54 to 83%, when the true change is zero. More pairs would need a second seed on the same roads, which doubles the cost and adds no new road.
- **80 pairs** puts the half width near the margin. Stage 1 can catch a very large change and it proves the pipeline. It cannot show that the markers are harmless.
- **A change under about 8 points will usually not be called real.** The second verdict row is unreachable for success and collisions at this size (simulated, 0% in every cell), because at the simulated discordance a passing test needs an estimate of at least about 6.5 points and the interval then reaches past 8. Below that discordance the row is reachable: at 213 pairs, 9 against 0 gives p 0.0039, estimate 4.2 and interval (1.81, 6.56), which needs discordance near 4% (hand check).

## Offline test

Replay saved frames with the markers present and painted out, then compare the policy's outputs frame by frame. This costs far less than the pairs, and it answers a smaller question.

**Data.** The first 40 ids of a seeded draw from unplanted background array 40715498, using its `capture/inputs/*.pt` (every 10th step) and `frames/*.png` (every 20th). Those 40 ids hold about 1,350 frames (estimate, from their 1,350 simulated seconds at one frame per simulated second). Its config, `configs/rollout/step5-background-wave3.yaml`, sets no `debug_level`, so it ran at `--debug 2`. No outcome enters the draw.

```python
import json, random
ids = sorted((e["id"] for e in json.load(open("configs/rollout/step5-background-wave3.manifest.json"))), key=int)
random.Random(14).shuffle(ids)
```

```text
1486260 270960 2475960 2436760 318460 2753260 374960 2639360 2645860 367060 2537860 2433060
239060 2833060 2586560 2822960 2585760 2542460 185260 2824360 357260 393660 369760 280260 386960
2643560 1765560 1831160 177360 220460 251360 2475760 221560 2639660 493760 2481660 2821060
2595560 466960 1484260
```

A route with no frames or no inputs gives way to the next id in the draw, and the run reports each one it passed over.

This replaces the Step 2 rerun, which was the first choice because it shares H14's routes and Step 4's scale. Its files sit on Chris's scratch, which is closed to this account. So these frames have seed 10 and drawn weather and scenario parameters, and they are not the roads Stage 1 drives.

**Mask.** Colour alone fails. A threshold on `results/local-ui-check/frames/000180.png` finds the two real green dots and also four green traffic lights and parts of a yellow car (measured, one frame). The rule in `find_markers` therefore needs a marker colour, a place in the policy's crop below row 250 (the horizon is near row 256), a small compact blob and plain surroundings. Debug points ignore scene lighting, so each colour renders almost fixed: green near (0, 245, 56), cyan (172, 241, 240), yellow (244, 246, 83) and red (248, 59, 71) (measured, local frames). No local frame showed orange, dark cyan or blue, so those three colour tests are guesses. In rain a faint green halo can survive the 2-pixel growth (seen on one local frame), which understates the effect.

**White blocks.** Grey points do not look like the road. Saved frames show opaque blocks near (243, 243, 243), up to about 15x11 pixels and 69 to 140 pixels in area, often larger than the green dots beside them, which have a median of 35 pixels (measured). The rule adds a white group: all channels at least 225, a channel spread of at most 8, 30 to 400 pixels, aspect at most 1.7, fill at least 0.8, and plain surroundings. On 240 local frames with a marker it drew 41 white rings in 34 frames. By eye about 3 of the 41 sit on a crosswalk stripe or a road reflection (measured sample, and many crops come from the same few drives). Colour and shape cannot fully separate these from paint, so the viewer decides: if at least 10% of white rings miss a block, or under 90% of blocks are caught, white blocks stay unpainted, the mask check judges coloured dots alone, and the block rate in `frames_with_white_block` is a stated understatement. The summary reports white blocks as their own group either way.

A blob cut by the crop line may be flatter than its colour's limit, up to an aspect of 6, so long strips of paint there stay out. Synthetic shapes still get past the rule: a 10x10 bright yellow patch, an 8x8 green patch, a 10x10 red patch and a pale-cyan 8x8 glint on plain road. Synthetic misses, which understate the effect: 4-pixel green, 25-pixel red, 16-pixel yellow, far dots merged into a 3x30 line, and markers on grass. All 50 yellow, 30 green and 9 red crops viewed from 300 local frames looked like real markers (by eye).

I tuned the rule by eye on local Mac frames, and the check below uses frames it has not seen. Check first: `sheets` draws 50 seeded frames from the 40 routes and rings the mask on each. Coloured rings are magenta and white rings orange, and `mask-check-frames.json` lists each blob's colour, area and position. A viewer fills in `mask-check.json` with the frames viewed, the coloured dots visible, the dots caught, the frames where a coloured ring touches a traffic light or a vehicle, the white blocks visible, the white blocks caught, and the white rings that are not on a block (`sheets` fills in the rings drawn). The mask must catch at least 90% of visible dots, counting white blocks while their rule holds, and touch no traffic light or vehicle. Zero touches on 50 frames still allows about 6% of frames to be touched (rule of three, estimate). If it fails, the offline work stops, and `replay` refuses to start until the file passes.

**Paint.** Inpaint the PNG with `cv2.inpaint`, on the mask grown by 2 pixels, before the agent's own JPEG step (`team_code/agent_simlingo.py:377-379`). Then run the agent's preprocessing, taking the non-image inputs from the saved `.pt`. The unpainted PNG must reproduce the saved `pixel_values` exactly at bfloat16, the dtype the model sees, and this is checked on every frame before the model loads. So a change too small to survive bfloat16 passes: a 1-level change on one pixel did (measured), and so does an edit below the crop line, which the policy never sees. Frames that do not are dropped, and over 5% dropped stops the work. On a local Mac capture 14 of 14 frames reproduced exactly (measured, `results/local-step3/20261006-capture-26956`); Savio's frames are unchecked until the job runs.

**Placebo.** Each painted frame also gets the same mask shapes on road at seeded spots, which measures what painting does alone. Road means plain low-saturation pixels joined to the ground just ahead of the car, then closed over gaps under 21 pixels, so lane paint and crosswalk stripes count, since markers sit on them too, and a larger object stays out. A far vehicle under 21 pixels can still be covered. Each shape takes a spot within 15 rows of its marker, or within 40 rows if that band has no room, or any row below the horizon. A frame with no room for every shape is left out and counted, as is a frame with no marker.

The match is closer but not exact. On 240 local frames with a marker, 23 had no room (9.6%), marker tops had a median row of 286 (p10 264, p90 336), placebo tops had 309.5 (p10 282, p90 347), and 109 of the 217 kept frames had every shape within 15 rows (measured). Before this rule the tops were 291 and 331 (measured), and a 22-fold gap in painted against placebo pixel change is mostly the marker itself, so the placebo still samples less inpainting error than the paint does. The direction of what remains is unknown. **Frames with no room are not a random subset**, and I expect them to be more crowded (guess). `census.jsonl` records every frame, and the summary gives marker pixels and lowest marker row for replayed and no-room frames.

**Measure.** Replay in bfloat16, the dtype the rollouts logged. Report route-waypoint and speed-waypoint shift against the intact frame, as in Step 4 Part B, and the shift in layer 10's driving-query mean. Give the median and 90th percentile with a route-level bootstrap, for painted and placebo frames, by marker colour, by whether the nearest marker is under 15 m (a flat-ground estimate from its image row), by the lowest marker's row band, and for frames where every placebo shape sat within 15 rows of its marker.

**Reading, fixed now.** Take the painted median minus the placebo median, on route waypoints, against Step 4's measured scale. That scale came from nominal Step 2 rerun routes and these frames come from drawn weather, so the comparison is approximate. The reading uses all frames, and the row-band and matched-placebo groups are reported beside it as sensitivity checks that cannot change the reading.

| Excess | Reading |
|---|---|
| Under 2 cm | No sign per frame. This clears nothing. |
| 2 to 7 cm | The size of removing one middle layer. Removing driving queries at layer 11 or layer 1 gave 11 and 14 failures of 40 against 9 intact, neither significant. |
| Over 7 cm | Larger than any middle layer. Run Stage 1 first. For scale, the vision bridge gives 21 cm, and all tokens at layer 0 gives 93 cm with 31 of 40 failing. |

**What it can show.** Whether the markers move the plan on the frame the policy saw, which colours and distances matter, and how far the markers shift activations. No driving verdict can reach that last one.

**What it cannot show.**

- It says nothing about success, collisions, completion or PRD 10.1.
- It misses anything that builds up over a drive, and every frame comes from a drive that had markers.
- Its roads are not the pairs' roads, so it says nothing about any one Stage 1 route.
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

**Code.** `evaluator_command` reads `simulator.debug_level`, default 2, and refuses `simulator.debug` (committed with `tests/test_debug_level.py`). The arms are `configs/rollout/h14-debug2.yaml` and `h14-debug0.yaml`, and they differ only in name, scope and level. The analysis is `analyze.py`, with `tests/test_h14_analyze.py`, written before any outcome exists. The offline test is `adapters/simlingo/marker_replay.py`, with `tests/test_marker_replay.py`. The new key changes only the new configs' hashes.

## Cost (estimates)

Rates, all measured:

| Run | SU per route | Conditions |
|---|---|---|
| Step 2 | 4.1 (910 for 220) | Same routes and capture setting, 2 per A40, before the per-step PNG fix |
| Step 4 Part C | 5.3 (658 for about 125) | Same pool, 2 per A40 |
| H6 | 2.6 (52.6 for 20) | Other routes, 2 per A40, after the PNG fix |

P19's 8.5 does not apply. Its routes average 172.5 simulated seconds against 42.5 here (measured), and it captured tokens.

The task column below uses a different model, because H14 runs 3 routes per A40 and one array task unpacks the tars. A task lasts as long as its slowest route. Step 2's own wall times on these routes (measured, 2 per A40, before the PNG fix) then give 9.4 A40-hours per arm for Stage 1 and 10.8 for Stage 2, at 29 SU/h. Unpacking the tars adds 3 to 5 minutes per task (guess; the first task's log gives the real figure). The PNG fix should shorten this and a third route on the GPU should lengthen it, and neither is measured here. Reruns are extra.

| Piece | Routes | Array tasks | SU from task model | SU at 2.6 to 5.3 per route |
|---|---|---|---|---|
| Offline: view 50 frames on the login node | 0 | 0 | 0 | 0 |
| Offline: one A40, 1-hour limit | 0 | 1 | about 10, at most 29 | at most 29 |
| Stage 1 | 160 | 27 per arm | about 650 | 420 to 850 |
| Stage 2 | 266 | 45 per arm | about 800 | 690 to 1,410 |
| All | 426 | 144 | about 1,450 | 1,140 to 2,290 |

The offline figure assumes three forward passes on each of about 1,350 frames at 0.13 s (measured, Step 4 Part B: 8,232 s for 63,600 passes), about 9 minutes, plus the reproduction pass and the unpacking. The longest Step 2 route took 85 minutes (measured), so a 3-hour limit on route tasks leaves room for slowdown.

About 4,595 of 10,000 SU remain (measured 2026-11-04 22:49). Stage 1 takes about 14% of that and everything about 32%, or 50% at the top of the range. Step 8's worked blind pool, about 6,200 SU, already exceeds what is left, so approving Stage 2 is also a decision about that pool.

The `--debug 0` arm is half the spend. Once both stages have run, it is also a one-seed Step 2 at the default setting with activations captured. Disk is about 210 to 430 GB on scratch, at the 0.5 to 1 GB per route seen on the Mac.

**Order.** Offline stopped at its mask check. Stage 1 runs only after Chris's decision (issue 8). Stage 2 runs only with its own approval from Jerry and Chris.

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

## Submit

Run these on Savio from `/global/scratch/users/imhaohao/HondaResearchInstitute`, after `git fetch origin main && git merge --ff-only origin/main`. Confirm first that no P20 array is still running.

**Offline, stopped 2026-11-04: the mask check failed, so `replay` was not submitted.** Two independent model viewers, not a person, with two panels spot-checked by the lead, agree on 85 caught of 118 coloured dots in total (72%, limit 90%). They mark 13 and 14 of 50 frames where a ring touches a vehicle (limit 0), and 13 is the count both mark. Four of 6 white rings are off a block and 2 of 11 to 14 white blocks are caught, so white blocks stay unpainted. Missed dots are mostly far, small or yellow, and markers are often drawn over a distant car, so painting one out edits that car. Rings are drawn 6 pixels wider than the mask, so some touches overstate what the mask itself covers. The locked rule counts rings, and 72% fails alone. No effect was measured; offline is untested. A new mask needs an amendment and frames it has not seen. Data: `docs/research/data/h14_mask_check.json`. Stage 1 does not use the mask.

**Offline; the original plan.** Run the real-model path once on one route with `--limit` first, because `Replayer` and `Probe` have not run in this form. The first command runs on the login node for 0 SU. View `results/savio/h14-offline/mask-check/*.png` and fill in `mask-check.json` before the second.

```bash
.runtime/policy-venv/bin/python adapters/simlingo/marker_replay.py sheets results/savio/40715498 --output results/savio/h14-offline
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 docs/research/experiments/h14-route-markers/marker_replay.sbatch
```

**Stage 1, not cleared until Chris decides (issue 8).** 80 routes at 3 per A40 make tasks 0 to 26. Submit both arrays together from one commit.

```bash
export CARLA_LOCAL_TAR=/global/scratch/users/imhaohao/carla-server.tar POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar
export ROUTE_IDS="25358 2664 26418 2082 24092 3144 28093 25424 3670 3708 25955 28229 24294 2201 18252 17655 28243 24330 24258 26405 26393 1773 1852 3378 27532 3813 11715 24841 25968 3800 28241 28330 14194 3572 23659 2204 27506 4669 2715 18311 20920 24252 17563 3564 24071 3184 2084 4183 2606 3876 23708 2943 26435 25845 28035 23670 28111 2115 2129 2086 2143 28198 24340 25857 28210 25928 2373 10857 3697 2127 3666 26458 28087 2643 3255 3476 1711 1792 2709 3712"
bash scripts/submit.sh gpu_a40 --time=0-03:00:00 --array=0-26%6 scripts/route_sample.sbatch configs/rollout/h14-debug2.yaml 3
bash scripts/submit.sh gpu_a40 --time=0-03:00:00 --array=0-26%6 scripts/route_sample.sbatch configs/rollout/h14-debug0.yaml 3
```

**Scoring.** Run on the login node once both arrays have ended. `score_routes.py` prints scores, so its output goes to a file that stays closed until the checks pass. `DEBUG2_JOB` and `DEBUG0_JOB` are the two array ids.

```bash
.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py configs/rollout/h14-debug2.yaml results/savio/$DEBUG2_JOB > results/savio/h14-debug2-score.log
.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py configs/rollout/h14-debug0.yaml results/savio/$DEBUG0_JOB > results/savio/h14-debug0-score.log
.runtime/policy-venv/bin/python docs/research/experiments/h14-route-markers/analyze.py checks --pairs 80
```

`checks` names any route still to run under `still_to_run`. Rerun those by arm with `ROUTE_IDS="<ids>"`, `--array=0-<ceil(routes / 3) - 1>%6` and the same config, then score again with every job id for that arm listed in order. Once `still_to_run` is empty, view the frames that `checks` lists, write `frames-viewed.json`, and run `checks` again. Rescoring after that needs `checks` again. Then read Stage 1:

```bash
.runtime/policy-venv/bin/python docs/research/experiments/h14-route-markers/analyze.py read --stage 1
```

If Stage 1 does not stop, Jerry and Chris decide Stage 2 from the discordance and the cost, with no metric shown. If they do not approve it, write `{"stage_2_approved": false}` to `results/savio/h14-read/stage-2-decision.json`, and the final read then uses the same pairs:

```bash
.runtime/policy-venv/bin/python docs/research/experiments/h14-route-markers/analyze.py read --stage final --pairs 80
```

If Stage 2 is approved, its 133 ids are the rest of the `routes` list in either config, and `checks --pairs 213` and `read --stage final --pairs 213` close the run.

## Before each part runs

**Offline.**

1. Confirm that frames and `capture/inputs` exist on Savio for the 40 drawn routes of array 40715498. `sheets` reports any id it passes over, at 0 SU.
2. Run the one-route smoke test above before the full job.

**Stage 1.**

1. Chris's decision on H14 is on issue 8 (Christopher-Vu/HondaResearchInstitute#8). His answers to the sealed counts say that it follows separately, and his decisions on C34 and C35 follow with it. Send him this protocol with its margins if he has not seen them.
2. Do not wait for Step 2 against the rerun on all 212 routes. Chris's scratch is closed, and the Sample size section says why the loose 6 of 40 figure is accepted.
3. Review CONFLICTS C35, which is still a draft.

## Predictions (guesses)

Offline excess under 2 cm 35%, 2 to 7 cm 40%, over 7 cm 25%. Stage 1 stops about 5% of the time. If Stage 2 runs: No effect as large as the margin 50%, Unresolved 30%, Real effect 20%.
