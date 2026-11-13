#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h18-controls
#SBATCH --output=h18-controls-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-02:00:00 docs/research/experiments/h18-residual-controls/run.sbatch
# DEV ONLY, NOT A VERDICT. H12's shards, H15's throwaway key and plain directives, no simulator. Protocol: protocol.md beside this file.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h18-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi

EXP=docs/research/experiments/h18-residual-controls
H15=results/savio/h15
OUT=results/savio/h18
LABEL="DEV DRY RUN, NOT A VERDICT: H18 residualization control on H12's dev pool"
SHARDS=(results/savio/step5-background-wave3/shards results/savio/step5-confirm-p4/shards
        results/savio/step5-confirm-p7/shards results/savio/step5-pilot-p19-main/shards)
MANIFESTS=(configs/rollout/step5-background-wave3.manifest.json configs/rollout/step5-confirm-p4.manifest.json
           configs/rollout/step5-confirm-p7.manifest.json configs/rollout/step5-pilot-p19-main.manifest.json)
ROUTES=(results/savio/step5-background-wave3/routes.jsonl results/savio/step5-confirm-p4/routes.jsonl
        results/savio/step5-confirm-p7/routes.jsonl results/savio/step5-pilot-p19-main/routes.jsonl)
KEY=$H15/throwaway/as-labelled
export PYTHONPATH=src
git rev-parse HEAD
for f in "$H15/action_residual.npz" "$KEY/key.json" "$KEY/salt" "$KEY/commitment.txt"; do
  [ -f "$f" ] || { echo "missing $f: H18 needs H15's outputs" >&2; exit 2; }
done
[ -d "$H15/directives/non_residualized" ] || { echo "missing H15's plain directives" >&2; exit 2; }

for CONTROL in shuffle top-variance; do
  RUN=$OUT/$CONTROL
  mkdir -p "$RUN"
  if [ ! -f "$RUN/shards.done" ]; then
    MATCH=()
    [ "$CONTROL" = top-variance ] && MATCH=(--match "$H15/action_residual.npz")
    rm -rf "$RUN/shards"
    $PY -m discovery.residual_controls "$CONTROL" "${SHARDS[@]}" --layer 10 --seed 18 "${MATCH[@]}" --output "$RUN/shards" \
      | tee "$RUN/fit.json"
    touch "$RUN/shards.done"
    echo "$CONTROL shards written after $SECONDS s"
  fi
  for SEED in 0 1 2 3 4 5; do
    for K in 32 48 64; do
      SAE=$RUN/sae/L10_k${K}_s${SEED}
      [ -f "$SAE/metrics.json" ] && continue
      $PY -m discovery.sae "$RUN/shards" --layer 10 --k "$K" --seed "$SEED" --frame-means --output "$SAE" \
        | grep -E '"(explained_variance|train_tokens)"'
    done
  done
  if [ ! -f "$RUN/directives.done" ]; then
    rm -rf "$RUN/directives"
    $PY -m discovery.emit_directives "$RUN/shards" --layer 10 --sae "$RUN"/sae/L10_* --output "$RUN/directives"
    touch "$RUN/directives.done"
  fi
  [ -f "$RUN/report-all-dictionaries.json" ] || $PY -m harness.scoring_run --directives "$H15/directives/non_residualized" "$RUN/directives" \
    --key "$KEY/key.json" --salt "$KEY/salt" --commitment "$KEY/commitment.txt" \
    --manifests "${MANIFESTS[@]}" --routes "${ROUTES[@]}" --efficacy-rule prd_9_1 --label "$LABEL ($CONTROL)" \
    --replicates 1000 --output "$RUN/report-all-dictionaries.json" > /dev/null
  echo "$CONTROL scored after $SECONDS s"
done

$PY "$EXP/read.py" "$OUT" --output "$OUT/result.json"
