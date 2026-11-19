#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh. One array task per part:
#   PARTS=4 bash scripts/submit.sh gpu --export=ALL --array=0-3 --time=0-04:00:00 \
#     docs/research/experiments/f2d-unpooled/replay.sbatch SHARDS OUT [--limit K]
#SBATCH --job-name=unpooled-replay
#SBATCH --output=unpooled-replay-%A_%a.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
nvidia-smi --query-gpu=name,memory.total --format=csv
SHARDS=$1 OUT=$2; shift 2
HF_HUB_OFFLINE=1 PYTHONPATH=src:adapters/simlingo .runtime/policy-venv/bin/python \
  docs/research/experiments/f2d-unpooled/replay_unpooled.py "$SHARDS" "$OUT" \
  --part "${SLURM_ARRAY_TASK_ID:-0}" --parts "${PARTS:-1}" "$@"
