#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=sae-sweep
#SBATCH --time=0-08:00:00
#SBATCH --output=sae-sweep-%j.out
#
# PRD 12.2's SAE sweep on the per-token driving-query activations of the Step 5
# pilots: layers 10 and 14, k in {32, 48, 64}, six seeds, seed-major so every
# (layer, k) has a seed-0 run before any second seed. Arguments: shard directories.
#   bash scripts/submit.sh gpu_a40 scripts/sae_sweep.sbatch results/savio/step5-pilot-p4-main/shards ...
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
OUT=results/savio/sae-sweep
for SEED in 0 1 2 3 4 5; do
  for LAYER in 10 14; do
    for K in 32 48 64; do
      RUN=$OUT/L${LAYER}_k${K}_s${SEED}
      [ -f "$RUN/metrics.json" ] && continue
      echo "=== layer $LAYER k $K seed $SEED"
      .runtime/policy-venv/bin/python -m src.discovery.sae "$@" --layer "$LAYER" --k "$K" --seed "$SEED" --output "$RUN" \
        | grep -E '"(explained_variance|normalised_mse|never_fired_fraction|dead_fraction_at_end|train_tokens)"'
    done
  done
done
