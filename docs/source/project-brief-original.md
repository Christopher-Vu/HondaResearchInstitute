# PRD — Unsupervised Failure-Axis Discovery for Driving Policies

**Status:** grounding document. Supersedes `prd-full.md`, `prd-short.md`, and
`project-brief.md`.
**Deadline:** December, self-imposed. No venue is locked in; an
interpretability-oriented workshop is the likely target and the mentor has not
constrained us.
**Audience:** the team and their agents. Anything here can be assumed as
context; anything not here is open.

---

## 1. One paragraph

When a driving policy fails, the practitioner wants to know what data to collect
next. The state of the art answers this by writing down a list of candidate
failure factors and measuring degradation against that list, which can only
surface failures a human already hypothesized. We are building a tool that
derives failure axes directly from a policy's internal representations with no
factor list, validating it against deliberately planted gaps in the training
data, and closing the loop by generating targeted scenarios and showing the
failure rate drops.

## 2. Glossary

Used consistently throughout. Agents should use these terms and not synonyms.

- **Axis** — a named, human-describable dimension along which a policy's
  performance degrades. Not a single scenario and not a scalar score. "Yields to
  oncoming traffic only when the oncoming vehicle is unoccluded" is an axis.
- **Planted gap** — a slice of training data deliberately withheld before
  fine-tuning, whose identity is recorded in a sealed answer key. The ground
  truth against which discovery is scored.
- **Control gap** — a planted gap that should be trivially recoverable by every
  method, included to demonstrate the harness has range. If nothing recovers the
  control gap, the harness is broken, not the methods.
- **Directive** — the tool's output: a ranked list of axes, each with supporting
  episodes and a parameterization spec describing what data to collect.
- **Describability** — the property that a human shown an axis's top-activating
  episodes can name what they have in common. An axis that fails this is not a
  discovery regardless of its numbers.
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

Fail2Drive evaluated SimLingo on a scenario where pedestrians walk in the ego
lane and the correct behavior is to slow and follow at a safe distance.
SimLingo's harmonic-mean score drops from 98.50 to 19.68, with collisions in 87%
of episodes. The documented mechanism: the language-action module hallucinates a
vehicle or cyclist that does not exist and follows it, because following cues in
training were always vehicle-shaped.

This is our paper's motivating example, and it is worth being precise about why.
The failure is not "pedestrians" — pedestrians are in the training data
everywhere. It is the conjunction of pedestrian, ego lane, sustained low speed,
and a following behavior learned only from vehicles. No factor list contains
that conjunction. But it is a coherent, nameable axis, and the policy's own
internals are where the vehicle-shaped following prior lives.

### 3.3 Why now

Two papers published within the last year set this up and neither takes the
step. The enumerate-and-test method's own limitations section names both halves
of our contribution: vulnerabilities not visible in observations, and iterative
rather than single-shot exploration of the factor space. The SAE-on-VLAs paper
concludes by proposing that episode-specific features could diagnose fine-tuning
brittleness and that feature metrics could serve as a training-time proxy for
generalization — our thesis, unclaimed and untested.

## 4. Related work: what exists and where we sit

Read this section before proposing anything. Three adjacent ideas are already
taken and a fourth is our direct competitor.

### 4.1 Predictive red teaming / RoboART (arXiv 2502.06575, DeepMind + Princeton)

**The competitor.** Pipeline: a human enumerates environmental factors; nominal
observations are edited with Imagen 3 to reflect each factor; a Gemini VLM critic
filters four candidate edits per input for fidelity; degradation is predicted by
an anomaly detector that measures mean k-nearest-neighbor cosine distance in
*policy embedding space*, thresholded by conformal prediction.

Results: 12 factors, 500+ hardware trials, two visuomotor diffusion policies at
~65% nominal success. Spearman ρ of 0.8 and 0.7 between predicted and true factor
rankings; average absolute success-rate prediction error 0.10 and 0.19. Targeted
collection of ~100 trajectories each for the worst three factors, co-finetuned at
an 80/20 old/new mixture, lr 5e-6, 20K steps, gives 2–7x improvement in those
conditions and 2–5x in conditions where no data was collected.

**Correction to earlier framing, which matters.** RoboART already uses internal
representations — the anomaly score is computed in the policy's own embedding
space. Do not write "internals versus behavior." The axis of comparison is
**enumerated factor list versus unsupervised discovery**, and secondarily
**single-frame observation edits versus temporal, interactional structure**. A
reviewer will know this; getting it wrong costs credibility immediately.

Also note the setting: visuomotor diffusion policies on a Kuka grasping task.
Not VLAs, not driving, not language-conditioned.

### 4.2 SAFE (arXiv 2506.09937, UofT + TRI, NeurIPS 2025)

Trains a small MLP or LSTM head on VLA hidden states to emit a scalar failure
likelihood, thresholded by functional conformal prediction for a time-varying
band. Features are taken from the final layer before decoding into token logits
or a velocity field. Feature aggregation is ablated over First / Last / Mean /
First&Last; the real-world configuration is pre-logits features with Mean
aggregation. Evaluated on OpenVLA, π0, π0-FAST by ROC-AUC, balanced accuracy,
and detection time. Detector training takes under a minute.

**Our relationship to it.** SAFE detects per-episode failure and raises an alert.
We aggregate across a corpus and emit a data directive — a different object. We
take their hooking location and aggregation ablation as settled engineering
rather than rediscovering them. Their sub-minute training cost means a
SAFE-style verifier is nearly free if we want one.

### 4.3 SAEs on VLAs / Dr. VLA (arXiv 2603.19183, Stanford)

Trains sparse autoencoders on residual-stream activations of π0.5 and OpenVLA.
Contributions we care about:

- **Generality metrics requiring no rollouts:** episode coverage, mean onset
  count, mean activation magnitude, relative run length. A logistic regression
  over these four, fit on 30 hand-labeled features, classifies every feature as
  general or memorized (LOO accuracy 100% on LIBERO, 96.7% on DROID).
- **A describability protocol:** sample features, label one interpretable when
  its temporal activation pattern consistently aligns with an identifiable
  sensorimotor event. 95 of 120 sampled SAE features were interpretable (79.2%),
  against 30% for an FFN-neuron baseline under an identical pipeline.
- **Causal validation by ablation:** removing the four most general features
  drops real-world success to 0/40.
- **A released package** for SAE training, feature evaluation, and steering.

**Two consequences.** First, this solves our describability problem — adopt their
protocol rather than inventing one. Second, their metrics are a *baseline we must
beat and which costs almost nothing to run*, because they need no rollouts at
all. If activation statistics over the fine-tuning data recover planted gaps as
well as our rollout-based pipeline does, our compute story collapses. Run this
early (see §12, October).

Their stated limitation is useful to us: clean top-activating examples do not
imply steerability — predictive is not causal. Our closed loop is a causal test,
which is a legitimate methodological advantage over steering.

### 4.4 RESample (arXiv 2510.17640)

Trains a conservative coverage function estimating whether a state-action pair is
supported by the demonstrations, then samples exploratory deviations followed by
recovery, selecting trajectories that maximize the minimum of a deviation score
and a recovery score. Up to 12% absolute gain on LIBERO with ≤20% added samples.

The nearest non-enumerated competitor. It finds coverage gaps without a factor
list — but it outputs trajectories, not a nameable axis, and it is manipulation.
**Related work, not a baseline** (see §9.3 for the reasoning).

### 4.5 Fail2Drive (arXiv 2604.08535, Tübingen)

A paired-route closed-loop generalization benchmark in CARLA: 200 routes in Town
13, 17 new scenario classes, 100 in-distribution/generalization pairs where only
the targeted shift varies. Metrics are Driving Score, Success Rate, and their
harmonic mean. Ships a scenario-authoring toolbox, new assets, and PDMLite-F2D, a
privileged rule-based expert usable as a solvability check on newly authored
scenarios.

**Two things this gives us and one rule that binds us.** It gives us SimLingo's
generalization profile (§10.1) and a ready-made held-out measurement for the
"did not degrade general performance" claim. It gives us an authoring toolbox and
a solvability checker, which de-risks scenario generation substantially.

The rule: **models must not train or fine-tune on Fail2Drive routes, scenario
definitions, or assets.** It is strictly a held-out test set. So our generated
training data must be authored with the toolbox but not drawn from their
benchmark scenarios or assets. This is a hard constraint on Workstream E.

### 4.6 The driving VLA landscape

DriveVLM, DriveMoE, SimLingo, LatentVLA, AutoVLA, Orion, HiP-AD, TransFuser++,
PlanT 2.0. The domain is crowded and mature. **Driving is not our novelty and must
never be pitched as such.** It is the setting where the enumeration argument
actually bites.

---

## 5. The claim

> Failure axes derived without supervision from a driving policy's internal
> representations recover data gaps that enumerated-factor analysis, behavioral
> success-rate stratification, and rollout-free activation statistics all miss,
> and targeted data generation along those axes closes the corresponding
> failures.

Three independent ways this can fail, and what each means:

1. **Axes are not recoverable.** Discovery returns nothing that maps to a planted
   gap. Dead end for the main claim; pivot per §12.
2. **Recoverable but not better than the baselines.** Still a paper — an honest
   comparison of four directive-generation methods on a benchmark nobody has
   built. This is the fallback and it is a real contribution.
3. **Better but not actionable.** Axes recover gaps, but generating along them
   does not close failures. Also a paper, and an interesting one: it would mean
   discovered structure is diagnostic but not prescriptive.

Only (1) leaves us without a result.

## 6. What we want out of this, independent of results

These hold if the research pivots. They are constraints on *how* we work, not
just nice-to-haves.

### 6.1 Outcomes

- **A paper.** Venue flexible.
- **A citable artifact.** The tool is the thing we expect to be cited, not the
  method. That means it must run on policies that are not SimLingo — see §7.
- **A released planted-gap benchmark.** Second citable object. Benchmarks get
  cited more than methods.
- **Everyone with a causal hand in the substantive results.** Where work can be
  structured as *shared setup → everyone runs their own ablations in parallel →
  compare and converge on the best configuration*, structure it that way. This is
  a design preference for how tasks are split, not a scheduling nicety: it means
  each person has actually run the experiment rather than having built one piece
  of it. It makes Workstream B load-bearing (§13).
- **Coverage across training, serving, and infra** rather than everyone in one
  lane.
- **A write-up of what broke.**

### 6.2 Technology

Preferences, not requirements. Any plan should justify each or propose better.
"Familiar" is not a justification. See §11 for which of these are scientifically
necessary and which are chosen.

- Serving: vLLM or Triton, containerized (Docker), measured throughput/latency.
- Orchestration: Ray, for rollout fan-out and fine-tuning.
- Tracking: Weights & Biases.
- Training: PyTorch; LoRA (already SimLingo's recipe); versioned configs;
  checkpointing.
- Results: a database. Any number in the paper reproducible from a query.
- Sim: CARLA 0.9.15 (Fail2Drive's build), authored via the F2D toolbox.

### 6.3 Workflow

- GitHub repo, everything in it.
- Agents write most or all code. Humans review before merge.
- Configs versioned with code; no result that cannot be regenerated from a config
  hash.
- Nothing outside Workstream C reads the sealed answer key. Enforced by repo
  layout (§14), not by good intentions.
- One named person owns re-checking arXiv, monthly. The closest papers are months
  old.

## 7. Honda and AV relevance

One paragraph, because it should be statable in a sentence and not belabored.

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
it unusable outside simulation. Generation is how *we* validate (Workstream E),
not part of what we ship.

### 8.2 Adapter interface

The generality claim is exactly as strong as this interface is small. A policy is
usable if its adapter exposes three things:

1. **Rollouts** — run the policy in its environment, return per-episode
   observation/action sequences.
2. **Activations** — per-timestep internal state at a specified hook point,
   mean-pooled over tokens by default (following Dr. VLA; per-token is optional
   and, in their experience, less interpretable).
3. **Success labels** — a per-episode binary or scalar outcome.

Ship two adapters: SimLingo, and a deliberately minimal stub that proves the
interface is implementable by someone who has not read our code. Do not design
this interface up front. Build it by refactoring *after* SimLingo works,
otherwise September is spent on abstraction rather than on a working system.

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
parameterization:            # what data to collect
  scenario_family: str
  parameters:
    - name: str
      range: [min, max]
      units: str
provenance:
  method: str                # sae | clustering | contrastive | baseline_name
  config_hash: str
  layer: str
  aggregation: str
```

`name` and `description` are human-written under the §9.2 protocol and are not
optional. An axis without them is a cluster, not a discovery.

### 8.4 Retrospective validation mode

Given held-out data the user already has, confirm the policy actually
underperforms on the flagged slice. No generation needed, works for any adapter,
and it makes the tool self-checking rather than trust-me. A reviewer will ask how
a user without a simulator falsifies a directive; this is the answer.

---

## 9. Method

### 9.1 Planted gaps (Workstream C)

The methodological contribution. Everything else is downstream of whether this is
built carefully.

**Procedure.** Before fine-tuning, remove a known slice of the training corpus.
Fine-tune. Run discovery. Score recovery against the sealed key.

**The worked example — use this as the template.**

```yaml
gap_id: occluded_left_turn_yield
type: interactional
description: >
  Left-turn-across-traffic events where the oncoming vehicle is occluded at
  decision time by a stopped or slow vehicle in the adjacent through lane.
predicate: |
  frame.ego_maneuver == "left_turn_unprotected"
  AND exists(actor: oncoming, conflicting_path)
  AND line_of_sight(ego, oncoming) blocked_by(actor: adjacent_lane, v < 2 m/s)
  AND t_to_conflict in [1.5, 4.0]
expected_matches: TBD          # measured, not guessed; see §16 item 2
removal_method: regenerate     # see below
correct_discovery_output: >
  An axis naming occlusion of oncoming traffic during unprotected left turns,
  or a superset that clearly includes it (e.g. "acts on visible agents only").
test_parameterization:
  scenario_family: unprotected_left
  parameters:
    - name: occluder_offset_m
      range: [0, 12]
    - name: oncoming_velocity_ms
      range: [4, 16]
    - name: occluder_velocity_ms
      range: [0, 2]
```

**Gap portfolio.** Three to five total, budget-bound (§16 item 1), spanning:

- One **control gap** — trivially recoverable. A weather or time-of-day
  condition. If no method recovers it, the harness is broken.
- Two to three **interactional gaps** like the example above. These are where the
  claim lives.
- One **near-miss gap** — a slice that is *nearly* listable, to probe where
  enumeration starts to fail rather than only showing the extremes.

**Removal method.** Two options, and this is an open decision (§16 item 2):
*delete* the matching frames, which shrinks the corpus and confounds the
comparison with a data-quantity effect; or *regenerate* with the PDM-Lite expert
so corpus size is held constant and only the slice's content changes. Regenerate
is methodologically cleaner and costs pipeline work. Decide before C starts.

**A confound to check.** SimLingo's training samples 650k of 3.1M per epoch
through interestingness buckets. Slice removal interacts with that sampler: a
removed slice may be over- or under-represented in the buckets, so the effective
removal is not the nominal one. Measure the post-sampler removal rate and report
it.

**Sealing.** Predicates and the key live under `gaps/sealed/`, owned by C, and
are not read by discovery or baseline code. Enforced by repo convention and by
CI check (§14). A leaked key invalidates the headline metric.

### 9.2 Discovery (Workstream D)

Collect activations across a large rollout corpus spanning many scenario
variations. Derive candidate axes from structure in those activations with no
factor list.

**Candidate methods**, to be swept rather than chosen up front:

- SAE features correlated with failure (primary; infrastructure exists)
- Clustering in a probe's residual space
- Contrastive directions between success and failure activation distributions

**Describability protocol** — adopted from Dr. VLA, not invented:

1. Sample candidate axes (a fixed number, pre-registered, not cherry-picked).
2. For each, render top-activating episodes with per-timestep activation
   overlaid on frames.
3. A rater labels the axis interpretable when its temporal activation pattern
   consistently aligns with an identifiable event, state, or phase.
4. Report the interpretable fraction against a baseline basis (raw neurons),
   through an identical pipeline. Dr. VLA's numbers — 79.2% vs 30% — are the
   reference point.
5. Raters do not have access to the sealed key.

**Hook point.** Open decision (§16 item 4). SimLingo has two candidates: the LLM
residual stream (Qwen2-0.5B, analogous to Dr. VLA's PaliGemma layers), and the
learnable waypoint query tokens before the MLP head (analogous to SAFE's
pre-logits). The commentary chain-of-thought means the LLM carries a lot of the
reasoning, so both are plausible. Sweep, do not guess.

### 9.3 Baselines

Three, after the cut. Each must run on the same corpus, through the same harness,
scored by the same metrics.

1. **Behavioral stratification.** Group rollouts by observable scenario
   attributes, rank by success rate. Nearly free — the rollouts already exist,
   this is grouping and ranking. This is the go/no-go gate in §12: if internals
   do not beat plain success rates at recovering planted gaps, the
   interpretability framing collapses and we pivot immediately.
2. **Enumerated-factor prediction (RoboART-style).** A human-written factor list
   plus image-edit-based degradation prediction plus an embedding-space anomaly
   detector. The head-to-head that carries the claim. Most expensive baseline to
   build; budget accordingly.
3. **Rollout-free activation statistics (Dr. VLA-style).** Episode coverage,
   onset count, activation magnitude, relative run length over the fine-tuning
   data; classify general vs memorized; treat memorized-feature concentration as
   a gap signal. Cheap and dangerous — if this wins, our rollout corpus is not
   justified. Run it in October, not November.

**Cut, with reasoning:** RESample-style coverage functions. They find gaps
without a factor list, which makes them conceptually relevant, but they output
trajectories rather than nameable axes and the method is manipulation-specific.
Related work, one paragraph.

### 9.4 Closed loop (Workstream E)

Take a discovered axis, parameterize a scenario family along it using the
Fail2Drive toolbox (authoring our own scenarios, **not** their benchmark
scenarios or assets — §4.5), validate solvability with PDMLite-F2D, generate
training data, fine-tune, and measure whether failures on that axis close.

One full cycle minimum, two if infra holds. Run the loop on one policy only;
a second closed loop buys little (§11).

## 10. Evaluation

### 10.1 Reproduction targets

"Reproduced" means a number, not a vibe. SimLingo's published results, as
reported in Fail2Drive:

| Benchmark | Metric | Target |
|---|---|---|
| Bench2Drive | DS | 85.1 |
| Fail2Drive in-distribution | DS / SR / HM | 82.6 / 79.3 / 80.9 |
| Fail2Drive generalization | DS / SR / HM | 71.7 / 55.0 / 62.2 |

Category-wise generalization HM, useful for sanity-checking that our setup
reproduces the *shape* of its weaknesses and not just the average: Behavior 31.2
(−64.2%), Visual-lateral 45.9 (−32.2%), Visual-longitudinal 71.1 (−9.0%),
Robustness 86.8 (−5.9%).

Accept reproduction within a tolerance we state in advance and record in the
harness. Three evaluation seeds, following Fail2Drive's protocol.

### 10.2 Primary metrics

- **Planted-gap recovery: precision and recall**, per method. The headline.
- **Spearman rank correlation** between each method's ranked directive and the
  true severity ordering of planted gaps. This is RoboART's metric; reporting it
  makes the head-to-head legible to anyone who has read that paper.
- **Failure-rate reduction after targeted fine-tuning**, per axis source.
- **Interpretable fraction** of proposed axes, per method, under §9.2.

### 10.3 Secondary

- **Coverage of interactional gaps specifically**, separated from control and
  near-miss gaps. This is where enumeration is predicted to fail and the
  separation is the argument.
- **Cross-model check.** Does an axis found in SimLingo surface in a second
  policy? A shared axis is a claim about the data distribution rather than one
  model, which is stronger. Also a real distributed-evaluation problem. First
  thing cut if September runs long.
- **No-degradation check.** Benchmark performance before and after targeted
  fine-tuning, to show we closed an axis without breaking general driving. Report
  on Fail2Drive (held out by rule, so clean) and Bench2Drive.

---

## 11. What we build versus what we take

Rule: the code should be minimal and explorable. Take anything that does not need
changing. Where we build something anyway, say honestly whether it is
scientifically necessary or an infrastructure choice — machinery with a
retrofitted justification is how a codebase turns into slop.

**Take, do not build.**

- SAE training stack — Dr. VLA is released, with hyperparameters (§12.2).
- Describability protocol — adopt as-is.
- SimLingo training, evaluation, and LoRA recipe.
- Fail2Drive scenario toolbox, custom CARLA build, PDMLite-F2D solvability check.
- CARLA.

**Build — no source exists.**

- **The planted-gap harness.** Nobody has built this. It is the contribution.
- **The adapter interface.** Generality is the tool's claim; it cannot be
  borrowed.
- **The comparison layer** that puts three methods on one corpus under one metric.
  Every paper evaluates its own method its own way; the comparison is ours.

**Build, necessary and wanted.**

- **Streaming activation capture inside the serving path.** Dr. VLA captures
  mean-pooled activations offline on manipulation episodes. We need capture
  during closed-loop driving rollouts at scale. Genuine rewrite.
- **The evaluation harness.** Existing benchmarks evaluate one model at a time.
  We need config-in / comparable-numbers-out across many variants and many
  people, which is what makes the §6.1 parallel-ablation model possible.

**Build, wanted but not scientifically necessary.** Stated plainly so nobody
invents a justification later:

- **The serving stack (vLLM/Triton).** Honest accounting: SimLingo runs a 4 fps
  closed loop on a 1B model, so per-step latency, not throughput, dominates. The
  stack is justified by *parallel rollout fan-out across the cluster*, not by
  making any single rollout faster. Real engineering, weaker scientific
  necessity.
- **Re-implementing the image-editing baseline** rather than adapting the
  published pipeline.
- **Ray.** Cluster job arrays would do it.

All three are approved. They are infrastructure choices made for team learning
and engineering quality, and the PRD says so rather than pretending otherwise.

## 12. Borrowed configuration

Copy these rather than rediscovering them.

### 12.1 Activation capture and hooking

- Hook the residual stream at the output of a full transformer block (after
  attention and MLP with their residual connections) — standard SAE location.
- PyTorch `register_forward_hook` on the target decoder-layer modules.
- Mean-pool over tokens per timestep by default; each episode yields a `(T, d)`
  matrix. Per-token capture is available but was less interpretable in Dr. VLA's
  hands and costs terabytes at scale.
- For a SAFE-style verifier: final layer before decoding to logits, `pre-logits`
  with `Mean` aggregation was their real-world choice. Ablate First / Last /
  Mean / First&Last.

### 12.2 SAE training

- TopK architecture with AuxK auxiliary loss.
- **Expansion ratio 1**, not 8–16. Dr. VLA found larger ratios produce
  substantially more dead features at robotics dataset scale with no
  interpretability gain. This is counterintuitive coming from LLM work — do not
  "fix" it.
- k = 100 for d = 2048 residual streams; scale proportionally.
- Adam, lr 1e-4, batch 4096, 100 epochs, geometric-median pre-bias from 10k
  samples, unit-norm decoder columns, dead-latent threshold 500 steps.
- Train several seeds and check that top features for a given episode recover
  consistently. Dr. VLA used six.

### 12.3 Fine-tuning

- SimLingo's own recipe: full fine-tune of all components except the LLM, LoRA on
  all linear layers of the LLM, DeepSpeed, SmoothL1 loss on waypoints.
- For targeted co-fine-tuning, RoboART's mixture is a reasonable starting point:
  80% original data / 20% new, reduced learning rate (they used 5e-6), ~20K
  steps. Adapt, but state the deviation.

### 12.4 Evaluation protocol

- Fail2Drive metrics: DS, SR, and their harmonic mean. Route Completion omitted —
  their routes are short and nearly always finishable, so RC is uninformative.
- Three evaluation seeds, averaged.
- RoboART's metrics for directive quality: Spearman rank correlation and average
  absolute prediction error.

## 13. Workstreams

Five. A gates everything; B, C, and D parallelize once A lands; E depends on D
producing a first axis. These divide the **setup** work, not the results — once
the harness exists, sweeps and ablations inside D and E fan out across everyone
(§6.1).

### A — Model and simulator bring-up

Get SimLingo running in the Fail2Drive CARLA build. Reproduce published numbers.

**Done when:** all three §10.1 targets reproduce within stated tolerance across
three seeds, from a versioned config, by someone who did not set it up.

### B — Evaluation and serving infrastructure

Inference server, containerization, distributed rollout fan-out, streaming
activation capture, experiment tracking, results database, config hashing.

**Done when:** any team member runs `harness run <config>` and gets a row in the
results DB comparable to every other row; a paper number can be regenerated from
its config hash alone; activation capture runs inside the rollout path without a
separate offline pass.

### C — Planted gaps

Gap specs, predicates, removal pipeline, gapped-model fine-tunes, sealed key.

**Done when:** three to five gaps are specified in the §9.1 format with measured
match counts and measured post-sampler removal rates; gapped checkpoints exist
and are registered in the results DB; the key is sealed and CI confirms no
discovery or baseline module imports from `gaps/sealed/`.

### D — Discovery and baselines

Axis discovery from activations, plus the three §9.3 baselines.

**Done when:** all three baselines and at least one discovery method emit
directives in the §8.3 schema over a shared corpus; the describability protocol
has been run with its interpretable fraction reported; layer and aggregation have
been swept rather than assumed.

### E — Generation loop

Scenario authoring along a discovered axis, solvability validation, data
generation, targeted fine-tune, measurement.

**Done when:** one complete discover → author → generate → fine-tune → measure
cycle has run end to end, with the no-degradation check reported, and every
authored scenario passes PDMLite-F2D solvability and uses no Fail2Drive benchmark
assets.

## 14. Repository

```
adapters/          simlingo/, stub/ — the §8.2 interface, one dir per policy
capture/           serving, hooks, streaming activation extraction
gaps/
  specs/           gap definitions in the §9.1 format (readable)
  sealed/          predicates + answer key — C ONLY, CI-enforced
  pipeline/        removal / regeneration
discovery/         sae/, clustering/, contrastive/
baselines/         stratification/, enumerated/, activation_stats/
harness/           config schema, runner, results DB, metrics
generation/        scenario authoring, solvability checks
analysis/          figures, tables, protocol tooling
configs/           every experiment, versioned, content-hashed
docs/              this PRD, decisions log, what-broke log
```

**Conventions.**

- Every experiment is a YAML config. Results are keyed by config content hash.
- No notebooks on main. Exploration lives in `analysis/` as scripts.
- One owner per top-level directory. Agents working in parallel stay in their
  directory or open a PR against the owner.
- CI check: nothing under `discovery/` or `baselines/` may import from
  `gaps/sealed/`.
- Adapters depend only on `harness/` interfaces, never on each other.

---

## 15. Timeline and kill criteria

- **September — bring-up.** SimLingo running, numbers reproduced, serving and
  capture standing up. This eats the whole month and is where projects of this
  shape usually die.
- **October — answer key and first signal.** Gaps specified and planted. First
  discovery results. All three baselines running on the same corpus. Describability
  tested early on a small corpus, before scaling. **The rollout-free baseline runs
  this month** — if activation statistics alone recover the gaps, we need to know
  in October, not after building a rollout corpus for it.
- **Early November — go/no-go.** Does discovery beat behavioral stratification on
  planted-gap recovery? If no, stop pursuing the main claim and pivot to the
  comparison paper, which is recoverable in the remaining time. This decision
  happens here, not in December.
- **November — closed loop.** One full cycle minimum, two if infra holds.
- **Early December — writing.** Ablations, figures, paper.

Budget: one main experiment plus one ablation round. Not three experiments.

## 16. Open decisions

Owners assigned in week one. Items 1 and 2 must close before Workstream C writes
code.

1. **Fine-tune cost, measured in Service Units.** SimLingo's published training is
   14 epochs on 8×A100-80GB over 24 hours — roughly 190 A100-hours for a full
   run. Nobody should plan against that number second-hand, and GPU-hours are not
   the unit we are billed in. **Task: confirm the GPU partition and SU rate
   available to `ic_cdss170fall` (§17.4), then time one gapped fine-tune from the
   released checkpoint and report it in both wall-clock and SUs.** The gap
   portfolio size in §9.1 scales directly off the answer.
2. **Deletion versus expert regeneration** for gap creation (§9.1). Decide before
   specs are written.
3. **Whether the interestingness-bucket sampler distorts removal** (§9.1). Measure
   the effective post-sampler removal rate.
4. **Hook point** — LLM residual stream versus waypoint query tokens (§9.2).
   Sweep.
5. **Layer and aggregation.** Sweep, do not guess. This is a legitimate compute
   use.
6. **Discovery method** — SAE, clustering, or contrastive directions as primary.
7. **Serving stack** — vLLM or Triton. Decide on how SimLingo's action decoding
   fits, not on familiarity.
8. **Which benchmarks to report** for the no-degradation check: Fail2Drive,
   Bench2Drive, or both.
9. **Second policy for the cross-model check** — and whether it survives the
   September budget at all.

## 17. Compute

**Source of truth: <https://datadisco.cdss.berkeley.edu/savio/> and its
subpages.** That is the Data Discovery Program's own Savio documentation and it
governs. Anything here that contradicts it is wrong; anything not covered there
goes to the program's support contact, not to guesswork.

### 17.1 Access

- Cluster: Savio, Berkeley Research Computing. SSH to `hpc.brc.berkeley.edu`.
- Project: **`ic_cdss170fall`**, joined through the MyBRC portal
  (<https://mybrc.brc.berkeley.edu/>) with CalNet credentials.
- Per-user steps, in order: sign the cluster user access agreement task on first
  login; join the project under "My BRC Cluster Projects"; set up one-time
  password authentication. Login is a PIN plus a 6-digit Google Authenticator
  code.
- Everyone who will run jobs does this in week one. It is not instant, and it
  blocks Workstream A.

**The `ic_` prefix matters.** This is an Instructional Computing Allowance held
by the program, not a faculty allowance and not a condo. Two consequences:

1. **Usage is tracked and deducted.** Only condo (`co_*`) jobs are untracked.
   `ic_*` draws down a fixed pool.
2. **The pool is shared across the program**, not reserved for this team. Our
   budget is a slice of a shared allocation, which is a stronger reason to size
   experiments deliberately than a private allowance would be.

Rules that bind us: Savio is approved for **unclassified, non-proprietary
fundamental research** only. Our work is public and open-source, so this is fine
— but if 99P Labs ever supplies an internal dataset or a proprietary checkpoint,
it cannot run here. Raise that with Ryan before accepting any such data. P2/P3
data requires a secure directory and an RDM consultation; we do not expect to
need it.

### 17.2 Job submission

Every submission needs an account, a partition, and a time limit
(`days-hours:minutes:seconds`). QoS options:

- `savio_normal` — default.
- `savio_debug` — brief testing only.
- `savio_lowprio` — preemptible. **Use this for rollout fan-out.** Rollouts are
  independent and individually cheap to lose, which is exactly the workload
  preemption suits. Do not use it for fine-tunes without checkpointing.

Job arrays are supported and are the natural fit for the parallel-ablation model
in §6.1.

### 17.3 What the budget is spent on

**Throughput.** The design multiplies: a rollout corpus large enough for
unsupervised structure to be visible, run against the base model, each gapped
model, and each fine-tuned variant from the closed loop, at three seeds per
condition, with three baselines evaluated over the same corpus. Thousands of
rollouts before any ablation. Per-rollout overhead is what decides whether the
November loop runs twice or zero times.

**Training.** Each gapped model is a fine-tune (see §16 item 1 for the real
number). The closed loop adds one fine-tune per cycle. Sweeps over layer and
aggregation add more.

**Not justified:** training a driving VLA from scratch. It would consume the
paper.

### 17.4 Unresolved, and who to ask

The program docs do not state the GPU partition names available to
`ic_cdss170fall`, the Service Unit charging rate for GPU jobs, the maximum wall
time, or the storage quota. All four are needed before §16 item 1 produces a
usable number — a fine-tune measured in GPU-hours is not a fine-tune measured in
SUs. Ask the program's Savio point of contact
(<https://datadisco.cdss.berkeley.edu/support>) rather than inferring from
general Research IT documentation, since ICA terms are set per agreement.

## 18. Non-goals and what we will not claim

- **No real-vehicle results.** Everything is CARLA.
- **No sim-to-real transfer claim.** Fail2Drive states the position we adopt:
  robustness in simulation is not sufficient for real-world robustness, but it is
  a necessary prerequisite. Say that, claim nothing more.
- **No cross-domain generality claim.** We will not demonstrate that this
  transfers to manipulation. We have arms available; they are useful as an early
  describability sanity check, not as a second experimental setup — manipulation
  confounds are listable, which is precisely the condition our argument says does
  not hold in driving. Running there would put us on the competitor's home turf
  with our weakest argument.
- **No test-time-scaling or verifier contribution.** A verifier may appear as
  implementation detail. The lane is crowded (RoboMonkey, RoVer, V-GPS,
  MG-Select) and it is not our paper. See §19.
- **No failure-detection contribution.** SAFE and its successors own that.
- **No world-model counterfactual validation.**
- **No UI, dashboard, or web frontend.**
- **No claim that driving is novel.** It is the setting, not the contribution.

## 19. The second paper

Stated so nobody drifts into it early.

Discovered axes tell you *where* a policy is uncertain, which is exactly where
test-time compute should be spent — sampling more, and reranking, on high-risk
axes rather than uniformly. Same infrastructure, same adapters, clean sequel. It
is deliberately excluded from this paper so that our results stay attributable to
the discovery system rather than to a sampling strategy layered on top.

Sequential, not parallel. Spring.

## 20. Risks

**The field is moving fast.** The two closest papers are months old and both
propose our contribution in their future-work sections. One person owns a monthly
arXiv re-check, by name.

**The rollout-free baseline wins.** Dr. VLA's metrics need no rollouts. If they
recover planted gaps as well as our pipeline, the compute story and half the
motivation go with them. Mitigation: run it in October. It would also still be a
paper — a negative result about when expensive discovery is worth it — but we
need the runway to write that one instead.

**Describability fails.** An axis nobody can name is not a discovery, regardless
of its numbers. Test on a small corpus early. Dr. VLA's own limitation is
relevant: clean top-activating examples do not guarantee causal effect, which is
why the closed loop matters.

**Infrastructure overrun.** September slipping into October is the single most
likely failure mode. Cut order: second policy first, then the results database
(scattered files are survivable; an unreproducible baseline is not), then the
custom serving stack.

**Infrastructure as an excuse.** The inverse risk. §11 states plainly which
machinery is chosen rather than necessary. If Workstream B is still being
polished in November, it has become the project.

**Gap leakage.** If discovery sees the key, the headline metric is worthless and
the failure is silent. CI check plus a separation of duties that is real, not
nominal.
