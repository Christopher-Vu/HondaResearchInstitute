# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.

Last updated: 2026-10-02

---

## Current position

**Step 0 — Track A done, Track B blocked.**

Track A (paper facts) is complete: six papers read, findings in
`docs/step0-trackA-findings.md`, applied to `PRD.md`. Track B (Savio access) is
blocked on cluster administration.

**Local CARLA and SimLingo completed a real route end to end. Savio Step 1 remains blocked.** The
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

## The blocker

Savio login works (user `christophervu`, allowance `ic_cdss170fall`), but there is
no usable GPU partition: `savio2_gpu` is retired, `savio3_gpu` and `savio4_gpu`
are rejected. A support request is open — the text is in
`docs/savio-support-email.md`.

When the reply arrives: set `gpu.available`, `gpu.partition`, `gpu.qos` and
`gpu.gres` in `configs/cluster/savio.yaml`. Nothing else needs editing.

Separately, **an agent can never reach the cluster** — login requires a PIN plus
a rotating 6-digit code and `ic_` allowances forbid unattended keys. Cluster work
means handing Chris a script to paste and reading back the output. Two such
scripts exist: `scripts/savio_recon.sh` (read-only recon) and
`scripts/check_gpu.sbatch` (GPU smoke test, also probes off-screen rendering).

## Built so far

53 CPU tests pass; local CARLA and model bring-up use the Mac GPU.

| Piece | Where |
|---|---|
| Scoring, metrics, harness-validity check | `src/harness/scoring.py` |
| Data contracts (axis card, directive, gap) | `src/harness/schema.py` |
| Config hashing + placeholder detection | `src/harness/config.py` |
| B1 random baseline | `src/baselines/random_baseline.py` |
| Sealed-key CI guard | `scripts/check_sealed_imports.py` |
| Cluster indirection | `configs/cluster/savio.yaml`, `scripts/submit.sh` |

Building the scoring layer before any rollout exists is deliberate, not
opportunistic: `PRD.md` §9.1 wants it frozen and hash-committed before the test
pool is generated.

## Who is doing what

- **Chris, Jerry** — harness, scoring, the step sequence.
- **A collaborator** — SimLingo setup, on a branch, landing as a PR. Scope and
  constraints: `docs/steps/adapter-simlingo-brief.md`. Partial progress expected,
  because the GPU block limits how far it can go.

## Next, if still blocked

`docs/steps/gpu-free-queue.md`, in order. The top item is **B7's gap-signal
definition** (`PRD.md` §16.9, `CONFLICTS.md` C18) — memorized-feature
concentration as a gap signal is our construction, not Dr. VLA's, so it needs a
written definition before Step 6 or B7 is not a fair baseline. Writing it before
we have seen any activations is also the honest order.

## Next, when unblocked

`docs/steps/01-smallest-rollout.md`. One route, not the benchmark. The five
stages are ordered so each failure is cheap to attribute; stage 1.2 (off-screen
rendering) is the most likely project-level blocker, and if it fails that is a
replan toward NRP rather than a debugging session.

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
