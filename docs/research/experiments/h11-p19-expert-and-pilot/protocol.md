# H11: P19's expert check, then its full pilot

**Locked before the expert or the pilot ran.** P19 passed its screen (H10). P14 shows how little that means: its screen said 78% against 33%, and its pilot said 52% against 36%. Practice gaps are dev data (PRD §9.2).

## Step 1: expert check

PDM-Lite drives all 20 of P19's screen routes, as in H8. The value used (1.2 m) lies outside the 0.15 to 0.6 m in the route sets, so avoidance may be impossible.

P19 counts as **solvable** when the expert is free of vehicle collisions on both:

1. at least 70% of scored slice routes;
2. at least 3 of the 4 roads where SimLingo failed only in the slice (2802, 3572, 63039, 63044).

Waiting until a timeout counts as clean and is reported separately. The expert sees true positions, so this is an upper bound on a careful driver. If either condition fails, **no pilot runs** and P19 is reported as unfair at 1.2 m.

## Step 2: full pilot, only if step 1 holds

55 base-route pairs, every unscreened InvadingTurn road available, at 1.2 m against 0.2 m (`configs/rollout/step5-pilot-p19-main.yaml`, generator seed 37). 55 is under the 60-pair sizing and above C23's floor of 30. Roads run up to 800 m here, since a 500 m limit left only 32.

1. **Check first (C24).** As in H9. If it fails, P19 is untested at this size.
2. **Verdict.** PRD 9.1 is the verdict of record: uplift at least 20 points, ratio at least 2, Fisher p under 0.01. C23's McNemar is reported with it.
3. **Read with it, verdict unchanged.** Share of slice-only failures that are vehicle collisions, and of those that are timeouts.

No slicing by family or road after the fact. Routes without an outcome are not rerun unless fewer than 30 bases score. Candidates tried so far: 19.

## Prediction

Solvable, about 55%. If solvable, passes PRD 9.1, about 40%: the screen's 70% against 30% is likely inflated, as P14's was. All guesses.

## Cost

Expert: about 60 SU. Pilot: 110 routes at 5 to 9 SU, so 550 to 1000 SU, because stalled routes are long (estimates). Spend so far 3978 of 6000 SU.
