#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=f2d-dev-h24
#SBATCH --output=f2d-dev-h24-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh cpu --time=0-03:00:00 docs/research/experiments/f2d-dev-simlingo/h24_export.sbatch
# DEV ONLY (VARIANTS.md v2). H24's feature export, unchanged, on the SimLingo Fail2Drive test pool.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
OUT=results/savio/f2d-dev/simlingo/v2
mkdir -p "$OUT"
STAGE=$(mktemp -d "/tmp/f2d-dev-h24-$SLURM_JOB_ID.XXXXXX")
trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
tar -xf "${POLICY_VENV_LOCAL_TAR:?needs a venv with torch and sklearn}" -C "$STAGE"
PYTHONPATH=src $STAGE/bin/python docs/research/experiments/h24-error-aware-grouping/export_features.py \
  results/savio/f2d-test-simlingo/shards --output "$OUT/features.npz"
echo "export done after $SECONDS s"
