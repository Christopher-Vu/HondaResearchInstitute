Supported 164 / wrong 16 / unsupported 3 (methods.tex 144/10/3; fig-pipeline.tex 20/6/0).

# Fact check: docs/paper/methods.tex and docs/paper/fig-pipeline.tex

Branch lw/20261121-041955-19147. Line numbers are for the .tex files after the fixes in this branch. S = supported,
W = wrong, U = unsupported. "Fixed by patch" means the previous worker's saved patch
(`tasks/fc-partial/methods-fig.diff`) made the fix and this pass re-verified it. VARIANTS.md, cache_methods.py,
pool_axes.py, sprint_score.py and the j scripts are under `docs/research/experiments/f2d-dev-simlingo/`;
protocol.md and view_score.py under `docs/research/experiments/f2d-unpooled/`.

No result number appears in either file (checked: every decimal is a setting, a threshold or a duration). Neither file
uses "significant", "confirmed" or "finding".

## methods.tex

| tex line | claim | verdict | source or correct value |
|---|---|---|---|
| 4-7 | Scoring compares first ten distinct axes with each gap's failing routes | S | sprint_score.py:10, :34-40, :102 |
| 14 | Search ran as the discovery sprint of prd-discovery-sprint.md | S | prd-discovery-sprint.md:1-3 |
| 19-20 | Row written in VARIANTS.md before its score is read | S | prd-discovery-sprint.md:115-117; VARIANTS.md:578, :1001, :1141 |
| 20-21 | Chris approved each batch before it ran | U | approval logged for m batches 1-5 and round 2 only (VARIANTS.md:44, :79, :96, :576, :790, :950); none for j batches (:120, :150) or j16-j27; comment added |
| 22-24 | One CPU pass (cache_pool.py) writes one per-route file; one scoring command | S | cache_pool.py:2; VARIANTS.md:40-42; sprint_score.py:1-6 |
| 23 | A method runs in minutes | S | VARIANTS.md:922, :971, :1013 (CPU jobs of 3 to 11 minutes) |
| 25-26 | Failures and cancelled runs count as tries | S | prd-discovery-sprint.md:116-117 |
| 26-27 | A rescore under a new rule is not a try | S | prereg-fail2drive.md:189 |
| 27-28 | Every dev table states the try count; dev p values exploratory | S | prereg-fail2drive.md:153 |
| 29-31 | At most three finalists, scored once per held-out model, one primary in the tag | S | prereg-fail2drive.md:156-158 |
| 34 | 134 tries at A2 | S | prereg-fail2drive.md:166 |
| 34 | 188 at the freeze | S | prereg-fail2drive.md:199 |
| 34-35 | 202 when the search stopped | S | prereg-fail2drive.md:253 |
| 35-36 | 219 once the views rows are counted | S | prereg-views.md:72 |
| 36 | Current count: was 'is 219', now 232 after j16-j27 | W (fixed by patch) | VARIANTS.md:1495 (232) |
| 38-39 | Chris's agents wrote m, Jerry's explore loop wrote j | U | j01-j15: VARIANTS.md:120, :150; j16-j27 rows name laptop workers, not a side (VARIANTS.md:1141, :1181); comment added |
| 39-40 | Both families logged in one file and used the same scorer | S | VARIANTS.md:150-153 |
| 46-47 | Failure step is the earliest timed infraction | S | src/harness/failure_time.py:52-70 |
| 47 | Collisions carry a logged step | S | failure_time.py:57 |
| 48-50 | Located infractions timed at first step within 0.5 m of nearest approach | S | failure_time.py:7-8, :22, :33 |
| 51 | No timed infraction, or passing: window ends at route end | S | failure_time.py:12-13, :54-55; cache_pool.py:38 |
| 54-57 | Three means per route, site, layer: whole, approach window, early | S | cache_pool.py:6-8, :36-41 |
| 59 | W = 6 by default | S | cache_pool.py:27, :49 |
| 59 | Frames 0.25 s apart | S | VARIANTS.md:27 |
| 61 (comment) | Source of 0.25 s given as WHAT_BROKE.md 2026-11-16 | W (fixed) | no 0.25 s entry in WHAT_BROKE.md; source is VARIANTS.md:27 |
| 59-60 | 6 frames about 1.5 s; 50 frames about 12.5 s | S | prereg-fail2drive.md:207; prereg-views.md:88 |
| 63-64 | Rows in salted-hash order, never route-id order (H25) | S | cache_pool.py:13, :51; flag for Chris added: raw route ids are kept (cache_pool.py:68, :75) against prereg-fail2drive.md:70-71 |
| 64-65 | frames_pool.py keeps last 50 frames of a few layers | S | frames_pool.py:2, :12-17 |
| 69 | L8 is layer 8 of driving_queries; SimLingo has 24 layers | S | transfer-spec.md:20 |
| 70-71 | Concatenated layers standardised and divided by sqrt(n) | S | cache_methods.py:89-90 |
| 76-77 | Most methods are variations on m03 (cache_methods.py) | S | cache_methods.py:2; VARIANTS.md tables |
| 79-80 | One summary, site and layer for every route | S | cache_methods.py:7, :85-90 |
| 81 | Standardise columns over all routes | S | cache_methods.py:8, :117 |
| 83 | PCA on all routes, 32 components, scores standardised | S | cache_methods.py:8, :117, :136, :171 |
| 84-85 | Ward linkage on failing rows | S | cache_methods.py:58, :139 |
| 86-90 | Cuts 2, 3, 5, largest first; A2 dedup, continue at 6, 7, ... | S | cache_methods.py:39, :52-72; prereg-fail2drive.md:171-176 |
| 93 | Only pass/fail is read | S | cache_methods.py:154 |
| 93-94 | No model trained on Fail2Drive in the sense its authors forbid | S | PRD.md:296-298 (rule covers training or fine-tuning); prd-fail2drive.md:88 |
| 99-100 | Each row changes one thing about m03 or combines earlier rows | W (fixed) | m01, m02, m14 build on B7 (VARIANTS.md:51-52, :89); clause added |
| 99 | Table lists the m methods | W (fixed) | m14, m18, m41-m51 were missing (VARIANTS.md:89, :107, :661-665, :797-801, :890-891); rows added. m21 is B3-infraction, m37 unused (VARIANTS.md:103, :606) |
| 105 | Pools merge two or three other methods | W (fixed) | m09 pools four sources (VARIANTS.md:84); now 'two to four' |
| 106-109 | Round-robin, skip Jaccard >= 0.8, stop at 10, fixed before scoring | S | pool_axes.py:7-9, :34-37 |
| 112 | Both finalists frozen at f2d-freeze-1 | S | prereg-fail2drive.md:200, :212-216; git tag f2d-freeze-1 |
| 115-118 | m23: m15 (L8 w50) then whole-route L8, pooled in that order | S | VARIANTS.md:589, :1050; prereg-fail2drive.md:213 |
| 119-121 | m23 idea: last seconds versus failures over the route | U | VARIANTS.md:588-589, :657-659 give a pedestrian view plus a FullyBlocked view; comment added |
| 122-124 | m40: L8 w50 PCA 64 then whole-route L20 | S | VARIANTS.md:661, :1051; prereg-fail2drive.md:215 |
| 135 | m01, m02 error-aware B7; m02 on window frames | S | VARIANTS.md:51-52 (rank is kappa times enrichment) |
| 137 | m04 balanced logistic probe picks components | S | cache_methods.py:10-11, :120-123 |
| 139 | m06 m03 plus kinematics, equal block weight | S | cache_methods.py:13-14, :172-174 |
| 140 | m07 window minus early mean | S | cache_methods.py:12, :163-164 |
| 142 | m14 (added row) | S | VARIANTS.md:89 |
| 144 | m05 sweep of 24 layers of two sites plus vision_bridge | S | VARIANTS.md:55, :72 |
| 145 | m08, m16 L5+L8+L20 concatenated | S | VARIANTS.md:83, :105 (m08 also tried L1+L5+L8+L20) |
| 147 | m11, m15, m24 windows 3-100; was 'Longer' | W (fixed by patch) | 3 < 6 (VARIANTS.md:88); now 'Other'; :104, :590 |
| 148 | m12, m17 other linkages | S | VARIANTS.md:86, :106 |
| 149 | m13 cut schedules 4+6; 10 | S | VARIANTS.md:87 |
| 151 | m18 (added row) | S | VARIANTS.md:107 |
| 153 | m19 layers by probe AUROC, uninformative | S | VARIANTS.md:108 |
| 156 | Pools m09, m10, m20, m23, m28 | S | VARIANTS.md:84-85, :109, :589, :594 |
| 157 | Pools m41-m46, m48, m50, m51 (added row) | S | VARIANTS.md:661-665, :797-798, :800, :890-891 |
| 158 | m22, m27 concatenated summaries or sites | S | VARIANTS.md:588, :593 |
| 159 | m25 whole route at other layers | S | VARIANTS.md:591 |
| 160 | m26 window minus whole-route mean | S | VARIANTS.md:592 |
| 161 | m29-m32 per-frame summaries | S | VARIANTS.md:595-598 |
| 163 | m33-m36 j09 variants | S | VARIANTS.md:599-602 |
| 164 | m38 j05 subtraction on L8 w50 | S | VARIANTS.md:603 |
| 166-167 | m39 PCA width; m40 pool (was one row 'm39, m40 & PCA width') | W (fixed by patch) | VARIANTS.md:604, :661 |
| 169-170 | m47, m49 (added rows) | S | VARIANTS.md:799, :801; probe_mixture.py:1-12 |
| 174 | Round-2 tries pooled on SimLingo and TF++ | S | VARIANTS.md:950 |
| 182 | j methods came from Jerry's explore loop | S | VARIANTS.md:120, :150 |
| 184 | Only pass/fail read; axes_from or largest-first unless stated | S | j01-j15 docstrings |
| 195 | j01 | S | j01_unwhite.py:1-17 |
| 197 | j02 cPCA after 32-dim unwhitened PCA | S | j02_cpca.py:6-17 |
| 199 | j03 cuts 8, 12, 16, size band, cohesion | S | j03_bandpool.py:1-8 |
| 201 | j04 | S | j04_bgmoment.py:10-14 |
| 203 | j05 10 nearest passing routes | S | j05_knnresid.py:10-15 |
| 205 | j06 | S | j06_kinresid.py:1-8, :15-19 |
| 207 | j07 two strata then j01 | S | j07_stratify.py:1, :11-15 |
| 209 | j08 listed among scored methods | W (fixed by patch) | held, never scored: JOURNAL.md:831-832, :863; no j08 row in VARIANTS.md; views and layers: j08_stability.py:11-17 |
| 212-216 | j09 diagonal HMM, last 50 frames, L8, PCA 16, occupancy and transitions | S | j09_hmm.py:1-8; JOURNAL.md:827-830 |
| 215-216 | Smyth uses a mixture of HMMs; j09 fits one | S | results/h21/cite-verify/ledger.md:143; j09_hmm.py:7 |
| 217 | j10 Fisher score on emission means | S | j10_hmmfisher.py:1-8 |
| 219 | j11 unit-length residuals | S | j11_knndir.py:1-7 |
| 220 | j12 passing-only mixture residual | S | j12_gmmresid.py:1-9 |
| 221 | j13 tangent removal, 10 neighbours | S | j13_knntangent.py:1-15 |
| 223 | j14 neighbours matched in early space | S | j14_earlymatch.py:1-17 |
| 225 | j15 HDBSCAN on j05 residuals, ranked by stability | S | j15_hdbscan.py:1-5 |
| 229-230 | Scripts j01..j15; settings per run in VARIANTS.md | S | VARIANTS.md:120-350 (j08 has no run; its row now says so) |
| 236-237 | Twelve more j rows on H21b after the search stopped | S | VARIANTS.md:1141-1480 (2026-11-20, after A4 of 2026-11-18) |
| 237-238 | Rows written before score, each a try, all exploratory | S | VARIANTS.md:1141, :1181, :1302, :1353, :1387, :1427, :1495 |
| 238-240 | Pooled with whole-route L8 first; j16 also alone | S | VARIANTS.md:1164, :1200-1202, :1328-1329, :1376-1377, :1409-1410, :1479-1480 |
| 240-242 | Default input: last 50 frames L8 in j09's PCA 16; Ward as m03 | S | VARIANTS.md:1200, :1328 |
| 245-249 | j16 step statistics | S | VARIANTS.md:1200 |
| 250-252 | j17 adds net displacement, m06 weighting | S | VARIANTS.md:1202 |
| 253-257 | j18 mixture on m15 features, BIC, ranked by mean log density | S | VARIANTS.md:1164 |
| 258-259 | j19 ranks by failing share | S | VARIANTS.md:1165 |
| 260-265 | j20 1-D conv encoder, own PCA 64, sub-window contrast | S | VARIANTS.md:1409 |
| 266 | j21 higher temperature | S | VARIANTS.md:1410 (0.5 against 0.1) |
| 267-270 | j22 dictionary, own PCA 32, change and late activity | S | VARIANTS.md:1376 |
| 271 | j23 change columns only | S | VARIANTS.md:1377 |
| 272-275 | j24 shared VAR(2), error direction and size | S | VARIANTS.md:1328 |
| 276-278 | j25 unit-length mean error direction | S | VARIANTS.md:1329 |
| 283-284 | j26 input is m15's: L8 50-frame mean, PCA 32 | S | j26_attr.py:6-7; VARIANTS.md:1479 |
| 284-287 | Window position differs by outcome; m19's probes read it | S | j26_attr.py:8-9; VARIANTS.md:108, :1443-1445 |
| 287-290 | Two positions, per-outcome targets, constant target dropped | S | j26_attr.py:9-12; VARIANTS.md:1450-1452 |
| 291-294 | Ridge directions removed until R2 <= 0.05 or 16 gone | S | j26_attr.py:12-14, :45-46; VARIANTS.md:1452-1453 |
| 294-296 | MLP 64-64, 5-fold cross-fitting | S | j26_attr.py:15-16, :44, :47 |
| 297-299 | Gradient times input, divided by fold RMS | S | j26_attr.py:17-19 |
| 300-301 | Ward on unstandardised attributions; only pooled row scored | S | j26_attr.py:22-24; VARIANTS.md:1474 |
| 303-306 | j27 10 probes per fold, same training fold, means | S | VARIANTS.md:1480; j26_attr.py:19-21 |
| 310 | Unpooled experiment on SimLingo's test pool | S | f2d-unpooled/protocol.md:13-15 |
| 313 | Saved model input replayed offline | S | protocol.md:19 |
| 313-317 | Three sites read token by token from the replay | W (fixed) | dq comes from the closed-loop log (protocol.md:28); parenthesis added |
| 319-322 | Codebook reduction over the approach window | W (fixed) | codebook uses the last 8 saved frames (protocol.md:36); wording added |
| 319-321 | Max over tokens and frames; top-k farthest from early frames | S | protocol.md:32-35 |
| 323-324 | DINOv2-base on the same two tiles, same reductions | S | protocol.md:49-50 |
| 324-325 | Every row runs m03; outcomes already read | S | protocol.md:14, :39-40 |
| 330 | Each rival ranks its own axes and is scored like a method | S | prereg-fail2drive.md:144 |
| 333-334 | B1: same sizes, failing routes only, 50 draws | S | sprint_score.py:14, :78, :105; prereg-fail2drive.md:139 |
| 335-336 | B3-behaviour from fleet signals, b3_behaviour.py, tag f2d-sprint-a1 | S | b3_behaviour.py:6; prereg-fail2drive.md:128, :132 |
| 337 | Window last 6 captured frames, about 1.5 s | S | prereg-fail2drive.md:207; b3_behaviour.py:28, :38 (docstring :8 still says 3 s) |
| 337-341 | Feature list | S | b3_behaviour.py:8-11, :40-41 |
| 341-342 | Standardised, Ward, cut as m03 | S | b3_behaviour.py:15-17, :55, :62 |
| 342-345 | Exclusions; steering and braking not in shards | S | b3_behaviour.py:12-13; prereg-fail2drive.md:134-135 |
| 346-348 | B3-infraction axes incl. no-infraction axis, largest first | S | b3_infractions.py:6-8, :32 |
| 349 | What a fleet team does first | S | b3_infractions.py:6 |
| 349-350 | No pass bar, not in best rival (A2) | S | prereg-fail2drive.md:184; sprint_score.py:139 |
| 351-354 | B7-pool: Dr. VLA statistics, TopK SAE, PRD 12.2 | S | docs/steps/b7-gap-signal.md:58-62; PRD.md:1083-1087 |
| 355-356 | Gap-signal use is our construction | S | b7-gap-signal.md:18 |
| 356-358 | One dictionary, L10_k64_s0 | S | prereg-fail2drive.md:136-137 |
| 359-360 | B4 decides the split, reported as rival | S | prereg-fail2drive.md:42-46, :138 |
| 361-362 | B2 with labels is an oracle ceiling | S | prereg-fail2drive.md:140 |
| 364-365 | Full B3 retired at A1 (distances) | S | prereg-fail2drive.md:131; prd-discovery-sprint.md:60-61 |
| 370-371 | Scorer sprint_score.py; harness scoring.py | S | sprint_score.py:1-2, :28 |
| 379-380 | Own order, exact repeats dropped, first M = 10 | S | sprint_score.py:10, :31-40; prereg-fail2drive.md:144, :171-172 |
| 383-389 | Best Jaccard per gap; mean over gaps, equal weight | S | sprint_score.py:56-61; src/harness/scoring.py:21-26 |
| 390-391 | J(empty, empty) = 0 | S | scoring.py:21-25 |
| 392 | No axes scores 0 | S | sprint_score.py:57 |
| 396-398 | Recall: one Hungarian assignment, J >= 0.5, over gaps | S | sprint_score.py:64-68; scoring.py:17 |
| 399-400 | Decoy hit rate definition | S | sprint_score.py:71-74, :103 |
| 400-403 | Precision divides by M | S | scoring.py:150-151; PRD.md:931-934 |
| 407-411 | Rank-averaged best match primary in views prereg; definition | S | prereg-views.md:179; view_score.py:11-12, :40-48; protocol.md:67-71 |
| 414-415 | Pair routes share a road; seeds share both twins | S | adapters/simlingo/fail2drive_pairs.py:6; prereg-fail2drive.md:26 |
| 416-417 | Resampling unit is the pair, all seeds (A1) | S | prereg-fail2drive.md:150; sprint_score.py:106-107 |
| 419-420 | Pair id must not carry the seed | S | VARIANTS.md:1153-1155 |
| 422-423 | 2,000 replicates; weight = times drawn | S | sprint_score.py:94, :125-126 |
| 424-426 | Weighted Jaccard, 0 when the union weighs 0 | S | src/harness/bootstrap.py:31-35 |
| 427-429 | Point difference, 2.5/97.5 percentiles, p = share <= 0 | S | sprint_score.py:130-134 |
| 431-432 | Best rival or best view re-chosen per replicate | S | sprint_score.py:131; prereg-views.md:187 |
| 432-433 | Pooled results are a fixed mean over units | S | prereg-views.md:180; protocol.md:73 |
| 438-439 | transfer-spec.md binding from f2d-freeze-1 | S | transfer-spec.md:3; prereg-fail2drive.md:221 |
| 441-442 | Site driving_queries on every model | S | transfer-spec.md:29-30 |
| 444-447 | Layer rule; TF++ m23 layer 2, m40 layers 2 and 4 | S | transfer-spec.md:31-42 |
| 448-449 | Window unchanged, all capture every 5 steps | S | transfer-spec.md:20-22, :45-46 |
| 450 | Everything else unchanged, own pool | S | transfer-spec.md:48-50 |
| 452-453 | B7 k = round(64 x width / 896) = 18 at 256 | S | transfer-spec.md:58-59; prereg-fail2drive.md:223-225 |
| 454-456 | UniAD fallback for B3-behaviour (A3) | S | prereg-fail2drive.md:234-236 |

## fig-pipeline.tex

| tex line | claim | verdict | source or correct value |
|---|---|---|---|
| 2 | Cited line numbers are as of 40dddab | S | git diff 40dddab HEAD is empty for prereg-fail2drive.md, prereg-views.md, PRD.md, cache_pool.py, frames_pool.py, scoring.py, src/discovery, prd-discovery-sprint.md |
| 20 | Dev search on SimLingo's test pool and H21 | S | prereg-fail2drive.md:199 |
| 23-24 | Cache, one row per route, cache_pool.py | S | cache_pool.py:2, :68 |
| 24 | 'Label fields removed' | W (fixed, flag for Chris) | raw route id is written (cache_pool.py:68, :75), which prereg-fail2drive.md:70 lists as removed; now 'Scenario fields removed; raw route ids kept' |
| 24-25 | 'Routes renamed by a salted hash' | W (fixed by patch, flag for Chris) | code only sorts rows by salted hash (cache_pool.py:32-33, :51); prereg-fail2drive.md:71 says renamed |
| 31-32 | Each method and rival sees rows in salted order | W (fixed, flag for Chris) | B7-pool's directive comes from emit_directives.py:88 via dev_eval.load_shards, sorted by route id (dev_eval.py:113-117); now 'method and cache-based rival' |
| 32 | Ranks its own axes | S | prereg-fail2drive.md:144 |
| 35-36 | First M = 10 count, own order, repeats dropped (A1, A2) | S | prereg-fail2drive.md:75-76, :144, :171-172; sprint_score.py:34-40 |
| 39-40 | Per gap best Jaccard among those 10 | S | prereg-fail2drive.md:145; sprint_score.py:56-57 |
| 40-41 | Precision divides by M | S | PRD.md:931-934; src/harness/scoring.py:150-151 |
| 44-45 | Mean over gaps, each weighted equally | S | prereg-fail2drive.md:145; sprint_score.py:60-61 |
| 48-49 | Paired bootstrap, 2,000 replicates, pairs carry all seeds | S | prereg-fail2drive.md:150; sprint_score.py:94, :125-126 |
| 52-55 | Delta, 95% interval, one-sided p; primary B3-behaviour; best rival per replicate; B3-infraction, B7-pool, B1 beside | S | prereg-fail2drive.md:146, :149-152, :183; sprint_score.py:130-139 |
| 58-59 | Frozen: m23 primary, m40, rivals, transfer rules | S | prereg-fail2drive.md:200-201, :212-216 |
| 63-65 | Scorer only: the salt | W (fixed, flag for Chris) | SALT is a constant in cache_pool.py:28, reused by frames_pool.py:8; prereg-fail2drive.md:71 says it stays with the scorer; 'the salt' removed |
| 64-65 | Scorer only: scenario labels and gap failing routes | S | sprint_score.py:100-103 (only the scorer loads manifest and routes); cache_pool.py:13-14 |
| 70-73 | Freeze tag before any method reads TF++ or UniAD test data | S | prereg-fail2drive.md:199-201; git tag f2d-freeze-1 |
| 78-81 | No labels above, labels enter below | S | prereg-fail2drive.md:68-71; cache_pool.py:13-14 |
| 88 | Axes as sets of hashed routes | W (fixed by patch) | axes hold raw route ids (cache_methods.py:67-72; sprint_score.py:46); now 'route ids' |
| 93 | Method minus rival, per replicate | S | sprint_score.py:131 |
| 96 | Pipeline under A1-A3 for one model's pool | S | prereg-fail2drive.md:124-236 |
| 97 | White boxes see no scenario label | S | cache_pool.py:13-14 |
| 97-98 | Scorer alone holds the salt | W (fixed, flag for Chris) | as row 63-65; caption now 'alone holds the gap key' |
| 100-101 | Freeze tag between dev search and held-out pools | S | prereg-fail2drive.md:199-201 |
| 101-102 | Views prereg keeps pipeline, rank-averaged best match primary | S | prereg-views.md:89-90, :179 |
| 102-104 | B2 with labels is an oracle ceiling only | S | prereg-fail2drive.md:140; prd-discovery-sprint.md:58 |

## Flag for Chris (code and pre-registration disagree; text now describes the code)

1. Route ids. `prereg-fail2drive.md:70-71`: the route id is removed and routes are renamed by a salted hash.
   `cache_pool.py:51, :68, :75`: rows are sorted by the salted hash, and the raw route id is written.
   Flags at `methods.tex:62` and `fig-pipeline.tex:27`.
2. The salt. `prereg-fail2drive.md:71`: the salt stays with the scorer. `cache_pool.py:28`: `SALT = "f2d-cache-v1"`
   is a constant in method-side code, also used by `frames_pool.py`. Flags at `fig-pipeline.tex:62` and `:99`.
3. B7-pool's row order. `prd-discovery-sprint.md:94-95`: any method that orders by route uses the salted names.
   B7-pool's directive is built by `src/discovery/emit_directives.py:88` through `dev_eval.load_shards`, which sorts
   shards by route id (`dev_eval.py:113-117`). Flag at `fig-pipeline.tex:30`.

## Unsupported (comment "% unsupported: ..." placed above each)

1. `methods.tex:20-21` "Chris approved each batch before it ran": logged for m batches 1-5 and round 2 only.
2. `methods.tex:38-39` "Jerry's explore loop wrote the j family": no source names whose side ran j16-j27.
3. `methods.tex:119-121` m23's stated idea (last seconds against failures over the route): the source frames it as a
   pedestrian view pooled with a FullyBlocked view.

## Other notes

- `b3_behaviour.py:8` still says the window is "about 3 s"; A3 (`prereg-fail2drive.md:207`) corrected it to 1.5 s.
  The paper says 1.5 s, which matches A3. The code docstring was not touched.
- Citation keys in methods.tex all resolve in refs.bib and are covered by `results/h21/cite-verify/ledger.md`.
- Every `\ref` in both files has exactly one `\label` in docs/paper/*.tex.
- The paper was not compiled; see the reply.
