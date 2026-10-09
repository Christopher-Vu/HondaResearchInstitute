# B7: rollout-free activation statistics, definition

**Status: frozen 2026-10-09, before anyone opened the activations recorded on
the Mac or on Savio; Chris and Jerry's sign-off pending.** `PRD.md` §16.9 and
`CONFLICTS.md` C18 require this definition to exist before that, so B7 cannot be
tuned to win or lose after the fact. Every parameter below is fixed. Sign-off may
still change a choice, but any change made after the activations are opened is
labelled post hoc wherever B7 is reported. It is hash-committed with the other
baseline configs (`PRD.md` §9.3, fairness rules) at Step 6.

## What B7 is for

B7 asks whether cheap statistics of the policy's activations, with no rollout
outcomes, find the planted gaps as well as our methods do. If they do, the
rollout corpus is not justified, which is why `PRD.md` §13 runs B7 at Step 6
with a stop condition. Dr. VLA computes the four statistics below to separate
general from memorized features. Using "how memorized a feature looks" as a gap
signal is our construction (C18), and this file defines it.

## Decision 1: which activations the statistics are computed over

`PRD.md` §9.3 says "over the training data". The same section warns that B7 may
be dangerously strong because a planted gap fires about once per episode in a
small subset, but that is true of the **test pool**, not the training data:
under Mode B (§9.1) the gaps are absent from SimLingo's training data by
construction. The two readings give two variants:

| Variant | Episodes | Rollouts needed | What a win would mean |
|---|---|---|---|
| **A, training data** | Route directories of SimLingo's released training set | None | Activations of training data alone point at the gaps; the rollout corpus is not needed |
| **B, test pool** | Every test-pool rollout, outcome labels never read | Only the pool every method is scored on | Label-free statistics find the gaps; the failure labels add nothing |

**Decided:** A is B7, since it is the claim the Step 6 stop condition is about,
and B is reported beside it as "B7-pool", since the §9.3 warning predicts B is
the stronger one and a reviewer will ask for it. The Step 6 stop condition fires
if **either** variant recovers the practice gaps as well as our methods do, so
the cheaper-looking variant cannot hide the stronger one. Both run the procedure
below unchanged; only the episode set differs.

## Procedure

1. **Features.** The TopK SAE latents of the SAE discovery method: same layer,
   site, non-residualized preprocessing, `k` and seed (`PRD.md` §9.2, §12.2).
   B7 never trains its own dictionary, so B7 and the SAE method differ only in
   signal, not in feature basis.
2. **Episodes and frames.** Variant A: a seeded random sample (seed 0) of
   N = 1,000 training route directories, or all of them if the released set has
   fewer, with every frame they store; the list is committed before any
   activation is computed. At roughly 200 stored frames a directory that is
   about 200,000 forward passes, a few GPU-hours, with no simulator. Variant B:
   every recorded step of every test-pool rollout.
3. **Firing.** Latent f is on at frame t when its activation exceeds
   τ_on = 0.1, compared with the raw latent activation, as Dr. VLA does
   (App. C.1, Eq. 7; the SAE's per-sample normalisation of its inputs, §12.2,
   keeps that scale comparable across frames). The draft had normalised by the
   latent's maximum; the paper's reference replaced it on 2026-10-09, a change
   fixed by the paper rather than by our data.
4. **Statistics**, over the episodes in which f is on at least once:
   - coverage `c`: share of all episodes with any on frame;
   - onset count `ō`: mean number of off-to-on transitions;
   - peak `ā`: mean of the per-episode maximum activation;
   - relative run length `ℓ̄_r`: mean number of consecutive on frames per onset,
     divided by episode length, averaged over the episodes where f is on
     (App. C.1, Eqs. 11–12).
5. **Exclusions.** Drop latents on in fewer than 3 episodes (noise) or in more
   than 50% of episodes (general features, which cannot be a gap).
6. **Concentration score**, the gap signal. A fixed formula, not a fitted
   classifier, because Dr. VLA's classifier was fit on 30 manipulation features
   and their code has no licence (`PRD.md` §16.10):

   κ(f) = z(−log c) + z(−|log ō|) + z(ā) + z(−ℓ̄_r)

   Each z-score is taken across the latents that survive step 5. A high κ means
   rare, firing about once per episode, strong and brief: Dr. VLA's description
   of a memorized feature, and §9.2's description of a planted gap. The four
   terms are weighted equally because any other weighting would need data we
   have agreed not to look at.
7. **Axes.** Rank latents by κ. Walk down the ranking and merge a latent into an
   existing axis when the Jaccard index of their sets of test rollouts in which
   they fire is at least 0.5; otherwise start a new axis. Stop at the axis
   budget M that every method gets.
8. **Membership and schema.** An axis's members are the **failing** test-pool
   rollouts in which any of its latents is on for at least one frame. Scoring
   compares an axis with a gap's failing rollouts (`src/harness/scoring.py`),
   and every other method's axes and B1's random subsets hold failing rollouts
   only, so leaving successes in would penalise B7 for a reason unrelated to its
   signal. Outcomes enter here and nowhere else: steps 1–7 never read them.
   Names and descriptions come from the shared describability pipeline (§9.2),
   as for every method.

## What B7 may never use

In steps 1–7: outcome labels (success, failure, infractions). Anywhere: scenario
type or parameters, weather presets, the sealed key, the dev practice-gap
labels, and any threshold chosen after the activations are opened.

## Parameters

| Parameter | Value |
|---|---|
| τ_on | 0.1, on the raw latent activation (Dr. VLA App. C.1) |
| Coverage floor and ceiling | 3 episodes; 50% of episodes |
| Merge threshold | Jaccard ≥ 0.5 |
| Axis budget | M, shared with every method |
| Variant A sample | N = 1,000 route directories (or all, if fewer), seed 0 |
| κ weights | Equal, 1 each |

## Settled 2026-10-09

The draft left four questions open. All four are now fixed:

1. A is B7 and B is the reported ablation "B7-pool"; either one can trigger the
   Step 6 stop condition.
2. N = 1,000 training route directories, or the whole released set if smaller.
   This does not need the set's size to be known first.
3. τ_on applies to the raw latent activation, as in Dr. VLA App. C.1, Eq. 7.
   This was read through a summarising web extraction of the v2 HTML, not the
   PDF; recheck the equation against the PDF at sign-off.
4. κ keeps equal weights. Any other weighting would have to be fitted on data
   we have agreed not to look at.

One change from the draft: membership (step 8) is restricted to failing
rollouts, as every other method's is.
