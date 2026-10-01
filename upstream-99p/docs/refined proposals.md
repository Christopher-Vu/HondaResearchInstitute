# 5 Publishable Research Proposals: TL;DR Pitches, Exigence, and Literature Gaps

> [!WARNING]
> **Audit (2026-09-28):**
> - Several cited titles and venues were wrong; see [`CITATION_AUDIT.md`](CITATION_AUDIT.md).
> - Quantitative claims are targets, not results.
> - The NeurIPS 2026 Interp4Discovery and ICRA 2027 deadlines have passed.
> - The Meteor query example `sun_altitude < 10 AND truck_occlusion = True` is not from Mobileye. Meteor forms its own hypotheses.
>
> The plan of record is [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md).

> **Document Type**: Executive Pitch & Exigence Dossier  
> **Affiliation**: 99P Labs / Honda Research Institute, US & UC Berkeley CDSS 170 (Fall 2026)  
> **Project Lead**: Ryan Lingo (Honda Research Institute)  
> **Student Team**: Jerry Yan (Zihao Yan), Chris, Catherine Wang, Hiram Lannes, Jason  
> **Citations Grounding**: All referenced papers resolve to entries in [`references.bib`](../references.bib).

---

## Executive Overview Matrix

| Proposal | Target Venue | TL;DR Pitch | Exigence & Prior Research Gap Covered |
| :--- | :--- | :--- | :--- |
| **1. ActAxis** | **NeurIPS** (Interp4Discovery) / **CVPR** | Decomposes VLA hidden activations with Sparse Autoencoders to discover monosemantic, unnamed failure axes without human labels. | **Exigence**: Fleet data scaling is stalling on "unknown unknowns."<br>**Gap**: Solves scalar-only prediction in [SAFE (2025)](../references.bib#L1-L6) & input-space bias in [Domino (ICLR 2022)](../references.bib#L150-L157). |
| **2. SimLoop** | **IEEE ICRA / IROS / T-IV** | Inverts discovered activation failure clusters into parametric simulation scenarios (CARLA/CTG++) to actively retrain policies and eliminate failure modes. | **Exigence**: Discovering failure is useless without safe retraining.<br>**Gap**: Automates the human query bottleneck in [Mobileye Meteor/Genario (2026)](../references.bib#L110-L117) & static gaps in [RESample (ICRA 2024)](../references.bib#L43-L49). |
| **3. SpecGap** | **ACL / EMNLP / NeurIPS** (AI for Science) | Extracts typed claim-evidence provenance graphs from engineering literature to detect cross-paper tensions and surface falsifiable open questions. | **Exigence**: AI science is plagued by hallucinated, unfalsifiable ideas.<br>**Gap**: Solves ungrounded ideation in [The AI Scientist (2024)](../references.bib#L223-L229) using planted answer keys and [Evidence-Based Backtesting (2026)](../references.bib#L216-L222). |
| **4. ConceptProbe-SDM** | **IEEE T-ITS / CVPR** | Dual linear concept probing across vision vs. action tokens to disentangle sensor perception failure from cognitive planning collapse. | **Exigence**: Black-box VLA crashes obscure hardware liability vs. policy bug.<br>**Gap**: De-obfuscates monolithic black boxes in [DriveVLM (2024)](../references.bib#L85-L91) across the 80-slot sensor reliability grid. |
| **5. AutoCurriculum-VLA** | **ICLR / CoRL** | Active introspective self-critique where rollout epistemic uncertainty triggers adversarial LLM scene mutations to map the failure boundary. | **Exigence**: Passive rollout collection requires millions of miles to encounter 1 edge case.<br>**Gap**: Upgrades passive guardrails in [RoboMonkey (IROS 2025)](../references.bib#L50-L56) and [ReasonBreak (NeurIPS 2025)](../references.bib#L29-L35) into an active self-critique curriculum. |

---

## Proposal 1: ActAxis — Unsupervised Failure Axis Discovery in Vision-Language-Action Policies via Sparse Autoencoder Latents

### 1. Target Venue & Track
- **Primary Venue**: *Advances in Neural Information Processing Systems (NeurIPS 2026/2027)* — Track: Interpretability / Workshop on Interpretability for Discovery ([Interp4Discovery](../references.bib#L207-L212)).
- **Secondary Venue**: *IEEE/CVF CVPR 2027* — Vision-Language-Action Models & Explainable Robotics.

### 2. TL;DR Pitch
> **"Instead of guessing what makes autonomous driving fail (rain, night, merges), ActAxis applies Sparse Autoencoders to intermediate VLA hidden states across rollouts, decomposing polysemantic activations into monosemantic latent features that automatically isolate and name previously invisible, compound failure axes."**
- **Input**: Unlabelled policy rollout activations from OpenVLA / DriveVLM.
- **Novel Mechanism**: Overcomplete Sparse Autoencoders (SAEs) + mutual-information failure attribution + LLM patch captioning.
- **Output**: Ranked, human-readable failure axes (e.g., *"low sun glare behind heavy vehicles causing pedestrian distance underestimation"*).
- **Advantage**: Bypasses human taxonomy bias and achieves $>85\%$ precision/recall on planted failure holdouts.

### 3. Exigence (Why Now?)
Autonomous fleets (Tesla FSD, Waymo, Honda SENSING) have logged billions of autonomous miles. Nominal data collection now yields severely diminishing returns; catastrophic accidents almost exclusively stem from rare, compound edge cases that no engineer anticipated on a checklist. The industry urgently requires an automated discovery engine that surfaces *what to collect next* without pre-specifying failure names.

### 4. Specific Literature Gaps Addressed
1. **Scalar Failure Prediction $\neq$ Axis Discovery**:  
   Recent SOTA VLA monitors, such as [SAFE (arXiv:2506.09937, 2025)](../references.bib#L1-L6) and [ProbeAct (CVPR 2025)](../references.bib#L15-L20), fit linear probes to intermediate states to output $P(\text{failure} \mid z_t)$. While they achieve high AUROC at predicting *that* a collision will happen in the next 15 steps, they output a scalar flag. Knowing 1,000 episodes crashed provides zero structural taxonomy for targeted fleet data collection.
2. **Input-Space Bias in Slice Discovery**:  
   Existing Slice Discovery Methods (SDMs) like [Domino (ICLR 2022)](../references.bib#L150-L157) and [Spotlight (FAccT 2022)](../references.bib#L159-L166) cluster pre-trained CLIP embeddings of raw input frames. This groups scenes by superficial background semantics (e.g., "scenes with autumnal trees") rather than the *causal internal failure logic* of the robot policy.
3. **Polysemanticity in Intermediate Activations**:  
   Raw activations are entangled—a single neuron fires for both road textures and pedestrian bounding boxes. ActAxis builds on Anthropic's dictionary learning ([Bricken et al., 2023](../references.bib#L187-L197); [Gao et al., OpenAI 2024](../references.bib#L199-L205)) to isolate individual monosemantic failure directions.

---

## Proposal 2: SimLoop — Closing the Loop on Discovered Failure Modes via Controllable Scenario Diffusion and Active Fine-Tuning

### 1. Target Venue & Track
- **Primary Venue**: *IEEE International Conference on Robotics and Automation (ICRA 2027)* or *IEEE/RSJ IROS 2027*.
- **Secondary Venue**: *IEEE Transactions on Intelligent Vehicles (T-IV)*.

### 2. TL;DR Pitch
> **"SimLoop bridges the gap between interpretability and active policy repair: it takes failure axes discovered from internal activations, inverts them into parametric simulation configs, synthesizes 500+ photorealistic counterfactuals in CARLA/CTG++, and fine-tunes the policy with LoRA, demonstrating over $80\%$ reduction in targeted failure rates without forgetting."**
- **Input**: Discovered activation failure clusters from ActAxis.
- **Novel Mechanism**: Multimodal activation-to-parameter inversion + controllable diffusion simulation ([CTG++](../references.bib#L118-L124) / [ChatSim](../references.bib#L125-L131)) + LoRA fine-tuning.
- **Output**: Fully repaired policy checkpoint + 5,000 synthetic remediation scenarios.
- **Advantage**: The first end-to-end autonomous policy debugging pipeline closing the loop from internal representations to simulation retraining.

### 3. Exigence (Why Now?)
In safety-critical autonomous systems, discovering that a model fails under certain conditions is clinically useless unless engineers can remediate the weakness. Collecting physical fleet data for rare edge cases is hazardous and costly ($>\$50\text{k}$ per captured safety intervention). Simulators exist, but currently require humans to manually script the scenario.

### 4. Specific Literature Gaps Addressed
1. **The Manual Query Bottleneck in Industrial Retraining**:  
   Mobileye’s cutting-edge pipeline ([Mobileye Meteor & Genario, 2026](../references.bib#L110-L117)) proved the industrial power of mining failures (Meteor) and synthesizing retraining data (Genario). However, Meteor’s search operates in *human query space*—an analyst or LLM must specify explicit attribute queries (e.g., `sun_altitude < 10 AND truck_occlusion = True`). SimLoop replaces manual queries by inverting latent activation clusters directly into simulator parameters.
2. **Open-Loop Probing Literature**:  
   SOTA robotics probing papers ([I-FailSense, 2025](../references.bib#L22-L27); [RoboART, 2025](../references.bib#L36-L41); [RESample, ICRA 2024](../references.bib#L43-L49)) end their contribution at gap identification. None complete the loop to verify whether targeted synthetic data actually fixes the underlying policy representation.

---

## Proposal 3: SpecGap — Contrastive Claim-Evidence Provenance Graphs for Falsifiable Open-Question Discovery

### 1. Target Venue & Track
- **Primary Venue**: *Association for Computational Linguistics (ACL 2026/2027)* or *EMNLP 2026*.
- **Secondary Venue**: *NeurIPS 2026/2027 Track on AI for Science*.

### 2. TL;DR Pitch
> **"SpecGap transforms scientific literature into atomic claim-evidence provenance graphs, uses contrastive graph reasoning to detect epistemic tensions and coverage voids, and automatically generates high-priority, falsifiable open research questions validated against planted ground-truth blindspots and historical backtesting."**
- **Input**: Domain corpus of 200–300 synthetic or historical papers (Wildfire IoT, Battery E-Waste, Microplastics).
- **Novel Mechanism**: Atomic claim extraction with verbatim provenance + layered concept abstraction + cross-paper tension detection.
- **Output**: Ranked, falsifiable research questions with proposed experimental test specifications.
- **Advantage**: Eliminates LLM scientific hallucinations by grounding every question in claim-level provenance, evaluated on objective planted answer keys.

### 3. Exigence (Why Now?)
Generative AI is flooding scientific research with speculative, LLM-generated papers and hypotheses. Over $90\%$ of LLM-generated research questions are trivial reformulations, scientifically untestable, or cite non-existent papers. The academic community urgently requires an auditable system that treats scientific gap discovery as a repeatable, verifiable engineering discipline.

### 4. Specific Literature Gaps Addressed
1. **Ungrounded Ideation & Hallucination**:  
   Seminal automated discovery frameworks, such as Sakana AI's [The AI Scientist (2024)](../references.bib#L223-L229) and [SciMon (ACL 2024)](../references.bib#L231-L236), operate via unconstrained prompt ideation. They suffer from high citation hallucination rates and lack explicit claim-level provenance.
2. **The "Answer Key" Vacuum**:  
   Existing systems evaluate generated questions using subjective LLM-as-a-judge scoring, leading to circular reasoning. SpecGap adopts the rigorous methodology of [Evidence-Based Scientific Question Discovery with Historical Backtesting (2026)](../references.bib#L216-L222) and Ryan Lingo's specification: testing against **deliberately planted multi-paper blindspots** and **historical time splits**.

---

## Proposal 4: ConceptProbe-SDM — Disentangling Perception Shifts vs. Cognitive Reasoning Bottlenecks in Autonomous Fleets

### 1. Target Venue & Track
- **Primary Venue**: *IEEE Transactions on Intelligent Transportation Systems (IEEE T-ITS)*.
- **Secondary Venue**: *IEEE/CVF CVPR 2027 (Autonomous Driving Workshop)*.

### 2. TL;DR Pitch
> **"When an end-to-end driving model crashes, ConceptProbe-SDM uses dual linear probing across intermediate vision tokens versus downstream action tokens to resolve the critical liability question: did the sensor hardware fail to perceive the obstacle, or did the cognitive policy planner make an erroneous decision despite seeing it?"**
- **Input**: Multi-sensor driving logs (Camera, LiDAR, Radar) across adverse environmental conditions.
- **Novel Mechanism**: Dual concept bottleneck probing comparing visual feature retention against action head attention.
- **Output**: Diagnostic failure decomposition isolating hardware/sensor blackout from policy planning collapse.
- **Advantage**: Resolves autonomous fleet accident liability across an 80-slot sensor reliability grid.

### 3. Exigence (Why Now?)
As the automotive industry transitions from modular pipelines (separate perception $\to$ prediction $\to$ planning) to monolithic end-to-end Vision-Language-Action systems, neural networks have become opaque black boxes. In fatal crashes (e.g. into stationary highway barricades or overturned trucks in fog), automotive OEMs cannot identify whether the sensor perception washed out or the policy planner suffered cognitive collapse.

### 4. Specific Literature Gaps Addressed
1. **Monolithic Black Box in Driving VLAs**:  
   Leading autonomous driving architectures, such as [DriveVLM (2024)](../references.bib#L85-L91) and [DriveMoE (2025)](../references.bib#L99-L105), fuse multi-modal sensory data into end-to-end action outputs. When a failure occurs, existing diagnostics cannot localize which stage in the neural computation failed.
2. **Tabular-Only Slicing Methods**:  
   Classical slice discovery frameworks ([SliceLine, VLDB 2021](../references.bib#L173-L182); [George, NeurIPS 2020](../references.bib#L167-L171)) require structured metadata tables and cannot penetrate the intermediate representations of vision-language foundation models.

---

## Proposal 5: AutoCurriculum-VLA — Self-Critiquing Policy Introspection for Targeted Counterfactual Edge-Case Discovery

### 1. Target Venue & Track
- **Primary Venue**: *International Conference on Learning Representations (ICLR 2027)*.
- **Secondary Venue**: *Conference on Robot Learning (CoRL 2026/2027)*.

### 2. TL;DR Pitch
> **"AutoCurriculum-VLA converts passive failure logging into an active self-critiquing agent: during policy rollouts, an introspective monitor detects spikes in internal epistemic uncertainty and triggers an adversarial LLM scenario agent to apply minimal counterfactual perturbations, systematically mapping the multidimensional decision boundary of policy failure."**
- **Input**: Live simulation rollouts in CARLA / MetaDrive.
- **Novel Mechanism**: Internal epistemic uncertainty monitoring (activation entropy) + real-time adversarial LLM scene mutation.
- **Output**: An automated, self-evolving curriculum of counterfactual edge cases mapped directly to policy failure frontiers.
- **Advantage**: Discovers safety-critical failure boundaries 100× faster than random rollout data collection.

### 3. Exigence (Why Now?)
Real-world robotic deployment cannot afford to wait for passive failures to occur during operational hours. Autonomous systems require proactive red-teaming that actively hunts for the exact boundary conditions where the policy's confidence collapses before commercial release.

### 4. Specific Literature Gaps Addressed
1. **Passive Test-Time Guardrails**:  
   Works like [RoboMonkey (IROS 2025)](../references.bib#L50-L56) and [RoVer (IEEE T-IV 2025)](../references.bib#L58-L63) deploy runtime monitors to trigger safe emergency stops. While useful for operation, they do not feed discoveries back into an automated training curriculum.
2. **Adversarial Probing without Counterfactual Realism**:  
   [ReasonBreak (NeurIPS 2025)](../references.bib#L29-L35) probes reasoning chain breakages, but uses unconstrained gradient perturbations (adversarial pixel noise) that do not correspond to physically realizable driving scenarios. AutoCurriculum-VLA uses semantic LLM perturbations (e.g. shifting pedestrian timing, modifying headlight glare).

---

## Summary of Catherine's 3 Mandatory Baselines

Every proposal above evaluates its discovery capability against the three non-negotiable baselines:
1. **Baseline 1 (Random Selection)**: Uniform random sampling of data slices or candidate questions.
2. **Baseline 2 (Predefined Human Taxonomy)**: Standard heuristic categorization (e.g., Weather $\times$ Lighting $\times$ Maneuver).
3. **Baseline 3 (Behavioral / Output-Only Clustering)**: Clustering scenario failures based solely on output trajectory loss, action deviations, or collision telemetry—**without looking at internal activations**.
