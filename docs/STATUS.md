# Status

One page. Where the project is, what is blocked, what is next. **Update this at
the end of any session that changes the answer**, before the context is lost.

Last updated: 2026-10-01

---

## Current position

**Step 0 — Track A done, Track B blocked.**

Track A (paper facts) is complete: six papers read, findings in
`docs/step0-trackA-findings.md`, applied to `PRD.md`. Track B (Savio access) is
blocked on cluster administration.

**Step 1 cannot start.** It needs a GPU partition.

## The blocker

Savio login works (user `christophervu`, allowance `ic_cdss170fall`), but there is
no usable GPU partition: `savio2_gpu` is retired, `savio3_gpu` and `savio4_gpu`
are rejected. A support request is open — the text is in
`docs/savio-support-email.md`.

When the reply arrives: set `gpu.available`, `gpu.partition`, `gpu.qos` and
`gpu.gres` in `configs/cluster/savio.yaml`. Nothing else needs editing.

Separately, **an agent can never reach the cluster** — login requires a PIN plus
a rotating 6-digit code and `ic_` allowances forbid unattended keys. Cluster work
means handing Chris a script to paste and reading back the output. Two such
scripts exist: `scripts/savio_recon.sh` (read-only recon) and
`scripts/check_gpu.sbatch` (GPU smoke test, also probes off-screen rendering).

## Built so far

All GPU-free, 45 tests passing.

| Piece | Where |
|---|---|
| Scoring, metrics, harness-validity check | `src/harness/scoring.py` |
| Data contracts (axis card, directive, gap) | `src/harness/schema.py` |
| Config hashing + placeholder detection | `src/harness/config.py` |
| B1 random baseline | `src/baselines/random_baseline.py` |
| Sealed-key CI guard | `scripts/check_sealed_imports.py` |
| Cluster indirection | `configs/cluster/savio.yaml`, `scripts/submit.sh` |

Building the scoring layer before any rollout exists is deliberate, not
opportunistic: `PRD.md` §9.1 wants it frozen and hash-committed before the test
pool is generated.

## Next, if still blocked

`docs/steps/gpu-free-queue.md`, in order. The top item is **B7's gap-signal
definition** (`PRD.md` §16.9, `CONFLICTS.md` C18) — memorized-feature
concentration as a gap signal is our construction, not Dr. VLA's, so it needs a
written definition before Step 6 or B7 is not a fair baseline. Writing it before
we have seen any activations is also the honest order.

## Next, when unblocked

`docs/steps/01-smallest-rollout.md`. One route, not the benchmark. The five
stages are ordered so each failure is cheap to attribute; stage 1.2 (off-screen
rendering) is the most likely project-level blocker, and if it fails that is a
replan toward NRP rather than a debugging session.

## Open questions worth remembering

- **Event-grounded SAEs (arXiv 2605.17204)** has not been read. Needed for the
  related-work paragraph and as the causal-check template. Due before Step 9.
- **Dr. VLA's repo has no LICENSE file.** Ask the authors before vendoring any of
  it; reimplement from the paper if they decline.
- **`d` (hidden size) is still unconfirmed.** The handoff says 896; the SimLingo
  paper does not state it. Every storage estimate and the SAE dictionary size
  scale with it. Read it off the loaded config at Step 1.
- **The gap portfolio size** (`PRD.md` §16.2) is budget-bound and cannot close
  until the rollout throughput measurement and the SU rate both exist.
