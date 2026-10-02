# adapters/simlingo

The SimLingo adapter. **In progress** — see
`../../docs/steps/adapter-simlingo-brief.md` for what is in scope.

Keep this concrete and specific. `PRD.md` §8.2: build the general interface by
refactoring after this works, not before. Step 11.

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

Unconfirmed, and the first thing to resolve — these need the loaded config, not
the paper:

- `d` (hidden size); handoff says 896, paper does not state it
- decoder layer count; handoff says 24
- the exact module path of the query tokens and the MLP that reads them

## Licensing

Code is Apache-2.0. The **dataset is Wayve non-commercial** — do not
redistribute it, and see `PRD.md` §16 for the open question about releasing
derived checkpoints.
