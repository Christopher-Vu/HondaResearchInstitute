#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=route-sample
#SBATCH --time=0-00:50:00
#SBATCH --array=0-30%4
#SBATCH --output=route-sample-%A_%a.out
#
# Routes from a rollout config's route list, each with its own CARLA server.
# Arguments: config (default configs/rollout/savio-mac-paired.yaml, whose route
# list the array range above covers; tests/test_savio_runtime.py checks it) and
# routes per GPU (default 1). With K routes per GPU, array task i runs routes
# i*K .. i*K+K-1 side by side, so the array needs ceil(routes / K) tasks. Another
# config needs its own --array and --time on the command line:
#   bash scripts/submit.sh gpu --dependency=afterok:<step1 job id> scripts/route_sample.sbatch
#   bash scripts/submit.sh gpu_a40 --time=0-03:00:00 --array=0-109%4 scripts/route_sample.sbatch configs/rollout/step2-bench2drive220.yaml 2
# Each route's own output goes to results/savio/<array job>/route-<id>/run.log.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
CONFIG=${1:-configs/rollout/savio-mac-paired.yaml}
PER_GPU=${2:-1}
mapfile -t ROUTES < <("$PY" -c '
import sys, yaml
routes = yaml.safe_load(open(sys.argv[1]))["routes"]
first = int(sys.argv[2]) * int(sys.argv[3])
print("\n".join(routes[first:first + int(sys.argv[3])]))' "$CONFIG" "$SLURM_ARRAY_TASK_ID" "$PER_GPU")

PIDS=()
for SLOT in "${!ROUTES[@]}"; do
  ROUTE=${ROUTES[$SLOT]}
  OUT=results/savio/$SLURM_ARRAY_JOB_ID/route-$ROUTE
  mkdir -p "$OUT"
  echo "=== route $ROUTE (array task $SLURM_ARRAY_TASK_ID, slot $SLOT of ${#ROUTES[@]}, job $SLURM_JOB_ID) ==="
  "$PY" adapters/simlingo/run_savio.py route --config "$CONFIG" --route "$ROUTE" --output "$OUT" \
    --slot "$SLOT" --slots "$PER_GPU" > "$OUT/run.log" 2>&1 &
  PIDS+=($!)
  # Two CARLA servers starting together crashed one with a segfault (2026-10-08),
  # so the next slot starts only once this server accepts clients or the route ends.
  while kill -0 "$!" 2>/dev/null && [ ! -f "$OUT/server-ready" ]; do sleep 5; done
done
STATUS=0
for INDEX in "${!PIDS[@]}"; do
  if wait "${PIDS[$INDEX]}"; then echo "route ${ROUTES[$INDEX]}: readiness written"
  else echo "route ${ROUTES[$INDEX]}: failed, see its run.log"; STATUS=1; fi
done
exit $STATUS
