#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=f2d-dev-cpu
#SBATCH --output=f2d-dev-cpu-%j.out
#   CMD='docs/research/experiments/f2d-dev-simlingo/cache_pool.py results/savio/f2d-test-simlingo/shards --output ...' \
#     POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar \
#     bash scripts/submit.sh cpu --time=0-02:00:00 --job-name=f2d-dev-m03 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
# DEV ONLY. Stages the venv (torch + sklearn) node-locally and runs one python command for the sprint's method loop.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
: "${CMD:?set CMD to a python script and its arguments}"
STAGE=$(mktemp -d "/tmp/f2d-dev-cpu-$SLURM_JOB_ID.XXXXXX")
trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
tar -xf "${POLICY_VENV_LOCAL_TAR:?needs a venv with torch and sklearn}" -C "$STAGE"
git rev-parse HEAD
PYTHONPATH=src $STAGE/bin/python $CMD
echo "done after $SECONDS s"
