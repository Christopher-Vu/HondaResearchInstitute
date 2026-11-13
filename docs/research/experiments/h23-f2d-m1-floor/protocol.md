# H23: M1 with a group floor of 3 on Fail2Drive's categories

**Locked by the commit that adds it, tagged `methods-frozen-f2d-v2`, before it runs.** Jerry asked for this test on 2026-11-12, after reading H22. It is **post hoc**: the one setting it changes was chosen because H22 showed that setting capped M1. It cannot replace H22's reading (`not_ahead`), and the report gives both results side by side. Dev only and not blind, for the same reasons as H22. No `PRD.md` 13.1 branch can be claimed (C34). Chris has not reviewed C38 or this test.

Every number is tagged: measured, estimate, or guess.

## Why

M1 founds an axis only from a latent that fires in at least 20 failing routes (`ContrastiveConfig.min_support`). H22's categories have 8, 5 and 3 failures (measured), so M1 could not exceed a mean Jaccard of 0.27. B3 scored 0.47 (measured). H22 therefore could not tell whether the activations hold these failures. H23 asks that question with the floor removed as a limit.

## The one change

M1's floor (`--m1-min-support`, for M1 raw and M1 capped) goes from 20 to **3**. Two reasons fix that value, and neither uses H22's scores:

- B7-pool, the activation baseline M1 is compared with, already uses a floor of 3 (`ActivationStatsConfig.min_episodes`). In H22 the two were not on equal terms.
- 3 is the smallest group this study treats as a candidate gap: the screen rule needs 3 excess slice-only failures.

Everything else is H22's, unchanged: the shards, the 18 dictionaries per variant (reused from H22's runs, not retrained), the `centre` and `vision` shards, the FDR gate (q below 0.05), the scorer, the categories, the rule and its threshold. B1 is redrawn because it is sized from M1's axes on `L10_k64_s0`, as before. B2 keeps its floor of 20 and stays outside the comparison.

## The reading, fixed before any result

H22's rule and sentences, read on the `plain` variant: `ahead` if the median delta across dictionaries is at least 0.15 and the bootstrap interval's lower end is above 0; `untested` if M1 raw, M1 capped or B7-pool has fewer than 12 counted dictionaries; otherwise `not_ahead`. Centre and vision are reported beside it with no bearing on it. The pair reading, per-category best and median, and B2 are reported as in H22.

Also reported, with no bearing on the result: the number of M1 axes per variant, and their sizes.

## What this cannot show

- A lower floor lets M1 emit smaller groups, and some will match by chance. The FDR gate is unchanged. The comparison with B1, which is redrawn at M1's new sizes, is the check on chance.
- An `ahead` here comes after a negative result on the same data, under a setting chosen in response to it. At most it says the floor was the obstacle. The categories are still public and still chosen on these pairs.

## Cost

About 2 to 5 SU on one A40, under a 1 hour limit (estimate). H22 emitted and scored three variants in about 7 minutes after training (measured).

## Predictions (guesses)

`not_ahead`, 65%. `ahead`, 25%. `untested`, 10%. Plain M1 raw emits at least one axis on at least 12 dictionaries, 60%.

## Commands

```bash
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-01:00:00 docs/research/experiments/h23-f2d-m1-floor/run.sbatch
```

## Result, 2026-11-12

Job 41250943, about 2 SU (measured). `not_ahead`: median delta -0.385, interval -0.500 to -0.266. Plain M1 raw now emits axes on all 18 dictionaries, and its mean best Jaccard is 0.142 at best and 0.085 at median, under B1 random (0.186) and B3 behavioral (0.471). Centre M1 raw reaches 0.250 at best. `docs/research/data/h23_plain.json`, `h23_centre.json` and `h23_vision.json`, read in `docs/research/dev-report.md`.
