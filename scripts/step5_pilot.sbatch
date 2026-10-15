#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step5-pilot
#SBATCH --time=0-02:00:00
#SBATCH --output=step5-pilot-%j.out
#
# A Step 5 efficacy pilot after its rollouts: score the routes, export each capture
# to a shard for the dev pool, and judge the gap by PRD 9.1 and CONFLICTS.md C23
# (src/harness/efficacy.py). Arguments: pilot config, gap id, results/savio/<array job> ...
#   bash scripts/submit.sh cpu --dependency=afterany:<array job> scripts/step5_pilot.sbatch configs/rollout/step5-pilot-p3.yaml P3_dense_fog_day results/savio/<array job>
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
CONFIG=${1:?pilot config}
GAP=${2:?gap id}
shift 2
OUT=results/savio/$(basename "$CONFIG" .yaml)
MANIFEST=$(.runtime/policy-venv/bin/python -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["route"]["manifest"])' "$CONFIG")

.runtime/policy-venv/bin/python adapters/simlingo/score_routes.py "$CONFIG" "$@" --output "$OUT"
.runtime/policy-venv/bin/python adapters/simlingo/export_activations.py "$@" --output "$OUT/shards" --manifest "$MANIFEST"
.runtime/analysis-venv/bin/python -m src.harness.efficacy "$MANIFEST" "$OUT/routes.jsonl" --gap "$GAP" --output "$OUT/efficacy.json"
