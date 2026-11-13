#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h19-m2
#SBATCH --output=h19-m2-%j.out
#   bash scripts/submit.sh cpu --time=0-03:00:00 docs/research/experiments/h19-m2-settings/run.sbatch
# DEV DRY RUN, NOT A VERDICT. H12's shards and H15's throwaway key, CPU only. Protocol: protocol.md beside this file.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
git rev-parse HEAD
[ -f results/savio/h15/throwaway/as-labelled/key.json ] || { echo "missing H15's throwaway key" >&2; exit 2; }
PYTHONPATH=src .runtime/policy-venv/bin/python docs/research/experiments/h19-m2-settings/sweep.py --output results/savio/h19/result.json
