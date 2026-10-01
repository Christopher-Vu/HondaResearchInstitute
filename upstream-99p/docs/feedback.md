# Feedback & Strategic Upgrades: Project Brief for Driving VLA Failure Discovery

> [!NOTE]
> **Superseded in part (2026-09-28)** by [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md) (§0.2):
> - The "prototype on OpenVLA-7B / DriveVLM" call is replaced by SimLingo. DriveVLM has no public weights or code.
> - DRAMA is 17,785 **2-second Tokyo clips** selected by the driver's braking response. It is request-only and non-commercial, and not suitable for pre-training a CARLA policy.
> - The suggested Llama-3.2-Vision captioner is not served on NRP; use a pinned `qwen3` or `gemma` model (handoff D7).

> **To**: Chris  
> **From**: Jerry (`imhaohao@berkeley.edu`) & Team (Catherine, Hiram, Jason)  
> **Context**: Review of *Project Brief — Failure Axis Discovery in Driving VLAs* (CDSS 170 / Honda Research Institute)  
> **Target**: Submission-ready NeurIPS / CVPR / ICRA paper by December 2026.

---

## ⚡ Quick Take: Why This Brief is Great

Yo Chris, this project brief is exceptionally sharp. 

1. **Focus**: Cutting out the generic NLP/text domains (wildfire, e-waste) and locking in **100% on Driving VLAs** is 100% the right call. It keeps us from getting scattered and aligns directly with Honda/Ryan Lingo.
2. **The Target to Beat**: Picking **RoboART / Predictive Red Teaming (arXiv:2502.06575)** as our direct baseline is lethal. RoboART uses human-written factor checklists in manipulation; beating them with *unsupervised model-derived failure axes in driving* gives us an airtight paper narrative.
3. **Sealed Answer Key**: Having Workstream C hold the ground-truth key while Workstream D runs blind discovery guarantees academic credibility. No reviewer can claim we cherry-picked the results.
4. **Heavy-Duty Infra**: Mandating vLLM/Triton containerization and Ray rollout orchestration ensures we can actually run the thousands of rollouts needed for statistical significance.

Below is a quick diff of how our plan evolved from the initial scaffolding, followed by **6 high-IQ upgrades** we should bake in now so we don’t hit roadblocks in October/November.

---

## 🔄 The Diff: What Shifted

```
┌───────────────────────────────────────┐          ┌───────────────────────────────────────┐
│           EARLIER SCAFFOLDING         │          │          CHRIS'S BRIEF (NOW)          │
├───────────────────────────────────────┤          ├───────────────────────────────────────┤
│ • Split focus (Text NLP vs. Robotics) │  ════>   │ • 100% focused on Driving VLAs        │
│ • General Slicing (Domino, Spotlight) │  ════>   │ • Head-to-head target: Beat RoboART   │
│ • Vague planted gaps                  │  ════>   │ • 3-Tier gaps + Sealed Answer Key (C) │
│ • Ad-hoc Python scripts               │  ════>   │ • vLLM/Triton + Ray + SQL DB results  │
│ • Midterm check at Week 6             │  ════>   │ • Workstream A gates everything       │
└───────────────────────────────────────┘          └───────────────────────────────────────┘
```

---

## 🛠️ 6 Concrete Upgrades to Lock in the Paper

### 1. Automating the "Describability" Bottleneck (No Eyeball Inspection)
* **The Problem**: You noted that *"the axis must be describable. If nobody can look at the top-activating rollouts and name what they share, it isn't a discovery."*  
  If we rely on humans eyeballing video clips, reviewers at NeurIPS/CVPR will dismiss our results as qualitative cherry-picking. Plus, human inspection doesn't scale across 50+ SAE latent features.
* **The Upgrade**: **Automated Contrastive VLM Captioning**.
  * For any discovered failure feature $f_j$, take the top-10 failure rollouts where $f_j$ fired vs. top-10 success rollouts where $f_j \approx 0$.
  * Extract the spatial attention patches that activated $f_j$.
  * Prompt an open multimodal model (Llama-3.2-Vision via our Berkeley Nautilus API) with a contrastive prompt:  
    > *"What specific environmental condition, hazard kinematics, or occlusion pattern is uniquely present in Group A (failures) that is absent in Group B (successes)?"*
  * This makes describability **automated, reproducible, and verifiable**.

---

### 2. Settling the "Which VLA" Decision Right Now
* **The Problem**: Leaving "Which VLA" open slows down Workstream A (which gates everything).
* **The Recommendation**: **OpenVLA-7B** (fine-tuned on driving control) OR **DriveVLM**:
  * **OpenVLA-7B** ([Kim et al., 2024](https://arxiv.org/abs/2406.09246)): Built on a Llama-2 backbone, has native vLLM serving support, and works out-of-the-box with `sae_lens` for dictionary learning. We just rebind its action tokens to discrete speed and steering bins.
  * **DriveVLM** ([Tian et al., 2024](https://arxiv.org/abs/2402.12289)): Built specifically for driving with scene understanding, but requires custom Triton backends.
  * **Call**: Let's prototype on **OpenVLA-7B** first for fast bring-up.

---

### 3. Avoiding the Simulator Parameterization Trap
* **The Problem**: You noted: *"Binding constraint is that the scenario generator must be parameterizable along an arbitrary discovered axis. Not all are."*  
  Writing custom CARLA Python scripts for every newly discovered axis will kill our velocity in Workstream E.
* **The Upgrade**: **Standard JSON Schema + CTG++ / ScenarioRunner**.
  * Use a unified JSON schema for scenario generation:
    ```json
    {
      "ego_maneuver": "unprotected_left",
      "adversary": {"type": "cyclist", "occluder": "box_truck", "offset_dist": 4.2},
      "environment": {"solar_elevation": 12, "weather": "wet_cloudy"}
    }
    ```
  * When Workstream D outputs a failure axis description, an LLM converts that description into 500 randomized parameterizations of this JSON schema.
  * CARLA `ScenarioRunner` executes the batch in parallel over our Ray cluster. Zero manual scripting per axis.

---

### 4. Beating the "Perception Shortcut" Failure Mode
* **The Problem**: You astutely noted that holding out scenarios like "night rain" might separate cleanly for trivial pixel reasons rather than true policy struggle.  
  In transformers, early/mid layers represent lighting and weather far more strongly than subtle decision logic. If we run an SAE or clustering on raw activations, we will cluster *weather*, not *planning failures*.
* **The Upgrade**: **Action-Residual Orthogonalization**.
  * Split the hidden tokens into visual tokens $z_t^{\text{vision}}$ and action prediction tokens $z_t^{\text{action}}$.
  * Regress $z_t^{\text{action}}$ on $z_t^{\text{vision}}$ and compute the residual:
    $$r_t = z_t^{\text{action}} - \mathbf{W}_{\text{proj}} z_t^{\text{vision}}$$
  * Fit the SAE or clustering **exclusively on the residual $r_t$**.
  * This mathematically subtracts out superficial visual appearance (asphalt color, sky brightness, rain streaks) and isolates the pure decision-making computation!

---

### 5. Exact Math for Planted Gap Precision & Recall
* **The Problem**: Matching unsupervised clusters to our sealed planted gaps needs a formal metric that reviewers won't question.
* **The Upgrade**: **Hungarian Bipartite Matching on Mutual Information**.
  * Construct a cost matrix $C_{km} = \text{Jaccard}(g_k^*, \hat{a}_m)$ between planted gaps $g_k^*$ and discovered clusters $\hat{a}_m$.
  * Solve the global optimal matching via the Hungarian algorithm:
    $$\text{Recall} = \frac{1}{K} \sum_{k=1}^K \mathbb{I}[C_{k, \pi^*(k)} \ge 0.5], \quad \text{Precision} = \frac{\sum_{k=1}^K \mathbb{I}[C_{k, \pi^*(k)} \ge 0.5]}{M}$$
  * This gives us rock-solid numbers for the results table.

---

### 6. The Honda / Ryan Lingo Advantage: Anchor on DRAMA
* **The Secret Weapon**: Instead of training our baseline on random CARLA miles, let's pre-train/fine-tune on **[Honda's DRAMA Dataset](https://usa.honda-ri.com/drama) (WACV 2023)**:
  * Collected right at **Honda Research Institute** (Ryan Lingo's lab).
  * **17,785 interactive video clips** specifically filtered on **human risk interventions and sudden braking events** in urban traffic, complete with CAN bus steering/brake signals and natural language risk explanations.
  * Starting with DRAMA gives us instant credibility with Ryan, provides real-world grounding before running sim rollouts, and ensures our model already understands edge-case risks.

---

## 📋 Suggested Workstream Ownership & Next Steps

Based on our team skill sets:
- **Workstream A (Model & Sim Bring-up)**: Chris & Jerry — Gate 1: Get OpenVLA running in CARLA with published baseline scores.
- **Workstream B (Serving & Infra)**: Jerry & Jason — Set up Docker container (vLLM), Ray rollout workers, and SQLite/PostgreSQL results logging.
- **Workstream C (Planted Gaps & Sealed Key)**: Catherine — Design the 3 planted slices (1 enumerable, 1 interactional, 1 control), fine-tune the gapped model, hold the key sealed.
- **Workstream D (Discovery & Baselines)**: Chris, Hiram & Catherine — Implement Action-Residual SAE + build the 2 baselines (RoboART-style & Behavioral Stratification).
- **Workstream E (Generation Loop)**: Team fan-out — ScenarioRunner JSON generation $\to$ fine-tuning $\to$ measuring remediation $\Delta \text{Fail}$.

Let's discuss in our next sync, lock in the VLA choice, and start Workstream A!
