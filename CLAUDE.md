# Working conventions

## Orientation for a cold start

Read in this order. It takes ten minutes and prevents re-deriving settled things.

0. **`docs/STATUS.md`** — one page: current position, the active blocker, what is
   next. Start here; it is the only file that is kept current by hand.
1. **`PRD.md`** — the grounding document. It supersedes everything else. §13 is
   the step list; §16 is what is still open.
2. **`docs/steps/`** — one spec per step, with a done-condition. Find the current
   step and read its spec before touching code.
3. **`CONFLICTS.md`** — why things are the way they are. Consult before
   reopening any decision; several entries record reversals, so an argument may
   already have been had and settled.
4. **`docs/WHAT_BROKE.md`** — what has already gone wrong. Read before debugging
   anything that smells familiar.
5. **`docs/JOURNAL.md`** — what recent sessions did and why, in plain language.
   Skim the top few entries.

`docs/source/project-brief-original.md` is the original brief and
`upstream-99p/` is a vendored read-only copy of the 99p repo. Both are
provenance, not instructions.

## Precedence

`PRD.md` was reconciled from two prior planning documents on one rule: **design
decisions from the original brief, verifiable facts from the 99p handoff.** Any
divergence from either gets an entry in `CONFLICTS.md` with reasoning. Reversing
a prior decision means **updating** its entry, not deleting it — the audit trail
is the point.

## Commits

- **Commit frequently.** Small, scoped commits over large ones. Commit as work
  lands, not at the end of a session.
- **Curt, concise messages.** One line, imperative mood, lowercase. A body only
  when the *why* is not obvious from the diff.
- **No attribution lines.** No `Co-Authored-By`, no "Generated with" footer.

Good: `add ray back for rollout fan-out`, `fix sbatch directive placement`.
Bad: multi-paragraph rationale, trailing attribution, past tense.

## Don't over-code

The failure mode in this repo is writing code nobody asked for. A file that
exists because a spec mentioned it, a wrapper for a one-line command, a stub that
prints "not yet implemented" — all of that is cost with no benefit, and it has
already happened here once (`scripts/run_rollout.sh`, deleted).

Rules:

- **Write code when a decision is already made and the work is mechanical.**
  Scoring arithmetic, schema validation, a CI guard — yes. Scaffolding for a step
  that is blocked — no.
- **No stubs, no placeholder files, no "not yet implemented".** If it does not
  work, it does not exist. A spec in `docs/steps/` is how we record intent.
- **No abstraction before the second caller exists.** `PRD.md` §8.2 is explicit
  about this for the adapter interface, and it generalises: the interface you
  guess will be wrong in ways you cannot see until two real things use it.
- **No wrapper for something a person can type.** `submit.sh` earns its place
  because it reads config and refuses an unsafe submission; a wrapper around
  `pytest` would not.
- **Prefer a sentence in a doc over a script.** Most of what this project needs
  recorded is a decision or a finding, not an executable.
- **When the next move is ambiguous, say so and stop.** Do not resolve ambiguity
  by building something plausible.

Tests are not over-coding: they encode reasoning that would otherwise be lost.
But test behaviour we rely on, not coverage for its own sake.

## Keeping memory across sessions

`docs/STATUS.md` is the handoff. **Update it at the end of any session that
changes the answer** — the blocker, the current step, or what is next — before the
context is lost. Everything else is already durable: decisions in `PRD.md`,
reasoning in `CONFLICTS.md`, specs in `docs/steps/`, surprises in
`docs/WHAT_BROKE.md`, sequence in git.

If a session ends mid-task, say so in `STATUS.md` explicitly. An unfinished thing
that nobody wrote down is indistinguishable from a thing nobody started.

## Journal

`docs/JOURNAL.md` is the human-readable record of what each agent session did,
written for a person who was not there. **Add an entry before stopping any
session that changed something** — code, docs, cluster state, or a decision.

It is not another status file:

- `STATUS.md` is the present, rewritten each time. The journal is history:
  append-only, newest entry at the top.
- git says *what* changed. The journal says *why*, and what it means for the
  project.
- `WHAT_BROKE.md` holds surprises. The journal links to them, not repeats them.

Each entry:

- Headed with the date and a one-line title naming what the session was about.
- Readable cold: full sentences, plain words, no unexplained acronyms; define a
  term the first time it appears. Someone who skipped the session should finish
  the entry knowing what happened.
- Covers what was done and why, what was found (measured numbers, marked as
  measured), what was decided, and what was left unfinished.
- Links to commits, files and result folders instead of pasting them.
- A few short paragraphs or a short list. Longer detail belongs in a doc the
  entry links to.

Do not rewrite old entries except to fix a factual error. If later work reverses
something, say so in the new entry.

## Standing rules

- **Never state a target as a result.** The inherited documents are full of
  aspirational figures (">85% precision", ">80% failure reduction") that were
  never measurements. Mark unverified claims as unverified.
- **Cite only what has been verified.** `upstream-99p/docs/CITATION_AUDIT.md` is
  the evidence ledger; `docs/step0-trackA-findings.md` holds what was read
  directly from the PDFs. New citations get evidence first.
- **Log surprises in `docs/WHAT_BROKE.md` as they happen.** Reconstructing it
  later never works, and `PRD.md` §6 commits us to publishing it.
- **Nothing outside scoring code reads `gaps/sealed/`.** CI-enforced.
- **Recheck any deadline or model-roster fact older than two weeks** before
  acting on it. Several dates in the source documents had already passed.

## Before running anything

```bash
python -m pytest -q                        # no GPU needed
python scripts/check_sealed_imports.py     # sealed-key guard
python scripts/check_configs.py            # config hashes, unresolved TBDs
```

## Cluster

Compute is Savio, allowance `ic_cdss170fall`. **Login needs a PIN plus a rotating
6-digit code, so an agent cannot reach the cluster** — cluster work means handing
Chris a script to paste and reading back the output.

**Never hardcode a partition, QoS or GPU type.** All of it lives in
`configs/cluster/savio.yaml`. `scripts/submit.sh` reads that file and refuses GPU
submission while `gpu.available: false`.

## Configs

Every experiment is a YAML config under `configs/`, keyed by content hash
(`PRD.md` §6.2). Values prefixed `TBD-` are deliberate placeholders for things a
later step measures; `harness.config.require_resolved()` refuses to run while any
remain. Do not guess them.

## Two deliberate scoring subtleties

Both look like bugs and both have tests asserting them. Do not "fix" either:

- `jaccard(empty, empty) == 0`, not 1 — otherwise a method scores perfectly by
  emitting nothing.
- Precision divides by the axis budget M, never by the number of axes emitted —
  otherwise emitting one safe axis beats a full directive.

## Filesystem

Windows, case-insensitive. Filenames differing only in case are the same file:
writing `PRD.md` silently overwrote `prd.md` once. Check before writing a file
whose name differs from an existing one only by case. `.gitattributes` forces LF
on `.sh`/`.sbatch`/`.yaml`/`.py`, since CRLF breaks shebangs on Linux.
