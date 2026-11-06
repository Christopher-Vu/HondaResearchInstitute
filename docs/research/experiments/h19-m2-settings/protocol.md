# H19: is M2's zero its clustering settings or its honest answer?

**Locked by the commit that adds it, before the sweep runs.** Dev only (PRD §9.2), on H12's pool with H15's throwaway public key. Not a verdict. No `PRD.md` 13.1 branch can be claimed from it (`CONFLICTS.md` C34), and M2's settings do not change because of it.

## Why

M2, the probe-residual method, has emitted 0 axes on every real pool (measured: H1, H2, H3, H12, H15). A code reading on 2026-11-06 found no bug. It found that every failing window frame on the 738-rollout pool came out as HDBSCAN noise, so no later gate was reached (research log, 2026-10-31 23:26). The clustering runs with `min_cluster_size=60` and sklearn's defaults otherwise (`src/discovery/probe_residual.py`). On synthetic data, one group of 40 failures that misperceives alike, with nothing else beside it, also gives no axis (`tests/test_probe_residual.py`). So the zero may come from the settings and not from the pool.

## What runs

One CPU job (`cpu` profile, 4 cores), no simulator, at about 2 SU or less (estimate). `sweep.py` loads H12's 4 shard folders at layer 10 and runs `probe_residual_directive` under 16 settings: `min_cluster_size` 20 or 60, `min_samples` unset, 5, 10 or 30, and `allow_single_cluster` off or on. `min_support` stays 20, and the window stays 3 s. `ProbeResidualConfig` gained the last two fields with defaults that reproduce the old call, which a test checks.

It then repeats the grid on a planted copy of the pool. 25 failures outside every key gap (seed 19) have their true `lead_distance` lowered by 2.3 success-frame standard deviations on their window frames, so their decode error on that state rises by 2.3. That is a positive control: a group M2 should find.

## The rule, fixed before any result

A planted group is **recovered** under a setting when some axis has a Jaccard of at least 0.5 with the 25 planted failures.

| Result | Condition | Fixed sentence |
|---|---|---|
| `default_finds_planted` | Recovered under the default setting | "M2's default settings recover a planted group of 25 failures, so its zero on the key gaps is not a settings blind spot for a group this strong." |
| `settings_hide_signal` | Not recovered under the default, recovered under another setting | "M2's default settings miss a planted group of 25 failures that another tried setting recovers, so its zero on real pools can come from its settings." |
| `planted_not_recovered` | Recovered under no setting | "No tried setting recovers a planted group of 25 failures, so M2's zero on real pools says little about whether the gaps are there." |

Reported beside the rule, with no bearing on it: each setting's axis count and support, and its best Jaccard on P4, P7 and P19 without the plant. Any setting that reaches 0.5 on a key gap is listed as exploratory, because the setting is then chosen using the key. The default run must give 0 axes, as every earlier pool did; if it does not, the pool or the code differs from before, and that is reported first.

## What this cannot show

The plant shifts one state. A real failure mode may shift several states a little, or none of the six probed ones: none names camera staleness or image occlusion, which are what P4 and P7 are. A recovered plant shows the settings can find a strong single-state group, not that the gaps exist in the residuals.

## Predictions (guesses)

`settings_hide_signal`, 50%. `default_finds_planted`, 15%. `planted_not_recovered`, 35%. Some setting reaches 0.5 on a key gap, 10%.

## Amendment, 2026-11-06 02:25, after the first run and before any rerun

The first run (job 40967092, `docs/research/data/h19_first_plant.json`) read `planted_not_recovered`, and that reading is withdrawn because the plant could not work as designed. `lead_distance` is unknown on frames with no lead vehicle, and `residuals` sets a frame's error to 0 where the true value is unknown. A check job (40967692) found the state known on 129 of the 293 planted window frames, so the mean planted shift was 1.01 and not 2.3. Only 11 of the 25 planted failures had at least half their window frames shifted, which is below `min_support` of 20, so no setting could recover the group (measured). The real runs are unaffected and stand: the default gives 0 axes, and no setting reaches 0.5 on a key gap.

The amended plant draws its failures only from those outside every key gap that know `lead_distance` on at least 60% of their window frames, with the same seed, shift and grid. If fewer than 25 qualify, all of them are planted. If fewer than 20 qualify, the result is `untested`: "H19 is untested: fewer than 20 failures outside the key gaps know lead_distance on enough window frames to carry the plant." The other fixed sentences are unchanged. The planted failures' known shares are reported.

## Result, 2026-11-06

Amended job 40967739, 3 SU (measured); with the first run and the plant check, 6.4 SU in all. `planted_not_recovered`. `docs/research/data/h19_result.json`, read in `docs/research/dev-report.md`.
