# Probe diagnostic: is the information there, and can clustering find it?

**Status:** protocol and decision rule fixed 2026-11-17, before any run. Chris's request, 2026-11-17.

This is a **label-reading diagnostic, not a discovery method**. It reads the gap labels on purpose. It is not a try,
gets no `VARIANTS.md` method row, and must not be used to choose or tune any method, layer or setting. It reads no
UniAD data. It follows Jerry's H21 ceiling check (`docs/JOURNAL.md`, 2026-11-15), which found speed beat layer 10 on
H21, and asks the same question on the two dev pools that now matter.

## Question

Given the gap labels, how well does a simple supervised probe separate each gap's failing routes from the other
failing routes, using (a) activations alone, (b) fleet-observable behaviour alone (B3-behaviour's features), and
(c) both? And when the information is there, how much of it does unsupervised clustering (m23) recover?

## Data

- Two pools, both dev: SimLingo and TransFuser++ on the Fail2Drive test pool (manifest
  `configs/rollout/f2d-test-simlingo.manifest.json`, shared by both models).
- Caches, built by `cache_pool.py` with full-length speed and a 50-frame approach window:
  `results/savio/f2d-dev/round2/simlingo/cache-w50.npz` and `results/savio/f2d-dev/round2/tfpp/cache-w50.npz`.
  Each holds `route_id`, `meta` (JSON: `success`, `infractions`, `failure_step`), `ego_speed`, `step`, and
  `driving_queries` of shape (routes, 3, layers, width). Summary index 0 is the whole route and index 1 is the
  approach window.
- **Only failing routes** (`meta.success` false) enter the probes.
- **Units** (model, gap), five in all: SimLingo PedestriansOnRoad, FullyBlocked, BadParking; TransFuser++
  PedestriansOnRoad, FullyBlocked. A route is in a gap if the manifest gives it `role: pilot_slice` with that type in
  `practice_gaps`, and it failed. Every other failing route of that model is the rest.
- **Groups:** the manifest's `pair` field. Each route belongs to one Fail2Drive pair.

## Features

- **Activations:** `driving_queries`. Summary ∈ {window, route}. Layer given as a fraction of depth f ∈ {0, 1/4,
  8/23, 1/2, 3/4, 1}, mapped by floor(f × (depth − 1) + 0.5). That gives SimLingo (depth 24) layers 0, 6, 8, 12, 17
  and 23, and TransFuser++ (depth 6) layers 0, 1, 2, 3, 4 and 5. For each (model, summary, layer): standardise over
  **all** routes of the pool, passing and failing (z-score; zero-variance columns left at 0). Then PCA to 32
  components, fit on all routes with `random_state=0`. This is label-free and matches m23's preparation. Then keep the
  failing rows.
- **Behaviour:** B3-behaviour's features, exactly as `b3_behaviour.py` computes them: `kinematics(speed, step,
  failure_step)` (9 values) plus one count per infraction type seen anywhere in that model's pool. Standardised over
  all routes.
- **Both:** the activation PCA block and the behaviour block, each standardised over the failing rows, each divided
  by the square root of its column count, then concatenated.

## Probes and cross-validation

- **Logistic regression:** `class_weight="balanced"`, `C=0.1`, `max_iter=2000`. Features are standardised again
  inside each training fold, with the training fold's mean and SD applied to the test fold. The score is the
  predicted probability of the gap class.
- **k-nearest neighbours:** k = 10, Euclidean, uniform weights, on the same fold-standardised features. The score is
  the fraction of the 10 neighbours that are in the gap.
- **Cross-validation:** `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0)`, with groups = pair. No pair
  is ever in both train and test. Out-of-fold scores from all five folds are pooled into one vector per cell.
- **Primary metric:** AUROC of the pooled out-of-fold scores. Also reported: balanced accuracy at threshold 0.5 for
  logistic, and at the training-fold gap prevalence for kNN.

## Cells

Per unit: activations 2 probes × 2 summaries × 6 layers = 24 cells; behaviour 2 probes = 2 cells; both 24 cells.
That is 50 per unit and **250 in all**. Every cell is reported.

## Null and intervals

- **Permutation null:** 200 shuffles of the gap labels across that model's failing routes (`numpy` default_rng,
  seed 1). Each shuffle reruns the full cross-validation with the same folds. Per-cell p = (1 + #{null ≥ observed}) /
  201.
- **Max-statistic test per unit:** for each shuffle, take the maximum AUROC over the unit's 24 activation cells. The
  unit's activation p compares the observed maximum with that distribution, which corrects for the grid.
- **Intervals:** 95% percentile interval from 1,000 bootstrap resamples of pairs (`numpy` default_rng, seed 2). The
  out-of-fold scores are fixed; each route is weighted by its pair's draw count, and AUROC uses sample weights.
  Contrasts between cells (both minus behaviour, activations minus behaviour) use the same draws, paired.

## Findability

- Per model, one **multinomial** logistic probe (classes: each gap of that model, plus "other failing"), with the same
  settings and folds. Its inputs are m23's: the window and whole-route blocks at fraction 8/23, each prepared as
  above, then concatenated.
- Each failing route gets its out-of-fold `decision_function` vector, one column per class. That vector is the probe's
  learned subspace.
- Cluster the failing routes in that subspace exactly as m23 clusters: standardise, then Ward,
  `cache_methods.axes_from` (cuts 2, 3 and 5, distinct groups, continued to 10 axes). Score each gap by best-match
  Jaccard over those 10 axes.
- **Findability gap** per unit = supervised-subspace Jaccard − m23's Jaccard on the same unit. m23's values come from
  `results/savio/f2d-dev/round2/batch1.json`, row m23: SimLingo PoR 0.591, FB 0.353, BP 0.171; TF++ PoR 0.063, FB
  0.171.

## Decision rule (fixed before running)

A unit **has the information** when both hold:
1. **Beats the null:** the max-statistic activation p < 0.05.
2. **Adds over behaviour:** for the logistic probe at window, fraction 8/23 (m23's main view, named in advance), the
   95% interval of AUROC(both) − AUROC(behaviour) excludes 0 on the positive side.

"Most gaps" means at least 3 of the 5 units.
- **Outcome 1, information insufficient:** fewer than 3 units have the information.
- **Outcome 2, information present but hard to find:** at least 3 units have it, and on those units the median
  findability gap is at least 0.20 Jaccard.
- **Outcome 3, present and findable (residual case, added for completeness):** at least 3 units have it, but the
  median findability gap is below 0.20. Then the clustering is not the bottleneck.

Per-model reporting is always given, and the rule is also stated per model (units of that model only, majority).

## Agreement

An independent worker reimplements this from this file alone, without reading `probe_diagnostic.py` or its outputs
until both have run. The two agree when at least 95% of the 250 cells are within 0.03 AUROC, every unit's decision
(information yes or no) matches, and the outcome matches. Disagreements are listed, not averaged away.

## Amendment (post hoc, 2026-11-17, after the primary run was read)

The primary run (job 41486627) gave per-cell AUROCs that depend strongly on the fold assignment. The same code on
the same data gave BadParking's behaviour probe 0.46 inside the job (policy venv) and 0.80 on the login node
(analysis venv, scikit-learn 1.9.1), because the two scikit-learn versions shuffle `StratifiedGroupKFold`
differently. Each gap holds only 3 to 6 Fail2Drive pairs, so a five-fold pair-grouped split is close to
leave-one-route-out over a handful of routes. Pooled out-of-fold AUROCs well below 0.5 (0.09 to 0.22) are that
effect: the probe learns the training routes and misranks the held-out ones.

Added check, fixed before it runs: every cell's AUROC over 20 split seeds (0 to 19), the same environment as the
primary run, reported as mean, minimum and maximum, with no null and no decision. The primary result and its outcome
stand as pre-registered. This check only says how far a single split can be trusted. The independent
reimplementation runs in the same job environment.
