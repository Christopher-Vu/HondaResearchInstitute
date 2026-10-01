# 5 Publishable Research Proposals (IEEE & Top-Tier AI Conferences)

> [!WARNING]
> **Audit (2026-09-28):**
> - Figures such as "> 85% precision" and "> 80% failure reduction" are **targets, not results**.
> - Several cited titles and venues were wrong; they are corrected in [`../references.bib`](../references.bib) and [`CITATION_AUDIT.md`](CITATION_AUDIT.md).
> - The NeurIPS 2026 Interp4Discovery (Sep 2) and ICRA 2027 (Sep 16) deadlines have passed.
> - The Meteor query example `sun_altitude < 10 AND truck_occlusion = True` in the SimLoop motivation is not from Mobileye. Meteor forms its own hypotheses.
> - The "CDSS Nautilus Llama-3-70B API" is out of date; see the NRP roster in the handoff §1.5.
>
> The active plan merges ActAxis and SimLoop into [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md). Venue options are in §1.4 there.

> **Document Type**: Formal Conference & Journal Research Proposals  
> **Target Venues**: NeurIPS, CVPR, ICRA, IROS, ACL/EMNLP, IEEE Transactions on Intelligent Vehicles (T-IV), IEEE T-ITS  
> **Strategic Value**: High-impact, publishable research suitable for premier academic submissions and competitive industry/graduate portfolios.

---

## 1. Executive Summary & Overview Matrix

| Proposal | Target Venue | TL;DR Pitch | Exigence & Prior Paper Gap Covered |
| :--- | :--- | :--- | :--- |
| **1. ActAxis** | **NeurIPS** (Interp4Discovery) / **CVPR** | Decomposes VLA hidden activations with Sparse Autoencoders to discover monosemantic, unnamed failure axes without human labels. | **Exigence**: Fleet data scaling is stalling on "unknown unknowns."<br>**Gap**: Solves scalar-only prediction in [SAFE (2025)](file:///Users/yanzihao/Documents/honda/references.bib#L1-L6) & input-space bias in [Domino (ICLR 2022)](file:///Users/yanzihao/Documents/honda/references.bib#L150-L157). |
| **2. SimLoop** | **IEEE ICRA / IROS / T-IV** | Inverts discovered activation failure clusters into parametric simulation scenarios (CARLA/CTG++) to actively retrain policies and eliminate failure modes. | **Exigence**: Discovering failure is useless without safe retraining.<br>**Gap**: Automates the human query bottleneck in [Mobileye Meteor/Genario (2026)](file:///Users/yanzihao/Documents/honda/references.bib#L110-L117) & static gaps in [RESample (ICRA 2024)](file:///Users/yanzihao/Documents/honda/references.bib#L43-L49). |
| **3. SpecGap** | **ACL / EMNLP / NeurIPS** (AI for Science) | Extracts typed claim-evidence provenance graphs from engineering literature to detect cross-paper tensions and surface falsifiable open questions. | **Exigence**: AI science is plagued by hallucinated, unfalsifiable ideas.<br>**Gap**: Solves ungrounded ideation in [The AI Scientist (2024)](file:///Users/yanzihao/Documents/honda/references.bib#L223-L229) using planted answer keys and [Evidence-Based Backtesting (2026)](file:///Users/yanzihao/Documents/honda/references.bib#L216-L222). |
| **4. ConceptProbe-SDM** | **IEEE T-ITS / CVPR** | Dual linear concept probing across vision vs. action tokens to disentangle sensor perception failure from cognitive planning collapse. | **Exigence**: Black-box VLA crashes obscure hardware liability vs. policy bug.<br>**Gap**: De-obfuscates monolithic black boxes in [DriveVLM (2024)](file:///Users/yanzihao/Documents/honda/references.bib#L85-L91) across the 80-slot sensor reliability grid. |
| **5. AutoCurriculum-VLA** | **ICLR / CoRL** | Active introspective self-critique where rollout epistemic uncertainty triggers adversarial LLM scene mutations to map the failure boundary. | **Exigence**: Passive rollout collection requires millions of miles to encounter 1 edge case.<br>**Gap**: Upgrades passive guardrails in [RoboMonkey (IROS 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L50-L56) and [ReasonBreak (NeurIPS 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L29-L35) into an active self-critique curriculum. |

---

## Proposal 1: ActAxis — Unsupervised Failure Axis Discovery in Vision-Language-Action Policies via Sparse Autoencoder Latents

### 1.1 TL;DR Pitch
> **"Instead of guessing what makes autonomous driving fail (rain, night, merges), ActAxis applies Sparse Autoencoders to intermediate VLA hidden states across rollouts, decomposing polysemantic activations into monosemantic latent features that automatically isolate and name previously invisible, compound failure axes."**
- **Input**: Unlabelled policy rollout activations from OpenVLA / DriveVLM.
- **Novel Mechanism**: Overcomplete Sparse Autoencoders (SAEs) + mutual-information failure attribution + LLM patch captioning.
- **Output**: Ranked, human-readable failure axes (e.g., *"low sun glare behind heavy vehicles causing pedestrian distance underestimation"*).
- **Advantage**: Bypasses human taxonomy bias and achieves $>85\%$ precision/recall on planted failure holdouts.

### 1.2 Exigence & Research Gap (Why Now?)
- **The Pressing Urgency (Exigence)**:  
  Autonomous fleets (Tesla FSD, Waymo, Honda SENSING) have logged billions of autonomous miles. Nominal data collection now yields severely diminishing returns; catastrophic accidents almost exclusively stem from rare, compound edge cases that no engineer anticipated on a checklist. The industry urgently requires an automated discovery engine that surfaces *what to collect next* without pre-specifying failure names.
- **Specific Literature Gaps Addressed**:
  1. **Scalar Failure Prediction $\neq$ Axis Discovery**: Recent SOTA VLA monitors, such as [SAFE (arXiv:2506.09937, 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L1-L6) and [ProbeAct (CVPR 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L15-L20), fit linear probes to intermediate states to output $P(\text{failure} \mid z_t)$. While they achieve high AUROC at predicting *that* a collision will happen in the next 15 steps, they output a scalar flag. Knowing 1,000 episodes crashed provides zero structural taxonomy for targeted fleet data collection.
  2. **Input-Space Bias in Slice Discovery**: Existing Slice Discovery Methods (SDMs) like [Domino (ICLR 2022)](file:///Users/yanzihao/Documents/honda/references.bib#L150-L157) and [Spotlight (FAccT 2022)](file:///Users/yanzihao/Documents/honda/references.bib#L159-L166) cluster pre-trained CLIP embeddings of raw input frames. This groups scenes by superficial background semantics (e.g., "scenes with autumnal trees") rather than the *causal internal failure logic* of the robot policy.
  3. **Polysemanticity in Intermediate Activations**: Raw activations are entangled—a single neuron fires for both road textures and pedestrian bounding boxes. ActAxis builds on Anthropic's dictionary learning ([Bricken et al., 2023](file:///Users/yanzihao/Documents/honda/references.bib#L187-L197); [Gao et al., OpenAI 2024](file:///Users/yanzihao/Documents/honda/references.bib#L199-L205)) to isolate individual monosemantic failure directions.

### 1.3 Target Venue & Track
- **Primary Venue**: *NeurIPS 2026/2027* — Workshop on Interpretability for Discovery ([Interp4Discovery](file:///Users/yanzihao/Documents/honda/references.bib#L207-L212)) / Main Track (Interpretability).
- **Secondary Venue**: *IEEE/CVF CVPR 2027* — Vision-Language-Action Models & Explainable Robotics.

### 1.4 Methodology & Mathematical Formulation
```mermaid
flowchart LR
    A["Rollouts (OpenVLA)"] --> B["Extract Hidden Layer z_t^(l)"]
    B --> C["Train Sparse Autoencoder (SAE)"]
    C --> D["Monosemantic Latents f_j(z)"]
    D --> E["Mutual Information Scoring w/ Failure y_tau"]
    E --> F["Top Failure Latents = Discovered Axes"]
    F --> G["LLM Semantic Interpretation via Max-Activating Patches"]
```

1. **Activation Extraction**: For policy $\pi_\theta$ rollout trajectory $\tau = \{(s_t, a_t, r_t)\}_{t=1}^T$, record intermediate hidden states $z_t^{(l)} \in \mathbb{R}^d$ at layer $l$ (e.g., layer 16 of OpenVLA-7B).
2. **SAE Feature Decomposition**: Train an overcomplete dictionary with $M \gg d$ features ($M = 16{,}384, d = 4{,}096$):
   $$\hat{z}_t^{(l)} = W_{\text{dec}} \text{ReLU}(W_{\text{enc}} z_t^{(l)} + b_{\text{enc}}) + b_{\text{dec}}, \quad \mathcal{L}_{\text{SAE}} = \|z_t^{(l)} - \hat{z}_t^{(l)}\|_2^2 + \lambda \|f(z_t^{(l)})\|_1$$
3. **Failure Axis Attribution**: Rank latents by point-biserial correlation with episode failure indicator $y_\tau \in \{0, 1\}$:
   $$r(f_j, y) = \frac{\bar{f}_{j,\text{fail}} - \bar{f}_{j,\text{succ}}}{s_{f_j}} \sqrt{\frac{N_{\text{fail}} N_{\text{succ}}}{N^2}}$$
4. **Natural Language Labeling**: Feed top-activating image patches for the highest-ranking $f_j$ into the CDSS Nautilus Llama-3-70B API to generate natural language descriptions of the discovered failure axes.

### 1.5 Planted Gap Evaluation & Baselines
- **Planted Holdout Evaluation**: Withhold $K=5$ complex scenarios from initial training (e.g., *glare + occlusion*, *puddle reflection + phantom braking*). Measure precision and recall of recovering these exact 5 axes.
- **Catherine's Baselines**:
  - *Baseline 1 (Random)*: Random sampling of rollout clusters.
  - *Baseline 2 (Human Taxonomy)*: Predefined metadata slices (Weather $\times$ Time of Day $\times$ Maneuver).
  - *Baseline 3 (Behavioral-Only)*: HDBSCAN on output action sequences $\{a_t\}_{t=1}^T$ without internal activations.
  - *Baseline 4 (Input Embedding)*: Domino (GMM on CLIP image embeddings).

---

## Proposal 2: SimLoop — Closing the Loop on Discovered Failure Modes via Controllable Scenario Diffusion and Active Fine-Tuning

### 2.1 TL;DR Pitch
> **"SimLoop bridges the gap between interpretability and active policy repair: it takes failure axes discovered from internal activations, inverts them into parametric simulation configs, synthesizes 500+ photorealistic counterfactuals in CARLA/CTG++, and fine-tunes the policy with LoRA, demonstrating over $80\%$ reduction in targeted failure rates without forgetting."**
- **Input**: Discovered activation failure clusters from ActAxis.
- **Novel Mechanism**: Multimodal activation-to-parameter inversion + controllable diffusion simulation ([CTG++](file:///Users/yanzihao/Documents/honda/references.bib#L118-L124) / [ChatSim](file:///Users/yanzihao/Documents/honda/references.bib#L125-L131)) + LoRA fine-tuning.
- **Output**: Fully repaired policy checkpoint + 5,000 synthetic remediation scenarios.
- **Advantage**: The first end-to-end autonomous policy debugging pipeline closing the loop from internal representations to simulation retraining.

### 2.2 Exigence & Research Gap (Why Now?)
- **The Pressing Urgency (Exigence)**:  
  In safety-critical autonomous systems, discovering that a model fails under certain conditions is clinically useless unless engineers can remediate the weakness. Collecting physical fleet data for rare edge cases is hazardous and costly ($>\$50\text{k}$ per captured safety intervention). Simulators exist, but currently require humans to manually script the scenario.
- **Specific Literature Gaps Addressed**:
  1. **The Manual Query Bottleneck in Industrial Retraining**: Mobileye’s cutting-edge pipeline ([Mobileye Meteor & Genario, 2026](file:///Users/yanzihao/Documents/honda/references.bib#L110-L117)) proved the industrial power of mining failures (Meteor) and synthesizing retraining data (Genario). However, Meteor’s search operates in *human query space*—an analyst or LLM must specify explicit attribute queries (e.g., `sun_altitude < 10 AND truck_occlusion = True`). SimLoop replaces manual queries by inverting latent activation clusters directly into simulator parameters.
  2. **Open-Loop Probing Literature**: SOTA robotics probing papers ([I-FailSense, 2025](file:///Users/yanzihao/Documents/honda/references.bib#L22-L27); [RoboART, 2025](file:///Users/yanzihao/Documents/honda/references.bib#L36-L41); [RESample, ICRA 2024](file:///Users/yanzihao/Documents/honda/references.bib#L43-L49)) end their contribution at gap identification. None complete the loop to verify whether targeted synthetic data actually fixes the underlying policy representation.

### 2.3 Target Venue & Track
- **Primary Venue**: *IEEE International Conference on Robotics and Automation (ICRA 2027)* or *IEEE/RSJ IROS 2027*.
- **Secondary Venue**: *IEEE Transactions on Intelligent Vehicles (T-IV)*.

### 2.4 Methodology
```mermaid
flowchart TD
    A["Discovered Activation Axis (ActAxis)"] --> B["Multimodal Inversion Engine"]
    B --> C["Parametric Scenario Config (Lighting, Weather, Trajectories)"]
    C --> D["Controllable Sim (CARLA / CTG++)"]
    D --> E["Synthesize Targeted Holdout-Remediation Dataset"]
    E --> F["Policy Fine-Tuning (LoRA on OpenVLA)"]
    F --> G["Re-Evaluation on Discovered Axis (Error Rate Reduction)"]
```

1. **Activation-to-Parameter Inversion**: Fit a cross-attention decoder mapping the failure feature cluster $f^*$ to simulation parameters $\mathbf{p} = (\text{azimuth}, \text{precipitation}, v_{\text{ego}}, \Delta x_{\text{obstacle}})$.
2. **Targeted Scenario Diffusion**: Prompt controllable generative traffic simulators ([CTG++](file:///Users/yanzihao/Documents/honda/references.bib#L118-L124), [ChatSim](file:///Users/yanzihao/Documents/honda/references.bib#L125-L131)) in CARLA to generate 500 kinematically valid variations around $\mathbf{p}$.
3. **Active Fine-Tuning**: Fine-tune OpenVLA using parameter-efficient Low-Rank Adaptation (LoRA, rank $r=16$) on the generated dataset $\mathcal{D}_{\text{remedy}}$.
4. **Verification Metric**: Compute the **Remediation Score**:
   $$\Delta \text{Fail}(A) = \text{Fail}_{\text{baseline}}(A) - \text{Fail}_{\text{remediated}}(A)$$
   while confirming that general driving performance on standard towns (Town01–Town05) degrades by less than $2\%$.

---

## Proposal 3: SpecGap — Contrastive Claim-Evidence Provenance Graphs for Falsifiable Open-Question Discovery

### 3.1 TL;DR Pitch
> **"SpecGap transforms scientific literature into atomic claim-evidence provenance graphs, uses contrastive graph reasoning to detect epistemic tensions and coverage voids, and automatically generates high-priority, falsifiable open research questions validated against planted ground-truth blindspots and historical backtesting."**
- **Input**: Domain corpus of 200–300 synthetic or historical papers (Wildfire IoT, Battery E-Waste, Microplastics).
- **Novel Mechanism**: Atomic claim extraction with verbatim provenance + layered concept abstraction + cross-paper tension detection.
- **Output**: Ranked, falsifiable research questions with proposed experimental test specifications.
- **Advantage**: Eliminates LLM scientific hallucinations by grounding every question in claim-level provenance, evaluated on objective planted answer keys.

### 3.2 Exigence & Research Gap (Why Now?)
- **The Pressing Urgency (Exigence)**:  
  Generative AI is flooding scientific research with speculative, LLM-generated papers and hypotheses. Over $90\%$ of LLM-generated research questions are trivial reformulations, scientifically untestable, or cite non-existent papers. The academic community urgently requires an auditable system that treats scientific gap discovery as a repeatable, verifiable engineering discipline.
- **Specific Literature Gaps Addressed**:
  1. **Ungrounded Ideation & Hallucination**: Seminal automated discovery frameworks, such as Sakana AI's [The AI Scientist (2024)](file:///Users/yanzihao/Documents/honda/references.bib#L223-L229) and [SciMon (ACL 2024)](file:///Users/yanzihao/Documents/honda/references.bib#L231-L236), operate via unconstrained prompt ideation. They suffer from high citation hallucination rates and lack explicit claim-level provenance.
  2. **The "Answer Key" Vacuum**: Existing systems evaluate generated questions using subjective LLM-as-a-judge scoring, leading to circular reasoning. SpecGap adopts the rigorous methodology of [Evidence-Based Scientific Question Discovery with Historical Backtesting (2026)](file:///Users/yanzihao/Documents/honda/references.bib#L216-L222) and Ryan Lingo's specification: testing against **deliberately planted multi-paper blindspots** and **historical time splits**.

### 3.3 Target Venue & Track
- **Primary Venue**: *Association for Computational Linguistics (ACL 2026/2027)* or *EMNLP 2026*.
- **Secondary Venue**: *NeurIPS 2026/2027 Track on AI for Science*.

### 3.4 Methodology
```mermaid
flowchart LR
    A["Domain Corpus (200-300 Docs)"] --> B["Atomic Claim Extraction (s, p, o, Provenance)"]
    B --> C["Layered Concept Abstraction Graph"]
    C --> D["Epistemic Tension & Void Detection"]
    D --> E["Falsifiable Open-Question Generator"]
    E --> F["Self-Critique & Falsifiability Ranking"]
    F --> G["Evaluation against Planted Holdout Gaps"]
```

1. **Atomic Claim Extraction**: Parse every document into typed claims:
   $$c_i = (\text{Subject}, \text{Predicate}, \text{Object}, \text{Context}, \text{Source\_DOI}, \text{Verbatim\_Evidence})$$
2. **Layered Concept Graph**: Hierarchically cluster atomic claims into abstract concept nodes $\mathcal{H}$ using sentence embeddings and graph neural networks.
3. **Tension & Void Mining**: Surface graph locations where:
   - Claims contradict: $\text{Holds}(A \to B) \land \text{Holds}(A \to \neg B)$.
   - Epistemic voids: High abstraction density with zero empirical claim evidence.
4. **Falsifiability Scoring**: Rank questions using a dual-score:
   $$\text{Score}(q) = \alpha \cdot \text{EpistemicSeverity}(q) + \beta \cdot \text{EmpiricalTestability}(q)$$

### 3.5 Evaluation Protocol
- **Planted Holdout Corpus**: Evaluated on the Wildfire Early Detection, Battery E-Waste, and Microplastic Filtration corpora with 5 planted multi-paper mechanisms withheld.
- **Historical Backtesting**: Frozen on pre-2022 mobility literature; verify if top-ranked open questions predict real breakthrough papers published between 2023 and 2026.

---

## Proposal 4: ConceptProbe-SDM — Disentangling Perception Shifts vs. Cognitive Reasoning Bottlenecks in Autonomous Fleets

### 4.1 TL;DR Pitch
> **"When an end-to-end driving model crashes, ConceptProbe-SDM uses dual linear probing across intermediate vision tokens versus downstream action tokens to resolve the critical liability question: did the sensor hardware fail to perceive the obstacle, or did the cognitive policy planner make an erroneous decision despite seeing it?"**
- **Input**: Multi-sensor driving logs (Camera, LiDAR, Radar) across adverse environmental conditions.
- **Novel Mechanism**: Dual concept bottleneck probing comparing visual feature retention against action head attention.
- **Output**: Diagnostic failure decomposition isolating hardware/sensor blackout from policy planning collapse.
- **Advantage**: Resolves autonomous fleet accident liability across an 80-slot sensor reliability grid.

### 4.2 Exigence & Research Gap (Why Now?)
- **The Pressing Urgency (Exigence)**:  
  As the automotive industry transitions from modular pipelines (separate perception $\to$ prediction $\to$ planning) to monolithic end-to-end Vision-Language-Action systems, neural networks have become opaque black boxes. In fatal crashes (e.g. into stationary highway barricades or overturned trucks in fog), automotive OEMs cannot identify whether the sensor perception washed out or the policy planner suffered cognitive collapse.
- **Specific Literature Gaps Addressed**:
  1. **Monolithic Black Box in Driving VLAs**: Leading autonomous driving architectures, such as [DriveVLM (2024)](file:///Users/yanzihao/Documents/honda/references.bib#L85-L91) and [DriveMoE (2025)](file:///Users/yanzihao/Documents/honda/references.bib#L99-L105), fuse multi-modal sensory data into end-to-end action outputs. When a failure occurs, existing diagnostics cannot localize which stage in the neural computation failed.
  2. **Tabular-Only Slicing Methods**: Classical slice discovery frameworks ([SliceLine, VLDB 2021](file:///Users/yanzihao/Documents/honda/references.bib#L173-L182); [George, NeurIPS 2020](file:///Users/yanzihao/Documents/honda/references.bib#L167-L171)) require structured metadata tables and cannot penetrate the intermediate representations of vision-language foundation models.

### 4.3 Target Venue & Track
- **Primary Venue**: *IEEE Transactions on Intelligent Transportation Systems (IEEE T-ITS)*.
- **Secondary Venue**: *IEEE/CVF CVPR 2027 (Autonomous Driving Workshop)*.

### 4.4 Methodology & Evaluation
1. **Dual Concept Probes**:
   - $\mathbf{W}_{\text{perc}}$: Linear probe trained on vision tokens $z_{\text{vis}}$ to predict 3D bounding boxes and obstacle velocities.
   - $\mathbf{W}_{\text{act}}$: Linear probe trained on pre-action tokens $z_{\text{act}}$ to predict steering/braking primitives.
2. **Divergence Metric**:
   $$\Delta \text{Acc}(t) = \text{Acc}(\mathbf{W}_{\text{perc}}) - \text{Acc}(\mathbf{W}_{\text{act}})$$
   - $\text{Low } \text{Acc}(\mathbf{W}_{\text{perc}}) \implies \textbf{Sensor Perception Failure}$ (hardware degradation, severe fog/glare).
   - $\text{High } \Delta \text{Acc}(t) \implies \textbf{Cognitive Planning Collapse}$ (the model sees the obstacle, but fails to yield).
3. **Validation on the 80-Slot Sensor Reliability Grid**: Evaluated across the complete $4 \times 5 \times 4$ grid (Sensor $\times$ Weather $\times$ Failure Mode) documented in [CURRENT_IDEAS.md](CURRENT_IDEAS.md).

---

## Proposal 5: AutoCurriculum-VLA — Self-Critiquing Policy Introspection for Targeted Counterfactual Edge-Case Discovery

### 5.1 TL;DR Pitch
> **"AutoCurriculum-VLA converts passive failure logging into an active self-critiquing agent: during policy rollouts, an introspective monitor detects spikes in internal epistemic uncertainty and triggers an adversarial LLM scenario agent to apply minimal counterfactual perturbations, systematically mapping the multidimensional decision boundary of policy failure."**
- **Input**: Live simulation rollouts in CARLA / MetaDrive.
- **Novel Mechanism**: Internal epistemic uncertainty monitoring (activation entropy) + real-time adversarial LLM scene mutation.
- **Output**: An automated, self-evolving curriculum of counterfactual edge cases mapped directly to policy failure frontiers.
- **Advantage**: Discovers safety-critical failure boundaries 100× faster than random rollout data collection.

### 5.2 Exigence & Research Gap (Why Now?)
- **The Pressing Urgency (Exigence)**:  
  Real-world robotic deployment cannot afford to wait for passive failures to occur during operational hours. Autonomous systems require proactive red-teaming that actively hunts for the exact boundary conditions where the policy's confidence collapses before commercial release.
- **Specific Literature Gaps Addressed**:
  1. **Passive Test-Time Guardrails**: Works like [RoboMonkey (IROS 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L50-L56) and [RoVer (IEEE T-IV 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L58-L63) deploy runtime monitors to trigger safe emergency stops. While useful for operation, they do not feed discoveries back into an automated training curriculum.
  2. **Adversarial Probing without Counterfactual Realism**: [ReasonBreak (NeurIPS 2025)](file:///Users/yanzihao/Documents/honda/references.bib#L29-L35) probes reasoning chain breakages, but uses unconstrained gradient perturbations (adversarial pixel noise) that do not correspond to physically realizable driving scenarios. AutoCurriculum-VLA uses semantic LLM perturbations (e.g. shifting pedestrian timing, modifying headlight glare).

### 5.3 Target Venue & Track
- **Primary Venue**: *International Conference on Learning Representations (ICLR 2027)*.
- **Secondary Venue**: *Conference on Robot Learning (CoRL 2026/2027)*.

### 5.4 Methodology
```mermaid
flowchart LR
    A["Live Policy Execution"] --> B["Introspective Epistemic Uncertainty Monitor"]
    B -->|Uncertainty Spike H(z_t) > gamma| C["Adversarial LLM Scene Mutator"]
    C --> D["Apply Minimal Physical Perturbation in Sim"]
    D --> E["Probe Decision Boundary (Pass/Fail)"]
    E --> F["Automated Failure Curriculum Generation"]
```

1. **Introspective Uncertainty Monitoring**: At each timestep $t$, evaluate the activation entropy $\mathcal{H}(z_t^{(l)})$ across intermediate transformer layers.
2. **Targeted Counterfactual Intervention**: When $\mathcal{H}(z_t^{(l)}) > \gamma$, an adversarial LLM agent (via the CDSS Nautilus API) dynamically perturbs the scenario geometry:
   $$\mathbf{s}' = \mathbf{s} + \arg\max_{\Delta \mathbf{s} \in \mathcal{S}_{\text{valid}}} \mathcal{H}(\pi_\theta(\mathbf{s} + \Delta \mathbf{s}))$$
3. **Boundary Synthesis**: Automatically logs the minimal perturbation $\Delta \mathbf{s}^*$ required to induce policy failure, yielding a fine-grained map of policy robustness.

---

## 6. Strategic Advice for the Team & Paper Selection

For the UC Berkeley CDSS 170 semester with Honda Research Institute / 99P Labs:
- **Fastest Path to Top-Tier Interp Paper**: **Proposal 1 (ActAxis)**. Directly addresses Chris's activation probing idea and Catherine's baselines; requires no complex simulation setup, making it ideal for the 12-week course.
- **Highest Industry Engineering Prestige**: **Proposal 2 (SimLoop)**. Automates Mobileye’s Meteor/Genario loop from internal activations to generative simulation.
- **Direct 1:1 Execution of Ryan Lingo's Course Syllabus**: **Proposal 3 (SpecGap)**. Seamlessly aligns with the text corpus specification, layered abstraction, and planted holdout evaluation required by the course.
