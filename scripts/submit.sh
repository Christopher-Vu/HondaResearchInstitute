#!/usr/bin/env bash
# Submit a job, reading cluster settings from configs/cluster/savio.yaml so that
# no script hardcodes a partition, QoS or GPU type.
#
#   bash scripts/submit.sh gpu scripts/check_gpu.sbatch
#   bash scripts/submit.sh cpu scripts/validate_configs.sbatch
#
# Refuses to submit a GPU job while gpu.available is false, which is the current
# state: ic_cdss170fall has only the retired savio2_gpu, and savio3_gpu /
# savio4_gpu are rejected pending a support request.
set -euo pipefail

KIND="${1:?usage: submit.sh <gpu|cpu> <script.sbatch> [args...]}"
SCRIPT="${2:?usage: submit.sh <gpu|cpu> <script.sbatch> [args...]}"
shift 2
CFG="${CLUSTER_CONFIG:-configs/cluster/savio.yaml}"

[ -f "$CFG" ] || { echo "no cluster config at $CFG" >&2; exit 1; }

get() { python3 -c "
import yaml,sys
d=yaml.safe_load(open('$CFG'))
for k in sys.argv[1].split('.'):
    d=(d or {}).get(k)
print('' if d is None else d)
" "$1"; }

ACCOUNT=$(get account)

if [ "$KIND" = gpu ]; then
  AVAIL=$(get gpu.available)
  if [ "$AVAIL" != "True" ] && [ "$AVAIL" != "true" ]; then
    cat >&2 <<MSG
REFUSING to submit: GPU access is not available yet.

  configs/cluster/savio.yaml has gpu.available: false

  ic_cdss170fall currently has only savio2_gpu (retired); savio3_gpu and
  savio4_gpu are rejected. A support request is open.

Once the reply arrives, set gpu.available, gpu.partition, gpu.qos and gpu.gres
in that file and re-run. Nothing else needs editing.
MSG
    exit 2
  fi
  PART=$(get gpu.partition); QOS=$(get gpu.qos)
  GRES=$(get gpu.gres);      CPUS=$(get gpu.cpus_per_task)
else
  PART=$(get cpu.partition); QOS=$(get cpu.qos)
  GRES="";                   CPUS=$(get cpu.cpus_per_task)
fi

[ -n "$PART" ] || { echo "$KIND partition is null in $CFG — fill it from the support reply or savio_recon.sh" >&2; exit 2; }

ARGS=(--account="$ACCOUNT" --partition="$PART")
[ -n "$QOS" ]  && ARGS+=(--qos="$QOS")
[ -n "$GRES" ] && ARGS+=(--gres="$GRES")
[ -n "$CPUS" ] && ARGS+=(--cpus-per-task="$CPUS")

echo "sbatch ${ARGS[*]} $SCRIPT $*"
exec sbatch "${ARGS[@]}" "$SCRIPT" "$@"
