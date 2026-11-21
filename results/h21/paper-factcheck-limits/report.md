Supported 192 / wrong 8 (all fixed) / unsupported 1; recount total 232, 127 of 127 appendix rows agree.

Fact check of `docs/paper/limitations.tex` and `docs/paper/appendix-tries.tex` (work item 5), laptop worker 20261121-041958-6290. Starting point: commit f43ffc0 plus the partial patch `tasks/fc-partial/limits-appendix.diff`, applied and re-verified (commit 482b8db). `VARIANTS.md` means `docs/research/experiments/f2d-dev-simlingo/VARIANTS.md`; bare script names are in that folder. Line numbers are of the files as committed in a833cc0.

No result number appears in the prose of either file (grep for decimals, "significant", "confirm", "finding" in non-comment lines: only the 0.05 tolerance, a setting). Comment lines hold one diagnostic number (limitations.tex:78, R^2 0.588), which is not typeset.

## Wrong items

| where | claimed | source says | status |
|---|---|---|---|
| appendix-tries.tex:346 | j09 refit over mixture seeds | VARIANTS.md:328 says KMeans seeds 1 to 10 | fixed (partial patch; re-verified) |
| limitations.tex:100-102 (old prose) | Exported shards drop scenario, type, role, pair, seed and route id and rename routes by a salted hash | export_activations.py:146-161 writes route_id, base_id, scenario, practice_gaps, role, neighbourhood_of, source; caches order by hash, keep raw ids | fixed (partial patch rewrote it; re-verified against code; flag added) |
| limitations.tex:47 comment | prd-discovery-sprint.md:89-91 | the cited rule runs :89-93 | fixed (patch) |
| limitations.tex:57 comment | data.tex:95-96 for H21b seeds | data.tex:96-97 | fixed (patch) |
| appendix-tries.tex:367 comment | JOURNAL.md:808 for j08 held | JOURNAL.md:831 (held), :843 (built), :863 (no score); the patch's :820, :852 were also wrong | fixed |
| appendix-tries.tex:263-268, :313 comments (patch) | prereg-views.md:71-74 | the rows are at :72-75 (:71 is blank); the original was right | patch edit reverted |
| limitations.tex:101 comment (patch) | export_activations.py:144-160 | sidecar() is :146-161 | fixed |
| limitations.tex:102 comment (patch) | frames_pool.py:8-9 | :8-10 | fixed |

The other partial-patch edits were checked and kept: `KMeans seeds` (above), the label-hiding rewrite (above), prd :89-93, data.tex :96-97, prd :83, CONFLICTS.md :847, and the j16-j27 batch line list.

## limitations.tex

| tex line | claim | verdict | source |
|---|---|---|---|
| limitations.tex:4-5 | No limit depends on a held-out outcome | supported | by inspection: every source cited in the file is dev, design or code; no held-out score is cited |
| limitations.tex:10 | Every route driven in CARLA, on Fail2Drive's routes | supported | upstream-99p/docs/CITATION_AUDIT.md:235 (CARLA 0.9.15); docs/prereg-fail2drive.md:27 (pool is Fail2Drive's own pairs) |
| limitations.tex:10-11 | Gaps are scenario types the benchmark's authors built | supported | docs/prereg-fail2drive.md:13; CITATION_AUDIT.md:235 |
| limitations.tex:11-14 | Recovery of known groups stands in for unknown ones | supported | docs/prd-discovery-sprint.md:30-31 |
| limitations.tex:20 | Methods were developed on SimLingo | supported | docs/prd-discovery-sprint.md:39 |
| limitations.tex:20-21 | TF++ held out in round 1, second dev pool in round 2 | supported | docs/prereg-fail2drive.md:238-241; docs/paper/data.tex:66 |
| limitations.tex:21-22 | UniAD is the only pool no method was tuned on | supported | docs/prd-discovery-sprint.md:45-47; data.tex:67; docs/prereg-views.md:59. Note: UniAD's seeds 24-26 screen is a dev pool (prereg-views.md:61); the sentence holds for the test pool |
| limitations.tex:22-23 | TF++ gap types are a subset of SimLingo's, so it tests models not types | supported | docs/prd-discovery-sprint.md:39-40, :45-46 |
| limitations.tex:23-25 | Transfer claim rests on few models, one unseen | supported | follows from lines 20-22 |
| limitations.tex:33 | Fail2Drive has 100 pairs over 17 types | supported | CITATION_AUDIT.md:235; prereg-fail2drive.md:13; measured: manifest has 100 pairs over 17 `practice_gaps` types |
| limitations.tex:33-35 | In the H21b manifest 14 types have 5 pairs, 3 have 10; 15 or 30 slice routes over three seeds | supported | measured, results/h21/h21b/manifest.json (pair with -sNN stripped): 14 x 5, 3 x 10; 15 or 30 slice rows. Note: of the 593 driven routes, 5 types have 1 or 2 fewer slice routes (13, 14 or 29) |
| limitations.tex:35-36 | Six-seed 5-pair type has 30 slice runs, the gap floor | supported | prereg-fail2drive.md:25 (six seeds), :31 (30 slice runs) |
| limitations.tex:36-38 | At most 30 or 60 failing routes per gap on six seeds | supported | arithmetic from 33-36 |
| limitations.tex:41-42 | Axes larger than the gap cap Jaccard below 1 | supported | arithmetic (Jaccard <= gap size / axis size) |
| limitations.tex:42 | Happened once already, to the frozen M1 | supported | docs/WHAT_BROKE.md:160-162 |
| limitations.tex:42-44 | Primary score is a mean over a pool's few gaps | supported | docs/prd-discovery-sprint.md:83 |
| limitations.tex:49 | A dev p value after many tries marks a candidate | supported | docs/prd-discovery-sprint.md:89-90; prereg-fail2drive.md:153 |
| limitations.tex:51 | Try count stands at 232 methods | supported | VARIANTS.md:1495; independent recount below = 232 |
| limitations.tex:51-52 | Every dev table states the running count beside its p values | unsupported | prereg-fail2drive.md:153 states it as a rule; VARIANTS.md score tables at :613, :669, :844, :975, :1015 have no count column (count is in the paragraph above). Marked `% unsupported:` |
| limitations.tex:52-53 | Only the held-out score of a frozen finalist is a result | supported | docs/prd-discovery-sprint.md:91-93 |
| limitations.tex:58-59 | H21 read by H22-H25; can rank and kill, not make a candidate | supported | VARIANTS.md:125, :360 |
| limitations.tex:59-60 | H21b drives the same routes on two more seeds | supported | VARIANTS.md:1031-1033; data.tex:96-97 |
| limitations.tex:60-62 | j16-j27 ran after the search stopped; exploratory; cannot enter the UniAD read | supported | CONFLICTS.md:847 (stop, 2026-11-18); VARIANTS.md:1144, :1196, :1305, :1356, :1391, :1430 (all dated 2026-11-20) |
| limitations.tex:69-70 | Window ends at failure (failing) or route end (passing) | supported | VARIANTS.md:108; cache_pool.py:7-8 |
| limitations.tex:70-72 | m19's probes read window position | supported | VARIANTS.md:108; docs/paper/whatbroke.tex:38-45 |
| limitations.tex:72-74 | Failing windows sit at different points; clusters can follow failure time | supported | VARIANTS.md:1458-1459 (diagnostic; no number in prose) |
| limitations.tex:74-75 | m23 and m40 do not remove position | supported | VARIANTS.md:589, :661; prereg-fail2drive.md:213-216 (no position step in either) |
| limitations.tex:79-81 | j26 removes ridge directions until no cross-fitted R^2 above 0.05 | supported | j26_attr.py:13-14, :45 (TOLERANCE 0.05), :97-108; VARIANTS.md:1451-1452 |
| limitations.tex:81-83 | A boosted tree still predicts position after removal; how much the probe uses is unmeasured | supported | VARIANTS.md:1455-1457 |
| limitations.tex:88 | Pair bootstrap reads the manifest pair field | supported | sprint_score.py:106-108, :125-126 |
| limitations.tex:89-91 | Pool builder copied base_id into pair; it carries the seed; units were pair-seed, against A1 | supported | WHAT_BROKE.md:21-24; VARIANTS.md:1065-1067; prereg-fail2drive.md:150 |
| limitations.tex:92-93 | Intervals too narrow, p too small, point scores unaffected | supported | WHAT_BROKE.md:24; VARIANTS.md:1065, :1069 |
| limitations.tex:93-94 | Caught by an independent scorer written from the prereg text | supported | WHAT_BROKE.md:24; VARIANTS.md:1067-1068 |
| limitations.tex:94-95 | Later H21b scores use a stripped manifest; UniAD manifest has no suffix | supported | WHAT_BROKE.md:27-28; VARIANTS.md:1073-1074 |
| limitations.tex:95-97 | Nothing in the scorer refuses a seed-carrying pair | supported | sprint_score.py:106-108 (pair used as written, no check) |
| limitations.tex:106-109 | Caches write no scenario/town/route-config field, salted order, raw ids kept; shards carry type and role | supported (flag for Chris) | cache_pool.py:13-14, :28-33, :51, :68, :75; frames_pool.py:8-10, :134, :186; export_activations.py:146-161. Disagrees with prereg-fail2drive.md:68-71; `% flag for Chris` added |
| limitations.tex:109-113 | Guard fails on sealed imports or sealed folder, key file, salt names under discovery/, baselines/, gate/ (top level and src/) | supported | scripts/check_sealed_imports.py:25-36. Note: it skips docstrings (:41-57, :86-87) and lines marked `# sealed-ok` (:38, :65-67) |
| limitations.tex:113-114 | Dev method scripts are outside the guard's scope | supported | check_sealed_imports.py:25-28; scripts live in docs/research/experiments/ |
| limitations.tex:114-116 | CI is off, guard runs only by hand | supported | CONFLICTS.md:693-699; .github/workflows/ci.yml:3 (`on: workflow_dispatch`) |
| limitations.tex:120 | Dev manifests give each route's Fail2Drive type | supported | measured: every slice row of results/h21/h21b/manifest.json has `practice_gaps` (and `scenario`) |
| limitations.tex:120-121 | Manifests sit on the same disk as scripts and pools | supported | inspection: results/h21/h21b/manifest.json and results/savio/f2d-h21b/pool/ in this clone |
| limitations.tex:121-123 | Never opening them is a VARIANTS.md rule (e.g. j26), unchecked by the guard | supported | VARIANTS.md:1467-1468; guard scope as above |
| limitations.tex:123-126 | H25 review caught category-sorted ids and a nearby answer mapping, before the lock | supported | WHAT_BROKE.md:150-152 |

## appendix-tries.tex

Each table row's description was read against the cited VARIANTS.md row and its spec; each position against the recount below.

| tex line | claim | verdict | source |
|---|---|---|---|
| appendix-tries.tex:6-12 | Every counted row of the 232, in counted order, one position per configuration; dagger marks count/row mismatches; nottried table lists uncounted rows | supported | VARIANTS.md:1495; recount below |
| appendix-tries.tex:15-19 | Pools: SL 1,185 cached routes, H21 200, H21b 593, SL+TF++ round-2 dev, UniAD blind | supported | VARIANTS.md:70, :122, :1033, :952; prereg-views.md:59 |
| appendix-tries.tex:42 | v1 rescored (pre-sprint, SL), position 1--3: description | supported | VARIANTS.md:61 |
| appendix-tries.tex:44 | m03 (batch 1, SL), position 4--6 dagger: description | supported | VARIANTS.md:62 (spec :53) |
| appendix-tries.tex:46 | m04 (batch 1, SL), position 4--6 dagger: description | supported | VARIANTS.md:63 (spec :54) |
| appendix-tries.tex:48 | m07 (batch 1, SL), position 4--6 dagger: description | supported | VARIANTS.md:64 (spec :57) |
| appendix-tries.tex:50 | m06 (batch 1, SL), position 4--6 dagger: description | supported | VARIANTS.md:65 (spec :56) |
| appendix-tries.tex:52 | m05 (batch 1, SL), position 7--55: description | supported | VARIANTS.md:72 |
| appendix-tries.tex:54 | m01 (batch 1, SL), position 56--57: description | supported | VARIANTS.md:73 |
| appendix-tries.tex:56 | m02 (batch 1, SL), position 58--59: description | supported | VARIANTS.md:74 |
| appendix-tries.tex:58 | m08 (batch 2, SL), position 60--61: description | supported | VARIANTS.md:83 |
| appendix-tries.tex:60 | m09 (batch 2, SL), position 62: description | supported | VARIANTS.md:84 |
| appendix-tries.tex:62 | m10 (batch 2, SL), position 63: description | supported | VARIANTS.md:85 |
| appendix-tries.tex:64 | m12 (batch 2, SL), position 64--69: description | supported | VARIANTS.md:86 |
| appendix-tries.tex:66 | m13 (batch 2, SL), position 70--71: description | supported | VARIANTS.md:87 |
| appendix-tries.tex:68 | m11 (batch 2, SL), position 72--77: description | supported | VARIANTS.md:88 |
| appendix-tries.tex:70 | m14 (batch 2, SL), position 78--79: description | supported | VARIANTS.md:89 |
| appendix-tries.tex:72 | m21 (batch 3, SL), position 80: description | supported | VARIANTS.md:103 |
| appendix-tries.tex:74 | m15 (batch 3, SL), position 81--86: description | supported | VARIANTS.md:104 |
| appendix-tries.tex:76 | m16 (batch 3, SL), position 87--90: description | supported | VARIANTS.md:105 |
| appendix-tries.tex:78 | m17 (batch 3, SL), position 91--94: description | supported | VARIANTS.md:106 |
| appendix-tries.tex:80 | m18 (batch 3, SL), position 95--101: description | supported | VARIANTS.md:107 |
| appendix-tries.tex:82 | m19 (batch 3, SL), position 102--103: description | supported | VARIANTS.md:108 |
| appendix-tries.tex:84 | m20 (batch 3, SL), position 104 dagger: description | supported | VARIANTS.md:109 |
| appendix-tries.tex:86 | j01 (explore loop, H21), position 105 dagger: description | supported | VARIANTS.md:131 (position reconciled at :168) |
| appendix-tries.tex:88 | j02 (explore loop, H21), position 106 dagger: description | supported | VARIANTS.md:132 (position reconciled at :168) |
| appendix-tries.tex:90 | j03 (explore loop, H21), position 107 dagger: description | supported | VARIANTS.md:133 (position reconciled at :168) |
| appendix-tries.tex:92 | j04 (explore loop, H21), position 108 dagger: description | supported | VARIANTS.md:134 (position reconciled at :168) |
| appendix-tries.tex:94 | j05 (explore loop, H21), position 109 dagger: description | supported | VARIANTS.md:142 (position reconciled at :168) |
| appendix-tries.tex:96 | j06 (explore loop, H21), position 110 dagger: description | supported | VARIANTS.md:143 (position reconciled at :168) |
| appendix-tries.tex:98 | j07 (explore loop, H21), position 111 dagger: description | supported | VARIANTS.md:144 (position reconciled at :168) |
| appendix-tries.tex:100 | j04 (explore loop, SL), position 112: description | supported | VARIANTS.md:161 |
| appendix-tries.tex:102 | j02 (explore loop, SL), position 113: description | supported | VARIANTS.md:162 |
| appendix-tries.tex:104 | j03 (explore loop, SL), position 114: description | supported | VARIANTS.md:163 |
| appendix-tries.tex:106 | j05 (explore loop, SL), position 115: description | supported | VARIANTS.md:164 |
| appendix-tries.tex:108 | j06 (explore loop, SL), position 116: description | supported | VARIANTS.md:165 |
| appendix-tries.tex:110 | j07 (explore loop, SL), position 117: description | supported | VARIANTS.md:166 |
| appendix-tries.tex:112 | j11 (explore loop, SL), position 118: description | supported | VARIANTS.md:183 |
| appendix-tries.tex:114 | j11 (explore loop, H21), position 119: description | supported | VARIANTS.md:184 |
| appendix-tries.tex:116 | j12 (explore loop, SL), position 120: description | supported | VARIANTS.md:202 |
| appendix-tries.tex:118 | j12 (explore loop, H21), position 121: description | supported | VARIANTS.md:203 |
| appendix-tries.tex:120 | j13 (explore loop, SL), position 122: description | supported | VARIANTS.md:224 |
| appendix-tries.tex:122 | j13 (explore loop, H21), position 123: description | supported | VARIANTS.md:225 |
| appendix-tries.tex:124 | j14 (explore loop, SL), position 124: description | supported | VARIANTS.md:249 |
| appendix-tries.tex:126 | j15 (explore loop, SL), position 125: description | supported | VARIANTS.md:281 |
| appendix-tries.tex:128 | j15 (explore loop, H21), position 126: description | supported | VARIANTS.md:282 |
| appendix-tries.tex:130 | j09 (explore loop, H21), position 127: description | supported | VARIANTS.md:319 |
| appendix-tries.tex:132 | j10 (explore loop, H21), position 128: description | supported | VARIANTS.md:320 |
| appendix-tries.tex:134 | m08 (H21 replication, H21), position 129: description | supported | VARIANTS.md:365 |
| appendix-tries.tex:136 | m15 (H21 replication, H21), position 130: description | supported | VARIANTS.md:366 |
| appendix-tries.tex:138 | m11 (H21 replication, H21), position 131: description | supported | VARIANTS.md:367 |
| appendix-tries.tex:140 | m12 (H21 replication, H21), position 132: description | supported | VARIANTS.md:368 |
| appendix-tries.tex:142 | m16 (H21 replication, H21), position 133: description | supported | VARIANTS.md:369 |
| appendix-tries.tex:144 | j05 (H21 replication, H21), position 134: description | supported | VARIANTS.md:370 |
| appendix-tries.tex:146 | j09 (batch 4, SL), position 135: description | supported | VARIANTS.md:587 |
| appendix-tries.tex:148 | m22 (batch 4, SL), position 136: description | supported | VARIANTS.md:588 |
| appendix-tries.tex:150 | m23 (batch 4, SL), position 137: description | supported | VARIANTS.md:589 |
| appendix-tries.tex:152 | m24 (batch 4, SL), position 138--139: description | supported | VARIANTS.md:590 |
| appendix-tries.tex:154 | m25 (batch 4, SL), position 140--144: description | supported | VARIANTS.md:591 |
| appendix-tries.tex:156 | m26 (batch 4, SL), position 145--146: description | supported | VARIANTS.md:592 |
| appendix-tries.tex:158 | m27 (batch 4, SL), position 147: description | supported | VARIANTS.md:593 |
| appendix-tries.tex:160 | m28 (batch 4, SL), position 148: description | supported | VARIANTS.md:594 |
| appendix-tries.tex:162 | m29 (batch 4, SL), position 149: description | supported | VARIANTS.md:595 |
| appendix-tries.tex:164 | m30 (batch 4, SL), position 150: description | supported | VARIANTS.md:596 |
| appendix-tries.tex:166 | m31 (batch 4, SL), position 151: description | supported | VARIANTS.md:597 |
| appendix-tries.tex:168 | m32 (batch 4, SL), position 152: description | supported | VARIANTS.md:598 |
| appendix-tries.tex:170 | m33 (batch 4, SL), position 153: description | supported | VARIANTS.md:599 |
| appendix-tries.tex:172 | m34 (batch 4, SL), position 154: description | supported | VARIANTS.md:600 |
| appendix-tries.tex:174 | m35 (batch 4, SL), position 155: description | supported | VARIANTS.md:601 |
| appendix-tries.tex:176 | m36 (batch 4, SL), position 156: description | supported | VARIANTS.md:602 |
| appendix-tries.tex:178 | m38 (batch 4, SL), position 157: description | supported | VARIANTS.md:603 |
| appendix-tries.tex:180 | m39 (batch 4, SL), position 158--159: description | supported | VARIANTS.md:604 |
| appendix-tries.tex:182 | m40 (batch 4 pools, SL), position 160: description | supported | VARIANTS.md:661 |
| appendix-tries.tex:184 | m41 (batch 4 pools, SL), position 161: description | supported | VARIANTS.md:662 |
| appendix-tries.tex:186 | m42 (batch 4 pools, SL), position 162: description | supported | VARIANTS.md:663 |
| appendix-tries.tex:188 | m43 (batch 4 pools, SL), position 163: description | supported | VARIANTS.md:664 |
| appendix-tries.tex:190 | m44 (batch 4 pools, SL), position 164: description | supported | VARIANTS.md:665 |
| appendix-tries.tex:192 | m41 (H21 replication of batch 4, H21), position 165: description | supported | VARIANTS.md:703 |
| appendix-tries.tex:194 | m40 (H21 replication of batch 4, H21), position 166: description | supported | VARIANTS.md:704 |
| appendix-tries.tex:196 | m44 (H21 replication of batch 4, H21), position 167: description | supported | VARIANTS.md:705 |
| appendix-tries.tex:198 | m23 (H21 replication of batch 4, H21), position 168: description | supported | VARIANTS.md:706 |
| appendix-tries.tex:200 | m39 (H21 replication of batch 4, H21), position 169: description | supported | VARIANTS.md:707 |
| appendix-tries.tex:202 | m45 (batch 5, SL), position 170: description | supported | VARIANTS.md:797 |
| appendix-tries.tex:204 | m46 (batch 5, SL), position 171: description | supported | VARIANTS.md:798 |
| appendix-tries.tex:206 | m47 (batch 5, SL), position 172: description | supported | VARIANTS.md:799 |
| appendix-tries.tex:208 | m48 (batch 5, SL), position 173: description | supported | VARIANTS.md:800 |
| appendix-tries.tex:210 | m49 (batch 5, SL), position 174: description | supported | VARIANTS.md:801 |
| appendix-tries.tex:212 | m41 (robustness neighbours, SL), position 175--176: description | supported | VARIANTS.md:824 (range 175-182 at :822) |
| appendix-tries.tex:214 | m41 (robustness neighbours, SL), position 177--178: description | supported | VARIANTS.md:825 (range 175-182 at :822) |
| appendix-tries.tex:216 | m40 (robustness neighbours, SL), position 179--180: description | supported | VARIANTS.md:826 (range 175-182 at :822) |
| appendix-tries.tex:218 | m23 (robustness neighbours, SL), position 181--182: description | supported | VARIANTS.md:827 (range 175-182 at :822) |
| appendix-tries.tex:220 | m49 (m49 follow-ups, SL), position 183--186: description | supported | VARIANTS.md:883 |
| appendix-tries.tex:222 | m50 (m49 follow-ups, SL), position 187: description | supported | VARIANTS.md:890 |
| appendix-tries.tex:224 | m51 (m49 follow-ups, SL), position 188: description | supported | VARIANTS.md:891 |
| appendix-tries.tex:226 | m23 (held-out round 1, TF++), position 189 dagger: description | supported | VARIANTS.md:923, :927 (position implied by :959) |
| appendix-tries.tex:228 | m40 (held-out round 1, TF++), position 190 dagger: description | supported | VARIANTS.md:923, :928 (position implied by :959) |
| appendix-tries.tex:230 | r01 (round 2, batch 1, SL+TF++), position 191: description | supported | VARIANTS.md:959 |
| appendix-tries.tex:232 | r02 (round 2, batch 1, SL+TF++), position 192: description | supported | VARIANTS.md:960 |
| appendix-tries.tex:234 | r03 (round 2, batch 1, SL+TF++), position 193: description | supported | VARIANTS.md:961 |
| appendix-tries.tex:236 | r04 (round 2, batch 1, SL+TF++), position 194: description | supported | VARIANTS.md:962 |
| appendix-tries.tex:238 | r05 (round 2, batch 1, SL+TF++), position 195: description | supported | VARIANTS.md:963 |
| appendix-tries.tex:240 | r06 (round 2, batch 1, SL+TF++), position 196: description | supported | VARIANTS.md:964 |
| appendix-tries.tex:242 | r07 (round 2, batch 1, SL+TF++), position 197: description | supported | VARIANTS.md:965 |
| appendix-tries.tex:244 | r08 (round 2, batch 2, SL+TF++), position 198: description | supported | VARIANTS.md:1007 |
| appendix-tries.tex:246 | r09 (round 2, batch 2, SL+TF++), position 199: description | supported | VARIANTS.md:1008 |
| appendix-tries.tex:248 | r10 (round 2, batch 2, SL+TF++), position 200: description | supported | VARIANTS.md:1009 |
| appendix-tries.tex:250 | r11 (round 2, batch 2, SL+TF++), position 201: description | supported | VARIANTS.md:1010 |
| appendix-tries.tex:252 | r12 (round 2, batch 2, SL+TF++), position 202: description | supported | VARIANTS.md:1011 |
| appendix-tries.tex:254 | u01--u03 (unpooled, SL), position 203--205: description | supported | VARIANTS.md:1085 |
| appendix-tries.tex:256 | u04--u06 (unpooled, SL), position 206--208: description | supported | VARIANTS.md:1086 |
| appendix-tries.tex:258 | u07--u09 (unpooled, SL), position 209--211: description | supported | VARIANTS.md:1087 |
| appendix-tries.tex:260 | u10, u11 (unpooled, SL), position 212--213: description | supported | VARIANTS.md:1088 |
| appendix-tries.tex:262 | u12--u14 (unpooled, SL), position 214--216: description | supported | VARIANTS.md:1089 |
| appendix-tries.tex:264 | img-mean (views prereg, SL, TF++, UniAD), position 217 dagger: description | supported | VARIANTS.md:1062 (rows defined in docs/prereg-views.md:72-75) |
| appendix-tries.tex:266 | query-mean (views prereg, SL, TF++, UniAD), position 218 dagger: description | supported | VARIANTS.md:1062 (rows defined in docs/prereg-views.md:72-75) |
| appendix-tries.tex:268 | caption (views prereg, SL, TF++, UniAD), position 219 dagger: description | supported | VARIANTS.md:1062 (rows defined in docs/prereg-views.md:72-75) |
| appendix-tries.tex:270 | j16 (laptop, temporal, H21b), position 220: description | supported | VARIANTS.md:1200 |
| appendix-tries.tex:272 | j16+route (laptop, temporal, H21b), position 221: description | supported | VARIANTS.md:1201 |
| appendix-tries.tex:274 | j17+route (laptop, temporal, H21b), position 222: description | supported | VARIANTS.md:1202 |
| appendix-tries.tex:276 | j18 (laptop, mixture, H21b), position 223 dagger: description | supported | VARIANTS.md:1164 (position assigned from :1298-1299) |
| appendix-tries.tex:278 | j19 (laptop, mixture, H21b), position 224 dagger: description | supported | VARIANTS.md:1165 (position assigned from :1298-1299) |
| appendix-tries.tex:280 | j24 (laptop, temporal, H21b), position 225: description | supported | VARIANTS.md:1328 (position at :1384) |
| appendix-tries.tex:282 | j25 (laptop, temporal, H21b), position 226: description | supported | VARIANTS.md:1329 (position at :1384) |
| appendix-tries.tex:284 | j22 (laptop, dictionary, H21b), position 227: description | supported | VARIANTS.md:1376 (position at :1384) |
| appendix-tries.tex:286 | j23 (laptop, dictionary, H21b), position 228: description | supported | VARIANTS.md:1377 (position at :1384) |
| appendix-tries.tex:288 | j20 (laptop, contrastive, H21b), position 229: description | supported | VARIANTS.md:1409 (position at :1415) |
| appendix-tries.tex:290 | j21 (laptop, contrastive, H21b), position 230: description | supported | VARIANTS.md:1410 (position at :1415) |
| appendix-tries.tex:292 | j26 (laptop, probe, H21b), position 231: description | supported | VARIANTS.md:1479 (position at :1495) |
| appendix-tries.tex:294 | j27 (laptop, probe, H21b), position 232: description | supported | VARIANTS.md:1480 (position at :1495) |
| appendix-tries.tex:302 | Positions 4-6 shared by four batch-1 rows | supported | VARIANTS.md:61-65, :76 (59 configurations) |
| appendix-tries.tex:306 | Position 104: m20 scored two pools, count +1 | supported | VARIANTS.md:109, :465, :470 |
| appendix-tries.tex:308 | Positions 105-111 recorded 75-78 from an older base; later placed after batch 3 | supported | VARIANTS.md:131-144, :168; docs/JOURNAL.md:840 (78 = 71 Chris + 7 j) |
| appendix-tries.tex:311 | Positions 189-190: '2 tried', implied by r01's 191 | supported | VARIANTS.md:923, :959 |
| appendix-tries.tex:314 | Positions 217-219 counted, no rows in the log | supported | VARIANTS.md:1062; prereg-views.md:72-75 |
| appendix-tries.tex:317 | Positions 223-224: both batches counted from 219; total without order | supported | VARIANTS.md:1156, :1200-1202, :1298-1299 |
| appendix-tries.tex:338 | Not counted: v1, v2 (old rule, before the count) | supported | VARIANTS.md:15-16, :20-22 |
| appendix-tries.tex:340 | Not counted: Rival rows (rivals) | supported | VARIANTS.md:67, :136, :1053-1054 |
| appendix-tries.tex:342 | Not counted: Failure-timing check; m16 rerun (diagnostic; rescore) | supported | VARIANTS.md:114-117 |
| appendix-tries.tex:344 | Not counted: A2 rescores (rescore) | supported | VARIANTS.md:383-392, :424-435 |
| appendix-tries.tex:346 | Not counted: Stability checks (no try) | wrong, fixed | VARIANTS.md:209-210, :258-264, :327-332 (:328: j09 refit with KMeans seeds 1 to 10) |
| appendix-tries.tex:348 | Not counted: Planned residual filter (first j16) (not run) | supported | VARIANTS.md:292-301 |
| appendix-tries.tex:350 | Not counted: j09 diagnostics (diagnostic) | supported | VARIANTS.md:310-312, :336-348 |
| appendix-tries.tex:352 | Not counted: Batch-4 stability (no try) | supported | VARIANTS.md:726-789 |
| appendix-tries.tex:354 | Not counted: Lead robustness (resampling) | supported | VARIANTS.md:812-820, :859, :881-882 |
| appendix-tries.tex:356 | Not counted: Fixed rival (rescore) | supported | VARIANTS.md:942 |
| appendix-tries.tex:358 | Not counted: Round-2 references (reference) | supported | VARIANTS.md:954, :1003 |
| appendix-tries.tex:360 | Not counted: \code{dq-mean}; probe ceiling (re-run; diagnostic) | supported | VARIANTS.md:1091, :1121 |
| appendix-tries.tex:362 | Not counted: H21b rescores (rescore) | supported | VARIANTS.md:1029-1054, :1221-1284 |
| appendix-tries.tex:364 | Not counted: Seed reruns (robustness) | supported | VARIANTS.md:1158, :1321, :1367, :1402, :1473 |
| appendix-tries.tex:366 | Not counted: Attribution; position check (diagnostic) | supported | VARIANTS.md:1418-1425, :1453-1459 |
| appendix-tries.tex:368 | Not counted: m37; j08 (no run) | supported | VARIANTS.md:606; docs/JOURNAL.md:831, :843, :863 |

## Recount from VARIANTS.md alone

Method: walk the file top to bottom; every table row in a section that the file says counts, one position per configuration the row scored; positions taken from the row's own "methods tried" cell where it gives one, otherwise from the prose line named. Not counted (the file says so): v1/v2 old-rule rows (:15-16), rival rows, A2 and H21b rescores (:387, :435, :1043, :1223), no-try checks (:258, :292, :327, :340, :726, :747, :760), resampling and seed reruns (:820, :881, :1158, :1321, :1367, :1402, :1473), the fixed rival (:942), round-2 reference rows (:954, :1003), `dq-mean` (:1091), the probe ceiling (:1121), the attribution diagnostic (:1420), j16-as-filter (:298), m37 (:606).

Disagreements with the appendix: none. Every appendix row cites the same VARIANTS.md row and gives the same position. The log's own inconsistencies, all already daggered in the appendix: four rows share 4-6 (:62-65); m20 has two configurations but one position (:109); j01-j07 record 75-78 (:131-144, reconciled at :168); 189-190 have no running count (:923); 217-219 have no rows (:1062); j18-j19 record "219 + n" (:1164-1165, total only at :1298-1299). Positions inside 175-182 follow the bullet order at :824-827; the log gives only the range (:822), so that order is inferred, and the appendix does not dagger it.

| # | VARIANTS.md line | id | my position | recorded in log | position source | appendix | agrees |
|---|---|---|---|---|---|---|---|
| 1 | 61 | v1 rescored | 1-3 | 3 | row | :61 1-3 | yes |
| 2 | 62 | m03 | 4-6 | 6 | row; 4 rows share 4-6 | :62 4-6 (dagger) | yes |
| 3 | 63 | m04 | 4-6 | 6 | row; shared | :63 4-6 (dagger) | yes |
| 4 | 64 | m07 | 4-6 | 6 | row; shared | :64 4-6 (dagger) | yes |
| 5 | 65 | m06 | 4-6 | 6 | row; shared, uncounted in log | :65 4-6 (dagger) | yes |
| 6 | 72 | m05 | 7-55 | 55 | row | :72 7-55 | yes |
| 7 | 73 | m01 | 56-57 | 59 | row | :73 56-57 | yes |
| 8 | 74 | m02 | 58-59 | 59 | row | :74 58-59 | yes |
| 9 | 83 | m08 | 60-61 | 71 | row | :83 60-61 | yes |
| 10 | 84 | m09 | 62 | 71 | row | :84 62 | yes |
| 11 | 85 | m10 | 63 | 71 | row | :85 63 | yes |
| 12 | 86 | m12 | 64-69 | 71 | row | :86 64-69 | yes |
| 13 | 87 | m13 | 70-71 | 71 | row | :87 70-71 | yes |
| 14 | 88 | m11 | 72-77 | 77 | row | :88 72-77 | yes |
| 15 | 89 | m14 | 78-79 | 79 | row | :89 78-79 | yes |
| 16 | 103 | m21 | 80 | 80 | row | :103 80 | yes |
| 17 | 104 | m15 | 81-86 | 86 | row | :104 81-86 | yes |
| 18 | 105 | m16 | 87-90 | 90 | row | :105 87-90 | yes |
| 19 | 106 | m17 | 91-94 | 94 | row | :106 91-94 | yes |
| 20 | 107 | m18 | 95-101 | 101 | row | :107 95-101 | yes |
| 21 | 108 | m19 | 102-103 | 103 | row | :108 102-103 | yes |
| 22 | 109 | m20 | 104 | 104 | row; 2 pools, count +1 | :109 104 (dagger) | yes |
| 23 | 131 | j01 | 105 | 75 | :168 reconciles | :131 105 (dagger) | yes |
| 24 | 132 | j02 | 106 | 75 | :168 | :132 106 (dagger) | yes |
| 25 | 133 | j03 | 107 | 75 | :168 | :133 107 (dagger) | yes |
| 26 | 134 | j04 | 108 | 75 | :168 | :134 108 (dagger) | yes |
| 27 | 142 | j05 | 109 | 76 | :168 | :142 109 (dagger) | yes |
| 28 | 143 | j06 | 110 | 77 | :168 | :143 110 (dagger) | yes |
| 29 | 144 | j07 | 111 | 78 | :168 | :144 111 (dagger) | yes |
| 30 | 161 | j04 | 112 | 112 | row | :161 112 | yes |
| 31 | 162 | j02 | 113 | 113 | row | :162 113 | yes |
| 32 | 163 | j03 | 114 | 114 | row | :163 114 | yes |
| 33 | 164 | j05 | 115 | 115 | row | :164 115 | yes |
| 34 | 165 | j06 | 116 | 116 | row | :165 116 | yes |
| 35 | 166 | j07 | 117 | 117 | row | :166 117 | yes |
| 36 | 183 | j11 | 118 | 118 | row | :183 118 | yes |
| 37 | 184 | j11 | 119 | 119 | row | :184 119 | yes |
| 38 | 202 | j12 | 120 | 120 | row | :202 120 | yes |
| 39 | 203 | j12 | 121 | 121 | row | :203 121 | yes |
| 40 | 224 | j13 | 122 | 122 | row | :224 122 | yes |
| 41 | 225 | j13 | 123 | 123 | row | :225 123 | yes |
| 42 | 249 | j14 | 124 | 124 | row | :249 124 | yes |
| 43 | 281 | j15 | 125 | 125 | row | :281 125 | yes |
| 44 | 282 | j15 | 126 | 126 | row | :282 126 | yes |
| 45 | 319 | j09 | 127 | 127 | row | :319 127 | yes |
| 46 | 320 | j10 | 128 | 128 | row | :320 128 | yes |
| 47 | 365 | m08 | 129 | 129 | row | :365 129 | yes |
| 48 | 366 | m15 | 130 | 130 | row | :366 130 | yes |
| 49 | 367 | m11 | 131 | 131 | row | :367 131 | yes |
| 50 | 368 | m12 | 132 | 132 | row | :368 132 | yes |
| 51 | 369 | m16 | 133 | 133 | row | :369 133 | yes |
| 52 | 370 | j05 | 134 | 134 | row | :370 134 | yes |
| 53 | 587 | j09 | 135 | 135 | row | :587 135 | yes |
| 54 | 588 | m22 | 136 | 136 | row | :588 136 | yes |
| 55 | 589 | m23 | 137 | 137 | row | :589 137 | yes |
| 56 | 590 | m24 | 138-139 | 139 | row | :590 138-139 | yes |
| 57 | 591 | m25 | 140-144 | 144 | row | :591 140-144 | yes |
| 58 | 592 | m26 | 145-146 | 146 | row | :592 145-146 | yes |
| 59 | 593 | m27 | 147 | 147 | row | :593 147 | yes |
| 60 | 594 | m28 | 148 | 148 | row | :594 148 | yes |
| 61 | 595 | m29 | 149 | 149 | row | :595 149 | yes |
| 62 | 596 | m30 | 150 | 150 | row | :596 150 | yes |
| 63 | 597 | m31 | 151 | 151 | row | :597 151 | yes |
| 64 | 598 | m32 | 152 | 152 | row | :598 152 | yes |
| 65 | 599 | m33 | 153 | 153 | row | :599 153 | yes |
| 66 | 600 | m34 | 154 | 154 | row | :600 154 | yes |
| 67 | 601 | m35 | 155 | 155 | row | :601 155 | yes |
| 68 | 602 | m36 | 156 | 156 | row | :602 156 | yes |
| 69 | 603 | m38 | 157 | 157 | row | :603 157 | yes |
| 70 | 604 | m39 | 158-159 | 159 | row | :604 158-159 | yes |
| 71 | 661 | m40 | 160 | 160 | row | :661 160 | yes |
| 72 | 662 | m41 | 161 | 161 | row | :662 161 | yes |
| 73 | 663 | m42 | 162 | 162 | row | :663 162 | yes |
| 74 | 664 | m43 | 163 | 163 | row | :664 163 | yes |
| 75 | 665 | m44 | 164 | 164 | row | :665 164 | yes |
| 76 | 703 | m41 | 165 | 165 | row | :703 165 | yes |
| 77 | 704 | m40 | 166 | 166 | row | :704 166 | yes |
| 78 | 705 | m44 | 167 | 167 | row | :705 167 | yes |
| 79 | 706 | m23 | 168 | 168 | row | :706 168 | yes |
| 80 | 707 | m39 | 169 | 169 | row | :707 169 | yes |
| 81 | 797 | m45 | 170 | 170 | row | :797 170 | yes |
| 82 | 798 | m46 | 171 | 171 | row | :798 171 | yes |
| 83 | 799 | m47 | 172 | 172 | row | :799 172 | yes |
| 84 | 800 | m48 | 173 | 173 | row | :800 173 | yes |
| 85 | 801 | m49 | 174 | 174 | row | :801 174 | yes |
| 86 | 824 | m41 | 175-176 | - | range 175-182 at :822, order inferred | :824 175-176 | yes |
| 87 | 825 | m41 | 177-178 | - | :822 | :825 177-178 | yes |
| 88 | 826 | m40 | 179-180 | - | :822 | :826 179-180 | yes |
| 89 | 827 | m23 | 181-182 | - | :822 | :827 181-182 | yes |
| 90 | 883 | m49 | 183-186 | 183-186 | prose | :883 183-186 | yes |
| 91 | 890 | m50 | 187 | 187 | row | :890 187 | yes |
| 92 | 891 | m51 | 188 | 188 | row | :891 188 | yes |
| 93 | 927 | m23 | 189 | - | '2 tried' at :923; implied by :959 | :923, :927 189 (dagger) | yes |
| 94 | 928 | m40 | 190 | - | :923, :959 | :923, :928 190 (dagger) | yes |
| 95 | 959 | r01 | 191 | 191 | row | :959 191 | yes |
| 96 | 960 | r02 | 192 | 192 | row | :960 192 | yes |
| 97 | 961 | r03 | 193 | 193 | row | :961 193 | yes |
| 98 | 962 | r04 | 194 | 194 | row | :962 194 | yes |
| 99 | 963 | r05 | 195 | 195 | row | :963 195 | yes |
| 100 | 964 | r06 | 196 | 196 | row | :964 196 | yes |
| 101 | 965 | r07 | 197 | 197 | row | :965 197 | yes |
| 102 | 1007 | r08 | 198 | 198 | row | :1007 198 | yes |
| 103 | 1008 | r09 | 199 | 199 | row | :1008 199 | yes |
| 104 | 1009 | r10 | 200 | 200 | row | :1009 200 | yes |
| 105 | 1010 | r11 | 201 | 201 | row | :1010 201 | yes |
| 106 | 1011 | r12 | 202 | 202 | row | :1011 202 | yes |
| 107 | 1085 | u01-u03 | 203-205 | 205 | row | :1085 203-205 | yes |
| 108 | 1086 | u04-u06 | 206-208 | 208 | row | :1086 206-208 | yes |
| 109 | 1087 | u07-u09 | 209-211 | 211 | row | :1087 209-211 | yes |
| 110 | 1088 | u10, u11 | 212-213 | 213 | row | :1088 212-213 | yes |
| 111 | 1089 | u12-u14 | 214-216 | 216 | row | :1089 214-216 | yes |
| 112 | 1062 | img-mean | 217 | - | total 219 at :1062; rows only in prereg-views.md:72-75 | :1062 217 (dagger) | yes |
| 113 | 1062 | query-mean | 218 | - | :1062 | :1062 218 (dagger) | yes |
| 114 | 1062 | caption | 219 | - | :1062 | :1062 219 (dagger) | yes |
| 115 | 1200 | j16 | 220 | 220 | row | :1200 220 | yes |
| 116 | 1201 | j16+route | 221 | 221 | row | :1201 221 | yes |
| 117 | 1202 | j17+route | 222 | 222 | row | :1202 222 | yes |
| 118 | 1164 | j18 | 223 | 219 + 1 | total 224 at :1298-1299, no order | :1164 223 (dagger) | yes |
| 119 | 1165 | j19 | 224 | 219 + 2 | :1298-1299 | :1165 224 (dagger) | yes |
| 120 | 1328 | j24 | 225 | 224 + 1 | :1384 assigns 225 | :1328 225 | yes |
| 121 | 1329 | j25 | 226 | 224 + 2 | :1384 assigns 226 | :1329 226 | yes |
| 122 | 1376 | j22 | 227 | 224 + 1 | :1384 assigns 227 | :1376 227 | yes |
| 123 | 1377 | j23 | 228 | 224 + 2 | :1384 assigns 228 | :1377 228 | yes |
| 124 | 1409 | j20 | 229 | 224 + 1 | :1415 assigns 229 | :1409 229 | yes |
| 125 | 1410 | j21 | 230 | 224 + 2 | :1415 assigns 230 | :1410 230 | yes |
| 126 | 1479 | j26 | 231 | 230 + 1 | :1495 | :1479 231 | yes |
| 127 | 1480 | j27 | 232 | 230 + 2 | :1495 | :1480 232 | yes |


## Compile, tests, guard

- `tectonic --only-cached` from docs/paper: in the sandbox it fails creating its cache folder (`Operation not permitted`); outside the sandbox it fails with `failed to open input file "tectonic-format-latex.tex"`, so the cache lacks the LaTeX format and a compile would need a download. No pages, overfull boxes or undefined references could be reported. No other LaTeX engine is installed. Labels referenced by the two files (sec:whatbroke, sec:h21b, tab:tries, tab:nottried) exist (grep). My edits add only comment lines.
- `python -m pytest -q`: 832 passed, 43 skipped, 24 failed; all 24 are sandbox failures in files not touched here (writes to /tmp, no free CARLA port, `submit.sh` subprocess): tests/test_j10_hmmfisher.py, test_savio_runtime.py, test_slow_watchdog.py, test_submit.py. test_submit.py and test_slow_watchdog.py fail the same way with my edits stashed.
- `python scripts/check_sealed_imports.py`: ok, 18 files clean.

## Commands

```
git apply /Users/yanzihao/autoresearch-local/tasks/fc-partial/limits-appendix.diff
/opt/miniconda3/bin/python results/h21/paper-factcheck-limits/recount.py
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q
/opt/miniconda3/bin/python scripts/check_sealed_imports.py
cd docs/paper && tectonic --only-cached -o $TMPDIR main.tex
```
Manifest counts: an inline Python read of results/h21/h21b/manifest.json (role `pilot_slice`, type = `practice_gaps`, pair with `-sNN` stripped) and routes.jsonl.
