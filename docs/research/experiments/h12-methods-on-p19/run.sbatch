#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h12-methods
#SBATCH --output=h12-methods-%j.out
#   bash scripts/submit.sh gpu_a40 --time=0-02:00:00 docs/research/experiments/h12-methods-on-p19/run.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
SHARDS=(results/savio/step5-background-wave3/shards results/savio/step5-confirm-p4/shards
        results/savio/step5-confirm-p7/shards results/savio/step5-pilot-p19-main/shards)
OUT=results/savio/h12
PY=.runtime/policy-venv/bin/python
for SEED in 0 1 2 3 4 5; do
  for K in 32 48 64; do
    RUN=$OUT/sae/L10_k${K}_s${SEED}
    [ -f "$RUN/metrics.json" ] && continue
    PYTHONPATH=src $PY -m discovery.sae "${SHARDS[@]}" --layer 10 --k "$K" --seed "$SEED" --frame-means --output "$RUN" \
      | grep -E '"(explained_variance|train_tokens)"'
  done
done
EVAL=(--layer 10 --sae $OUT/sae/L10_* --gap P19_wide_invading_turn P4_camera_occlusion P7_camera_freeze
      --manifests configs/rollout/step5-background-wave3.manifest.json configs/rollout/step5-confirm-p4.manifest.json
      configs/rollout/step5-confirm-p7.manifest.json configs/rollout/step5-pilot-p19-main.manifest.json)
PYTHONPATH=src $PY -m discovery.dev_eval "${SHARDS[@]}" "${EVAL[@]}" --output $OUT/plain.json
PYTHONPATH=src $PY -m discovery.dev_eval "${SHARDS[@]}" "${EVAL[@]}" --stale-latent --output $OUT/stale.json
