# Findings

The evolving answer to: does the discovery SDK recover failures we planted in CARLA, and how?

## Current understanding

- Planting works: three camera faults (P4, P7, P8) each raise SimLingo's failure rate by 52 to 80 points on the
  same roads (measured, full pilots, PRD 9.1).
- Recovery is untested on a pool where the planted gaps are a minority. H1 tests it.

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
- Do the three camera faults share one internal signature?
