#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=b2d-ability
#SBATCH --time=0-01:00:00
#SBATCH --output=b2d-ability-%j.out
#
# Bench2Drive's own per-ability success rates (tools/ability_benchmark.py) for a
# merged 220-route result from adapters/simlingo/score_routes.py. The script
# starts its own CARLA to find each traffic-sign route's junction, hence a GPU.
# It writes <merged>_ability.json next to the merged file; keep the path free of
# other dots, since the script cuts the name at the first one.
#   bash scripts/submit.sh gpu_a40 scripts/ability_benchmark.sbatch results/savio/step2-bench2drive220/res/merged.json
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

MERGED=$(realpath "${1:?merged.json from score_routes.py}")
CARLA_ROOT=$PWD/.runtime/carla-linux PYTHONPATH=$PWD/.runtime/carla-linux/PythonAPI/carla \
  .runtime/policy-venv/bin/python .runtime/simlingo/Bench2Drive/tools/ability_benchmark.py \
  -f .runtime/simlingo/leaderboard/data/bench2drive220.xml -r "$MERGED"
