#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh. Exports the re-driven route folders to
# shards (export_activations.py), then writes tfpp_unpooled.py's per-route npz. Only array task 0 exports, so a run
# split into PARTS tasks needs the shards first: submit task 0 alone, then 1..N-1 with --dependency=afterok on it.
# Smoke, one task:
#   bash scripts/submit.sh gpu --export=ALL --array=0-0 --time=0-01:00:00 \
#     docs/research/experiments/f2d-unpooled/tfpp_unpooled.sbatch OUT ROUTE_DIR_OR_JOB_DIR... [-- --limit K]
#SBATCH --job-name=tfpp-unpooled
#SBATCH --output=tfpp-unpooled-%A_%a.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
nvidia-smi --query-gpu=name,memory.total --format=csv
OUT=$1; shift
ROUTES=(); while [ $# -gt 0 ] && [ "$1" != "--" ]; do ROUTES+=("$1"); shift; done
[ "${1:-}" = "--" ] && shift
PY=.runtime/policy-venv/bin/python
export PYTHONPATH=src:adapters/simlingo HF_HUB_OFFLINE=1
if [ "${SLURM_ARRAY_TASK_ID:-0}" = 0 ]; then
  $PY adapters/simlingo/export_activations.py "${ROUTES[@]}" --output "$OUT/shards" \
    --manifest configs/rollout/f2d-test-simlingo.manifest.json
fi
$PY docs/research/experiments/f2d-unpooled/tfpp_unpooled.py "$OUT/shards" "$OUT/npz" \
  --part "${SLURM_ARRAY_TASK_ID:-0}" --parts "${PARTS:-1}" "$@"
