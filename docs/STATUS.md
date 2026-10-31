# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.
Tick the matching done-conditions in `docs/steps/progress.yaml` at the same time,
and rewrite its `week` block each Friday; the status dashboard
(https://failure-axis-status.vercel.app) reads it from GitHub.

Last updated: 2026-10-31 (P9 fails its screen; P7 and P8 full pilots queued; current step is 5)

---

## Current position

**2026-10-31, P9 closed; P7 and P8 full pilots queued (Jerry's account).** The P9 glare
screen reran cleanly with the dormant-light fix: 9 of 10 pairs scored (route 2809933 lost
to a CARLA start crash), glare routes failed 3 of 9 against 4 of 10 without, 0 excess
failures against the 3 required (measured). Even a failed-only-with-glare outcome on the
missing pair could not reach 3, so P9 is dropped without a full pilot. P7 camera freeze
(array 40681180, scoring job 40681181) and P8 camera latency (array 40681196, scoring job
40681197, starts after P7) are submitted, 60 pairs each, configs
`configs/rollout/step5-pilot-p{7,8}-main.yaml`; screen bases are disjoint from the main
bases (checked). Expect roughly 500 SU each (unmeasured; P4's pilot is the reference).
Savio's checkout is at 15b29c8. The C21 background wave is not queued: its generator has one
hard-coded id offset for background routes (`dev_routes.py` `ROLE_ID_OFFSET`), so a
third wave would collide with wave 2's route ids, and C21 still needs Chris and Jerry.

**2026-10-30, P9 screen resubmitted (Jerry's account).** Savio's checkout was
fast-forwarded to 8e1e873 by git bundle, which carries the dormant-light fix. Array
40659402 reruns all 20 routes; scoring job 40659403 runs after it and writes
`results/savio/step5-pilot-p9-screen/efficacy.json`. The crashed run's results moved
to `results/savio/step5-pilot-p9-screen-crashed-40341126`. About 85 SU expected.
Savio was back after the 2026-10-26 maintenance (checked 2026-10-28: no inactive
storage targets, 3,001 scratch reads clean).

**2026-10-23, P7–P9 screens scored (measured).** P7 camera freeze passes its screen
(6 slice-only against 0 neighbourhood-only failures over 10 pairs) and P8 camera
latency passes (5 against 0 over 9 pairs; route 2420641 stopped for slow simulation).
Both need full-pilot configs next. P9 glare does not pass, but only 3 of 10 pairs
scored: 7 slice routes crashed on our own glare code, not on CARLA or the disk
(`docs/WHAT_BROKE.md` 2026-10-23). The crash is fixed in code (unit-tested, not yet
run in CARLA); next, bring Savio's checkout up to date and rerun the P9 screen.
Scratch reads were clean today (3,000 files, 0 failures), but the 2026-10-26
maintenance still applies. Jerry's account still cannot read Chris's Step 2 shards:
`/global/scratch/users/christophervu` is `drwx------`; Chris must grant access.

**2026-10-22, a pass rule for the dev evaluation, drafted and not run.** Pooling the
two Step 4 waves with the P4 pilot, all already in Jerry's Savio share, gives 504
rollouts and 140 failures with P4 at 31% instead of 70%, with no new rollouts.
`docs/steps/dev-eval-pooled.md` fixes the methods, baselines (B3 included), a 0.5
catch-all cap and what counts as separation before anything runs. Needs Chris's
review; Tier 2 needs read access to his Step 2 shards, which Jerry's account lacks.

**2026-10-21 18:00, P7–P9 screens submitted (Jerry's account).** Savio's checkout was
fast-forwarded to `main` (b11ad6a) by git bundle and the left-crossing patch applied
to its runtime; a test read of 2,000 runtime files found no scratch-disk failures.
Arrays 40341122 (P7), 40341124 (P8), 40341126 (P9), 10 pairs each at two routes per
A40; scoring jobs 40341123, 40341125, 40341127 run after them and write
`results/savio/step5-pilot-p{7,8,9}-screen/efficacy.json`. The automatic follow-on
to a full pilot was not chained: P7–P9 have no full-pilot configs yet. About 250 SU
expected. If a route crashes at startup, check the scratch disk first
(`docs/WHAT_BROKE.md` 2026-10-20).

**2026-10-21, three new practice gaps ready.** Every gap that only
changed appearance failed, and P4, which removes information, passed. So the next
candidates all remove information: P7 camera freeze (stale for 2 s of every 3 s),
P8 camera latency (every frame 1 s old) and P9 traffic-light glare (each light in
view painted white, on the 30 signalized-junction routes only). Screen configs:
`configs/rollout/step5-pilot-p{7,8,9}-screen.yaml`; submit commands in their
headers. **Needs a Savio login**, and after the 2026-10-26 disk fix is safer. If
P9's screen passes, its full pilot cannot reach C23's 60 pairs (open decision).
A rear-end-while-stopped "blind-spot control" is proposed in CONFLICTS.md C32 for
Chris's review; not built.

**2026-10-21, IEEE IV 2026 sweep (296 papers, 13 read in full).** Nothing changes
the method or the novelty claim. Four more gap families that remove information
(optimised billboard, semantic-rule scenarios, misleading commands, scene edits
around a failure) and an open-loop replay pre-screen to try before closed-loop
pilots: `docs/iv2026-literature-findings.md`. All unverified; needs sign-off.
Follow-up the same day (measured, open loop, 88 replayed frames): SimLingo obeys
trained commands (stop, lane change) but barely responds to harmful or falsely
reassuring ones, and Bench2Drive sends it no text, so misleading commands are a
weak gap family. PDM-Lite uses no camera, so it should run without rendering;
the timing test is blocked by disk (compute-box 3 GB free, laptop 1.5 GB).

**2026-10-16, decisions (Chris and Jerry).**

- **Step 4 closed.** Driving queries at layer 10 are the logged site; per-token
  capture moves from layers 10 and 14 to 10 and 11. New rollout configs set
  `capture_token_layers: [10, 11]` (`docs/steps/04-layer-site-ablation.md`).
- **B7 signed off** with the correction to Dr. VLA's Eq. 7 hysteresis (C18,
  `src/baselines/activation_stats.py`). Earlier B7 numbers are pre-correction.
- **CARLA segfaults** lost 8 of about 90 long-route tasks overnight; reran.
  Budget about one rerun per 20 long-route tasks (`docs/WHAT_BROKE.md`).
- **Still blocking Step 5:** P4 is the only practice gap that passes; the spec
  needs 4 to 6 gaps and 2 decoys. Every appearance-only gap (fog, P5, P6) failed.

**2026-10-15 overnight, Chris's session (account christophervu).** Running.

- **Independent Savio bring-up passed.** Setup from scratch in
  `/global/scratch/users/christophervu/hri`; GPU job 39967188 ran (Step 0's
  "both of us"). **Step 1 rerun passed** (job 39967189, n0280): route 26956
  completed, 299 model steps, 0.078x real time, 9.42 GB peak VRAM, strict
  checkpoint load (measured; Jerry's run 0.071x, 9.4 GB).
- **Step 2 rerun passed** (array 39967810, `configs/rollout/step2-rerun.yaml`,
  measured): official driving score **88.34**, success rate 70.3% over 219 of 220
  routes (Jerry's run 88.60 / 72.7% over 220). Without the same 7 skipped
  Interurban scenarios: 88.22 / 71.2% over 212 (Jerry 88.63 / 73.7% over 213).
  Real-time factor 0.092. Route 26456 lost to a CARLA start crash and is rerunning
  (40008751). The run also saved layer 10 and 14 tokens on every route: the dev
  corpus where P4 is a minority (Next, item 1), in Chris's Savio scratch.
- **Left-crossing stall diagnosed** (Chris, evening): Bench2Drive's
  `DynamicObjectCrossing` with `direction: left` loops forever on two-way roads
  (166 of 220 Bench2Drive trigger points). Patch verified on public routes,
  not yet applied to the shared runtime (needs Chris and Jerry):
  `docs/infra/left-crossing-stall.md`.
- **Step 4 ablation over layers and sites, done** (`docs/steps/04-layer-site-ablation.md`,
  measured): driving queries at layers 10 and 11 are the only stable picks, on a
  second corpus and under 50 resamples. Knocking out layer 11 live on 40 routes
  changes nothing measurable (11 against 9 failures). Knocking out the first
  layer's pass over all tokens collapses driving (31 of 40 fail). Suggestion for
  Jerry: keep layer 10, capture layer 11 per token instead of 14.
- **Some routes ran ~50x too slowly** (real-time factor 0.002) because of a
  scenario, not the nodes; an exclusion of n0278 and n0281 was reverted
  (`docs/WHAT_BROKE.md`).
- **New code on main:** B3 behavioral baseline, probe-residual (M3a), the
  §13.1 bootstrap, key sealing, per-step logging of nearby vehicles,
  two-wheelers, animals and obstacles, camera freeze and latency faults. Specs
  for B3, probe-residual, the describability gate and B8, Step 8 and Step 10.
  B4's factor list is committed and tagged `b4-factors-v1` (C30). C18 now notes
  that Dr. VLA's firing rule is a hysteresis, which B7 does not follow yet.

**2026-10-15 overnight, finished (agent; Jerry asleep).** Nothing is queued.
Spend this round 991 of 2,000 SU (2,592 since 2026-10-13 02:30, measured).

- **P6, animal crossing: failed its screen** (1 of 9 against 2 of 10 with a
  person); the auto-continue job declined the full pilot. P4 is still the only
  passing practice gap, and every gap that only changes appearance has failed.
- **Layer sweep with P4 scored for the first time:** driving queries layer 10
  first again; the all-tokens site recovers P4 far better (Jaccard 0.77 at layer
  18 against 0.36), since P4 is perceptual.
- **SAE (PRD 12.2), 36 runs:** held-out explained variance 0.92 to 0.93, no dead
  latents, but seeds learn largely different dictionaries (mean best cosine 0.28
  to 0.43 against 0.11 for random).
- **First dev evaluation: inconclusive.** P4 is 70% of the token corpus's
  failures, so an all-failures axis scores 0.70 and every method sits there;
  contrastive diffing's top axis is that catch-all (C27's shared direction,
  measured). Capping a latent's failure share removes it, but across six seeds
  the capped method averages 0.70 to 0.74. Details in `docs/WHAT_BROKE.md`.

**2026-10-15: P4, camera occlusion, passed efficacy, the first practice gap
that does.** 60 paired base routes (array 39921545, scored by job 39921546):
43 of 60 failed with the patch against 12 of 60 without (uplift 52 points,
ratio 3.6, Fisher p = 1.9e-8); paired, 31 bases failed only with it and none
only without (McNemar p = 9e-10). Driving score 63.4 against 91.9; vehicle
collisions 30 against 6, red lights 8 against 0, pedestrian collisions 5
against 0. Evidence: `results/savio/step5-pilot-p4-main/`, shards with layer
10 and 14 tokens on Savio. Steps 6 and 7 now have a passing practice gap to
develop against. Spend this round: 828 SU of 2,000 at 23:50.

**2026-10-14: screens.** Screens
of 10 paired base routes, each judged by a rule fixed beforehand
(`gaps/practice/practice_v2.yaml`):

- **P4, camera occlusion:** passed. 8 of 10 failed with the patch, 4 of 10
  without; 5 bases failed only with it, 1 only without. Full pilot passed (above).
- **P5, pedestrians walking in the ego lane:** walkers present on every slice
  route, but SimLingo failed 2 of 8 against 1 of 9. Screen failed; stopped
  (`docs/WHAT_BROKE.md`).
- **P6, an animal crossing:** Fail2Drive's server runs our routes and its
  animals appear (`docs/p6-animal-check.jpg`); both smoke routes passed. Screen
  runs as array 39921553, scored by job 39921554.

Per-token capture (layers 10 and 14, 30 driving-query tokens, float16) is
verified: the tokens average exactly to the logged means. Spend this round:
189 SU of 2,000 at 17:20 (measured), about 760 once these jobs finish.

**2026-10-13 overnight: Step 4 is not closed, and the third weather gap failed.**
The stability check changed the chosen layers in 4 of 5 resamples (layer 10 held
in 4; `results/savio/step4-dev-pool/stability.json`), so the spec's second wave of
200 background routes is running on Savio as array 39868383 (started about 06:10,
after the pilot below), then job 39868384 re-sweeps both waves into
`results/savio/step4-dev-pool-both/`. **P3, dense fog at noon, failed efficacy**:
25% failures in fog against 30% at clear noon over 59 paired base routes
(Fisher p = 0.68, McNemar p = 0.79; `results/savio/step5-pilot-p3/`). No practice
gap passes yet, and weather does not seem able to make one. B2 (human taxonomy)
and B7's statistics (steps 3–8) are coded and tested. Spend: about 510 SU by
05:15, 1,350 projected with the second wave, under Jerry's 2,000 cap.

**2026-10-13: a literature sweep narrowed the novelty claim.** Three papers the
PRD had missed are now in §4.10–4.12. SPHINX closes the loop from a driving
policy's internals, Motzkus & Bernhard put SAEs on an end-to-end driving model
(open-loop), and Gupta et al. close the loop from logs with no internals at all.
Planted-gap scoring for closed-loop policies is still unclaimed. Proposed for
Chris and Jerry: a required log-based VLM baseline (C25), leading with the
harness (C26), and three cheap discovery checks on dev (C27). Evidence:
`docs/step0-trackA-findings.md`.

**2026-10-12: Step 4's sweep is done and read, on Savio only.** It chose the
driving-query site at decoder layers 10 and 11 (combined ranks 7.9 and 9.5).
**Both practice gaps failed efficacy**: P1 7/30 vs 5/29 (p = 0.75), P2 2/30 vs
0/30 (p = 0.49), so gap recovery was skipped and no third pair was added. 189 of
190 routes have an outcome (DS 93.8, SR 84.7%); route 2535800 is on the rerun
list. A design review found the efficacy check underpowered and unpaired
(`CONFLICTS.md` C23) and proposed a manipulation check (C24); future arrays now
run in a shuffled order (`05979cb`). Not yet done: layers written into the
config, `sweep.json` copied into the repo, the resampling stability check.

**Night of 2026-10-09: Step 4's dev pool ran on Savio.** Array job
39784630 drives 190 routes (95 tasks, two routes per A40, at most 6 at once;
about 780 SU and 5 hours at Step 2's rate), and job 39784631 starts when it
ends: it scores the routes, exports each capture to a shard, checks the two
practice gaps' efficacy and runs the layer sweep, writing
`results/savio/step4-dev-pool/{routes.jsonl,shards/,sweep.json}` on Savio.
Spec: `docs/steps/04-dev-pool-and-layer-sweep.md`. Every route now also logs
ground-truth state, collision events and the vision bridge, verified on two Mac
routes; it had not run on Savio before this array, so check the first routes'
`run.log` if anything looks wrong.

- **B7 is frozen** (`docs/steps/b7-gap-signal.md`), before any activation was
  opened; Chris and Jerry's sign-off pending.
- **Practice gaps** (`gaps/practice/practice_v1.yaml`): P1, a dust storm at
  night (30 routes, one per scenario family); P2, a pedestrian stepping out from
  behind a container at night (30 routes, with the same grid at noon as its
  neighbourhood). Each is checked against the §9.1 efficacy thresholds before
  the sweep scores recovery of it. **On Savio the dust is invisible at night,
  so P1 tests a very dark night** (`docs/WHAT_BROKE.md`); the first 12 routes
  captured state and activations with no errors.
- **Step 3 on Savio is exact against itself, not against the live log**
  (jobs 39784216 and 39784287, 5 SU). Replays of 331 Step 2 frames in CUDA
  bfloat16 sit 1–3 rounding steps (median 1–3 cm) from the logged waypoints,
  while three replays of the same frames agree to 0.0 m. `CONFLICTS.md` C22
  proposes replay-against-replay as the done-condition; `docs/WHAT_BROKE.md` has
  the candidates for the difference.

**Steps 1 and 2 passed on Savio, 2026-10-08.** Step 2's last open item is a
rerun by whichever of us did not set it up.

**Step 2: Bench2Drive-220, one seed, CoT off, bfloat16, v0.0.3 — official DS
88.60, SR 72.7%** (Bench2Drive's own merge over all 220; bar DS ≥ 75; paper
84.41 / 64.84 over three seeds). Without the 7 routes whose scenario Bench2Drive
skipped (all Interurban(Advanced)ActorFlow): 88.63 / 73.7% over 213. Config
`configs/rollout/step2-bench2drive220.yaml`; evidence `results/savio/step2-bench2drive220/`
(summary, per-route rows, merged JSON; laptop copy) and, on Savio, the per-route
directories under `results/savio/<job>/` with Step 3 capture every 10th step.
Cost 31.0 GPU-hours, 910 SU (4.1 SU per route), two routes per A40.

What it answered: the Mac's 93% success was mostly its easy route sample (those
routes succeed 82.5% on Savio, the Mac 92.5%; the paired difference is p = 0.29),
and SimLingo's 40-second stalls recur across platforms (`docs/WHAT_BROKE.md`).
48 of 213 routes stood still for 38+ simulated seconds. Per-ability success
matches the paper's shape (Give Way 50.0 and Merging 62.5 weakest, Emergency
Brake 85.0 and Traffic Sign 86.8 strongest; `PRD.md` §10.1).

Step 1, job 39732394 on one A40: real off-screen camera image, strict checkpoint
load (hidden size 896, 24 layers), route 26956 completed with score 100 at
**0.071× real time** and **9.4 GB** peak VRAM for 4.75 SU
(`configs/rollout/step1-single-route.yaml`, `PRD.md` §17.3). Open items: the
container became the pinned tarball (`CONFLICTS.md` C20, pending review), and
§16.2 has its inputs but is a design call for Chris and Jerry.

Savio lessons from the night, all in `docs/WHAT_BROKE.md`: use the `gpu_a40`
profile when the A5000 queue is long; always pass
the faulty A40 nodes, which `configs/cluster/savio.yaml` now excludes on every `gpu_a40` submission; two routes share an A40
safely now that their CARLA servers start one after the other; an evaluator
silent for 15 minutes is stopped (`f111121`).

Track A (paper facts) is complete: six papers read, findings in
`docs/step0-trackA-findings.md`, applied to `PRD.md`. Track B: the allowance
has GPU access on A5000 (`gpu` profile) and A40 (`gpu_a40` profile). On
2026-10-08 the A5000 queue was days long while A40s started within minutes.

**Local CARLA and SimLingo completed a real route end to end.** The
released model strict-loads on CPU and MPS. Stock Windows CARLA 0.9.15 runs on the
M5 Pro through Sikarugir/D3DMetal, using an arm64 client compiled for Python 3.11.
The camera/control smoke passed 100 matching frames and moved the vehicle 4.704 m.

`Open CARLA.command` starts a fresh server and runs the real SimLingo model on
Bench2Drive route 26956. It shows the existing model camera feed in a native
window, records controls and writes the benchmark result. The completed run is
`results/local-mac/20261002-182756/`: 73.757 m, 100% route completion, 293 actual
model inference steps, 14.7 simulated seconds in 244.670 wall seconds (0.0601×).
There were no collisions, traffic-light/stop violations, route deviation or
timeout. Minimum-speed checkpoint ratios are retained in the raw result; the
pinned benchmark logs these unconditionally and excludes them from the score
penalty. The desktop street view, Space pause/resume and Escape cleanup were
verified. The camera window has its own event loop and app identity, so model
inference cannot block its controls. UI evidence is in `results/setup/ui-smoke.json`.

The Mac config is `configs/rollout/local-mac.yaml`; source revisions, released
checkpoint checksum, native wheel checksum and compatibility patches are in
`configs/setup/simlingo-artifacts.yaml`. Full rendering quality bypassed the Low
quality camera-startup crash. Offline model smoke results never count as route
proof. Local execution does not establish Savio performance/VRAM or compatibility
with the Fail2Drive custom server. Official additional maps are installed: all
22,211 packaged files passed length and CRC checks, and every town referenced by
the 220-route XML is available. Town12 passed 100 synchronous camera/control
frames after installation. Evidence is in
`results/setup/additional-maps-installed.json` and
`results/setup/town12-smoke/result.json`. These checks do not validate all 220
policy routes. Keep the lid open during runs; the launcher prevents ordinary
idle sleep with a temporary assertion and releases it on exit.

## compute-box, 2026-10-07/08: no CARLA; used for the bfloat16 replay

compute-box (`ssh compute-box`, M1 Pro, 16 GB; also serves production's Blender
offload) has the CARLA setup but **must not run routes**: its D3DMetal renders
the policy camera nearly black from the first frame (mean pixel 3.6/255 on a
daytime route where the laptop sees 138/255), fading to flat. The relaxed check
from `6763534` no longer rejects such frames, so a compute-box run would now
drive blind without crashing (`docs/WHAT_BROKE.md`). **The two stall repeats
17635 and 24841 are still undone**; to finish them on the laptop (about 50
minutes, plugged in):
`.runtime/policy-venv/bin/python adapters/simlingo/sweep_local.py --routes 3457,2144,14909,2204,17635,24841 --until 23:59 --capture-every 10 --output results/local-sweep/20261006-repeats`.

**bfloat16 replay, 2026-10-08 (measured).** compute-box replayed 60 saved Mac
frames (5 per route, 12 routes) in CPU bfloat16 against the fp32 log
(`results/replay-bf16*/`). Route waypoints moved by a median 4.0 cm (worst
13.4 cm); speed waypoints by a median 8.0 cm, and 58 of 60 frames stayed within
57 cm. Two frames flipped: late in routes 26956 and 25424, at about 11 m/s, fp32
plans to keep going and bfloat16 to slow sharply (8.7 m and 6.7 m apart). Savio's
bfloat16 drive of 26956 did brake there while the Mac accelerated. During a
stall both dtypes agree on standing still. So Mac and Savio runs agree on what
SimLingo does except near such decision points; details in the adapter README.

## Overnight local work, 2026-10-06

Savio was not touched. The Mac GPU ran a local route sweep and the Step 3
replay de-risk from 02:20 to 09:20. Report with screenshots:
https://claude.ai/artifact/MuXb6v1BD4v1z9zbDAhDcr (private to its owner).

- **Sweep:** `adapters/simlingo/sweep_local.py`, one seeded route per scenario
  type; all 44 done (`results/local-sweep/20261006-overnight/`, measured).
  38 of 41 scored routes succeeded (92.7%, mean DS 96.8), far above the
  paper's 64.8% (`docs/WHAT_BROKE.md`). The 7 routes added after the 37-route
  count all succeeded. Failures: collisions on 28330 and 24781, a lane departure
  on 3800. Two stalled routes were capped unscored (2144, 3457), and 23918 is
  unscored because Bench2Drive skipped its scenario. Real-time factor 0.058.
  Across all 41 scored routes, 9 stood still for 38+ simulated seconds (all
  completed; 8 freed by the creep). The stall list below is from the first 31.
- **SimLingo stalls, and the benchmark hides it.** 10 of 31 routes stood still
  or crawled for 38+ simulated seconds. Nine were stalls: at debris, behind a
  cyclist, leaving a parking space, before two overtakes (an accident and a
  parked obstacle), at route start on an open highway, in a sequential lane
  change, at a foggy junction on green, and behind a blocked intersection. The
  tenth was the collision route, pinned against a car at full throttle. 8
  stalls moved again only when the agent's scripted stuck detector forced
  throttle; the 7 that finished all scored 100. Whether such stalls should
  become a dense label is a design question.
- **The stalls are reproducible.** Routes 1956, 23659 and 25845, rerun after
  07:50 (`results/local-sweep/20261006-repeats/`), stalled again at the same
  place for 40–41 simulated seconds, each rescued by one creep. Despite
  pixel-level nondeterminism, these stalls are properties of the scene, which
  makes them usable targets for the discovery methods.
- **Step 3 replay passes on the Mac.** Replaying logged inputs reproduces the
  waypoints exactly on MPS and to 9.1e-5 m on CPU. Float16 drifts by up to
  4.8 cm and bfloat16 (Savio's dtype) by up to 18 cm, so replay must match the
  logging dtype, and Mac and Savio rollouts are not frame-comparable. Details
  in the adapter README. Routes from the third onward carry capture.
- **Replay storage:** the agent's own JPEG regenerates the exact model input,
  32x smaller than the fp32 tensor. Measured table in `PRD.md` §12.1.
- **Closed loop is not reproducible:** the same route and seed see faintly
  different camera pixels from frame one (`docs/WHAT_BROKE.md`).
- **Step 2 sizing, first cut:** 36.2 simulated seconds per route on average,
  so 220 routes are about 34–49 GPU-hours at PRD §17.3's 0.045–0.065 real-time
  factor, before server start-up and with capped routes as lower bounds.
- **Desk research closed several open items:** event-grounded SAEs read,
  Fail2Drive repo checked, bucket weights and route-directory withholding
  confirmed from source, Drive-π0 release and licence checked, venue deadlines
  pinned (`PRD.md` §15, `docs/step0-trackA-findings.md`).
- **Activations from tonight are on disk but unread.** B7's definition still
  has to be written before anyone opens them.

## Next, in order

1. **A dev corpus where P4 is a minority of failures** (decision for Chris and
   Jerry, C21). The SAE methods need per-token data, which only the Step 5
   pilots have. A background wave of about 400 routes with token capture
   (roughly 1,600 SU at 4.1 SU per route) would bring P4 to about 15% of
   failures with 30 of its slice routes; until then the dev evaluation cannot
   separate methods.
2. **More practice gaps that remove information.** Appearance changes (night,
   fog, dust, pedestrians in lane, animals) all failed; blinding the camera
   passed. Candidates: hazards hidden until late, a camera fault on one side
   only, a lead vehicle invisible to the camera. Interactional ones still need
   C23's 30-base-route floor. More candidates, and a replay pre-screen to
   reject no-effect gaps before they cost a pilot, in
   `docs/iv2026-literature-findings.md`.
3. **Sign-offs:** C23 to C28 (C27 now carries a correction), and the pinned
   readings in `src/discovery/contrastive.py`, `src/baselines/activation_stats.py`
   and `taxonomy.py`; per-token SAE at layer 10 or 14 (k 48 to 64 look best).
4. Step 2's rerun: passed (DS 88.34, array 39967810, Chris). Score with
   `adapters/simlingo/score_routes.py configs/rollout/step2-rerun.yaml results/savio/39967810`
   on Chris's Savio scratch; the shards need read access granted to Jerry.
5. Code reaches Savio without GitHub: `git bundle create x.bundle <savio head>..codex/carla-bringup`,
   copy it over, then on Savio `git fetch ../x.bundle codex/carla-bringup:refs/remotes/bundle/carla-bringup`
   and `git merge --ff-only bundle/carla-bringup`. Savio's checkout was at
   `ccc4534` on 2026-10-13. Savio refuses a second SSH session while
   one is busy, so run cluster commands one at a time.

**An agent can reach the cluster only through a shared SSH connection that a
person opened.** Login requires a PIN plus a rotating 6-digit code and `ic_`
allowances forbid unattended keys. Run `ssh savio`, log in, then `exit`; the
agent's `ssh savio '<cmd>'` reuses that connection for up to 12h idle (verified
2026-10-08). See `CLAUDE.md` § Cluster.

## Built so far

177 CPU tests pass (one more needs the CARLA client). Route runs use Savio A40s; the Mac runs single routes locally.

| Piece | Where |
|---|---|
| Scoring, metrics, harness-validity check | `src/harness/scoring.py` |
| Data contracts (axis card, directive, gap) | `src/harness/schema.py` |
| Config hashing + placeholder detection | `src/harness/config.py` |
| B1 random baseline | `src/baselines/random_baseline.py` |
| Sealed-key CI guard | `scripts/check_sealed_imports.py` |
| Cluster indirection | `configs/cluster/savio.yaml`, `scripts/submit.sh` |
| Savio runtime setup and Step 1 job | `adapters/simlingo/setup_savio.py`, `run_savio.py`, `scripts/step1.sbatch` |
| Route runner shared by Mac and Savio | `adapters/simlingo/route_run.py` |
| Route arrays, two routes per GPU | `scripts/route_sample.sbatch` |
| Step 2 scoring (Bench2Drive merge plus validity columns) | `adapters/simlingo/score_routes.py` |
| Per-ability scores | `scripts/ability_benchmark.sbatch` |
| Practice-gap predicates, dev-pool routes | `src/harness/predicates.py`, `adapters/simlingo/dev_routes.py` |
| State, collision and vision-bridge capture | `adapters/simlingo/capture_agent.py`, `world_state.py`, `state_geometry.py` |
| Shards and the layer sweep, with the efficacy gate | `adapters/simlingo/export_activations.py`, `src/discovery/layer_sweep.py`, `scripts/step4_sweep.sbatch` |
| Savio replay check | `scripts/step3_replay.sbatch` |
| B3 behavioral stratification | `src/baselines/behavioral.py` |
| Probe-residual discovery (M3a) | `src/discovery/probe_residual.py` |
| §13.1 condition 2 bootstrap | `src/harness/bootstrap.py` |
| Answer-key commitment and gap loading | `src/harness/seal.py` |

Building the scoring layer before any rollout exists is deliberate, not
opportunistic: `PRD.md` §9.1 wants it frozen and hash-committed before the test
pool is generated.

## Who is doing what

- **Chris, Jerry** — harness, scoring, the step sequence.
- **A collaborator** — SimLingo setup, on a branch, landing as a PR. Scope and
  constraints: `docs/steps/adapter-simlingo-brief.md`. Partial progress expected,
  because the GPU block limits how far it can go.

## In parallel with Step 1

`docs/steps/gpu-free-queue.md`, in order. The top item is **B7's gap-signal
definition** (`PRD.md` §16.9, `CONFLICTS.md` C18). It must be written before
anyone looks at real activations, and Step 3 will produce them soon.

## Open questions worth remembering

- **Event-grounded SAEs (arXiv 2605.17204)** is read (2026-10-06,
  `docs/step0-trackA-findings.md`). Its causal edit assumes a per-token SAE,
  which clashes with §12.1's mean-pooling; decide the causal operator before
  Step 7. Its code is MIT-licensed.
- **Dr. VLA's repo has no LICENSE file** (rechecked 2026-10-06: none in the tree or `pyproject.toml`). Ask the authors before vendoring any of
  it; reimplement from the paper if they decline.
- **Model architecture is now confirmed locally.** Hidden size 896 and 24
  decoder layers were read from the strict-loaded released model; query module
  paths are recorded in the SimLingo adapter README and PRD §16.11.
- **The gap portfolio size** (`PRD.md` §16.2) is budget-bound and cannot close
  until the rollout throughput measurement and the SU rate both exist.
- **`savio_lowprio` is not available to this allowance**, so `PRD.md` §17.2's
  preemptible fan-out plan needs revisiting before Step 2 (`CONFLICTS.md` C20).
