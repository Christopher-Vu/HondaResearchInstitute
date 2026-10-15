# B3: behavioral stratification, definition

**Status: drafted 2026-10-15 before B3 has seen any rollout; Chris's sign-off
pending.** `PRD.md` §9.3 gives B3 one line: clustering on action error versus
the expert, kinematics and infraction type, given the same per-frame state
features the probe-residual method gets. This file fixes everything that line
leaves open, so B3 cannot be tuned after the fact. Hash-committed with the other
baseline configs before the gaps are finalised (§9.3 fairness rule).

## What B3 is for

B3 is the go/no-go comparison (§13.1): if the policy's internals do not find the
planted gaps better than grouping failures by what the car visibly did, the
interpretability framing collapses. B3 must therefore be a competent baseline,
not a straw man: it sees everything a practitioner reading the logs would see,
and nothing from inside the model.

## Deviation: no expert action error

The rollouts log no expert (PDM-Lite) action, so "action error versus the
expert" cannot be computed without a second simulator pass per rollout. B3 v1
uses kinematics, the state list and infraction type only. If PDM-Lite is later
run alongside the test pool, waypoint error versus the expert joins the feature
set as one more block, decided before the test pool is scored. Proposed in
`CONFLICTS.md` C29.

## Procedure

1. **Rollouts.** Failing rollouts only (`success` false). Every method's axes
   hold failing rollouts, and scoring matches against a gap's failing rollouts.
   Rollouts with no valid outcome are left out.
2. **Window.** The 3 s (60 steps at 20 Hz) ending at the first collision, else
   at the end of the rollout. This is the contrastive method's window, so B3
   and the activation methods look at the same moments.
3. **Features**, per rollout, from the logged state list (`CONTINUOUS_STATES`,
   `red_light`, `occluded` in `export_activations.py`):
   - in the window: mean, minimum and maximum ego speed; minimum lead distance;
     mean lead relative speed; minimum pedestrian distance; minimum junction
     distance; minimum time to junction; fraction of frames at a red light;
     fraction of frames occluded;
   - over the whole rollout: fraction of frames with ego speed below 0.1 m/s
     (the stalls of `docs/WHAT_BROKE.md`);
   - infraction type: one 0/1 column per penalized infraction
     (`sweep_local.PENALIZED`), 1 if the rollout has at least one.
4. **Missing values.** A distance or time with no actor (NaN) becomes a far cap
   (100 m, 10 s): no lead is behaviorally the same as a distant lead. A
   fraction or speed that is NaN on every window frame becomes 0.
5. **Scaling.** Each column is z-scored across the failing rollouts (population
   standard deviation; a constant column becomes 0), so no block dominates by
   units.
6. **Clustering.** k-means with k = min(M, number of failing rollouts),
   10 initialisations, seed 0.
7. **Axes.** One axis per cluster, ranked by size (largest first; ties to the
   cluster whose smallest rollout id sorts first). Score = cluster share of
   failing rollouts. Members = the cluster's rollouts, with their window as
   timesteps.
8. **Names.** The two features with the largest absolute centroid z-score, with
   the direction ("high ego_speed_max, collisions_vehicle"). The description
   lists the cluster size and those features' raw means. The describability
   gate replaces these with the shared pipeline's names, as for every method.

## What B3 may never use

Activations, scenario type or parameters, weather, town, the sealed key, the
practice-gap labels. Outcomes enter only to select failing rollouts (step 1).

## Parameters

| Parameter | Value |
|---|---|
| Window | 3 s (60 steps), ending at the first collision or the rollout end |
| Stall threshold | ego speed < 0.1 m/s |
| Far caps | 100 m for distances, 10 s for times |
| k | min(M, failing rollouts) |
| k-means | 10 initialisations, seed 0 |

## Implementation

`src/baselines/behavioral.py`, tested on synthetic rollouts in
`tests/test_behavioral.py`. Interpretations the code pins where this file is
silent are listed in its docstring for sign-off.
