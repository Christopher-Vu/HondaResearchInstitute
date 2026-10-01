# Unsupervised Failure-Axis Discovery for Driving Policies

UC Berkeley CDSS Data Discovery × 99P Labs / Honda Research Institute USA.
Chris and Jerry, mentored by Ryan Lingo.

## The one-sentence version

When a driving policy fails, you want to know what data to collect next. Everyone
answers that by writing a list of suspected failure factors and testing against
it — which can only find failures somebody already thought of. We derive failure
axes from the policy's own internal representations with no list, score them
against gaps we planted and sealed in advance, and then generate data along a
discovered axis to show the failure closes.

## Start here

| Document | What it is |
|---|---|
| **[`PRD.md`](PRD.md)** | The grounding document. Read §1–§5 for the argument, §9 for the method, §13 for the steps. |
| **[`CONFLICTS.md`](CONFLICTS.md)** | Every disagreement between the two source documents and what we decided. Read when you want to know *why* something is the way it is. |
| **[`docs/steps/`](docs/steps/)** | One spec per step. Currently: [Step 0](docs/steps/00-ground-the-facts.md). |
| `docs/WHAT_BROKE.md` | Running log of what broke. Written as it happens, not reconstructed. |
| `upstream-99p/` | The `Imhaohao/99p` repo as pulled at `ad3932f`, read-only reference. Its `docs/CITATION_AUDIT.md` is the evidence ledger behind most facts in the PRD. |

The original project brief is kept for provenance at
[`docs/source/project-brief-original.md`](docs/source/project-brief-original.md)
(it started life as `prd.md`; it lives under a distinct name because Windows
filesystems are case-insensitive and `prd.md`/`PRD.md` collide). `PRD.md`
supersedes it.

## How this document set came to be

Two independent planning documents existed: the project brief (`prd.md`) and the
99p repo's `MASTER_HANDOFF.md`. They were the same project at different levels —
the brief had the sharper scientific argument, the handoff had verified facts and
better execution machinery, and the handoff was partly a review *of* the brief.

`PRD.md` reconciles them on one rule: **design decisions from the brief, verifiable
facts from the handoff.** Where that rule was overridden, `CONFLICTS.md` says so
and why.

## Where things stand

Step 0 — grounding the facts and getting onto Savio. Nothing is built yet, and
that is correct: several numbers the plan rests on have not been read out of a
paper by anyone on this team, and two of them would change what we build.

## Reading it out loud

The PRD is written to be talked through rather than skimmed, so if you are going
over it in voice mode, these are the threads worth pulling:

- **§3.1 and §4.1 together** — the enumeration argument, and the one framing
  mistake that would cost us credibility with a reviewer immediately.
- **§5** — the claim, and the four distinct ways it can fail. Only one of them
  leaves us with nothing.
- **§9.1** — gaps, and why "delete the training data and retrain" is a trap.
  This is the biggest change from the brief and the reasoning is the interesting
  part.
- **§11** — what we build versus what we take, including an honest list of the
  machinery that is *chosen* rather than necessary. Three things got cut here.
- **§13.1** — the go/no-go rule, written down before we see any numbers, which
  is the whole point of writing it down.
- **§20** — the risks, in rough order of how likely they are to actually bite.

## Standing rules

- Never state a target as a result. The inherited documents are full of
  aspirational figures (">85% precision") that were never measurements.
- Cite only what has been verified. New citations get evidence first.
- Every experiment is a committed config; every number traces to a config hash.
- Nothing outside scoring code reads `gaps/sealed/`. CI enforces it.
- Recheck any deadline or model-roster fact older than two weeks before acting
  on it.
