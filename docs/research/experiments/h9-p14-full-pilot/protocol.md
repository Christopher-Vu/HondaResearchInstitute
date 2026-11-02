# H9: does joining fast traffic pass the full efficacy test?

**Locked before any of these routes ran. Efficacy only; no discovery method runs here.** P14 passed its screen (H7) and the expert check (H8).
Jerry asked on 2026-11-02 to keep going until the results are NeurIPS-ready.

## Design

60 fresh base-route pairs, one slice route with the stream at 15 m/s and one neighbourhood route at 7 m/s, in `configs/rollout/step5-pilot-p14-main.yaml`. None of P14's screen bases is reused.

Bench2Drive-220 has only 10 unscreened roads in these four families, so the bases come from a new file: those 10 plus routes cut from the leaderboard's `routes_validation.xml` and `routes_training.xml` (Town13 and Town12), 100 to 500 m long, around one scenario each (`adapters/simlingo/cut_routes.py`). Generator seed 33, chosen once. The draw gave 30 non-signalized right turns, 26 signalized right turns, 2 EnterActorFlow and 2 MergerIntoSlowTrafficV2, with 1 base from Bench2Drive-220, which is much heavier on right turns than the screen. Per-token capture stays on, so these rollouts can enter the dev pool.

**What differs from the screen:** the routes are longer, start on other roads and mostly use a family (non-signalized right turn) with one route in the screen. So this can fail by generalising badly.

## Decision rule

1. **Check first (C24).** As in H7: the car passes within 5 m of the trigger with another vehicle within 50 m in the next 10 s, on at least 70% of scored slice routes. If it fails, P14 is untested at this size.
2. **Verdict.** PRD 9.1 is the verdict of record: uplift at least 20 points, ratio at least 2, Fisher p under 0.01, at least 30 slice rollouts. C23 is reported with it: McNemar p under 0.01 on at least 30 base routes.
3. **Read with it, verdict unchanged.** Results per family; share of slice-only failures that are vehicle collisions.
4. **If it passes,** PDM-Lite drives 20 slice routes drawn with seed 33, and the same H8 rule applies (collision-free on at least 70%).

Routes without an outcome are not rerun unless fewer than 30 base routes score. Candidates tried so far, these included: 16.

## Prediction

Passes PRD 9.1, about 55% (a guess). The screen's 78% against 33% is likely inflated, because it was the best of three screens.

## Cost

120 routes at 3 to 6 SU each: 360 to 720 SU (estimate from H6 and H7; these routes are longer). Spend so far 2954 of 6000 SU.
