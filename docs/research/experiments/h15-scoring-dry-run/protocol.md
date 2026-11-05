# H15: a dry run of the scoring path

**Locked 2026-11-04 before submission. DEV DRY RUN, NOT A VERDICT.** The key here is public, so it is not blind. No `PRD.md` 13.1 branch can be claimed from this run (`CONFLICTS.md` C34).

Every number is tagged: measured, simulated, estimate, read from the code, or guess. Numbers from earlier runs are expected values for a bug check, and they are not targets.

## Why

The path from a directive to PRD 13.1's two conditions has only seen synthetic tests (`docs/research/dev-report.md`, "PRD checks that never ran"). A bug found at the real scoring run could not be fixed, because the pool scores once. This run pushes real activations through every step while a fix is still free. PRD Step 7 also asks for both preprocessing variants, and the residualized one had no code.

## What runs

No simulator. One A40 job, because H12's dictionaries were encoded on an A40 and this run compares against them.

| # | Step | Code | Output under `results/savio/h15/` |
|---|---|---|---|
| 1 | Fit vision to action queries at layer 10 on success frames, and write residual shards | `discovery.residualize` | `action_residual.npz`, `residual-shards/` |
| 2 | Train 18 TopK dictionaries on the residual frame means, with H12's k and seeds | `discovery.sae --frame-means` | `sae/L10_k*_s*/` |
| 3 | Emit directives: H12's dictionaries on H12's shards, and step 2's on the residual shards | `discovery.emit_directives` | `directives/` |
| 4 | Build a throwaway key, and commit to it beside itself | `build_key.py`, `seal.write_commitment` | `throwaway/<key>/` |
| 5 | Verify the commitment, then run `gaps_from_key`, `score`, `harness_is_valid` and `advantage` | `harness.scoring_run` | `report-*.json` |
| 6 | Compare the reports with what the repo already measured | `check.py` | `check.json` |

**Pool.** H12's four shard folders: wave 3, P4 confirm, P7 confirm and P19 main. Read from local manifests and `routes.jsonl` on 2026-11-04 (measured): 550 routes listed, 536 with an outcome, 229 failures. No P20 file is named anywhere in the job.

**Residual variant.** Read `src/discovery/residualize.py`'s docstring for what it pins. `vision_bridge` stands in for PRD 9.2's "pooled visual tokens", because it is the only purely visual site; a same-layer pool could be approximated from the shards (see "Readings to confirm"). That array should be in every H12 shard, since `capture_agent.py` has logged it since 2026-10-09 (read from the code, not checked on the files), and step 1 stops with the route's name if one lacks it. The fit uses about 54,000 frames from 307 successful rollouts (estimate from `duration_game` at 4 logged frames per second). A frozen fit can be applied to a test pool without reading any outcome.

## The throwaway key

`build_key.py` writes two keys and copies each predicate verbatim from `gaps/practice/`. A neighbourhood is read from the manifest's own `neighbourhood_of` label. No new predicate exists. Both keys and their commitments stay under `results/savio/h15/throwaway/`, and the script refuses a path under `gaps/` or `src/`. `src/harness/KEY_COMMITMENT.txt` is never written.

| Key | P4 | P7 | P19 | Why |
|---|---|---|---|---|
| `as-labelled` | T0 | T0 | T2 | Tiers as the practice files state them, so the output can be compared with H12 |
| `branch` | T0 | decoy | T2 | P7 is called a decoy only to run C31's rule and the hit rate on real data. This says nothing about P7. |

## What would count as finding a bug

Any line below is a bug in the path. `check.py` tests all of them except the first and exits 1 if any fails.

| Check | Bug if | Expected value and source |
|---|---|---|
| The job finishes | Any crash or `SchemaError` between steps 1 and 5, or any write outside `results/savio/h15/` | |
| `pool_and_key_sizes_match_h12` | A count differs | 536 rollouts, 229 failures, keys P4 46, P7 54, P19 42 (measured, `docs/research/data/h12_layer10_plain.json`) |
| `efficacy_matches_stored_pilots` | Any number from the key's predicates differs from the pilot's own report | P19 42 of 53 against 7 of 48, 46 pairs (measured, `results/savio/step5-pilot-p19-main/efficacy.json`); likewise `step5-confirm-p4`, `step5-confirm-p7` |
| `jaccards_match_h12` | A non-residualized best Jaccard differs from H12's: above 1e-12 for M2, B2 and B3, above 0.01 for any row that reads a dictionary | Each row of `h12_layer10_plain.json`. The 0.01 allows GPU rounding at the firing threshold (guess). |
| `every_h12_row_was_scored` | An H12 row has no counterpart here | 18 x 3 + 3 rows |
| `delta_agrees_with_the_table` | `advantage`'s point delta differs from the maxima recomputed from the report's per-gap table | Arithmetic |
| `only_non_residualized_validates` | Condition 1 reads valid with no non-residualized activation method recovering a control gap | PRD 13.1 |
| `reports_labelled_and_clean` | A report lacks "DEV DRY RUN", or holds predicate text | |
| `decoy_path_ran` | A decoy enters the Hungarian assignment, or has no C31 verdict | `scoring.py`'s docstring, C31 |
| `residual_shards_sound` | A stored residual differs from the fit's arithmetic, another layer holds values, a scored rollout has no residual shard or its outcome changed, or vision still predicts the residual with R2 above 0.01 on the fit frames | The 0.01 is a guess at what a small ridge penalty leaves behind. It can fire falsely if vision explains almost everything: at explained variance above 0.99 on a small fixture, shrinkage alone left R2 0.33 (simulated). Read `explained_on_fit` before calling this a bug. |
| `outcomes_agree` | `routes.jsonl` and the sidecars disagree on any outcome | Scoring reads the first and the methods read the second |
| `no_real_commitment_written` | `src/harness/KEY_COMMITMENT.txt` exists | It does not exist today (measured) |

**After a bug:** log it in `docs/WHAT_BROKE.md`, fix it with a test before `scoring-frozen-v1`, and rerun the affected steps. A rerun stays a dry run.

## What is not a bug

These are outcomes of the methods on this pool, and the report states them without judging them.

- **Condition 1 reads invalid.** Expected under both rules. No activation axis reached 0.5 on P4 (best 0.490) or P7 (best 0.275) across H12's 18 dictionaries (measured), and only P19 is T2. The report's reason string says "the harness is broken", which is the code's fixed wording for a real pool. Three public gaps cannot show that here.
- **No gap re-confirms under C23.** Expected: 58, 58 and 46 pairs against a floor of 60 (measured from local files).
- **Condition 2 is `evaluated: false`.** Expected: B4, B4p, B5 and B6 have no directive. `arithmetic` is printed so the code runs, and its `holds` is not a result.
- **B2 beats the methods on P19.** Expected: 0.857 (measured, H12).
- **The residual variant misses P4 or P7, or M2 emits no axes in either variant.** PRD 9.2 expects the first, and M2 has emitted no axes on every real pool so far (measured).
- **A residual dictionary has explained variance below 0.8.** It is reported, it does not count, and it stays out of condition 2, as in `dev_eval`. Its best and median sit under `spread`'s `uncounted` key.

## How condition 2 is run

`report-as-labelled.json` uses one dictionary per SAE method, `L10_k64_s0`. That is `SaeConfig`'s default k with seed 0, fixed before this run and without consulting that dictionary's H12 row. `report-all-dictionaries.json` takes the maximum over all of them, to show what `PREREGISTRATION.md` open item 3 is about: H12's gap between best and median was 0.705 against 0.375 on P19 (measured). Replicates and seed are the preregistration's, 10,000 and 20261016. B1 is one seeded draw, because `advantage` takes directives and PRD 10.3 asks for an average over draws. The preregistration does not say how to reconcile those.

## Code changes this rests on

Each change has tests, and `harness/PREREGISTRATION.md` has not been edited.

| Gap | From | Change |
|---|---|---|
| 1. `harness_is_valid` counted any method's match | Preregistration | `Directive.preprocessing` reaches `ScoringReport`, and the check drops residualized reports. `emit_directives` takes the variant from the shards, not from a flag. |
| 2. Fisher against C23 | Preregistration | `harness_is_valid(efficacy_rule=)` and `Gap.reconfirms`. The default stays Fisher, because C23 is pending. The report gives both rules, and `--efficacy-rule` names the one of record. |
| 3. C31 not coded | Preregistration | `efficacy.decoy_verdict`, with the old 5-point band beside it, as C31's reversal asks. It needs at least 60 pairs, because a small pilot would otherwise pass for lack of power. |
| 4. Second pair on a base overwrote the first | Preregistration | `outcome_pairs` pairs the n-th slice route of a base with its n-th neighbourhood route, and `base_routes` counts distinct bases. All 21 stored non-P20 reports recompute unchanged (measured, 2026-11-04). |
| 5. `budget_m` not held at 10 | Preregistration | `scoring.require_budget`, called by `advantage` and by `scoring_run` on every directive it loads. |
| 6. Pilot statistics read as re-confirmation | Found here | `gaps_from_key` copied the key's `efficacy` block, so `harness_is_valid` would have read the sealing pilot's numbers as the test pool's. A key now needs `neighbourhood_predicate`, and efficacy is computed on the pool. This changes the key format, so Chris needs to see it. |
| 7. No way from directive to score | Found here | `emit_directives`, `Directive.to_dict` and `scoring_run`. `dev_eval` scored inside one process, so a method and the key were never separated by a file. |
| 8. A report could name a gap's routes | Found here | `routes_without_outcome` is a count in the report, since the report goes out before the key is revealed. |
| 9. A mistyped dictionary emptied condition 2 of SAE methods | Found here | `condition_2` and `emit_directives.random_run` refuse a dictionary name that matches nothing. |
| 10. The dry-run label came only from the command line | Found here | A key's `dry_run` stamps the report and refuses a label without "DEV DRY RUN". C34's sentence on the best axis travels beside `spread` as `spread_reading`. |

## Readings to confirm

- **"Method" in condition 1 means an activation method.** `scoring_run` passes only those to `harness_is_valid`. This matters here: B3 reached 0.500 on P7 in H12 (measured), so counting baselines could turn "no T0 recovered" into a recovery. `t0_recovered_by` lists every directive either way.
- **`vision_bridge` is the visual pool. Chris, this is your choice.** The handoff's table pools visual tokens at the same decoder layer. Shards can approximate that from `all_tokens` and `driving_queries`, since `capture_agent.py` stores the mean over all tokens and the mean over the last `driving_tokens` positions (read from the code), so their difference gives the mean of the other positions with prompt tokens mixed in. `vision_bridge` was chosen because it is purely visual. A same-layer variant is not built, and it would be built only if Chris asks for it.
- **A residualized B7-pool counts as a baseline.** `B7_pool@<dictionary>@action_residual` has kind baseline, so condition 2's baseline maximum includes it when its dictionary counts (read from the code). This can only make condition 2 harder to meet.
- **Positional pairing.** It assumes a manifest lists twins in the same order on a base. The pool generator should keep that true, and no stored manifest has a second pair on a base for one gap in H12's pool (measured).

## Not in this run

The stale-latent variant of H3, so P7's 0.889 (measured) cannot appear. Nuisance projection and per-layer standardization from PRD 9.2. The describability gate. Any test-pool property: seals, tags and blindness stay untested beyond their arithmetic.

## Predictions (guesses)

`check.py` finds no bug on the first run, about 55%. If it finds one, `jaccards_match_h12` is the likeliest. A residual M1 axis reaches 0.5 on P19 in at least one of 18 dictionaries, about 30%. Residual M1 reaches 0.5 on P4 or P7 in any dictionary, about 10%.

## Reading order

Read `check.json` first. Report it as "the scoring path ran end to end on a throwaway key of public gaps and found N bugs". Quote a report's numbers only with its label, and with best and median across dictionaries beside any axis score (C34).

## Cost

One A40 job with a 2 hour limit, so at most about 58 SU at 29 SU an hour. About 20 to 40 SU is likely (estimate), since H12 did 18 dictionaries and two evaluations in about 16 SU (measured), and this adds one fit, shard writing and three bootstrap runs. Residual shards take about 1 GB (estimate).

```bash
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar \
  bash scripts/submit.sh gpu_a40 --time=0-02:00:00 docs/research/experiments/h15-scoring-dry-run/run.sbatch
```

## Result, 2026-11-04

Job 40906511, 12 SU (measured). The scoring path ran end to end on a throwaway key of public gaps and found 0 bugs. `docs/research/data/h15_dry_run.json`, read in `docs/research/dev-report.md`.
