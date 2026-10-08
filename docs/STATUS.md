# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.

Last updated: 2026-10-08 02:25 (Step 1 passed on Savio; Step 2 running; overnight agent session in progress)

---

## Current position

**Step 1 passed on Savio, 2026-10-08. Step 2 (Bench2Drive-220) is starting.**

Step 1, job 39732394 on one A40 (`gpu_a40` profile): off-screen rendering gave
a real camera image, the checkpoint strict-loaded (hidden size 896, 24 layers),
and route 26956 completed with score 100 in 299 model steps. Measured: **0.071×
real time** (Mac 0.060×), **9.4 GB** whole-stack peak VRAM, 4.75 SU for the
9.7-minute job. Numbers are in `configs/rollout/step1-single-route.yaml` and
`PRD.md` §17.3; evidence in `results/savio/39732394/` (laptop copy). Done
condition items still open: "in the container" is replaced by the pinned
tarball (`CONFLICTS.md` C20, pending review), §16.2 has its inputs but is a
design call for Chris and Jerry, and a person who did not set it up has not yet
rerun it.

**Step 2 in progress (overnight session, 2026-10-08).** Config
`configs/rollout/step2-bench2drive220.yaml`: all 220 routes, one seed, CoT off,
bfloat16, with Step 3 capture every 10th step. It also covers the 31 Mac-paired
routes, so `savio-mac-paired.yaml` (old item 4a) is not run separately. Runs two
routes per A40 (`scripts/route_sample.sbatch <config> 2`) after a pilot of the
first four routes, array job **39732614**, then the main array **39732818**. Score with
`adapters/simlingo/score_routes.py`, which reports Bench2Drive's own merge and a
clean number without skipped scenarios, and lists crashed routes for rerun. The
first pilot (39732585) died on a faulty A40 in `n0214`; always pass
`--exclude=n0214.savio3` until Savio fixes it (`docs/WHAT_BROKE.md`).

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

## compute-box, 2026-10-07: set up, but cannot run routes yet

CARLA runs were moved off the laptop to compute-box (`ssh compute-box`, M1 Pro,
16 GB; it also serves production's Blender offload). Setup is complete and
matches the laptop's install, but 6 of 7 route attempts crashed on a black
camera frame within the first 2 simulated seconds (`docs/WHAT_BROKE.md`). Freeing
memory did not help, so the cause is not memory. No
compute-box route has produced a result. **The two stall repeats 17635 and 24841
are still undone.** Next: rerun them on the laptop (about 50 minutes, plugged in):
`.runtime/policy-venv/bin/python adapters/simlingo/sweep_local.py --routes 3457,2144,14909,2204,17635,24841 --until 23:59 --capture-every 10 --output results/local-sweep/20261006-repeats`. To retry there:
`open -a Terminal ~/run_routes.command` on compute-box (sweep with a 120-minute
cap and a swap/disk guard; it runs at 0.009–0.021× real time).

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

Steps 0–1 on Savio are done (setup, push access, GPU check, Step 1 route,
measurements into the config and `PRD.md` §17.3). The 2026-10-07 `import carla`
failure was a passing scratch fault; nothing was rebuilt (`docs/WHAT_BROKE.md`).

1. Finish Step 2. Running since 2026-10-08 02:20: pilot **39732614** (routes
   1711, 1790, 1792 scored; 1773's CARLA crashed at startup), main array
   **39732818** (tasks 2–109, two routes per A40, at most 4 A40s), and 1773's
   rerun **39732819**. Do not change runtime code on Savio (`run_savio.py`,
   the agents, `route_run.py`) until these finish, since every task runs the
   checkout it starts with (`cd8ac06` behaviour).
2. Score: `.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py configs/rollout/step2-bench2drive220.yaml results/savio/<pilot> results/savio/<rest> [retries]`.
   Rerun the routes it lists under `rerun` as a new array, never re-roll a
   driving outcome. The bar is official DS ≥ 75 (`PRD.md` §10.1).
3. Per-ability scores: `Bench2Drive/tools/ability_benchmark.py` on the merged
   JSON. It starts its own CARLA, so it needs one short GPU job.
4. Compare with the Mac sample on the 31 shared routes (outcome only). If Savio
   lands near the paper's 64.8% success while the Mac got 93%, an fp32 arm on
   Savio separates precision from platform (`docs/WHAT_BROKE.md`, 2026-10-06).
5. Close `PRD.md` §16.2 (gap portfolio size) as a design decision, using §17.3.

**An agent can reach the cluster only through a shared SSH connection that a
person opened.** Login requires a PIN plus a rotating 6-digit code and `ic_`
allowances forbid unattended keys. Run `ssh savio`, log in, then `exit`; the
agent's `ssh savio '<cmd>'` reuses that connection for up to 12h idle (verified
2026-10-08). See `CLAUDE.md` § Cluster.

## Built so far

60 CPU tests pass; local CARLA and model bring-up use the Mac GPU.

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
