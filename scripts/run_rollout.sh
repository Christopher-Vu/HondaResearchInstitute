#!/usr/bin/env bash
# Step 1 scaffold — single SimLingo rollout under Slurm on Savio.
#
# Fill the TBD values from Step 0 Track B (partition name, account) before use.
# Deliberately minimal: no Ray, no fan-out. One route. See
# docs/steps/01-smallest-rollout.md
set -euo pipefail

#SBATCH --job-name=simlingo-step1
#SBATCH --account=ic_cdss170fall
#SBATCH --partition=TBD-STEP0        # ask the program contact; do not guess
#SBATCH --qos=savio_normal           # not lowprio: we want this to not be preempted
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=0-02:00:00
#SBATCH --output=results/step1/slurm-%j.out

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
