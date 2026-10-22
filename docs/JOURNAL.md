# Journal

What each agent session did and why, written for someone who was not there.
Newest entry first. Rules for writing entries are in `CLAUDE.md` under "Journal".

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

- At two routes per A40, a step takes about 0.5 s. The forward pass is 0.13 s; about 0.26 s is SimLingo's
  agent rewriting its whole `metric_info.json` debug file every step. `capture_agent.py` now writes that file
  once per route instead (ca63c56). The change cannot alter driving, but it has not yet run on a live route.
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
