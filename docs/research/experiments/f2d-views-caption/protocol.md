# The caption row, as run

The rules are in `docs/prereg-views.md` ("The caption row", and the record after the tag). This file holds the exact
prompts and commands. Outcomes of SimLingo and TF++ were already read; UniAD's caption row runs inside each UniAD read.

**Captioner.** Claude Code subagents (general-purpose type) of Chris's session. Each agent writes its exact model id
into its answer, and `agents.py audit` tallies them. Every agent in the contamination run reported `claude-opus-5-5`.

**Pools.** The pool names are neutral: `c` = SimLingo, `d` = TF++, `e` = UniAD (`e-dev` for UniAD's seed-24 test of
the pipeline). Frames are copied from Savio to `C:/Users/CVuDev/caption-frames/<pool>/`, which holds nothing else, and
answers go to `C:/Users/CVuDev/caption-out/<pool>/`. Both folders are outside the repository. Each model's salt and
mapping stay in `results/savio/f2d-views/`.

## Describe prompt

This is H25's `captionPrompt`, unchanged except for the last paragraph. `N` is the route's frame count, and `PATHS`
lists `.../caption-frames/<pool>/<id>/f0.png` to `f<N-1>.png`.

```
You are looking at N frame(s) from the forward camera of a car driven by an AI in a driving simulator.
The frames are one second apart, oldest first: PATHS.
Read each of these images with the Read tool. Do not open, list or search any other file or folder.
The episode ended in a failure, such as a collision, getting stuck, leaving the lane or a traffic violation, at or
shortly after the last frame. Look at what is in the scene and how it changes across the frames, think step by step
about what the AI most likely did wrong, then answer. Describe only what you can see; if the frames do not show the
cause, say so in the reason.

Answer format: use the Write tool exactly once, to write C:/Users/CVuDev/caption-out/<pool>/<id>.json, containing only
a JSON object with the keys "scene" (what is in front of the car that matters, in one or two sentences), "reason" (the
most likely reason the driving AI failed, in one or two sentences), "mode" (a short phrase naming the kind of failure,
3 to 8 words) and "model" (your exact model id, as your system prompt states it). Use no other tool. Then reply with
just "done".
```

## Group prompt

This is H25's `groupPrompt`. There is one change: the list of descriptions is in a file, built by
`agents.py inputs` in workflow.js's order for run `r`, instead of being pasted into the prompt.

```
The file C:/Users/CVuDev/caption-out/<pool>/group-input-<r>.txt holds descriptions of K failed episodes of a driving
AI in a simulator, one per line, each starting with its id. Read that one file with the Read tool; do not open, list
or search any other file or folder. First decide on a taxonomy of at most 10 failure modes that explains these
failures, grouping by the cause of the failure. Then assign every id to exactly one mode. Use every id exactly once
and copy ids exactly. Name each mode in a few plain words.

Answer format: use the Write tool exactly once, to write C:/Users/CVuDev/caption-out/<pool>/group-<r>.json, containing
only a JSON object {"modes": [{"name": ..., "members": [ids]}], "model": your exact model id as your system prompt
states it}. Use no other tool. Then reply with just "done".
```

## Steps per pool

1. Run `export.sh` on Savio as a CPU job. It writes the frames, the mapping and the marker sheet.
2. Check the marker sheet by eye: frame 200 of 2 routes per type, the first 2 by salted hash.
3. Copy `caption-frames/<pool>/` to the laptop.
4. Run one describing agent per id, in sorted id order.
5. `agents.py inputs`.
6. Run 6 grouping agents.
7. `agents.py groups`.
8. `agents.py audit`. Any breach voids the pool's row.
9. `agents.py flags`.
10. On Savio:
    - run H25's `to_axes.py` on `groups.json` and the mapping;
    - run `view_score.py` with `--row caption <model>=runs:AXES.json`, which scores the median over the 6 runs in
      every draw;
    - set `--restrict` to the routes with frames, with every other row rescored on the same routes.

## SimLingo (pool c)

- **Export** (job 41610479): 357 failing routes, each with 4 frames, and none without frames. The job's marker step
  failed because the saved frames have zero-padded names. The fix is commit 69043b5, and the marker sheet was rebuilt
  on the login node.
- **Marker check** (2026-11-19, by eye, `results/savio/f2d-views/markers-simlingo.png`):
  - The sheet has 34 frames from 17 types.
  - None shows a route line, waypoint, trigger box or debug text.
  - One frame shows a billboard of a pedestrian. That is the ImageOnObject scenario's object, not a marker.
  - No flag.

- **Describing, incident (2026-11-19):**
  - The session runs at most 20 subagents at once. The first five dispatchers of 25 hit that limit, and most of
    their launches were refused.
  - One dispatcher relaunched the refused agents, and relaunched route `2055f1c8b059` while its first agent was
    still running.
  - The second agent found the first agent's answer file and read it, because the Write tool reads a file before
    overwriting it. Then it wrote its own answer.
  - That read is of the same route's description, so no label or other route was seen. But it is a touch outside the
    agent's frame folder, so `audit.py` counts it as a breach. Under the prereg's wording that voids pool c's row.
    Chris rules on it, and until then the breach stays in the audit.
  - The overwritten file is kept aside as `caption-out/breach-2055f1c8b059-overwritten.json`. The route was described
    again by a fresh agent.
  - Dispatchers now run waves of at most 18 agents and never relaunch. Missing routes are found from disk and sent
    again by the session.

- **Describing and grouping by the Batch API (2026-11-19)**, as the record after the tag in the prereg allows:
  - **Run:** `api.py describe`, then `collect`. Outputs go to `C:/Users/CVuDev/caption-api/c/`, and the request
    record with frame hashes goes to `c-records/`.
  - **Describe:** 357 of 357 routes, all reported as `claude-opus-5-5`.
    - One answer came back without JSON (`ddc719d083eb`). Its identical request was sent once more and succeeded.
    - Tokens: 497k in, 156k out, about $2.56 at batch prices.
  - **Group:** 6 runs, about $1.30.
    - Runs 0, 1, 2, 4 and 5 gave 10 modes, and run 3 gave 9.
    - There were 0 invented ids and 0 repeats. Run 1 left 1 route unassigned.
  - **Flags:** 33 of 59 mode names match the synonym list.
  - **Earlier subagent descriptions:** the 123 made by subagents (`caption-out/c/`) are kept as a record and not
    scored.
  - **Scoring:** `score_simlingo.sh`, job 41614593.

## Contamination run (2026-11-19, before any real frame was shown)

- Four flat grey 640×360 frames went to one describing agent. It answered: scene "uniform flat gray with no road,
  vehicles ...", mode "undeterminable, no visible scene content".
- One grouping run on that description gave one mode, "undeterminable, no visible scene".
- No mode name matched the synonym list.
- The audit found 4 frame reads and 0 breaches, and both agents reported `claude-opus-5-5`.
- The outputs are in `C:/Users/CVuDev/caption-out/blank/`.

## UniAD (pool e), interim read (2026-11-22)

- **Frames** (`uniad_read.sh`, job 41693917): 552 failing routes of the 872 driven by Sat 09:00, each with 4 frames,
  and none without frames.
- **Describe:** 552 of 552 routes, all reported as `claude-opus-5-5`.
  - One answer came back without JSON (`c6bef1e2489d`). Its identical request was sent once more and succeeded.
  - Tokens: 818k in, 206k out, about $3.70 at batch prices.
- **Group:** runs 0, 1, 3 and 5 finished (10, 9, 10 and 10 modes; 0 invented, 0 repeats, 0 unassigned), about $1.95.
  - Runs 2 and 4 stopped at the 16,000-token cap. Thinking used most of it, and the answer was cut off inside the
    id list. The cap is the script's, not H25's, so grouping's cap was raised to 32,000 (`api.py` `GROUP_TOKENS`),
    and runs 2 and 4 were sent again with the same input.
- **Scoring:** `docs/research/experiments/f2d-unpooled/uniad_caption.sh` on the read's folder.

## TF++ (pool d)

- **Export:** `export_tfpp.sh` from the hri-tfpp clone, a CPU job. It takes each re-driven route's chosen attempt,
  runs `match_rate.py` against the first drive, and runs `f2d-unpooled/tfpp_frames.py` on the failing routes of
  reproducing pairs. The frames are the `rgb` argument of the saved forward calls (1024×384), every 2nd capture,
  so 1 s apart.
- **Trial run** (job 41699093, 2026-11-22 ~06:40, before the s103 and s104 re-drives finished; frames re-exported
  later):
  - 506 of 528 re-driven routes have a valid attempt.
  - Match rate: routes 411/506 (0.81), pairs 163/239 (0.68), with 28 pairs pending.
  - 219 failing routes exported, and none without frames.
- **Marker check** (2026-11-22, by eye, `results/savio/f2d-views/markers-tfpp.png`):
  - The sheet has 29 frames from 15 types, at step 200 of 2 routes per type.
  - None shows a route line, waypoint, trigger box or debug text.
  - One frame shows the ImageOnObject billboard of a pedestrian, and one shows construction cones. Both are scenario
    objects, not markers.
  - No flag.
- **Export** (job 41701155, 2026-11-22 ~07:15, all re-drives done except the one-route s103b rerun):
  - 524 of 534 re-driven routes have a valid attempt.
  - Match rate: routes 423/524 (0.81), pairs 172/257 (0.67), with 10 pairs pending.
  - 230 failing routes exported, and none without frames. 903 frames in all, since some routes have fewer than 4.
  - The kept routes are 1,071: every first-drive passing route plus the 344 routes of reproducing pairs.
- **Describe:** 230 of 230, all `claude-opus-5-5`, 0 failed, about $1.44.
- **Group:** 6 runs at the 32,000 cap, 10 modes each, 0 invented, 0 repeats, 0 unassigned, about $0.84.
- **Flags:** 45 of 60 mode names match the synonym list.
- **Scoring:** `score_tfpp.sh` (job 41701327) for TF++ alone, and `uniad_caption.sh` with this folder (job 41701536)
  for the pooled interim.
  - The first pooled run (41701329) is void: `view_score.py` kept only the last `--restrict`, so TF++ was not
    restricted. It was fixed (repeated `--restrict` now adds) and rerun.
