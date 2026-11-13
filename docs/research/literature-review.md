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
