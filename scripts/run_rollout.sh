#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=simlingo-step1
#SBATCH --time=0-02:00:00
#SBATCH --output=results/step1/slurm-%j.out
#
# Step 1 scaffold — single SimLingo rollout under Slurm on Savio.
#   bash scripts/submit.sh gpu scripts/run_rollout.sh <config>
# Blocked until configs/cluster/savio.yaml has a GPU partition.
# Deliberately minimal: no Ray, no fan-out. One route.
# See docs/steps/01-smallest-rollout.md
#
# NOTE: #SBATCH directives must appear before the first executable line,
# so keep `set -euo pipefail` and everything else below this block.
set -euo pipefail

CONFIG="${1:-configs/rollout/step1-single-route.yaml}"
mkdir -p results/step1

echo "=== node and GPU ==="
hostname
nvidia-smi

echo "=== container runtime ==="
# Savio almost certainly requires Singularity/Apptainer rather than Docker.
command -v apptainer || command -v singularity || echo "WARN: no apptainer/singularity on PATH"

echo "=== config ==="
cat "$CONFIG"
echo "config sha256: $(sha256sum "$CONFIG" | cut -d' ' -f1)"

echo "=== rollout ==="
# TODO(step1): start the CARLA server off-screen, wait for the port, then run
# the Bench2Drive agent on one route. Record wall-clock around the rollout only,
# not around container startup.
echo "not yet implemented — see docs/steps/01-smallest-rollout.md"
