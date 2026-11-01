# H1b: SAEs trained on the representation every rollout shares

**Locked 2026-10-31 22:59. EXPLORATORY**: designed after H1 Tier 1 showed that the only SAEs available
(`share/sae-sweep`, trained on single driving-query tokens) do not fit the layer frame means (explained variance
about -0.5), so M1 and B7 could not be tested (`docs/research/research-log.md`, 22:59). Dev only (PRD §9.2).

## Change from H1

Only the SAEs. Everything else is H1's protocol and clarifications unchanged: same 738 rollouts, same answer key,
same methods and baselines, same metric, same Claim A and Claim B rule, same bootstrap.

- **Training data:** the `driving_queries` frame means at the layer, one sample per logged frame, for all 738
  rollouts in the pool. No labels: training never reads `success`, `practice_gaps`, `role` or `sensor`. A tenth of
  base routes is held out by seed for the explained-variance check, as `sae.py` already does.
- **Grid:** layers 10 and 14, k in {32, 48, 64}, seeds 0 to 5: 36 runs, the same grid as the token sweep. Recipe
  otherwise PRD 12.2's (expansion 1, TopK with AuxK).
- **Counting rule:** unchanged; an SAE counts if its held-out explained variance on frame means is at least 0.8.

## Why this is fair

The SAE sees the activations of the pool it will be asked about, as any unsupervised discovery tool would in use.
It never sees outcomes or the planted fault. B7-pool, a baseline, uses the same SAEs, so the advantage test still
compares like with like.

## Prediction

SAEs on frame means fit well (explained variance above 0.8; a frame mean is smoother than a token). With a fitting
SAE, M1 recovers P4 (Tier 1's misfitting SAEs already reached 0.55) and at least one of P7 and P8 (Claim A).
Claim B is uncertain because B7-pool reads the same latents.

## How it will be reported

Always as exploratory, next to H1's confirmatory result and never instead of it. Tier 2 (per-token data from
wave 3, run with the per-token SAEs the protocol named) remains the confirmatory test of M1.
