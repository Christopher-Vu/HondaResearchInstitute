# What broke

Running log. Written as things happen, not reconstructed at the end — `PRD.md` §6
commits us to publishing this, and reconstructing it later never works.

One entry per surprise. Format: date, what we expected, what happened, what we
did. Dead ends count. "Turned out to be my typo" counts.

---

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
