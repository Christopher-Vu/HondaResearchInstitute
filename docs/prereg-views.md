# Pre-registration: a ranking of failure-discovery views across three driving models

**Status: approved by Chris 2026-11-19 and tagged `views-prereg-v1`; binding from the tag.**
No UniAD outcome has been read, and none is read before the tag (`docs/prereg-fail2drive.md` §10, A4, as amended by `CONFLICTS.md` C43). Drafted 2026-11-19 after the unpooled experiment was read
(`docs/research/experiments/f2d-unpooled/protocol.md`; its reading was "neither").

## Decisions (Chris, voice, 2026-11-19 ~13:10, before any UniAD outcome is read)

- **Headline:** both of these, each under the decision rule below.
  - The pooled three-model ranking, labelled "SimLingo/TF++ outcomes already read".
  - UniAD alone, labelled as the only blind test.
- **Primary units:** the rule units without Wall. Wall is excluded by name, not by a rule that reads outcomes. Wall
  was set aside as a ceiling control before the sprint and fails on every slice. All rule units (with Wall) and the
  named gaps are reported beside the primary.
- **Rows:** `img-topk` is dropped everywhere. Only the averaged rows and the caption row are new.
- **UniAD sites:** the last BEV encoder grid is the image site, and the track queries are the query site. The FPN rows
  are reported only.
- **Coverage:** two UniAD reads, both fixed here: an interim on Saturday and the final on the full pool (below).
- **Expected outcome:** "Behaviour ties or beats every view" is an expected, reportable outcome, not a failure of the
  study.
- **Flags answered** (Chris, 2026-11-19, before the tag):
  - The image site stays `llm10`, and `vit-mean` is reported as a labelled post hoc row.
  - Tag on approval, once the caption row is in.
  - Interim coverage is every driven route; the caption row's coverage is stated on its own.
  - The TF++ re-drive is kept, because it is the only source of TF++ frames.
- **Caption row added** (Chris, 2026-11-19, before the tag): caption-then-cluster on saved camera frames, H25-style,
  on all three models. It counts as a try. Its rules are below under "The caption row".
- **Recorded after the tag, before any UniAD outcome is read** (2026-11-19):
  - The tag did not fix a layer for the TF++ and UniAD sites. The last layer is used at every site: the TF++ join
    tokens, UniAD's BEV encoder and UniAD's track queries.
  - UniAD's saved front frames are 256 px wide and are upscaled to 640. The native width is recorded per route.
  - Captioning runs as Claude Code subagents of Chris's session (Chris, 2026-11-19). Each agent reports its exact
    model id, which is logged with its output. H25's prompts are kept. There are three mechanical changes: an answer
    format replaces the runner's schema; each agent writes its answer to one file of its own, outside the frames;
    and grouping agents read one file of descriptions instead of a pasted list. `audit.py` allows exactly those
    files.

## Question

Which ways of looking at a driving model find its Fail2Drive gaps best, and is any of them better than what a fleet
already observes (the car's behaviour)? The answer is a ranking with honest, narrow intervals across SimLingo,
TransFuser++ (TF++) and UniAD.

## Data

| Model | Pool | Outcomes |
|---|---|---|
| SimLingo | test pool, 1,185 scored routes | already read (dev for rounds 1–2) |
| TF++ | test pool | already read |
| UniAD | test pool, 6 seeds (101–106), 1,200 routes | **blind** until the tag |

- Seeds 24–26 (H21, H21b, and UniAD's screen) are a dev pool and never count as evidence.
- Every row below except `caption` is computed from per-step layer means that every route logs. So for those rows a
  route counts toward coverage once it is driven, whether or not it has the unpooled capture. `caption` needs camera
  frames, so its coverage is stated on its own (see "The caption row").

## Rows (fixed at the tag)

Rivals and frozen finalists (not new tries):
- **B3-behaviour** (the primary rival), **B3-infraction** and **B7-pool**, per model as in `transfer-spec.md`.
- **m23** (the primary finalist) and **m40**: §9 and `transfer-spec.md`, unchanged.

New views. Each counts as a try, so the running total goes from 216 to **219**:
- **`img-mean`**: the per-frame mean over the image-token site.
- **`query-mean`**: the per-frame mean over the query site.
- **`caption`**: caption-then-cluster on camera frames (see "The caption row").
- **`vit-mean`** (SimLingo only, **post hoc**; already counted as try u10, so not counted again): the pooled vision tokens
  before the projector. It was the best new
  row of the unpooled experiment (0.247 on the named units), and it is added after that score was seen. It is always
  labelled post hoc, enters no ranking claim, and does not change the image site, which stays `llm10` (Chris,
  2026-11-19).

| Model | Image site | Query site |
|---|---|---|
| SimLingo | `llm10` (see the note to Chris) | `dq`, driving queries at layer 10 |
| TF++ | the fused backbone grid (`vision_bridge`) | the decoder join tokens |
| UniAD | the last BEV encoder grid | the track queries |

Each new view is the mean over the approach window: 12.5 s before the failure step, or the route's last 12.5 s. Its
discovery step is m03: standardise, PCA 32 over all routes, Ward clustering of the failing routes, A2 distinct axes,
top 10. Every fit is label-free and runs on the routes being scored.

## The caption row

H25's method (`docs/research/experiments/h25-caption-cluster/protocol.md`, its `workflow.js` prompts unchanged),
applied per model.

**Frames.**
- For each failing route: its last 4 front-camera frames at or before the failure step, 1 s apart, resized to 640 px
  wide.
- The frames per model:

  | Model | Source | Spacing used |
  |---|---|---|
  | SimLingo | driver-camera PNGs | the saved PNGs, every 20 steps |
  | TF++ | RGB in `capture/inputs`, which only the re-drive saved | every 2nd capture |
  | UniAD | front JPEGs | every 4th JPEG (they are saved every 5 steps) |

- A route with fewer frames gets those it has. A failing route with none gets no description and is listed.

**Captioner.**
- Claude Opus 5.5 (`claude-opus-5-5`), as in H25: one describing agent per failing route, then 6 independent
  grouping runs per model. Each grouping run builds at most 10 modes and assigns every route.
- Axes are a run's modes, largest first, top 10 (`to_axes.py`).
- The row's score is the median of its 6 runs' scores, taken within every bootstrap draw.
- Captioning uses no Savio GPU. Frame export is a CPU job, and no captioning runs on the A40s UniAD needs.

**Label hiding.**
- Each route's frame folder is named by a salted hash (a new salt, kept in git-ignored `results/`), under neutral
  pool names. Routes are sorted by hash before captioning, so their order carries no route id or type.
- The frames are copied to a folder outside the repository that holds nothing else, and the mapping stays in
  `results/`.
- `audit.py` lists every file each agent touched. Any touch outside an agent's own frame folder voids that model's
  caption row, which is then reported as `untested`.

**Contamination check**, as `docs/prereg-fail2drive.md` §3 requires:
- (a) Before any frame is shown, the describe and group prompts are run once on blank frames (no rollout data), and
  the outputs are kept.
- (b) Every mode name is matched mechanically (case-insensitive, word stems) against the synonym list below. Every
  matching axis is flagged in every table.
- The frames show what defines each Fail2Drive type, because the inserted object is in view. So flags are expected.
  Each type's score is shown separately, beside B2's oracle ceiling.

**Route markers.**
- All three test pools were driven with `debug_level: 0` (the configs, checked 2026-11-19), so no route or trigger
  markers were drawn.
- Before captioning, frames are also checked visually for markers: frame 200 of 2 routes per type per model, chosen
  by salted order without reading outcomes.
- If any marker is found, the row's results are flagged, and marker density per type is reported.

**Coverage.**
- The caption row covers only failing routes with frames, so it is stated on its own:
  - SimLingo: every route.
  - TF++: re-driven pairs whose failure reproduces.
  - UniAD: driven routes.
- The other rows and rivals are rescored on the same routes beside it, so its contrasts stay paired.
- UniAD's descriptions are made once. The final read adds descriptions for newly driven failures and reruns the 6
  grouping runs on all of them.

**Synonym list** (frozen at the tag; hand-written, expanded once by the agent, a language model):

| Type | Matches |
|---|---|
| Animals | animal, deer, dog, cow, horse, wildlife, creature |
| BadParking | parked, parking, double-parked, badly parked, stopped car, vehicle on shoulder |
| ConstructionPedestrian | construction, roadwork, worker, cone, barrier, pedestrian |
| ConstructionPermutations | construction, roadwork, cone, barrier, lane closure |
| CustomObstacles | obstacle, object, debris, box, unusual object |
| FullyBlocked | blocked, road blocked, impassable, closure, dead end |
| HardBrake | hard brake, sudden braking, brake check, lead vehicle stop, rear-end |
| ImageOnObject | image, picture, poster, billboard, painted, sticker |
| ObscuredStop | stop sign, obscured, hidden sign, occluded sign |
| OppositeConstruction | construction, roadwork, oncoming lane, opposite lane, cone |
| PassableObstacles | passable, small obstacle, drive over, low object |
| PedestrianCrowd | crowd, group of pedestrians, many people |
| PedestrianOtherBlocker | pedestrian, occluded pedestrian, hidden pedestrian, emerging pedestrian |
| PedestriansOnRoad | pedestrian, person on road, people on road, walker |
| RightConstruction | construction, roadwork, right lane, cone |
| RightOfWay | right of way, yield, failed to yield, junction, intersection priority |
| Wall | wall, barrier, concrete, solid structure |

## Units, metric and intervals

As in the unpooled protocol:
- **Units:** `units_rule.py`, run inside each read (on UniAD that means inside the blind read). It admits every
  Fail2Drive type whose generalisation routes fail at least 1.5× as often as their base twins, with at least 5
  failing generalisation routes.
  - **Primary:** those units minus Wall.
  - Also reported: all rule units, and the named gaps.
- **Metric:** rank-averaged best match is primary; top-10 best match is secondary.
- **Intervals:** a pair bootstrap with 2,000 draws. Pooled numbers are a fixed mean over units, with no random effect.

## Decision rule (both headlines: pooled, and UniAD alone)

- **A row ranks above the fleet** if its 95% interval against B3-behaviour lies above 0.
- **Row A ranks above row B** only if the paired interval of A minus B lies above 0. Otherwise they tie, and the
  ranking is the partial order these intervals give.
- **Selection:** wherever a "best of the new views" is quoted, it is re-selected in every draw.
- **Reporting:** each model alone, the full try count and the coverage are reported whatever the result.

## UniAD reads

1. **Interim: Saturday 2026-11-21, 09:00 PT.**
   - It uses every test-pool route that has a driven record by then.
   - It is labelled interim, with coverage stated: routes, pairs, and failing routes per unit.
2. **Final: the full 6-seed pool once it lands.** This is the result of record.

Nothing changes between the two reads: not the rows, units, metric or rules. The units rule runs inside each read,
on that read's routes.

## Order

1. Chris approves this file, then it is tagged `views-prereg-v1`.
2. The SimLingo and TF++ rows are scored. Their outcomes are already read, so this needs no tag.
3. The interim UniAD read, then the final.
4. The pooled ranking at each read.
