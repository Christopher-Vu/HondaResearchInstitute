# Literature review: finding failure groups in driving policies

2026-11-12, after H22 and H23 read `not_ahead` on Fail2Drive. Question: refine our activation methods, or adopt a different method?

**How this was checked.** A research run searched five angles, fetched 15 primary sources and extracted 56 claims. Three independent checkers voted on each of 25 claims, and a claim died at 2 votes against: 21 held and 4 died. Branches the run left empty were then searched directly, and three abstracts were fetched and quoted. Each row below says how far it was checked. Nothing here has been read past the abstract unless the row says so. Every performance number is the authors' own.

| Check level | Meaning |
|---|---|
| Panel | The abstract or paper text was fetched, and a 3-vote panel upheld the claim |
| Abstract | The abstract page was fetched and the claim quoted from it |
| Snippet | Only search-result text was seen. Do not cite until read |

## What the field reports

| Work | What it does | Tested on known groups? | Reported result | Check |
|---|---|---|---|---|
| Domino. Eyuboglu et al., ICLR 2022, [2203.14960](https://arxiv.org/abs/2203.14960) | Embeds inputs with an image-and-text model, then fits an **error-aware** mixture model, so the failure label shapes the groups | Yes: dcbench, 1,235 planted settings (images, X-rays, EEG) | Recovers **36%** of planted slices, 12 points above earlier methods | Panel |
| Johnson, Cabrera, Plumb, Talwalkar, AAAI HCOMP 2023, [2306.08167](https://arxiv.org/abs/2306.08167) | User study of Domino and PlaneSpot (15 people, 40 slices, object detector) | Human use, not recovery | "Some benefit over a naive baseline" | Panel |
| Spotlight. d'Eon et al., 2021, [2107.00758](https://arxiv.org/abs/2107.00758) | Reweights data around a point in the last hidden layer to find a weak region | No numbers seen | Not seen | Snippet |
| PlaneSpot and SpotCheck. Plumb et al., TMLR 2023, [2207.04104](https://arxiv.org/abs/2207.04104) | SpotCheck trains models with known planted blind spots on synthetic images. PlaneSpot finds them in a 2-D image representation | Yes, synthetic | "Competitive with and in many cases outperforms" earlier methods | Snippet |
| FACTS. Yenamandra et al., ICCV 2023, [2309.17430](https://arxiv.org/abs/2309.17430) | Amplifies a model's shortcut, then clusters the samples it confidently gets wrong | Yes, correlation-bias benchmarks | Up to 35% better precision@10 | Snippet |
| B2T. Kim et al., CVPR 2024, [2301.11104](https://arxiv.org/abs/2301.11104) | Captions misclassified images, pulls frequent keywords, checks them with CLIP | Yes: known biases in CelebA, Waterbirds, ImageNet-R/C | Recovers the known biases | Snippet |
| DrML. Zhang et al., ICLR 2023, [2302.04269](https://arxiv.org/abs/2302.04269) | Probes a CLIP-style image-text space with text alone | Yes, image datasets with known error slices | Only works on models built on that embedding | Panel |
| InfEmbed. Wang et al., NeurIPS 2023, [2312.04712](https://arxiv.org/abs/2312.04712) | K-means on influence embeddings (how each sample pulls the model's loss) | "2 benchmarks", not named in the abstract | "Outperforms current state-of-the-art methods" | Abstract |
| MCSD. Yu et al., 2025, [2501.19032](https://arxiv.org/abs/2501.19032) | Optimises error and group coherence directly | A benchmark, not named in the abstract | "Superiority", no numbers in the abstract | Abstract |
| Caption-then-cluster. Gupta, Ciftci, Bansal, 2025, [2506.06570](https://arxiv.org/abs/2506.06570) | A vision-language model explains each failure from a few frames, and an LLM groups the explanations | Yes: RoboFail, 100 robot videos, 8 expert failure modes | Finds all 8 modes. Assignment F1 **85.5% against 32.4%** for an embedding-similarity baseline. Driving shown only on human dashcam crashes, judged by eye | Panel |
| FailSAE. Ma, Liu, Zhu, 2026, [2609.04276](https://arxiv.org/pdf/2609.04276) | A classifier on SAE latents predicts whether a vision-language model is wrong and how | No: failure types are the authors' own corruptions | Supervised prediction, not discovery | Panel |
| Swann et al., 2026, [2603.19183](https://arxiv.org/abs/2603.19183) (Dr. VLA) | SAEs on a vision-language-action robot policy. Some features steer behaviour, and a metric sorts features into "general transferable primitives or episode-specific memorizations" | No | No failure-discovery test | Abstract |
| Fail2Drive. Gerstenecker, Geiger, Renz, IROS 2026, [2604.08535](https://arxiv.org/abs/2604.08535) | 200 paired CARLA routes. "Each shifted route is matched with an in-distribution counterpart, isolating the effect of the shift" | It is the benchmark | Reports failures such as ignoring clearly visible objects | Panel |
| Bench2ADVLM. Zhang et al., 2025, [2508.02028](https://arxiv.org/abs/2508.02028) | Closed-loop scenario generation that hunts new failures of vision-language drivers | No: it finds new failures and does not recover known ones | Not checked | Panel (abstract) |
| KING. Hanselmann et al., ECCV 2022, [2204.13683](https://arxiv.org/abs/2204.13683) | Gradients through a simple car model make CARLA traffic adversarial | No | 20% higher success than black-box search | Snippet |
| Dynasto, 2026, [2603.21427](https://arxiv.org/pdf/2603.21427) | Turns each failure trace into a sequence of events (cut-in, then collision) and clusters the sequences | Not seen | Not seen | Snippet |
| Lyu, Fu, Bayen, 2026, [2601.20367](https://arxiv.org/abs/2601.20367) | Scores unusual traffic by a trajectory predictor's error | No: checked only against proxy safety measures | Spearman about -0.24 to 0.31 | Panel |

**Refuted by the panel (0 to 3), do not use:** an ICLR 2026 page's claims that mean-pooling activations caused 88% failure and that discrete action tokens gave 0% success in SAE steering. A search snippet said most of Swann et al.'s features are memorised demonstrations, and the abstract does not say that.

**Not found:** any method tested on recovering known failure groups of a closed-loop driving policy, any SAE failure-discovery work on a driving model, and any planted-group benchmark for driving.

### Clustering around a known nuisance (added 2026-11-15, autoresearch loop)

Proposed by a Gemini literature read (`results/h21/lit-nuisance-gemini.txt`). A Grok worker then checked each item against DBLP, Crossref, arXiv and publisher pages (`results/h21/cite-check.md` on the loop machine, not tracked), and I re-read the Crossref records for Gondek, Bae and Gretton. Check levels are the same as above.

| Work | What it does | Check |
|---|---|---|
| cPCA. Abid, Zhang, Bagaria, Zou, *Nature Communications* 9:2134 (2018), [doi:10.1038/s41467-018-04608-8](https://doi.org/10.1038/s41467-018-04608-8) | Directions where the target data varies more than the background, from `C_X − α C_Y` (paper text, figure 1 caption). Basis of `j02` | Abstract and text |
| HSIC. Gretton, Bousquet, Smola, Schölkopf, ALT 2005, LNCS 3734, [doi:10.1007/11564089_7](https://doi.org/10.1007/11564089_7) | Kernel dependence measure (Hilbert-Schmidt norm of the cross-covariance operator) | Abstract |
| Non-redundant clustering. Gondek, Hofmann, ICDM 2004, [doi:10.1109/ICDM.2004.10104](https://doi.org/10.1109/ICDM.2004.10104); journal version KAIS 12(1), 2007 | "Coordinated conditional information bottleneck": a clustering that avoids redundancy with a known grouping | Abstract (via OpenAlex) |
| COALA. Bae, Bailey, ICDM 2006, [doi:10.1109/ICDM.2006.37](https://doi.org/10.1109/ICDM.2006.37) | An alternative clustering of high quality that is dissimilar to a given one. The agglomerative and cannot-link details are not in the abstract and were not checked | Abstract (via OpenAlex) |
| Niu, Dy, Jordan, "Multiple Non-Redundant Spectral Clustering Views", ICML 2010 | Learns several subspaces at once and penalises dependence between them. It does not take a given clustering as input | Abstract |
| Spotlight. d'Eon, d'Eon, Wright, Leyton-Brown, FAccT 2022, [doi:10.1145/3531146.3533240](https://doi.org/10.1145/3531146.3533240) | Replaces the Snippet-level row above: it finds contiguous regions of the final hidden layer where loss is high | Abstract and text |

**Wrong citations, do not use:** "Niu, Dy, Jordan (2010), *Dimensionality Reduction for Alternative Clustering using Information Theoretic Divergence*, AISTATS 2010" does not exist; the nearest real paper is the ICML 2010 entry above. COALA is by two authors, not by "Bae, Bailey, Leckie, PAKDD 2006". Gondek and Hofmann's 2003 item is a workshop paper titled "Conditional information bottleneck clustering", and it was not retrieved.

### Cluster stability under resampling (added 2026-11-15, autoresearch loop)

Basis of `j08`, which ranks candidate clusters from several views by how stable each one is on subsamples of the failing routes. A Grok worker read the records listed below; I re-read the Crossref records for all three and the ScienceDirect abstract text for Hennig.

| Work | What it does | Check |
|---|---|---|
| Hennig, "Cluster-wise assessment of cluster stability", *Computational Statistics & Data Analysis* 52(1):258–271 (2007), [doi:10.1016/j.csda.2006.11.025](https://doi.org/10.1016/j.csda.2006.11.025) | Stability of each single cluster: the Jaccard coefficient against the most similar cluster in resampled data, averaged over the resamples. Uses the bootstrap, and also subsetting, jittering and noise points. The abstract warns that clusters are sometimes stable only because of the inflexibility of the clustering method | Abstract |
| Ben-Hur, Elisseeff, Guyon, "A stability based method for discovering structure in clustered data", Pacific Symposium on Biocomputing 7:6–17 (2002), [doi:10.1142/9789812799623_0002](https://doi.org/10.1142/9789812799623_0002) | Stability of a whole clustering under subsampling, used to choose the number of clusters | Metadata and PDF header only |
| Lange, Roth, Braun, Buhmann, "Stability-based validation of clustering solutions", *Neural Computation* 16(6):1299–1323 (2004), [doi:10.1162/089976604773717621](https://doi.org/10.1162/089976604773717621) | Stability as how well a clustering reproduces on a second sample, read as a classification risk | Abstract |

### Clustering sequences with hidden Markov models (added 2026-11-15, autoresearch loop)

Background for `j09`, which fits one Gaussian hidden Markov model (HMM: a small set of hidden states, each with its own Gaussian, plus state-to-state transition probabilities) on every route's frame sequence and clusters failing routes by state occupancy and transitions. A Gemini worker proposed the list from memory; a Grok worker checked each against Crossref or OpenAlex, and I re-read the Crossref records for Alon, both Bicego papers and Celeux. Only metadata was checked, not the papers' contents, so the "what it does" column is the common description, unverified.

| Work | What it does (unverified) | Check |
|---|---|---|
| Smyth, "Clustering sequences with hidden Markov models", NIPS 9:648–654 (1996) | Clusters sequences by fitting HMMs and grouping by cross-likelihood | OpenAlex W2132875213 only; no DOI |
| Alon, Sclaroff, Kollios, Pavlovic, "Discovering clusters in motion time-series data", CVPR 2003, I-375–I-381, [doi:10.1109/cvpr.2003.1211378](https://doi.org/10.1109/cvpr.2003.1211378) | HMM mixture clustering of motion sequences | Crossref |
| Bicego, Murino, Figueiredo, "Similarity-based clustering of sequences using hidden Markov models", MLDM 2003, LNCS, pp. 86–95, [doi:10.1007/3-540-45065-3_8](https://doi.org/10.1007/3-540-45065-3_8) | Embeds sequences by their likelihoods under a set of HMMs, then clusters | Crossref |
| Bicego, Murino, Figueiredo, "Similarity-based classification of sequences using hidden Markov models", *Pattern Recognition* 37(12):2281–2291 (2004), [doi:10.1016/s0031-3203(04)00162-1](https://doi.org/10.1016/s0031-3203(04)00162-1) | The same embedding used for classification | Crossref |
| Jaakkola, Haussler, "Exploiting generative models in discriminative classifiers", NIPS 11:487–493 (1998) | Fisher score of a generative model as a fixed-length sequence embedding | OpenAlex only; no DOI |
| Celeux, Durand, "Selecting hidden Markov model state number with cross-validated likelihood", *Computational Statistics* 23(4):541–564 (2008), [doi:10.1007/s00180-007-0097-1](https://doi.org/10.1007/s00180-007-0097-1) | Compares BIC-type criteria and cross-validated likelihood for choosing the number of states | Crossref |

**Do not use** (Gemini's metadata, wrong): DOI 10.1109/CVPR.2003.1211376 (a different paper); 10.1007/3-540-70659-3_9 and "SSPR 2002, LNCS 2396" for Bicego 2002 (a different paper, and the venue is MLDM 2003); 10.1016/j.patcog.2004.05.006 (a different paper); a Celeux and Durand paper in *CSDA* 52(4):2071–2085 (not found). Keribin, "Consistent estimation of the order of mixture models", *Sankhyā A* 62(1):49–66 (2000) was not found in Crossref or OpenAlex, so it is not cited until someone checks it another way. Report: `/tmp/ar-cite-hmm/report.md` on the loop machine.

## What this means for us

1. **Our negative result is ordinary for this field.** The reference method recovers about a third of planted groups on its own benchmark, and people gain only a little from these tools. A behaviour baseline beating activations on 16 failures does not show that activations are useless, and it does not suggest a quick fix either.
2. **The methods that work best use the failure label while grouping.** Domino's error-aware mixture, FACTS and InfEmbed all do this. M1 groups by latent first and only then compares failures with successes, and B3 won by grouping failures directly on what they share. This is the clearest refinement the literature supports.
3. **Descriptions beat raw embeddings in the one test found.** Caption-then-cluster beat embedding similarity by 85.5 to 32.4 F1. That is robot manipulation, the numbers are self-reported, and one model family both groups and judges, so it may be optimistic.
4. **Nobody has tested any of this on a driving policy's known failures.** Whatever we run next is new, and its result is ours to measure.

## Options, cheapest first

| Option | Kind | Data it needs | Evidence | Cost |
|---|---|---|---|---|
| Error-aware mixture (Domino-style, PRD's planned B5) on activations, behaviour, or both | Refine | Stored shards and traces | Domino, FACTS, InfEmbed (images, not driving) | About 5 SU or local |
| Paired contrast: each unseen route minus its own twin, then group the differences | Refine | Stored shards and traces | Fail2Drive's pair design. **Our idea, not a published method** | About 5 SU or local |
| Per-moment activations instead of route averages | Refine | Stored shards | None verified. The supporting claim was refuted | About 5 SU |
| Caption-then-cluster with a vision-language model on camera frames | New | Frames. The capture agent saves the driver's camera every 20 steps, unconfirmed for H21 until Savio is logged in | Gupta et al. (robots) | API cost, no SU if frames exist |
| Image-embedding grouping of frames (Domino's original form) | New | Frames | Domino | Local |
| Scenario search or scene edits (KING, Bench2ADVLM) | Different question | New drives | Finds new failures, not known ones | Hundreds of SU |

## Caution before any of these runs

H22 and H23 have already looked at Fail2Drive's three categories twice. A third method tuned on the same 16 failures could win by chance. Any next test should be locked first, should also run on a pool it has not been tuned on (H1's or H12's pool, with P4, P7, P8 and P19), and should keep H22's random matched-size control.
