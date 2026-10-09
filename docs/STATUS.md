# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.
Tick the matching done-conditions in `docs/steps/progress.yaml` at the same time;
the status dashboard (https://failure-axis-status.vercel.app) reads it from GitHub.

Last updated: 2026-10-08 08:45 (Step 2 passed on Savio: DS 88.60, SR 72.7%; bfloat16 replay measured on compute-box)

---

## Current position

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
`--exclude=n0214.savio3,n0215.savio3` (faulty A40s); two routes share an A40
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

Steps 0–2 on Savio are done except Step 2's independent rerun. Do not reopen the
2026-10-07 `import carla` failure: it was a passing scratch fault.

1. Step 2's done condition wants the run reproduced by whichever of Chris and
   Jerry did not set it up. A full rerun costs about 910 SU; decide whether that
   or a handful of routes plus a rescore is enough. To rescore:
   `.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py configs/rollout/step2-bench2drive220.yaml results/savio/39732614 results/savio/39732818 results/savio/39732819 results/savio/39732860 results/savio/39734524`
2. Design calls for the two of you: close `PRD.md` §16.2 (gap portfolio size;
   §17.3 now has measured cost) and review `CONFLICTS.md` C20 (tarball instead
   of container). Three seeds of Bench2Drive-220 (§10.1) would cost about
   2,700 SU at Step 2's rate.
3. Step 3 on Savio: the Step 2 routes captured model inputs in bfloat16 every
   10th step. Replaying a few of them with `adapters/simlingo/replay_capture.py`
   on a CUDA node checks Step 3's 1e-3 m done condition in Savio's dtype (one
   short GPU job). Write B7's definition (`docs/steps/gpu-free-queue.md`) before
   anyone opens the captured activations.
4. Before the next campaign, raise `timeout_seconds` from 60 to Bench2Drive's
   default 600 in the rollout configs (one route lost its setup to the 60 s
   limit; `docs/WHAT_BROKE.md`).

**An agent can reach the cluster only through a shared SSH connection that a
person opened.** Login requires a PIN plus a rotating 6-digit code and `ic_`
allowances forbid unattended keys. Run `ssh savio`, log in, then `exit`; the
agent's `ssh savio '<cmd>'` reuses that connection for up to 12h idle (verified
2026-10-08). See `CLAUDE.md` § Cluster.

## Built so far

84 CPU tests pass. Route runs use Savio A40s; the Mac runs single routes locally.

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
