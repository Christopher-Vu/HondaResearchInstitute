# H12: do the methods find P19?

**Locked before any SAE or evaluation sees P19's rollouts.** Dev only (PRD §9.2). P19 passed PRD 9.1 (H11), so it is the first interactional gap the methods can be tested on. Until now they have only been tested on camera faults.

## Pool

H3's 439 shards (wave 3, P4-confirm, P7-confirm) plus P19's pilot shards. Rollouts without an outcome are dropped. The answer key for P19 is its 42 failing slice rollouts; I expect about 229 failures in all, so the catch-all should sit near 0.18.

## Fixed pipeline, as H3

1. 18 TopK SAEs on `driving_queries` frame means at layer 10 over the whole pool (k in {32, 48, 64}, seeds 0 to 5), defaults otherwise. No labels.
2. `dev_eval.py` scores M1 raw and capped, M2, B1, B2, B3 and B7-pool, once plain and once with `--stale-latent`.
3. Gaps scored: P19, with P4 and P7 as controls. P4 and P7 keep H3's rollouts but get new SAEs, so these numbers do not replace H3's.

## Claims, as H3, for P19

- **Claim A:** an activation method has an axis with Jaccard at least 0.5 that holds at most 50% of failures.
- **Claim B:** the best activation method beats the best baseline and the catch-all by at least 0.15, the base-route bootstrap interval of the margin is above 0, and at least 4 of 6 seeds agree.
- **Claim A′:** a label-free activation method (M1 raw or capped, or B7-pool) meets Claim A. The stale-latent run is read for P7 only, because a frozen-input detector has no reason to find P19.

## Known weakness, stated before the data

**B2 will probably win, and this says little about the methods.** B2 reads the scenario name. P19 is one scenario family, and its neighbourhood fails rarely (7 of 48), so an axis reading `InvadingTurn` should hold about 42 of about 50 failures, near Jaccard 0.8. Claim B then cannot hold unless a method beats that. So the report will also give, for the best axis, how many members are slice and how many are neighbourhood, because B2 cannot tell 1.2 m from 0.2 m.

## Audits, reported with the claims

- **Length.** The best N longest failing rollouts, against P19's key, as in H3. 14 of P19's 32 slice-only failures end in a scenario timeout, so a stopwatch may do well.
- **Spread.** Median and range of the best Jaccard across the 18 SAEs, as well as the best.

## Predictions (guesses)

Best activation axis reaches 0.5 on P19, about 50%. B2 at least 0.7, about 85%. Claim B fails, about 80%. P4's M1 still reaches 0.5, about 60%. P7's stale axis still reaches 0.85, about 85%.

## Cost

One A40 job, under 2 hours, under 60 SU (estimate). Spend so far 4943 of 6000 SU.
