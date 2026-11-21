Counts: 154 supported / 9 wrong / 1 unsupported (164 claims across intro.tex, data.tex, prereg.tex, whatbroke.tex).

# Fact check of the paper draft, work item 5

Laptop worker 20261120-155444-17096, 2026-11-20. Checked against the repo at `d4f5a7d` (branch lw/20261120-155444-17096).
Line numbers for the .tex files refer to the draft before the fixes. Source line numbers are for the files as they are in this clone.
Tag dates come from `git cat-file -p <tag>` (tagger timestamp, converted to America/Los_Angeles).

Verdict key:
- **S**: supported by the source given.
- **W**: wrong. The source says what is shown instead. "fixed" means a one-line change in the .tex file. "comment" means a `% wrong:` comment was added, because the fix needs new prose and is not a one-line value change.
- **U**: unsupported. A `% unsupported:` comment was added on the line above.
- **R**: flag only, on top of the verdict. The sentence carries a number or a reading taken from a result (dev scores, pool counts, gap classifications, diagnostics), or it implies a held-out outcome. These stay out of the paper until Chris reviews the three-model table. Nothing flagged R was removed: removing it is a decision for Chris, not a fact fix.

Banned words: no "significant" and no "finding" (noun) is applied to our work. "finding unknown ones" (intro.tex:23) is a verb about the proxy. "confirmed on UniAD alone" (data.tex:116, prereg.tex:108) restates the A3 rule's own wording (`docs/prereg-fail2drive.md:243`). It describes a planned procedure, not a claim that a result is confirmed. "a human should confirm" (prereg.tex:31) is an instruction. All four are flagged here and left unchanged.

Compile: not run. `tectonic --only-cached` stops on `size11.clo` (it is not in the cache), and fetching it needs the network.

## intro.tex

| tex:line | claim | verdict | source or correct value |
|---|---|---|---|
| intro.tex:7-10 | usual practice is to enumerate factors and measure degradation, so it finds only listed failures | S | PRD.md:71-80, PRD.md:144 |
| intro.tex:15-18 | a method sees activations, outcomes, speed and infractions, but no scenario name or route config | S | docs/prereg-fail2drive.md:69-71, :133 |
| intro.tex:21-22, 29-30 | recovery of known groups is a proxy for unknown ones | S | docs/prd-discovery-sprint.md:31-33 |
| intro.tex:23-25 | pairs: an in-distribution base route, and a twin on the same road with one unseen scenario | S | CONFLICTS.md:746; docs/step0-trackA-findings.md:70 |
| intro.tex:27 | 100 pairs, 17 scenario types | S | upstream-99p/docs/CITATION_AUDIT.md:235 |
| intro.tex:27-29 | a gap is a type whose twins fail far more than their bases | S | docs/prereg-fail2drive.md:31-32 |
| intro.tex:33-35 | the main rival groups by speed and infractions (B3-behaviour) | S | docs/prereg-fail2drive.md:133, :151 |
| intro.tex:35-37 | the earlier rival read sim distances and was retired because no car has them | S | docs/prereg-fail2drive.md:131; CONFLICTS.md:794 |
| intro.tex:41-42 | SimLingo is a vision-language-action model and the dev model | S | docs/prd-discovery-sprint.md:39 |
| intro.tex:42-43 | finalists are frozen and scored on TF++ (camera + LiDAR) | S | docs/prereg-fail2drive.md:200-232; docs/prd-discovery-sprint.md:40 |
| intro.tex:44-45 | UniAD is modular and camera-only, and blind until the pre-registered read | S | docs/prd-discovery-sprint.md:41; docs/prereg-views.md:4, :59 |
| intro.tex:45-46 | all driving runs in CARLA | S | upstream-99p/docs/CITATION_AUDIT.md:235 (CARLA 0.9.15) |
| intro.tex:55 | no results section yet | S | docs/paper/main.tex:1-2 |
| intro.tex:60-61 | target figures from the planning documents are left out | S | CLAUDE.md "Never state a target as a result"; no target figure found in the four files |

## data.tex

| tex:line | claim | verdict | source or correct value |
|---|---|---|---|
| data.tex:7-8 | a generalisation route plus a base twin on the same road, with only the shift differing | S | CONFLICTS.md:746 |
| data.tex:10 | 100 pairs, 17 types | S | upstream-99p/docs/CITATION_AUDIT.md:235; docs/prereg-fail2drive.md:13 |
| data.tex:10-11 | the benchmark forbids training on its routes, scenarios and assets | S | docs/step0-trackA-findings.md:74 |
| data.tex:11-12 | we train nothing on it | S | docs/prereg-fail2drive.md:113 |
| data.tex:12-14 | definitions of slice, neighbourhood and unit | S | docs/prereg-fail2drive.md:14-16 |
| data.tex:14-15 | route id = seed * 100000 + id | S | docs/prereg-fail2drive.md:26 |
| data.tex:22-24 | gap: 30 runs, 20 points, 2x, Fisher p < 0.01, McNemar beside | S | docs/prereg-fail2drive.md:31-32 |
| data.tex:26-27 | ceiling: 95% and 20%, a control | S | docs/prereg-fail2drive.md:33-34; docs/prd-discovery-sprint.md:43 |
| data.tex:28 | decoy: uplift of at most 10 points, McNemar p > 0.2 | S | docs/prereg-fail2drive.md:35 |
| data.tex:30-31 | background stays in the pool and is never scored | S | docs/prereg-fail2drive.md:36 |
| data.tex:34-35 | B4 has 12 factors, tag `b4-factors-v1` | S | docs/prereg-fail2drive.md:42-43; configs/baselines/b4_factors_v1.yaml (12 factors, counted) |
| data.tex:35 | B4 tagged "before any Fail2Drive drive" | W, fixed | The source says "before this track existed" (docs/prd-fail2drive.md:57). The P6 animal pilot drove Fail2Drive's simulator build before the tag (commit 388e9f6, 2026-10-13; docs/WHAT_BROKE.md:467-473). Changed to "before the Fail2Drive track existed". |
| data.tex:35-36 | Jaccard of at least 0.4 | S | docs/prereg-fail2drive.md:45 |
| data.tex:37 | "B4-unnamed", never "interactional" | S | docs/prereg-fail2drive.md:58 |
| data.tex:41 | `units_rule.py` runs inside each read | S | docs/prereg-views.md:174 |
| data.tex:43-44 | at least 1.5x, at least 5 failing routes | S | docs/prereg-views.md:175-176 |
| data.tex:44-46 | primary units drop Wall, which is excluded by name | S | docs/prereg-views.md:12, :177 |
| data.tex:46 | Wall was a ceiling control "from the start" | W, fixed | "set aside as a ceiling control before the sprint" (docs/prereg-views.md:12-13). Changed to "before the sprint". |
| data.tex:51-52 | a held-out pool is read once, after a freeze tag | W, comment | UniAD is read twice (interim and final) after `views-prereg-v1` (CONFLICTS.md:864-868; docs/prereg-views.md:190-197). |
| data.tex:62 | SimLingo test pool: seeds 101-106, dev in rounds 1 and 2 | S | docs/prereg-fail2drive.md:25; docs/prereg-views.md:57 |
| data.tex:63 | H21: seed 24, second dev pool | S | docs/prereg-fail2drive.md:25, :187; docs/JOURNAL.md:526 |
| data.tex:64 | H21b: seeds 24-26, replication | S | docs/research/experiments/f2d-dev-simlingo/VARIANTS.md:1029-1031 |
| data.tex:65 | TF++: held out in round 1, dev in round 2 | S | docs/prereg-fail2drive.md:227-243; VARIANTS.md:950 |
| data.tex:66 | UniAD: 101-106, held out and blind | S | docs/prereg-views.md:59 |
| data.tex:69-70 | seeds 24-26 never count as evidence | S | docs/prereg-views.md:61 |
| data.tex:76 | 1,200 routes by design | S | docs/prd-discovery-sprint.md:34; docs/prereg-fail2drive.md:24-25 |
| data.tex:80-81 | 1,188 routes with an outcome, 1,185 with state, 357 failing | S, R | Counted: results/savio/f2d-test-simlingo/routes.jsonl has 1,188 rows (3 with `success` null, 357 false); b4-split.json `rollouts_with_states` 1185; VARIANTS.md:8, :70 |
| data.tex:81-82 | a third lost on the first pass and rerun | S | docs/WHAT_BROKE.md:115-136 |
| data.tex:84-86 | SimLingo gaps PedestriansOnRoad, FullyBlocked, BadParking, all B4-unnamed | S, R | docs/prd-discovery-sprint.md:35-39; VARIANTS.md:8-9 |
| data.tex:86-88 | model input saved every 10 steps; driver camera every 20 steps | S | VARIANTS.md:32-35; docs/prereg-views.md:104; h25-caption-cluster/export_frames.py:7 |
| data.tex:93 | H21 is all 100 pairs on seed 24 | S | CONFLICTS.md:746; docs/prereg-fail2drive.md:25; f2d-all/routes.jsonl (200 rows) |
| data.tex:95 | 200 routes, 52 failing | S, R | Counted: results/savio/f2d-all/routes.jsonl; docs/WHAT_BROKE.md:68 |
| data.tex:95-96 | H21b is the same routes, with only the seed changed (25, 26) | S | docs/JOURNAL.md:526 |
| data.tex:98-99 | s25 has 198 routes, s26 has 195; seven tasks failed and were not rerun | S, R | docs/JOURNAL.md:187; counted (s26 routes.jsonl has 197 rows, 2 with no outcome) |
| data.tex:101-102 | 593 routes, 174 failing, 100 pairs | S, R | Counted: results/h21/h21b/routes.jsonl and manifest.json, with -sNN stripped; VARIANTS.md:1059 |
| data.tex:102-103 | manifest `pair` carries the seed and must be stripped | S | docs/WHAT_BROKE.md:22-27 |
| data.tex:103-104 | H21 categories already read; it can rank and kill but cannot make a candidate | S | VARIANTS.md:125, :1053 |
| data.tex:108-109 | TF++ uses the same 1,200-route design | S | CONFLICTS.md:750 |
| data.tex:111-112 | TF++ gaps FullyBlocked, PedestriansOnRoad | S, R | transfer-spec.md:69; docs/prd-discovery-sprint.md:40 |
| data.tex:112-113 | both are SimLingo gaps, so it tests across models, not types | S | docs/prd-discovery-sprint.md:45-46 |
| data.tex:113-117 | A3's round-2 trigger and rule | S | docs/prereg-fail2drive.md:238-243 |
| data.tex:117-118 | round 2 opened and closed by A4 | S, R | docs/prereg-fail2drive.md:249-251; VARIANTS.md:950. Opening round 2 implies m23's TF++ interval included zero, which is a held-out result (docs/JOURNAL.md:310). |
| data.tex:118-119 | TF++ re-driven for frames, and only the re-drive has them | S | docs/prereg-views.md:25, :105 |
| data.tex:122 | UniAD (Bench2DriveZoo) is modular and camera-only | S | docs/JOURNAL.md:970; docs/prd-discovery-sprint.md:41 |
| data.tex:122-123 | not cited: no audited reference | S | No UniAD row in CITATION_AUDIT.md. refs.bib:331 `hu2023uniad` is checked for metadata only, and main.tex:12-15 allows citing only audit-confirmed keys. |
| data.tex:125 | six seeds, 1,200 routes | S | docs/prereg-views.md:59 |
| data.tex:125-127 | outcomes unread; two reads fixed before the tag | S | docs/prereg-views.md:4, :18; CONFLICTS.md:864-868; docs/STATUS.md:15 |
| data.tex:132-134 | every 5 steps, mean-pooled, 0.25 s at 20 Hz | S | VARIANTS.md:30-31; docs/WHAT_BROKE.md:46; transfer-spec.md:20-22 |
| data.tex:135-136 | sites `driving_queries` (the controller's), `all_tokens`, `vision_bridge` | S | VARIANTS.md:31-32; transfer-spec.md:18 |
| data.tex:138-139 | SimLingo 24 x 896; TF++ 6 x 256 | S | transfer-spec.md:20-21 |
| data.tex:139-140 | methods see speed, infractions and outcome | S | VARIANTS.md:32-33; docs/prereg-fail2drive.md:133 |
| data.tex:140-144 | fields removed, salted-hash renaming | S | docs/prereg-fail2drive.md:69-71 |

## prereg.tex

| tex:line | claim | verdict | source or correct value |
|---|---|---|---|
| prereg.tex:4-6 | each change was written, dated and tagged before its data was read | W, comment | A4 has no tag: it is commit c3c3046 (the table caption says so). The items recorded after the views tag are untagged (docs/prereg-views.md:28-44). |
| prereg.tex:8-10 | texts and CONFLICTS C38-C43 | S | docs/prereg-fail2drive.md §1-§10; CONFLICTS.md:745-881 |
| prereg.tex:19 | `b4-factors-v1` 2026-10-15 | S | tag dated 2026-10-15 03:27 PDT; docs/prereg-fail2drive.md:42 |
| prereg.tex:20 | `f2d-prereg-v1` 2026-11-06 | S | docs/prereg-fail2drive.md:3. The tag is absent in this clone (`git tag`), as the caption says. |
| prereg.tex:21 | `methods-frozen-f2d-v1`, `-v2`: 2026-11-12, H22 and H23 on H21 (C38) | S | tags dated 2026-11-12 02:39 and 15:53 PST; CONFLICTS.md:750, :755 |
| prereg.tex:21 | the same tags are "superseded" | U | No source uses the word. CONFLICTS.md:755 says Jerry closed the H21 Fail2Drive line on 2026-11-12. |
| prereg.tex:22 | `f2d-sprint-a1` 2026-11-14 | S | tag 2026-11-14 20:33 PST; docs/prereg-fail2drive.md:124 |
| prereg.tex:23 | `f2d-sprint-a2` 2026-11-16 | S | tag 2026-11-16 18:33 PST; docs/prereg-fail2drive.md:164 |
| prereg.tex:24 | `f2d-freeze-1` 2026-11-17 | S | The document date (docs/prereg-fail2drive.md:197) is 2026-11-17, and the caption says dates are document dates. The tag object is dated 2026-11-16 23:03 PST (2026-11-17 07:03 UTC). |
| prereg.tex:25 | c3c3046 2026-11-18, A4 | S | `git log c3c3046`: 2026-11-18 "prereg A4: round 2 closed..." |
| prereg.tex:26 | `views-prereg-v1` 2026-11-19 | S | tag 2026-11-19 13:24 PST; docs/prereg-views.md:3 |
| prereg.tex:29-32 | A4 has no tag; `f2d-prereg-v1` is not in the clone | S | `git tag` (checked) |
| prereg.tex:38-39 | approved by Chris before the screens or test pool were read | S | docs/prereg-fail2drive.md:3, :6 |
| prereg.tex:39-44 | the base fixes pools, classification, B4 split, label hiding, synonyms, and a primary test with a margin | S | docs/prereg-fail2drive.md:24-25, :30-36, :45, :69-71, :85, :93-97 |
| prereg.tex:44-45 | A1-A3 replace most of the analysis; pools, gap rule and hiding stand | S | CONFLICTS.md:786-791; docs/prereg-fail2drive.md:161-162 |
| prereg.tex:49-50 | A1 came after v1 and v2 and before any sprint method; TF++ unread | S | docs/prereg-fail2drive.md:126-128; VARIANTS.md:15-16 |
| prereg.tex:52 | B3-behaviour replaces full B3 | S | docs/prereg-fail2drive.md:131 |
| prereg.tex:54-56 | each method's own top 10; the old key-chosen rule flatters | S | docs/prereg-fail2drive.md:144; CONFLICTS.md:795-796 |
| prereg.tex:57-60 | no margin; delta, 95% interval and one-sided p by pair bootstrap; primary and secondary rivals | S | docs/prereg-fail2drive.md:148-152 |
| prereg.tex:61-63 | at most 3 finalists, one primary, scored once; pooled headline | S | docs/prereg-fail2drive.md:156-160 |
| prereg.tex:64-66 | caption methods dropped because no frames were thought to exist | S | docs/prereg-fail2drive.md:141; VARIANTS.md:29-33 |
| prereg.tex:72 | A2 came after 134 dev configurations | S | docs/prereg-fail2drive.md:166 |
| prereg.tex:74-77 | Ward repeats; 7 or 8 distinct axes | S, R | docs/prereg-fail2drive.md:177-178; CONFLICTS.md:813 |
| prereg.tex:78-80 | B3-infraction reported, no bar, outside best-rival, proposed after the leads | S | docs/prereg-fail2drive.md:181-184; CONFLICTS.md:815 |
| prereg.tex:81-82 | rescore on both dev pools; a rescore is not a try | S | docs/prereg-fail2drive.md:187-189 |
| prereg.tex:88-89 | A3 after the SimLingo search, before held-out data | S | docs/prereg-fail2drive.md:199-200 |
| prereg.tex:92-94 | Chris chose m23 and m40 on the full record | S | docs/prereg-fail2drive.md:191-195, :212-215 |
| prereg.tex:95-99 | 100-frame cap removed before held-out scores; features unchanged | S | docs/prereg-fail2drive.md:203-206; docs/WHAT_BROKE.md:43 |
| prereg.tex:100-101 | transfer spec binding; B7 sparsity rule fixed blind | S | docs/prereg-fail2drive.md:221-225 |
| prereg.tex:102-104 | order: TF++ interim, UniAD, pooled; scorer before UniAD | S | docs/prereg-fail2drive.md:227-232 |
| prereg.tex:105-109 | round-2 rule; round 1 reported in full | S | docs/prereg-fail2drive.md:238-245 |
| prereg.tex:115-117 | 12 round-2 tries; Chris stopped; none beat m23; nothing frozen | S, R | docs/prereg-fail2drive.md:249-251. This is a dev outcome, and opening round 2 implies the TF++ held-out result. |
| prereg.tex:118 | UniAD scores m23 and m40 under A3 | S | docs/prereg-fail2drive.md:252 |
| prereg.tex:118-121 | read after the views tag; one shared read; post hoc but blind | S | docs/prereg-fail2drive.md:254, :258-259 (later made two reads by C43, which prereg.tex:152 covers) |
| prereg.tex:126 | approved by Chris, tagged at 69668f5, before UniAD read | S | docs/prereg-views.md:3-4; `views-prereg-v1^{}` = 69668f5 |
| prereg.tex:127-128 | the question | S | docs/prereg-views.md:49-51 |
| prereg.tex:130-132 | the two headlines and their labels | S | docs/prereg-views.md:9-11 |
| prereg.tex:133-135 | units: rule units without Wall primary | S | docs/prereg-views.md:12-14, :177-178 |
| prereg.tex:136-139 | rows; img-mean and query-mean via m03; caption | S | docs/prereg-views.md:68-75, :88-90 |
| prereg.tex:141 | try count 216 to 219 | S | docs/prereg-views.md:72 |
| prereg.tex:141-142 | vit-mean: SimLingo only, post hoc, already counted, no ranking | S | docs/prereg-views.md:76-80 |
| prereg.tex:144-145 | metric; 2,000 draws | S | docs/prereg-views.md:179-180 |
| prereg.tex:146-150 | decision rule; "Behaviour ties" is an expected outcome | S | docs/prereg-views.md:184-186, :19 |
| prereg.tex:152-155 | interim 2026-11-21 09:00 PT; final is the record; nothing changes | S | docs/prereg-views.md:192-197; CONFLICTS.md:864-868 |
| prereg.tex:157-160 | 4 frames, 6 grouping runs, median within each draw, new salt, hash order | S | docs/prereg-views.md:98, :111-114, :118-119 |
| prereg.tex:160-162 | blank-frame run first; mode names matched and flagged | S | docs/prereg-views.md:126-129; f2d-views-caption/protocol.md:108-116 |
| prereg.tex:166 | "Two things" decided after the tag | W, comment | docs/prereg-views.md:28-44 lists four: last layer per site, UniAD frames upscaled 256 to 640 px, subagent captioning, then the move to the Batch API. |
| prereg.tex:167-168 | last layer at every TF++ and UniAD site | S | docs/prereg-views.md:29-30 |
| prereg.tex:168-170 | Batch API, same model and prompt, frames listed by hash | S | docs/prereg-views.md:37-42 |
| prereg.tex:170-171 | SimLingo captioned again in full; one captioner per pool | S | docs/prereg-views.md:43-44; docs/JOURNAL.md:56-58 |

## whatbroke.tex

| tex:line | claim | verdict | source or correct value |
|---|---|---|---|
| whatbroke.tex:4-5 | running log written as things happen | S | CLAUDE.md standing rule; docs/WHAT_BROKE.md |
| whatbroke.tex:14 | raw route ids sort by type | S | docs/WHAT_BROKE.md:152 |
| whatbroke.tex:15-17 | H25: 2 of 6 runs would see category blocks; mapping in the parent folder | S | docs/WHAT_BROKE.md:152 |
| whatbroke.tex:17-18 | review caught it before the lock, 2026-11-12 | S | docs/WHAT_BROKE.md:150, :152 |
| whatbroke.tex:18-19 | caches, frame folders and requests ordered by salted hash | S | docs/WHAT_BROKE.md:152; docs/prereg-views.md:118-119; VARIANTS.md:1034 |
| whatbroke.tex:19-20 | an audit lists every file each captioning agent touched | W, fixed | Since the move to the Batch API, "the audit is the request record: each route's frames, listed with their sha256 hashes" (docs/prereg-views.md:37-42). Changed to "an audit lists the frames each caption request carried, by hash". |
| whatbroke.tex:20 | opaque ids are not blind if their order is not | S | docs/WHAT_BROKE.md:152 |
| whatbroke.tex:23-24 | B2 with labels scored PedestriansOnRoad perfectly via a route field (v1) | S, R | VARIANTS.md:15 (B2 1.000) |
| whatbroke.tex:24-25 | B2 has been an oracle ceiling only "since then" | W, fixed | B2 was already oracle-only in the base prereg (docs/prereg-fail2drive.md:79, 2026-11-06) and in C38 item 4 (CONFLICTS.md:753), both before v1 (2026-11-12). Changed to "since the base pre-registration". |
| whatbroke.tex:28-30 | the key-chosen best axis flatters; A1 replaced it | S | VARIANTS.md:20; CONFLICTS.md:795-796; docs/prereg-fail2drive.md:144 |
| whatbroke.tex:34-37 | Ward repeats; 7 or 8 axes; Jerry's agent; A2 continues to 10 | S, R | docs/prereg-fail2drive.md:171-178 |
| whatbroke.tex:41-45 | m19 probes reach an AUROC near 1 by reading window position | S, R | VARIANTS.md:108 (~0.99) |
| whatbroke.tex:48-51 | first dev corpus: 51 of 73 failures; every method scored the same | S, R | docs/WHAT_BROKE.md:423-426, :462 |
| whatbroke.tex:51-52 | needs minority gaps, which Fail2Drive gives | S | docs/WHAT_BROKE.md:434-435; b4-split.json gap failing counts of 17-24 against 357 failing |
| whatbroke.tex:57 | A1: B3 describes speed just before the failure | S | docs/prereg-fail2drive.md:133 |
| whatbroke.tex:58-59 | speed kept for 100 frames; activations use all | S | docs/WHAT_BROKE.md:43-44 |
| whatbroke.tex:61-62 | 645 of 1,185 routes; a median of about 10 s early | S, R | docs/WHAT_BROKE.md:45-46 |
| whatbroke.tex:62-63 | window about 1.5 s, not 3 s | S | docs/WHAT_BROKE.md:47; docs/prereg-fail2drive.md:207 |
| whatbroke.tex:63-64 | cap removed before any held-out score | S | docs/prereg-fail2drive.md:206; CONFLICTS.md:830 |
| whatbroke.tex:64 | the fix "can only raise the rival" | W, fixed | It raised the rival on SimLingo dev, 0.189 to 0.225 (CONFLICTS.md:837). The same window fix lowered it on H21, 0.354 to 0.318 (docs/WHAT_BROKE.md:52-53). Changed to "which raised the rival on SimLingo dev". |
| whatbroke.tex:64-65 | the 6-frame window stands, as tagged in code | S | docs/prereg-fail2drive.md:207-208 |
| whatbroke.tex:68 | B1 draws from failing routes | S | docs/WHAT_BROKE.md:66 |
| whatbroke.tex:69-70 | the first chance column drew from all routes and read low (2026-11-15) | S | docs/WHAT_BROKE.md:64, :68 |
| whatbroke.tex:70 | comparisons and p values did not use it | S | docs/WHAT_BROKE.md:68 |
| whatbroke.tex:71 | the scorer now draws from failing routes only | S | docs/research/experiments/f2d-dev-simlingo/sprint_score.py:105 |
| whatbroke.tex:75-79 | `pair` = `base_id` with the seed (f2d-0, -s25, -s26), against A1 | S | docs/WHAT_BROKE.md:21-23; docs/prereg-fail2drive.md:150 |
| whatbroke.tex:81 | 299 seed-tagged units against 100 pairs | S, R | Counted: 299 distinct `pair` values among the 593 routes, 100 after stripping; VARIANTS.md:1062. Note: WHAT_BROKE.md:19, :23 and VARIANTS.md:1067 say 300, which is the 600-entry manifest's count. |
| whatbroke.tex:81-82 | intervals and p values too narrow | S | docs/WHAT_BROKE.md:23-24; VARIANTS.md:1065 |
| whatbroke.tex:83-86 | independent scorer: same point scores; wider intervals when stripped; the unit explains the gap | S, R | VARIANTS.md:1068-1073 |
| whatbroke.tex:86-87 | reading unchanged; UniAD manifest has no suffix | S, R | VARIANTS.md:1073-1075; docs/WHAT_BROKE.md:26-28 |
| whatbroke.tex:87-89 | recorded in VARIANTS; "no entry in WHAT_BROKE.md yet" | W, fixed | docs/WHAT_BROKE.md:19 has the 2026-11-19 entry. Changed to "and in WHAT_BROKE.md (2026-11-19)". |
| whatbroke.tex:89-90 | concatenated pools must strip the suffix | S | docs/WHAT_BROKE.md:27 |
| whatbroke.tex:93-98 | j02 and j04: tests at the wrong shape, singular covariance, 32 components (b8a3e5a), 2026-11-15 | S | docs/WHAT_BROKE.md:72-78; `git log b8a3e5a` |
| whatbroke.tex:103-107 | floor of 20; categories of 8, 5 and 3; knowable in advance | S, R | docs/WHAT_BROKE.md:162; tag message of `methods-frozen-f2d-v1` (M1 primary) |
| whatbroke.tex:112 | 803 of 1,200 after the first arrays | S, R | docs/WHAT_BROKE.md:119 |
| whatbroke.tex:113-117 | slowdown plus cleanup bug; fixed, tested and rerun once | S | docs/WHAT_BROKE.md:121-136; docs/prereg-fail2drive.md:122 |
| whatbroke.tex:120-123 | TF++ calls `forward` directly, so hooks skip (2026-11-05); the adapter wraps it | S | docs/WHAT_BROKE.md:140-146 |
| whatbroke.tex:126-128 | debug flag draws waypoints and a named trigger point (2026-11-03) | S | docs/WHAT_BROKE.md:172-176 |
| whatbroke.tex:128-129 | test pools driven with the flag off | S | docs/prereg-views.md:134; VARIANTS.md:36-37 |
| whatbroke.tex:129-130 | views prereg checks frames by eye | S | docs/prereg-views.md:136-137 |
| whatbroke.tex:133-134 | reruns differ from the first frame (2026-10-06) | S | docs/WHAT_BROKE.md:1063-1070 |
| whatbroke.tex:134-136 | TF++ re-drive is new; caption covers reproducing pairs, coverage stated | S | docs/prereg-views.md:141, :143 |
| whatbroke.tex:139-140 | no frames in shards, so A1 dropped captions | S | VARIANTS.md:29-31; docs/prereg-fail2drive.md:141 |
| whatbroke.tex:140-143 | 2026-11-18: SimLingo input saved every 10 steps | S | VARIANTS.md:32-34 |
| whatbroke.tex:143-144 | driver-camera images in the same run folders | S | h25-caption-cluster/export_frames.py:7 |
| whatbroke.tex:144-145 | enabled the unpooled experiment and the caption row | S | VARIANTS.md:35; docs/prereg-views.md:26-27 |
| whatbroke.tex:149-151 | UniAD median 34 min over 624 routes; timeouts; partial seeds; resubmitted | S, R | docs/WHAT_BROKE.md:32 (timing, not an outcome) |
| whatbroke.tex:151-153 | interim read by a set time, labelled, C43 | S | docs/prereg-views.md:192-194; CONFLICTS.md:861-868 |

## Unsupported claims

- prereg.tex:21: calls `methods-frozen-f2d-v1` and `-v2` "superseded". No source says so. CONFLICTS.md:755 says Jerry closed the H21 Fail2Drive line.

## Wrong claims left with a comment (the fix needs new prose)

- data.tex:51-52: a held-out pool "read once, after a freeze tag". UniAD has two reads after `views-prereg-v1`.
- prereg.tex:4-6: "tagged in git". A4 and the post-tag records are untagged.
- prereg.tex:166: "Two things". The source records four.
