#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h16-capture
#SBATCH --output=h16-capture-%A_%a.out
#SBATCH --time=0-00:30:00
#
# H16: B7 variant A's training frames, no simulator. `check` compares the input path with saved rollouts and reads one
# route's head, under its own job name; `capture` streams one drawn chunk per array task to node-local disk and writes layer-10 means to
# results/savio/h16/training. A finished route is never redone, so a task that hits its limit is resubmitted by index.
# job_guard.py refuses a wrong job name, a longer limit, spend past the cap, or an oversized output folder.
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-00:30:00 \
#     --job-name=h16-check docs/research/experiments/h16-b7-rollout-free/capture.sbatch check
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-03:30:00 \
#     --array=0-5%2 docs/research/experiments/h16-b7-rollout-free/capture.sbatch capture
# CHUNK_DIR=<dir of the six tars> reads them from there, for when a compute node cannot reach Hugging Face.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
MODE=${1:?check or capture}
HERE=docs/research/experiments/h16-b7-rollout-free
REVISION=796abab62acaddb6183d0d01c9b43a622c5c58c8
MIN_FREE_KB=$((30 * 1024 * 1024))
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=adapters/simlingo:src

STAGE=$(mktemp -d "/tmp/h16-$SLURM_JOB_ID.XXXXXX")
trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
[ "$(df -k --output=avail "$STAGE" | tail -1)" -ge "$MIN_FREE_KB" ] || { echo "under 30 GB free on /tmp" >&2; exit 2; }
PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  mkdir "$STAGE/venv"
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE/venv"
  PY=$STAGE/venv/bin/python
  echo "policy venv staged after $SECONDS s"
fi
"$PY" "$HERE/job_guard.py" "$MODE"
mkdir "$STAGE/frames"
chunk_name() { "$PY" -c 'import sys; from baselines.b7_variant_a import CHUNKS; print(CHUNKS[int(sys.argv[1])])' "$1"; }
chunk_url() { echo "https://huggingface.co/datasets/RenzKa/simlingo/resolve/$REVISION/$1"; }
unpack() { tar -xzf - -C "$STAGE/frames" --wildcards '*/rgb/*.jpg' '*/measurements/*.json.gz'; }

if [ "$MODE" = check ]; then
  # The first 200 MB hold the first listed route whole, so the cut stream's tar error is expected.
  curl -fsSL -r 0-199999999 "$(chunk_url "$(chunk_name 0)")" | unpack || true
  "$PY" "$HERE/capture_training.py" check --rollouts results/savio/40715498 --stage "$STAGE/frames" \
    --output results/savio/h16/check.json
  exit 0
fi

CHUNK=$(chunk_name "$SLURM_ARRAY_TASK_ID")
if [ -n "${CHUNK_DIR:-}" ]; then unpack < "$CHUNK_DIR/$CHUNK"
else curl -fsSL --retry 5 --retry-delay 10 "$(chunk_url "$CHUNK")" | unpack; fi
echo "$CHUNK unpacked after $SECONDS s: $(du -sh "$STAGE/frames" | cut -f1)"
"$PY" "$HERE/capture_training.py" capture --stage "$STAGE/frames" --output results/savio/h16/training \
  --task "$SLURM_ARRAY_TASK_ID" --workers $((SLURM_CPUS_PER_TASK - 1))
