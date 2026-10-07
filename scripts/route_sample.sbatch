#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=route-sample
#SBATCH --time=0-00:50:00
#SBATCH --array=0-30%4
#SBATCH --output=route-sample-%A_%a.out
#
# One route per array task from configs/rollout/savio-mac-paired.yaml, each with
# its own CARLA server. The array range must cover that file's route list
# (tests/test_savio_runtime.py checks it). Submit once Step 1 has passed:
#   SBATCH_DEPENDENCY=afterok:<step1 job id> bash scripts/submit.sh gpu scripts/route_sample.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
CONFIG=configs/rollout/savio-mac-paired.yaml
ROUTE=$("$PY" -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["routes"][int(sys.argv[2])])' \
  "$CONFIG" "$SLURM_ARRAY_TASK_ID")
OUT=results/savio/$SLURM_ARRAY_JOB_ID/route-$ROUTE
mkdir -p "$OUT"
echo "=== route $ROUTE (array task $SLURM_ARRAY_TASK_ID, job $SLURM_JOB_ID) ==="
"$PY" adapters/simlingo/run_savio.py route --config "$CONFIG" --route "$ROUTE" --output "$OUT"
