# H13: a gap that cuts across scenario families (draft)

**Draft, not locked. Nothing has run.** It locks when Jerry approves it and the commit is pushed before any route is submitted. Dev only (PRD §9.2).

## Why this gap

P19 fails PRD Step 5 because one family nearly equals the gap (H12). A single-family gap cannot escape this: passing PRD 9.1 means the neighbourhood holds at most half the key's failures, so B2 stays under 0.4 only if the family holds more failures outside the pilot than the key itself. Bench2Drive-220 has 5 routes per family.

## Gap P20: oncoming traffic hidden

- **Slice:** the left of the camera is blacked out (box 0.0, 0.25, 0.45, 0.65) on a road where the car meets vehicles coming the other way.
- **Neighbourhood:** the same road with the mirror-image patch on the right (0.55, 0.25, 1.0, 0.65), so oncoming traffic stays visible.
- **Families, evenly drawn:** `AccidentTwoWays`, `ParkedObstacleTwoWays`, `HazardAtSideLaneTwoWays`, `VehicleOpensDoorTwoWays`, `InvadingTurn`. Offsets and flows stay at the routes' own values. Roads available: 280.
- **Weather:** each pair takes one drawn from the background's weather, so `ClearNoon` cannot act as a label.

PRD §9.1 names "an `InvadingTurn` with the oncoming vehicle occluded" as a candidate; this widens it to families sharing that mechanism (CONFLICTS C23 allows this). Both arms carry a patch of one size, so only whether the patch hides the traffic differs.

## B2 pre-check (simulated, no rollouts)

`b2_precheck.py`, data in `docs/research/data/h13_b2_precheck.json`. Expected B2 is 0.24 to 0.33 across slice rates 0.5 to 0.8 and added neighbourhood rates 0 to 0.24, under the 0.4 limit. The top stratum is `ability = Overtaking`. Run on P19's real rates, the same simulation gives 0.801 against the measured 0.857.

**The real B2 is measured after the pilot.** If it reaches 0.4, P20 does not count as interactional, whatever else it does.

## The risk: the patch alone

P11's left-patch arm failed 4 of 10 roads with no hazard on that side, where those families' unplanted rates predict about 1.6 (measured, small). If the mirror patch adds about 0.24 here too, the neighbourhood sits near 0.40, and PRD 9.1's ratio of 2 needs a slice near 0.80. The simulation gives a 38% chance of passing even at a true slice rate of 0.80.

## Steps

1. **Screen.** 10 pairs, 2 from each family. Check first: at least 99% of the box is black in the saved frames of the first 5 scored slice routes, and the car passes within 5 m of the scenario's trigger with another vehicle within 50 m in the 10 s after, on at least 70% of scored slice routes. Pass: at least 3 excess slice-only failures.
2. **Full pilot, only if the screen passes.** 40 new pairs, 8 from each family, none reused. PRD 9.1 is the verdict. C23's McNemar is reported with it, and 40 pairs sits under its floor of 60.
3. **Methods, only if PRD 9.1 passes.** H12's pipeline on H12's pool without P19, plus P20's rollouts: Claims A, A′ and B, the length audit, and B2's measured score against 0.4.

If the screen fails, the remaining SU stay unspent and the candidate count rises to 20. No slicing by family after the fact.

The expert check does not apply: PDM-Lite reads true positions and has no camera to patch, so it could not fail for this reason.

## Predictions (guesses)

Screen passes, about 30%. PRD 9.1 passes, if screened, about 40%. So about 12% overall. Measured B2 under 0.4 if it passes, about 85%.

## Cost (estimates)

Screen, 20 routes at about 6 SU: 120 SU. Pilot, 80 routes at about 8.5 SU (P19's rate): 680 SU. Methods: about 20 SU. Total about 820 of the 1041 SU left, leaving about 220.
