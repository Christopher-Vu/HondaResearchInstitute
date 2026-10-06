# PRD — Unsupervised Failure-Axis Discovery for Driving Policies

**Status:** grounding document. Reconciles `prd.md` (the project brief) with
`upstream-99p/docs/MASTER_HANDOFF.md` (the verified plan of record).
Supersedes both.

**Precedence rule.** Design decisions come from the brief. Verifiable facts come
from the handoff, which is backed by a 175-record evidence ledger
(`upstream-99p/docs/CITATION_AUDIT.md`). Where this document changed something
the brief said, the change is listed in `CONFLICTS.md` with a reason. Where a
fact is marked unverified here, treat it as unverified.

**Team:** two people, Chris and Jerry. There are no workstreams and no role
blinding. Work proceeds as numbered steps, one at a time, each with a spec and a
done-condition.

**Deadline:** none single. Venue targets form a ladder (§15) and we submit to
whichever rung the results have reached.

**Audience:** the two of us and our agents. Anything here can be assumed as
context; anything not here is open.

---

## 1. One paragraph

When a driving policy fails, the practitioner wants to know what data to collect
next. The state of the art answers this by writing down a list of candidate
failure factors and measuring degradation against that list, which can only
surface failures a human already hypothesized. We are building a tool that
derives failure axes directly from a policy's internal representations with no
factor list, validating it against gaps whose identity is recorded in a sealed
answer key, and closing the loop by generating targeted scenarios and showing the
failure rate drops.

## 2. Glossary

Used consistently throughout. Agents should use these terms and not synonyms.

- **Axis** — a named, human-describable dimension along which a policy's
  performance degrades. Not a single scenario and not a scalar score. "Yields to
  oncoming traffic only when the oncoming vehicle is unoccluded" is an axis.
- **Gap** — a scenario region that the policy is under-trained for *and* that it
  demonstrably fails in. Both halves are required; see §9.1. Its identity lives
  in a sealed answer key and is the ground truth against which discovery is
  scored.
- **Mode B gap** — a gap created by finding a region absent from the released
  training data, using the released checkpoint. No retraining. The default.
- **Mode A gap** — a gap created by deleting a slice from the training corpus and
  re-fine-tuning. The gold standard, and expensive. Deferred.
- **Control gap** — a gap that should be trivially recoverable by every method,
  included to demonstrate the harness has range. If nothing recovers the control
  gap, the harness is broken, not the methods.
- **Decoy** — a scenario region that *looks* novel but which the policy handles
  fine. Included so that "novelty" cannot masquerade as "failure."
- **Directive** — the tool's output: a ranked list of axes, each with supporting
  episodes and a parameterization spec describing what data to collect.
- **Describability** — the property that a human or a held-out model shown an
  axis's top-activating episodes can name what they have in common. An axis that
  fails this is not a discovery regardless of its numbers.
- **Adapter** — the per-policy shim exposing rollouts, activations, and success
  labels to the tool.
- **Retrospective validation** — checking a directive against data the user
  already has, rather than against newly generated data. The falsifiability path
  for users who cannot generate scenarios.

## 3. Motivation

### 3.1 The enumeration problem

Enumeration works when the confound space is listable. Manipulation confounds
largely are: lighting, background color, distractor objects, table height. That
is why the leading enumerate-and-test method works well there.

Driving's long tail is interactional. The failure is a particular merge geometry
under a particular occlusion at a particular relative velocity, between agents
whose behavior is itself a variable. These do not appear on lists because nobody
thinks to write them down, and — importantly — they are not renderable as a
single-frame image edit, which is how the leading method measures degradation.
Its instrument cannot reach them even if the factor were listed.

### 3.2 The motivating case study

Verified from Fail2Drive §4.2 and Fig. 6 (Step 0, Track A). On the
`PedestriansOnRoad` scenario, where pedestrians walk in the ego lane and the
correct behavior is to slow and follow at a safe distance, SimLingo's harmonic
mean **drops from 98.50 to 19.68, with collisions in 87% of cases.** The authors'
own stated mechanism: its language-action module *"often hallucinates a
nonexistent car or cyclist to follow… showing overfitting to the language used
during training."* Their summary: vehicle-following cues do not generalize to
non-vehicle agents.

Aggregate context, same table: in-distribution HM 80.9, generalization HM 62.2,
with the Behavior category falling hardest at −64.2%.

**Use this case study carefully, because it is not an unlistable conjunction and
claiming otherwise is an own-goal.** `PedestriansOnRoad` is an authored scenario
class, and any competent factor list could name "pedestrians walking in the ego
lane." If we present it as something enumeration could never reach, the first
reviewer to open Fail2Drive will notice.

What it *is* evidence for, and what we should claim: the policy's competence
rests on a **cue-specific prior learned from the training distribution** —
following behavior bound to vehicle-shaped agents — and that prior lives in the
policy's internals, not in the scenario description. The failure is legible as a
representational fact and illegible as a factor name, because the factor name
("pedestrians in lane") is in the training data everywhere while the thing that
breaks is the shape of the learned following cue. That is the argument this paper
is about, and it survives the fact that the scenario itself is listable.

The genuinely unlistable conjunctions are what our planted interactional gaps are
for (§9.1). This case study motivates *why* representation-level discovery is
worth trying; it does not itself demonstrate that enumeration fails.

### 3.3 Why now

Two papers published within the last year set this up and neither takes the
step. The enumerate-and-test method's own limitations section names both halves
of our contribution: vulnerabilities not visible in observations, and iterative
rather than single-shot exploration of the factor space. The SAE-on-VLAs paper
concludes by proposing that episode-specific features could diagnose fine-tuning
brittleness and that feature metrics could serve as a training-time proxy for
generalization — our thesis, unclaimed and untested.

## 4. Related work: what exists and where we sit

Read this section before proposing anything. Every citation below is as corrected
by the audit; the brief had several venue and identity errors that are fixed here.

### 4.1 Predictive red teaming / RoboART

*Majumdar, Sharma, Kalashnikov, Singh, Sermanet, Sindhwani. **CoRL 2025**, PMLR
305:1615–1635. arXiv 2502.06575. No public code.* RoboART is the name of the
pipeline, not the paper, which is titled *Predictive Red Teaming: Breaking
Policies Without Breaking Robots*.

**The competitor.** A human enumerates environmental factors; nominal
observations are edited with Imagen 3 to reflect each factor; **four candidate
edits are generated per input and a Gemini Pro 1.5 critic picks the best or
discards all four**; degradation is predicted by an anomaly detector measuring
mean k-nearest-neighbor cosine distance in *policy embedding space*, thresholded
by conformal prediction (k = 5 against 3000 nominal first-timestep observations
for one policy, k = 10 against 500 for the other, 100 edited observations per
factor).

Results: 12 off-nominal conditions, two visuomotor diffusion policies, bimanual
Kuka manipulation. Spearman ρ of 0.8 and 0.7 between predicted and true factor
rankings, and average absolute success-rate prediction error of 0.10 and 0.19,
with ground truth from 20+ hardware episodes per factor. Targeted collection of
~100 trajectories (about an hour) for each of the three worst factors,
co-finetuned at an 80/20 old/new mixture per mini-batch at lr 5e-6 for 20K steps,
gives **2–7×** improvement on the collected conditions and 2–5× on uncollected
ones.

**The 12 conditions are levels of only five factors** — lighting color, table
background color, four distractor objects, one person near the table, one
table-height change. That is a narrower factor space than "12 factors" suggests,
and it is worth saying so when we describe what enumeration bought them.

**The framing that matters.** RoboART already uses internal representations — the
anomaly score is computed in the policy's own embedding space. Do not write
"internals versus behavior." The axis of comparison is **enumerated factor list
versus unsupervised discovery**, and secondarily **single-frame observation edits
versus temporal, interactional structure**. A reviewer will know this; getting it
wrong costs credibility immediately.

Note the setting: manipulation, no weather, not VLAs, not driving, not
language-conditioned.

**One more detail that helps us.** They score only the **first-timestep**
observation of each episode. Our argument is that driving failures are temporal
and interactional, so an instrument that reads one frame per episode cannot reach
them — and this is that instrument, stated in their own method. Use it.

Their limitations section names both halves of our contribution explicitly:
*hidden environmental factors* (their method needs a visible change) and
*multi-round predictive red teaming* (theirs uses one fixed factor set).

### 4.2 SAFE

*Gu, Ju, Sun, Gilitschenski, Nishimura, Itkina, Shkurti. **NeurIPS 2025**.
arXiv 2506.09937. Code at `vla-safe/SAFE`.* Title: *Multitask Failure Detection
for Vision-Language-Action Models*. Manipulation.

Trains a small 1–2 layer MLP or LSTM head on VLA hidden states to emit a scalar
failure likelihood, thresholded by functional conformal prediction. Features come
from the final layer before decoding; aggregation is ablated over First / Last /
Mean / First&Last, and the real-world configuration is pre-logits features with
Mean. **Detector training takes under a minute on an A100-40GB** — which is why
B6 is nearly free.

**Our relationship to it.** SAFE detects per-episode failure and raises an alert.
We aggregate across a corpus and emit a data directive — a different object. We
take their hooking location and aggregation ablation as settled engineering. Their
sub-minute training cost means a SAFE-style detector is nearly free, which is why
it also appears as a baseline (§9.3, B6).

### 4.3 Dr. VLA

*Swann, McGranahan, Buurmeijer, Kennedy, Schwager (Stanford). arXiv 2603.19183.
CoRL 2026 per the authors' repo. Code at `swannaiden/drvla`, release announced
for 1 Oct 2026.* Title: *Sparse Autoencoders Reveal Interpretable and Steerable
Features in VLA Models*. Trains SAEs on residual-stream activations of π0.5.

All figures below verified against the PDF (Step 0, Track A).

- **A generality metric requiring no rollouts.** Four per-feature statistics —
  episode coverage, mean onset count, mean peak activation, relative run length —
  fed to a logistic regression giving P(general), validated on 30 hand-labeled
  features per dataset at 100% / 96.7% leave-one-out accuracy. **Most features
  are memorized:** only 2.62% general on π0.5/LIBERO, 10.81% on π0.5/DROID, 0.45%
  on OpenVLA/LIBERO-Goal.
- **A describability protocol:** label a feature interpretable when its temporal
  activation pattern consistently aligns with an identifiable sensorimotor event.
  **95 of 120 SAE features (79.2%) were interpretable, against 6 of 20 FFN
  neurons (30.0%).** Note the baseline n is 20, not 120 — cite it correctly.
- **Causal validation by ablation**, on real-world DROID tasks: unsteered 39/40,
  random memorized features 37/40, random general 26/40, **top-4 most general
  0/40.**

**Three consequences.** First, we adopt their describability protocol and their
SAE configuration (§12.2). Second, their metrics are *a baseline we must beat and
which costs almost nothing to run*, because they need no rollouts — if activation
statistics over the training data recover gaps as well as our rollout pipeline
does, our compute story collapses, which is why it is Step 6 (§9.3, B7).

Third, and least obvious: **we do not adopt their memorization filter as a
default.** A planted gap looks memorized by their definition, so filtering on it
would plausibly delete what we are hunting. It becomes an ablation; see §9.2.

Their stated limitation is useful to us: *"meaningful top activations of a feature
does not imply reliable steerability"* — predictive is not causal. Our closed loop
is a causal test. They also propose, untested, that episode-specific features
could diagnose fine-tuning brittleness and that feature metrics could act as a
training-time proxy for generalization (§6) — which is our thesis, unclaimed.

### 4.4 Event-grounded SAEs

*Jin, Chatterjee, Kumar, Paleja (Purdue). arXiv 2605.17204.* SAE features ranked
against behavioural events clustered from rollouts, with VLM labels and
residual-preserving zero-out checks, on OpenVLA and π0.5.

**The closest method precedent, and the brief missed it entirely.** Differentiate
on four axes: we are failure-conditioned, scored against planted gaps, in
driving, and we close the loop. Their residual-preserving zero-out is the right
template for our causal check.

### 4.5 RESample

*Xue, Lu, Wu, Zhang, Jia, Gu, Wang. arXiv 2510.17640, preprint; no acceptance
found.* Manipulation. **Not ICRA 2024, as the brief's bibliography said.**

Trains a conservative coverage function estimating whether a state-action pair is
supported by the demonstrations, then samples exploratory deviations followed by
recovery. The nearest non-enumerated competitor — it finds coverage gaps without
a factor list — but it outputs trajectories, not a nameable axis, and it is
manipulation. **Related work, not a baseline** (§9.3).

### 4.6 CUPID

*Agia, …, Bohg (Stanford/TRI). CoRL 2025.* Influence functions rank
demonstrations by their effect on closed-loop return.

Worth one paragraph for a sharp reason: **attribution can only rank data that is
present, and a planted gap is data that is absent.** This is a clean statement of
why our problem is not an attribution problem. Discuss, do not run.

### 4.7 Fail2Drive

*Gerstenecker, Geiger, Renz. **IROS 2026** (to appear); arXiv 2604.08535. Code at
`autonomousvision/fail2drive`. CARLA 0.9.15.* A paired-route closed-loop
generalization benchmark: 100 route pairs, 17 unseen scenarios, 30 novel assets
(17 animal assets, visual noise, adversarial obstacles), where only the targeted
shift varies between a route and its in-distribution twin. Metrics are Driving
Score, Success Rate, and their harmonic mean, averaged over three seeds. Ships a
scenario, asset and behavior authoring toolbox, and **PDMLite-F2D**, a privileged
rule-based expert offered as a solvability check for newly authored scenarios —
it scores 94.6 HM on the generalization split, so it is a credible oracle.

It gives us SimLingo's generalization profile (§10.1), a source of Mode B gap
regions (§9.1), and a ready-made held-out measurement for the "did not degrade
general performance" claim.

**The rule that binds us**, quoted from §3.2: *"Models must not use the routes,
scenario definitions, or assets introduced in Fail2Drive for training or
fine-tuning. The benchmark serves strictly as a held-out test set."* Pretraining
on external data and foundation models is explicitly allowed, so SimLingo's own
pretraining is fine. Three consequences, stated explicitly because the brief left
an ambiguity here that an agent could walk into:

1. **Evaluating** on Fail2Drive is fine and is what it is for.
2. Using Fail2Drive's **CARLA build and authoring toolbox** is fine.
3. Any gap used as a **fine-tuning target in the closed loop (§9.4) must be one
   we authored ourselves**, not drawn from Fail2Drive scenarios or assets.
   Fail2Drive-derived gaps are discovery-and-evaluation-only.

### 4.8 The driving VLA landscape

DriveVLM (no public weights or code), DriveMoE/Drive-π0, SimLingo, AutoVLA (no
CARLA code), ORION, HiP-AD, TransFuser++, PlanT, LEAD/TFv6. The domain is crowded
and mature. **Driving is not our novelty and must never be pitched as such.** It
is the setting where the enumeration argument actually bites.

### 4.9 Slice discovery

Domino (ICLR 2022) introduced planted-slice evaluation and is the precedent for
our harness; also Spotlight (FAccT 2022), George (NeurIPS 2020), SliceLine
(SIGMOD 2021). Domino appears as a baseline (§9.3, B5) because it finds slices in
*input embedding* space, which is the natural "did you need the policy's
internals at all?" control.

---

## 5. The claim

> Failure axes derived without supervision from a driving policy's internal
> representations recover data gaps that enumerated-factor analysis, behavioral
> success-rate stratification, input-embedding slice discovery, and rollout-free
> activation statistics all miss, and targeted data generation along those axes
> closes the corresponding failures.

Four independent ways this can fail, and what each means:

1. **The harness is invalid.** Planted gaps do not actually cause failures, so
   there is nothing to recover. This is the one outcome that leaves us without a
   result, and §9.1's efficacy check exists to catch it *before* we spend the
   compute. If it happens anyway, the paper is a negative result about planting
   failure gaps in closed-loop driving.
2. **Axes are not recoverable.** The harness is valid but discovery returns
   nothing that maps to a gap. A real negative result on the limits of
   representation probing in sequential policies.
3. **Recoverable but not better than the baselines.** Still a paper — an honest
   comparison of directive-generation methods on a benchmark nobody has built.
4. **Better but not actionable.** Axes recover gaps, but generating along them
   does not close failures. Also a paper, and an interesting one: it would mean
   discovered structure is diagnostic but not prescriptive.

Only (1) leaves us without a result, which is why it is tested first and
cheaply.

> **Note on a reframing.** The handoff re-tiered the brief's outcomes, demoting
> "axes not recoverable" from worst case to middle and making "harness invalid"
> the new worst case. That reframing is adopted above, because it is correct:
> a negative result about probing is publishable, whereas a broken measuring
> instrument is not. Logged in `CONFLICTS.md`.

## 6. What we want out of this, independent of results

- **A paper.** Venue flexible; see the ladder in §15.
- **A citable artifact.** The tool is the thing we expect to be cited, not the
  method. That means it must run on policies that are not SimLingo — see §7.
- **A released planted-gap benchmark.** Second citable object. Benchmarks get
  cited more than methods.
- **Both of us with a causal hand in the substantive results.** With two people
  this is easy and mostly automatic, but it still shapes the step specs: where a
  step is a sweep, both of us run arms of it and compare, rather than one of us
  building it and the other consuming the output.
- **A write-up of what broke.** Kept continuously in `docs/WHAT_BROKE.md`, not
  reconstructed at the end.

### 6.1 Technology

Preferences, not requirements. Any plan should justify each or propose better.
"Familiar" is not a justification. §11 says which of these are scientifically
necessary and which are chosen.

- Compute: Savio (§17).
- Orchestration: Ray, for rollout fan-out and sweeps, launched inside a Slurm
  allocation. Chosen rather than necessary — see §11 for the honest accounting.
- Training: PyTorch; LoRA (already SimLingo's recipe); versioned configs;
  checkpointing.
- Tracking: Weights & Biases.
- Results: a database. Any number in the paper reproducible from a query.
- Sim: CARLA 0.9.15, Bench2Drive harness, Fail2Drive build and toolbox.
- Serving: **deferred, and possibly never.** See §11.

### 6.2 Workflow

- GitHub repo, everything in it.
- Agents write most or all code. Both of us review before merge.
- Configs versioned with code; no result that cannot be regenerated from a config
  hash.
- The sealed answer key is read by nothing except scoring code. Enforced by repo
  layout and a CI check (§14), not by good intentions.
- One of us owns re-checking arXiv, monthly. The closest papers are months old.
  Default: Jerry, who owns the citation audit.

## 7. Honda and AV relevance

A deployed autonomous driving program's central data question is which of the
effectively infinite possible collection targets is worth the money. The current
answer is human intuition plus a factor list, and the failure mode is structural:
the list is written by the same people whose model of the world produced the
training distribution in the first place. A method that proposes collection
targets from the policy's own representations, with no list, addresses exactly
that blind spot. The artifact is a tool someone at an AV program could point at
their own policy through an adapter, which is why §8 matters as much as §9.

## 8. The system

The tool, not the experiment. This is what gets released and cited.

### 8.1 Shape

Data in, directive out. The tool does **not** include scenario generation —
most policies cannot generate, and coupling generation into the tool would make
it unusable outside simulation. Generation is how *we* validate (§9.4), not part
of what we ship.

### 8.2 Adapter interface

The generality claim is exactly as strong as this interface is small. A policy is
usable if its adapter exposes three things:

1. **Rollouts** — run the policy in its environment, return per-episode
   observation/action sequences.
2. **Activations** — per-timestep internal state at a specified hook point,
   mean-pooled over tokens by default.
3. **Success labels** — a per-episode binary or scalar outcome.

Ship two adapters: SimLingo, and a deliberately minimal stub that proves the
interface is implementable by someone who has not read our code. **Do not design
this interface up front.** Build it by refactoring *after* SimLingo works,
otherwise the early steps are spent on abstraction rather than on a working
system.

### 8.3 Output schema

The contract. Vagueness here is how tool papers die. Every discovered axis
serializes as:

```yaml
axis_id: str                 # stable identifier
name: str                    # human-written, from the describability protocol
description: str             # what the top episodes share
supporting_episodes:         # ranked, with activation evidence
  - episode_id: str
    activation: float
    timesteps: [int, int]    # where on the episode the axis fires
rank: int                    # position in the directive
score: float                 # method-specific, documented per method
generality:                  # Dr. VLA memorization filter
  general: bool
  metric: str
causal:                      # §9.2 causal check
  ablation_delta: float
  control_p95: float
  verdict: str               # causal | correlational_only
gate:                        # §9.2 describability
  auroc: float
  shuffle_auroc: float
  passed: bool
parameterization:            # what data to collect
  scenario_family: str
  parameters:
    - name: str
      range: [min, max]
      units: str
provenance:
  method: str                # sae | contrastive | probe_residual | baseline_name
  config_hash: str
  layer: str
  aggregation: str
  preprocessing: [str]
```

`name` and `description` are written under the §9.2 protocol and are not
optional. An axis without them is a cluster, not a discovery.

### 8.4 Retrospective validation mode

Given held-out data the user already has, confirm the policy actually
underperforms on the flagged slice. No generation needed, works for any adapter,
and it makes the tool self-checking rather than trust-me. A reviewer will ask how
a user without a simulator falsifies a directive; this is the answer.

---

## 9. Method

### 9.1 Gaps and the sealed key

The methodological contribution. Everything else is downstream of whether this is
built carefully.

**Procedure.** Define candidate gap regions. **Check that the policy actually
fails in them.** Seal the surviving ones into an answer key with a committed
hash. Run discovery blind. Score recovery against the key.

#### Two planting modes

**Mode B — novel by construction. The default.** Use the released SimLingo
checkpoint. A gap is a scenario region absent from SimLingo's released training
data: Fail2Drive's unseen scenarios and novel assets, plus parameter regions we
build outside SimLingo's collection distribution. Absence is checked against the
released dataset and collection configs. Cost: roughly zero GPU-hours for
planting. This is what we do.

**Mode A — withholding. The gold standard, deferred.** Remove the gap slices from
the training corpus, re-fine-tune, and compare against a matched in-house
full-data control rather than against the released checkpoint. Cost: on the order
of 190 A100-hours per model by the paper's recipe. Deferred until the main result
exists, then run as the strengthening experiment.

> **This is the brief's largest design change and the reason is worth stating.**
> The brief assumed Mode A and treated the delete-versus-regenerate question as
> its blocking open decision. Mode A has a hidden assumption: that removing
> training data causes failures. **Neural policies generalize, so it often does
> not.** Delete every occluded-left-turn example, retrain, and the policy may
> handle occluded left turns anyway. The sealed key then lists a gap where
> performance is normal; discovery correctly finds nothing; the headline number
> measures our planting procedure rather than the method. The failure is silent.
> Mode B sidesteps it entirely — there is nothing to retrain, so nothing to
> confound — and the efficacy check below catches it in either mode.

#### The efficacy check — run before sealing, in both modes

A candidate region becomes a gap only if the policy demonstrably fails more
inside it than in its matched neighbourhood (the same scenario family, parameters
outside the region). Require all of:

- a failure-rate uplift of at least 20 percentage points **and** a ratio of at
  least 2×, so the gap-attributable share is at least 0.5;
- Fisher exact p < 0.01;
- at least 30 rollouts in the slice.

Replace candidates that fail, and **report how many candidates were tried.**
Pilot estimates are noisy and subject to the winner's curse, so efficacy is
re-confirmed on the scoring pool at scoring time.

#### Gap portfolio

Four to six gaps plus two decoys, budget-bound, spanning:

- **One or two control gaps** — perceptual or environmental, e.g. a weather or
  lighting preset family. Every competent method should find these. If none does,
  the harness is broken rather than the methods.
- **One enumerable gap** — a single factor any reasonable list would name, e.g.
  one novel actor type. This probes where enumeration starts to fail rather than
  only showing the extremes. (The brief called this the "near-miss gap.")
- **Two or three interactional gaps** — conjunctions or sub-ranges no standard
  list names. **The main claim is about these.** Candidate families, drawn from
  real CARLA/Bench2Drive scenario classes: a `HighwayCutIn` only when the gap is
  below some distance *and* relative speed above some threshold; a
  `ParkingCrossingPedestrian` only above some ego speed; an `InvadingTurn` with
  the oncoming vehicle occluded.
- **Two decoys** — one visually novel family and one kinematic region outside the
  collection distribution, each with a failure rate within 5 percentage points of
  its neighbourhood. These stop "novelty" from standing in for "failure," and the
  decoy hit rate is a reported metric.

Any predicate written in this document or any other shared document is a *public
illustration* and is excluded from the sealed key. The sealed predicates are
drawn from a candidate pool recorded only in `gaps/sealed/`.

#### A confound to check

SimLingo's training samples through interestingness buckets. Slice removal
interacts with that sampler: a removed slice may be over- or under-represented,
so effective removal is not nominal removal. This matters for Mode A only, but it
matters a lot there. The audit adds detail: withholding means filtering route
directories rather than zeroing bucket weights, and the VQA, commentary and
dreamer labels leak the withheld concept unless they are dropped too. Measure and
report the effective post-sampler removal rate when Mode A runs.

#### Sealing protocol

1. Predicates, tiers, prevalence, efficacy statistics and absence rationale go in
   `gaps/sealed/key_v1.json`. `gaps/sealed/` is git-ignored.
2. Seal before the scoring pool is generated. Commit `sha256(key ‖ salt)` to
   `harness/KEY_COMMITMENT.txt` and tag it.
3. Freeze methods before any of them reads scoring-pool outcomes. Tag that too.
4. Score once. Later re-runs are labelled post hoc and reported as such.
5. Reveal the key and salt only after causal checks and scenario specs are
   committed.

With two people we cannot have a sole key holder who touches nothing else, and
pretending otherwise would be theatre. What replaces it is mechanical: the
hash commitment, the frozen tags, the one-shot scoring run, and the CI check that
nothing under `discovery/` or `baselines/` imports from `gaps/sealed/`. The
credibility comes from the commitments being timestamped in git, not from who
knew what.

### 9.2 Discovery

Collect activations across a rollout corpus spanning many scenario variations.
Derive candidate axes from structure in those activations with no factor list.

**Rollout pools.** Three, and keeping them separate is what makes the result
blind:

- **Nominal** — the Bench2Drive 220-route set, for reproduction and regression.
- **Dev** — a few hundred to a thousand rollouts for method development, with two
  public practice gaps. Everything is visible here. **Sweep freely on dev.** This
  is where both of us fan out across layers, preprocessing and methods.
- **Test** — the blind scoring pool, containing the sealed gaps and decoys. Each
  gap occupies roughly 4–8% of it, all injected slices together stay under 40%,
  and every slice meets the power analysis and at least 60 rollouts. Methods
  touch this once, through a committed script, after being frozen.

**Preprocessing**, ablated:

- **Standardization** per layer, fitted on dev success frames.
- **Action-residual orthogonalization.** Ridge-regress the action-query states on
  the pooled visual tokens, fitted on success frames, and keep the residual. This
  removes "it is raining" directions so clusters follow decisions rather than
  appearance. The brief identified this risk; this is the fix, adopted from the
  handoff.
- **Nuisance projection**, optionally removing the top components that predict
  town or weather.

Control gaps are perceptual, so the *non-residualized* variant is what should
recover them and what the harness-validity check uses. Residualized variants are
expected to miss control gaps and that does not count against them.

**Methods**, to be swept rather than chosen up front:

- **Contrastive diffing.** Per-feature standardized mean difference and firing-rate
  log-odds between failure and success windows; keep at FDR q < 0.05 with support
  ≥ 20 rollouts; merge co-firing features into axes; rank by effect × support.
- **SAE latents.** TopK SAE on the selected layer, raw and residualized, trained
  on unlabeled dev and test activations. Test *outcome labels* may never be used
  to tune it. Report dead-latent fraction, explained variance, and waypoint error
  when reconstructions are spliced back in.

  **The memorization filter is an ablation, not a default — and this is
  deliberate.** Dr. VLA's classifier labels a feature memorized when it fires
  roughly once per episode across a coherent but small subset of the data. *That
  is a precise description of a planted gap:* one cut-in per route, in 4–8% of the
  pool. Filtering on it would plausibly delete exactly the features we are trying
  to find. Two further reasons not to take it on faith: the classifier was fit on
  30 hand-labeled **manipulation** features, so transfer to driving is unproven;
  and in their models only 0.45%–10.81% of features are general, so the filter is
  aggressive. Run discovery with the filter off as the default and on as an
  ablation, report both, and if the filter version wins, say so. If we ever want
  it as a default, relabel ~30 driving features and refit first.

  This cuts against §4.3's "adopt rather than invent," and the reason is that
  our use is not theirs: they filter to find *general* features, we are hunting
  something that looks memorized by construction.
- **Probe residuals.** Decode a pre-registered generic state list (lead distance
  and relative speed, nearest-pedestrian distance, traffic-light state,
  time-to-intersection, occlusion flag) from activations, fitted on success
  frames; cluster the residuals on failure frames. Separately, cluster
  policy-minus-expert waypoint residuals jointly with activation projections,
  which separates "right perception, wrong decision" from "wrong perception."

**Hook point.** Open (§16). SimLingo's LLM is Qwen2-0.5B — 24 decoder layers,
hidden size 896, confirmed by strict-loaded checkpoint inference on 2026-10-02.
Two candidate sites: the
LLM residual stream, and the learnable waypoint query tokens before the MLP head.
The query tokens are the action bottleneck, since the waypoint MLPs read only
those. Also include the vision bridge, because at least one paper reports the
visual pathway dominating action generation in VLAs. Sweep on dev; pick before the
test pool is generated; log only the selected layers at scale.

**Describability gate.** Adopted from Dr. VLA, made automatic and falsifiable:

1. For each axis, take the top failure keyframes and matched contrast frames.
   Contrast frames are success frames matched on ego speed and road type from
   logged kinematics, never from scenario labels.
2. A pinned open vision model answers a contrastive prompt: what is present in
   group A and absent in group B?
3. A **separate text-only model** gets only that description plus an
   auto-generated structured summary of each held-out rollout, built only from
   logged observations — actor classes, speeds, distances, time-to-collision.
   Never from scenario type, parameters, or weather presets. It predicts which
   held-out rollouts score high on the axis. **Pass if AUROC ≥ 0.70.**
4. Report two controls: random axes, and a description-shuffle control that scores
   each axis with another axis's description. **The shuffle control's pass rate is
   the gate's false-positive rate.** Without it the gate rubber-stamps everything.
5. The policy's own chain-of-thought commentary is never ground truth. Distilled
   CoT is post-hoc rationalization.

This replaces the brief's human-rater protocol. The brief was right that
describability is a hard requirement and right to borrow the protocol; the
handoff is right that a human eyeballing clips is unscalable and will read as
cherry-picking. Keep a human spot-check as a sanity pass, not as the metric.

**Causal check**, on every top-ranked axis:

- **Projection removal.** On logged failure frames, remove the axis direction from
  the activation and measure the change in waypoints.
- **Steering.** Add the direction to success frames and check whether waypoints
  move toward the failure pattern.
- **Controls.** Random directions with matched norm, and non-failure latents.

Axes whose effect falls below the 95th percentile of controls are marked
**correlational only**. They are still scored but not prioritized for generation.
A null result is informative: at least one paper shows a linearly decodable
direction can have no causal effect on actions. Control gaps are the positive
control here.

### 9.3 Baselines

Seven. Each runs on the same test pool, through the same harness, with the same
axis budget, scored by the same metrics. More baselines is the right instinct —
each one closes a specific reviewer objection, named below.

- **B1 Random.** Random failing-rollout subsets, sized from the primary method's
  axis sizes, averaged over many draws. *The chance floor.*
- **B2 Human taxonomy.** Top single-factor strata of benchmark metadata —
  scenario family, weather, town, ability — ranked by failure rate. *Standard
  practice.*
- **B3 Behavioral stratification.** Clustering on action error versus the expert,
  kinematics, and infraction type, given the same per-frame state features the
  probe-residual method gets. *The go/no-go gate: if internals do not beat plain
  behavioral grouping, the interpretability framing collapses and we pivot.*
- **B4 Enumerated factors, RoboART-style.** A factor list of roughly 8–15 factors
  × levels, written from public sources and hash-committed **before** gaps are
  designed. Primary variant renders each factor natively in CARLA and measures
  the real failure rate, which is the stronger and fairer variant in simulation;
  the image-edit variant with an anomaly detector in embedding space is the
  faithful port. Also run a pairwise-factor version, which answers "your factor
  list was just weak." *The head-to-head that carries the claim.*
- **B5 Input-embedding slice discovery, Domino-style.** Error-aware mixture model
  over CLIP/SigLIP embeddings of failure keyframes. *Did you need the policy's
  internals, or would any perceptual embedding do?*
- **B6 Detector-embedding clustering, SAFE-style.** Train a failure detector on
  the same activations, cluster its latent space. *Is discovery just detection?*
- **B7 Rollout-free activation statistics, Dr. VLA-style.** The four per-feature
  statistics — episode coverage `c`, mean onset count `ō` (τ_on = 0.1), mean peak
  activation `ā`, relative run length `ℓ̄_r` — computed over the training data
  with no rollouts, using memorized-feature concentration as the gap signal.

  **This construction is ours, not theirs.** Dr. VLA never proposes these metrics
  as a gap signal; they use them to separate general from memorized features.
  So B7 needs a written definition — how concentration is measured, over what
  partition, and how it ranks into axes — committed **before Step 6**, or it is
  not a fair baseline.

  **And note the irony, which cuts against us.** A planted gap looks memorized by
  construction (§9.2): it fires about once per episode across a small coherent
  subset. So a statistic designed to *find* memorized features may be unusually
  well-suited to finding our gaps. **B7 may be stronger than we would like**, and
  it costs no rollouts at all.

  **Cheap and dangerous — if this wins, our rollout corpus is not justified. Run
  it early (Step 6), not late.** It would still be a paper: a negative result
  about when expensive discovery is worth paying for. But we need the runway to
  write that one instead, which is the entire reason it is Step 6.

A VLM-captioning baseline (cluster captions of failure clips, Meteor-style) is
worth adding if time allows; it is the surface-semantic industrial pipeline and a
natural contrast. Optional.

**Cut:** RESample-style coverage functions. Conceptually relevant, but they output
trajectories rather than nameable axes and the method is manipulation-specific.
Related work, one paragraph. CUPID likewise — discussed, not run (§4.6).

**Fairness rules.** The B4 factor list is written from public sources and hashed
before gap candidates are chosen. Every method gets the same axis budget, the same
rollouts, and the same gate. Baseline configs are committed and hashed before the
gaps are finalized.

### 9.4 Closed loop

Take a discovered axis, parameterize a scenario family along it, validate
solvability with PDM-Lite, generate training data with the expert, fine-tune, and
measure whether failures on that axis close.

**Reproduction test first.** Before generating training data, run the policy on
50 sampled scenarios from the axis's parameterization. The axis **reproduces** if
its failure rate is at least 2× the nominal rate for that scenario class and at
least 30%. An axis that does not reproduce does not get a fine-tune. This is also
what rescues unmatched axes: an axis that reproduces but matches no planted gap
is a *validated natural axis*, not an error, and is reported through a secondary
"validated precision."

**Repair.** LoRA (r = 32, α = 64, dropout 0.1) on all the LLM's linear layers,
which is SimLingo's native path, with a 1:1 mix of targeted and replay data.
Hyperparameters fixed before targeted data is generated and identical across
conditions.

**We freeze the vision encoder; SimLingo does not.** Their recipe fully
finetunes every component except the LLM (§12.3). Freezing is our deliberate
deviation: a repair step that retrains the encoder can fix a failure by shifting
perception, which both costs more compute and muddies the claim that we repaired
the *decision* the discovered axis names. Label it as our deviation in the paper,
not as SimLingo's recipe, and run an unfrozen arm if a reviewer would ask or if
the frozen version underfits.

**Controls, at matched frames and matched GPU-hours.** This is what makes the
result mean "targeting worked" rather than "more data helped":

- no fine-tuning;
- random scenarios;
- LLM-proposed hazards from a generic list, with no access to activations;
- B4's worst factor levels;
- B3's clusters;
- an oracle built from the true key predicates — the upper bound.

**Evaluation.** Failure rate on held-out routes from the gap slice, kept separate
by location and seed. Failure rates on *other* gaps, to separate targeted repair
from generic improvement. And a no-degradation check on Bench2Drive-220 across
three seeds, where non-inferiority means the lower bound of the one-sided 95%
interval on the Driving Score change is at least −2.

**Targets must be gaps we authored**, never Fail2Drive-derived (§4.7).

One full cycle minimum, two if the infrastructure holds. One policy only.

## 10. Evaluation

### 10.1 Reproduction targets

"Reproduced" means a number, not a vibe.

| Benchmark | Metric | Target |
|---|---|---|
| Bench2Drive (v0.0.3) | DS / SR | 85.07 ± 0.95 / 67.27 ± 2.11 |
| Bench2Drive, CoT off | DS | 84.41 ± 1.76 |
| Fail2Drive in-distribution | HM | 80.9 |
| Fail2Drive generalization | HM | 62.2 |

Two facts that change how we read these. **First, record the Bench2Drive
version** — v0.0.3 and v0.0.4 numbers are not comparable, and under v0.0.4
SimLingo is 86.55 DS. Second, **the only public reproduction attempt we know of
got DS 75.5**, on 219 routes, configuration unconfirmed, with no maintainer
reply. So the practical bring-up bar is **DS ≥ 75**, not 85, and anything below
that means debugging rather than proceeding. Three evaluation seeds.

Category-wise generalization, useful for checking that our setup reproduces the
*shape* of SimLingo's weaknesses and not just the average: Behavior −64.2%,
Visual-lateral −32.2%, Visual-longitudinal −9.0%, Robustness −5.9%.

SimLingo also already fails often in interactive abilities, which sets the
background failure rate our planted gaps must stand out against (paper Table 8):
Merging 54.01, Overtaking 57.04, Give Way 53.33, Emergency Brake 88.33, Traffic
Sign 82.45, mean 67.03.
Natural failures will dominate the test pool. Size prevalence with a power
analysis on dev, and aim interactional gaps at the known-weak abilities.

**Run with commentary and chain-of-thought off** in the main campaign. Paper
Table 10: without CoT, DS 84.41 ± 1.76 / SR 64.84 ± 2.42; with CoT, DS 85.07 ±
0.95 / SR 67.27 ± 2.11. The DS difference is within noise, turning CoT off removes
a text-generation pass from every step, and at 15–20× slower than real time that
matters. Note the SR gap is larger than the DS gap, so report both and keep CoT-on
as an ablation.

### 10.2 Primary metrics

- **Planted-gap recovery: precision and recall**, per method, per tier. The
  headline. Matching is one Hungarian assignment over all gaps on failing-rollout
  Jaccard with threshold 0.5, at a fixed axis budget — so precision always
  divides by the budget. Report threshold-free metrics too.
- **Spearman rank correlation** between each method's ranked directive and the
  true severity ordering. This is RoboART's metric; reporting it makes the
  head-to-head legible to anyone who has read that paper.
- **Failure-rate reduction after targeted fine-tuning**, per axis source.
- **Gate pass rate** per method, against the shuffle control's false-positive
  rate.

### 10.3 Secondary

- **Coverage of interactional gaps specifically**, separated from control and
  enumerable gaps. This is where enumeration is predicted to fail and the
  separation is the argument.
- **Decoy hit rate.** How often a method's axes land in regions that look novel
  but are handled fine.
- **Mean best Jaccard** and per-gap attributable share.
- **Validated precision**, counting reproducing-but-unmatched axes.
- **Cross-model check.** Does an axis found in SimLingo surface in a second
  policy? A shared axis is a claim about the data distribution rather than one
  model. First thing cut if bring-up runs long.
- **No-degradation check** on Bench2Drive-220 and Fail2Drive.

Statistical care: with only two or three interactional gaps, results are
conditional on the specific gaps planted, so **always report per-gap results**
alongside any aggregate. The headline comparison is a single pre-registered test,
so no multiplicity correction; everything else is exploratory and labelled so.
Confidence intervals come from a bootstrap that resamples routes, not rollouts,
because rollouts within a route are correlated.

---

## 11. What we build versus what we take

Rule: the code should be minimal and explorable. Take anything that does not need
changing. Where we build something anyway, say honestly whether it is
scientifically necessary or an infrastructure choice — machinery with a
retrofitted justification is how a codebase turns into slop.

**Take, do not build.**

- SAE training stack and the memorization filter — Dr. VLA is released.
- The describability protocol — adopt, then automate per §9.2.
- SimLingo training, evaluation, and LoRA recipe.
- Bench2Drive harness and metrics.
- Fail2Drive scenario toolbox, CARLA build, PDM-Lite solvability check.
- CARLA.
- Hungarian matching — it is `scipy.optimize.linear_sum_assignment`.

**Build — no source exists.**

- **The gap harness with its efficacy check.** Nobody has built this. It is the
  contribution.
- **The adapter interface.** Generality is the tool's claim; it cannot be
  borrowed.
- **The comparison layer** that puts seven baselines and three discovery methods
  on one corpus under one metric. Every paper evaluates its own method its own
  way; the comparison is ours.

**Build, necessary and wanted.**

- **Streaming activation capture inside the rollout path.** Published SAE work
  captures activations offline on manipulation episodes. We need capture during
  closed-loop driving rollouts at scale. Genuine work.
- **The evaluation harness.** Config in, comparable numbers out, across many
  variants and both of us.

**Build, wanted but not scientifically necessary.** Stated plainly so nobody
invents a justification later. The brief's own honest accounting, kept:

- **Ray**, for rollout fan-out and sweep orchestration. A Slurm job array would
  also do it, and §17.2 says so. Ray is chosen anyway: it gives one orchestration
  layer across rollout fan-out, the layer sweep, and the baseline matrix, with
  retries and failure handling that we would otherwise hand-roll in bash, and it
  keeps the fan-out code portable off Savio — which matters because NRP is the
  documented fallback and the tool is meant to run elsewhere (§8). The honest
  version: this is an engineering choice with a real but secondary payoff, not a
  scientific requirement. Ray on Slurm means launching a Ray cluster inside an
  allocation; budget a day for that and do not let it become a week.

**Cut, versus the brief.**

- **The serving stack (vLLM/Triton).** The brief's own accounting said it is
  justified by parallel rollout fan-out, not by making any single rollout faster,
  since SimLingo runs a 4 fps loop on a 1B model where per-step latency
  dominates. With Ray doing the fan-out, the serving stack has no remaining
  justification. **Cut.** If per-rollout throughput turns out to be the binding
  constraint, revisit — but measure at Step 1 first.
- **Re-implementing the image-editing baseline** rather than adapting a published
  pipeline. The sim-rendered B4 variant is both cheaper and fairer in simulation,
  so it is primary; the image-edit variant is secondary and only if time allows.

The brief approved all three explicitly and said plainly that they were chosen
for team learning rather than scientific necessity, which is the right instinct.
That rationale weakened at two people, which is why two are cut — but Ray carries
its own justification above and stays. Logged in `CONFLICTS.md`.

## 12. Borrowed configuration

Copy these rather than rediscovering them. **Verified against the primary PDFs
in Step 0, Track A** (`docs/step0-trackA-findings.md` holds the per-item
references). Items still marked ❓ there need a loaded model or a repo rather than
a paper, and are resolved in Steps 1–2.

### 12.1 Activation capture and hooking

- Hook the residual stream at the output of a full transformer block — standard
  SAE location.
- PyTorch `register_forward_hook` on the target decoder-layer modules.
- Mean-pool over tokens per timestep by default; each episode yields a `(T, d)`
  matrix. Per-token capture costs terabytes at scale and was reportedly less
  interpretable.
- For a SAFE-style detector: final layer before decoding to logits, pre-logits
  with mean aggregation. Ablate First / Last / Mean / First&Last.

Storage arithmetic, which decides what we can log — recompute it once d is
confirmed at Step 1. At `layers × tokens × d × 2`
bytes in fp16, logging all 24 layers over ~35 token-vectors is about 1.5 MB per
frame; three layers is about 190 KB per frame, so a few thousand rollouts is
roughly 70 GB. Log all layers on the small dev pilot only, then three layers at
scale. Per-rollout Zarr or Parquet shards plus a SQL index.

**Measured 2026-10-06** on the Mac capture run of route 26956
(`adapters/simlingo/capture_agent.py`). Each forward pass is 573–574 tokens:
512 image tokens (two 448×448 tiles of 256), about 31 prompt tokens, then the 30
driving queries (20 route, 10 speed), which are always the last 30 positions.
The policy runs at 20 Hz. Per frame, in fp16:

| What is logged | Per frame | Per simulated second |
|---|---|---|
| Mean over all tokens, 24 layers | 42 KB | 0.84 MB |
| Mean over the 30 driving queries, 24 layers | 42 KB | 0.84 MB |
| The 30 driving-query tokens kept individually, 24 layers (the "~35 token-vectors" above) | 1.29 MB | 26 MB |
| Every token, 24 layers | 24.7 MB | 490 MB |
| Exact preprocessed model input for replay (fp32 image tiles dominate) | 4.8 MB | 97 MB |
| The agent's own JPEG of the camera frame, which regenerates that input | ~150 KB | 3 MB |

Mean-pooled activations are cheap; the replay inputs are what cost storage.
SimLingo JPEG-encodes every camera frame at test time (to match its JPEG
training data) and the model only ever sees the decoded JPEG. Rerunning the
agent's own preprocessing on the saved camera frame reproduced the logged fp32
image input exactly (difference 0.0 on 14 of 14 frames), so storing those JPEG
bytes plus the small speed, target-point and prompt tensors is lossless for
replay and 32× smaller. That holds only with the same OpenCV and Pillow builds;
pin them and re-verify on Savio before relying on it there.

Store the **exact preprocessed model input losslessly** for every frame that may
be replayed — all failure-window frames at minimum. JPEG thumbnails are for the
gate only. Without this, the causal checks are not reproducible.

### 12.2 SAE training

Verified against Dr. VLA App. B.1 and Table 6 (Step 0, Track A).

- TopK architecture with an AuxK auxiliary loss, `k_aux` 512, aux coefficient
  1/32. JumpReLU as an ablation.
- **Expansion ratio 1.** At d = 896 that is a 896-latent dictionary.
  **d = 896 is confirmed** by strict-loaded checkpoint inference on 2026-10-02;
  the SimLingo paper itself does not state it. Every storage estimate and
  dictionary size here scales with it.
  Dr. VLA:
  *"larger expansion ratios lead to substantially more dead features while
  providing similar interpretability in our setting… likely due to the much
  smaller scale dataset sizes… in robotics."* **This is counterintuitive coming
  from LLM work — do not "fix" it.** 8×–32× is an ablation, not the default.
  (For reference, they used 0.5 on OpenVLA to hold the dictionary near 2048.)
- **k:** 100 at d = 2048, and 64 at d = 1024. No scaling rule is stated, so at
  d = 896 **sweep k ∈ {32, 48, 64}** rather than extrapolating.
- Adam (0.9, 0.999), lr 1e-4, batch 4096, 100 epochs, grad clip 1.0.
- Pre-bias initialized to the geometric median of 10k samples. Per-sample
  mean-subtraction and ℓ2 normalization. Unit-norm decoder columns with
  tangent-projected gradients. No encoder or decoder bias.
- Dead-latent threshold: no activation in the last 500 steps.
- **Six seeds**, checking that top features for a given episode recover
  consistently.
- Ablation operator for the causal check: `y' = y − (yᵀv)v`, applied at every
  token and, in their diffusion setting, every denoising step.

**The code is released** at `github.com/swannaiden/drvla`: SAE training, the
generality metrics, the general-vs-memorized classifier, a feature index and a
dashboard. It does **not** include steering or ablation code, and the hooks are
π0.5/openpi-specific, so the causal check (§9.2) is still ours to write. **There
is no LICENSE file — ask the authors before vendoring any of it.**

### 12.3 Fine-tuning

- SimLingo's own recipe, verified (paper §4.2 + appendix): LoRA r = 32, α = 64,
  dropout 0.1 on all the LLM's linear layers, and **every other component fully
  finetuned — the vision encoder is trained, not frozen.** SmoothL1 on waypoints,
  changed from L2 because of training instability. AdamW, lr 3e-5, weight decay
  0.1, cosine schedule with 5% warmup. 14 epochs on 8×A100-80GB in about 24 hours
  (≈192 A100-hours); batch 12 per GPU, 96 global.
- **Our repair step freezes the vision encoder, which is a deviation from that
  recipe, not an instance of it** (§9.4).
- For targeted co-fine-tuning, an 80/20 old/new mixture at reduced learning rate
  is a reasonable starting point from RoboART; the default here is a 1:1 targeted
  and replay mix, which is more conservative. State the deviation either way.
- Primary targeted volume 20k expert frames, with 5k and 50k as a sweep on the
  targeted condition only. Volume matters: published scaling curves show
  chain-of-thought supervision trailing action-only training below ~50k samples
  and overtaking it by ~100k on one benchmark, while action-only wins at every
  scale on another.

### 12.4 Evaluation protocol

- Bench2Drive: DS, SR, per-ability SR. DS is route completion times the product
  of infraction penalties; SR is the share of routes completed with no counted
  infraction and no timeout.
- Fail2Drive: DS, SR, harmonic mean. Route Completion omitted — their routes are
  short and nearly always finishable, so RC is uninformative.
- Log CARLA's minimum-speed infraction but **do not count it as failure**;
  Bench2Drive excludes it from DS, SR and ability scores.
- Treat a rollout as failed exactly when Bench2Drive marks it unsuccessful. This
  single definition is the unit behind every failure rate, efficacy check,
  reproduction test and remediation number in this document.
- Near misses (minimum time-to-collision under 1.5s) and expert disagreement are
  dense per-frame labels used for failure windows and axis cards, not rollout
  outcomes. **Hard deceleration is a feature, not a failure label** — correct
  emergency braking would otherwise count against the policy.
- The failure window is the 3 seconds before an infraction event.
- Three evaluation seeds, averaged, paired by route.
- **Evaluate closed-loop only.** Open-loop L2 misleads badly: a model averaging
  0.29 m L2 on nuScenes scores 0% success rate in closed loop on Bench2Drive, and
  roughly 74% of nuScenes is straight driving.

---

## 13. Steps

No workstreams. Each step has a spec, a done-condition, and an owner. We step
through them in order, and a step is not done until its done-condition is
demonstrated and logged. Specs live in `docs/steps/NN-name.md`.

Steps 0 through 3 are strictly sequential. From Step 4 onward some steps overlap,
and where a step is a sweep, both of us run arms of it.

**Step 0 — Ground the facts.** Read the four primary papers and settle every item
marked unverified above. Confirm Savio access end to end. *Done when: every
unverified flag in this document is either confirmed with a page reference or
struck, and both of us have run a trivial GPU job on Savio.*

**Step 1 — Smallest possible SimLingo rollout on Savio.** One route, one seed, in
the container, with measured wall-clock. Not the benchmark — one route. *Done
when: a single rollout completes on a Savio GPU node from a versioned config, and
we know its wall-clock cost and VRAM footprint.*

**Step 2 — Reproduce.** Bench2Drive-220, one seed, CoT off. *Done when: DS ≥ 75
from a versioned config, by whichever of us did not set it up, with the
Bench2Drive version and checkpoint hash recorded.*

**Step 3 — Hooks and the activation store.** Capture at the candidate sites,
losslessly store replay inputs, verify determinism. *Done when: replaying a
logged frame offline reproduces the logged waypoints to within 1e-3 m, and a
rollout writes a shard the reader can load.*

**Step 4 — Dev pool and the layer sweep.** A couple hundred rollouts logging all
layers, then the sweep: probe AUROC for failure versus success, probe R² for the
state list, practice-gap recovery. *Done when: 2–3 layers and sites are chosen
and written into the config, with the sweep results committed.*

**Step 5 — Gap candidates and efficacy.** Build candidate regions, run the
efficacy pilots, keep what survives. *Done when: 4–6 gaps plus 2 decoys pass the
§9.1 thresholds with measured statistics, the count of candidates tried is
recorded, and no single-factor stratum has expected Jaccard ≥ 0.4 with any
interactional gap.*

**Step 6 — The cheap baselines, including the dangerous one.** Random, human
taxonomy, behavioral stratification, and **rollout-free activation statistics**.
*Done when: all four emit directives in the §8.3 schema on the dev pool. If B7
recovers the practice gaps as well as our methods do, stop and re-plan before
building the rollout corpus.*

**Step 7 — Discovery on dev.** All three methods, both preprocessing variants.
Sweep. *Done when: each method emits schema-valid directives on dev, and the gate
runs with its shuffle control reported.*

**Step 8 — Seal, freeze, generate, score.** Seal the key, hash-commit, generate
the test pool, freeze methods, run everything once, score once. *Done when the
scoring report exists and every tag is in git in the right order.*

**Step 9 — Causal checks and the go/no-go read.** *Done when: every top axis has
a causal verdict against matched controls, and we have decided whether discovery
beat behavioral stratification on interactional gaps.*

**Step 10 — Closed loop.** Reproduction tests, scenario authoring, generation,
LoRA, controls, regression. *Done when one full cycle has run with the
no-degradation check reported, every authored scenario passes solvability, and no
Fail2Drive asset was trained on.*

**Step 11 — Adapter refactor and the stub.** Only now, by refactoring what works.
*Done when the stub adapter runs the pipeline end to end on a toy policy.*

**Step 12 — Write.** Continuous from Step 8, not a phase.

### 13.1 The go/no-go read

At Step 9 we decide. Two conditions:

1. **Harness validity.** At least one control gap recovered by at least one
   method using the non-residualized variant, **and** at least two interactional
   gaps re-confirming efficacy on the test pool.
2. **Activation advantage.** The best activation method beats *every* baseline on
   interactional-gap recall, and its mean best Jaccard is at least 0.15 above the
   best baseline's with a 95% interval excluding zero, bootstrapped over routes
   with both "best" selections re-made in every replicate.

If both hold, go to the closed loop. If validity holds but advantage does not, the
paper is the comparative study — honest, real, and on a benchmark nobody has
built. If validity fails, the paper is the negative result about planting gaps,
and the remaining time goes to fixing the harness.

Deciding this *before* seeing the numbers is the entire point. Write the rule into
`harness/PREREGISTRATION.md` and do not edit it afterward.

## 14. Repository

```
adapters/          simlingo/, stub/ — the §8.2 interface, one dir per policy
capture/           hooks, streaming activation extraction, replay inputs
gaps/
  specs/           gap definitions, readable
  sealed/          predicates + answer key — git-ignored, scoring code only
  pipeline/        candidate generation, efficacy checks
discovery/         contrastive/, sae/, probe_residual/, preprocessing/
baselines/         random/, taxonomy/, behavioral/, enumerated/, domino/,
                   detector/, activation_stats/
gate/              describability gate + shuffle control
harness/           config schema, Ray runner, results DB, metrics, PREREGISTRATION.md,
                   KEY_COMMITMENT.txt
generation/        scenario authoring, solvability checks
repair/            targeted data + LoRA + replay
analysis/          figures, tables, protocol tooling
configs/           every experiment, versioned, content-hashed
docs/              this PRD, CONFLICTS.md, steps/, WHAT_BROKE.md, decisions log
upstream-99p/      the 99p repo as pulled, read-only reference
```

**Conventions.**

- Every experiment is a YAML config. Results are keyed by config content hash.
- No notebooks on main. Exploration lives in `analysis/` as scripts.
- CI check: nothing under `discovery/`, `baselines/`, or `gate/` may import from
  `gaps/sealed/`.
- Adapters depend only on `harness/` interfaces, never on each other.
- Each top-level directory gets a `CLAUDE.md` stating its local contract, so an
  agent working there reads its constraints without loading this whole document.

## 15. Venue ladder

No single deadline. We submit at whatever rung the results have reached, and
having targets at several time scales means a result is never stranded.
**Recheck every date before acting on it** — several in the brief had already
passed when it was written.

- **Nearest archival, ~6 pages:** IEEE IV 2027, mid-November. Best fit for a
  discovery-only or comparative result.
- **Archival extended abstract:** RSS 2027 Stage 1, early December, with an
  invited full paper the following April — which means a discovery result can go
  in while the closed loop finishes.
- **High bar:** CVPR 2027, mid-November.
- **Non-archival, in person:** AAAI-27 and ICLR 2027 workshops, roughly late
  November and February.
- **Rolling:** IEEE RA-L, which transfers to IROS presentation; IEEE T-IV for the
  journal version with full closed-loop results.
- **Fallback archival conference:** IROS 2027, early March.

Do not submit substantially the same work to two venues whose review periods
overlap. The course poster symposium happens regardless.

## 16. Open decisions

Items 1 and 2 close before Step 5 writes code.

1. ~~**SAE expansion ratio.**~~ **Closed 2026-10-01: ratio 1**, confirmed from
   Dr. VLA App. B.1 (§12.2). The brief was right; 8×–32× is an ablation.
   Successor question: **k at d = 896**, which has no stated scaling rule —
   sweep {32, 48, 64}. *Step 7.*
2. **Gap portfolio size** — bounded by measured rollout throughput from Step 1
   and Savio's actual SU rate, not by the brief's guess. *Step 1.*
3. **Hook point** — residual stream versus waypoint query tokens versus vision
   bridge. Sweep (§9.2). *Step 4.*
4. **Layer and aggregation.** Sweep. A legitimate compute use. *Step 4.*
5. **Primary discovery method** — contrastive, SAE, or probe residuals. Must be
   named before the test pool is generated, because the random baseline's set
   sizes and the closed-loop target rule both key off it. *Step 7.*
6. **Which benchmarks for the no-degradation check** — Bench2Drive, Fail2Drive,
   or both. *Step 10.*
7. **Second policy for the cross-model check**, and whether it survives at all.
   Candidate: Drive-π0 from the DriveMoE repo, PaliGemma-3B based, trained on
   Bench2Drive data organized so a slice is a folder filter. *Step 11 or cut.*
8. **Describability model** — a pinned open model, with the exact ID logged, and
   a closed API only as an optional comparison. *Step 7.*
9. **B7's gap signal.** Memorized-feature concentration as a gap signal is our
   construction, not Dr. VLA's, so it needs a written definition before it can be
   a fair baseline (§9.3). *Before Step 6.*
10. **Dr. VLA code licensing.** The repo has no LICENSE file. Ask the authors
    before vendoring anything from it; reimplement from the paper if they decline.
    *Step 7, but email now.*
11. **Bucket weights**, PDMLite-F2D standalone usability, and the Fail2Drive
    toolbox API surface remain open. *Steps 1–2.* The strict-loaded released
    SimLingo model confirms Qwen2 hidden size 896 and 24 decoder layers as of
    2026-10-02. Query parameters live at `adaptors.driving.query_embeds_wps` and
    `adaptors.driving.query_embeds_speed`; their readouts are `route_head` and
    `speed_wps_head`. The pinned SimLingo source includes Bench2Drive 0.0.3.

**Closed, versus the brief:** fine-tune cost is no longer blocking, because Mode B
needs no fine-tune for planting. Delete-versus-regenerate is deferred with Mode A.
Interestingness-sampler distortion is a Mode A question. Serving stack is cut
(§11).

## 17. Compute

**Source of truth: the Data Discovery Program's own Savio documentation at
<https://datadisco.cdss.berkeley.edu/savio/> and its subpages.** Anything here
that contradicts it is wrong; anything not covered there goes to the program's
support contact, not to guesswork.

### 17.1 Access

Cluster: Savio, Berkeley Research Computing, via SSH to `hpc.brc.berkeley.edu`.
Project: **`ic_cdss170fall`**. Chris's account is registered under it.

Per-user steps, in order: sign the cluster user access agreement on first login;
join the project under "My BRC Cluster Projects" in the MyBRC portal; set up
one-time-password authentication. Login is a PIN plus a 6-digit authenticator
code. **Jerry needs to complete these too, and it is not instant.** This blocks
Step 1, so it happens now.

**The `ic_` prefix matters.** This is an Instructional Computing Allowance held by
the program — not a faculty allowance, not a condo. Two consequences: usage is
tracked and deducted from a fixed pool, since only condo jobs are untracked; and
the pool is shared across the program rather than reserved for us. Our budget is a
slice of a shared allocation, which is a stronger reason to size experiments
deliberately than a private allowance would be.

Savio is approved for **unclassified, non-proprietary fundamental research** only.
Our work is public and open-source, so this is fine — but if 99P Labs ever
supplies an internal dataset or a proprietary checkpoint, it cannot run here.
Raise that with Ryan before accepting any such data.

### 17.2 Job submission

Every submission needs an account, a partition, and a time limit. QoS options:
`savio_normal` as default; `savio_debug` for brief testing; `savio_lowprio`,
which is preemptible. **Use lowprio for rollout fan-out** — rollouts are
independent and individually cheap to lose, which is exactly the workload
preemption suits. Do not use it for fine-tunes without checkpointing.

Job arrays are supported and are the fallback fan-out mechanism. We drive
rollouts and sweeps through **Ray** instead (§11), launched inside a Slurm
allocation — one orchestration layer for rollouts, the layer sweep and the
baseline matrix, portable off Savio. Preemption under `savio_lowprio` interacts
with a long-lived Ray cluster, so size allocations to survive it: prefer several
shorter allocations over one long one, and make rollout tasks idempotent and
individually re-runnable so a lost worker costs one rollout rather than a batch.
If Ray on Slurm fights us for more than a day, fall back to a plain job array and
move on — the fan-out mechanism is not the contribution.

### 17.3 What the budget is spent on

**Throughput.** The design multiplies: a rollout corpus large enough for
unsupervised structure to be visible, run against the base model and each
fine-tuned variant, at three seeds per condition, with seven baselines over the
same corpus. Thousands of rollouts before any ablation.

The number that decides everything: **SimLingo runs at roughly 0.045–0.065× real
time** on a consumer GPU, using about 11.4 GB including the CARLA server. A
third-party fork reports roughly 60 minutes per 300 simulated seconds on an A6000
— but with inference every 5th frame, which is not the released configuration, so
expect worse with per-frame inference. A thousand-plus-rollout campaign plus
efficacy pilots and baseline rollouts is on the order of **300–1,000
GPU-hours.** Fix the real budget from the Step 1 measurement.

**Storage.** Roughly 150 GB for activations and images at three layers, plus the
training dataset if Mode A ever runs. Confirm the quota.

**Not justified:** training a driving VLA from scratch. It would consume the
paper.

### 17.4 Unresolved, and who to ask

The program docs do not state the GPU partition names available to
`ic_cdss170fall`, the Service Unit charging rate for GPU jobs, the maximum wall
time, or the storage quota. **All four now matter more, not less**, because the
cost estimates we inherited were sized for different hardware, and GPU-hours are
not the unit we are billed in. Ask the program's Savio contact at
<https://datadisco.cdss.berkeley.edu/support> rather than inferring from general
Research IT documentation, since allowance terms are set per agreement.

**Fallback.** NRP Nautilus is available through the program: an OpenAI-compatible
LLM gateway plus GPU pods, where interactive pods are capped at 16 CPU / 32 GB /
6 hours so rollouts must run as batch jobs, A6000/A40/L40-class GPUs are freely
requestable, and A100 needs a quota request. Use it for the describability model
and as overflow. Pin and log model IDs; the roster rotates.

## 18. Non-goals and what we will not claim

- **No real-vehicle results.** Everything is CARLA.
- **No sim-to-real transfer claim.** Robustness in simulation is not sufficient
  for real-world robustness, but it is a necessary prerequisite. Say that, claim
  nothing more.
- **No cross-domain generality claim.** We will not demonstrate that this
  transfers to manipulation. Manipulation confounds are listable, which is
  precisely the condition our argument says does not hold in driving. Running
  there would put us on the competitor's home turf with our weakest argument.
- **No test-time-scaling or verifier contribution.** A verifier may appear as
  implementation detail. The lane is crowded and it is not our paper. See §19.
- **No failure-detection contribution.** SAFE and a 2026 wave of detectors own
  that. Detection appears only as baseline B6.
- **No world-model counterfactual validation.**
- **No UI, dashboard, or web frontend.**
- **No claim that driving is novel.** It is the setting, not the contribution.
- **No text-corpus track.** The project's earlier dual-track framing — a text
  knowledge system alongside the policy work — is dropped. If the course requires
  a text deliverable, that is a conversation to have early, not a scope change to
  absorb quietly.

**And a standing rule: never state a target as a result.** The inherited
documents are full of aspirational figures — ">85% precision", ">80% failure
reduction" — that were never measurements. Anything in this document that is not
yet measured is marked as unverified or as a target.

## 19. The second paper

Stated so nobody drifts into it early.

Discovered axes tell you *where* a policy is uncertain, which is exactly where
test-time compute should be spent — sampling more, and reranking, on high-risk
axes rather than uniformly. Same infrastructure, same adapters, clean sequel. It
is deliberately excluded so that our results stay attributable to the discovery
system rather than to a sampling strategy layered on top.

Sequential, not parallel. Spring.

## 20. Risks

**Bring-up overruns.** The single most likely failure mode, and both source
documents independently say so. The policy runs 15–20× slower than real time and
the one public reproduction attempt fell 9 DS short of published. Mitigation:
Steps 0–3 are deliberately small and sequential, and Step 1 is one route rather
than a benchmark. Cut order if it slips: second policy first, then the image-edit
baseline variant, then the results database. Scattered files are survivable; an
unreproducible baseline is not.

**The rollout-free baseline wins.** Dr. VLA's metrics need no rollouts. If they
recover gaps as well as our pipeline, the compute story and half the motivation
go with them. Mitigation: it is Step 6, before the corpus is built. It would
still be a paper — a negative result about when expensive discovery is worth it —
but we need the runway to write that one instead.

**Planted gaps do not cause failures.** The silent killer. Mitigation: the
efficacy check (§9.1), re-confirmed at scoring, plus decoys to catch novelty
masquerading as failure.

**Natural failures swamp planted ones.** SimLingo already fails half the time on
merging, overtaking and give-way. Mitigation: power analysis on dev, prevalence at
the top of the 4–8% range, gaps aimed at known-weak abilities, and validated
natural axes reported rather than discarded.

**Activations cluster by appearance, not decisions.** High likelihood — deep
networks encode lighting and weather far more strongly than subtle decision
logic. Mitigation: action-residual orthogonalization, nuisance projection,
control gaps as positive controls, and reporting raw alongside residualized.

**Describability fails, or the gate rubber-stamps.** An axis nobody can name is
not a discovery; a gate that passes everything is not a gate. Mitigation: the
held-out AUROC test with the shuffle control as the measured false-positive rate,
tested early on a small corpus.

**The generator cannot express an axis.** Mitigation: a rich scenario schema
including occluders and relative kinematics; report non-parameterizable axes as
findings rather than hiding them.

**Infrastructure as an excuse.** The inverse risk. §11 states plainly which
machinery is chosen rather than necessary, and §11 cuts three things the brief had
approved. If we are still polishing infrastructure late, it has become the
project.

**Key leakage or post-hoc tuning.** With two people there is no real separation of
duties, so the protection is entirely mechanical: hash commitment before the test
pool exists, frozen method tags, one scoring run, key revealed only after specs
and causal checks are committed. If we edit a method after the freeze tag, it is a
new version and gets reported as one.

**Prior-art scoop.** The field is moving fast and the closest papers are months
old. Event-grounded SAEs and Dr. VLA are the nearest; RoboART is the most likely
to be cited against us. One of us owns a monthly re-check, by name, and a full
sweep with web access before any submission.
