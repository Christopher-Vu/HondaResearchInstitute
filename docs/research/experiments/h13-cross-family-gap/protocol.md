# H13: a gap that cuts across scenario families

**Locked 2026-11-03 on Jerry's approval, before any route ran.** Dev only (PRD §9.2).

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

1. **Screen.** 10 pairs, 2 from each family. Check first: at least 99% of the box is black in the saved frames of the first 5 scored slice routes, and the car passes within 5 m of the scenario's trigger with another vehicle within 50 m in the 10 s after, on at least 70% of scored slice routes. Pass: at least 3 excess slice-only failures. Configuration: `configs/rollout/step5-pilot-p20-screen.yaml`; the check is `check.py`.
2. **Full pilot, only if the screen passes and the SU left cover 680.** 40 new pairs, 8 from each family, none reused (the same seeded draw, past the screen's). PRD 9.1 is the verdict. C23's McNemar is reported with it, and 40 pairs sits under its floor of 60.
3. **Methods, only if PRD 9.1 passes.** H12's pipeline on H12's pool without P19, plus P20's rollouts: Claims A, A′ and B, the length audit, and B2's measured score against 0.4.

If the screen fails, the remaining SU stay unspent and the candidate count rises to 20. No slicing by family after the fact.

The expert check does not apply: PDM-Lite reads true positions and has no camera to patch, so it could not fail for this reason.

## Predictions (guesses)

Screen passes, about 30%. PRD 9.1 passes, if screened, about 40%. So about 12% overall. Measured B2 under 0.4 if it passes, about 85%.

## Cost (estimates)

Screen, 20 routes at about 6 SU: 120 SU. Pilot, 80 routes at about 8.5 SU (P19's rate): 680 SU. Methods: about 20 SU. Total about 820 of the 1041 SU left, leaving about 220.

## Notes added 2026-11-03, before any P20 outcome was read

These change no number above. A review of the check and scoring code found them while the screen was driving (`docs/WHAT_BROKE.md`).

- **Check, as coded.** It refuses to give an answer when data is missing: no scored slices, fewer than 5, a scored slice with no shard, a first-five slice with no frames, or no task log. A route whose log says `Ignoring scenario` does not count as meeting traffic, because the leaderboard dropped its scenario and the drive holds no planted event. No route had logged this by 20:38.
- **Lost routes.** Routes stopped before a driving outcome go to the scorer's `rerun` list. Rerunning them cannot change a route that already has an outcome, because the scorer keeps the first attempt with one.
- **Limits on reading a null.** C24's traffic clause counts any vehicle within 50 m, parked hazards included, so it does not show oncoming traffic. By arithmetic, the patch covers an oncoming car only in the last 16 to 32 m of a straight road. The mirror patch can cover the hazard, so the neighbourhood arm is not neutral. Night routes can pass the black test with no patch; two of the first five slices run at night.

## Amendment approved by Jerry, 2026-11-04, before any P20 outcome was read

The first screen array and its rerun have finished and been scored by script, but nobody has read an outcome from them. Everything below was fixed before anyone did.

1. **Three pairs are replaced.** 64155, 64223 and 64250 ended before their hazard (`docs/WHAT_BROKE.md`), so a failure there could only come from the patch. They are cut again as 64901, 64902 and 64903: the same road, start, weather and scenario, running at least 60 m past the hazard and past the end of any bicycle ride. Configuration: `configs/rollout/step5-pilot-p20-screen-amended.yaml`, written by `recut_pairs.py`. The first drives of 64155 stay unread and unscored. 64145 is borderline and is kept, because its invaders drive towards the car; read it with that noted.
2. **Lost routes are rerun.** 2585439, 6408039 and 6423749 were stopped before any driving outcome and rerun as job 40849201. The scorer keeps a route's first driving outcome, so a rerun cannot replace a result.
3. **The new pairs drive one pair per GPU,** so both arms share a node. The first array split arms unevenly across tasks.
4. **What counts as no result.** A failed check, or fewer than 8 scored pairs, reads as untested, not failed, and the candidate is not closed by it. `screen_rule.min_pairs` in `gaps/practice/practice_v3.yaml` encodes the floor.
5. **The rule is unchanged:** at least 3 excess slice-only failures. Reported with it: infractions per arm, how many slice-only failures include a vehicle collision and how many are timeouts only, and discordant pairs by array task and node.

Before any full pilot, the route cutter must measure its tail past the hazard, since the same draw would otherwise repeat this fault.

**Note, 2026-11-04, before P20 was read.** Chris reports that a sealed candidate overlaps P20's region (issue 8), and that candidate is counted as tried and not passed. The screen is still read. A screen pass does not start the full pilot without Chris's say.

## Result, 2026-11-04

P20 fails its screen: 0 against 4 on 10 pairs. The check held. The count becomes 20. `docs/research/data/h13_p20_amended_check.json`, `docs/research/data/h13_p20_amended_efficacy.json`, read in `docs/research/dev-report.md`.
