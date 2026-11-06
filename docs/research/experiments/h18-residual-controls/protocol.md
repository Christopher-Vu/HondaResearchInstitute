# H18: does the residualization gain on P19 need the visual fit?

**Draft, locked by the commit that adds it, before any control shard exists.** Dev only (PRD §9.2), on H12's pool with H15's throwaway public key. Not a verdict, and no `PRD.md` 13.1 branch can be claimed from it (`CONFLICTS.md` C34).

Every number is tagged: measured, estimate, read from the code, or guess.

## Why

H15 found that action residualization lifts contrastive diffing (M1 raw) on P19 from a median Jaccard of 0.375 to 0.540 across 18 dictionaries, with best 0.705 and 0.689 (measured, `docs/research/data/h15_dry_run.json`). Residualization fits the layer 10 driving-query states on `vision_bridge` with a ridge and keeps what vision does not predict (`src/discovery/residualize.py`). The fit's `explained_on_fit` is 0.773 at alpha 1.0, the smallest alpha tried (measured, H15's log). That number is sklearn's average R squared over hidden units, each unit weighted equally, so it is not the share of total variance the fit removes.

That gain has two cheap explanations that have nothing to do with vision. Removing the fit's mean could change what the dictionary learns, or removing that much variance in any direction could. H18 tests both before the result is used for anything.

## What runs

One A40 job, no simulator, on the same 536 shards and the same SAE grid as H15 (k of 32, 48 and 64, seeds 0 to 5, frame means, layer 10). Each control writes its own shards with `src/discovery/residual_controls.py` and goes through H15's steps: 18 dictionaries, `emit_directives`, and `scoring_run` with H15's `as-labelled` throwaway key and H15's plain directives.

| Control | What it removes | What it keeps fixed |
|---|---|---|
| `shuffle` | The same ridge, fitted with the visual frames permuted (seed 18) against the query frames. It removes the mean and almost nothing that vision predicts. | Ridge form, alphas, success frames |
| `top-variance` | The mean and the fewest leading principal components of the success frames' query states whose share of total variance reaches the share the real fit removes from those frames. That share is measured in the run and recorded in `fit.json`. | Share of total variance removed |

## The rule, fixed before any result

The quantity is M1 raw's median Jaccard on P19 across the dictionaries that count, out of 18. Let G be the gain H15 measured, 0.540 − 0.375 = 0.165. A control **reaches halfway** when its median is at least 0.375 + G/2 = 0.4575.

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | A control trains fewer than 18 dictionaries, fewer than 12 of them count (held-out explained variance of at least 0.8, as `scoring_run` decides), or a step fails | "H18 is untested: a control did not run in full." |
| `needs_vision` | Neither control reaches halfway | "On P19, neither control reaches halfway to the residualization gain, so the gain needs the visual fit." |
| `not_vision` | `shuffle` reaches halfway | "A fit on shuffled vision reaches halfway to the residualization gain on P19, so the gain does not need the visual fit." |
| `not_shown_specific` | Only `top-variance` reaches halfway | "Removing as much variance without vision reaches halfway to the gain on P19, so H18 cannot show that the gain is specific to vision." |

Reported beside the rule, with no bearing on it: best and median for M1 raw, M1 capped and B7-pool on P4, P7 and P19 under each control; dictionaries at 0.5 or above; the shuffle fit's `explained_on_fit`; the real fit's removed share and the number of components `top-variance` removed; and a bootstrap interval (seed 18, 5000 draws over dictionaries) for each control's median minus the real residual's median. The best axis is chosen using the key, beside every axis score.

## What this cannot show

- It covers one gap, P19, which already fails Step 5's single-factor condition, since B2's list of scenario names scores 0.857 on it (measured, H12). Nothing here changes P19's standing.
- `needs_vision` shows that the gain depends on the visual fit on this pool. It does not show the gain holds on other gaps or pools.
- The same-layer visual pool, Chris's alternative to `vision_bridge` (H15 protocol, "Readings to confirm"), is not run: the shards hold no token counts to recover it from, so it needs a recapture.

## Cost

About 25 to 50 SU on one A40 with a 2 hour limit (estimate). H15 trained 18 dictionaries and wrote residual shards in about 21 minutes (measured), and H18 does that twice.

## Predictions (guesses)

`needs_vision`, 45%. `not_shown_specific`, 35%. `not_vision`, 15%. `untested`, 5%.

## Commands

On Savio, after `git fetch origin main && git merge --ff-only origin/main`:

```bash
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-02:00:00 docs/research/experiments/h18-residual-controls/run.sbatch
```

## Result, 2026-11-06

Job 40967052, 16 SU (measured). `needs_vision`. Shuffle 0.447 and variance-matched 0.436, against halfway 0.4575. `docs/research/data/h18_result.json`, read in `docs/research/dev-report.md`.
