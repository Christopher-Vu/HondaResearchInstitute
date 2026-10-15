# Step 8 — Seal, freeze, generate, score

**Status: drafted 2026-10-15 (Chris's lane, sign-off pending).** `PRD.md` §13
Step 8; §9.1 (sealing protocol), §9.2 (pools), §13.1 (go/no-go).

**Done when** the scoring report exists and every tag below is in git, in this
order, with its timestamp.

## Order of commitments

| # | Tag | What is frozen | Precondition |
|---|---|---|---|
| 1 | `scoring-frozen-v1` | `src/harness/scoring.py`, `bootstrap.py`, `efficacy.py` | tests green |
| 2 | `prereg-v1` | `src/harness/PREREGISTRATION.md` | Chris (and Jerry) sign |
| 3 | `b4-factors-v1` | `configs/baselines/b4_factors_v1.yaml` + its sha256 | before any sealed candidate is chosen |
| 4 | `baselines-frozen-v1` | B1–B8 configs, hashed (§9.3 fairness rule) | before gaps are finalised |
| 5 | `key-v1` | `src/harness/KEY_COMMITMENT.txt` = sha256(key ‖ salt) | 4–6 gaps + 2 decoys passed efficacy |
| 6 | `pool-v1` | the test-pool manifest and generation config | after `key-v1` |
| 7 | `methods-frozen-v1` | discovery code + configs, primary method named | before any test-pool outcome is read |
| 8 | `score-v1` | the one scoring run's report | after 6 and 7 |

Key and salt are revealed only after causal checks and closed-loop scenario
specs are committed (§9.1 step 5).

## Pool composition

With G real gaps and 2 decoys (S = G + 2 slices):

- **Slices.** Each slice ≥ 60 rollouts from ≥ 30 distinct base routes, 4–8% of
  the pool; all slices together < 40% (§9.2).
- **Paired neighbourhoods.** Every slice rollout has a neighbourhood twin on the
  same base route (C23 pairing), so efficacy can be **re-confirmed on the test
  pool** with McNemar, as the preregistration requires for condition 1(b).
- **Background.** Nominal rollouts across the scenario families, so axes must
  pick slices out of ordinary failures, including SimLingo's natural ones
  (HighwayExit, YieldToEmergencyVehicle and the stalls).

Worked size for G = 4 (S = 6), 90 rollouts per slice: 540 slice + 540
neighbourhood + 420 background = **1,500 rollouts**, slices at 6% each, 36% in
total. At 4.1 SU per rollout ≈ **6,200 SU**; at two routes per A40 and six A40s
at once, about 40–45 hours of wall time if the queue cooperates.

## Keeping the key sealed in a public manifest

A rollout's run settings (weather, sensor fault, actors, route) must be in the
manifest for the job to run, so the manifest alone could reveal slices. Two
rules keep it from doing so:

1. **Camouflage.** Background and neighbourhood rollouts also receive
   variations drawn from the same parameter families the slices use (weather,
   sensor perturbations at sub-gap strength, actor mixes), so no field singles
   out a slice. The draw is seeded and its config is part of `pool-v1`.
2. **No labels outside `gaps/sealed/`.** The manifest carries rollout id, base
   route and run settings only. Role, slice membership and tier live in the
   sealed key; scoring code joins them (CI-enforced, `check_sealed_imports.py`).

Jerry does not read `gaps/sealed/` or the pool generation config's sealed half;
the commitments above are what make that checkable rather than a promise (C9).

## Generation

- Shuffled run order (C24), two routes per A40, the selected layers captured
  per-token at Step 4's sites, state and collisions logged (as the dev waves).
- **Orchestration:** Ray inside a Slurm allocation, per C8's reversal (one layer
  for rollout fan-out, sweeps and the baseline matrix, with retries). Fallback
  if it fights us for more than a day: the existing `route_sample.sbatch` array,
  which has run every wave so far. Tasks are idempotent: a route with a valid
  `results.json` is never rerun.
- Manipulation check (C24) on the first frames of a few routes per slice before
  the full pool runs.

## Scoring (one run)

Every method and baseline emits its directive on the pool with the frozen code
and configs; `score-v1` runs `harness.scoring.score` per directive, the
§13.1 checks (`harness_is_valid`, `bootstrap.advantage`) and writes one report.
Any later run is labelled post hoc.

## Open for Chris

1. G = 4 (the §16.2 recommendation) and 90 rollouts per slice?
2. Camouflage rule as above?
3. Ray as primary orchestrator for this step, array as fallback (C8)?
