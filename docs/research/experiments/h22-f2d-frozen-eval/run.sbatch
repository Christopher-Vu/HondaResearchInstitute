#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h22-f2d-eval
#SBATCH --output=h22-f2d-eval-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-03:00:00 docs/research/experiments/h22-f2d-frozen-eval/run.sbatch
# DEV ONLY, NOT BLIND. Frozen methods (tag methods-frozen-f2d-v1) on H21's shards. Protocol: protocol.md beside this file.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

git merge-base --is-ancestor methods-frozen-f2d-v1 HEAD \
  || { echo "HEAD does not contain methods-frozen-f2d-v1; the freeze comes first" >&2; exit 2; }

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h22-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi

EXP=docs/research/experiments/h22-f2d-frozen-eval
OUT=results/savio/h22
SHARDS=results/savio/f2d-all/shards
MANIFEST=configs/rollout/f2d-all.manifest.json
ROUTES=results/savio/f2d-all/routes.jsonl
export PYTHONPATH=src
git rev-parse HEAD
mkdir -p "$OUT"

prepare() {  # variant: writes $OUT/<variant>/shards; plain reads the H21 shards as they are
  local variant=$1 run=$OUT/$1
  mkdir -p "$run"
  [ "$variant" = plain ] && return 0
  [ -f "$run/shards.done" ] && return 0
  rm -rf "$run/shards"
  if [ "$variant" = centre ]; then
    $PY -m discovery.residual_controls centre "$SHARDS" --layer 10 --output "$run/shards" | tee "$run/fit.json"
  else
    $PY -m discovery.residualize "$SHARDS" --layer 10 --model "$run/action_residual.npz" --output "$run/shards" | tee "$run/fit.json"
  fi
  touch "$run/shards.done"
}

for VARIANT in plain centre vision; do
  RUN=$OUT/$VARIANT
  prepare "$VARIANT"
  if [ "$VARIANT" = plain ]; then INPUT="$SHARDS"; else INPUT="$RUN/shards"; fi
  for SEED in 0 1 2 3 4 5; do
    for K in 32 48 64; do
      SAE=$RUN/sae/L10_k${K}_s${SEED}
      [ -f "$SAE/metrics.json" ] && continue
      $PY -m discovery.sae "$INPUT" --layer 10 --k "$K" --seed "$SEED" --frame-means --output "$SAE" \
        | grep -E '"(explained_variance|train_tokens)"'
    done
  done
  if [ ! -f "$RUN/directives.done" ]; then
    rm -rf "$RUN/directives"
    $PY -m discovery.emit_directives "$INPUT" --layer 10 --sae "$RUN"/sae/L10_* --manifests "$MANIFEST" \
      --primary-dictionary L10_k64_s0 --output "$RUN/directives"
    touch "$RUN/directives.done"
  fi
  [ -f "$RUN/report.json" ] || $PY "$EXP/score.py" --directives "$RUN/directives" --shared "$OUT/plain/directives" \
    --manifest "$MANIFEST" --routes "$ROUTES" --variant "$VARIANT" --output "$RUN/report.json"
  echo "$VARIANT scored after $SECONDS s"
done
