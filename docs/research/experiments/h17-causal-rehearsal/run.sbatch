#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h17-causal
#SBATCH --time=0-04:30:00
#SBATCH --output=h17-causal-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar \
#     bash scripts/submit.sh gpu_a40 docs/research/experiments/h17-causal-rehearsal/run.sbatch
# The time limit holds spend under H17's 142 SU cap. If it ends the job, run `causal_replay.py report` by hand.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h17-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi
export HF_HUB_OFFLINE=1 PYTHONPATH=src
OUT=results/savio/h17-causal-rehearsal
POOL=(results/savio/step5-background-wave3/shards results/savio/step5-confirm-p4/shards
      results/savio/step5-confirm-p7/shards results/savio/step5-pilot-p19-main/shards)
git rev-parse HEAD
nvidia-smi
[ -f "$OUT/directions.pt" ] || "$PY" adapters/simlingo/causal_replay.py select "${POOL[@]}" \
  --frames-from results/savio/step5-confirm-p4/shards --sae results/savio/h12/sae/L10_k32_s3 \
  --stored docs/research/data/h12_layer10_plain.json --gap P4_camera_occlusion --output "$OUT"
"$PY" adapters/simlingo/causal_replay.py replay "$OUT" --device cuda
"$PY" adapters/simlingo/causal_replay.py report "$OUT"
