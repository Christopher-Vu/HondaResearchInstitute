#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step3-replay
#SBATCH --time=0-00:45:00
#SBATCH --output=step3-replay-%j.out
#
# Step 3 on Savio (PRD 13): replay frames that Step 2 rollouts saved, in the
# dtype and device they were logged with (CUDA bfloat16), and check the
# waypoints match the logs to within 1e-3 m. Arguments: route directories.
#   bash scripts/submit.sh gpu_a40 --exclude=n0214.savio3,n0215.savio3 scripts/step3_replay.sbatch \
#     results/savio/39732818/route-26956 results/savio/39732818/route-25424 \
#     results/savio/39732818/route-2204 results/savio/39732819/route-1773
# Each writes <route>/capture/replay-cuda.json.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
nvidia-smi
for RUN in "$@"; do
  echo "=== $RUN ==="
  HF_HUB_OFFLINE=1 .runtime/policy-venv/bin/python adapters/simlingo/replay_capture.py "$RUN" \
    --device cuda --limit "${REPLAY_LIMIT:-10}"
done
