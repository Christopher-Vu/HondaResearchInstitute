# Journal

What each agent session did and why, written for someone who was not there.
Newest entry first. Rules for writing entries are in `CLAUDE.md` under "Journal".

---

## 2026-11-07: all of Fail2Drive queued, and a proposal to build the evaluation on it

Jerry asked to run Fail2Drive on Savio. Fail2Drive is a published benchmark of 100 road pairs, where each pair is the same road with and without one situation SimLingo never saw in training. Its source code was not on Jerry's copy, so this session cloned it at the revision Chris pinned and applied Chris's compatibility patch. That gives 200 routes in 17 categories. A [locked protocol](research/experiments/h21-fail2drive-all/protocol.md) says what will be reported: whether SimLingo fails the unseen-situation routes more than their twins across all 100 pairs, and a screen for each category.

Two problems came up on the way. Packing the simulator folder into one file for fast loading ran at about 0.3 MB a second on the shared disk, so Fail2Drive's own 12.8 GB download from Hugging Face was used instead. The first download broke at 335 MB, and a resumed one finished in about 4 minutes. The GPU queue is long: Slurm puts the first task's start at about 01:15 on 2026-11-08. So one task runs first as a test, and the other 66 run only if it succeeds. Chris has not yet said whether his own array of 2026-11-05 already did this, and Jerry chose to go ahead anyway.

Separately, [CONFLICTS C38](../CONFLICTS.md) proposes building the final evaluation on Fail2Drive's pairs instead of a sealed blind pool. The current plan has not closed Step 5 on 20 public tries, and its pool costs more than the remaining budget. A review caught a serious hole in the first draft: one oversized group of failures would have won every pair. Jaccard now stays the main score, and the pair reading only counts groups that are specific to the situation. Until Chris and Jerry decide, no method reads the Fail2Drive activations.

---

## 2026-11-06: an agent channel, a refreshed dashboard, and three checks on what preprocessing does

Jerry asked for a place where his agents and Chris's agents can talk. That is now pinned issue [#9](https://github.com/Christopher-Vu/HondaResearchInstitute/issues/9), with a header and rules in its body and a pointer in `CLAUDE.md`. The repository is public, so nothing sealed goes there. The [status dashboard](https://failure-axis-status.vercel.app) was redeployed with this week's summary, P7, P8, P19 and P20, and the current spend. Its Next.js was also moved to 16.4.3, because 16.4.0 has a critical remote-code-execution advisory in `use cache`, which the dashboard uses.

Three dev experiments then asked whether H15's residualization result is real, at 48 SU in all (measured).

- **[H18](research/experiments/h18-residual-controls/protocol.md)** repeated residualization with shuffled visual features and with a variance-matched removal. Its rule says the gain on P19 needs the visual fit. But the shuffle control, which removes about the average activation and almost nothing else, already gets 44% of the gain. It also lifts the B7-pool baseline on P19 to a median Jaccard of 0.666, above our method.
- **[H19](research/experiments/h19-m2-settings/protocol.md)** asked why the probe-residual method, M2, never finds an axis. Planting a group of 25 failures with a clear decoding error did not help: no clustering setting found it. So M2's zero tells us nothing about the gaps. The first attempt planted the error on blank frames, where M2 cannot see it, and was [withdrawn](WHAT_BROKE.md) before the rerun.
- **[H20](research/experiments/h20-centring-second-pool/protocol.md)** removed only the average on a second, separate pool. It moved B7-pool on P8 by +0.149 and our method on P4 by −0.088, the same directions as before.

What it means: a preprocessing step that the PRD does not fix moves both our method's and the baseline's scores. That matters most for the comparison with B7, which decides whether the study goes on to a blind test. [CONFLICTS C37](../CONFLICTS.md) proposes what to fix before the methods are frozen, and Chris decides. All of this is dev data with public keys, and the best axis is chosen using the key.

---

## 2026-11-04: P20 fails its screen, the scoring path works, and a causal rehearsal gives a mixed answer

Three things that needed no decision from Chris were read tonight, and one stopped early. H15 and H17 cost 61 SU (a unit of cluster compute) on top of the 5344 measured after P20's drives, so spend is 5405 of 10000.

**P20** planted a camera patch that hides oncoming traffic. Its bug check held, and its rule needed at least 3 more failures in the patched arm than in the comparison arm. It got 0 against 4 on 10 road pairs, so it [fails its screen](research/research-log.md). This is not evidence that SimLingo copes without seeing oncoming traffic, because the patch covers an oncoming car only briefly. The count of public candidates is now 20.

**H15** pushed real activations (the policy's internal numbers) through the whole scoring path on a [throwaway public key](research/experiments/h15-scoring-dry-run/protocol.md), and its bug check found 0 bugs on the first run. So the code that would score a blind test has now seen real data. It is not a verdict. It also gave a new exploratory result. Before training, it removed from the policy's action-query numbers whatever the visual features predict. On P19 contrastive diffing then read best 0.689, median 0.540, against best 0.705, median 0.375 without that step (Jaccard overlap with the planted failures, measured, with the best axis chosen using the key). A list of scenario names still scores 0.857.

**H17** [removed one discovered direction](research/experiments/h17-causal-rehearsal/protocol.md) from the activations in offline replay. Removing it shifted the speed plan more than random edits of equal size (0.121 m against 0.105 m, measured). The route plan did not clear the rule, stopping at both its floor and its interval. H17 could not show that it moves the plan more on failing frames than on their clean twins (speed difference interval -0.016 to 0.016 m, measured), and its shift does not exceed the 95th percentile of other dictionary directions. This is a rehearsal on one axis and not Step 9's verdict.

**H14's offline test** did not run. Its route-marker mask caught 72% of dots against a 90% limit, and a ring drawn around a dot touched a vehicle in 13 of 50 frames, so the [protocol's stop](WHAT_BROKE.md) applied. The route-marker effect is still unmeasured.

What is left needs a person. Chris decides the pending conflicts, H14's driving stage, the preregistration and his new direction, and Jerry and Chris decide whether B7-pool's reading on P19 stops the blind pool. The [report](research/dev-report.md) stays a draft.

---

## 2026-11-04 (Chris): Fail2Drive runs on our harness; the kinematic decoy screen ran

Chris decided to keep SimLingo and change where the gaps come from. Every gap that has passed so far is a camera fault, which an out-of-distribution detector would also flag and which says little about missing training data. [Fail2Drive](https://arxiv.org/abs/2604.08535) is a published benchmark built for exactly this: 100 route pairs where only an unseen scenario or object differs. Its authors report SimLingo's largest drops in the Behavior category (-64.2%) and the Visual-lateral category (-32.2%), including PedestriansOnRoad falling from 98.50 to 19.68. We had never run its own routes. P5 and P6 were our re-implementations on Bench2Drive roads, and neither moved SimLingo.

This session made Fail2Drive's own routes run end to end. A rollout config can now name `simulator.benchmark: fail2drive`, which runs Fail2Drive's evaluator and scenario runner at a pinned revision on its own CARLA build (`adapters/simlingo/route_run.py`). Getting there took four small fixes:
- [`fail2drive-compat.patch`](../adapters/simlingo/patches/fail2drive-compat.patch) drops a `pkg_resources` version check, as SimLingo's copy of Bench2Drive already does.
- Fail2Drive's base twins, which carry no scenario, are now runnable routes.
- The agent gets an empty metric record under Fail2Drive's base agent class.
- A node-local copy of a named CARLA build can be staged, as the stock server already could.

[`fail2drive_pairs.py`](../adapters/simlingo/fail2drive_pairs.py) turns each Fail2Drive pair into one base: the generalization route is the slice and its base twin the neighbourhood, so `src/harness/efficacy.py` scores it like a planted gap. These routes stay public and never enter the sealed key, and Fail2Drive forbids training on them.

**Measured:** one pair (PedestriansOnRoad 1085 and its twin 85) drove cleanly in 14 minutes on one A40, about 3.5 SU a route. One pair says nothing about rates. Fail2Drive's evaluator places route points 200 m apart where Bench2Drive's places them 50 m apart, so the route SimLingo is given is sparser than in our pilots. These runs use `--debug 0`, the benchmark's default. The 20-pair reproduction screen ([config](../configs/rollout/f2d-repro-screen.yaml); PedestriansOnRoad, Wall, CustomObstacles) is built and has not run.

Separately, Chris's kinematic decoy screen ran and was read privately. The answer key stays sealed, so nothing about it is recorded here.

**Savio was slow:** a CARLA map load timed out after 300 s, and policies importing the venv from scratch sat idle for 20 minutes. Staging CARLA and the venv on node-local disk fixed both, so use `CARLA_LOCAL_TAR` and `POLICY_VENV_LOCAL_TAR` for every array. One launch was cancelled for this, at about 70 SU. Fail2Drive's simulator tarball (`.runtime/downloads/fail2drive_simulator.tar.gz`) can be staged directly with `CARLA_LOCAL_BUILD=fail2drive`.

---

## 2026-11-04: drafted a protocol to measure what the route markers do to driving

Every SimLingo route has run with `--debug 2`, which draws small coloured route points into the world where the policy camera can see them. Nobody knows whether that changes how the car drives. This session wrote a draft experiment to find out, [H14](research/experiments/h14-route-markers/protocol.md). It ran nothing on Savio and spent no SU. Jerry and Chris approve it before anything runs, and it stays unlocked until then.

The main test drives the same routes twice, with markers and without, and compares success, collisions and route completion. The routes come from a seeded draw of the 213 Bench2Drive routes that Step 2 already drove. A first stage of 80 pairs would cost about 660 SU and all 213 pairs about 1,750 SU (estimates, from Step 2's measured 4.1 SU per route). A simulation shows that even 213 pairs reach a "no effect as large as 8 points" verdict only 54 to 83% of the time when there is no change, so a small effect could stay unresolved. A cheaper offline check paints the markers out of saved frames and compares the policy's plan, at most 29 SU. It can set priorities, and it cannot replace driving the routes.

Reading the code settled two things and corrected a third. The step lines `SilenceGuard` listens for come from our agent and not from the flag, so the guard needs no change at `--debug 0`. SimLingo's own launchers do not draw markers, so its training images probably have none. The flag also dates from 2026-10-02 and not 2026-10-05 as [WHAT_BROKE](WHAT_BROKE.md) first said, so I found no marker-free run to compare against.

A draft [CONFLICTS C35](../CONFLICTS.md) proposes keeping `--debug 2` until H14 reads and running the blind pool at `--debug 0`, pending review. Nothing else changed. Still open: Chris has not been told, the full 212-route repeat-run comparison has not been read, and nobody has confirmed the replay data still exists on scratch.

---

## 2026-11-04: Chris's counts keep the blind test open, with no interactional gap yet

Chris answered the counts-only question ([issue 8](https://github.com/Christopher-Vu/HondaResearchInstitute/issues/8)). Of 9 sealed candidates and 3 decoys, one control and one enumerable gap passed PRD 9.1, no interactional gap did, and one visually novel decoy passed C31, at about 6,000 SU. PRD 13.1 needs two interactional gaps, so the blind test cannot run yet. Chris says more candidates are coming under a new direction and asks that the study not close at the dev-only ending.

P20's region overlaps a candidate of Chris's, which is already counted as tried and not passed. P20's screen will still be read, but no full pilot follows without Chris's say. The marker test's first stage also waits for Chris's decision, while its cheap offline part and the other dev experiments go ahead.

---

## 2026-11-04: Jerry asked for the study to be finished, so its end was defined first

An audit of every PRD step found that no step from 5 onward meets its done-condition and that the blind test has not started. Public gaps can never enter the sealed key, so nothing done on P1 to P20 can produce the PRD's go or no-go read. [CONFLICTS C34](../CONFLICTS.md) therefore defines two honest ends: a dev-only report, reachable without Chris, and the blind read, which needs Chris's sealed work and probably more compute. It also fixes the wording for each P20 result, and it was committed before P20 was read.

Jerry approved amending the screen. Three pairs that ended before their hazard were cut again past it, under new ids, and the check and the reader now refuse to answer on missing data. The six new routes were then lost to the slow shared disk, at about 37 SU (estimate), before any drive. They are running again with CARLA and Python copied to each node's own disk, which is a new way of starting routes and has not yet been shown to work at this scale.

An agent drafted [the question for Chris](research/chris-ask.md), [a sheet of pending decisions](research/conflicts-sheet.md), [the preregistration](../harness/PREREGISTRATION.md) and [report v0](research/dev-report.md), and independent reviewers corrected them. Nothing has been sent, and the preregistration binds nobody until it is signed. P19's truncation was checked: without its 8 uncertain pairs it reads 40 of 45 against 7 of 42 (exploratory), so its verdict holds.

---

## 2026-11-03: reviewing the P20 screen before reading it found route markers in the camera

The repeating start test opened CARLA's port in 120 seconds at 19:48 and started the screen by itself. A same-node test showed the shared disk is the main cause of the slow starts: CARLA's port opened in 127 seconds from the shared disk and 4 seconds from the node's own disk (measured). Six routes were stopped by the slow-simulation guard before any drive had really begun, because the guard counted loading time. They are listed for rerun and were never scored, and the guard now starts timing at the first control row.

While the screen drove, independent reviewers read the check, scoring and route code, so that any fix would come before anyone saw a result. Two findings matter most. Three of the 10 pairs end before their hazard, because the route cutter measures its 60 m tail from the trigger and ignores how far along the hazard sits. And since 2026-10-05 our evaluator has run with `--debug 2`, which draws route dots into the world that SimLingo's camera sees; I confirmed this by eye on two saved frames. Every SimLingo route shares it, and its effect on driving is unmeasured ([WHAT_BROKE](WHAT_BROKE.md)).

The check now refuses to answer on missing data, a report with no pairs reads as no result, and `route_sample.sbatch` can rerun named routes. No P20 outcome has been read. Jerry decides next whether to amend the screen as [proposed in STATUS](STATUS.md), and nothing about the markers has been changed.

---

## 2026-11-03: the compute budget rose to 10,000 units while the Savio link was down

Jerry raised the compute budget from 6,000 to 10,000 SU (service units, Savio's measure of compute used). The last measured spend was 5,033, so about 4,967 remain. This does not change P20's locked rules, because a protocol is fixed before its data exists and the only budget condition in it, that the full pilot's 680 SU are available, was already met. The note that the blind test pool needs more SU than the budget is no longer known to be true, so it now says the cost needs rechecking.

The Savio login expired before the start test could be read. Those jobs continue without the link, so the P20 screen may have started or may still be waiting. Nothing about P20 has been measured.

---

## 2026-11-03: the P20 screen was locked and submitted, and CARLA would not start

Jerry approved the screen for P20, the gap that hides oncoming traffic across five scenario families. The protocol and route files were committed before any drive ran ([protocol](research/experiments/h13-cross-family-gap/protocol.md)). The generator gained two small abilities: drawing evenly from each family, and giving each pair one weather shared by both arms.

The first attempt produced no results. CARLA, the driving simulator, normally starts in about 18 seconds, and it was not ready after 300 on any node. File operations on Savio's shared disk were slow from the compute nodes while looking normal from the login node, so slow disk lookups are the likely cause, though this is not confirmed. About 69 SU were lost, leaving about 971 of the 6,000. Details are in [WHAT_BROKE](WHAT_BROKE.md).

One retry is queued on Savio. A short test at 14:14 checks that CARLA opens its port within 150 seconds, and the screen runs only if it does. Nothing about P20 has been measured yet.

That test failed at 14:17, so the screen did not run. The scoring job ran anyway, because the way it was chained treats a cancelled job as finished. It cost about 3 SU and wrote an empty result folder. A new test (job 40831451) starts at 16:38 and repeats every 3 hours, up to 5 times, and it submits the screen itself only when CARLA starts in time. Spend is 5033 of 6000 SU.

---

## 2026-11-03: checking the last gap against the taxonomy baseline before spending on it

H12 showed that P19 is nearly the same thing as its scenario family, so a plain list of scenario names (B2) finds it. Jerry asked to check this first for the next gap, because about 1,041 compute units (SU) remain and a full pilot costs about 860. I wrote [b2_precheck.py](research/experiments/h13-cross-family-gap/b2_precheck.py), which adds simulated drives on real roads to the H12 pool and runs B2's own code. It used no compute budget and no simulator.

Three things came out. A gap inside one family cannot get under the PRD's limit of 0.4, by arithmetic, which corrects the note I wrote hours earlier that a family failing often might be enough. A gap spread evenly over four or more families can: the simulation expects 0.24 to 0.33 for the draft gap P20, a camera patch that hides oncoming traffic, and it gives 0.801 on P19 against the measured 0.857. These are simulated numbers, and the real score only exists after a pilot.

The risk has moved. The comparison drives carry a mirror-image patch, and a patch alone already fails often (P11: 4 of 10 against about 1.6 expected, measured on a small sample), which makes the required ratio of 2 hard to reach. I put the overall chance of P20 passing at about 12%, a guess. The [draft protocol](research/experiments/h13-cross-family-gap/protocol.md) is not locked and nothing was submitted; it needs Jerry's approval.

## 2026-11-03 (Jerry) — Reading H12: partial recovery of P19, and a problem with P19 itself

H12 had finished overnight on Savio without anyone reading it, so this session read it and ran the audits its protocol named. It asked whether the discovery methods find P19, oncoming traffic 1.2 m over the line on a bend, the first failure tested that is not a camera fault. In the best of 18 dictionaries (sets of features learned from activations), contrastive diffing returns 33 failing drives, 31 of them P19's, with no factor list. That is far beyond chance and beyond sorting by drive length. Most dictionaries do worse (median Jaccard 0.375, where Jaccard is shared members over combined members), and a plain list of scenario names scores 0.857.

The protocol expected the list to win. What it missed is that the PRD's Step 5 forbids any single label reaching 0.4 on an interactional gap, so P19 does not meet the definition, although yesterday's notes called it the first interactional gap. Getting under the limit would take an estimated 370 more routes of that family. So the count of qualifying gaps is back to zero, which affects the go/no-go and the NeurIPS bar. Details are in [`docs/research/research-log.md`](research/research-log.md).

No new jobs ran and nothing was spent beyond H12's 16 SU. The session stopped there because the last affordable full pilot should go on a gap that cuts across scenario families, and what P19 now counts as is for Jerry and Chris to decide.

---

## 2026-11-02 — P19 passes the full test, the first interactional gap to do so

P19 puts oncoming traffic 1.2 m over the centre line on a bend. On 55 new roads, SimLingo failed 42 of 53 drives at 1.2 m and 7 of 48 at 0.2 m (measured, dev data). The rule needs a rise of 20 points and a ratio of 2; it got 64.7 points and 5.43. On the 46 roads with both drives, 32 failed only at 1.2 m and none failed only at 0.2 m, and all 32 were vehicle collisions. The prediction was a pass at about 40%.

Nine routes were lost to simulator failures. Even if each lost route had gone against P19, it would still pass. The paired check's own floor of 60 pairs is not met, at 46.

This is one gap on practice data, so it does not meet the go/no-go, which needs two on the test pool. The value 1.2 m is also outside the 0.15 to 0.6 m in the route sets, so this may be mainly an out-of-range failure, and nobody has yet measured how failure changes with offset. The plan to stop and hand the paper choice to Jerry and Chris applied only if this pilot failed, so work continues: next is whether the methods recover P19, then one more gap, which is all the budget allows. See `docs/research/research-log.md`.

## 2026-11-02 — P19 goes to a full pilot after the expert drives it

P19 puts oncoming traffic 1.2 m over the centre line on a bend. PDM-Lite, the rule-based expert, drove the routes with no vehicle collisions on 9 of 9 (measured), so the locked rule lets the 55-pair pilot run. The expert is told the exact offset by the scenario, so this shows only that the road has room to avoid the traffic. If this pilot also fails, the plan is to stop adding candidates and bring the choice of paper to Jerry and Chris.

## 2026-11-02 — The first promising traffic gap failed its full test

P14, joining fast traffic, passed its 10-pair screen and the expert check, then failed the real test on about 60 pairs. Failure rose from 36% to 52%, which is 15.5 points where the rule needs 20, and the statistics were well short (Fisher p 0.13 against 0.01; measured). The screen had shown 78% against 33%. That gap between a screen and a pilot is the main lesson: the screen picks the luckiest of a few small tests.

Three more screens ran. P17 (a parked car cutting in later) and P18 (an emergency vehicle close behind) did not pass. P19 did: oncoming traffic crossing 1.2 m over the centre line on a bend gave 4 extra failures on 10 pairs. It deserves the same doubt as P14, and it has not yet gone through the expert check or a pilot.

Also today: Jerry asked for work to go straight to `main`, so PR 7 merged by fast-forward at 86eddfa. A commit with two failing tests went in at 4700bd3 and was fixed at 2d10e7f (`docs/WHAT_BROKE.md`). No interactional gap passes PRD 9.1 on this branch yet, after 19 candidates tried in all. See `docs/research/research-log.md`.

## 2026-11-02 — The expert driver can handle P14's fast traffic

The worry about P14 was that nobody could join a stream at 15 m/s, so its crashes would say nothing about the model. PDM-Lite, the rule-based expert that generated SimLingo's training data, drove the same routes. It collided on 1 of 9 routes with fast traffic, where SimLingo collided on 8 of 10 (measured). That passes the rule locked before the run.

It is not a clean sweep. The expert sees true positions, which a camera model cannot. It also fails the project's success label on 4 of 9, partly by waiting until a timeout. Getting the expert running took two fixes: it needs its source folder as the working directory, and only one of its routes can share a node. Details are in `docs/research/research-log.md`.

## 2026-11-02 — Joining fast traffic passes a screen, the first interactional gap to do so

H7 ran three traffic gaps on the same roads. P14, joining a stream at 15 m/s against 7 m/s, gave 5 failures only with the fast stream and 1 only with the slow one, on 9 pairs; the screen needs an excess of 3 (measured, dev data). P15 (left turns) and P16 (dense oncoming traffic) did not pass. Details: `docs/research/research-log.md`.

This does not prove a gap yet. The evidence is 9 pairs, and in several crashes the car's speed jumps at impact, so a stream vehicle probably hit it from behind. If a careful driver cannot join that stream either, the failures say nothing about the model. The next step is to run the expert driver on these routes.

## 2026-11-02 — A later walker did not break SimLingo, so the search moves to traffic

Jerry asked for a harder version of P10, and later asked to keep going until the results are NeurIPS-ready. I first measured how quickly SimLingo stops. From 10 to 12 m/s it takes 7 to 8 m. That ruled out starting the walker 1.0 s
out, because normal stops would end at the walker's path and a crash would measure physics. P13 used 1.2 s. It failed its screen: one failure only with the condition and one only without it, against the 3 extra required (measured; screen on dev data; `docs/research/data/h6_check.json`). A walker was struck once in each arm.

A count over 601 drives with nothing planted explains why: 2 of 65 walker crossings failed, against 8 of 13 signalized right turns and 8 of 11 left turns into entering traffic. H7 now varies traffic on the same roads through three new gaps, locked first in
`docs/research/experiments/h7-traffic-pressure/protocol.md`. Main was merged for Chris's speed-up. The merged evaluation no longer calls Catherine's stability check; PR 7 asks Chris about that, and about a possible overlap between these public gaps and the sealed pool.

Unfinished: H7 is running. The blind test needs Chris and more compute than the 6000 SU budget.

## 2026-11-02 — Rollouts now run almost twice as fast; one decoy rule for every decoy

On 2026-10-23 the rollout profiling (10-20 entry) was corrected. The third of each policy step that looked like
evaluator bookkeeping was actually our own viewer agent saving `last-camera.png` every step for a live window
that never runs on Savio. That save now runs only when the viewer is open (94fbbed). The earlier metric-file
change was reverted. The confirming run (job 40414722, 3 routes on one A40) measured these per-step times:
forward pass 0.15 s, model input 0.05 s, everything after the model 0.05 s (it was 0.25–0.29 s). That is about
0.28 s a step against about 0.5 s before. One of the three routes died at step 124 with no error in its log,
which is the usual CARLA crash rate (`docs/WHAT_BROKE.md`). The next rollout arrays can run 3 routes per GPU.
Four per GPU is still out: the forward pass slowed to 0.85 s.

The same day, Chris reversed part of C31 in `CONFLICTS.md` (d3733a5). Every decoy, an included gap that the
policy should handle about as well as its neighbourhood, is now judged by one rule: uplift within 10 points and
McNemar p above 0.2 on 60 pairs. The change came after a result, and the entry says so and gives the reasons.

The rest of that session's jobs finished on 10-23. Their results stay in the sealed notes. Since then nothing
has run on Savio (10-23 to 11-02). In the meantime Catherine merged a resampling stability check for the
contrastive method (#4, `src/discovery/contrastive_stability.py`, now reported by `dev_eval.py`) and a
failure-axis explorer page for the dashboard (#5, #6). Its tests pass and the sealed-import guard is clean.

## 2026-11-01 (Jerry) — three new interactional gaps miss their screens by one failure each

The project's go/no-go rule needs two interactional gaps that pass, where an interactional gap is a failure caused by how the car and
something else in the world meet, not by a broken camera alone. None had passed. The earlier two met a car starting from rest, so
the agent tried three new ones with hazards at speed or on the camera's blind side. It wrote the rules down first
(`docs/research/experiments/h5-interactional-screen/protocol.md`) and ran 10 pairs of routes for each, where each pair is the same road
with and without the planted condition.

None passed (measured). A gap needs at least 3 more failures with the condition than without it, and each reached 2: P10 (a faster walker
seen later), P11 (a walker from the blacked-out side of the camera) and P12 (walkers 60 m ahead). P11 was properly tested, and most of
its failures had nothing to do with the walker, so the black patch on either side seems to be the cause. Walkers were struck in about
1 route in 5.

The agent's own check on P10 and P12 turned out to be badly designed. It asked for a walker within 15 m of a moving car, which a car that
brakes early fails, so by the locked rule both gaps are reported as untested. Waiving the check would not change the result. Details are
in the research log at 12:15 and in `docs/WHAT_BROKE.md`. This cost 343 SU (2580 of 6000 spent). Nothing is queued: what to try next
is Jerry's decision.

## 2026-11-01 (Jerry, autoresearch) — fresh drives confirm two of the three planted faults are found

Everything found earlier was exploratory, because the method was chosen after looking at the same drives it was judged
on. So the agent wrote the rules and the expected results down first (`docs/research/experiments/h3-confirm-fresh-pilots/protocol.md`),
then ran 320 new routes on Savio: 60 pairs each of the black-patch (P4) and frozen-camera (P7) faults, and 200 ordinary
drives. Both faults broke driving again (measured: P4 78.0% failed against 15.3% on the same roads without it, P7 93.1%
against 31.7%). Four routes crashed the simulator and stayed lost, as the rules said.

The tool scored the same as before on data it had never seen (measured). Score is Jaccard: the overlap between the tool's
group and the true fault's failures, where 1 is perfect. On P4 the contrastive method reached 0.557 against 0.354 for the best
method that ignores the model's insides, and that passes both locked claims. On P7 the same method missed (0.340), as
predicted, and the "nothing changed since the last frame" signal found 48 drives, all of them truly P7 (0.889).

The agent then tried to knock its own result down. Only 3 of the 18 dictionaries reach 0.5 on P4, so 0.557 is a best case
and the typical value is 0.405. One prediction failed: a method without the "nothing changed" signal reached 0.541 on P7. The
audit showed that sorting failures by drive length alone already gets 0.48, because frozen drives stall, so that result
is treated as a stopwatch rather than a discovery. The delayed-camera fault (P8) stays unrecovered and was left out of this
test. Numbers and audits are in the research log at 09:29. The final video followed: a 130-second explainer at `video/renders/final.mp4`, with a free macOS voice, which Jerry chose to keep.

## 2026-11-01 (Jerry, autoresearch) — the discovery methods find two of the three planted faults

Jerry asked the agent to prove that our discovery tools find failures we planted on purpose in CARLA, keeping a
full log (`docs/research/research-log.md`) and ending with an explainer video. The test pool mixes 738 driving
runs: the three camera-fault pilots (P4 black patch, P7 frozen image, P8 one-second delay) and 384 ordinary runs.
Each fault is 15 to 21% of the failures, so a method that simply returns every failure scores only about 0.2.

The first, pre-registered run could not test the activation methods at all. The only sparse autoencoders (SAEs,
which split the model's internal state into a dictionary of features) had been trained on single tokens, and they
do not fit the averaged per-frame data every run has. Retrained on that data (they fit well, about 92% of the
variance), the contrastive method found the black-patch fault: a group of 31 failing runs, 27 of them P4, none of
them from the same roads without the patch (measured, Jaccard 0.574 against 0.219 for the best baseline).

The frozen and delayed faults were invisible to it, and the reason is now understood: a frozen frame is a normal
picture, only an old one. A research agent found that when the car is stopped and the image is frozen, the model's
activations repeat exactly, which never happens otherwise. Adding that "nothing changed" signal as one extra
feature, the activation-statistics method (B7) found the frozen-camera fault almost perfectly (48 runs, all P7
failures; Jaccard 0.906). The contrastive method still misses it because it only looks at the 3 seconds before a
failure, while the frozen frames come earlier in a long stall. The delayed-camera fault is still not found.

All of this is exploratory, because the methods were adjusted after seeing the data. The confirming test is
running: fresh P4 and P7 runs on Savio, judged by a pipeline written down before they finish
(`docs/research/experiments/h3-confirm-fresh-pilots/protocol.md`). Two smaller fixes: Savio's policy environment
gained scikit-learn, and the background-wave generator gained its own route-id offset so a third wave does not
reuse wave 2's ids.

---

## 2026-10-31 (Jerry) — P8, camera latency, passes its full pilot

P8 delays every camera frame by one second. On its 60-pair full pilot, every one of the 58 routes with the
delay that finished failed, against 12 of 60 on the same roads without it (measured, Fisher p about 5e-22).
Paired by road, 46 roads failed only with the delay and none failed only without it. As with P7, the paired
check reports "false" only on count: it wants 60 pairs and has 58. The two missing routes both crashed the
simulator, and on their one rerun they crashed again at the same moments, so P8 stays at 58 pairs.

One of them sits on base route 3800, which also crashed the simulator for P7 at nearly the same moment. Both
gaps change only the camera image, so this road crashes CARLA whatever we plant on it. That is logged in
`docs/WHAT_BROKE.md`.

With P4, P7 and P8, three practice gaps now pass. All three remove information from the camera. Step 5 asks
for four to six, plus two decoys.

---

## 2026-10-31 (Jerry) — P7, camera freeze, passes its full pilot

The overnight session reran the P9 screen, found it had no effect, and ran P7's 60-pair full pilot. P9's
routes with glare failed 3 of 9 times against 4 of 10 without (measured), so glare is dropped.

P7 passes. Of 56 routes with the camera freeze, 53 failed, against 15 of 60 on the same roads without it
(measured, Fisher p about 2e-15, the verdict of record). Paired by road, 40 roads failed only with the
freeze and none failed only without it. The paired check reports "false" for a count reason alone: it wants
60 pairs and we have 56, because four routes with the freeze crashed the simulator twice at the same point
and the project's rule is not to rerun a route a third time. No replacement roads were drawn, because
adding roads to the seeded draw would change which roads the other 57 pairs use. Chris and Jerry should
decide whether 56 is accepted or four replacement pairs are drawn. The lost routes all had the freeze, so
the loss makes the gap look weaker, not stronger.

P8 (camera latency) is running the same way; its scoring job runs behind it. Also logged in
`docs/WHAT_BROKE.md`: the P7 and P8 pilot configs are labelled "screen" in one field by a text-replacement
slip. Nothing reads the field.

---

## 2026-10-31 (Jerry) — P9 fails its screen; P7 and P8 full pilots submitted

The P9 traffic-light glare screen finished with the dormant-light fix in place, and the fix held: glare
code ran on 19 of 20 routes with no crash (the twentieth, route 2809933, lost its CARLA server at start, a
known failure). Over the 9 pairs that scored, routes with glare failed 3 times and routes without failed 4
times (measured), so glare does nothing detectable to SimLingo and P9 is dropped. The earlier crash had
hidden this: the first screen only had 3 scored pairs.

P7 (camera freeze) and P8 (camera latency) both passed their screens on 2026-10-23, so each now has a
60-pair full pilot config, generated the same way as P4's and on base routes that do not overlap its
screen. Savio's code was brought up to date by git bundle, P7's array was submitted, and P8's array was
chained behind it so the two do not share the four GPU slots. Each array has a scoring job after it that
writes `efficacy.json`.

Left undone: the C21 background wave. Its route generator gives every background-only route the same id
offset as wave 2, so a new wave would reuse wave 2's ids; fixing that and choosing the presets is a
decision for Chris and Jerry, so no code was written.

---

## 2026-10-30 (Jerry) — P9's glare screen rerun with the dormant-light fix

Savio came back from its 2026-10-26 maintenance in good shape: on 2026-10-28 no storage target was inactive
and a test read of 3,001 scratch files had no failures (measured), though A40 nodes were busy. Savio's code
was brought up to 8e1e873, which includes the fix from 2026-10-23 that skips sleeping ("dormant") traffic
lights. The P9 traffic-light glare screen was resubmitted in full, all 20 routes, so its gap and no-gap
routes come from the same code (array 40659402, scoring job 40659403). The crashed run's files were kept
under a `-crashed-40341126` name. This is also the first time the fix runs inside CARLA; if a gap route
still ends "Agent crashed", read its `run.log` before trusting the verdict.

---

## 2026-10-23 (Jerry) — P7 and P8 pass their screens; P9's glare crash fixed

The three screens submitted on 2026-10-21 have all finished. A screen is the 10-pair first stage of a pilot:
each pair is one route with the practice gap and one similar route without it. Measured: P7 camera freeze
had 6 routes fail only with the gap and 0 only without it; P8 camera latency had 5 against 0 over 9 pairs.
Both clear the screen rule (an excess of 3), so they are candidates for full pilots, which still need configs.

P9 traffic-light glare gave no usable result. 7 of its 10 gap routes crashed in our own glare code: on the
large Town12 and Town13 maps CARLA keeps far-away actors "dormant", and a dormant light refuses the call that
reads its size and position. `LightBoxCache` now reads a light only once it is awake (15ae746, unit-tested,
not yet run in CARLA). The P9 screen was not resubmitted; it needs Savio's checkout updated first.

Also checked: Savio scratch reads were clean today (3,000 files, 0 failures) ahead of the 2026-10-26
maintenance, and Chris's scratch is still closed to Jerry's account. The screen score files were committed
under `results/savio/step5-pilot-p{7,8,9}-screen/` (e27fac4), the first pilot results kept in git; shards
stay on Savio. Details: [`docs/WHAT_BROKE.md`](WHAT_BROKE.md) 2026-10-23.

---

## 2026-10-22 (Jerry) — A pass rule for a dev evaluation where P4 is a minority

The first dev evaluation could not tell methods apart because P4 made up 70% of its failures, so an axis of
every failure already scored 0.70. Checking Savio showed the fix needs no new rollouts: the two Step 4
background waves and the P4 pilot, already in Jerry's share folder and captured the same way, pool to 504
rollouts with 140 failures, P4 being 43 of them (31%). Chris's Step 2 shards are not readable from Jerry's
account, so they become a second tier once he grants access.

Before running anything, [`docs/steps/dev-eval-pooled.md`](steps/dev-eval-pooled.md) writes down what counts
as separation: the best activation method must beat both the best baseline and the all-failures axis (0.31)
by 0.15 Jaccard with a bootstrap interval over base routes excluding zero, without being a catch-all, and
on at least 4 of 6 SAE seeds. B3, behavioural clustering, is included because it decides the go/no-go. The
rule waits for Chris's review; no code changed and nothing ran.

---

## 2026-10-21 night (Jerry) — The stop-in-time demo's 3D view is now the driver's seat

On `/drive`, "3D street" used to watch all three lanes from 22 m behind and 12 m up. It now looks out from
the visitor's own car: left seat, 1.45 m up, the gold hood along the bottom. The pedestrian steps out from
behind the parked van in your own lane, which is what the demo is about. Braking dips the view about 2 degrees.
Your own crash shows as a red glow around the edges rather than the 3D burst, which would sit on the windscreen.
The two model lanes are 6.6 m to either side, so they are mostly out of view; their name tags float above
their roofs when they are ahead of you, and the comparison is in the result panel and the Top-down view.

Driving rounds in headless Chromium showed the ground plane, 1 cm under the road, showing through the
asphalt in about a quarter of frames from this low angle. It now sits 6 cm down; a road pixel sampled in 48
frames over four rounds was asphalt in all of them. The poster's phone picture
(`dashboard/public/poster/drive-phone.png`) still shows the old chase view until it is retaken with
`scripts/render_poster.py --phone`.

Deployed to production at 23:11 from a clean checkout of `main` at fe64b71 (Vercel deployment
`failure-axis-status-22232iz6t`), together with the poster's PowerPoint and Canva exports. Pushing `main` does
not deploy this project; each production deploy is `vercel deploy --prod` from `dashboard/`. Checked live: both
pages and both export files load, and a headless round on `/drive` drives in first person.

---

## 2026-10-21 night (Jerry) — The poster page downloads as PowerPoint and goes to Canva

The `/poster` page now has three buttons, shown on screen only. "Download PowerPoint" gives one 48 by 36 inch
slide. Its background is the poster captured at 144 dpi with the page's own text made invisible, and every
heading, paragraph and caption sits on top as an editable text box in the same place; labels drawn inside
charts stay part of the picture. 2x capture failed in Chromium, so the PDF stays the file to print. The text
boxes name IBM Plex Sans, which PowerPoint swaps for another font where it is not installed. "Download PDF for
Canva" saves the print PDF and opens Canva, where Create a design, then Import file brings it in with editable
text. "Import into Canva" does that in one step through Canva's own API. It appears only once a Canva developer
app's `CANVA_CLIENT_ID` and `CANVA_CLIENT_SECRET` are set on Vercel and the site is redeployed, with
`https://failure-axis-status.vercel.app/api/canva/callback` registered as its redirect URL and the
`design:content:write` scope; until then nothing calls Canva. The sign-in step was checked against a local
production build with placeholder keys; the import itself has not run, because there is no Canva app yet.

`scripts/render_poster.py` writes all three files into `dashboard/public/poster/exports/`; rerun it after any
poster change, since the downloads are fixed files. The "Built with" row now shows the Berkeley Research
Computing logo beside "Savio" instead of a text credit.

Later the same night, at Jerry's request, the buttons were shortened to "PowerPoint" and "Canva" (their
screen-reader names still say what downloads), and the Canva button became the one-click import once keys
exist, replacing the second button. The bar collapses to a small "Export" pill so it stops covering the
poster's top corner; the choice is remembered in the browser.

---

## 2026-10-21 late — Poster gets a results panel, a network-style pipeline and tool logos

Jerry asked for a results section, a smaller demo box, logos of the tools we used and more technical
diagrams. The top right is now "Results": the blocked-camera waffles, the paired 31-to-0 count, the layer
chart and the control check, with a line saying the repair is not measured yet. The demo moved to the
bottom left. The pipeline now draws SimLingo as a network with layer 10 lit, and the contrast step as a
plane cutting the activation cloud. A strip of the tools we used (SimLingo, Bench2Drive, CARLA, PyTorch,
Hugging Face, Savio) sits along the bottom; the three logos are the projects' own files. The `/poster` page
now scales to fit the screen, while the PDF stays full size.

One correction: the paired 31-to-0 count had been printed with the unpaired Fisher p-value (2 × 10⁻⁸). It
now carries the paired McNemar p-value from the same `efficacy.json` (9 × 10⁻¹⁰).

---

## 2026-10-21 late — The stop-in-time demo gets a 3D street

`/drive` now opens on a 3D view built with three.js through react-three-fiber
(`dashboard/src/components/drive/three/`): three lanes side by side on a city street, a chase camera behind
the visitor's car, parked vans, and pedestrians marked by a gold ground ring. It draws from the same
physics and game state as the top-down view, which stays as a switch and as the fallback when the browser
has no WebGL. The poster's phone image now shows the 3D result. Two bugs found on the way are in
`docs/WHAT_BROKE.md`; the one that mattered for the science-fair use is that slow phones under-reported
reaction times, now fixed for both views.

---

## 2026-10-21 evening — Research poster rebuilt in React, with a stop-in-time demo

The Canva poster draft was rebuilt as code: a 48 x 36 in page at `/poster` in the dashboard app
(`dashboard/src/components/poster/`), in Berkeley Blue and California Gold, with crash prevention as the
motif. The motif is the stopping-distance bar: the hero shows a top-down street where a blocked camera
centre hides a person stepping out from behind a van. Every number on the poster comes from one file,
`facts.ts`, which reads the existing result JSON and names each source. One finding shaped the copy:
on the P4 control gap, every method scores the same overlap (Jaccard 0.70), random axes included, so the
poster says the test bench works and does not claim our method wins.

The poster's QR code points to `/drive`, a phone game: hold Brake when a pedestrian appears, then compare
with "model alone" and "model + SDK" lanes. Those two lanes are illustrations with fixed reaction times
(1.2 s and 0.25 s), and the page says so; the SDK-trained result is a goal, not a measurement. Testing found
that the SDK lane could itself crash at the nearest spawn distance, so spawns now start at 23 m.

`scripts/render_poster.py` renders `poster/poster.pdf` (for print and for Canva import) and a preview,
and reports the smallest text size (24 pt) and any overflowing panel. Jerry approved a production deploy the same
evening, from a clean checkout of branch `poster-drive-demo` (not yet merged to `main`), and a scripted round
on the live `/drive` page played through. Canva import of the PDF was not tested,
because the Canva connector was not signed in. Font embedding is in `docs/WHAT_BROKE.md`.

---

## 2026-10-21 evening (Jerry) — P7, P8 and P9 screens submitted

The three camera gaps that remove information (a freezing camera, a one-second delay, white-painted
traffic lights) went to Savio, ten paired routes each, under Jerry's account. Savio's copy of the code was
92 commits behind and lacked all three gaps, so it was brought up to `main` with a git bundle, a pure
fast-forward with no jobs running. The fix for routes that hang on a left-side pedestrian crossing
(`docs/infra/left-crossing-stall.md`) was applied to the shared runtime. Savio's scratch disk has been
dropping files until its 2026-10-26 repair, so a test read of 2,000 runtime files came first; none failed.
Each screen's scoring job writes its verdict to `efficacy.json` when its routes finish. The step that
would launch a 60-pair full pilot on a pass was left out, because P7–P9 have no full-pilot configs and the
spend should be a decision. Job numbers are in `docs/STATUS.md`.

---

## 2026-10-21 evening (Jerry) — Misleading commands barely move SimLingo; PDM-Lite test blocked by disk

Two cheap checks from the IV 2026 sweep. First, whether misleading language commands could be a gap
family. SimLingo turns out to take free text only in two modes from its "action dreaming" training: one
where it obeys instructions (even "Hit the pedestrian."), one where it refuses unsafe ones; Bench2Drive's
evaluation uses neither. Replaying 88 saved frames under 15 prompts (measured, open loop) showed the channel
works for trained actions: "Stop immediately." cut the planned distance on 75% of moving frames, by up to
18 m, and a lane-change command shifted the path by about a metre. Acceleration, harmful and falsely
reassuring commands moved the plan by more than a metre on only 7 to 16% of moving frames, and the safety
mode held. So misleading commands are a weak gap family; the one lead is a false "the road is clear" claim
that added several metres of planned motion on about a fifth of stopped frames. Details and the table are in
[`docs/iv2026-literature-findings.md`](iv2026-literature-findings.md) under "Follow-up checks".

Second, whether PDM-Lite, the rule-based expert, can run with CARLA's rendering off, which would make it a
cheap guide to where failures lie. It uses no camera, only a motion sensor and the simulator's own state,
so it should. The timing run did not finish. The laptop showed sustained battery drain while plugged in, so
the replay was paused and moved to compute-box. There, free disk fell from 7.7 GB to 3 GB as another
workload downloaded data, and the guard stopped CARLA before the first route ended. The laptop has 1.5 GB
free, so nothing was started there. The scripts are kept with the replay data in
`results/command-replay-20261021/`, which is local only.

---

## 2026-10-21 (Jerry) — A sweep of IEEE IV 2026 for faster, more varied failure discovery

Jerry worried that planting one gap and checking that discovery finds it again is too narrow to show
the tool can cover a VLA's failure modes, and asked whether this year's Intelligent Vehicles Symposium
had anything that would help. All 296 abstracts were screened by four subagents; the 13 strongest were
downloaded through Berkeley's IEEE access and read in full. Findings, per-paper verdicts and proposals
are in [`docs/iv2026-literature-findings.md`](iv2026-literature-findings.md).

No paper finds failures from a policy's internals or tests a camera-only driving model closed loop, so
the method and the novelty claim stand. Every paper was weaker in full than in its abstract: the
boundary-tracing paper still needs about 300 to 550 simulations per two-parameter slice and assumes a
repeatable simulator; the "closed-loop" patch attack scores recorded frames; one headline number
(DTCCL's 48.6%) cannot be reproduced from its own table. What survives helps the Step 5 blocker, the
supply of gaps that actually make SimLingo fail: four gap families that remove or corrupt information,
and an open-loop pre-screen that replays logged frames with a candidate perturbation and only sends it
to a closed-loop pilot if SimLingo's plan moves. The pre-screen first has to separate fog (failed) from
occlusion (passed) on routes we already have. On "cover all failure modes", no paper claims that; the
ones that measure coverage do so against a declared operating domain. Nothing was built and nothing ran.

---

## 2026-10-21 (Jerry) — Three camera gaps that remove information, and a blind-spot proposal

Jerry read Kurse et al. 2025, a study of 628 California crash reports involving
self-driving cars, and asked which of its crash types would make useful gaps. Of
six practice gaps so far only P4 (a black box over the camera) passed, and it is
the only one that hides information from the policy; fog, people in the lane and
animals only changed what the scene looks like. So three new gaps all hide
information: P7 freezes the camera for 2 s of every 3 s, P8 delays every frame
by 1 s, and P9 paints each traffic light in view white so its colour is lost.
P9 is drawn from the paper's "misread signals due to glare, dirt or occlusion".
A subagent built them; they are ready to screen but have not run. Each slice
route now logs how stale its frame is (`camera_frame_age_steps`) and P9 logs
how many lights it covered, which the pre-registered manipulation checks read.

P9 only runs on the 30 Bench2Drive routes with signalized junctions, so it can
be screened but cannot reach the 60-pair full pilot without a design change.

The paper's largest crash type, being rear-ended while stopped, is not a data
gap for SimLingo: its one forward camera cannot see the car coming. It is not a
PRD decoy either, since it fails by construction. CONFLICTS.md C32 proposes it
as a third category, a blind-spot control, and notes that it would trap
contrastive diffing as well as B3. Not built; waiting on Chris.

## 2026-10-21 (Jerry) — Two prevention fixes for slow and hanging routes

Two fixes from Chris's write-up of the left-crossing stall
(`docs/infra/left-crossing-stall.md`, "Prevention"), both built by subagents and
reviewed. First, runtime setup now applies `left-crossing-walk.patch` after the
other three source patches, so a newly built runtime no longer hangs on a
left crossing; the four patches were checked to apply cleanly in order to an
unpatched SimLingo (89f3b65). A runtime built earlier, Jerry's included, still
needs the one-line command in that write-up, run on Savio. Second, the launcher
now stops a route that is still below 0.01 times real time after 10 minutes,
writes the reason to `stop-reason.json`, and the scorer lists it for rerun
instead of scoring it (cd04531). Normal routes run at 0.07 to 0.10, so the
margin is wide; the watchdog has not yet run on a live CARLA route.

Not fixable from here and left open: Savio's scratch disk (Berkeley fixes it in
the 2026-10-26 outage), CARLA's crashes on Town12 and Town13 (inside Bench2Drive's
parked-vehicle spawning), the stale dev evaluation (needs Savio and Chris's Step 2
shards), and the Step 5 gap shortage. 311 CPU tests pass.

---

## 2026-10-20 (Chris) — Where a rollout step's time goes, and a fix for the largest part

Rollouts are the project's main cost, so four short profiling jobs timed every part of a policy step
(`SIMLINGO_PROFILE`, 158859d and 1ef00c5; about 30 SU in all). Measured:

- At two routes per A40, a step takes about 0.5 s. The forward pass is 0.13 s; about 0.26 s is spent after
  the model. (This entry first blamed SimLingo's per-step `metric_info.json` write; the 2026-10-23 entry
  corrects that: the cost is our own per-step PNG save.)
- The GPU is mostly idle: 18%, 27% and 37% average use at one, two and three routes per card. At four
  routes the forward pass jumps to 0.85 s, so three per card is the packing to use.
- Our own capture code costs under 1% of a step, so it needs no work.

Savio's scratch disk began failing reads during the session (`docs/WHAT_BROKE.md`), so the confirming run
waits until it recovers. Details of each measurement are in `docs/WHAT_BROKE.md`'s 2026-10-20 entry.

---

## 2026-10-20 (Jerry) — Contrastive now fires the way B7 does, and the gap panel ships

Contrastive diffing used to call a latent "firing" whenever it went above 0.1 inside the window. B7 was corrected on
2026-10-16 to Dr. VLA's hysteresis: a latent switches on above 0.1 and stays on until it drops to exactly 0. The two
methods are compared head to head, so they now share one rule. Contrastive runs the hysteresis over the whole
rollout, so a latent that switched on before the 3 s window and stays faintly active counts as firing inside it.
The helper is `on_state` in `src/baselines/activation_stats.py`, made public for this. Any contrastive numbers from
before this change, including the inconclusive first dev evaluation, are pre-correction. A test pins the new
behaviour. 336 CPU tests pass.

The dashboard has a planted-gap panel: P4's failure rates with and without the patch, then P3, P5 and P6, which
failed. The figures match `docs/STATUS.md`. The P4 and P5 camera frames it was drawn for were never copied off
Savio, so for now those two gaps show numbers only. Chris's `poster-frames.yaml` run is the natural source for
them.

Nothing ran on Savio: no shared SSH connection was open this session.

---

## 2026-10-19 evening (Chris) — Checking which simulator objects count as obstacles and animals

Jerry flagged that the per-step actor logging might mislabel objects (`349d7ef`). Two checks were done
without a live simulator:

- **Obstacles.** Every prop name the runtime's scenario code and route files can spawn now gets the intended
  label. Debris, warning signs, barriers and cones count as obstacles. The objects that hide a crossing
  pedestrian (vending machine, container, advertisement, food cart, hay bale, bus stop) do not.
- **Animals.** The `walker.animal.` prefix matches the animal the P6 pilot spawned on Fail2Drive's
  simulator, so the prefix is right. But none of the 510 shards in Jerry's shared folders records an animal
  at any distance. None records an obstacle either, and it was not checked whether those shards were
  written before the logging was added.

The finding is written into `actor_class`'s docstring (366f36f). The rollout profiling jobs from the
previous entry were still waiting for GPUs when the session ended, so they have not been read.

---

## 2026-10-19 (Chris) — The adapter contract, a stub policy, and rollout profiling

The paper claims the method works for any driving policy, not just SimLingo (`PRD.md` §8.2). That claim
needs two things: a written contract for what a policy's adapter must hand over, and a second adapter that
meets it. Both exist now.

- **The contract** is `src/harness/shards.py` (9512f9c). One rollout is two files: a JSON sidecar
  (outcome, infractions, base route) and a numpy archive (per-step activations at one or more named sites,
  plus optional state). Every method already reads these files. The module spells out which keys are
  required, and `python -m harness.shards <dir>` checks a directory against it. SimLingo's export is held
  to it by a test.
- **The stub adapter** is `adapters/stub/stub_adapter.py` (6d79656). It is a toy road with a small numpy
  policy fitted to an expert, and it imports nothing from the rest of the repository. One gap is planted
  on purpose: fog makes pedestrians look 15 m further away, so the policy brakes late only when fog and a
  pedestrian occur together. A CPU test runs probe-residual and B3 on it end to end. Probe-residual
  recovers the planted gap at the second hidden layer (best Jaccard 0.82, measured); B3 gets 0.30. The
  result depends on the clustering setting (`min_cluster_size` 20 and 60 found nothing useful), which is
  worth knowing about the method. Testing on a second *real* policy is still Step 11.

Separately, rollouts are slow and partly idle (measured on round-3 and weekend arrays):
- the simulator runs at 0.09 of real time;
- the policy takes about 0.2 s per step, at every 20 Hz step, which is half of a route's wall time;
- tasks that run two routes side by side use only 48–68% of the GPU-slot time they pay for.

`SIMLINGO_PROFILE` (config key `profile: true`, 158859d) now splits each step's time into world-state
reading, input preparation, the forward pass, the capture hook and the simulator. `GPU_LOG=1` on
`scripts/route_sample.sbatch` samples GPU use. Three profiling jobs (one, two and three routes per GPU,
`configs/rollout/profile-rollouts.yaml`) were submitted. Their results go in the next entry.

The left-crossing patch is now applied to Chris's runtime (eb7077d).

---

## 2026-10-19 (Chris) — Failure windows end at the first infraction; the obstacle fix

These items came out of Jerry's reply to the 10-18 split. Contrastive, probe-residual and B3 each look at
a "failure window": the 3 seconds before a failing rollout went wrong. That window used to end at the
first collision, or else at the end of the route. For a red light, a stall or a lane departure, the end of
the route can be minutes after the actual failure. Now one shared rule, `src/harness/failure_time.py`,
ends the window at the first infraction of any kind (dc82169). Bench2Drive records most non-collision
infractions with a place but no time, so captures now log the car's world position each step, and
exports carry each infraction's location (00e8058). An infraction is timed at the moment the car came
closest to where it happened. Shards captured before today use stand-ins: a red light is timed when the
car drives out of the light's zone while it is red, and a stall at the start of the final standstill. A
pure timeout still uses the last 3 seconds.

Jerry's agent also found that every crossing route logged an "obstacle". The crossing scenario's blocker,
a vending machine or similar, counted as one. Only debris and construction props count now (2046f52).
Older shards can't be corrected, so their obstacle distance on crossing routes is unusable
(`docs/WHAT_BROKE.md`).

---

## 2026-10-18 (Chris) — Repeat simulator crashes, and a chase camera for figures

Some routes that crashed the CARLA server crash again at exactly the same point on a rerun. One route
died at simulation step 1384 on both attempts. The pattern: the large maps (Town12 and Town13), the car
stalled in one place, and Bench2Drive's background thread spawning parked cars just before the server
segfaults. Of the 30 crashed routes whose map is known, 24 were on those two maps (measured). Rerunning
such a route only repeats the crash, so a pilot now replaces a route that crashes twice with a seeded new
base route instead of dropping it. Dropping would bias results, because the routes that crash are mostly
ones where the car is struggling. Details are in `docs/WHAT_BROKE.md` (4d4c871).

Separately, the capture agent can now save third-person frames from a camera behind the car
(`chase_every` in a rollout config). The policy never sees this camera. The first use is
`configs/rollout/poster-frames.yaml`: two public P4 route pairs re-driven for the course poster
(e6823d9).

---

## 2026-10-15 — The dashboard and Jerry's checkout move to main

Chris merged `codex/carla-bringup` into `main` overnight and kept working
there, so the dashboard, which still read the old branch, missed his week
block. It now reads `main` by default (`dashboard/src/lib/source.ts`; Vercel
sets no `DATA_REF`), redeployed to production and checked live. Jerry's local
checkout moved to `main` by fast-forward; the old branch stays on GitHub,
merged, and nothing new goes to it.

---

## 2026-10-16 (early morning, Chris) — The layer ablation finishes: layer 10 is where failures are readable, not where driving is decided

The closed-loop part of the Step 4 ablation finished overnight. Each condition
removed one layer's contribution live while SimLingo drove 40 Bench2Drive
routes, compared route by route with an intact run.

Removing the very first layer's pass over all tokens broke driving: 31 of 40
routes failed against 9 intact. Removing layer 11's update at the driving
queries, the layer the rules recommend logging, changed nothing that 40 routes
can detect: 11 failures against 9, while two intact runs already disagree on 6
routes. With 50 resamples of the layer sweep, driving queries at layers 10 and
11 are the only stable choices.

So the logged site is right for reading failure-relevant state, but no single
middle layer is where SimLingo decides; that happens in its last four layers.
This matters for Step 9's causal checks: removing one middle-layer update will look null even
for a real axis, so causal checks should steer along the axis direction instead.
Suggestion for Jerry: capture layer 11 per token instead of 14. All numbers and
the reasoning: `docs/steps/04-layer-site-ablation.md`. About 813 SU for this
work and the left-crossing fix together, under the 1,000 set for it.

---

## 2026-10-15 (evening, Chris) — Why left crossings hang the simulator, and which layers the policy uses

Two pieces of work, with a budget of 1,000 SU.

**The stall.** A pedestrian crossing set to come from the left made routes hang
or crawl at about 1/50 of normal speed. Bench2Drive places that pedestrian by
stepping one lane left at a time until it finds a sidewalk. On a two-way road,
the lane to the left of the oncoming lane is the car's own lane again, so the
walk never ends. A probe that replays the walk without a policy found it loops
at 166 of the 220 Bench2Drive trigger points. Bench2Drive's own routes never ask
for a left crossing, which is why nobody had seen it. A 10-line patch was tested
on two public routes: they now drive normally and the pedestrian crosses. It is
not applied to the runtime everyone uses yet. Write-up:
`docs/infra/left-crossing-stall.md`.

**Which layer to log.** The Step 4 sweep picks a layer by what can be read from
it. This session asked two more questions (`docs/steps/04-layer-site-ablation.md`).
Does the pick hold on a different corpus? Yes: on the 212 nominal Step 2 rerun
routes, driving queries at layer 10 come first again (measured). Does the policy
*use* that layer? Removing each layer's own contribution, one at a time, on 848
saved frames shows the plan is set in the last four layers. Any single middle
layer, layer 10 included, moves it only a few centimetres (measured). A
closed-loop version on 40 routes per condition, and 50 resamples of the sweep,
were still running at the end of the session.

Unfinished: Part C's closed-loop scores, Part A's resamples and the final
recommendation, all chained on Savio. Probe-residual's empty result on nominal
data was traced to there being no structure to find, not a bug.

---

## 2026-10-15 (overnight, Chris) — An independent Savio bring-up, new baselines, and a Step 2 rerun that doubles as a dev corpus

Chris's agent set up the whole SimLingo runtime from scratch under his own Savio
account, to check that the bring-up is reproducible by someone who did not do
it. It is: the GPU check ran, and the Step 1 route completed at 0.078 times real
time with 9.42 GB of GPU memory, against 0.071 and 9.4 GB the first time
(measured, job 39967189). That closes the "rerun by whoever did not set it up"
check for Steps 0 and 1 in `docs/steps/progress.yaml`.

The Step 2 rerun (all 220 Bench2Drive routes) is queued as array 39967810, with
one change from the original config: it also saves layer 10 and 14 tokens
(`configs/rollout/step2-rerun.yaml`). Jerry's dev evaluation stalled because the
practice gap P4 made up 70% of the only per-token corpus; 220 nominal routes
make P4 a minority without a separate 1,600 SU background wave.

On the code side: B3, the behavioral baseline that clusters failures by what
the car visibly did before failing (`src/baselines/behavioral.py`); the
probe-residual method, which clusters failures by where a linear probe of the
world state goes wrong (`src/discovery/probe_residual.py`); the bootstrap that
decides §13.1's go/no-go comparison (`src/harness/bootstrap.py`); and the hash
commitment for the sealed answer key (`src/harness/seal.py`). Each has a spec
in `docs/steps/` listing the interpretations that still need sign-off. The B4
factor list was committed and tagged before any sealed gap was chosen
(`CONFLICTS.md` C30). Rereading the Dr. VLA paper showed its firing rule is a
hysteresis, which our B7 does not follow (C18). Capture now logs nearby
vehicles, two-wheelers, animals and obstacles each step.

Some routes ran about 50 times too slowly for hours. It looked like two bad
nodes, which were excluded, but the same split appeared on a third node with a
fast route beside each slow one, so the exclusion was reverted; the likely cause
is a scenario's actor-placement loop (`docs/WHAT_BROKE.md`).
Unfinished: the Step 2 rerun and Chris's sealed-gap screens are still queued,
and the new logging fields have not yet been checked on a real Savio route.

---

## 2026-10-15 (overnight) — The SAE and the first dev evaluation, and why it could not decide

With P4 passing, the night went to Steps 6 and 7. The animal gap P6 failed its
screen and a new job declined its full pilot on its own, so no SU went there.
The layer sweep, rerun with P4, scored practice-gap recovery for the first time
and showed that the image-heavy all-tokens site finds a perceptual gap far more
easily than the driving queries do.

The per-token sparse autoencoder from `PRD.md` §12.2 was written
(`src/discovery/sae.py`) and swept on Savio: 36 runs over layers 10 and 14,
three values of k and six seeds. Every run reconstructed held-out tokens well
(explained variance about 0.93) with no dead features, but different seeds
learned largely different dictionaries (measured).

Contrastive diffing (`src/discovery/contrastive.py`) and a runner that scores
it, B7-pool, B1 and B2 against P4 (`src/discovery/dev_eval.py`) then ran on the
only rollouts with per-token data, the Step 5 pilots. The comparison could not
decide anything: P4 makes up 70% of those rollouts' failures, so an axis that
simply holds every failure scores 0.70, and that is what contrastive diffing's
top axis turned out to be, the generic "trouble ahead" direction C27 warned
about. A cap on a latent's share of failures removes the catch-all; averaged
over six seeds the capped method still only reaches 0.70 to 0.74. C27's own
first proposal, projecting out the shared direction, turned out to be
degenerate and is corrected in `CONFLICTS.md`.

The next step is a decision, not code: a dev corpus with per-token capture in
which P4 is a minority of failures (about 1,600 SU), and more practice gaps that
take information away. Both are in `docs/STATUS.md`. Spend this round: 991 of
2,000 SU.

---

## 2026-10-13 to 15 — Per-token capture, three new gaps, and the first one that works

Jerry chose per-token capture for the SAE and three practice-gap ideas from the
previous review. Capture now stores all 30 driving-query tokens at decoder
layers 10 and 14 for every step, beside the frame means of all 24 layers. The
second layer was added after the two-wave re-sweep ranked 14 and 13 first and
10 fourth, all within two rank points, so only the site, not the layer, is
settled. Averaging the stored tokens reproduces the logged means exactly.

Each gap ran a 10-pair screen with a continuation rule fixed beforehand
(`gaps/practice/practice_v2.yaml`). **P4**, a black patch over the middle of the
camera image, passed its screen and then its 60-pair pilot: 72% of routes
failed with the patch against 20% without, and on 31 base routes only the
patched run failed while the reverse never happened (measured). It is the
first practice gap to pass PRD §9.1's rule, and it also passes C23's paired
test. **P5**, Fail2Drive's pedestrians walking in the ego lane injected into
ordinary routes, put walkers within metres of the car on every route but
SimLingo failed only 2 of 8, so the screen stopped it. **P6**, an animal
crossing on Fail2Drive's own simulator (installed on Savio, 12.78 GB, checksum
checked), runs: a zebra and a deer appear in the smoke test. Its screen was
still running at the time of writing.

Weather and pedestrians both failed to make SimLingo fail, and blinding its
camera did. That fits Fail2Drive's finding that SimLingo is robust to
appearance changes it can see through, and suggests planted gaps need to remove
information, not just change how it looks. Along the way: Savio's login dropped
several times (about every three hours), an efficacy scorer bug hid P4's first
result until fixed, and the launcher now accepts Fail2Drive's 0.9.15 patch
build. Spend this round: 828 SU of the 2,000 Jerry set.

---

## 2026-10-13 (overnight) — Step 4's stability check failed, and dense fog did not hurt SimLingo

Jerry handed the night to the agent with a 2,000 SU cap on Savio, compute-box for
CPU work, and approval to size gap pilots by `CONFLICTS.md` C23 while Chris
reviews it.

**Step 4.** The resampling stability check (drop a random fifth of the base
routes, re-run the sweep, five times) was coded into `src/discovery/layer_sweep.py`
and run on Savio. It changed the chosen layers in 4 of 5 resamples, where the
spec allows 1 (measured). Driving queries at layer 10 survived in 4 of 5; the
second pick wandered among layers 7, 9, 11 and 12. A rerun on compute-box also
showed that a different scikit-learn version alone flips the second pick
(`docs/WHAT_BROKE.md`). So, as the spec's pre-set rule says, a second wave of
200 background routes was generated and queued to start after the pilot below,
with a job that re-sweeps both waves. It started at about 06:10; cancelling
it stops the remaining tasks if the team would rather settle the tie another
way, such as logging a band of layers.

**A replacement practice gap.** P3, dense fog at noon, was chosen because no
daytime stock preset has fog above density 7 and, unlike P1's night dust, fog
is lit and reaches the camera on Savio. It was piloted as 60 pairs on 60
distinct base routes, each route run in fog and at clear noon
(`configs/rollout/step5-pilot-p3.yaml`, new generator `adapters/simlingo/pilot_routes.py`,
new scorer `src/harness/efficacy.py` reporting both PRD §9.1's rule and C23's
paired test). **It failed both** (measured): 25% failures in fog against 30% in
clear. Fog made SimLingo slower, not worse. This is the third weather
condition SimLingo shrugs off, which matches Fail2Drive's own numbers (its
"Robustness" shifts cost SimLingo 5.9%, "Behavior" shifts 64.2%). A control gap
probably has to come from behaviour or novel objects, not weather.

Two things went wrong along the way, both in `docs/WHAT_BROKE.md`: a third
faulty A40 node, n0262 (now excluded for every A40 submission through
`configs/cluster/savio.yaml`), and the pre-set image check for P3, whose
measure (pixel spread) failed on low-contrast scenes although the fog was
plainly visible. The pilot was paused by that rule and then resumed on visual
evidence, which is recorded as a deviation.

**Baselines.** B7's statistics, score and axis construction (steps 3–8 of
`docs/steps/b7-gap-signal.md`) and B2, the human-taxonomy baseline, are coded
and tested (`src/baselines/`). Both list the choices the specs left open, for
sign-off. B2 run on the dev pool ranks P1's dust slice third, as "custom"
weather. The SAE itself was not started: whether it should be per-token or on
frame means is still open (`docs/step0-trackA-findings.md`, A5 consequence 1).

**Also measured:** of 99 base routes run twice (Step 2 and the dev pool), 29
failed at least once but only 10 failed both times, so one run says little about
a route. HighwayExit and YieldToEmergencyVehicle fail almost always (7 of 7 and
6 of 7), natural axes any method will find.

---

## 2026-10-13 — Has anyone already done this? A literature sweep

The question was whether someone has already published our design, and if not,
why not. Gemini searched from seven angles, run through Google's Antigravity
command line (`agy`) because the old `gemini` command no longer logs in. Three
separate Gemini fact-checkers then tried to disprove each key claim. Every arXiv
ID it cited (41 of 41) was checked against arXiv, and the three closest papers
were read in full. Facts and sources are in `docs/step0-trackA-findings.md`
under "Literature sweep".

Nobody has published the whole design, but three papers the PRD had missed come
close and are now in `PRD.md` §4.10–4.12. SPHINX (June 2026) explains a driving
policy's decisions from its activations, has a vision-language model turn that
into adversarial scenarios, and retrains on them, in BeamNG rather than CARLA.
Motzkus and Bernhard (July 2026) train sparse autoencoders on an end-to-end
driving model, open-loop only. Gupta, Ciftci and Bansal find failure modes by
clustering a vision-language model's explanations of failure logs, never looking
inside the policy, and their targeted data cut navigation failures from 46% to
18%, against 34% for the same amount of uniform data (all as reported by those
papers). No paper was found that scores failure discovery for a closed-loop
policy against planted gaps. That part is still ours, and it is hard, which
Step 4's failed practice gaps show first-hand.

Nothing about the method was changed. Three proposals await Chris and Jerry in
`CONFLICTS.md`: C25 makes the log-based taxonomy a required baseline, C26 leads
the paper with the planted-gap harness, and C27 adds three cheap checks on dev
(a shared "trouble ahead" direction, route memorization in the SAE, and
retrospective-only separability). Three workshop papers, RiskLens among them,
were reported only by Gemini and are marked unconfirmed.

---

## 2026-10-12 — Step 4's sweep read, and a design review of the efficacy check

The Oct 9 dev pool finished long ago; this session opened the Savio connection
and read the result for the first time. The sweep (job 39784631) chose the
driving-query site at decoder layers 10 and 11. Both practice gaps failed the
efficacy check, the test that a planted gap really makes SimLingo fail more
than its matched neighbourhood: P1, the dust storm at night that Savio renders
as plain darkness, failed 7 of 30 against 5 of 29; P2, the pedestrian behind a
container, failed 2 of 30 against 0 of 30 (measured). With no passing gap, the
sweep skipped its gap-recovery metric. Step 4's done-condition only needs the
chosen layers, so it can close without new routes; Steps 6 and 7 still need a
passing practice gap.

A review of the experimental design, using the newly installed
`experimental-design` skill, then asked whether the check could have passed
anything. An exact power calculation says barely: at 30 rollouts per arm and a
15% background failure rate, a gap that truly fails 40% passes less than a
quarter of the time. The check also treats paired data (the same routes under
two conditions) as unrelated groups, and P2's 30 rollouts come from only 5 base
routes. These are proposed as `CONFLICTS.md` C23, pending Chris and Jerry. C24
proposes a check that a perceptual gap actually changes the camera image before
its efficacy is tested, which would have caught P1's invisible dust.

One finding was mechanical and is fixed: the dev pool array ran each slice in a
separate block of tasks, and so at other times and on other nodes, from its
neighbourhood. Every future array now runs routes in a seeded shuffle
(`05979cb`). Details in `docs/WHAT_BROKE.md`. Left unfinished: copying
`sweep.json` into the repo, writing the layers into the config, and the
resampling stability check.

---

## 2026-10-09 (afternoon) — The dashboard says who does what next week

The live dashboard had fallen behind: 13 commits, including Step 4's launch, had
never been pushed, and the dashboard reads everything except its fixed route grid
from GitHub. Pushing the branch caught it up. The Friday week block in
`docs/steps/progress.yaml` was rewritten, and the layer-sweep panel now says the
sweep is running against the frozen B7 rather than waiting for a draft.

The "Next week" column is now grouped by person: each item in `week.next` carries
a GitHub login in `who`, and the page shows that person's avatar and their items
together. Avatars now come straight from the login (`avatars.githubusercontent.com/<login>`)
instead of the commit feed, which had no avatar for anyone without a recent
commit. The split is Imhaohao (Jerry) on the layer sweep and the gap portfolio
size, Christopher-Vu on the B7 and C22 decisions, the Step 2 rerun and the
tarball review, and cattayw on shortlisting Step 5 gap candidates. Deployed to
production with `vercel deploy --prod` from `dashboard/`. The sweep's own result
is not on the page yet: the Savio connection was closed, so it could not be read.

---

## 2026-10-09 (night) — Step 4 unblocked and its dev pool launched

The question was what it would cost to reach Step 4 by morning. Money was never
the constraint (the whole program had used about 2,800 of 200,000 SU); three
undone pieces were. Step 4 needed practice gaps to measure recovery against, a
frozen definition of baseline B7 before anyone opened an activation, and code
for the layer sweep. This session supplied all three and started the overnight
run.

- **B7 frozen** (`docs/steps/b7-gap-signal.md`, commits `1381167`, `ceece00`).
  The earlier draft's four open questions were settled: B7 runs over a sample of
  SimLingo's training data, "B7-pool" runs the same statistics over the test
  pool without outcome labels, and either can trigger Step 6's stop condition.
  Axis members were restricted to failing rollouts, as every method's are.
  Dr. VLA's paper fixed the onset threshold to the raw activation.
- **Practice gaps chosen from Step 2's numbers.** Stock weather barely moves
  SimLingo's failure rate (night 24%, clear day 29%), so a weather gap would
  fail its efficacy check. P1 is a dust storm at night, a combination none of
  the collection presets contains. P2 is a pedestrian stepping out from behind
  a container at night, a conjunction of two factors that each leave SimLingo
  unharmed (`docs/steps/04-dev-pool-and-layer-sweep.md`, `CONFLICTS.md` C21).
- **Built, by three parallel agents and reviewed here:** a dev-route generator
  (190 routes), per-step ground-truth state and collision logging plus the
  vision bridge as a third activation site (verified on two Mac routes), an
  exporter and the layer sweep, and an efficacy gate so a practice gap is only
  scored if the policy really fails more inside it. Generating the routes found
  that a route with two weather entries silently drops a dust storm after a few
  steps (`docs/WHAT_BROKE.md`).
- **Step 3 on Savio, measured:** replay is bit-exact against itself in CUDA
  bfloat16 but 1–3 rounding steps off the live log. `CONFLICTS.md` C22 proposes
  replay-against-replay as the condition, since that is what the causal checks
  use.
- **Running:** array job 39784630 (190 routes, about 780 SU) with job 39784631
  chained to score, export and sweep. Unfinished: reading the sweep, writing
  the chosen layers into the config, the resampling stability check, and every
  sign-off listed in `docs/STATUS.md`.

## 2026-10-09 — B7 drafted, and the activations on the dashboard

The team asked to see "the activation layer analysis" on the dashboard. No such
analysis exists yet: the activations recorded on the Mac and on Savio have never
been opened, because `PRD.md` §16.9 requires baseline B7's definition to be
written first, so B7 cannot be tuned after seeing the data. The team chose to
add what does exist to the dashboard and to have B7 drafted for approval.

The dashboard's new Activations section shows where SimLingo's activations are
recorded (every layer of its 24-layer language model, on every step of all 220
Savio routes, 181,240 steps), an empty 24-layer strip that Step 4's layer sweep
will fill in, and the bfloat16 replay from compute-box: 60 frames whose plans
moved by centimetres, except two where the decision flipped.

The B7 draft is `docs/steps/b7-gap-signal.md`. Writing it exposed a
contradiction in `PRD.md` §9.3: it says B7 runs over the training data, but its
warning that B7 may be dangerously strong only holds over the test pool, since
Mode B gaps are absent from the training data. The draft recommends the
training-data version as B7 and the test-pool version as an ablation, and lists
four open questions. Also corrected: the replay summary said 58 of 60 frames
stayed within 57 cm; one of those was 57.4 cm, so it is 58 within 58 cm.

---

## 2026-10-08 (evening) — a status dashboard for the team

The team asked for one page that shows how the project is going in graphs
rather than prose, plus recent changes from each teammate in 20 words or fewer.
It is live at https://failure-axis-status.vercel.app, built as a small Next.js
app in `dashboard/` and deployed to Vercel from the laptop.

It shows the 13 steps of `PRD.md` §13 as a progress bar filled by each step's
done-conditions, Step 2's Bench2Drive scores against the paper, all 220 routes
as a grid of outcomes grouped by ability (stalls marked), and Savio spending
against the 200,000 SU allowance. Live parts are read from GitHub every 10
minutes with no token: commits from every branch, the measured blocks of the
step configs, and a new file, `docs/steps/progress.yaml`, which says which
done-conditions are met. Keep that file current alongside `docs/STATUS.md`, or
the dashboard goes stale. The route grid is a fixed copy of last night's result.

---

## 2026-10-08 (overnight, compute-box) — How far bfloat16 moves SimLingo's plans

Savio runs SimLingo in bfloat16 (a 16-bit number format) and the Mac in 32-bit
fp32, and until now only four frames had been compared. compute-box, unable to
run CARLA, spent 01:25–08:37 replaying 60 frames saved during the Mac sweep in
bfloat16 on its CPU, 5 per route across 12 routes, including the failures and
the stall routes. `replay_capture.py` gained `--dtype` and now saves after every
frame and records the waypoints it predicted (`bcba62e`, `9dcf5f0`).

Measured: path waypoints moved by a median 4.0 cm (worst 13.4 cm) and speed
waypoints by a median 8.0 cm, with 58 of 60 frames within 58 cm. Two frames
flipped the decision: near the end of routes 26956 and 25424, at about 11 m/s,
the fp32 plan keeps going and the bfloat16 plan slows sharply. Savio's own
bfloat16 drive of 26956 did brake at that point while the Mac's accelerated,
which supports the replay, though the two drives did not see identical images.
On stall frames both formats plan to stand still, and the stall routes that the
Mac and Savio both drove mostly stall on both, so stalls are a property of the
policy, not of the Mac. Numbers and caveats are in the adapter README.

Also found: compute-box's CARLA failures were never a sudden black frame. Its
renderer produces near-black images from the first frame (about 4/255 against
the laptop's 138/255), and the relaxed camera check from the Savio session
would no longer catch that, so compute-box must not be used for CARLA
(`docs/WHAT_BROKE.md`). The sweep summary files were regenerated so they no
longer count route 23918, and `docs/STATUS.md` now quotes all 44 Mac routes.
The two Mac stall repeats 17635 and 24841 remain undone.

## 2026-10-08 (overnight) — Steps 1 and 2 passed on Savio

An agent ran this session unattended through the shared SSH connection, with the
instruction to spend Savio compute only where the result is certainly useful.

**Why the 2026-10-07 attempt failed.** The CARLA library that would not load
was readable again from a login node, and the checkpoint matched its pinned hash.
The two compute nodes involved had each lost contact with the scratch
filesystem for a while, so nothing needed rebuilding (`docs/WHAT_BROKE.md`).

**Step 1 passed** (job 39732394, one A40). CARLA rendered a real street off
screen, the checkpoint strict-loaded on the node, and SimLingo drove route
26956 to completion with score 100. Measured: 0.071× real time (the Mac does
0.060×), 9.4 GB peak GPU memory for CARLA plus the policy, and 4.75 service
units (SU, Savio's billing unit) for the 9.7-minute job. These went into
`configs/rollout/step1-single-route.yaml` and the compute budget in `PRD.md`
§17.3.

**Step 2 passed: driving score (DS) 88.60, success rate (SR) 72.7%** over all
220 Bench2Drive routes, one seed, as Bench2Drive's own merge script computes
them. The bar was DS 75; the paper reports 84.41 and 64.8% over three seeds, so
one seed above it is not yet evidence of anything. Seven routes had their
scenario skipped by a Bench2Drive setup error; without them it is 88.63 and
73.7%. The run cost 31.0 GPU-hours and 910 SU, about 0.5% of the program's
allowance. Success by ability has the paper's shape: Give Way (50%) and Merging
(62.5%) weakest, Emergency Brake (85%) and Traffic Sign (86.8%) strongest. Numbers are in `configs/rollout/step2-bench2drive220.yaml` and `PRD.md`
§10.1 and §17.3.

**What it answered.** The Mac's 93% success rate came mostly from its route
sample: the same routes succeed 82.5% of the time on Savio, against 73.7%
across all routes, and the remaining Mac-versus-Savio gap is within chance
(p = 0.29). So the planned float32 run on Savio was not worth its GPU time. And
SimLingo's 40-second stalls are a property of the scenes: four stood still for
the same 40–41 s on both platforms, and 48 of 213 Savio routes stood still for
38 seconds or more (`docs/WHAT_BROKE.md`).

**How the run was kept cheap.** Instead of running the 31-route Mac comparison
and then the benchmark separately, the 220 routes (which contain those 31) ran
once, each also recording the Step 3 capture so later steps need not drive them
again. Two routes shared each A40, which cut cost per route by roughly 30%.

**What went wrong, and the fixes.** The A5000 queue was days long, so jobs moved
to A40s (`submit.sh gpu_a40`). Two A40s, in `n0214` and `n0215`, fail every job
within seconds and are now excluded. Two CARLA servers starting together
sometimes crashed one, so they now start in turn. Our own black-frame check,
written for compute-box, crashed a valid night route, because 53 of the 220
routes are at night with a camera averaging about 1/255; it now fails only flat
frames. One route's CARLA hung and held a GPU idle for an hour, so a route that
prints nothing for 15 minutes is now stopped. Eleven routes without a driving
outcome were rerun, six of them lost on `n0215`; no driving outcome was re-rolled.

Still open: the independent rerun the Step 2 done condition asks for, and the
design calls in `docs/STATUS.md`.

---

## 2026-10-08 — agent can now run commands on Savio

Until now an agent could not touch Savio, because every login needs a PIN plus a
rotating 6-digit code. This session added a `savio` entry to `~/.ssh/config` that
uses SSH connection sharing: one login opens a connection that stays alive in the
background for up to 12 idle hours, and later `ssh savio '<cmd>'` calls go through
it without asking for the code. The person still types the PIN and code. The agent
never sees them.

One surprise: while the person's own shell was open, Savio refused the agent's
command ("Session open refused by peer"). Savio apparently allows one session per
connection. After the person typed `exit`, the background connection stayed up and
the agent's command ran (measured: `hostname` returned `ln003.brc`). The steps are
in `CLAUDE.md` under "Cluster" and in `docs/STATUS.md`.

---

## 2026-10-07 (afternoon) — CARLA runs moved from the laptop to compute-box

The local sweep made the laptop too laggy to work on, so the CARLA setup was
rebuilt on compute-box, a separate M1 Pro Mac with 16 GB of memory reached over
Tailscale (described in the standardphysics project's notes). The laptop sweep
was stopped cleanly at 13:00. By then the 44-route sample was complete and
four of the six stall repeats were done; route 17635 was cut off mid-run and
left no record, so it reruns from the start.

compute-box now has the same CARLA install (identical file list, stored
compressed at 17 GB), the pinned SimLingo source, weights and Python
environment, and passed a live route start. It is about 2.8 times slower than
the laptop (0.021× real time, measured), so the last two repeats, 17635 and
24841, run there with a 120-minute cap into
`results/local-sweep/20261007-computebox-repeats/`, which records the host. A
memory guard stops CARLA before swap can freeze the box, since it also serves
production. Setbacks along the way are in `docs/WHAT_BROKE.md`.

It did not work out. After one clean test, all four real attempts at the two
routes crashed within 2 simulated seconds because CARLA handed SimLingo a black
camera frame, which never happened on the laptop. The likely cause is too
little GPU memory on the 16 GB box, but that is unconfirmed. The two routes are
still undone, so the stall-repeat set is 4 of 6. One real fix came out of it:
the sweep had been keeping Bench2Drive's score for a crashed agent, and now
leaves such routes unscored (`034fe3f`). No laptop route was affected.
A retry after freeing memory on compute-box (Docker Desktop and idle apps
stopped by the user) failed identically, so memory is not the cause and the
routes go back to the laptop.

## 2026-10-07 (morning) — Finishing the Mac sweep after the battery died

The second local night run stopped after an hour: the Mac was on battery and
went to sleep at 1% charge at 01:58 (`docs/WHAT_BROKE.md`). It was restarted at
08:50 on mains power, the two routes the sleep had cut off were set aside and
rerun, and the sweep reached 37 of its 44 routes by 09:50. Measured so far: 31
of 34 scored routes succeeded (91.2%) against the paper's 64.8%, with 11 routes
stalling for 38 or more simulated seconds, 9 of them only freed by SimLingo's
scripted creep forward. The rest of the sweep, then reruns of six stalled
routes, keep running.

Two smaller fixes landed. `scripts/submit.sh` now passes `--dependency` and
other `--` options to Slurm, because Savio ignored the environment-variable form
last night (tested with a fake `sbatch`). And the sweep no longer counts a route
whose scenario Bench2Drive skipped: route 23918 was scored 100 by the benchmark
even though its InterurbanActorFlow scenario failed to set up, which will need
checking in every Step 2 log too. The Savio file-read problem is still open;
the recovery plan is in `docs/STATUS.md`.

## 2026-10-07 (01:15) — First Savio GPU jobs ran, and failed on a file read

The GPU check passed: the job landed on an RTX A5000 and finished cleanly. Step 1
and all 31 tasks of the comparison array then failed within seconds, each at
the same point: Python could not read one library file inside the CARLA client
package on Savio's scratch disk ("Cannot send after transport endpoint
shutdown", which is the file system refusing the read, not a code bug). The
array should have waited for Step 1 to pass, but the dependency was passed as
an environment variable and Slurm ignored it, so all 31 tasks started anyway.
Nothing was lost beyond a few GPU-minutes. Details and next steps are in
`docs/WHAT_BROKE.md`. The cluster's limits are now recorded: 4 running jobs per
user and 8 hours per job (`configs/cluster/savio.yaml`).

## 2026-10-07 — An overnight Savio comparison run, chained after Step 1

The Mac drove 31 Bench2Drive routes on 2026-10-06 and succeeded on 27 of 29
scored ones (93%), against the 64.8% the SimLingo paper reports. One untested
explanation is number precision. The Mac runs the model in 32-bit floats, while
CUDA runs, Savio's included, use bfloat16 (a 16-bit format), which moves the
model's waypoints by up to 18 cm on the frames checked.

To test it, this session added a Slurm job array (one batch job per route):
`scripts/route_sample.sbatch` reads the same 31 route ids from
`configs/rollout/savio-mac-paired.yaml` and runs each through `run_savio.py`,
which gained a `--route` option. It is meant to be submitted with a dependency
on the Step 1 job, so it only runs if Step 1 shows that CARLA renders on Savio
and a route completes. A test checks that the array size matches the route
list. An existing port test was also fixed: it asked the operating system for
any free port, which on the Mac is often above 60,000, outside the range the
code searches.

Two sessions were committing in this checkout at once, and one backed out the
`--route` change as an accident before it was restored (`7662bee`). Nothing was
lost. Nothing has been submitted to Savio by this session; the user types every
cluster command.

## 2026-10-06 (evening) — Making the local sweep safe to leave running past midnight

The local sweep script (`adapters/simlingo/sweep_local.py`) stops starting new
routes at a clock time given as `--until HH:MM`. It read that time as *today*,
so an overnight run started at 21:40 with `--until 06:30` would have treated
06:30 as already past and stopped at once. It now means the next time the clock
reads 06:30, with a test for the midnight case. Nothing else changed; no runs
were started in this session.

## 2026-10-06 — Getting the code and model onto Savio for the first time

The goal tonight is Step 1: the first real driving run on Savio, Berkeley's
computing cluster. It answers one question the whole budget depends on — how
fast the simulator runs on their GPUs — and it uses about 1–1.5 of the 8
GPU-hours available tonight. Every earlier run happened on the Mac.

**The code could not be pushed to GitHub.** The account this Mac uses
(Imhaohao) does not have write access to `Christopher-Vu/HondaResearchInstitute`,
so GitHub refused the push with a permission error. Instead, the branch was
packed into a single file (a *git bundle*, 33 MB, ending at commit `857ec95`),
uploaded to Savio's file-transfer machine, and cloned from there. By the next
morning Imhaohao had write access and the branch was pushed normally.

**The agent cannot type on Savio.** Logging in needs a PIN plus a code that
changes every 30 seconds, so a person types every Savio command and the agent
reads the output from the terminal tab. An attempt to share one logged-in
connection with the agent was blocked by the app's safety filter, which wants
an explicit permission rule from the user first. That was left alone.

**Setup finished cleanly** (09:38 UTC, login node `ln001`). It downloaded the
Linux build of the CARLA driving simulator, the released SimLingo model and its
Python environment. The model file's fingerprint (`ec894372…`) matches the one
the Mac runs used, so both machines run the identical model, and all 12 maps
the benchmark needs are present. No GPU job had run yet at this point.

**An overnight Mac run landed while this was happening**: 32 commits, including
a 31-route sweep and the Step 3 record-and-replay test (see `docs/STATUS.md`).
None of the files Savio runs tonight changed, so the slightly older copy on
Savio is still correct for Steps 0 and 1. The sweep also showed the full
220-route benchmark (Step 2) needs roughly 34–49 GPU-hours, an estimate from
Mac speed, so it cannot be finished tonight.

**Two pieces for people outside the project, built from the Mac runs.** A web
page ([Inside SimLingo's Stall](https://claude.ai/artifact/Bg3omkBQDvnS5iY1WQncan),
private until shared) replays route 1956, where the car sat parked for 41.1
seconds with the brake fully on until the agent's stuck timer forced the
throttle at 40.1 s. Its camera and pedal traces are real. Its view inside the
model is invented. The page also has a short video of the only crash in the
overnight sweep, route 28330: the car turned left across traffic at 14.4 m/s,
hit two cars, then held full throttle against the second one for about a minute
(3 vehicle collisions, score 20.9; `results/local-sweep/20261006-overnight/route-28330`).
Neither piece is committed: both are presentation, not evidence.

**The recorded internal activity stayed closed.** Showing the real activity
would have meant opening it before baseline B7's rule is written down, which
the project forbids so that rule cannot be shaped by what we see. The page uses
made-up activity instead, labelled as such on every panel. Writing B7's
definition is now the thing blocking a real version.

**Left to do:** this session ended without confirming the GPU check
(`scripts/check_gpu.sbatch`) was submitted, so no Savio GPU job is known to
have run. After it, the one-route run (`scripts/step1.sbatch`), then record the
measured speed and memory use.
