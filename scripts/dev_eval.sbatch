#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=dev-eval
#SBATCH --time=0-03:00:00
#SBATCH --output=dev-eval-%j.out
#
# H1 planted-gap recovery on the pooled dev corpus (src/discovery/dev_eval.py,
# docs/research/experiments/h1-planted-gap-recovery/protocol.md). Arguments: output
# file, then shard directories. LAYER (default 10) is the decoder layer of the frame
# means. SAE_RUNS is a glob of SAE run directories (default: every run of the sweep;
# runs at another layer are skipped with a note); set it to the empty string to run M2,
# B2 and B3 only.
#   bash scripts/submit.sh cpu --cpus-per-task=8 --dependency=afterany:<sae sweep> scripts/dev_eval.sbatch results/savio/dev-eval/h1-L10.json share/dev-pool-wave1-shards share/dev-pool-wave2-shards share/p4-main-shards results/savio/step5-pilot-p7-main/shards results/savio/step5-pilot-p8-main/shards
#   SAE_RUNS= LAYER=14 bash scripts/submit.sh cpu scripts/dev_eval.sbatch ...
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
OUT=${1:?output file}
shift
SAE_RUNS=${SAE_RUNS-results/savio/sae-sweep/L*}
SAE_ARGS=()
if [[ -n "$SAE_RUNS" ]]; then
  SAE_ARGS=(--sae $SAE_RUNS)
fi
PYTHONPATH=src .runtime/policy-venv/bin/python -m discovery.dev_eval "$@" \
  --layer "${LAYER:-10}" ${SAE_ARGS[@]+"${SAE_ARGS[@]}"} \
  --gap P4_camera_occlusion P7_camera_freeze P8_camera_latency \
  --manifests 'configs/rollout/step4-dev-pool*.manifest.json' 'configs/rollout/step5-pilot-*.manifest.json' \
  --output "$OUT"
