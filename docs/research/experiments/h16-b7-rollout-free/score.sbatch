#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h16-score
#SBATCH --output=h16-score-%j.out
#SBATCH --time=0-02:00:00
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-02:00:00 \
#     --dependency=afterok:<capture array> docs/research/experiments/h16-b7-rollout-free/score.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
HERE=docs/research/experiments/h16-b7-rollout-free
OUT=results/savio/h16
PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h16-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  PY=$STAGE/bin/python
fi
export PYTHONPATH=src
$PY $HERE/job_guard.py score
# H12's four pools by name. Never glob the pilot folders: that would open P20.
SHARDS=(results/savio/step5-background-wave3/shards results/savio/step5-confirm-p4/shards
        results/savio/step5-confirm-p7/shards results/savio/step5-pilot-p19-main/shards)
COMMON=(--training $OUT/training --sae results/savio/h12/sae/L10_*)
$PY $HERE/score.py "${SHARDS[@]}" "${COMMON[@]}" --gap P19_wide_invading_turn P4_camera_occlusion P7_camera_freeze \
  --reproduce docs/research/data/h12_layer10_plain.json --output $OUT/plain.json
$PY $HERE/score.py "${SHARDS[@]}" results/savio/step5-pilot-p8-main/shards "${COMMON[@]}" --gap P8_camera_latency \
  --output $OUT/plain-p8.json
$PY $HERE/read_rule.py $OUT/plain.json $OUT/plain-p8.json --output $OUT/stop-condition.json
$PY $HERE/score.py "${SHARDS[@]}" "${COMMON[@]}" --gap P7_camera_freeze --stale-latent --output $OUT/post-hoc-frozen-input.json
