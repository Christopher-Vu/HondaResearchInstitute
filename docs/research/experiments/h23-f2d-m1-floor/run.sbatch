#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h23-f2d-floor
#SBATCH --output=h23-f2d-floor-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-01:00:00 docs/research/experiments/h23-f2d-m1-floor/run.sbatch
# DEV ONLY, NOT BLIND, POST HOC. H22's dictionaries, M1's floor at 3. Protocol: protocol.md beside this file.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

git merge-base --is-ancestor methods-frozen-f2d-v2 HEAD \
  || { echo "HEAD does not contain methods-frozen-f2d-v2; the lock comes first" >&2; exit 2; }

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h23-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
fi

EXP=docs/research/experiments/h23-f2d-m1-floor
H22=results/savio/h22
OUT=results/savio/h23
MANIFEST=configs/rollout/f2d-all.manifest.json
ROUTES=results/savio/f2d-all/routes.jsonl
export PYTHONPATH=src
git rev-parse HEAD

for VARIANT in plain centre vision; do
  RUN=$OUT/$VARIANT
  mkdir -p "$RUN"
  [ "$(ls -d "$H22/$VARIANT"/sae/L10_* | wc -l)" -eq 18 ] || { echo "H22 $VARIANT lacks 18 dictionaries" >&2; exit 2; }
  if [ "$VARIANT" = plain ]; then INPUT=results/savio/f2d-all/shards; else INPUT="$H22/$VARIANT/shards"; fi
  if [ ! -f "$RUN/directives.done" ]; then
    rm -rf "$RUN/directives"
    $PY -m discovery.emit_directives "$INPUT" --layer 10 --sae "$H22/$VARIANT"/sae/L10_* --manifests "$MANIFEST" \
      --primary-dictionary L10_k64_s0 --m1-min-support 3 --output "$RUN/directives"
    touch "$RUN/directives.done"
  fi
  [ -f "$RUN/report.json" ] || $PY "$EXP/score.py" --directives "$RUN/directives" --shared "$OUT/plain/directives" \
    --manifest "$MANIFEST" --routes "$ROUTES" --variant "$VARIANT" --output "$RUN/report.json"
  echo "$VARIANT scored after $SECONDS s"
done
