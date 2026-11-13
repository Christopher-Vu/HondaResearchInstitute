#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h20-centring
#SBATCH --output=h20-centring-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-03:00:00 docs/research/experiments/h20-centring-second-pool/run.sbatch
# DEV DRY RUN, NOT A VERDICT. H1's pool, a throwaway public key, no simulator. Protocol: protocol.md beside this file.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h20-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi

EXP=docs/research/experiments/h20-centring-second-pool
OUT=results/savio/h20
LABEL="DEV DRY RUN, NOT A VERDICT: H20 centring on H1's pool"
NAMES=(step4-dev-pool step4-dev-pool-wave2 step5-pilot-p4-main step5-pilot-p7-main step5-pilot-p8-main)
SHARDS=(); MANIFESTS=(); ROUTES=()
for NAME in "${NAMES[@]}"; do
  SHARDS+=("results/savio/$NAME/shards"); MANIFESTS+=("configs/rollout/$NAME.manifest.json"); ROUTES+=("results/savio/$NAME/routes.jsonl")
done
KEY=$OUT/throwaway
export PYTHONPATH=src
git rev-parse HEAD
mkdir -p "$OUT"
[ -f "$KEY/key.json" ] || $PY "$EXP/build_key.py" "$KEY"

prepare() {  # variant: writes $OUT/<variant>/shards, or for plain points at the pool itself
  local variant=$1 run=$OUT/$1
  mkdir -p "$run"
  [ "$variant" = plain ] && return 0
  [ -f "$run/shards.done" ] && return 0
  rm -rf "$run/shards"
  if [ "$variant" = centre ]; then
    $PY -m discovery.residual_controls centre "${SHARDS[@]}" --layer 10 --output "$run/shards" | tee "$run/fit.json"
  else
    $PY -m discovery.residualize "${SHARDS[@]}" --layer 10 --model "$run/action_residual.npz" --output "$run/shards" | tee "$run/fit.json"
  fi
  touch "$run/shards.done"
}

for VARIANT in plain centre vision; do
  RUN=$OUT/$VARIANT
  prepare "$VARIANT"
  if [ "$VARIANT" = plain ]; then INPUT=("${SHARDS[@]}"); EXTRA=(--manifests "${MANIFESTS[@]}"); else INPUT=("$RUN/shards"); EXTRA=(); fi
  for SEED in 0 1 2 3 4 5; do
    for K in 32 48 64; do
      SAE=$RUN/sae/L10_k${K}_s${SEED}
      [ -f "$SAE/metrics.json" ] && continue
      $PY -m discovery.sae "${INPUT[@]}" --layer 10 --k "$K" --seed "$SEED" --frame-means --output "$SAE" \
        | grep -E '"(explained_variance|train_tokens)"'
    done
  done
  if [ ! -f "$RUN/directives.done" ]; then
    rm -rf "$RUN/directives"
    $PY -m discovery.emit_directives "${INPUT[@]}" --layer 10 --sae "$RUN"/sae/L10_* "${EXTRA[@]}" --output "$RUN/directives"
    touch "$RUN/directives.done"
  fi
  DIRECTIVES=("$OUT/plain/directives")
  [ "$VARIANT" = plain ] || DIRECTIVES+=("$RUN/directives")
  [ -f "$RUN/report.json" ] || $PY "$EXP/score.py" --directives "${DIRECTIVES[@]}" --key "$KEY/key.json" \
    --manifests "${MANIFESTS[@]}" --routes "${ROUTES[@]}" --label "$LABEL ($VARIANT)" --output "$RUN/report.json"
  echo "$VARIANT scored after $SECONDS s"
done

$PY "$EXP/read.py" "$OUT" --output "$OUT/result.json"
