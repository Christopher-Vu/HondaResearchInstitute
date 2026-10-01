# Agent Guide: 99P Labs / Honda Workspace

> **Notice to Incoming Agents**: This document is the primary onboarding interface for autonomous agents and LLM assistants operating in this repository. Read this document first to understand the team context, operational rules, system architecture, and current task priorities.
>
> **Plan of record (updated 2026-09-28):** the Fall 2026 experimental design, role split, gates and venue plan are in [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md). Its §0.3 has a copy-paste prompt for orchestration agents, and §13 has the operating rules. Cite only works verified in [`CITATION_AUDIT.md`](CITATION_AUDIT.md). Where this guide conflicts with the handoff, the handoff wins.

---

## 1. Project Identity & Team Context

- **Course & Institution**: UC Berkeley CDSS 170 (Fall 2026) — Data Discovery Project.
- **Industry Partner**: [99P Labs](https://99plabs.com/) / **Honda Research Institute, US** (HRI-US).
- **Industry Mentor**: **Ryan Lingo** (Applied AI Research Engineer & Developer Advocate, 99P Labs / Honda Research Institute USA). He is not the student **team lead** (weekly planning; receives `MASTER_HANDOFF.md` §0.3 rule 7 escalations), who is named at G0 (Oct 2); see `MASTER_HANDOFF.md` O1.
- **Student Research Team**:
  - **Jerry Yan (Zihao Yan)** (`imhaohao@berkeley.edu`) — Research Investigator / Architecture & Repository Lead.
  - **Chris** — Failure Probing & Policy Scenarios.
  - **Catherine Wang** (`cattayw@berkeley.edu`) — Evaluation Metrics, Baseline Benchmarking & Rigor.
  - **Hiram Lannes** (`hiram_lannes@berkeley.edu`) — Mentoring Agreements, Pipeline Scaffolding & Integration.
  - **Jason** (`jhe08@berkeley.edu`) — Data Engineering & Holdout Design.
- **GitHub Repository**: `Imhaohao/99p`
- **Local Workspace Path**: `/Users/yanzihao/Documents/honda`

---

## 2. Executive Research Mission

> **Core Objective**: Build an AI system that develops layered abstractions over its domain, critiques its own internal representations, and discovers **unsupervised failure axes and open knowledge gaps** without requiring human engineers to pre-specify the taxonomy of failures in advance.

### The Dual-Track Formulation
The project bridges two complementary paradigms:
1. **Track A (Text Knowledge System - Course Spec)**:
   Extracts layered conceptual abstractions from a synthetic corpus, performs automated self-critique, and identifies high-priority open scientific questions evaluated against planted holdout gaps or historical backtesting.
2. **Track B (Robotics / Driving Policy Failure Discovery - Honda Interp Spec)**:
   Extracts internal activations and Sparse Autoencoder (SAE) latent features across policy rollouts (e.g., OpenVLA, trajectory planners) to discover previously unknown failure axes. Evaluated with planted data holdouts (precision/recall on discovered axes) and closed-loop sim-retraining (e.g., CARLA / MetaDrive).

**Fall 2026 scope:** the plan of record ([`MASTER_HANDOFF.md`](MASTER_HANDOFF.md)) covers Track B only, on SimLingo in CARLA 0.9.15 + Bench2Drive. OpenVLA and MetaDrive are references only (§4). Track A is not in the plan.

---

## 3. Repository Directory Structure

```
/Users/yanzihao/Documents/honda/
├── README.md                     # High-level overview and landing page for researchers
├── references.bib                # Standard BibTeX database of relevant literature
├── papers/                       # Primary paper PDFs and literature archive
│   ├── README.md                 # Loaded papers index and summaries
│   └── simlingo_2503.09594.pdf   # SimLingo (CVPR 2025) primary PDF
└── docs/
    ├── AGENT_GUIDE.md            # [THIS FILE] Operational handbook for autonomous agents
    ├── MASTER_HANDOFF.md         # PLAN OF RECORD: experimental design, roles, gates, venues, contacts, mentor asks
    ├── CITATION_AUDIT.md         # Verified citations/facts with evidence (2026-09-28)
    ├── DRIVING_VLA_LITERATURE_REVIEW.md # Corrected AutoVLA / Bench2Drive / closed-loop evaluation review
    ├── audit/verification-2026-09-28.jsonl # Full per-record evidence ledger behind CITATION_AUDIT.md
    ├── SIMLINGO_ANALYSIS.md      # Deep technical breakdown & tactical integration for SimLingo (CVPR 2025)
    ├── RESEARCH_PURPOSE.md       # Comprehensive problem formulation, motivation, and course requirements
    ├── LITERATURE_REVIEW.md      # Deep academic literature review, taxonomy, and research gap matrix
    ├── CURRENT_IDEAS.md          # Brainstormed application domains and baseline requirements
    ├── PUBLISHABLE_PROPOSALS.md  # 5 publication-ready conference proposals (NeurIPS, CVPR, ICRA, ACL)
    ├── refined proposals.md      # TL;DR pitches, exigence, and prior research gap mappings
    ├── PROJECT_BRIEF_DIFF_AND_IMPROVEMENTS.md # Diff report & tactical improvements on Chris's brief
    ├── feedback.md               # Peer review & strategic recommendations for Chris and team
    ├── FUTURE_PLANS.md           # 12-week semester roadmap, baseline specs, compute, and deliverables
    └── domain-candidates.md      # Initial exploratory notes on candidate grids (sensors, fictional laws)
```

---

## 4. Compute Resources & Tooling Environment

1. **NRP Nautilus (via the CDSS Data Discovery program)**:
   - **LLM gateway.** OpenAI-compatible endpoint `https://ellm.nrp-nautilus.io/v1`; an `/anthropic` path also exists.
     - Tokens are self-generated at nrp.ai/llmtoken after joining the course namespace.
     - As of Sep 2026 the roster includes vision-capable `qwen3`, `qwen3-small` and `gemma`. **The roster rotates.** Pin and log model IDs; the older "Llama-3-70B / Mistral" list is outdated.
   - **GPUs.**
     - Interactive pods are capped at 16 CPU / 32 GB / 6 h, so run rollouts as batch Jobs.
     - A6000/A40/L40 and similar can be requested freely. A100 needs a quota request. H100/H200 are not user-requestable.
   - **Other compute.** There is **no LBNL cluster called "Salvo"**; the name likely meant UC Berkeley **Savio**, which needs a faculty allowance. See `MASTER_HANDOFF.md` §1.5.
2. **Robotics & Autonomous Driving Policies**:
   - `SimLingo` (CVPR 2025): the primary policy.
     - Model: InternVL2-1B (InternViT-300M + Qwen2-0.5B).
     - Released: checkpoints at `RenzKa/simlingo` on Hugging Face, plus the training dataset under a Wayve non-commercial licence.
     - Its driving-only variant SimLingo-BASE (CarLLaVA) won the CARLA Challenge 2024.
   - `Drive-π0` (DriveMoE repo, CVPR 2026): the secondary policy (stretch).
   - `OpenVLA` (7B, manipulation only; no driving checkpoint) is a methods reference only.
   - Simulator and benchmark: **CARLA 0.9.15 + Bench2Drive (220 routes) + ScenarioRunner**. MetaDrive/HighwayEnv are only for early prototyping, since a CARLA-trained VLA will not transfer to them.
3. **Core Python Stack**:
   - PyTorch, Hugging Face `transformers`, `accelerate`.
   - Interpretability: `sae_lens`, `transformer_lens`, linear probing via `scikit-learn`.
   - Unsupervised Clustering: HDBSCAN, UMAP, Gaussian Mixture Models.
   - Text Processing & Embeddings: `sentence-transformers`, `faiss-cpu`, `spacy`.

---

## 5. Non-Negotiable Research Constraints & Baselines

When developing methods or running experiments in this repository, agents MUST respect the baseline controls formulated during team discussions:

1. **Failure Discovery vs. Failure Detection**:
   - *Do NOT* build another runtime anomaly detector that flags "this episode will crash" (saturated area).
   - *Build* an engine that discovers the **axis / category of failure** (e.g., "low-sun angle glare behind large vehicles causing distance underestimation").
2. **Catherine's Required Baselines**:
   Any discovered failure axis or open question must be benchmarked against:
   - **Baseline 1 (Random Selection)**: Uniformly sampling candidate data slices / questions.
   - **Baseline 2 (Human Predefined Taxonomy)**: Standard heuristic splits (e.g., weather = rain/fog/night).
   - **Baseline 3 (Behavioral / Output-Only Clustering)**: Clustering trajectory errors or loss without looking at internal model activations.
3. **Planted Gap Evaluation Metric**:
   Every dataset or rollout collection must maintain a controlled holdout split $\mathcal{G}^*$:
   $$\text{Precision} = \frac{|\mathcal{A}_{\text{discovered}} \cap \mathcal{G}^*|}{|\mathcal{A}_{\text{discovered}}|}, \quad \text{Recall} = \frac{|\mathcal{A}_{\text{discovered}} \cap \mathcal{G}^*|}{|\mathcal{G}^*|}$$
   In the plan of record, $|\mathcal{A}_{\text{discovered}}|$ is fixed at the axis budget M = 10, so precision always divides by 10. Matching is one Hungarian assignment on Jaccard ≥ 0.5 (`MASTER_HANDOFF.md` §4.2, Appendix B).

---

## 6. Current Implementation State

- **Stage**: Scaffolding & Conceptual Design (Weeks 1–3). As of 2026-09-28, follow the week-by-week plan and gates in [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md) §9. G0 (decisions locked) is Fri Oct 2.
- **Next Immediate Tasks** (superseded by `MASTER_HANDOFF.md` §9 where they differ):
  - Implement synthetic data generation pipeline for the chosen domain with planted holdout gaps.
  - Implement activation extraction hooks for policy rollout episodes.
  - Set up baseline clustering algorithms (HDBSCAN on activations vs. HDBSCAN on output actions).
