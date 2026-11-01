# Findings

The evolving answer to: does the discovery SDK recover failures we planted in CARLA, and how?

## Current understanding

- **Confirmed on fresh drives (H3, a pipeline frozen before the data existed).** On 435 new rollouts with 180 failures,
  contrastive diffing recovers P4 (Jaccard 0.557 vs 0.354 for the best baseline and 0.256 for the catch-all; margin
  interval +0.108 to +0.350; Claims A and B hold). A frozen-input signal read from activations recovers P7 (0.889, 48
  rollouts, all P7 failures; Claim A′ holds). Contrastive diffing alone still misses P7 (0.340). Both results are close to
  their exploratory values (0.574, 0.906). P8 was not tested in H3 and stays unrecovered.
- Caveats to carry with those numbers: 0.557 is the best of 18 dictionaries, and the median is 0.405; the P7 axis does not
  depend on the dictionary at all; "best axis" is chosen using the answer key, as the scoring rule defines.
- Planting works: three camera faults (P4, P7, P8) each raise SimLingo's failure rate by 52 to 80 points on the
  same roads (measured, full pilots, PRD 9.1).
- **The SDK recovers a planted failure from the policy's activations (exploratory, H1b, layer 10).** In a pool of 738
  rollouts where P4 is 15% of the 278 failures, contrastive diffing over an SAE trained on frame means returns a
  group of 31 failing rollouts, 27 of them P4 failures and none from P4's fault-free twin routes (Jaccard 0.574
  vs 0.219 for the best baseline; bootstrap interval of the margin +0.26 to +0.52; stable across seeds).
- The same method does not recover P7 (freeze) or P8 (latency). An activation-statistics baseline (B7) finds one
  group that mixes them (58 slice rollouts, 36 of them P8): the two timing faults look alike inside the model.
- H1 Tier 1 could not test activation methods because its SAEs did not fit the input. H3 became the confirmatory test.
  Tier 2 (per-token data on the whole pool) was not run; wave 3 captured the tokens, so it stays possible.
- **No interactional gap passes yet (H5, screens, measured).** P10, P11 and P12 each reached 2 of the 3 excess failures
  required. P11 was properly tested. P10 and P12 failed the manipulation check (3 of 5, 4 needed), so by the locked rule they are
  untested, and they would miss the screen even if the check were waived. PRD 13.1 needs two passing interactional gaps; there are none.

## Patterns and insights

- Every gap that only changed appearance (fog, dust, night, pedestrians, animals, glare) failed to cause failures;
  every gap that removed information from the camera passed. SimLingo is robust to looks, fragile to missing input.
- Before a failure, SimLingo's layer-10 activations mis-decode lead distance, closing speed, pedestrian distance,
  occlusion and red light about twice as badly as on success frames (probe-residual audit, measured). That shift is
  shared by every failure, so probe-residual cannot split failures by cause on this pool: zero axes.

## Lessons and constraints

- Rollout length alone reaches Jaccard 0.48 on P7, because frozen drives stall and run long. Any P7 axis near that
  value is a stopwatch, not a discovery (plain B7's 0.541 is one). Check length before believing a timing-fault axis.
- A pool's size sets the bar: H3's smaller pool made each fault a bigger share of failures, so the catch-all rose from
  0.155-0.209 to 0.256-0.300.
- A planted gap that is most of the failures makes every method look the same (the 2026-10-15 dev evaluation).
- A manipulation check must not depend on how the model reacts. "Walker within 15 m with the car above 4 m/s" fails when the
  car brakes early, which is the behaviour under test. Measure the hazard before the model can respond (H5).
- Base routes 3048 and 3800 crash CARLA at the same simulated second every time; don't count on them.
- Savio's shared login drops every few hours; an agent cannot reopen it.
- SAEs trained on single tokens do not transfer to frame means (explained variance about -0.5); train on the
  representation you will encode.

## Open questions

- Can any interactional gap break SimLingo strongly enough to pass? Walkers met at speed were struck in only about 1 route in 5 (H5),
  and 8 of 29 neighbourhood routes fail anyway, so a weak effect is hard to see in 10 pairs.
- Do activation methods beat behaviour (B3) on these gaps, or does the car's behaviour already give them away?
- Do the three camera faults share one internal signature? Partly answered: P7 and P8 seem to share one; P4 has
  its own.
- P8 (delayed camera) is still not recovered. A lag probe (H4) flags camera faults in general with high
  specificity but cannot single out the delay, because the delayed cars stop moving and stop revealing the lag.
