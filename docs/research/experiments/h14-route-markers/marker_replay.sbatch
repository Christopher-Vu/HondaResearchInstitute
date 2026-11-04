#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=h14-offline
#SBATCH --time=0-01:00:00
#SBATCH --output=h14-offline-%j.out
#
# H14's offline test on the 40 drawn routes of array 40715498, after results/savio/h14-offline/mask-check.json passes:
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 docs/research/experiments/h14-route-markers/marker_replay.sbatch
# The protocol's Submit section gives the step before it, which draws the frames to view.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h14-offline-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi
HF_HUB_OFFLINE=1 "$PY" adapters/simlingo/marker_replay.py replay results/savio/40715498 --output results/savio/h14-offline --device cuda
