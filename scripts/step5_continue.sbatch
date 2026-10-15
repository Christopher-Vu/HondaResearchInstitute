#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=step5-continue
#SBATCH --time=0-00:10:00
#SBATCH --output=step5-continue-%j.out
#
# After a Step 5 screen is scored: if it passes its gap's screen_rule, submit the
# 60-pair pilot and its scoring job; otherwise stop. Arguments: screen config,
# full-pilot config, gap id, and optionally the gaps file (default gaps/practice/practice_v2.yaml).
#   bash scripts/submit.sh cpu --dependency=afterok:<screen scoring job> scripts/step5_continue.sbatch configs/rollout/step5-pilot-p6-screen.yaml configs/rollout/step5-pilot-p6-main.yaml P6_animal_crossing
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
SCREEN=${1:?screen config}
MAIN=${2:?full-pilot config}
GAP=${3:?gap id}
GAPS=${4:-gaps/practice/practice_v2.yaml}
REPORT=results/savio/$(basename "$SCREEN" .yaml)/efficacy.json
if ! .runtime/analysis-venv/bin/python -m src.harness.efficacy --screen "$REPORT" --gaps "$GAPS"; then
  echo "screen did not pass; the full pilot is not submitted"
  exit 0
fi
ARRAY=$(bash scripts/submit.sh gpu_a40 --time=0-03:00:00 --array=0-59%6 scripts/route_sample.sbatch "$MAIN" 2 | tail -1 | awk '{print $4}')
bash scripts/submit.sh cpu --dependency=afterany:"$ARRAY" scripts/step5_pilot.sbatch "$MAIN" "$GAP" "results/savio/$ARRAY"
echo "full pilot submitted as array $ARRAY"
