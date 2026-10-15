#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=layer-sweep
#SBATCH --time=0-04:00:00
#SBATCH --output=layer-sweep-%j.out
#
# The layer sweep over several shard directories at once, through a directory of
# links, in the analysis venv that wrote every earlier sweep. Arguments: output
# directory, then shard directories. Used when a practice gap passes efficacy,
# so practice-gap recovery joins the sweep's metrics.
#   bash scripts/submit.sh cpu --cpus-per-task=8 scripts/layer_sweep.sbatch results/savio/step4-sweep-with-p4 results/savio/step4-dev-pool/shards results/savio/step4-dev-pool-wave2/shards results/savio/step5-pilot-p4-main/shards
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
OUT=${1:?output directory}
shift
mkdir -p "$OUT/shards"
for SHARDS in "$@"; do ln -sf "$PWD/$SHARDS"/* "$OUT/shards/"; done
.runtime/analysis-venv/bin/python -m src.discovery.layer_sweep "$OUT/shards" --output "$OUT/sweep.json"
