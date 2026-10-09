#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step4-sweep
#SBATCH --time=0-02:00:00
#SBATCH --output=step4-sweep-%j.out
#
# Step 4 after the dev pool's rollouts (docs/steps/04-dev-pool-and-layer-sweep.md):
# score the routes, export each capture to a shard, run the layer sweep with its
# practice-gap efficacy check. Arguments: results/savio/<array job> directories.
#   bash scripts/submit.sh cpu --dependency=afterany:<array job> scripts/step4_sweep.sbatch results/savio/<array job>
# Needs .runtime/analysis-venv (numpy, scipy, scikit-learn, pyyaml), built once on a login node:
#   uv venv .runtime/analysis-venv --python 3.11 && uv pip install --python .runtime/analysis-venv/bin/python -r requirements.txt
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
CONFIG=configs/rollout/step4-dev-pool.yaml
OUT=results/savio/step4-dev-pool

.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py "$CONFIG" "$@" --output "$OUT"
.runtime/policy-venv/bin/python adapters/simlingo/export_activations.py "$@" --output "$OUT/shards" \
  --manifest configs/rollout/step4-dev-pool.manifest.json
.runtime/analysis-venv/bin/python -m src.discovery.layer_sweep "$OUT/shards" --output "$OUT/sweep.json"
