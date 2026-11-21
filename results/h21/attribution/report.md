# Which source supplies the best axis in pooled j rows (diagnostic, not a try, 230 tried)

Yes, with one exception each way: in m23 and in every pooled j row, Wall's best axis is whole-route L8's axis #4 (12 routes, 0.529, measured), and CustomObstacles' best axis is whole-route L8's axis #5 (116 routes, 0.210, measured) in every row except j20 and j21. So the new view moves the score only through PedestriansOnRoad, unless one of its 4 to 6 pooled axes beats 0.210 or 0.529 (only j20 did, 0.243 on CustomObstacles) or displaces a whole-route axis (j21 did, and lost CustomObstacles).

Exploratory, dev, H21b only. This can never enter the UniAD read. It rescores already-scored rows and adds nothing to the 230 tried. Every number is a measured point value (no bootstrap) from `attribute.py`, which reads the pooled axes and the `sources` that `pool_axes.py` wrote into them. It replays the round-robin to tag each kept axis and scores with `sprint_score.py`'s own `read_method`, `best` and `mean_best`. The script checks that the replayed top 10 equals the scored one, and that every per-gap score equals the row's recorded report. Manifest `results/h21/j18/manifest-pair-fixed.json`, routes `results/h21/h21b/routes.jsonl`. Gaps: CustomObstacles 28 failing routes, Wall 14, PedestriansOnRoad 9. j26 and j27 had no folders on main, so they are not covered.

| row | top-10 sources (R = route-L8, V = view) | CustomObstacles best | Wall best | PedestriansOnRoad best | pooled | route-L8 alone: axes, CO / Wall / Ped | view alone: axes, CO / Wall / Ped |
|---|---|---|---|---|---:|---|---|
| m23 | `VVRVRRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #7 (4) 0.444 | 0.395 | 5: 0.210 / 0.529 / 0.068 | m15-source, 5: 0.168 / 0.084 / 0.444 |
| j16+route | `RVRVVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #3 (74) 0.078 | 0.272 | 5: 0.210 / 0.529 / 0.068 | j16, 5: 0.181 / 0.143 / 0.078 |
| j17+route | `RVRVVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #5 (58) 0.098 | 0.279 | 5: 0.210 / 0.529 / 0.068 | j17, 5: 0.173 / 0.180 / 0.098 |
| j18 | `RVRVVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #4 (32) 0.206 | 0.315 | 5: 0.210 / 0.529 / 0.068 | j18-source, 5: 0.120 / 0.240 / 0.206 |
| j19 | `RVRVVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #2 (32) 0.206 | 0.315 | 5: 0.210 / 0.529 / 0.068 | j19-source, 5: 0.120 / 0.135 / 0.206 |
| j20 | `RVRVVRVRVR` | **view #2 (64) 0.243** | route-L8 #4 (12) 0.529 | view #3 (57) 0.100 | 0.291 | 5: 0.210 / 0.529 / 0.068 | j20-source, 5: 0.243 / 0.147 / 0.100 |
| j21 | `RVRVVRVVVR` | **view #3 (105) 0.198** | route-L8 #4 (12) 0.529 | view #6 (21) 0.111 | 0.280 | 4: 0.169 / 0.529 / 0.054 | j21-source, 6: 0.198 / 0.112 / 0.111 |
| j22 | `RVRVVRVRRV` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #6 (47) 0.120 | 0.286 | 5: 0.210 / 0.529 / 0.068 | j22-source, 5: 0.193 / 0.164 / 0.120 |
| j23 | `RRVRVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | route-L8 #6 (38) 0.068 | 0.269 | 6: 0.210 / 0.529 / 0.068 | j23-source, 4: 0.158 / 0.089 / 0.062 |
| j24 | `RVRVVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | route-L8 #6 (38) 0.068 | 0.269 | 5: 0.210 / 0.529 / 0.068 | j24-source, 5: 0.194 / 0.200 / 0.058 |
| j25 | `RVRVVRVRVR` | route-L8 #5 (116) 0.210 | route-L8 #4 (12) 0.529 | view #2 (75) 0.077 | 0.272 | 5: 0.210 / 0.529 / 0.068 | j25-source, 5: 0.170 / 0.141 / 0.077 |

How to read a cell: "route-L8 #5 (116) 0.210" means the best Jaccard for that gap comes from route-L8's own 5th-ranked axis, which holds 116 failing routes and scores 0.210. "Alone" scores use only that source's axes inside the pooled top 10, not the source's full list. In m23 the view is m15 (50-frame window, L8), pooled first. No pooled axis is identical to an axis of the other source, and no gap has a tie for best axis.

Notes (measured):
- route-L8 #3 (154 routes) never enters a pool: its Jaccard with route-L8 #1 (166) is 0.928, over `pool_axes.py`'s 0.8 skip.
- j21's view displaced two route-L8 axes. Its axis #1 (137) has Jaccard 0.82 with route-L8 #5, and its axis #2 (37) has 0.875 with route-L8 #6. route-L8 #5 was CustomObstacles' best axis, so CustomObstacles fell to 0.198.
- j20's CustomObstacles gain comes from its own axis #2 (64 routes, 0.243).
- With route-L8 fixed at 0.210 and 0.529, a pooled row beats m23's 0.3946 only if its PedestriansOnRoad exceeds 0.444, which is m15's 4-route axis. Otherwise the view must beat 0.210 or 0.529 itself. The best view-alone values so far are PedestriansOnRoad 0.206 (j18, j19), CustomObstacles 0.243 (j20) and Wall 0.240 (j18).

Reproduce: `PYTHONPATH=src /opt/miniconda3/bin/python results/h21/attribution/attribute.py` rewrites `attribution.json`; two runs gave the same SHA-1, `4049a51e43b5ab8e3229564be32bab22914b5bcc`.
