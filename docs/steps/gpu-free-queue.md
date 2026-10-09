# GPU-free work queue

What can be built while Savio GPU access is blocked. Everything here runs on a
laptop: no GPU, no cluster, no partition name, no rollouts.

**Why this is not filler.** Most of it is work that has to happen anyway, and
some of it is better done now. The scoring layer in particular wants to be
frozen and hash-committed *before* the test pool exists (`PRD.md` §9.1), so
building it during a GPU block is the correct order, not a consolation prize.

**Standing constraint:** nothing here may assume a GPU model or a partition
name. Cluster facts live in `configs/cluster/savio.yaml` and are read, never
hardcoded.

---

## Done

### ✅ Scoring and metrics · `src/harness/scoring.py`
The headline metric, testable on synthetic data. Hungarian assignment over all
gaps at once, per-tier recall, precision@M dividing by the budget, mean best
Jaccard, decoy hit rate, validated precision, and the §13.1 harness-validity
check. 32 tests in `tests/`.

Three behaviours worth knowing, because each is a trap avoided:
- `jaccard(∅, ∅) == 0`, not 1 — otherwise a method scores perfectly by emitting
  nothing.
- One Hungarian assignment, not greedy per-gap best match — otherwise one broad
  axis gets credited for two gaps.
- Precision divides by M, never by the number of axes emitted — otherwise
  emitting a single safe axis beats a full directive.

### ✅ Data contracts · `src/harness/schema.py`
Axis card, directive, gap. A directive that does not validate cannot enter
scoring, so a malformed baseline fails loudly instead of scoring zero and
looking like a real negative result. Empty `name` or `description` is a hard
error: an axis without them is a cluster, not a discovery (`PRD.md` §8.3).

### ✅ Sealed-key CI guard · `scripts/check_sealed_imports.py`
The mechanical half of what blinding used to buy socially. Catches both import
and string-path leaks under `discovery/`, `baselines/`, `gate/`. Tested by
injecting real leaks. Docstrings mentioning the rule are exempt — false
positives train us to ignore the checker.

### ✅ Config plumbing · `src/harness/config.py`, `scripts/check_configs.py`
Content hashing (`PRD.md` §6.2) and `TBD-` placeholder detection, so a run
cannot silently proceed on a placeholder.

### ✅ Cluster indirection · `configs/cluster/savio.yaml`, `scripts/submit.sh`
Single place any partition or GPU type is named. `submit.sh` refuses GPU
submission while `gpu.available: false` and prints why.

---

## Next, in value order

### 1 · B1 random baseline, end to end
The only baseline that needs no policy at all: draw M random subsets of failing
rollout ids, sized from the primary method's axis sizes. Fully implementable now,
and it exercises the whole scoring path with a real method object rather than a
test fixture.

Deliverable: `src/baselines/random_baseline.py` plus tests, emitting a valid
`Directive`. Closes a real line item from `PRD.md` §9.3.

### 2 · B7's gap-signal definition · `PRD.md` §16.9, `CONFLICTS.md` C18
**Done 2026-10-09:** frozen in `docs/steps/b7-gap-signal.md` before any activation was opened.

**Must exist before Step 6 or B7 is not a fair baseline.** Dr. VLA never proposes
memorized-feature concentration as a gap signal — that construction is ours, so
we owe it a written definition: how concentration is measured, over what
partition, how it ranks into axes.

Writing it now, before we have seen any activations, is also the honest order:
we cannot tune it to win or lose after the fact.

### 3 · Synthetic end-to-end dry run
Generate a fake rollout corpus with known planted structure, run B1 and a stub
discovery method through scoring, and produce the actual report artifact. This
smokes out the whole pipeline's plumbing and gives us the results-table format
before real data exists.

It also answers a question we should not discover late: what does the scoring
report look like when a method recovers nothing? The negative-result paper needs
that table to be legible.

### 4 · `harness/PREREGISTRATION.md` skeleton
The §13.1 go/no-go rule, the efficacy thresholds, the gate AUROC threshold, the
primary-method declaration. **The entire value of pre-registration is that it is
written before the numbers exist**, so drafting it during a GPU block is exactly
right. Fill the thresholds now; leave only the primary-method choice open, since
that legitimately depends on the Step 4 sweep.

### 5 · Gap predicate schema and the public practice gaps
**Done 2026-10-09:** `gaps/practice/practice_v1.yaml`, matched by `src/harness/predicates.py`; reasoning in `docs/steps/04-dev-pool-and-layer-sweep.md`.

The predicate DSL from `PRD.md` §9.1, plus the two public practice gaps that live
in the dev pool. Needs no rollouts — only a schema and a matcher that can be
tested against synthetic metadata.

Keep sealed predicates out of this; only the practice gaps are public.

### 6 · Describability gate scaffolding
The two-model protocol with its shuffle control (`PRD.md` §9.2). The prompt
templates, the held-out split logic, and the AUROC computation are all
testable on synthetic descriptions. The actual VLM calls need NRP, not Savio,
so this may be runnable even while Savio is blocked.

### 7 · Results database schema
Config hash → run record → metrics. `PRD.md` §6.2 requires every paper number to
be regenerable from a query. Pure schema work.

---

## Deliberately not now

- **Anything touching the SimLingo checkpoint.** It needs ~2 GB of download and,
  for a forward pass, ideally a GPU. The architecture facts it would resolve
  (`PRD.md` §16.11) are Step 1 items. If a non-Savio GPU appears, this jumps the
  queue, since it de-risks Step 3's hook placement.
- **The adapter interface.** `PRD.md` §8.2 says explicitly to build it by
  refactoring after SimLingo works. Designing it now would be the abstraction
  mistake the brief warned about.
- **Ray orchestration.** One route does not need it and we cannot test the
  Slurm interaction without a partition.
- **Container work.** Needs the cluster.
