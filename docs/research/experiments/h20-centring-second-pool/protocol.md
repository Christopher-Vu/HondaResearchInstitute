# H20: does removing the mean move method scores on a second pool?

**Locked by the commit that adds it, before it runs.** Dev only (PRD §9.2), on H1's pool with a throwaway public key of P4, P7 and P8. Not a verdict. No `PRD.md` 13.1 branch can be claimed from it (`CONFLICTS.md` C34), and no preprocessing changes because of it.

## Why

In H18 the shuffle control removed little more than the success-frame mean (its fit explains 0.008), and it still moved scores on H12's pool. M1 raw on P19 went from a median of 0.375 to 0.447, and B7-pool on P19 from 0.372 to 0.666 (measured, `docs/research/data/h18_result.json`). If removing the mean moves scores that much in general, every method reading depends on a preprocessing step that `PRD.md` does not fix. H12's pool has one interactional gap, so H20 asks the same question on a pool that shares no rollout with it.

## What runs

One A40 job, no simulator. The pool is H1's, read on Savio: `step4-dev-pool`, `step4-dev-pool-wave2`, `step5-pilot-p4-main`, `step5-pilot-p7-main` and `step5-pilot-p8-main`, every shard with an outcome, at layer 10 frame means. The key holds P4, P7 and P8, verbatim from `gaps/practice/practice_v2.yaml` (`build_key.py`, using H15's builder).

| Variant | Input to the dictionaries |
|---|---|
| `plain` | The shards as they are |
| `centre` | The shards minus the success frames' mean (`residual_controls centre`) |
| `vision` | The shards minus what `vision_bridge` predicts, fitted on this pool (`residualize`) |

As in H15 and H18, `plain` trains its dictionaries on every shard, including the few with no outcome, which `centre` and `vision` drop. Only rollouts with an outcome are scored. Each variant trains H15's grid of 18 dictionaries (k of 32, 48 and 64, seeds 0 to 5), emits directives, and is scored by `scoring_run`.

## The rule, fixed before any result

The cells are M1 raw, M1 capped and B7-pool, each on P4, P7 and P8, which makes 9 cells. A cell's value is its median Jaccard across the dictionaries that count. A cell **moves** when `centre` minus `plain` is at least 0.1 in either direction.

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | A variant trains fewer than 18 dictionaries or has a cell with fewer than 12 counted, or a step fails | "H20 is untested: a variant did not run in full." |
| `replicates` | At least one cell moves | "On H1's pool, removing only the mean moves a method's median Jaccard on a planted gap by at least 0.1, so method readings depend on a preprocessing step the PRD does not fix." |
| `not_replicated` | No cell moves | "On H1's pool, removing only the mean moves no method's median Jaccard on a planted gap by 0.1 or more." |

Reported beside the rule, with no bearing on it: best, median and dictionaries at 0.5 or above for every cell under all three variants, and the vision fit's `explained_on_fit`. The best axis is chosen using the key, beside every axis score. On H12's pool, under the same definition, the shuffle control moved 2 of 9 cells (B7-pool on P19 by +0.294 and M1 capped on P19 by +0.132), and that pool has no P8.

## What this cannot show

H1's pool has no interactional gap, so it cannot repeat the P19 result. A move shows sensitivity to the mean. It does not say which variant is right, or why the mean matters when `sae.py` already centres each frame vector on its own features.

## Cost

About 30 to 60 SU on one A40 with a 3 hour limit (estimate). H18 ran two variants of 18 dictionaries in 33 minutes on 536 shards (measured), and H20 runs three on about 740.

## Predictions (guesses)

`replicates`, 60%. `not_replicated`, 35%. `untested`, 5%.

## Commands

```bash
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-03:00:00 docs/research/experiments/h20-centring-second-pool/run.sbatch
```

## Amendment, 2026-11-06 02:50, before any score was read

The first submission (job 40967835) stopped at its first scoring step. `scoring_run` always evaluates `PRD.md` 13.1's condition 2, which needs an interactional gap, and this key has none. No report was written and no score was read. Scoring now uses `score.py` beside this file, which computes each directive's best Jaccard per key gap with `scoring_run`'s own loaders and `mean_best_jaccard`. Everything else is unchanged, and the plain variant's dictionaries and directives from the first submission are reused.

## Result, 2026-11-06

Job 40968012, with 40967835's plain dictionaries; 25 SU in all (measured). `replicates`: B7-pool on P8 moved by +0.149. `docs/research/data/h20_result.json`, read in `docs/research/dev-report.md`.
