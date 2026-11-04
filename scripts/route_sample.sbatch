#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=route-sample
#SBATCH --time=0-00:50:00
#SBATCH --array=0-30%4
#SBATCH --output=route-sample-%A_%a.out
#
# Routes from a rollout config's route list (`routes`, else the ids in the manifest
# named by `route.manifest`), each with its own CARLA server.
# Arguments: config (default configs/rollout/savio-mac-paired.yaml, whose route
# list the array range above covers; tests/test_savio_runtime.py checks it) and
# routes per GPU (default 1). Routes run in route_run.run_order's seeded shuffle,
# so a slice and its neighbourhood never sit in separate blocks of array tasks.
# With K routes per GPU, array task i runs shuffled routes i*K .. i*K+K-1 side by
# side, so the array needs ceil(routes / K) tasks. Arrays submitted before
# 2026-10-12 ran in config order: rerun those by route id, not task index. Another
# config needs its own --array and --time on the command line:
#   bash scripts/submit.sh gpu --dependency=afterok:<step1 job id> scripts/route_sample.sbatch
#   bash scripts/submit.sh gpu_a40 --time=0-03:00:00 --array=0-109%4 scripts/route_sample.sbatch configs/rollout/step2-bench2drive220.yaml 2
# Each route's own output goes to results/savio/<array job>/route-<id>/run.log.
# ROUTE_MODE=expert runs PDM-Lite on the same routes instead of the policy.
# ROUTE_IDS="a b c d" reruns those routes (score_routes' rerun list) instead, K per GPU: pass K and --array=0-<ceil(routes / K) - 1>.
# CARLA_LOCAL_TAR=<tar> runs the server, and POLICY_VENV_LOCAL_TAR=<tar> the policy's Python, from a copy on node-local disk,
# CARLA_LOCAL_BUILD=<name> says the tar holds that carla.builds entry (e.g. fail2drive) instead of the stock server,
# for when slow scratch makes a route miss its start limits (docs/WHAT_BROKE.md, 2026-11-03). The first tar holds CarlaUE4,
# Engine, Plugins and CarlaUE4.sh at its top level; the second holds the venv's contents.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
unset CARLA_SERVER_ROOT CARLA_SERVER_BUILD
if [ -n "${CARLA_LOCAL_TAR:-}${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/route-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
fi
if [ -n "${CARLA_LOCAL_TAR:-}" ]; then
  mkdir "$STAGE/carla"
  tar -xf "$CARLA_LOCAL_TAR" -C "$STAGE/carla"
  [ -x "$STAGE/carla/CarlaUE4.sh" ] || { echo "$CARLA_LOCAL_TAR has no CarlaUE4.sh at its top level" >&2; exit 2; }
  export CARLA_SERVER_ROOT=$STAGE/carla
  [ -z "${CARLA_LOCAL_BUILD:-}" ] || export CARLA_SERVER_BUILD=$CARLA_LOCAL_BUILD
  echo "CARLA server staged at $CARLA_SERVER_ROOT after $SECONDS s"
fi
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  mkdir "$STAGE/venv"
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE/venv"
  [ -x "$STAGE/venv/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/venv/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi
CONFIG=${1:-configs/rollout/savio-mac-paired.yaml}
PER_GPU=${2:-1}
if [ -n "${ROUTE_IDS+x}" ]; then
  read -ra NAMED_ROUTES <<< "${ROUTE_IDS//$'\n'/ }"
  [ "${#NAMED_ROUTES[@]}" -gt 0 ] || { echo "ROUTE_IDS names no route" >&2; exit 2; }
  ROUTES=("${NAMED_ROUTES[@]:SLURM_ARRAY_TASK_ID*PER_GPU:PER_GPU}")
else
  mapfile -t ROUTES < <(PYTHONPATH=adapters/simlingo "$PY" -c '
import sys, yaml
from route_run import configured_route_ids, run_order
routes = run_order(configured_route_ids(yaml.safe_load(open(sys.argv[1]))))
first = int(sys.argv[2]) * int(sys.argv[3])
print("\n".join(routes[first:first + int(sys.argv[3])]))' "$CONFIG" "$SLURM_ARRAY_TASK_ID" "$PER_GPU")
fi

# GPU_LOG=1 samples the GPU's utilisation and memory every 2 s next to the routes (rollout profiling).
if [ -n "${GPU_LOG:-}" ]; then
  mkdir -p "results/savio/$SLURM_ARRAY_JOB_ID"
  nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv -l 2 \
    > "results/savio/$SLURM_ARRAY_JOB_ID/gpu-$SLURM_ARRAY_TASK_ID.csv" &
  GPU_LOGGER=$!
fi

PIDS=()
for SLOT in "${!ROUTES[@]}"; do
  ROUTE=${ROUTES[$SLOT]}
  OUT=results/savio/$SLURM_ARRAY_JOB_ID/route-$ROUTE
  mkdir -p "$OUT"
  echo "=== route $ROUTE (array task $SLURM_ARRAY_TASK_ID, slot $SLOT of ${#ROUTES[@]}, job $SLURM_JOB_ID) ==="
  "$PY" adapters/simlingo/run_savio.py "${ROUTE_MODE:-route}" --config "$CONFIG" --route "$ROUTE" --output "$OUT" \
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
[ -n "${GPU_LOGGER:-}" ] && kill "$GPU_LOGGER"
exit $STATUS
