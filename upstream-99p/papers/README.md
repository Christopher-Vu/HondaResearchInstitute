# Loaded Research Papers

This directory hosts primary research literature, technical reports, and preprints loaded into the repository for direct inspection and analysis by autonomous agents and human researchers.

---

## 1. SimLingo (arXiv:2503.09594 / CVPR 2025)

- **File**: [`simlingo_2503.09594.pdf`](simlingo_2503.09594.pdf)
- **Title**: SimLingo: Vision-Only Closed-Loop Autonomous Driving with Language-Action Alignment
- **Authors**: Katrin Renz (Wayve / Univ. of Tübingen), Long Chen (Wayve), Elahe Arani (Wayve), Oleg Sinavski (Wayve)
- **Venue**: IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR) 2025
- **Preprint**: [arXiv:2503.09594](https://arxiv.org/abs/2503.09594) (Preliminary Challenge Report: [arXiv:2406.10165](https://arxiv.org/abs/2406.10165))
- **Official Code**: [github.com/RenzKa/simlingo](https://github.com/RenzKa/simlingo)
- **Model Checkpoints**: [huggingface.co/RenzKa/simlingo](https://huggingface.co/RenzKa/simlingo)
- **In-Depth Technical Dossier**: [`docs/SIMLINGO_ANALYSIS.md`](../docs/SIMLINGO_ANALYSIS.md)
- **BibTeX Key**: `@simlingo2025` / `@Renz2025cvpr` in [`references.bib`](../references.bib)

### Key Highlights:
1. **Vision-Only Closed-Loop Driving**: Operates strictly on camera inputs (eliminating expensive LiDAR), achieving SOTA on the CARLA Leaderboard 2.0 (Sensor track) and winning the CARLA Challenge 2024.
2. **Compact VLA Architecture**: Built on InternVL-2 (~800M parameters: InternViT-300M vision encoder + Qwen2-0.5B-Instruct language backbone), vastly more resource-efficient than 7B generalist VLAs.
3. **Disentangled Action Heads**: Predicts geometric path waypoints $p \in \mathbb{R}^{N_p \times 2}$ (spatial steering geometry) and temporal speed waypoints $w \in \mathbb{R}^{N_w \times 2}$ (longitudinal acceleration) via parallel learnable query tokens.
4. **Action Dreaming**: Novel data-collection and benchmark paradigm that generates diverse counterfactual instruction-action pairs for the same visual context using kinematic bicycle simulation under the "world-on-rails" assumption, preventing the model from ignoring language instructions.
