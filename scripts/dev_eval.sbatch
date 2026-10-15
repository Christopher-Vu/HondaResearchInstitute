#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=dev-eval
#SBATCH --time=0-03:00:00
#SBATCH --output=dev-eval-%j.out
#
# Discovery on the dev pool against the practice gaps that passed efficacy
# (src/discovery/dev_eval.py), for every seed-0 run of the SAE sweep. Arguments:
# output file, then shard directories.
#   bash scripts/submit.sh cpu --cpus-per-task=8 --dependency=afterany:<sae sweep> scripts/dev_eval.sbatch results/savio/dev-eval/p4.json results/savio/step5-pilot-p4-main/shards ...
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
OUT=${1:?output file}
shift
PYTHONPATH=src .runtime/policy-venv/bin/python -m discovery.dev_eval "$@" \
  --sae results/savio/sae-sweep/L*_s0 --gap P4_camera_occlusion \
  --manifests 'configs/rollout/step5-pilot-*.manifest.json' --output "$OUT"
