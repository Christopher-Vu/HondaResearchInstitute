# Savio support email — send today

To: the Data Discovery program's Savio contact via
<https://datadisco.cdss.berkeley.edu/support>

Send this before anything else. The reply time is outside our control, and
answers 1 and 2 are half the input to `PRD.md` §16.2 (gap portfolio size).
Ask the program, not general Research IT — `ic_` allowance terms are set per
agreement.

---

**Subject:** GPU partition, SU rate and storage questions for `ic_cdss170fall`

Hello,

I'm an undergraduate on a Data Discovery project using the `ic_cdss170fall`
allowance, working on interpretability for an autonomous-driving policy with
99P Labs / Honda Research Institute. My account is registered under the project.

We're sizing a simulation campaign before we commit to it, and I couldn't find
the following in the program's Savio documentation. Could you point me to it or
answer directly?

1. **Which GPU partitions can `ic_cdss170fall` submit to?** I want to put the
   correct `--partition` in our job scripts rather than guess.
2. **What is the Service Unit charging rate for GPU jobs** on those partitions?
   Our workload is estimated in GPU-hours and I'd like to convert that to SUs
   against our allowance before scheduling it.
3. **Maximum wall time** for GPU jobs under the allowance.
4. **Storage quota, and where large data should live.** We expect roughly
   150 GB of intermediate arrays, and possibly a ~1 TB public dataset later.
5. **Is `savio_lowprio` available to an instructional allowance?** Our main
   workload is many short independent simulation runs, which preemption suits
   well — we'd rather use lowprio than normal if we can.
6. **Any practical cap on job-array width** we should design around.

Two smaller environment questions, if you happen to know:

7. **Is Apptainer/Singularity the supported container runtime** on GPU nodes?
   We need a CARLA 0.9.15 container and assume Docker isn't available.
8. **Can an OpenGL/Vulkan application render off-screen on a GPU node** with no
   display attached? CARLA needs GPU rendering headlessly, and whether this
   works determines whether Savio is the right home for this workload at all.

Happy to share our planned job shapes if that's useful.

Thank you,
Christopher Vu
christopher.vu@berkeley.edu

---

## Why each question is here

| # | Blocks |
|---|---|
| 1 | `scripts/run_rollout.sh` `--partition`. Step 1 cannot submit without it. |
| 2 | `PRD.md` §16.2 and §17.3 — the budget is in SUs, not GPU-hours. |
| 3 | Whether a 220-route × 3-seed run fits one job or needs checkpointing. |
| 4 | Step 3's activation store layout. |
| 5 | Step 4's fan-out design, and `PRD.md` §17.2. |
| 6 | Ray-vs-job-array fallback (`PRD.md` §11). |
| 7–8 | Step 1 stages 1.1 and 1.2. **8 is the most likely project-level blocker.** |

Log the reply in `docs/WHAT_BROKE.md` if any answer invalidates a plan
assumption — particularly 8.
