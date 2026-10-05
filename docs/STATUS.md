# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.

Last updated: 2026-10-05

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
   `PRD.md` §17.3, and close §16.2.

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

- **Event-grounded SAEs (arXiv 2605.17204)** has not been read. Needed for the
  related-work paragraph and as the causal-check template. Due before Step 9.
- **Dr. VLA's repo has no LICENSE file.** Ask the authors before vendoring any of
  it; reimplement from the paper if they decline.
- **Model architecture is now confirmed locally.** Hidden size 896 and 24
  decoder layers were read from the strict-loaded released model; query module
  paths are recorded in the SimLingo adapter README and PRD §16.11.
- **The gap portfolio size** (`PRD.md` §16.2) is budget-bound and cannot close
  until the rollout throughput measurement and the SU rate both exist.
- **`savio_lowprio` is not available to this allowance**, so `PRD.md` §17.2's
  preemptible fan-out plan needs revisiting before Step 2 (`CONFLICTS.md` C20).
