# H8: can an expert driver join P14's traffic?

**Locked before the expert ran on these routes.** H7's protocol requires this before any full pilot of P14.

## Why

P14 passes its screen, but SimLingo's speed jumps at several collisions, so a stream vehicle probably hit it from behind. Spacing does not change across the arms, so faster traffic means
shorter time gaps. If a careful driver cannot join either, P14 measures physics.

## Design

PDM-Lite, the rule-based expert that generated SimLingo's training data, drives all 20 of P14's routes with the same route file and traffic seed. It sees true positions, so **it is an upper bound on what a careful driver could do**, and it does not prove a person could. It runs from its own scenario-runner tree, whose `actor_flow.py` matched Bench2Drive's over the lines compared (80 to 120).

## Decision rule

A route is **clean** when it finishes with no vehicle collision. Waiting until a timeout counts as clean but is reported separately.

P14 counts as **solvable** if the expert is clean on both of the following:

1. at least 70% of scored slice routes;
2. at least 4 of the 5 routes where SimLingo failed only in the slice (2201, 26956, 27506, 3676, 4937).

If either fails, no full pilot runs at 15 m/s. I would then screen a slower flow on the unscreened bases.

The expert's own failure rate on the neighbourhood is reported with it.

## Prediction

Solvable, about 50% (a guess). Stream vehicles may not brake for anyone who joins in front of them.

## Cost

20 routes with no model on the GPU: under 80 SU (estimate). Spend so far 2873 of 6000 SU.
