# adapters/simlingo

The SimLingo adapter. **Closed-loop execution remains unverified** — see
`../../docs/steps/adapter-simlingo-brief.md` for what is in scope.

Keep this concrete and specific. `PRD.md` §8.2: build the general interface by
refactoring after this works, not before. Step 11.

## Offline checkpoint verification

The Mac setup has pinned source in `.runtime/simlingo`, the base model in
`.runtime/InternVL2-1B`, and the checksum-verified released weights under
`checkpoints/simlingo/`. Exact revisions live in
`../../configs/setup/simlingo-artifacts.yaml`; the CPU environment is separate
from the harness and CARLA runtime.

```bash
uv venv --python 3.11 .runtime/policy-venv
uv pip install --python .runtime/policy-venv/bin/python -r adapters/simlingo/requirements-cpu.lock
HF_HUB_OFFLINE=1 .runtime/policy-venv/bin/python adapters/simlingo/verify_checkpoint.py
```

The verifier checks the source revision, applied patch and weight checksum,
strict-loads the whole model, then checks finite waypoint outputs from a dummy
camera input. It writes `results/setup/model-smoke.json`; it never marks CARLA
camera rendering or closed-loop driving as verified.

`patches/commentary-off.patch` selects commentary-off inference in the agent and
unpacks the feature/logit tuple correctly in that model branch. The original
branch raises `TypeError: tuple indices must be integers or slices, not tuple`;
the patched branch passes with the same released weights. Apply it after cloning
the manifest's source revision:

```bash
git -C .runtime/simlingo apply ../../adapters/simlingo/patches/commentary-off.patch
```

## Policy facts

Verified from the paper (`docs/step0-trackA-findings.md`):

- InternVL2-1B = InternViT-300M-448px + Qwen2-0.5B-Instruct.
- Learnable query tokens `q_p` (path) and `q_w` (speed); an MLP on their output
  features predicts waypoint *differences*, cumulatively summed. One forward
  pass, not autoregressive.
- LoRA r=32, α=64, dropout 0.1 on all LLM linear layers. **Everything else is
  fully finetuned — the vision encoder is NOT frozen** in SimLingo's own recipe.
  (Our repair step freezes it, which is our deviation; see `PRD.md` §9.4.)
- SmoothL1 waypoint loss.
- Run with commentary/CoT **off** in the main campaign (`PRD.md` §10.1).

Verified by strict checkpoint loading and CPU inference on 2026-10-02:

- Hidden size: 896; language decoder layers: 24.
- Query parameters: `adaptors.driving.query_embeds_wps` (1 × 20 × 896) and
  `adaptors.driving.query_embeds_speed` (1 × 10 × 896).
- Readout heads: `adaptors.driving.route_head` and `adaptors.driving.speed_wps_head`.
- The pinned source includes Bench2Drive 0.0.3.

## Licensing

Code is Apache-2.0. The **dataset is Wayve non-commercial** — do not
redistribute it, and see `PRD.md` §16 for the open question about releasing
derived checkpoints.
