#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step1-route
#SBATCH --time=0-01:00:00
#SBATCH --output=step1-%j.out
#
# Step 1 stages 1.2-1.4 (docs/steps/01-smallest-rollout.md) in dependency
# order, stopping at the first failure so each one stays attributable.
# Requires adapters/simlingo/setup_savio.py to have finished.
#   bash scripts/submit.sh gpu scripts/step1.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
OUT=results/savio/$SLURM_JOB_ID
mkdir -p "$OUT"
nvidia-smi

echo "=== 1.2 off-screen rendering: camera pixels and vehicle control ==="
"$PY" adapters/simlingo/run_savio.py render --output "$OUT/render"

echo "=== 1.3 checkpoint: strict load and finite waypoints ==="
HF_HUB_OFFLINE=1 "$PY" adapters/simlingo/verify_checkpoint.py --output "$OUT/model-smoke.json"

echo "=== 1.4 one route, closed loop ==="
"$PY" adapters/simlingo/run_savio.py route --output "$OUT/route"

echo "=== done: $OUT/route/readiness.json ==="
