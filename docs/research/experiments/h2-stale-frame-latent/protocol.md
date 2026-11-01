# H2: a stale-frame latent lets contrastive diffing see a frozen camera

**Locked 2026-11-01 00:16. EXPLORATORY**: designed after the H2 diagnostic (`docs/research/research-log.md`,
00:14) showed that frozen frames give bitwise-identical activations when the car is stopped.

## Change from H1b

One added latent per frame, appended to every SAE's latents for M1 and B7-pool alike (`dev_eval.py
--stale-latent`): 1 when the layer-10 frame mean changed by less than 0.1% (relative L2) since the previous logged
frame, else 0. No labels. Everything else is H1b: same pool, SAEs, methods, baselines, metric and rule.

## Decision rule for H3

The latent joins H3's fixed pipeline if, here, M1's best Jaccard with P7 is at least 0.5 **and** M1's best Jaccard
with P4 does not drop below H1b's 0.574. Committed to H3's protocol before H3's evaluation runs.

## Prediction

P7 recovered (oracle ceiling from the diagnostic: 0.906 for the rule alone); P4 unchanged; P8 unchanged.
Watch for: the latent founding a "stopped car" axis in background rollouts (none had an exact repeat in H1's pool).
