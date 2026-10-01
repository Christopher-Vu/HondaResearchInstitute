# Conflict log

Every place `prod.md` (the brief) and `upstream-99p/docs/MASTER_HANDOFF.md` (the
handoff) disagreed, what `PRD.md` does about it, and why. Kept so that nobody
re-opens a settled question, and so that any decision can be reversed knowingly.

**Precedence rule:** design decisions from the brief, verifiable facts from the
handoff.

Status values: **applied** (handoff correction adopted), **kept** (brief's
position retained), **merged** (both contributed), **deferred**, **open**.

---

## A. Factual corrections — handoff wins

### A1 · Compute platform · merged
The brief built §17 entirely on Savio under `ic_cdss170fall`. The handoff said
primary compute is NRP Nautilus and that Savio needs a faculty allowance the team
may not have.

**Resolution:** Savio is primary — Chris's account is registered under the
project, so the handoff's doubt is resolved by fact on the ground. NRP is the
documented fallback and the home for the describability model. The handoff's
compute *sizing* assumptions were written for NRP hardware, so they do not
transfer; the brief's four unresolved Savio questions (partition names, SU rate,
wall time, storage quota) are now **more** load-bearing, not less. `PRD.md` §17.

### A2 · Venue deadlines · applied, restructured
The brief said "December, no venue locked in." The handoff's audit found AAAI-27,
ICRA 2027, ICLR 2027 and NeurIPS 2026 deadlines had **already passed**, and that
IEEE IV (mid-Nov) and RSS Stage 1 (early Dec) were the live archival options.

**Resolution:** facts applied, but reframed as a **ladder** (`PRD.md` §15) rather
than a single target, per your instruction to publish as results land. Leaning
toward the handoff's dates. Every date carries a recheck warning.

### A3 · Reproduction bar · applied
The brief set the target at SimLingo's published Bench2Drive DS 85.1. The handoff
found the only public reproduction attempt reached **DS 75.5** (one user, 219
routes, configuration unconfirmed, no maintainer reply) and set the practical
bring-up bar at DS ≥ 75.

**Resolution:** bar is DS ≥ 75; published numbers listed as reference with the
Bench2Drive version attached, since v0.0.3 and v0.0.4 are not comparable.
`PRD.md` §10.1. This is a significant softening and it is the honest one.

### A4 · Fail2Drive identity · applied
Brief: "arXiv 2604.08535, Tübingen, 200 routes in Town 13, 17 new scenario
classes." Handoff: same arXiv ID, venue **IROS 2026**, 100 route *pairs*, 17
unseen scenarios, **30 novel assets**.

**Resolution:** these mostly agree — 100 pairs is 200 routes. Venue and asset
count added. `PRD.md` §4.7.

### A5 · RoboART venue and description · applied
Brief treated it as an arXiv preprint and wrote that a "Gemini VLM critic filters
four candidate edits per input." Handoff: **CoRL 2025**, PMLR 305:1615–1635;
RoboART is the pipeline name, not the title; 12 author-chosen conditions that are
levels of a few factors; **no weather**; no public code.

**Resolution:** corrected. The brief's framing warning — that RoboART already
reads policy embeddings, so the axis is *enumerated list vs. unsupervised
discovery* — is **kept verbatim in spirit** because it is the single most
important positioning point in either document. `PRD.md` §4.1.

### A6 · RESample citation · applied
Brief and the repo bibliography both had this wrong in different ways. It is
arXiv 2510.17640, a preprint with no acceptance found — not ICRA 2024.
Still cut as a baseline, for the brief's original reasoning. `PRD.md` §4.5.

### A7 · Motivating case study · applied, with a flag
The brief's §3.2 leaned on a specific Fail2Drive result: SimLingo's score falling
98.50 → 19.68 with collisions in 87% of episodes, and a named mechanism (the
language-action module hallucinating a vehicle-shaped lead actor). The audit
confirms Fail2Drive and SimLingo's aggregate numbers but **not** that
per-scenario figure or that mechanism.

**Resolution:** `PRD.md` §3.2 rewritten around the verified aggregate numbers
(HM 80.9 → 62.2, Behavior −64.2%) and carries an explicit **unverified** block.
The specific figures are Step 0 homework. The brief's *argument* — that the
failure is a conjunction no list contains — is untouched and still works.

### A8 · Dr. VLA numbers · applied as flag
The brief quoted LOO accuracy 100%/96.7%, 95-of-120 features interpretable
(79.2%) vs 30% for neurons, 0/40 after ablation, six seeds. The audit confirms
the paper's identity but not these figures.

**Resolution:** marked unverified, qualitative claims kept. Step 0. `PRD.md` §4.3.

### A9 · Missing prior art · applied
The brief omitted **event-grounded SAEs** (Jin et al., arXiv 2605.17204) — the
closest method precedent in the literature — and **CUPID** (CoRL 2025).

**Resolution:** both added. `PRD.md` §4.4, §4.6. CUPID earns its paragraph for a
sharp reason: attribution can only rank data that is *present*, and a planted gap
is absent data. That is a clean statement of why this is not an attribution
problem.

### A10 · Minimum-speed infraction, hard braking, failure definition · applied
The brief had no single definition of "failure." The handoff supplies one and two
traps: Bench2Drive excludes the minimum-speed infraction from its scores, and
hard deceleration must not be a failure label because correct emergency braking
would then count against the policy.

**Resolution:** one definition, used everywhere. `PRD.md` §12.4.

### A11 · Open-loop evaluation · applied
Added the handoff's evidence for closed-loop-only evaluation: a model averaging
0.29 m L2 on nuScenes scores **0% success** in closed loop on Bench2Drive, and
~74% of nuScenes is straight driving. `PRD.md` §12.4.

### A12 · CoT off · applied
New decision not in the brief: run SimLingo with commentary and chain-of-thought
**off** in the main campaign. Published difference is within noise (84.41 ± 1.76
vs 85.07 ± 0.95) and it removes a text-generation pass per step. CoT-on is an
ablation. `PRD.md` §10.1.

### A13 · SimLingo architecture facts · applied
Qwen2-0.5B, 24 layers, hidden size 896 (to confirm from config); LoRA r = 32,
α = 64; InternVL2-1B ≈ 1B not 800M. Storage arithmetic follows from d = 896.
`PRD.md` §9.2, §12.1, §12.3.

---

## B. Design decisions — brief wins

### B1 · "What we build vs. what we take" · kept
The handoff has no equivalent section. The brief's §11 — including the explicit
admission of which machinery is *chosen rather than scientifically necessary* —
is the best thing in either document and is kept as `PRD.md` §11, extended to
cover the new borrowings.

### B2 · The enumeration argument · kept
`PRD.md` §3.1 and §4.1 keep the brief's framing, including the warning not to
write "internals versus behavior." Strictly better than the handoff's softer
positioning sentence.

### B3 · Tool/experiment separation · kept
The brief's §8 — the tool is data-in/directive-out, generation is how *we*
validate and is not part of what ships — has no handoff equivalent and is what
makes the artifact citable. Kept whole, with the output schema extended to carry
the generality, causal and gate fields the handoff's axis card had.

### B4 · Retrospective validation mode · kept
Brief-only (§8.4). The answer to "how does a user without a simulator falsify a
directive." Kept.

### B5 · Adapter interface, and refusing to design it early · kept
Brief-only, including the instruction to build it by refactoring *after* SimLingo
works. Kept, and it is why Step 11 is near the end.

### B6 · The second paper · kept
Brief-only §19. Kept verbatim in substance.

### B7 · Run the dangerous baseline early · kept and strengthened
The brief's instinct — run rollout-free activation statistics in October, not
November, because if it wins the compute story collapses — is kept and made
structural: it is **Step 6**, before the corpus is built, with an explicit stop
condition. `PRD.md` §9.3 B7, §13.

### B8 · Interestingness-sampler confound · kept
A real catch the handoff does not address as such. Relevant to Mode A only, so it
travels with the deferred mode. The audit adds detail: withholding means
filtering route directories, and VQA/commentary/dreamer labels leak the withheld
concept. `PRD.md` §9.1.

### B9 · Non-goals · kept, extended
The brief's §18 list kept, plus the handoff's "never state a target as a result"
rule, which exists because the inherited documents are full of aspirational
figures presented as findings.

---

## C. Substantive changes — reasoned, reversible

### C1 · Gap planting: Mode A → Mode B · applied · **biggest change**
The brief assumed withholding plus re-fine-tuning, and made delete-vs-regenerate
its blocking open decision. The handoff's correction: **withheld data does not
reliably cause failures, because policies generalize.** A sealed key can name a
gap where performance is normal; discovery correctly finds nothing; the headline
number then measures the planting procedure. Silent failure.

**Resolution:** Mode B (novel-by-construction, released checkpoint, ~0 GPU-h for
planting) is the default. Mode A is documented as the gold standard and deferred
to a strengthening experiment. The **efficacy check** applies in both modes and is
the real fix. `PRD.md` §9.1.

Consequences: the brief's open decision #1 (fine-tune cost in SUs) stops blocking;
#2 (delete vs regenerate) travels with Mode A; #3 (sampler distortion) likewise.

### C2 · Efficacy check and decoys · applied
Not in the brief at all. A candidate becomes a gap only on ≥20pp uplift, ≥2×
ratio, Fisher p < 0.01, ≥30 rollouts — with the number of candidates tried
reported, and re-confirmation at scoring. Decoys added so "novelty" cannot
masquerade as "failure." `PRD.md` §9.1.

### C3 · Baselines: 3 → 7 · applied
The brief had three and, per the handoff's correction #17, dropped two the team
had previously mandated (Random, Human taxonomy) plus two reviewers will ask for
(input-embedding, detector-embedding). Now B1–B7 with one optional, each tied to
the specific objection it closes. `PRD.md` §9.3.

### C4 · Describability: human raters → automated gate · applied
The brief specified sampling axes, rendering top episodes, and a human rater
labelling interpretability. The handoff's objection: unscalable, and reviewers
read it as cherry-picking.

**Resolution:** automated two-model gate with a held-out AUROC ≥ 0.70 threshold
and — the load-bearing part — a **description-shuffle control whose pass rate is
the gate's measured false-positive rate.** Without it a gate that passes
everything looks like a gate. Human spot-check retained as sanity, not as metric.
`PRD.md` §9.2.

### C5 · Outcome tree re-tiered · applied
The brief's worst case was "axes not recoverable." The handoff demotes that to
middle and makes **"harness invalid"** the new worst case.

**Resolution:** adopted, because it is right — a negative result about probing is
publishable; a broken measuring instrument is not. This is also why validity is
tested first and cheaply. `PRD.md` §5.

### C6 · Action-residual orthogonalization · applied
The brief *identified* the risk (holding out "night rain" may separate for
trivial pixel reasons). The handoff supplies the fix: regress action-query states
on pooled visual tokens, keep the residual. Note the corollary — residualized
variants are *expected* to miss perceptual control gaps, so harness validity uses
the non-residualized variant. `PRD.md` §9.2.

### C7 · Three rollout pools · applied
The brief had one undifferentiated corpus. Nominal / dev / test, with blinding
only on test, is what makes "sweep freely" and "blind result" compatible at once.
`PRD.md` §9.2.

### C8 · Serving stack, Ray, image-edit reimplementation · **cut** · reversible
The brief approved all three explicitly as infrastructure chosen for team
learning, and said so honestly rather than inventing a justification — the right
instinct.

**Cut anyway**, because that rationale was for a five-person team wanting
engineering experience, and there are two of you. On Savio, parallel rollout
fan-out is what a job array does, which is the brief's own stated justification
for the serving stack. The sim-rendered B4 variant is cheaper *and* fairer than
the image-edit port, so it is primary.

**This is the one place a brief design decision is overridden on grounds other
than fact.** Say the word and it comes back. `PRD.md` §11, §17.2.

### C9 · Workstreams and blinded roles → sequential steps · superseded by you
The brief had five workstreams with directory ownership; the handoff had five
blinded roles P1–P5 with a sole key holder. **Both dropped** per your
instruction: realistically two people, so numbered steps with specs, stepped
through one at a time.

What is preserved from the blinding design is **mechanical, not social**: hash
commitment before the test pool exists, frozen method tags, one scoring run, key
revealed only after specs and causal checks are committed, CI check on sealed
imports. Credibility comes from timestamped git commitments, not from who knew
what. Pretending to separation of duties with two people would be theatre.
`PRD.md` §9.1, §13.

### C10 · Reproduction test before fine-tuning · applied
New gate not in the brief: an axis must reproduce (≥2× nominal failure rate and
≥30%) before it earns a fine-tune. Also rescues unmatched axes as *validated
natural axes* rather than counting them as errors. `PRD.md` §9.4.

### C11 · Matched-volume controls for the closed loop · applied
The brief measured failure-rate reduction on the target axis. Without
matched-volume controls that cannot distinguish "targeting worked" from "more data
helped." Six controls added, including an oracle upper bound built from the true
predicates. `PRD.md` §9.4.

### C12 · Lossless replay inputs · applied
Store the exact preprocessed model input for every frame that may be replayed.
Without it the causal checks are not reproducible. JPEG is for gate thumbnails
only. `PRD.md` §12.1.

### C13 · Statistical protocol · applied
Bootstrap resamples **routes**, not rollouts, since rollouts within a route are
correlated; the "best method" selection is re-made inside every replicate;
per-gap results always reported because with 2–3 interactional gaps the result is
conditional on which gaps were planted. `PRD.md` §10.3, §13.1.

### C14 · Fail2Drive training prohibition · clarified
The brief stated the rule but left an ambiguity: §4.5 forbade training on F2D
assets while §13 Workstream A said to bring SimLingo up *in the Fail2Drive build*
and §10.1 made F2D numbers a reproduction target.

**Resolution:** three explicit consequences written out — evaluating is fine,
using the build and toolbox is fine, **closed-loop fine-tuning targets must be
gaps we authored ourselves.** F2D-derived gaps are discovery-and-evaluation-only.
`PRD.md` §4.7.

### C15 · Track A dropped · applied
The repo's earlier dual-track framing (a text knowledge system alongside the
policy work) is out, consistent with the brief, which never had it. Flagged in
non-goals because if the course requires a text deliverable that is a
conversation to have early. `PRD.md` §18.

---

## D. Open contradictions

### D1 · SAE expansion ratio · **unresolved, matters**
The brief says **ratio 1**, attributing to Dr. VLA a finding that larger ratios
produce more dead features at robotics dataset scale with no interpretability
gain, and explicitly warns "do not fix it." The handoff says **8×–32× of d = 896**
(≈7k–29k latents).

These cannot both be right, and the brief's framing implies someone read a
specific counterintuitive finding. Resolve from the paper in **Step 0**. Until
then, sweep width as an ablation and hard-code neither. `PRD.md` §12.2, §16.1.

### D2 · Gap portfolio size · open
Brief: 3–5 gaps, budget-bound by fine-tune cost. Handoff: 4–6 plus 2 decoys,
budget-bound by rollout throughput. With Mode B the binding constraint is rollout
throughput and Savio's SU rate, neither of which is measured yet. Closes at
**Step 1**. `PRD.md` §16.2.

### D3 · Primary discovery method · open by design
Both documents say sweep rather than guess. But one method must be *named primary*
before the test pool is generated, because the random baseline's set sizes and the
closed-loop target rule both key off it. Closes at **Step 7**. `PRD.md` §16.5.

### D4 · Savio operational unknowns · open, now more important
Partition names, SU charging rate for GPU jobs, max wall time, storage quota. The
brief flagged all four; the handoff's cost estimates were sized for NRP hardware
and do not transfer. Ask the program contact. `PRD.md` §17.4.
