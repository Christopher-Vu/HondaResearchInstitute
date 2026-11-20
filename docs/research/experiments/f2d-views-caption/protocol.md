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

## Contamination run (2026-11-19, before any real frame was shown)

- Four flat grey 640×360 frames went to one describing agent. It answered: scene "uniform flat gray with no road,
  vehicles ...", mode "undeterminable, no visible scene content".
- One grouping run on that description gave one mode, "undeterminable, no visible scene".
- No mode name matched the synonym list.
- The audit found 4 frame reads and 0 breaches, and both agents reported `claude-opus-5-5`.
- The outputs are in `C:/Users/CVuDev/caption-out/blank/`.
