# Probe-residual discovery (M3a), definition

**Status: drafted 2026-10-16; Chris's sign-off pending.** `PRD.md` §9.2 and the
handoff's M3a (`upstream-99p/docs/MASTER_HANDOFF.md`, following Buurmeijer et
al.'s linear observers) define it: decode a pre-registered generic state list
from activations, fitted on success frames, and cluster the residual vectors
(decoded − true) on failure frames with HDBSCAN. The result groups failures by
**what the policy mis-represents**. This file fixes what that leaves open.

M3b (policy-minus-expert waypoint residuals) needs expert actions the rollouts
do not log; it waits on the same PDM-Lite pass as B3's expert block (C29).

## The state list (pre-registered; frozen before sealing)

`lead_distance`, `lead_relative_speed`, `pedestrian_distance`, `red_light`,
`time_to_junction`, `occluded`: the PRD's six, exactly as `world_state.py` logs
them and `export_activations.py` stores them. Nothing is added after activations
from the test pool exist.

## Procedure

1. **Activations.** One vector per logged frame at the selected layer and site
   (Step 4's choice), non-residualized or action-residualized as the
   preprocessing variant dictates (§9.2). Frame vectors, not SAE latents: the
   probes need the dense representation.
2. **Probes.** For each state, a ridge regression from activations to the state
   (standardized inputs; ridge strength chosen by `RidgeCV` over 1, 10, 100,
   1000, as in the Step 4 layer sweep), fitted on every frame of every
   **successful** rollout where the state has a value.
3. **Residuals.** On the 3 s window before each failing rollout's failure (the
   contrastive and B3 window), residual = (decoded − true) / σ, where σ is the
   state's standard deviation over the success frames. A state with no value at a
   frame contributes 0 there (no evidence of mis-representation).
4. **Clustering.** HDBSCAN over the residual vectors of all window frames of all
   failing rollouts, minimum cluster size 60 frames (about five rollouts' windows
   at the shards' stride of 5).
5. **Membership.** A failing rollout belongs to the cluster holding the most of
   its window frames, if that cluster holds at least half of them; otherwise to
   none. So each rollout joins at most one axis.
6. **Axes.** Drop clusters with fewer than 20 member rollouts (the contrastive
   support floor, §9.2). Rank by effect × support: mean residual norm of the
   cluster's frames × member rollouts. Keep the top M.
7. **Names.** The two states with the largest absolute mean residual, as
   "over-estimates lead_distance" (decoded > true) or "under-estimates …". The
   describability gate replaces these, as for every method.

## Blinding on the test pool (from the handoff)

Ground-truth state on test-pool rollouts is privileged: residuals there are
computed by the committed script after `methods-frozen-v1`, and nobody inspects
test-pool state values before the key is revealed. B3 receives the same state
features, so no activation method gets covariates a baseline lacks.

## Parameters

| Parameter | Value |
|---|---|
| Probe | StandardScaler + RidgeCV, alphas {1, 10, 100, 1000}, success frames |
| Window | 3 s before the first collision, else the rollout's last 3 s |
| HDBSCAN | min_cluster_size 60 frames, other parameters scikit-learn defaults |
| Rollout membership | modal cluster, if it holds ≥ half the window frames |
| Support floor | 20 rollouts |

## Implementation

`src/discovery/probe_residual.py`, tested on synthetic activations in
`tests/test_probe_residual.py`. Readings the code pins where this file is silent
are in its docstring for sign-off.
