# H7: does traffic pressure break SimLingo where walkers did not?

**Locked before any of these routes ran. Efficacy screen only; no discovery method runs here.** Jerry asked on 2026-11-02 to keep
going until the results are NeurIPS-ready. PRD §13.1 needs two interactional gaps, and this branch has none. Practice gaps are dev data (PRD §9.2).

## Why

Every interactional gap so far (P5, P6, P10 to P13) planted a walker or an animal, and walker crossings are one of SimLingo's best
scenarios: 2 of 65 unplanted DynamicObjectCrossing routes failed. So I read the failure rate per scenario family over the 601 unplanted routes
in Step 2, the Step 4 dev pool and wave 3. The families that fail most involve other vehicles in motion: signalized right turns 8 of 13, left turn with
entering flow 8 of 11, EnterActorFlow 6 of 10. On signalized right turns, the bases at 13 to 14 m/s failed 8 of 8 and those at 10 to 12 m/s failed 0
of 5 (5 base routes; exploratory; speed was not varied on a fixed road).

**Hypothesis:** SimLingo misjudges vehicles when they are fast or closely spaced, and this holds on the same road, so a change of traffic alone causes the failure.

## Design

Three gaps in `gaps/practice/practice_v3.yaml`, each screened on 10 base-route pairs. Each arm changes only a parameter of the
base route's own scenario, so the pair is the same road and the same scenario with different traffic.

| Gap | Families | Slice | Neighbourhood |
|---|---|---|---|
| P14 fast flow to join | Signalized and non-signalized right turn, EnterActorFlow, MergerIntoSlowTrafficV2 | flow 15 m/s | flow 7 m/s |
| P15 fast flow on a left turn | Signalized and non-signalized left turn, with and without entering flow | flow 15 m/s | flow 7 m/s |
| P16 dense oncoming traffic | Construction, parked obstacle, accident and open-door two-way overtakes | gaps 30 to 45 m | gaps 120 to 200 m |

Generator seeds 30, 31 and 32, chosen once with no redraws. **Some of these base routes helped form the hypothesis.** The change of traffic on a fixed
road is new. Three routes per A40 after main's speed-up.

## Decision rule

1. **Check first (C24).** The car passes within 5 m of the scenario's trigger point in at least 70% of scored slice routes, with
   another vehicle within 50 m in the next 10 s. If this fails, the gap is untested. **The check does not confirm the traffic's speed:** that
   comes from the scenario code reading the parameter and is not measured.
2. **Screen.** Each gap's `screen_rule`: slice-only failures exceed neighbourhood-only failures by at least 3 of 10.
3. **Read with it, verdict unchanged.** Infractions per arm, and how many slice-only failures are timeouts and not collisions. A
   timeout under dense traffic may be correct waiting.

A pass means "worth a solvability check and a full pilot". Before a full pilot, an expert driver (PDM-Lite) must pass the slice, or the failure may be
impossible to avoid. Each family has 5 base routes in Bench2Drive-220, so these gaps hold 20 bases at most. C23's floor of 30 bases will need routes from
another set. Candidates tried so far, these included: 16.

## Prediction

P14 passes (about 50%), P15 passes (about 40%, since its neighbourhood may still fail often), P16 passes (about 30%). At least one
passes (about 70%). All are guesses.

## Cost

60 routes at no more than 5.9 SU per route (H5, before the speed-up): under 360 SU, inside the 6000 SU budget.

## Coordination risk

PRD §9.1 excludes any predicate in a shared document from the sealed key. I cannot read the sealed candidates, so these gaps might overlap one
of Chris's. If they do, that candidate must be replaced. Chris needs to be told.
