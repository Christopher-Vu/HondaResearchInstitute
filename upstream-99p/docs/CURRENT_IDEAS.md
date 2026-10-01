# Current Ideas & Brainstorming Synthesis

> **Status**: Living Working Document  
> **Origin**: Synthesized from team discussions (Jerry Yan, Chris, Catherine Wang, Hiram Lannes, Jason) and CDSS 170 / Honda Research Institute collaboration.

---

## 1. The Foundational Prompt & Conceptual Questions

The project originated from an open-ended challenge posed by Ryan Lingo (99P Labs / Honda Research Institute):

> *"How might we build a knowledge system that develops layered abstractions, tests and critiques its own understanding, and identifies the open questions and knowledge gaps most worth investigating?"*

### Core Conceptual Explorations:
1. **Short-Answer to Multiple-Choice Transformation**: How can an AI system automatically formulate diagnostic multiple-choice probes to test its own understanding? If an LLM or policy cannot discriminate between a true physical mechanism and subtle distractor mechanisms, an epistemic gap is surfaced.
2. **Latent Knowledge vs. Retrieval Failure**: Investigating the phenomenon where *"there are things the system knows internally, but cannot retrieve or express in output space."* In robotics, this mirrors a policy whose internal activations encode an obstacle or risk, yet the action head still commands a collision course.
3. **Persistent Memory & Cumulative Self-Critique**: Moving beyond single-session prompts toward a system that maintains a persistent knowledge graph or activation archive, iteratively refining its map of unknown regions over time.

---

## 2. Brainstormed Application Domains (Track A: Synthetic Text Corpora)

To enable rigorous evaluation, the team brainstormed three societal domains where a synthetic corpus (200–300 documents) could be constructed with **deliberately planted knowledge gaps** acting as an objective ground-truth answer key:

### Domain 1: Climate Resilience — Wildfire Prevention & Early Detection
- **The Real-World Goal**: Accelerate research on preventing catastrophic wildfires before runaway propagation.
- **The Corpus (200–300 docs)**: Synthetic research notes covering IoT temperature sensors, satellite infrared imaging, and drone inspection routes for power lines.
- **The Planted Gap**: Cover physical monitoring technologies exhaustively, but deliberately omit AI micro-climate prediction (e.g., how sudden valley wind shifts affect ember transport).
- **Evaluation**: The system must synthesize the monitoring literature, critique its own predictive power, and propose: *"How do local micro-climate wind shifts affect ember spread in sensor-monitored valleys?"*

### Domain 2: Sustainable Cities — Micro-Mobility & E-Waste Recycling
- **The Real-World Goal**: Develop localized urban recycling for e-scooter and EV battery packs without toxic hydrometallurgical processing.
- **The Corpus (200–300 docs)**: Synthetic briefs on hydrometallurgical recycling, battery disassembly automation, and municipal collection logistics.
- **The Planted Gap**: Exhaustively cover chemical extraction steps for cobalt/nickel, but intentionally omit safety handling mechanisms for damaged or swollen lithium cells during automated robotic disassembly.
- **Evaluation**: The system flags that the automated disassembly workflow lacks protocols for thermal runaway in compromised cells.

### Domain 3: Public Health — Microplastic Filtration in Local Water Systems
- **The Real-World Goal**: Identify critical gaps in low-cost municipal water purification for emerging microscopic contaminants.
- **The Corpus (200–300 docs)**: Synthetic papers on bio-based membrane filters, sand filtration, and chemical coagulants.
- **The Planted Gap**: Cover standard macro-pollutant and microplastic removal, but omit nanoplastic polymer degradation under seasonal water temperature fluctuations.
- **Evaluation**: The system proposes investigating polymer degradation dynamics across freeze-thaw municipal cycles.

---

## 3. Structured Matrix Domains (Discrete Evaluation Grids)

To eliminate ambiguity and allow exact precision/recall calculation, the team explored domains that naturally factor into a discrete multidimensional grid:

### Vehicle Domain: Perception Sensor Reliability Grid
- **Dimension 1 (Sensor Type, 4)**: Camera, LiDAR, Radar, Ultrasonic.
- **Dimension 2 (Environmental Condition, 5)**: Fog, Direct Glare, Heavy Rain, Snow, Night.
- **Dimension 3 (Failure Mode, 4)**: Sensor Dropout, False Positive Phantom Braking, Range Degradation, Calibration Drift.
- **Total State Space**: $4 \times 5 \times 4 = 80$ discrete slots.
- **The Planted Gap**: Deliberately withhold data for specific combinations that are rarely documented in isolation (e.g., *Ultrasonic × Heavy Rain × Calibration Drift* or *Radar × Snow × False Positive*). If the discovery engine reconstructs the grid and flags the missing cells, recall is $100\%$.

### Fictional Regulatory Domains
- **Building Code Compliance**: Occupancy Type (Assembly, Residential, Industrial) $\times$ Building System (Egress, Fire Suppression, Ventilation, Structural) $\times$ Requirement Category.
- **Fictional Payments Regulation**: 5 License Classes $\times$ 6 Transaction Types $\times$ 5 Obligation Categories (Capital, Reporting, Consumer Disclosure, Data Residency, Settlement Timing). Documents mimic regulatory text, supervisory guidance, and enforcement actions.

---

## 4. Policy Failure Discovery in Robotics & Driving (Track B: Chris's Proposal)

Chris proposed pivoting the core discovery engine to **robotics and autonomous driving policies**, aligning directly with Honda Research Institute's mission:

### The Core Premise:
Standard autonomous driving development relies on human-authored checklists (rain, night, merges). When an end-to-end driving policy fails, collecting more data on arbitrary checklists yields diminishing returns.
Instead of relying on human hypotheses, **extract activations across policy rollouts, cluster the activation space without supervision, and discover the true underlying failure axes.**

### Closing the Loop:
1. Discover an activation cluster corresponding to high failure rates.
2. Translate that cluster into simulator scenario parameters (in CARLA or MetaDrive).
3. Synthesize targeted training variations and fine-tune the policy.
4. Verify whether the policy failure rate on that axis drops to zero.

---

## 5. Team Critique & Essential Methodological Requirements

During group deliberations, **Catherine Wang** raised critical points that define the scientific rigor of our experiments:

### Point 1: Operationalizing "What Counts as a Gap"
- *Question*: Is a discovered gap an activation cluster associated with high loss / collision rates, or is it an underrepresented density void in training representation space?
- *Resolution*: We distinguish between:
  1. **Performance Failure Axes**: Clusters with high policy intervention/collision rates.
  2. **Epistemic Representation Gaps**: High-entropy or low-density activation regions where the policy exhibits high epistemic uncertainty.

### Point 2: The Three Mandatory Baselines
To demonstrate that policy activations provide genuine scientific value over existing approaches, our discovery engine **must** be benchmarked against:
1. **Baseline 1: Random Data Collection**: Uniformly sampling scenarios/questions from the parameter space.
2. **Baseline 2: Predefined Human Taxonomy / Slices**: Segmenting failures using standard manual metadata tags (e.g., weather = rain, time = night).
3. **Baseline 3: Behavioral / Output-Only Clustering**: Clustering scenarios based solely on output trajectory deviations, steering errors, or collision telemetry—**without looking at internal activations**.

*Catherine's Principle*: If activation-based clustering does not significantly outperform output-only clustering in precision/recall against planted gaps, internal representations add no value.

---

## 6. Available Computing Infrastructure

- **UC Berkeley CDSS Nautilus NRP LLM API**: Provides high-throughput API keys for running open-source large language models on the Nautilus Kubernetes GPU cluster (`https://ellm.nrp-nautilus.io/v1`).
- **Open-Source Robotic Models**: `OpenVLA` (7B parameter VLA based on Llama-2 backbone), accessible on campus compute nodes.
- **Simulation Platforms**: `CARLA 0.9.15`, `MetaDrive`, and `HighwayEnv` for policy evaluation and scenario generation.
