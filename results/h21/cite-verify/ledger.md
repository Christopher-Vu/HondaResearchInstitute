# Citation verification ledger, 2026-11-20

Scope: the unverified Part 2 of `docs/paper/refs.bib` (12 entries; the task said 13, but the file had 12 at commit b88db53), plus a spot check of 5 audit-verified Part 1 entries. Sources: the Crossref, OpenAlex and arXiv public APIs only, generic User-Agent, no personal details. No source refused: no HTTP 429, 403 or bot check was seen. OpenAlex and Crossref sometimes cut a response short (`IncompleteRead`); those requests were retried after a pause and then succeeded.

"Verified" here means the API record and the bib entry agree on title, authors, year and venue. It says nothing about what the paper claims. Content claims are in the second half of this file.

## Part 2: the formerly unverified entries

| Key | API record (title; authors; year; venue; id) | Bib before | Fix applied | Verdict |
|---|---|---|---|---|
| `hu2023uniad` | Crossref: "Planning-oriented Autonomous Driving"; Hu, Yang, Chen, Li, Sima, Zhu, Chai, Du, Lin, Wang, Lu, Jia, Liu, Dai, Qiao, Li (16); 2023; CVPR 2023, pp. 17853-17862; doi 10.1109/cvpr52729.2023.01712. OpenAlex W4386076400 agrees | Title, authors, venue, year matched | Added pages and DOI; dropped the "from memory" note | verified crossref |
| `gupta2025caption` | arXiv 2506.06570v4: "Unsupervised Discovery of Failure Taxonomies from Deployment Logs"; Aryaman Gupta, Yusuf Umut Ciftci, Somil Bansal; first posted 2025-06-06; no journal_ref. v1 title: "Enhancing Robot Safety via MLLM-Based Semantic Interpretation of Failure Data". Not found by title in Crossref or OpenAlex | Placeholder title, surnames only | Real title, full names, note on the v1 title | verified arxiv |
| `yenamandra2023facts` | Crossref: "FACTS: First Amplify Correlations and Then Slice to Discover Bias"; Yenamandra, Ramesh, Prabhu, Hoffman; 2023; ICCV 2023, pp. 4771-4781; doi 10.1109/iccv51070.2023.00442. OpenAlex W4390872142 and arXiv 2309.17430 ("Accepted to ICCV 2023") agree | Title incomplete, "and others" | Full title, four authors, pages, DOI | verified crossref |
| `kim2024b2t` | Crossref: "Discovering and Mitigating Visual Biases Through Keyword Explanation"; Younghyun Kim, Sangwoo Mo, Minkyu Kim, Kyungmin Lee, Jaeho Lee, Jinwoo Shin; 2024; CVPR 2024, pp. 11082-11092; doi 10.1109/cvpr52733.2024.01054. OpenAlex W4402727755 and arXiv 2301.11104 ("CVPR 2024") agree | Placeholder title, "and others" | Real title, six authors, pages, DOI; B2T name moved to a note | verified crossref |
| `wang2023infembed` | Crossref: "Error Discovery By Clustering Influence Embeddings"; Fulton Wang, Julius Adebayo, Sarah Tan, Diego Garcia-Olano, Narine Kokhlikyan; 2023; Advances in Neural Information Processing Systems 36, pp. 41765-41777; doi 10.52202/075280-1809. arXiv 2312.04712 ("NeurIPS 2023 conference paper") agrees | Placeholder title, "and others" | Real title, five authors, volume, pages, DOI | verified crossref |
| `plumb2023planespot` | arXiv 2207.04104v3: "Towards a More Rigorous Science of Blindspot Discovery in Image Classification Models"; Gregory Plumb, Nari Johnson, Ángel Alexander Cabrera, Ameet Talwalkar; journal_ref "TMLR 2023"; OpenReview MaDvbLaBiF. OpenAlex W4285070034: TMLR, year 2022 (the arXiv year), DOI is the arXiv DOI. Not found in Crossref by title | Placeholder title, "and others" | Real title, four authors, OpenReview URL; year kept at 2023 per journal_ref | verified arxiv |
| `abid2018cpca` | Crossref: "Exploring patterns enriched in a dataset with contrastive principal component analysis"; Abid, Zhang, Bagaria, Zou; 2018; Nature Communications 9(1); doi 10.1038/s41467-018-04608-8. OpenAlex W2805695370 gives article number 2134 | Matched | Added number 1; dropped note | verified crossref |
| `hennig2007stability` | Crossref: "Cluster-wise assessment of cluster stability"; Christian Hennig; issued 2007-09; Computational Statistics & Data Analysis 52(1):258-271; doi 10.1016/j.csda.2006.11.025. OpenAlex gives year 2006 (online date) | Matched | Dropped note | verified crossref |
| `smyth1996hmm` | OpenAlex W2132875213: "Clustering Sequences with Hidden Markov Models"; Padhraic Smyth; 1996; Neural Information Processing Systems, vol. 9, pp. 648-654; no DOI. Crossref title search did not find it | Matched | Title case and note | verified openalex |
| `ward1963hierarchical` | Crossref: "Hierarchical Grouping to Optimize an Objective Function"; Joe H. Ward; 1963; JASA 58(301):236-244; doi 10.1080/01621459.1963.10500845. OpenAlex W2016381774 agrees (it lists only first page) | Matched | Added DOI; dropped note | verified crossref |
| `efron1979bootstrap` | Crossref: "Bootstrap Methods: Another Look at the Jackknife"; B. Efron; 1979; The Annals of Statistics 7(1):1-26; doi 10.1214/aos/1176344552. OpenAlex W2117897510 agrees | Matched | Added DOI; dropped note | verified crossref |
| `oquab2024dinov2` | arXiv 2304.07193v2: "DINOv2: Learning Robust Visual Features without Supervision"; Oquab and 25 others; posted 2023-04-14; no journal_ref. OpenAlex W4366208220: TMLR, year 2023. Not found in Crossref by title | Year 2024, "and others" | All 26 authors, arXiv id, year 2023 per OpenAlex. No API gave the TMLR publication date, so if the TMLR year matters it is still unchecked. The key keeps "2024" so nothing that names it breaks | verified arxiv (venue via openalex; TMLR year unverified) |

## Part 1: spot check of 5 audit-verified entries

| Key | API record | Match |
|---|---|---|
| `kuhn1955hungarian` | Crossref: "The Hungarian method for the assignment problem"; H. W. Kuhn; 1955; Naval Research Logistics Quarterly 2(1-2):83-97; doi 10.1002/nav.3800020109 | Yes |
| `corso2021survey` | Crossref: "A Survey of Algorithms for Black-Box Safety Validation of Cyber-Physical Systems"; Corso, Moss, Koren, Lee, Kochenderfer; 2021; JAIR 72; doi 10.1613/jair.1.12716. Crossref returns no pages, so 377-428 is not checked | Yes |
| `campello2013hdbscan` | Crossref: "Density-Based Clustering Based on Hierarchical Density Estimates"; Campello, Moulavi, Sander; 2013; Lecture Notes in Computer Science, pp. 160-172; doi 10.1007/978-3-642-37456-2_14. Crossref gives no volume, so 7819 is not checked | Yes |
| `sagadeeva2021sliceline` | Crossref: "SliceLine: Fast, Linear-Algebra-based Slice Finding for ML Model Debugging"; Sagadeeva, Boehm; 2021; SIGMOD 2021, pp. 2290-2299; doi 10.1145/3448016.3457323. OpenAlex W3173326111 agrees | Yes |
| `Renz2025cvpr` | arXiv 2503.09594v1: "SimLingo: Vision-Only Closed-Loop Autonomous Driving with Language-Action Alignment"; Renz, Chen, Arani, Sinavski; comment "CVPR 2025". arXiv gives no pages, so 11993-12003 is not checked | Yes |

### Seen in passing and not changed (Part 1 is copied from the audit)

The arXiv batch also returned records for other Part 1 entries. These differences were seen and left alone. The orchestrator can decide on them.

- `jin2026eventsae`: arXiv 2605.17204v2 has the comment "NeurIPS 2026 camera-ready version". The bib still says arXiv preprint.
- `babu2026depthwise`: arXiv 2608.07361 has the comment "Accepted at the 6th DriveX Workshop ... ECCV 2026". The bib says arXiv preprint.
- `jaeger2023hidden`: OpenAlex W4390872706 gives ICCV 2023, pp. 8206-8215, doi 10.1109/iccv51070.2023.00757. The bib has no pages and no DOI.
- `zimmerlin2024hidden`: OpenAlex W4405355500 has only the arXiv preprint 2412.09602, posted December 2024. The bib says CVPRW 2024, and no API confirmed that venue.
- `zhang2023cat`: OpenAlex W4387838419 has only the arXiv preprint 2310.12432. The CoRL/PMLR venue in the bib is not confirmed by these APIs.
- `swann2026sparse`: arXiv lists "Monroe Kennedy", and the bib has "Kennedy III, Monroe". The two names agree in substance.

## Claims in the text about cited papers

Legend: **abstract: yes** means the claim can be checked from title or abstract, and the abstract supports it. **abstract: partly** means part of the claim is supported and the rest needs the paper. **PDF** means the API metadata cannot check it. No claim text was changed.

### `docs/paper/related.tex`

| Claim | Paper | Checkable from metadata? |
|---|---|---|
| Pairs each unseen scenario with an in-distribution twin | Fail2Drive | abstract: yes ("Each shifted route is matched with an in-distribution counterpart") |
| ... "on the same road" | Fail2Drive | PDF (not in abstract) |
| SimLingo's sharpest drop is on PedestriansOnRoad, attributed to following a nonexistent car or cyclist | Fail2Drive | PDF (sourced to trackA A2) |
| Closed-loop driving benchmark on CARLA | Bench2Drive | abstract: yes (closed-loop E2E-AD benchmark; CARLA named in the abstract) |
| CARLA is the simulator the pools were driven in | CARLA | Our fact, not a claim about the paper |
| TransFuser++ is the first held-out model | Jaeger 2023 | abstract: partly (the abstract introduces "TF++"); held-out status is ours |
| Discovers systematic errors with cross-modal embeddings | Domino | abstract: yes |
| General method for discovering systematic errors in deep models | Spotlight | abstract: yes (title) |
| Targets hidden subclasses inside coarse classes | George | abstract: yes ("hidden stratification", unlabeled subclasses) |
| Finds slices for model debugging with linear algebra | SliceLine | abstract: yes |
| SAE features on VLA policies can be inspected and in some cases steered | Swann; Jin | abstract: yes for both (Swann: "causally steerable"; Jin: interventions with causal effects) |
| Dr. VLA's per-feature statistics separate general features from episode-specific ones | Swann | abstract: partly ("a metric to categorize features as general transferable primitives or episode-specific memorizations"); "per-feature statistics" needs the PDF |
| Interpretability work on end-to-end driving models | Motzkus | abstract: yes (title) |
| Probed and pruned the planning token of a driving VLA | Babu | abstract: yes (title) |
| Interpreted road scenes through VLA models | Panda | abstract: yes (title) |
| Extracted control vectors from motion transformers | Tas | abstract: yes (title) |
| Linear probes | Alain | abstract: yes (title) |
| None of these scores the recovery of known failure groups | all of the above | PDF (a claim of absence; an abstract cannot settle it) |
| Edits observations and predicts degradation for manipulation policies | RoboART | abstract: yes (generative image editing; predicts performance; manipulation) |
| Generate safety-critical driving scenarios | KING, AdvSim, ChatScene | abstract: yes (titles) |
| Trains against adversarial scenarios in closed loop | CAT | abstract: yes |
| Survey of black-box safety validation | Corso | abstract: yes (title) |
| Predicts that a failure will happen | SAFE | abstract: yes ("predict a single scalar indicating the likelihood of task failure") |
| Uncited list: "caption-then-cluster failure discovery for robot videos" | Gupta | abstract: partly (v4 abstract: infers failure explanations with vision-language reasoning, then clusters them). v4 covers manipulation, indoor navigation and autonomous driving, so "robot videos" is narrower than the paper |
| Uncited list: FACTS, B2T, InfEmbed and PlaneSpot are "error-aware slice methods" | FACTS, B2T, InfEmbed, PlaneSpot | abstract: yes for B2T (captions of mispredicted images), FACTS (bias-aligned slicing of underperforming slices) and InfEmbed (slices where the model under-performs). PDF for PlaneSpot: the abstract does not say whether errors enter the grouping |
| Uncited list: contrastive PCA, cluster-wise stability, HMM sequence clustering, Ward linkage, the bootstrap, DINOv2 | each | abstract: yes as names (titles). "Ward linkage" as the minimum-variance criterion is not in Ward's abstract, which describes a general objective chosen by the investigator, so that reading needs the PDF |

### `docs/research/literature-review.md`

| Row | Claim | Checkable from metadata? |
|---|---|---|
| Domino | Cross-modal embeddings plus an error-aware mixture model | abstract: yes |
| Domino | 1,235 planted settings; recovers 36%, 12 points above earlier methods | abstract: yes |
| Domino | "images, X-rays, EEG" | abstract: partly (the abstract says natural images, medical images, time series; X-ray and EEG need the PDF) |
| Johnson et al. | User study, 15 people, 40 slices, object detector, "some benefit over a naive baseline" | abstract: yes. Also AAAI HCOMP 11(1):65-76, doi 10.1609/hcomp.v11i1.27548 |
| Johnson et al. | "of Domino and PlaneSpot" | PDF (the abstract says only "two state-of-the-art slice discovery algorithms") |
| Spotlight | Final-hidden-layer regions where the model performs poorly | abstract: yes |
| Spotlight | "Reweights data around a point" | PDF |
| PlaneSpot/SpotCheck | SpotCheck plants blind spots in synthetic images; PlaneSpot uses a 2-D representation; "competitive with and in many cases outperforms" | abstract: yes (exact quote present) |
| FACTS | Amplify the shortcut, then slice; correlation-bias benchmarks; up to 35% better precision@10 | abstract: yes |
| FACTS | "clusters the samples it confidently gets wrong" | PDF (the abstract says mixture modelling in bias-aligned feature space) |
| B2T | Captions misclassified images, pulls keywords, checks them; known biases in CelebA, Waterbirds, ImageNet-R/C | abstract: yes |
| B2T | Checks keywords "with CLIP" | PDF (the abstract says "a vision-language scoring model") |
| DrML | Probes a multi-modal embedding with text alone; image datasets with known error slices | abstract: yes |
| DrML | "Only works on models built on that embedding" | PDF |
| InfEmbed | K-means on influence embeddings; "2 benchmarks"; "outperforms current state-of-the-art methods" | abstract: yes |
| MCSD | Optimises risk and coherence directly; "superiority", no numbers | abstract: yes |
| Caption-then-cluster | A vision-language model explains failures and the explanations are clustered | abstract: yes (v1 and v4) |
| Caption-then-cluster | RoboFail, 100 videos, 8 expert modes, all 8 found, F1 85.5% vs 32.4% | PDF. Neither v1 nor v4 abstract has these numbers |
| Caption-then-cluster | An LLM groups the explanations; driving shown only on human dashcam crashes, judged by eye | PDF. The v4 abstract names an autonomous-driving evaluation, so this may describe an earlier version. Recheck against v4 before use |
| FailSAE | A classifier on SAE latents predicts VLM failure; supervised, not discovery | abstract: yes |
| FailSAE | "failure types are the authors' own corruptions" | PDF |
| Swann (Dr. VLA) | SAE features steer behaviour; quote "general transferable primitives or episode-specific memorizations" | abstract: yes |
| Fail2Drive | 200 paired routes; matched-counterpart quote; ignoring clearly visible objects | abstract: yes ("ignoring objects clearly visible in the LiDAR") |
| Bench2ADVLM | Closed-loop scenario generation that finds new failures of VLM drivers | abstract: yes |
| KING | Gradients through a simple car model; 20% higher success than black-box search | abstract: yes ("kinematic bicycle model"; "20% higher success rate than black-box optimization") |
| Dynasto | Clusters failures by event sequences | abstract: partly ("a graph-based clustering pipeline groups failures into representative modes based on semantic event sequences"). The main contribution is RL and genetic-algorithm scenario search, which the row omits. Authors per arXiv: Humeniuk, Hamdaqa, Ben Braiek, Bennaceur, Khomh; evaluated in HighwayEnv |
| Lyu, Fu, Bayen | Scores unusual traffic by prediction residuals; checked against surrogate safety measures | abstract: yes |
| Lyu, Fu, Bayen | Spearman about -0.24 to 0.31 | PDF (the abstract names Kendall and Jaccard for stability, and correlations with surrogate safety measures without numbers) |
| cPCA | Directions enriched in target data relative to background | abstract: yes |
| cPCA | The `C_X - alpha C_Y` form (figure 1 caption) | PDF |
| Hennig | Per-cluster Jaccard against the most similar resampled cluster; bootstrap, subsetting, jittering, noise; the warning about inflexible methods | PDF here: neither Crossref nor OpenAlex returns an abstract. The review says it read the ScienceDirect abstract, and this pass did not recheck that |
| Smyth | Clusters sequences by fitting HMMs | abstract: yes (a model-based mixture of HMMs; also proposes initialisation and choosing K) |
| Smyth | "grouping by cross-likelihood" | PDF |

Rows of the review that have no `refs.bib` entry were not rechecked in this pass: HSIC, Gondek and Hofmann, COALA, Niu et al., Ben-Hur et al., Lange et al., Alon et al., the two Bicego papers, Jaakkola and Haussler, Celeux and Durand, Wiskott and Sejnowski, Hyvärinen and Morioka, van den Oord et al., Schmid, and De Cock and De Moor.

## Requests made

All requests went through `urllib` or `curl` with `User-Agent: cite-check/1.0 (generic)`.

- arXiv: `https://export.arxiv.org/api/query?id_list=...`, two batch requests: one with the 5 Part 2 ids, one with 27 ids including `2506.06570v1`. Plain `http://` returned a 301 redirect to https.
- Crossref: `https://api.crossref.org/works/<doi>` and `https://api.crossref.org/works?rows=N&query.bibliographic=<title>`.
- OpenAlex: `https://api.openalex.org/works/<doi:...|W...>` and `https://api.openalex.org/works?per_page=N&search=<title>`.
