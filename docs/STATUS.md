# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.

Last updated: 2026-10-06 (overnight local session)

---

## Current position

**Step 0 — Track A done, Track B unblocked; Step 1 built and ready to submit.**

Track A (paper facts) is complete: six papers read, findings in
`docs/step0-trackA-findings.md`, applied to `PRD.md`. Track B: the allowance
does have GPU access (`savio4_gpu` / `a5k_gpu4_ica`, `savio3_gpu` /
`a40_gpu3_ica`); the earlier "rejected" was the wrong QoS (`docs/WHAT_BROKE.md`).
**No GPU job has run yet.** The Savio Step 1 path is written but untested on the
cluster: `adapters/simlingo/setup_savio.py`, `run_savio.py`,
`scripts/step1.sbatch`. CARLA runs from the release tarball on the GPU node
(`CONFLICTS.md` C20, pending review).

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

## Overnight local work, 2026-10-06

Savio was not touched. The Mac GPU ran a local route sweep and the Step 3
replay de-risk from 02:20 to 09:20. Report with screenshots:
https://claude.ai/artifact/MuXb6v1BD4v1z9zbDAhDcr (private to its owner).

- **Sweep:** `adapters/simlingo/sweep_local.py`, one seeded route per scenario
  type; 31 of 44 run (`results/local-sweep/20261006-overnight/`). 27 of 29
  scored routes succeeded (93.1%, mean DS 97.1), far above the paper's 64.8%
  (`docs/WHAT_BROKE.md`). Failures: collisions on 28330, a lane departure on
  3800. Two stalled routes were capped unscored (2144, 3457). Real-time factor
  0.059.
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
  factor, before server start-up and with the capped route as a lower bound.
- **Desk research closed several open items:** event-grounded SAEs read,
  Fail2Drive repo checked, bucket weights and route-directory withholding
  confirmed from source, Drive-π0 release and licence checked, venue deadlines
  pinned (`PRD.md` §15, `docs/step0-trackA-findings.md`).
- **Activations from tonight are on disk but unread.** B7's definition still
  has to be written before anyone opens them.

## Next, in order

The exact commands are in `docs/steps/01-smallest-rollout.md`.

1. Push this branch, then clone it under `/global/scratch/users/$USER` on Savio.
2. Run `setup_savio.py` on a login node (about 20 GB of downloads; rerun after
   any interruption). Any failure here is a download or disk problem, not CARLA.
3. Submit `scripts/check_gpu.sbatch`. Its output closes Step 0 and says whether
   the GPU node has a Vulkan loader and outbound internet.
4. Submit `scripts/step1.sbatch`. If stage 1.2 (`render`) fails, read
   `results/savio/<job>/render/server.log`, then try the container fallback in
   `configs/cluster/savio.yaml`. If that also fails, it is the NRP replan.
5. Copy the measured wall-clock, real-time factor and peak VRAM from
   `route/readiness.json` into `configs/rollout/step1-single-route.yaml` and
   `PRD.md` §17.3, and close §16.2. Compare the Savio route with the Mac runs on
   outcome and real-time factor only; trajectories will differ (rendering noise,
   and bfloat16 moves waypoints by up to 18 cm).
6. Size Step 2 with tonight's numbers: 220 routes × mean simulated seconds per
   route (`results/local-sweep/20261006-overnight/`) ÷ Savio's real-time factor.
   Stalls make simulated time per route vary from 10 to over 100 seconds.

**An agent can never reach the cluster.** Login requires a PIN plus a rotating
6-digit code and `ic_` allowances forbid unattended keys. A person logs in in a
terminal; an agent can read that terminal's output but not type into it.

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
