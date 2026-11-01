# Findings

The evolving answer to: does the discovery SDK recover failures we planted in CARLA, and how?

## Current understanding

- Planting works: three camera faults (P4, P7, P8) each raise SimLingo's failure rate by 52 to 80 points on the
  same roads (measured, full pilots, PRD 9.1).
- **The SDK recovers a planted failure from the policy's activations (exploratory, H1b, layer 10).** In a pool of 738
  rollouts where P4 is 15% of the 278 failures, contrastive diffing over an SAE trained on frame means returns a
  group of 31 failing rollouts, 27 of them P4 failures and none from P4's fault-free twin routes (Jaccard 0.574
  vs 0.219 for the best baseline; bootstrap interval of the margin +0.26 to +0.52; stable across seeds).
- The same method does not recover P7 (freeze) or P8 (latency). An activation-statistics baseline (B7) finds one
  group that mixes them (58 slice rollouts, 36 of them P8): the two timing faults look alike inside the model.
- The confirmatory test (H1 Tier 1) could not test activation methods: its SAEs did not fit the input. Tier 2
  (per-token data on the whole pool, wave 3) is the confirmatory test, running.

## Patterns and insights

- Every gap that only changed appearance (fog, dust, night, pedestrians, animals, glare) failed to cause failures;
  every gap that removed information from the camera passed. SimLingo is robust to looks, fragile to missing input.
- Before a failure, SimLingo's layer-10 activations mis-decode lead distance, closing speed, pedestrian distance,
  occlusion and red light about twice as badly as on success frames (probe-residual audit, measured). That shift is
  shared by every failure, so probe-residual cannot split failures by cause on this pool: zero axes.

## Lessons and constraints

- A planted gap that is most of the failures makes every method look the same (the 2026-10-15 dev evaluation).
- Base routes 3048 and 3800 crash CARLA at the same simulated second every time; don't count on them.
- Savio's shared login drops every few hours; an agent cannot reopen it.
- SAEs trained on single tokens do not transfer to frame means (explained variance about -0.5); train on the
  representation you will encode.

## Open questions

- Do activation methods beat behaviour (B3) on these gaps, or does the car's behaviour already give them away?
- Do the three camera faults share one internal signature? Partly answered: P7 and P8 seem to share one; P4 has
  its own.
- P8 (delayed camera) is still not recovered. A lag probe (H4) flags camera faults in general with high
  specificity but cannot single out the delay, because the delayed cars stop moving and stop revealing the lag.
