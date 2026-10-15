#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step4-wave2
#SBATCH --time=0-03:00:00
#SBATCH --output=step4-wave2-%j.out
#
# Step 4 after its second wave: score the 200 background routes, export their
# shards, and rerun the layer sweep over both waves (390 rollouts) through a
# directory of links, leaving wave 1's evidence as it is. Arguments:
# results/savio/<wave 2 array job> directories.
#   bash scripts/submit.sh cpu --cpus-per-task=8 --dependency=afterany:<wave 2 array> scripts/step4_wave2.sbatch results/savio/<wave 2 array>
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
CONFIG=configs/rollout/step4-dev-pool-wave2.yaml
OUT=results/savio/step4-dev-pool-wave2
BOTH=results/savio/step4-dev-pool-both

.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py "$CONFIG" "$@" --output "$OUT"
.runtime/policy-venv/bin/python adapters/simlingo/export_activations.py "$@" --output "$OUT/shards" \
  --manifest configs/rollout/step4-dev-pool-wave2.manifest.json
mkdir -p "$BOTH/shards"
ln -sf "$PWD"/results/savio/step4-dev-pool/shards/* "$PWD/$OUT"/shards/* "$BOTH/shards/"
.runtime/analysis-venv/bin/python -m src.discovery.layer_sweep "$BOTH/shards" --output "$BOTH/sweep.json"
