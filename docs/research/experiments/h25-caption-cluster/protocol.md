# H25: describe each failure from the camera, then group the descriptions

**Locked by the commit tagged `h24-h25-locked`, with H24, before either reads any data.** Jerry asked on 2026-11-12 for both directions from the [literature review](../../literature-review.md), run in parallel. Dev only and not blind. It reads Fail2Drive's categories for a third time, so it also reads H1's pool, which no H22 to H25 choice was tuned on. No `PRD.md` 13.1 branch can be claimed (C34).

Every number is tagged: measured, estimate, or guess.

## Why

The only test the review found comparing description-based grouping with embedding-based grouping (Gupta, Ciftci and Bansal, [2506.06570](https://arxiv.org/abs/2506.06570)) reports 85.5% against 32.4% F1 for an embedding baseline, on robot videos with 8 known failure modes. The review's caveats carry over: it is robot manipulation, the numbers are self-reported, and one model family both groups and judges. H25 asks whether the same approach recovers known failure groups of a driving policy. This is a new method, not a refinement: it reads the camera, not the activations.

## What runs

| Item | Value |
|---|---|
| Pools | Fail2Drive and H1's pool, with the same categories and the same scorer as H24 |
| Input | For each failing route, the last 4 driver-camera frames saved at or before its failure step (1 s apart), resized to 640 px wide (`export_frames.py`). A route with fewer saved frames gets those it has, and its prompt names only them. A failing route with no saved frame is listed and gets no description |
| Blinding | By separation and instruction, checked afterwards. Each route's folder is named by a salted hash, under pools named `a` (Fail2Drive) and `b` (H1's pool). The frames are copied to a folder outside the repository that holds nothing else; the mapping and salt stay in the repository's ignored `results/`. Ids are sorted by hash before captioning, so their order carries no route id or category. Describing agents are told to open only their own frames; grouping agents to use no tool. `audit.py` lists every file each agent touched. **Any touch outside an agent's own frame folder voids that pool's H25 reading as `untested`** |
| Describe | One agent per failing route reads its frames and returns the scene, the most likely reason for the failure, and a 3 to 8 word failure mode (`workflow.js`, prompt fixed in this commit). The session's model, Claude Opus 5.5 (`claude-opus-5-5`), is used |
| Group | 6 independent runs per pool. Each gets every description, in a different fixed order, builds a taxonomy of at most 10 modes and assigns every route to one. Ids an agent invents are dropped and counted; a route listed in a second mode stays only in its first, and the repeat is counted; routes left out are counted. A run whose agent fails is kept and scores as no axes |
| Axes | A run's modes, largest first, top 10 (`to_axes.py`) |
| Scorer | H24's `score_sets.py` |

Deviations from Gupta et al.: Claude, not Gemini and o4-mini; one agent builds the taxonomy and assigns, rather than two; 4 frames from the end, not frames chosen from the whole run.

## The reading, fixed before any result

H24's rule and sentences (median delta at least 0.15, a win on every category, and the route bootstrap's lower end above 0), with "H25" for "H24" and `--min-runs 4` (at least 4 of the 6 runs must have an axis). A pool also reads `untested` if more than 20% of any category's failing routes have no frame, or if the audit finds a breach. If any failing route lacks frames, the primary reading scores H25, B3 and the random control on the routes with frames only (`--restrict-to`), and the all-routes reading is reported beside it. **Primary:** `H25_caption_cluster` on Fail2Drive and on H1's pool, read separately. It counts as supported only if it is `ahead` on both. On Fail2Drive the pair reading is reported beside it, as in H24.

Also reported, with no bearing on the result: the routes without frames; ids invented and left out per run; each run's mode names; and 10 descriptions per pool picked by a fixed rule (the first 10 ids in sorted order) so a reader can judge them.

## What this cannot show

- The describing model is far larger than SimLingo and was trained on other data. A win shows the camera holds enough to group these failures. It says nothing about SimLingo's internals.
- **The frames show what defines each category.** The saved frames are taken after the camera fault is applied, so P4's patch is visible in every frame and P7's freeze shows as repeated frames. Each Fail2Drive category is defined by the object put in view (a wall, an obstacle, pedestrians). A win can therefore mean the describer saw the fault or the object, which is close to reading the scenario label (B2's ceiling under C38 item 4), not that it found why the policy failed. The report says this beside every H25 result, with each category's score shown separately.
- The frames end at the first infraction, whose step is read from outcome details.
- P8's latency, a delayed frame, is probably invisible in 4 frames, so P8 may read low for that reason.
- Claude may have seen Fail2Drive's paper. The agents get frames only, never a name, but the model's prior cannot be removed.
- Agent outputs vary between runs. Six grouping runs give a spread; the descriptions themselves are made once.

## Cost

No SU beyond the shared export. About 52 describing agents for Fail2Drive and about 270 for H1's pool (estimate), plus 12 grouping agents.

## Predictions (guesses)

On Fail2Drive: `ahead` 40%, `not_ahead` 50%, `untested` 10%. On H1's pool: `ahead` 30%, `not_ahead` 55%, `untested` 15%. P4's patch and P7's freeze are visible, so those two should score high; P8's delay probably is not, and it can block the every-category condition.

## Commands

After H24's export, copy `results/savio/h25-frames/` (and nothing else) to a scratch folder outside the repository, then run `workflow.js` with that folder as `frames_dir` for pools `a` and `b`, ids and frame counts read from the mappings by the session, not by any agent. Save its return value as `results/savio/h24-h25/h25-groups.json`. Then:

```bash
python docs/research/experiments/h25-caption-cluster/audit.py TRANSCRIPT_DIR FRAMES_DIR --output results/savio/h24-h25/h25-audit.json
python docs/research/experiments/h25-caption-cluster/to_axes.py results/savio/h24-h25/h25-groups.json results/savio/h24-h25/f2d-mapping.json --pool a --output results/savio/h24-h25/h25-f2d-axes.json
python docs/research/experiments/h25-caption-cluster/to_axes.py results/savio/h24-h25/h25-groups.json results/savio/h24-h25/h1-mapping.json --pool b --output results/savio/h24-h25/h25-h1-axes.json
```

Then H24's two `score_sets.py` commands with `--axes` set to these files, `--min-runs 4`, labels "H25 on Fail2Drive" and "H25 on H1's pool", outputs `h25-f2d-report.json` and `h25-h1-report.json`, and `--restrict-to` a list of the routes with frames only if any failing route lacks one.

## Review before the lock

The same review as H24's found these H25 problems, all fixed before the tag: route ids sorted by category would have set the order of descriptions (now sorted by hash); the mapping sat next to the frames (now separated, with an audit that voids a breach); `to_axes.py` could not read the workflow's output (now `--pool`); a route could sit in two modes (now kept in its first only); runs with failed agents were dropped (now scored as no axes); the frames show the defining fault or object (now stated); and there was no rule for missing frames (now 20%).

## Result, 2026-11-13

342 agents, none failed. Every grouping run assigned every route, with no invented ids and no repeats. The audit found 2,678 frame reads and 0 touches outside an agent's own frame folder (`docs/research/data/h25_audit.json`). No route lacked frames, so no restriction applies. `not_ahead` on both pools (measured). `docs/research/data/h25_f2d_report.json`, `h25_h1_report.json`, `h25_groups.json`.

| Pool | Mean best Jaccard (median of 6 runs) | B3 | Random, matched | Median delta | Route bootstrap | Per category delta |
|---|---:|---:|---:|---:|---|---|
| Fail2Drive | 0.510 | 0.471 | 0.208 | +0.039 | -0.123 to +0.185 | CustomObstacles +0.07, Wall +0.15, PedestriansOnRoad -0.10 |
| H1's pool | 0.161 | 0.184 | 0.127 | -0.023 | -0.071 to +0.013 | P4 -0.03, P7 +0.03, P8 -0.06 |

Reported beside it, with no bearing: on H1's pool the descriptions mention a black patch or blocked view in 38 of 278 and frozen or identical frames in 51, but the grouping runs grouped by what went wrong on the road (for example "Did not brake for vehicle ahead"), never by the camera fault, because the prompt asks why the driving failed.
