# H22: frozen methods on Fail2Drive's three screened categories

**This file, `score.py` and `run.sbatch` are the freeze.** The commit that adds them carries the tag `methods-frozen-f2d-v1` (`CONFLICTS.md` C38, item 2), placed before any discovery method reads H21's shards. `run.sbatch` refuses to run on a checkout without the tag. Dev only and not blind: the categories are public, and they were chosen from outcomes on the same 100 pairs that are scored here. No `PRD.md` 13.1 branch can be claimed from this run (C34). Jerry accepted C38 on 2026-11-12; Chris has not reviewed it.

Every number is tagged: measured, estimate, or guess.

## What is frozen

| Item | Value |
|---|---|
| Pool | H21's 200 routes (`configs/rollout/f2d-all.manifest.json`), shards at `results/savio/f2d-all/shards`, outcomes from `results/savio/f2d-all/routes.jsonl`: 52 failures (measured) |
| Gaps | The three H21 screen candidates. A category's failing set is its generalization routes that failed: CustomObstacles 8, Wall 5, PedestriansOnRoad 3 (measured) |
| Representation | `driving_queries`, layer 10, frame means, as in H12 to H20 |
| Dictionaries | 18 top-k SAEs: k of 32, 48 and 64, seeds 0 to 5, trained on this pool's frames. A dictionary under 0.8 explained variance is reported and does not count (`dev_eval`) |
| Primary method | M1 raw (contrastive diffing). M1 capped and M2 are also activation methods and enter the comparison. M2 is labelled "no verified power" beside every score, because H19 found it recovers no planted group (C37) |
| Primary preprocessing | `plain`: the shards as they are, with no dataset-mean step and no vision residual. PRD 13.1 counts only the non-residualized variant for validity, and H20 showed mean removal can lower M1 raw on a perceptual gap (P4, 0.353 to 0.265, measured) |
| Secondary variants | `centre` (minus the success frames' mean, C37 item 1) and `vision` (minus what `vision_bridge` predicts). Each is reported beside the primary and has no bearing on its reading |
| Baselines | B1 random, one seeded draw sized from M1 raw's axes on `L10_k64_s0`. B3 behavioral. B7-pool on the same latents and the same preprocessing as the method beside it (C37 item 2). B2 is the ceiling only (C38 item 4): Fail2Drive's scenario names separate each category from its twin by construction |
| Code | `discovery.sae`, `discovery.emit_directives`, `discovery.residual_controls`, `discovery.residualize` and `harness.scoring` at this commit |

## The reading, fixed before any activation is read

For each directive and category, the score is the best Jaccard between any of its axes and the category's failing set. The best axis is chosen using the failing set, and the report says so beside every score.

**Comparison (primary).** For each counted dictionary, delta is the best activation method's mean score over the three categories, minus the best rival's (B1, B3, and that dictionary's B7-pool). Both "best"s are re-picked inside every replicate. The statistic is the median delta across dictionaries. Its interval is the 2.5 to 97.5 percentile of 10,000 bootstrap replicates that resample the three categories with replacement (seed 20261016).

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | M1 raw, M1 capped or B7-pool has fewer than 12 counted dictionaries in `plain`, or a step fails | "H22 is untested: the primary variant did not produce 12 counted dictionaries for every method." |
| `ahead` | Median delta at least 0.15 (PRD 13.1's margin) and the interval's lower end above 0 | "On Fail2Drive's three screened categories, activation methods recover the failing routes better than the activation-free and pooled baselines, by a median of at least 0.15 Jaccard across dictionaries." |
| `not_ahead` | Otherwise | "On Fail2Drive's three screened categories, activation methods are not shown to recover the failing routes better than the activation-free and pooled baselines." |

**Pair reading (beside it, C38 item 3).** For each pair where the generalization route failed and its twin did not (13 pairs: 5, 5 and 3, measured), the pair is a hit for a directive when one of its emitted axes holds the generalization route, does not hold the twin, and has Jaccard at least 0.3 with the category's failing set. Only the axes the method emitted under its budget are used; none is added or picked by the key. Reported per family as best and median across dictionaries, with no bearing on the result.

Also reported, with no bearing on the result: best and median per family and category; B2's scores; the catch-all axis's Jaccard (the category's failures over all 52); each variant's fit.

## Deviations from C38's text

- C38 asks for B7 matched to the method's axis sizes. B7-pool's sizes come from its own rule, as in every earlier run, and are reported. Changing B7 now would be a method change made for this run.
- B1 is one draw, sized from one dictionary, as `emit_directives` does everywhere else.
- With three categories, the bootstrap has 10 distinct resamples. The interval is coarse, and the report says so.

## What this cannot show

- The categories are known in advance, and they were picked on these pairs. A good score shows that the methods separate known failures. It does not show that they discover unknown ones.
- PedestriansOnRoad has 3 failures. One axis member changes its Jaccard by up to a third.
- The dictionaries are trained on this pool, so the axes can fit its quirks. No held-out pool exists.

## Cost

About 20 to 50 SU on one A40 with a 3 hour limit (estimate). H20 trained three variants of 18 dictionaries on about 740 shards for 25 SU (measured); this pool has 200.

## Predictions (guesses)

`not_ahead`, 60%. `ahead`, 30%. `untested`, 10%. M1 raw's best Jaccard on Wall is at least 0.5 on at least one dictionary, 50%.

## Commands

```bash
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-03:00:00 docs/research/experiments/h22-f2d-frozen-eval/run.sbatch
```

## Amendment, 2026-11-12, before any score was read

The first submission (job 41226034, 3.5 minutes, measured) trained the plain variant's 18 dictionaries and stopped while emitting directives: B2's records read a `weather` field that Fail2Drive's manifests do not carry. No directive or report was written, so nothing was read. B2 now stratifies only on the fields a manifest carries (`baselines/taxonomy.py`, `dev_eval.taxonomy_records`), with a test. This touches B2 alone, which never enters the comparison. Everything else is unchanged, and the plain dictionaries from the first submission are reused.

B2's ranking needs at least 20 routes in a stratum (`min_support`), and no Fail2Drive scenario has more than 10. So B2 as frozen cannot isolate a category, and item 4's "ceiling" does not hold on this pool. B2's scores are still reported, with this sentence beside them.
