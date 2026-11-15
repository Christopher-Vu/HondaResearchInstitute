# Start prompt: third-model bring-up (paste into a fresh agent session)

You are bringing up a **third driving policy** on Fail2Drive for the HRI failure-discovery project, in the repo at
`C:\Users\CVuDev\desktop\work\hri`. Another agent is running the discovery-method loop on SimLingo at the same time.
**Your work must never slow that loop down.** The rules for that come first, below.

## Read first (about 15 minutes)

1. `CLAUDE.md`: conventions, git rules, Savio access, the agent channel.
2. `docs/STATUS.md`: the top three paragraphs.
3. `docs/prd-discovery-sprint.md`, all of it. §7 is your brief.
4. `docs/prd-fail2drive.md` and `docs/prereg-fail2drive.md` §1–2: how a model's gaps are classified from its own pool.
5. How TransFuser++ was brought up, which is your template:
   - `adapters/tfpp/tfpp_agent.py`;
   - the TF++ configs `configs/rollout/f2d-tfpp-smoke.yaml`, `f2d-tfpp-screen.yaml` and `f2d-test-tfpp-s10*.yaml`;
   - the journal entries that mention TF++ (`grep -n -i "transfuser\|tf++" docs/JOURNAL.md`);
   - `docs/WHAT_BROKE.md` entries on CARLA, Fail2Drive and venvs. Read those before debugging anything.
6. `src/harness/shards.py`: the shard contract. Your export must pass it, and the SimLingo test that holds an export
   to it is your model.

## Goal, with done-conditions

1. **Pick UniAD or VAD** from Bench2DriveZoo, whichever is easier to run on Fail2Drive's CARLA 0.9.15 build.
   - Check its checkpoint against the scores in Fail2Drive's paper.
   - Record the choice and the check in the journal, with what you read.
   - **Done when** a smoke route drives and its score is within the paper's range, or you have written down why it
     cannot be.
2. **Adapter and hooks.** Write `adapters/<model>/`, copying TF++'s layout, with activation hooks at several layers
   and sites. Capture per frame, mean-pooled, at **every layer you can afford**, the way SimLingo's shards keep all 24
   layers. Save ego speed and position per frame. **Also save a downsampled front-camera frame every captured step**
   (for example 256 px JPEG): the SimLingo and TF++ pools have none, and the caption methods need them.
   - **Done when** a smoke shard passes the shard contract test.
3. **One-seed screen.** Drive every Fail2Drive pair at one seed, as `f2d-screen-full.yaml` did for SimLingo.
   - **Done when** `routes.jsonl` and the shards exist, and the screen's results are in the journal.
4. **Full pool.** If the screen works, drive the 6-seed test pool (seeds 101–106), with the same configs as
   `f2d-test-tfpp-s10*.yaml`.
5. **Classify gaps** by the pre-registered rule (prereg §1–2) on this model's pool only, and write `b4-split.json`.
   No method reads this pool before that file exists.
6. **Fast-loop cache.** Run the same per-route cache pass the method loop uses: route mean, approach-window mean and
   early-route mean, for every layer and site, in one file. A frozen method can then be scored on this model in
   minutes. The cache script is `docs/research/experiments/f2d-dev-simlingo/cache_pool.py`: run it, do not edit it.

## Non-interference rules (the method loop always wins)

- **GPU priority.** Submit every job with `--nice=10000`, for example
  `bash scripts/submit.sh gpu_a40 --nice=10000 ...`. Slurm then starts the method loop's pending jobs ahead of yours,
  while yours still use idle capacity, overnight included. Before each submission, run
  `squeue -u christophervu -o "%i %j %T"`. If a method-loop job (name starting `f2d-dev` or `m0`) is **pending**, hold
  yours until it starts.
- **SSH.** Savio allows one session per connection, so you and the other agent share one connection. If a command
  returns "Session open refused by peer", wait 30 s and retry, up to 5 times. Never hold a session open for long:
  no interactive shells, no `du` on big trees, no `tail -f`.
- **Files you never edit:**
  - `docs/research/experiments/f2d-dev-simlingo/`;
  - `docs/prereg-fail2drive.md`;
  - `CONFLICTS.md`, except a new entry of your own;
  - anything under `src/discovery/` or `src/baselines/`.
- **Files you may edit:** `adapters/<model>/`, `configs/rollout/f2d-*-<model>*`, and new files of your own. Append
  your own entries to `docs/JOURNAL.md` and `docs/WHAT_BROKE.md`, and add one STATUS paragraph headed "Third model".
  Run `git pull --rebase` before each commit, because the other agent pushes main too.
- **Data you never read:**
  - `gaps/sealed/`;
  - `results/savio/f2d-dev/` (the method loop's outputs);
  - TransFuser++'s test-pool shards.
- **Disk:** write under `results/savio/f2d-*-<model>/`, and keep scratch use reported.

## Working rules

- Git: Christopher-Vu account, curt lowercase one-line messages, no attribution lines, push main as you go. Never
  commit `.claude/` or `chris-plans/`.
- Read issue Christopher-Vu/HondaResearchInstitute#9 at session start, and post a `heads-up` before Savio arrays.
  The repo is public: post nothing sealed. If `gh` is not logged in, tell Chris to run `! gh auth login`.
- Budget: no SU cap (Chris, 2026-11-14). Report the SU used per job: sacct GPU hours × 29.36.
- Log every surprise in `docs/WHAT_BROKE.md` as it happens.
- When Chris says he is ending a session, tell him what you have queued, and whether the GPUs will sit idle.
- Stop and ask Chris only for a choice that is his to make. Otherwise keep going.
