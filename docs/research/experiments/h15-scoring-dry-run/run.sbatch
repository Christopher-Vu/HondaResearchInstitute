#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h15-dry-run
#SBATCH --output=h15-dry-run-%j.out
#   POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-02:00:00 docs/research/experiments/h15-scoring-dry-run/run.sbatch
# DEV DRY RUN, NOT A VERDICT. H12's shards and dictionaries, no simulator. Protocol: protocol.md beside this file.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PY=.runtime/policy-venv/bin/python
if [ -n "${POLICY_VENV_LOCAL_TAR:-}" ]; then
  STAGE=$(mktemp -d "/tmp/h15-local-$SLURM_JOB_ID.XXXXXX")
  trap 'chmod -R u+w "$STAGE" 2>/dev/null; rm -rf "$STAGE" || true' EXIT
  tar -xf "$POLICY_VENV_LOCAL_TAR" -C "$STAGE"
  [ -x "$STAGE/bin/python" ] || { echo "$POLICY_VENV_LOCAL_TAR has no bin/python at its top level" >&2; exit 2; }
  PY=$STAGE/bin/python
  echo "policy venv staged at $PY after $SECONDS s"
fi

EXP=docs/research/experiments/h15-scoring-dry-run
OUT=results/savio/h15
LABEL="DEV DRY RUN, NOT A VERDICT: H15, throwaway key of public practice gaps on H12's dev pool"
DICTIONARY=L10_k64_s0
SHARDS=(results/savio/step5-background-wave3/shards results/savio/step5-confirm-p4/shards
        results/savio/step5-confirm-p7/shards results/savio/step5-pilot-p19-main/shards)
MANIFESTS=(configs/rollout/step5-background-wave3.manifest.json configs/rollout/step5-confirm-p4.manifest.json
           configs/rollout/step5-confirm-p7.manifest.json configs/rollout/step5-pilot-p19-main.manifest.json)
ROUTES=(results/savio/step5-background-wave3/routes.jsonl results/savio/step5-confirm-p4/routes.jsonl
        results/savio/step5-confirm-p7/routes.jsonl results/savio/step5-pilot-p19-main/routes.jsonl)
mkdir -p "$OUT"
echo "$LABEL" > "$OUT/DEV-DRY-RUN-NOT-A-VERDICT.txt"
export PYTHONPATH=src

[ -f "$OUT/residual-shards.done" ] || {
  $PY -m discovery.residualize "${SHARDS[@]}" --layer 10 --model "$OUT/action_residual.npz" --output "$OUT/residual-shards"
  touch "$OUT/residual-shards.done"
  echo "residual shards written after $SECONDS s"
}
for SEED in 0 1 2 3 4 5; do
  for K in 32 48 64; do
    RUN=$OUT/sae/L10_k${K}_s${SEED}
    [ -f "$RUN/metrics.json" ] && continue
    $PY -m discovery.sae "$OUT/residual-shards" --layer 10 --k "$K" --seed "$SEED" --frame-means --output "$RUN" \
      | grep -E '"(explained_variance|train_tokens)"'
  done
done
echo "residual dictionaries trained after $SECONDS s"

$PY -m discovery.emit_directives "${SHARDS[@]}" --layer 10 --sae results/savio/h12/sae/L10_* \
  --manifests "${MANIFESTS[@]}" --primary-dictionary "$DICTIONARY" --output "$OUT/directives/non_residualized"
$PY -m discovery.emit_directives "$OUT/residual-shards" --layer 10 --sae "$OUT"/sae/L10_* --output "$OUT/directives/action_residual"
echo "directives emitted after $SECONDS s"

score() {  # key name, report file, then any extra scoring_run options
  local key=$1 report=$2
  shift 2
  [ -f "$OUT/throwaway/$key/key.json" ] || $PY "$EXP/build_key.py" "$key" "$OUT/throwaway/$key"
  [ -f "$report" ] || $PY -m harness.scoring_run --directives "$OUT"/directives/* \
    --key "$OUT/throwaway/$key/key.json" --salt "$OUT/throwaway/$key/salt" --commitment "$OUT/throwaway/$key/commitment.txt" \
    --manifests "${MANIFESTS[@]}" --routes "${ROUTES[@]}" --efficacy-rule prd_9_1 --label "$LABEL ($key)" \
    --output "$report" "$@"
}
score as-labelled "$OUT/report-as-labelled.json" --dictionary "$DICTIONARY"
score as-labelled "$OUT/report-all-dictionaries.json"
score branch "$OUT/report-branch.json" --dictionary "$DICTIONARY"
echo "scoring done after $SECONDS s"

$PY "$EXP/check.py" "$OUT" --output "$OUT/check.json"
