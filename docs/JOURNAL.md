# Journal

What each agent session did and why, written for someone who was not there.
Newest entry first. Rules for writing entries are in `CLAUDE.md` under "Journal".

---

## 2026-10-06 — Getting the code and model onto Savio for the first time

*Session in progress; this entry will be updated before it ends.*

The goal tonight is Step 1: the first real driving run on Savio, Berkeley's
computing cluster. It answers one question the whole budget depends on — how
fast the simulator runs on their GPUs — and it uses about 1–1.5 of the 8
GPU-hours available tonight. Every earlier run happened on the Mac.

**The code could not be pushed to GitHub.** The account this Mac uses
(Imhaohao) does not have write access to `Christopher-Vu/HondaResearchInstitute`,
so GitHub refused the push with a permission error. Instead, the branch was
packed into a single file (a *git bundle*, 33 MB, ending at commit `857ec95`),
uploaded to Savio's file-transfer machine, and cloned from there. Chris needs
to add Imhaohao as a collaborator before the normal push route works.

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

**Left to do:** submit the GPU check (`scripts/check_gpu.sbatch`), then the
one-route run (`scripts/step1.sbatch`), and record the measured speed and memory
use.
