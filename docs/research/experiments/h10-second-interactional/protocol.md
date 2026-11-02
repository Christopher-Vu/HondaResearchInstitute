# H10: looking for a second interactional gap

**Locked before any of these routes ran. Efficacy screen only.** PRD §13.1 needs two interactional gaps. P14 is in its full pilot (H9), and P15 and P16 did not pass. Practice gaps are dev data (PRD §9.2).

## Why these

All three are other vehicles, where SimLingo fails most (601 unplanted routes, `docs/research/research-log.md`).

| Gap | Slice | Neighbourhood | Counts toward |
|---|---|---|---|
| P17 late static cut-in | Parked car cuts in at 1.6 s, or 10 m | Stock 2.7 s, or 15 m | Interactional |
| P18 close emergency vehicle | Starts 25 m behind | Starts 140 m behind | Enumerable slot only |
| P19 wide invading turn | Oncoming traffic 1.2 m over the line on a bend | 0.2 m | Interactional |

P17 needs `adapters/simlingo/patches/cut-in-timing.patch`, which keeps stock defaults when the parameters are absent. Bases come from Bench2Drive-220 plus cuts (`adapters/simlingo/cut_routes.py`), generator seeds 34, 35 and 36. I first set P19 as a highway exit through fast traffic, and replaced it before anything ran because only 6 bases fit within 500 m, too few for a full pilot.

**P18 cannot count as interactional:** a list of scenario families would name it. It would fill PRD §9.1's enumerable slot, where a behavioural baseline should recover it.

## Decision rule

As in H7. The check comes first: the car passes within 5 m of the trigger with another vehicle within 50 m in the next 10 s, on at least 70% of scored slice routes. Then each gap's `screen_rule`: excess of at least 3 of 10. A pass leads to PDM-Lite on the same routes under H8's rule, then a full pilot. Candidates tried so far, these included: 19.

## Prediction

P17 passes about 40%, P18 about 70%, P19 about 35%. At least one of P17 and P19 passes, about 55%. All are guesses.

## Cost

60 routes at 3 to 6 SU each: 180 to 360 SU (estimate), on top of H9's 360 to 720 SU. Spend before both: 2954 of 6000 SU.
