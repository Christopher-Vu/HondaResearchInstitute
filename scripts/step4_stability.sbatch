#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step4-stability
#SBATCH --time=0-05:00:00
#SBATCH --output=step4-stability-%j.out
#
# Step 4's resampling stability check (docs/steps/04-dev-pool-and-layer-sweep.md):
# five sweeps, each without a random fifth of the base routes, against sweep.json's
# chosen set. Runs in .runtime/analysis-venv, the environment that wrote sweep.json:
# scikit-learn's grouped folds differ between versions (docs/WHAT_BROKE.md).
#   bash scripts/submit.sh cpu --cpus-per-task=8 scripts/step4_stability.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
OUT=results/savio/step4-dev-pool
.runtime/analysis-venv/bin/python -m src.discovery.layer_sweep "$OUT/shards" \
  --output "$OUT/stability.json" --stability-of "$OUT/sweep.json"
