# SimLingo setup — scoped brief for a collaborator

**Status:** open for work. Lands as a PR; review before merge.
**Relates to:** `PRD.md` §8.2 (adapter), `docs/steps/01-smallest-rollout.md`
(Step 1, which this unblocks part of).

Read `docs/STATUS.md` and `CLAUDE.md` first — ten minutes, and it prevents
re-deriving things that are already settled.

---

## The situation you are walking into

> **Superseded 2026-10-05:** the GPU block below was the wrong QoS, not missing
> access, and the closed-loop route now runs on a Mac and is built for Savio.
> Current state: `docs/STATUS.md`.

**We have no usable GPU partition.** Savio login works, but the allowance
`ic_cdss170fall` has only `savio2_gpu`, which is retired; `savio3_gpu` and
`savio4_gpu` are rejected. A support request is open and unanswered.

So **the closed-loop part of SimLingo setup cannot be finished right now**, by
anyone. That is not a reason to avoid the work — it is a reason to be clear about
which half is blocked, so you do not burn time discovering it.

What is genuinely available without a GPU partition is a surprising amount: the
checkpoint loads on CPU, the architecture facts we need can be read off the
config, and the container can be built and tested locally.

## Highest-value thing you could do

**Read the architecture off the loaded SimLingo checkpoint and write it down.**

This closes `PRD.md` §16.11, it needs no GPU, and three downstream estimates are
currently resting on an unverified number:

- **`d`, the hidden size.** The 99p handoff says 896. The SimLingo paper does not
  state it. **Every storage estimate in `PRD.md` §12.1 and the SAE dictionary size
  in §12.2 scale with this number**, and the SAE expansion ratio is 1 (confirmed
  from Dr. VLA), so the dictionary *is* `d`. If `d` is not 896, several numbers in
  the PRD are wrong.
- **Decoder layer count.** Handoff says 24.
- **Where the waypoint query tokens `q_p` and `q_w` live**, and which module reads
  them. This is the primary activation hook site for Step 3, and finding it now
  while you are already inside the model saves a second pass.
- **Checkpoint SHA256.** Every rollout record carries it.
- **Which Bench2Drive version the repo targets.** v0.0.3 and v0.0.4 numbers are
  not comparable, and Step 2's pass/fail threshold depends on knowing which.

Write the answers into `configs/rollout/step1-single-route.yaml`, replacing the
`TBD-STEP1` placeholders. `python scripts/check_configs.py` lists what is still
unresolved.

Checkpoint: `RenzKa/simlingo` on Hugging Face. Apache-2.0 code; note the
*dataset* is Wayve non-commercial, so do not redistribute data.

## Also valuable, also GPU-free

**The container.** CARLA 0.9.15, plus the SimLingo agent. Two things worth
knowing before you start:

- Savio will almost certainly require **Apptainer/Singularity, not Docker** — HPC
  sites disallow Docker because it needs root. If a CARLA image exists for
  Fail2Drive or Bench2Drive, converting it beats building from scratch.
- Fail2Drive ships a **custom CARLA build**; Bench2Drive expects stock 0.9.15. If
  those differ, record which one the container has. It matters at Step 10.

**Off-screen rendering is the thing we are most worried about.** CARLA needs to
render headlessly on a GPU node with no display. `-RenderOffScreen` first, then
`-opengl`, then `xvfb-run`. If you can establish on *any* GPU — yours, a lab
machine, Colab, anything — that the container renders off-screen and a client can
read a **non-black** camera image, that is genuinely de-risking. Check the pixel
values, not just the array shape: a silently black camera feed produces a policy
that drives badly for reasons that cost a week to attribute.

## Please do not

These are not territorial; each has a specific reason.

- **Do not design an adapter interface or an abstract base class.** `PRD.md` §8.2
  says build it by refactoring after one policy works. Keep
  `adapters/simlingo/` concrete and specific. Generalising is Step 11.
- **Do not touch `src/harness/`, `src/baselines/`, or `tests/`.** That is the
  scoring layer; it is finished, tested (45 tests), and intended to be frozen and
  hash-committed before any test pool exists (`PRD.md` §9.1). If you think it is
  wrong, say so rather than editing it — two of its behaviours look like bugs and
  are deliberate, and `CLAUDE.md` lists them.
- **Do not hardcode a partition, QoS or GPU type anywhere.** All of that lives in
  `configs/cluster/savio.yaml`. `scripts/submit.sh` reads it.
- **Do not train or fine-tune on anything from Fail2Drive** — routes, scenario
  definitions or assets. It is strictly a held-out test set and this is a hard
  rule from its authors (`PRD.md` §4.7). Evaluating on it is fine; using its
  CARLA build and authoring toolbox is fine.
- **Do not edit `PRD.md` or `CONFLICTS.md` to change a decision.** Raise it
  instead. Correcting a *fact* with a reference is welcome — several PRD numbers
  are explicitly waiting for exactly that.
- **Do not commit large binaries.** Checkpoints, datasets, rollouts and
  activations are gitignored. Keep manifests, not blobs.

## Conventions

- Commit frequently, small scoped commits, one-line lowercase imperative
  messages, no attribution footers.
- Work on a branch, open a PR.
- Before pushing: `python -m pytest -q`, `python scripts/check_sealed_imports.py`,
  `python scripts/check_configs.py`. CI runs all three.
- Log anything surprising in `docs/WHAT_BROKE.md` as it happens, including dead
  ends. `PRD.md` §6 commits us to publishing what broke, and reconstructing it
  later never works.

## What "done" looks like

There is no single done condition here, which is deliberate — the GPU block means
partial progress is the expected outcome. Any one of these is a useful PR:

1. The architecture facts, written into the config with the placeholders removed.
2. A container that starts CARLA and accepts a client connection.
3. Evidence that off-screen rendering works, with a non-black camera frame.
4. A documented failure: "off-screen rendering does not work on X because Y" is
   genuinely valuable, because it is the trigger for replanning toward NRP rather
   than Savio for rollouts.

Partial is fine. Write down where you stopped and what you learned.
