#!/usr/bin/env bash
# Submit a job, reading cluster settings from configs/cluster/savio.yaml so that
# no script hardcodes a partition, QoS or GPU type.
#
#   bash scripts/submit.sh gpu scripts/check_gpu.sbatch
#   bash scripts/submit.sh gpu --dependency=afterok:123 scripts/route_sample.sbatch
#   bash scripts/submit.sh gpu_a40 scripts/step1.sbatch
#   bash scripts/submit.sh cpu scripts/validate_configs.sbatch
#
# The first argument names a profile in the config (gpu, gpu_a40, cpu).
#
# Options starting with -- before the script go to sbatch; anything after it goes
# to the script. Savio's sbatch ignored SBATCH_DEPENDENCY, so pass --dependency here.
# Refuses to submit a GPU job while gpu.available is false.
set -euo pipefail

USAGE="usage: submit.sh <profile: gpu|gpu_a40|cpu> [--sbatch-option ...] <script.sbatch> [args...]"
KIND="${1:?$USAGE}"
shift
EXTRA=()
while [ $# -gt 0 ] && [[ "$1" == --* ]]; do EXTRA+=("$1"); shift; done
SCRIPT="${1:?$USAGE}"
shift
CFG="${CLUSTER_CONFIG:-configs/cluster/savio.yaml}"

[ -f "$CFG" ] || { echo "no cluster config at $CFG" >&2; exit 1; }

# Savio's system python3 may lack PyYAML; the policy venv from setup_savio.py has it.
PY=python3
[ -x .runtime/policy-venv/bin/python ] && PY=.runtime/policy-venv/bin/python
"$PY" -c 'import yaml' 2>/dev/null || { echo "$PY cannot import yaml; run adapters/simlingo/setup_savio.py first" >&2; exit 1; }

get() { "$PY" -c "
import yaml,sys
d=yaml.safe_load(open('$CFG'))
for k in sys.argv[1].split('.'):
    d=(d or {}).get(k)
print('' if d is None else d)
" "$1"; }

ACCOUNT=$(get account)

if [[ "$KIND" == gpu* ]]; then
  AVAIL=$(get "$KIND.available")
  if [ "$AVAIL" != "True" ] && [ "$AVAIL" != "true" ]; then
    cat >&2 <<MSG
REFUSING to submit: GPU access is not available yet.

  $CFG has $KIND.available: ${AVAIL:-missing}

Set $KIND.available, .partition, .qos and .gres in that file from
sacctmgr -nP show assoc user=$USER format=Account,Partition,QOS, then re-run.
MSG
    exit 2
  fi
fi
PART=$(get "$KIND.partition"); QOS=$(get "$KIND.qos")
GRES=$(get "$KIND.gres");      CPUS=$(get "$KIND.cpus_per_task")

[ -n "$PART" ] || { echo "$KIND partition is null in $CFG; fill it from sacctmgr show assoc" >&2; exit 2; }

ARGS=(--account="$ACCOUNT" --partition="$PART")
[ -n "$QOS" ]  && ARGS+=(--qos="$QOS")
[ -n "$GRES" ] && ARGS+=(--gres="$GRES")
[ -n "$CPUS" ] && ARGS+=(--cpus-per-task="$CPUS")
ARGS+=(${EXTRA[@]+"${EXTRA[@]}"})

echo "sbatch ${ARGS[*]} $SCRIPT $*"
exec sbatch "${ARGS[@]}" "$SCRIPT" "$@"
