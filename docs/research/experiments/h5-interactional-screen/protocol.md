# H5: can an interactional gap break SimLingo?

**Locked 2026-11-01, before any of these routes ran. Efficacy screen only; no discovery method runs here.** Jerry asked for
this after H3 (2026-11-01). Practice gaps are dev data (PRD §9.2).

## Why

H3 showed the tool finds two camera faults, which are control gaps. The go/no-go rule (PRD §13.1) is decided on
interactional gaps, and none has passed: P5 (pedestrians in the lane) and P6 (animal crossing) failed their screens.
Both met a car that was starting from rest or close to it (`docs/WHAT_BROKE.md`).

**Hypothesis:** SimLingo fails when a hazard meets the car at speed, or when it falls where the car cannot see it, and
not when the hazard is merely unusual.

## Design

Three gaps in `gaps/practice/practice_v3.yaml`, each screened on 10 fresh base-route pairs, one array each:

| Gap | Slice | Neighbourhood | Tests |
|---|---|---|---|
| P10 late fast crossing | Walker at 3.5 m/s, starts 1.4 s out, car at speed | Same crossing, stock 2 m/s, 2.1 s | A sub-range of a known scenario |
| P11 blind-side crossing | Right side of camera black, walker from the right | Left side black, walker from the right | A conjunction: patch and hazard side |
| P12 walkers at speed | Three walkers 60 m ahead | No walkers | Whether speed explains P5 against Fail2Drive's 87% |

Base routes come from seeds 11, 14 and 16. Earlier seeds were redrawn before anything ran because they drew base routes 3048 and 3800, which
crash CARLA at the same simulated second every time (`docs/WHAT_BROKE.md`). No outcome informed this.

## Decision rule

The existing rule in each gap's `screen_rule`: among scored pairs, slice-only failures exceed neighbourhood-only failures
by at least 3 of 10. The C24 manipulation check is read first; a gap whose check fails says nothing, and is reported as untested.

A pass means "worth a full pilot", not "this gap works". **No full pilot starts from this protocol:** that spend is Jerry's
call after reading the screens. Routes without an outcome are not rerun.

## Predictions

- P12 is the most likely to pass, since it copies a published setup. Medium confidence.
- P10 is uncertain: SimLingo stops well for walkers, but it may be too late at speed.
- P11 passes only if the car cannot infer the walker some other way. It may fail by both arms failing: then the patch alone
  is the cause, which is a control gap and not an interaction. **Read neighbourhood failures for this.**

At least one of the three passes (a guess, about 60%).

## Cost

60 routes at about 4.6 SU per route plus stalls: expected under 500 SU, inside the 6000 SU budget (2237 spent).
