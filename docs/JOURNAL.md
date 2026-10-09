# Journal

What each agent session did and why, written for someone who was not there.
Newest entry first. Rules for writing entries are in `CLAUDE.md` under "Journal".

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
waypoints by a median 8.0 cm, with 58 of 60 frames within 57 cm. Two frames
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
