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
