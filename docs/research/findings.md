# Findings

The evolving answer to: does the discovery SDK recover failures we planted in CARLA, and how?

## Current understanding

- **The methods find P19 in some dictionaries, and B2 beats them (H12, measured, dev data).** Contrastive diffing's best axis reaches Jaccard 0.705 (33 rollouts, 31 in the key, 14% of failures), far above a stopwatch (0.327) and the catch-all (0.183). The median of 18 dictionaries is 0.375, and 0 of 6 seeds beat B2's `InvadingTurn` stratum (0.857). This is the first time the methods have been tested on anything other than a camera fault.
- **P19 breaks PRD Step 5's single-factor condition (H12).** One family with few neighbourhood failures nearly equals the gap, so B2 reaches 0.857 where the limit is 0.4. Lowering it would take about 370 more `InvadingTurn` routes at ordinary offsets (estimate). On a realistic pool P19 is enumerable, so **interactional gaps meeting the PRD's definition: 0.** A gap has to cut across scenario families (corrected by the H13 pre-check below).
- **A single-family gap cannot meet Step 5 on any pool we can afford (H13 pre-check, arithmetic).** Passing PRD 9.1 leaves the neighbourhood at most half the key's failures, so B2 stays under 0.4 only if the family holds more failures outside the pilot than the key itself. This corrects the earlier note that a family failing often would be enough. Spreading a gap over at least four families drawn evenly brings expected B2 to 0.24 to 0.33 (simulated, no rollouts; the same simulation gives 0.801 for P19 against 0.857 measured). This says nothing about whether such a gap makes SimLingo fail.
- **P4's result depends on the dictionaries (H12).** The best M1 axis is 0.490 here against 0.557 in H3, so Claim A misses by 0.010. Claim B still holds, on 6 of 6 seeds. The frozen-input signal gives 0.889 on P7 again.
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
- **H5's screens found no passing gap (measured).** P10, P11 and P12 each reached 2 of the 3 excess failures
  required. P11 was properly tested. P10 and P12 failed the manipulation check (3 of 5, 4 needed), so by the locked rule they are
  untested, and they would miss the screen even if the check were waived. PRD 13.1 needs two passing interactional gaps.
- **P19 passes PRD 9.1, the first interactional gap on this branch to do so (H11, measured, dev data).** With oncoming traffic 1.2 m over the line on a bend, SimLingo fails 42 of 53 against 7 of 48 at 0.2 m on the same roads: uplift 64.7 points, ratio 5.43, Fisher p 4e-11. On 46 pairs, 32 fail only at 1.2 m and none only at 0.2 m (McNemar p 5e-10); C23's floor of 60 pairs is not met. All 32 are vehicle collisions. The worst case for the 9 lost routes still passes (uplift 50.9, ratio 3.0). One gap on dev data does not meet PRD 13.1, which needs two on the test pool, and 1.2 m lies outside the routes' 0.15 to 0.6 m. No dose-response has been measured.
- **P19 is solvable by the locked rule (H11, measured).** PDM-Lite had no vehicle collision on 9 of 9 slice routes. It reads the exact offset from the scenario, so this shows the road has room and not that a camera-only driver could respond in time.
- **P14 fails its full pilot (H9, measured, 58 slice routes).** 52% against 36%, uplift 15.5 points, ratio 1.43, Fisher p 0.13, on routes that were almost all right turns. Its screen's 78% against 33% did not hold, so **a 10-pair screen pass is weak evidence.**
- **P19, oncoming traffic 1.2 m over the line on a bend, passes its screen (H10, measured, 10 pairs).** 4 slice-only against 0 neighbourhood-only. Expert check and full pilot not done. P17 (late cut-in) and P18 (close emergency vehicle) do not pass.
- **P14, joining fast traffic, is the first interactional gap to pass a screen (H7, measured, 9 pairs).** 5 slice-only against 1 neighbourhood-only failures; 15 m/s against 7 m/s on the same roads. Far short of PRD 9.1's evidence, and not yet shown to be solvable: the car may be hit from behind. P15 (left turn) and P16 (dense oncoming) did not pass.
- **P14 is solvable by the locked rule (H8, measured).** PDM-Lite, which sees true positions, collides on 1 of 9 slice routes against SimLingo's 8 of 10. It fails the success label on 4 of 9, two of them by waiting until a timeout, so fast traffic is harder for it as well.
- **A later walker changes nothing (H6, screen, measured).** P13, with the walker starting at 1.2 s, gives 1 slice-only and 1 neighbourhood-only failure on 10 pairs, with one walker struck in each arm. The check held.

## Patterns and insights

- SimLingo rarely fails walkers and often fails moving traffic (601 unplanted routes, measured): crossings 2 of 65, signalized right turns 8 of 13, left turn with entering flow 8 of 11, EnterActorFlow 6 of 10. Walkers were the wrong place to look for interactional gaps. Whether traffic speed itself causes failures is H7.
- Every gap that only changed appearance (fog, dust, night, pedestrians, animals, glare) failed to cause failures;
  every gap that removed information from the camera passed. SimLingo is robust to looks, fragile to missing input.
- Before a failure, SimLingo's layer-10 activations mis-decode lead distance, closing speed, pedestrian distance,
  occlusion and red light about twice as badly as on success frames (probe-residual audit, measured). That shift is
  shared by every failure, so probe-residual cannot split failures by cause on this pool: zero axes.

## Lessons and constraints

- Screens can mislead in both directions. P14's effect shrank from 78% against 33% to 52% against 36%, while P19's grew from 70% against 30% to 79% against 15%.
- A screen's best of three is inflated. P14 went from 78% against 33% to 52% against 36%. Read a screen pass as a reason to run the pilot and nothing more.
- Cut routes and base routes both carry a neighbourhood failure rate near 35%, which eats power: the efficacy check needs a strong effect to show at all.
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
