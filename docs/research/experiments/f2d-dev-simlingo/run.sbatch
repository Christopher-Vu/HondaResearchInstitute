#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=f2d-dev
#SBATCH --output=f2d-dev-%j.out
#   VARIANT_ID=v1 LAYER=10 POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar \
#     bash scripts/submit.sh gpu_a40 --time=0-04:00:00 docs/research/experiments/f2d-dev-simlingo/run.sbatch
# Our policy-venv.tar lacks sklearn, which dev_eval imports; Jerry's (H22's) has it.
# DEV ONLY. H22's pipeline on the Fail2Drive test pool; one VARIANT_ID per row of VARIANTS.md.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

: "${VARIANT_ID:?set VARIANT_ID to a row of VARIANTS.md}"
LAYER=${LAYER:-10}
MODEL=${MODEL:-simlingo}
PREPS=${PREPS:-plain centre vision}
KS=${KS:-32 48 64}
SEEDS=${SEEDS:-0 1 2 3 4 5}
FLOORS=${FLOORS:-20 5}
GAPS=${GAPS:-F2D_PedestriansOnRoad F2D_FullyBlocked F2D_BadParking F2D_CustomObstacles F2D_Wall}

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/f2d-dev-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  PY=$STAGE/bin/python
  echo "policy venv staged after $SECONDS s"
fi

EXP=docs/research/experiments/f2d-dev-simlingo
OUT=results/savio/f2d-dev/$MODEL/$VARIANT_ID
SHARDS=results/savio/f2d-test-$MODEL/shards
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
ROUTES=results/savio/f2d-test-$MODEL/routes.jsonl
export PYTHONPATH=src
git rev-parse HEAD
mkdir -p "$OUT"

for PREP in $PREPS; do
  RUN=$OUT/$PREP
  mkdir -p "$RUN"
  INPUT=$SHARDS
  if [ "$PREP" != plain ]; then
    INPUT=$RUN/shards
    if [ ! -f "$RUN/shards.done" ]; then
      rm -rf "$INPUT"
      if [ "$PREP" = centre ]; then
        $PY -m discovery.residual_controls centre "$SHARDS" --layer "$LAYER" --output "$INPUT" | tee "$RUN/fit.json"
      else
        $PY -m discovery.residualize "$SHARDS" --layer "$LAYER" --model "$RUN/action_residual.npz" --output "$INPUT" \
          | tee "$RUN/fit.json"
      fi
      touch "$RUN/shards.done"
    fi
  fi
  for SEED in $SEEDS; do
    for K in $KS; do
      SAE=$RUN/sae/L${LAYER}_k${K}_s${SEED}
      [ -f "$SAE/metrics.json" ] && continue
      $PY -m discovery.sae "$INPUT" --layer "$LAYER" --k "$K" --seed "$SEED" --frame-means --output "$SAE" \
        | grep -E '"(explained_variance|train_tokens)"'
    done
  done
  for FLOOR in $FLOORS; do
    DIR=$RUN/directives-ms$FLOOR
    if [ ! -f "$DIR.done" ]; then
      rm -rf "$DIR"
      $PY -m discovery.emit_directives "$INPUT" --layer "$LAYER" --sae "$RUN"/sae/L${LAYER}_* --manifests "$MANIFEST" \
        --primary-dictionary "L${LAYER}_k64_s0" --m1-min-support "$FLOOR" --output "$DIR"
      touch "$DIR.done"
    fi
    SHARED=$OUT/plain/directives-ms$FLOOR
    [ -d "$SHARED" ] || SHARED=$DIR
    $PY "$EXP/score.py" --directives "$DIR" --shared "$SHARED" --manifest "$MANIFEST" --routes "$ROUTES" \
      --variant "$PREP-ms$FLOOR" --gaps $GAPS --output "$RUN/report-ms$FLOOR.json"
  done
  echo "$PREP scored after $SECONDS s"
done
