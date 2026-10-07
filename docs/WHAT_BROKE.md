# What broke

Running log. Written as things happen, not reconstructed at the end — `PRD.md` §6
commits us to publishing this, and reconstructing it later never works.

One entry per surprise. Format: date, what we expected, what happened, what we
did. Dead ends count. "Turned out to be my typo" counts.

---

## 2026-10-07 — Moving the Mac CARLA runs to compute-box

**Expected:** copy the laptop's CARLA install (30 GB) to compute-box, the M1 Pro
16 GB Mac on the tailnet, and keep sweeping there.

**Actual, four surprises:**
- The laptop left the shared network mid-copy; Tailscale fell back to a relay at
  about 1.2 MB/s and dropped connections. compute-box instead downloaded the
  pinned Windows CARLA and AdditionalMaps zips itself (about 20 MB/s, checksums
  matched) and only the 476 MB Wine wrapper went over the relay.
- `ditto -x -k --hfsCompression` (unzip with APFS compression) failed on 347 of
  34,087 files with "Invalid argument" and stored the rest uncompressed. Plain
  `ditto --hfsCompression` file to file works, so a small script extracted each
  zip member, compressed it that way and checked the zip CRC. CARLA shrinks from
  30 GB to 17 GB; the file list matches the laptop's install exactly.
- Running the Sikarugir `launcher` over SSH prints "Closing Sikarugir" and starts
  nothing. CARLA starts when launched inside the logged-in desktop session
  (`open -a CARLA.app`, or the sweep started from a Terminal window via `open`).
- Memory: CARLA at Epic, idle, takes the box to 10.8 GB wired (GPU) memory and
  5.9 GB swap. With SimLingo on MPS it still runs, with swap steady at 6–7 GB,
  but at 0.021× real time against the laptop's 0.059×.

**Did:** ran the remaining repeat routes there with the sweep's wall cap raised
from 35 to 120 minutes (at 0.021× a 35-minute cap ends a route after about 45
simulated seconds, which would leave stall routes unscored) and a guard that
stops CARLA if swap passes 8 GB or free disk drops under 5 GB, because the box
also serves production's Blender offload.

## 2026-10-01 — Reconciled the two planning documents

**Expected:** two competing PRDs needing a winner picked.

**Actual:** the same project at two levels. The brief had the better scientific
argument; the 99p handoff had verified facts, better execution machinery, and was
partly a review of the brief. Resolved by precedence rule — design from the
brief, facts from the handoff — rather than by choosing.

**Notable:** the handoff's audit found the brief's motivating case study
(SimLingo 98.50 → 19.68 on pedestrians in the ego lane, with a hallucinated
vehicle-shaped lead actor) is unconfirmed. The aggregate Fail2Drive numbers hold.
Step 0 resolves it. Also unresolved: the brief and handoff give contradictory SAE
expansion ratios (1 vs 8×–32×) and both sound confident.

**Did:** wrote `PRD.md`, `CONFLICTS.md`, `docs/steps/00-ground-the-facts.md`.

## 2026-10-01 — Overwrote the original brief

**Expected:** writing `PRD.md` would sit alongside the existing `prd.md`.

**Actual:** Windows filesystems are case-insensitive, so `PRD.md` replaced
`prd.md`. Caught it on a post-write directory listing, not by noticing at write
time. The README had already been written claiming the original was preserved.

**Did:** restored all 881 lines byte-for-byte from the session's persisted
tool-result capture to `docs/source/project-brief-original.md`, under a
non-colliding name. Fixed the README.

**Lesson:** on this box, filenames differing only in case are the same file.
Applies to any future `README.md`/`readme.md` or config-casing pair.

## 2026-10-01 — Step 1 cannot be agent-automated; Savio needs interactive MFA

**Expected:** hand Step 1 to an agent and have it run start to finish.

**Actual:** structurally impossible. Savio requires a PIN plus a rotating
6-digit TOTP code at every login, and `ic_` allowances do not permit unattended
SSH keys. `hpc.brc.berkeley.edu` is reachable from this box and the TCP
connection succeeds, but authentication needs a human with a phone. There is
also no local GPU to rehearse against.

Compounding it: the `--partition` value for `ic_cdss170fall` is not published,
so even an authenticated agent could not submit a correct job yet.

**Did:** split the work by what actually needs a human.
- `docs/savio-support-email.md` — send first; longest external latency, and
  answers 1-2 are half the input to PRD §16.2.
- `scripts/savio_recon.sh` — one paste on a login node, read-only, answers most
  of Step 1 stages 1.1-1.2 without waiting for the email reply.
- `scripts/check_gpu.sbatch` — Step 0's done-condition, and it probes the
  off-screen rendering question (libGL/vulkan/Xvfb) since that is the most
  likely project-level blocker.

**Lesson:** MFA-gated clusters make the human the bottleneck for the first
touch of every environment. Design the asks as single-paste scripts whose output
can be handed back, rather than as sessions an agent drives.

**Also:** scripts written on Windows got CRLF endings, which break the shebang
on Linux. Added `.gitattributes` forcing LF on `.sh`/`.sbatch`/`.yaml`/`.py`.

## 2026-10-01 — Savio GPU partitions blocked; pivoted to GPU-free work

**Expected:** working login means we can submit a GPU job.

**Actual:** login works (user christophervu) but `ic_cdss170fall` has only
`savio2_gpu`, which is **retired**, and `savio3_gpu` / `savio4_gpu` are
**rejected**. No usable GPU partition. Support request open. Step 1 is blocked
on the reply, not on anything we can write.

**Did:**
- Externalised every cluster setting to `configs/cluster/savio.yaml`. No script
  names a partition, QoS or GPU type. `scripts/submit.sh` reads it and refuses
  GPU submission while `gpu.available: false`, printing the reason — so the
  failure mode is a clear message rather than a confusing Slurm rejection.
- Built the GPU-free half of the harness instead: schema contracts, Hungarian
  scoring, metrics, 32 tests. The headline metric is now verified on synthetic
  data before any rollout exists.
- Added the sealed-key CI guard the PRD promised, with tests that inject real
  leaks to prove it fails.

**Lesson:** "we have an allowance" and "we have a usable partition" are
different facts. Worth checking the second before planning around the first.
A retired partition is also a reminder to re-verify inherited infrastructure
claims — this one came from documentation, not from a successful job.

## 2026-10-02 — Mac compatibility and commentary-off model bring-up

The available machine is an Apple M5 Pro Mac with 48 GB RAM. CARLA 0.9.15 has
standard Windows/Linux server releases and no macOS Python wheel. A community
Windows-server path using Wine/D3DMetal is being tested, rather than changing
the experiment to CARLA 0.10. Docker Desktop's initial `info` probe returned 500;
no existing containers or VM state were deleted or reset.

Downloaded the released SimLingo checkpoint at Hugging Face revision
`26c7c89e797d4e25bbf640013317af8da26a5454` and verified SHA256
`ec8943723d266ee9f5f56f45d153a163b22616960bfccb741965ea5daa700d28`.
Its full model strict-loads on CPU and emits finite 10-point speed and 20-point
route predictions from a dummy camera input.

The pinned source defaults to commentary on. Setting `predict_language=False`
exposed a real error: `forward_model()` returns `(features, logits)`, but the
commentary-off branch passes that tuple to a tensor-indexing function. Reproduced
the original `TypeError`, patched the unpacking, and wired the agent's
`use_cot=False` setting into the model. The same weights and input then pass.
The patch and verifier are under `adapters/simlingo/`; CPU model execution does
not establish CARLA camera rendering or closed-loop experiment readiness.


## 2026-10-02 — Native client and local route bring-up

The Docker client could handshake but stalled during synchronous operations.
Built an arm64 Python 3.11 client from nfriend/CARLA revision
`0786f27568f1adfa645232e812b440cc7e3742ed`. Boost 1.80's enum used a Python GC
flag without a traverse function; the upstream one-line Boost.Python fix made
it import. NumPy 1.26.4 and framework Python headers were required for the build.
The client labels itself `0.9.15-macclient`, so the version-string warning is
expected and recorded. Real camera/frame matching and control then passed.

A route omitted `SCENARIO_RUNNER_ROOT` and silently skipped its scenario. That
attempt is invalid. The launcher sets the path and rejects any skipped-scenario
log or agent/server crash. Some later diagnostic retries overlapped a helper's
live tests; those attempts are excluded. All subsequent runs have one lifecycle
owner and one evaluator.

Low rendering crashed Unreal's render thread during camera warmup. Threading
flags, off-screen mode and a warmup delay did not resolve it. Epic rendering
reached real sensor input. Repeated world reloads were also unstable, so local
launches use a fresh server per route. Server readiness retries create a new
client after a failed startup connection.

The first live step tried to call Hugging Face `snapshot_download` with the
installed base-model directory as a repository ID. The prompt code now uses the
same offline directory as model setup. Cleanup expected an absent legacy
`data_module.encoder` field; it now reads that optional field safely.

The first model prediction exposed a one-element speed array in the PID history,
which NumPy 1.26 rejects as a ragged array. The PID boundary now requires scalar
speed with `velocity.item()`. The agent explicitly enters evaluation mode and
uses inference mode. MPS requires CPU fallback for bicubic upsampling under
PyTorch 2.2.0. The complete route now passes with
294 model inference steps and 100% route completion. Evidence is in
`results/local-mac/20261002-160934/`; the launcher stopped its owned server.

Minimum-speed records include ratios above 100%. In the pinned criterion, every
checkpoint unconditionally emits `MIN_SPEED_INFRACTION`; the percentage is ego
mean speed divided by background mean speed. Slow background traffic therefore
produces large values. The pinned statistics manager marks this penalty as
`unused`, matching PRD §13. Raw events and scores are preserved. This single
route verifies local plumbing and does not establish benchmark reproduction.


The first native window processed events on the inference thread, and macOS
accessibility calls could not inspect it reliably. Existing programs also share
Python's default app identity. The camera now runs in a separate, locally signed
Python app with its own event loop. Desktop camera pixels, Space pause/resume and
continued model controls were observed.

After closing the viewer, the upstream evaluator could linger in shutdown. The
viewer now records cancellation before announcing it; the launcher's log reader
then stops its owned process group immediately. Escape cleanup passed and the
cancelled run has no readiness result. The complete route using the independent
viewer is `results/local-mac/20261002-163439/`.


## 2026-10-02 — Viewer teardown and Mac sleep

Normal viewer teardown sends SIGTERM. SDL converted that signal into a quit event,
so the camera incorrectly recorded a user cancellation after a completed route.
The viewer now sets SDL_NO_SIGNAL_HANDLERS=1 before initialization, preserving
normal process termination while Escape and window-close still record a user stop.

The subsequent route stalled inside MPS inference and was correctly rejected as
an agent crash. The power log records maintenance sleep at 17:33:49 for 721
seconds during that attempt, followed by a dark wake at 17:45:50. The lid is now
open. The launcher uses macOS caffeinate to prevent ordinary idle display/system
sleep only while the run is active; it does not override lid closure or change
persistent power settings. The failed attempt remains in
`results/local-mac/20261002-173210/` with no readiness report.

The official additional map package was streamed into the dedicated CARLA app
after space became available. Every packaged file passed length and CRC checks,
and Town12 passed camera/control smoke. Task-generated native build caches were
removed after confirming the installed client uses system dynamic libraries; the
pinned wheel and source remain available.

Final delivered-launch validation after map installation and both lifecycle fixes
passed in `results/local-mac/20261002-182756/`: 100% completion, 293 model steps,
14.7 simulated seconds in 244.670 wall seconds. Normal teardown did not create
a user-stop marker; readiness was saved. No owned camera, model, Wine/server or
caffeinate processes remained afterward.

## 2026-10-05 — Savio GPU "rejection" was the wrong QoS, not missing access

**Expected (2026-10-01 entry above):** `ic_cdss170fall` has no usable GPU
partition; wait for support.

**Actual:** `sacctmgr -nP show assoc user=$USER format=Account,Partition,QOS`
lists the allowance on `savio3_gpu` with `a40_gpu3_ica`, `v100_gpu3_ica` and
`gtx2080_gpu3_ica`, and on `savio4_gpu` with `a5k_gpu4_ica`. The earlier jobs
asked for `savio_normal`, which these partitions only offer to other account
types. Typed `--gres` (`gpu:A5000:1`) and the per-type CPU ratio (4 per A5000,
8 per A40) are also required. `savio_lowprio` is not associated at all, so
`PRD.md` §17.2's lowprio fan-out plan does not apply to this allowance.

**Did:** filled `configs/cluster/savio.yaml` from the association list (A5000 by
default, A40 as the documented alternative) and built the Step 1 path:
`adapters/simlingo/setup_savio.py`, `run_savio.py` and `scripts/step1.sbatch`.
No GPU job has run yet.

**Lesson:** read the scheduler's own association table before concluding that
access is missing. "Rejected" without the rejection text was not evidence.

The same day, a Mac regression run after splitting `run_local.py` into the
shared `route_run.py` hung for 30 seconds inside the unchanged Sikarugir
launcher call, before any refactored code ran, while two 8 GB downloads were
streaming. An immediate rerun passed: `results/local-mac/20261005-150141/`,
route completed, 294 model steps, 0.0558x real time, only the unpenalized
minimum-speed checks. If the launcher timeout recurs, rerun before debugging.

## 2026-10-06 — Same route and seed does not reproduce the same rollout

**Expected:** synchronous CARLA with a fixed traffic-manager seed replays the
same drive, so repeated runs of route 26956 give identical control traces.

**Actual:** the five completed Mac runs of 26956 (2026-10-02 and 2026-10-05,
same config) see different camera pixels from the very first policy frame
(per-frame mean 105.889-105.949). Throttle is saturated early, which hides it
until step 16-20, when controls diverge; speed differs by up to 3 m/s at
the same step index later in the route. All five still completed the route in
293-295 model steps. The server starts the route on a different frame each time
(first frame 47-167), so warm-up length is one candidate cause. Another is
that the policy camera keeps CARLA's defaults: Bench2Drive's agent wrapper sets
only size and field of view, and 0.9.15 defaults to histogram auto-exposure,
motion blur 0.45 and post-processing on, all of which carry state across
frames. A first look favours rendering: against the 2026-10-02 18:27 run, the
first policy frame of four other runs differs in 1.2-4.8% of pixels, scattered
over the whole image and mostly by one or two intensity levels (at most 33 of 255,
in under 0.1% of pixels). A different world state would differ in patches. The
earliest run (2026-10-02 16:09) differs in 75% of pixels; not investigated.
By step 40 the drives have separated (13.6% of pixels differ by more than 8).

**Did:** nothing to the code. Recorded so that two things are planned for rather
than discovered: a closed-loop rerun is a new sample, not a replay, so efficacy
and reproduction tests (§9.1, Step 10) must be statistical over seeds; and
Step 3's determinism check has to replay *logged* inputs offline, which is what
`adapters/simlingo/replay_capture.py` does. Unchecked on Savio.

## 2026-10-06 — The Mac drives Bench2Drive far better than the paper says

**Expected:** a success rate near SimLingo's published 64.8% (Table 10, CoT
off) and a driving score near 84, with PRD §8's practical bar at DS ≥ 75.

**Actual:** the overnight sweep (`results/local-sweep/20261006-overnight/`, one
seeded route per scenario type, 31 of 44 run) scored 27 of 29 routes a success
(93.1%) with mean DS 97.1 (standard error 2.7). Under the paper's rate, 27 or
more of 29 has probability 0.0005. Per ability: Merging 8/10 (paper 54.0%),
Overtaking 5/5 (57.0%), Emergency Brake 9/9 (88.3%), Give Way 2/2 (53.3%),
Traffic Signs 11/12 (82.5%). The failures were route 28330, three vehicle
collisions after a left turn into traffic (DS 20.9), and route 3800, a brief
lane departure (DS 95.9).

What it hides: 10 of 31 routes stood still or crawled for 38+ simulated
seconds, and 8 only moved again when SimLingo's scripted stuck detector forced
throttle. Bench2Drive scores those as successes. Two stalled routes hit the
wall cap unscored: 2144 at 35 minutes, and 3457 at the 15-minute cap used in
the last half hour. Three
of the rescued stalls (1956, 23659, 25845), rerun at the end of the night,
stalled again at the same place for 40–41 seconds.

**Did:** nothing to the stack. Candidate explanations, none tested: this Mac
runs fp32 where published CUDA runs use bfloat16, which moves waypoints by up
to 18 cm on the frames checked; the Windows CARLA build renders differently;
chance. Step 2 on Savio is the comparison, and an fp32 arm there would
separate precision from platform. If Savio lands near the paper, do not
"fix" the Mac result; report both.

## 2026-10-06 — Imhaohao cannot push to the shared repository

**Expected:** `git push -u origin codex/carla-bringup` puts the branch on GitHub
so Savio can clone it.

**Actual:** HTTP 403. The Imhaohao GitHub account has no write access to
`Christopher-Vu/HondaResearchInstitute`.

**Did:** shipped the branch as a git bundle instead (`git bundle create`, `scp`
to `dtn.brc.berkeley.edu`, `git clone` from the file on Savio). It works but the
Savio copy goes stale with every new commit. Chris to add Imhaohao as a
collaborator.

**Resolved 2026-10-07:** the same push succeeded; Imhaohao now has write access.

## 2026-10-07 — First Savio GPU jobs: carla import fails on the node, and the dependency did not hold

**Expected:** `check_gpu.sbatch`, then `step1.sbatch`, then the 31-route array
`route_sample.sbatch` submitted with `SBATCH_DEPENDENCY=afterok:<step1>`, so the
array would only start if Step 1 passed.

**Actual:** the GPU check completed (3 s, RTX A5000 visible). Step 1 failed in
2 s at `import carla`: reading
`.runtime/policy-venv/lib/python3.10/site-packages/carla.libs/libz-7d499572.so.1.2.11`
returned "Cannot send after transport endpoint shutdown", a filesystem error
from the scratch file system, not a Python one. All 31 array tasks then ran
anyway and failed the same way in 1–5 s each, so the dependency set through the
`SBATCH_DEPENDENCY` environment variable was not applied. Cost was a few
GPU-minutes. `sacctmgr` shows the QoS allows 4 running jobs per user and 8 hours
of wall time (now in `configs/cluster/savio.yaml`).

**Did:** nothing on the cluster yet. Next: try `import carla` on a login node to
tell a bad file from a bad node; if the file is unreadable everywhere,
reinstall the carla wheel into the venv so its libraries are rewritten. `scripts/submit.sh` now forwards `--` options before the script to sbatch,
so the array is submitted with a real `--dependency=afterok:<step1>`.

## 2026-10-07 — The Mac ran out of battery an hour into the night run

**Expected:** the second local night run (13 remaining sample routes, then six
stall reruns) would finish by morning; the launcher's `caffeinate` keeps the Mac
from idling to sleep.

**Actual:** the Mac was on battery at 47%. It entered "Low Power Sleep" at 1%
at 01:58 (`pmset -g log`) and stayed asleep until 08:47. `caffeinate` blocks
idle sleep, not a flat battery. One route finished (24781); 3905 was cut off by
the sleep and 23918 failed on waking because its CARLA server was gone. Both
are set aside in `results/local-sweep/20261007-sleep-invalid.jsonl` and rerun.
Because 07:30 had passed by then, the sweep stopped starting routes and the
chain jumped to the reruns, which were stopped and reordered.

**Lesson:** check `pmset -g batt` says AC power before leaving a night run.

## 2026-10-07 — Bench2Drive scores a route whose scenario never ran

**Expected:** every Bench2Drive route plays its authored scenario.

**Actual:** route 23918 (Town13, InterurbanActorFlow) logged "Skipping scenario
'InterurbanActorFlow_1' due to setup error: Couldn't find an end position",
then drove the empty route and was scored 100, a success. `route_run.summarize`
already refused readiness for it, but `sweep_local.route_record` read the score
from `result.json` and counted it.

**Did:** `route_record` now marks such a run `scenario_skipped` and leaves it
unscored (tested); the stored record was rewritten. The setup error is a map
query, so it will likely recur on Savio, and the official 220-route score would
count it silently. Check every Step 2 log for "Skipping scenario".
