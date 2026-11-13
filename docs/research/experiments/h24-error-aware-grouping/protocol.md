# H24: error-aware grouping of failures, in Domino's manner

**Locked by the commit tagged `h24-h25-locked`, with H25, before either reads any data.** Jerry asked on 2026-11-12 for both directions from the [literature review](../../literature-review.md), run in parallel. Dev only and not blind. Fail2Drive's categories have already been read twice (H22, H23), so this run also reads a second pool it has never been tuned on. No `PRD.md` 13.1 branch can be claimed (C34). Chris has not reviewed C38 or this test.

Every number is tagged: measured, estimate, or guess.

## Why

The review's best-checked slice-discovery method, Domino (Eyuboglu et al., ICLR 2022, checked by a 3-vote panel), uses the failure label while grouping, through an error-aware mixture. FACTS (seen only in search results) and InfEmbed (abstract only) also use errors while grouping. M1 groups latents first and compares outcomes afterwards. H24 asks whether grouping routes by their activations, error-aware, recovers known failure groups better than B3 and than random groups of the same sizes.

A correction shapes the comparison. B3 is not a pure behaviour baseline. Its features include the simulator's exact distances to the nearest obstacle, pedestrian, animal, two-wheeler, lead car and junction, and the penalties the car incurred (`baselines/behavioral.py`). Those are ground truth the policy never receives. So H24 also groups on the car's kinematics alone, to separate "how the car drove" from "what the simulator knows was near it".

## What runs

| Item | Value |
|---|---|
| Pools | **Fail2Drive** (H21's 200 routes; categories CustomObstacles, Wall, PedestriansOnRoad; 8, 5 and 3 failures, measured). **H1's pool** (H20's 738 shards; P4, P7 and P8, read from the public manifests; never tuned on by any H22 to H25 choice) |
| Window | B3's: the logged steps in the 3 s before the failure step, or before the last step for a success |
| Representations | `act`: the window mean of layer-10 driving-query frame means. `kin`: speed mean, minimum and maximum in the window, and the route's stationary share. `full`: B3's feature row. `act+kin`: both blocks, each scaled to equal total variance |
| Model | `mixture.py`: each block standardised and reduced to at most 32 principal components; a 10-component diagonal Gaussian mixture with a Bernoulli outcome term weighted by 1, started from k-means (10 restarts) |
| Axes | For each component, its failing routes; ranked by the component's failure rate, then failing count; the top 10 |
| Arms | `act` (primary), `act_gamma0` (the same with no outcome term, a plain mixture), `kin`, `full`, `act+kin` |
| Runs | Seeds 0 to 17 per arm and pool |
| Scorer | `score_sets.py`: per category, the best Jaccard of any axis with the category's failing set (chosen using that set), averaged over categories |

**Positive controls (measured on synthetic data, before any real data; `tests/test_h24_grouping.py`).** On a pool shaped like Fail2Drive (groups of 8, 5 and 3 failures, each shifted by 3 SD on its own 8 of 64 dimensions, among 52 failures in 200 routes), the primary setting recovers the groups at a median mean Jaccard of at least 0.9 over 6 seeds. On a pool with no structure, failures spread over at least 5 axes. The outcome weight was fixed at 1 on these pools: 0 and 1 recovered the groups about equally (median 1.0 at 3 SD, 0.60 and 0.54 at 2 SD), while 3 and 10 merged failures into one large group (median largest axis 25 to 36 against 9 to 11). Weight 0 also does as well as 1 on these pools, so the controls check the code, not error-awareness; the `act_gamma0` arm measures that on the real pools. A per-dimension average of the feature term was tried and merged every failure into one group, so it was dropped.

## The reading, fixed before any result

Per method and pool, a run's delta is its mean score minus the better of B3 and that run's matched random control. The control redraws 50 random partitions of the pool's failing routes into groups of the run's own axis sizes and averages them. `ahead` needs all three of:

1. the median delta over runs is at least 0.15;
2. on every category, the median over runs of that category's delta is above 0. With three categories, a category bootstrap's lower end is about the worst category, so this is stated directly: `ahead` needs a win on 3 of 3 categories in a pool, and 6 of 6 under the both-pools rule;
3. a route bootstrap (each category's failing routes resampled with replacement, 1,000 times, seed 20261016, every score recomputed with weighted Jaccard and the random draws held fixed) has its 2.5th percentile of the median delta above 0. This carries the route-level noise that three categories cannot.

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | Fewer than 12 of 18 runs have an axis | "H24 is untested: {method} produced fewer than 12 runs with an axis." |
| `ahead` | All three conditions | "On {pool}, {method} recovers the categories' failing routes better than B3 and random groups of the same sizes, by a median of at least 0.15 Jaccard, on every category." |
| `not_ahead` | Otherwise | "On {pool}, {method} is not shown to recover the categories' failing routes better than B3 and random groups of the same sizes." |

The report gives each category's delta, the delta against random groups alone, and which condition failed.

**Primary:** `H24_act` on Fail2Drive and on H1's pool. The two are read separately and both reported. An activation result counts as supported only if it is `ahead` on both pools.

**Secondary, with no bearing on the primary:** `H24_act_gamma0`, `H24_kin`, `H24_full` and `H24_act+kin`, on both pools. If `act` and `act_gamma0` read alike, the result is reported as a plain Gaussian mixture, not as evidence about error-aware grouping. `act+kin` against `kin` says whether activations add anything to kinematics. `full` against B3 compares two ways of grouping the same features. On Fail2Drive the pair reading is reported beside every method. Axes hold failures only, so C38's twin condition (the twin is not in the axis) is always met here; the reading counts slice-only pairs whose slice route sits in an axis with Jaccard at least 0.3.

## What this cannot show

- The mixture's settings come from Domino's idea and from synthetic pools, not from Domino's code. A loss does not show Domino would lose.
- H1's pool has large groups (tens of failures each) and camera faults; Fail2Drive has groups of 3 to 8. A method can win one and lose the other.
- Every score picks the best axis using the answer. That is the same for every method here, including the random control.
- The window ends at the first infraction's step, which is read from outcome details. Every method uses the same anchor.
- B3 is one seed-0 run, and its Fail2Drive score (0.471) was known when this rule was written.

## Commands

Export, on Savio after the tag (one job for H24 and H25):

```bash
bash scripts/submit.sh cpu --time=0-02:00:00 docs/research/experiments/h24-error-aware-grouping/export.sbatch
```

Then, with `results/savio/h24-h25/` copied back:

```bash
PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/mixture.py results/savio/h24-h25/f2d-features.npz --output results/savio/h24-h25/h24-f2d-axes.json
PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/mixture.py results/savio/h24-h25/h1-features.npz --output results/savio/h24-h25/h24-h1-axes.json
PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/score_sets.py --axes results/savio/h24-h25/h24-f2d-axes.json --manifests configs/rollout/f2d-all.manifest.json --routes results/savio/f2d-all/routes.jsonl --categories F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad --b3 results/savio/h24-h25/f2d-b3.json --pairs --min-runs 12 --pool "Fail2Drive's three screened categories" --label "H24 on Fail2Drive" --output results/savio/h24-h25/h24-f2d-report.json
PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/score_sets.py --axes results/savio/h24-h25/h24-h1-axes.json --manifests configs/rollout/step4-dev-pool.manifest.json configs/rollout/step4-dev-pool-wave2.manifest.json configs/rollout/step5-pilot-p4-main.manifest.json configs/rollout/step5-pilot-p7-main.manifest.json configs/rollout/step5-pilot-p8-main.manifest.json --routes results/savio/h24-h25/h1-routes.jsonl --categories P4_camera_occlusion P7_camera_freeze P8_camera_latency --b3 results/savio/h24-h25/h1-b3.json --min-runs 12 --pool "H1's pool (P4, P7, P8)" --label "H24 on H1's pool" --output results/savio/h24-h25/h24-h1-report.json
```

## Cost

Features: one CPU job shared with H25, under 2 hours (estimate, a few SU). The mixtures run on a laptop.

## Predictions (guesses)

`H24_act` on Fail2Drive: `not_ahead` 75%, `ahead` 15%, `untested` 10%. On H1's pool: `not_ahead` 55%, `ahead` 35%. `H24_kin` scores below B3 on Fail2Drive: 80%.

## Review before the lock

Four reviewers with separate lenses read this protocol and its code, and three skeptics checked each major finding. Eleven held and two were rejected. The fixes: the outcome weight went from 10 to 1, because 10 merged failures on pools shaped like ours; the `act_gamma0` arm was added; the three-category interval was replaced by the explicit every-category check plus a route bootstrap; the random control became a partition; a misspelt category now stops the run; and these commands were fixed. H25's fixes are listed in its own protocol.

## Result, 2026-11-13

Export job 41255052 (about 4 SU, estimated from 1,042 s on 4 cores); mixtures and scoring on a laptop. Every arm reads `not_ahead` on both pools (measured). `docs/research/data/h24_f2d_report.json`, `h24_h1_report.json`.

| Arm | Fail2Drive median delta | Route bootstrap | H1's pool median delta | Route bootstrap |
|---|---:|---|---:|---|
| `act` (primary) | -0.227 | -0.269 to -0.146 | +0.109 | +0.017 to +0.143 |
| `act_gamma0` | -0.218 | -0.262 to -0.139 | +0.117 | +0.032 to +0.154 |
| `act+kin` | -0.050 | -0.184 to +0.160 | +0.096 | +0.019 to +0.125 |
| `full` | -0.043 | -0.097 to -0.030 | +0.072 | +0.015 to +0.082 |
| `kin` | -0.127 | -0.232 to +0.042 | +0.046 | -0.009 to +0.079 |

On H1's pool `act` beats both rivals on every category (P4 +0.27, P7 +0.04, P8 +0.02) and its route bootstrap stays above 0. It misses only the 0.15 margin, so the reading is `not_ahead`. `act` and `act_gamma0` read alike, so this is reported as a plain Gaussian mixture, not as evidence about error-aware grouping.
