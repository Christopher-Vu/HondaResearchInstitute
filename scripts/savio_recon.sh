#!/usr/bin/env bash
# Savio reconnaissance — run this on a LOGIN node right after you authenticate.
# Read-only, no jobs submitted, takes seconds. Paste the output back.
#
# Answers Step 1 stages 1.1-1.2 and several Step 0 Track B items without
# waiting for the support email. See docs/steps/01-smallest-rollout.md
#
#   bash savio_recon.sh 2>&1 | tee ~/savio-recon.txt

echo "######## 1. identity and allowance"
whoami; id -Gn
echo "--- projects/accounts visible to slurm ---"
sacctmgr -nP show assoc user="$(whoami)" format=Account,Partition,QOS 2>&1 | head -40

echo "######## 2. partitions we can actually use"
sinfo -o '%20P %10a %12l %6D %10G %N' 2>&1 | head -40
echo "--- GPU partitions only ---"
sinfo -o '%20P %10G %6D %N' 2>&1 | grep -i gpu | head -20

echo "######## 3. QOS list (is savio_lowprio available to us?)"
sacctmgr -nP show qos format=Name,MaxWall,MaxTRES 2>&1 | head -30

echo "######## 4. container runtime"
for c in apptainer singularity podman docker; do
  printf '%-12s ' "$c"; command -v $c >/dev/null && $c --version 2>&1 | head -1 || echo "ABSENT"
done
echo "--- module system ---"
command -v module >/dev/null && { module --version 2>&1|head -2; echo "--- gpu/cuda/python modules ---"; module avail 2>&1 | grep -iE 'cuda|python|apptainer|singularity|ml/' | head -25; } || echo "no module command"

echo "######## 5. storage and quota"
echo "HOME=$HOME"; df -h "$HOME" 2>&1 | tail -2
for d in /global/scratch/users/$(whoami) /global/scratch/$(whoami) /clusterfs; do
  [ -d "$d" ] && { echo "--- $d"; df -h "$d" 2>&1|tail -1; }
done
command -v check_usage.sh >/dev/null && check_usage.sh 2>&1 | head -20
echo "--- quota ---"; quota -s 2>&1 | head -10

echo "######## 6. GPU visible from login node? (expect none; that is normal)"
command -v nvidia-smi >/dev/null && nvidia-smi -L 2>&1 | head -5 || echo "nvidia-smi absent on login node (normal)"

echo "######## 7. outbound network (can we pull from HF / GitHub?)"
for h in huggingface.co github.com; do
  printf '%-20s ' "$h"
  curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 "https://$h" 2>&1 | tail -1
done

echo "######## 8. python / ray availability"
python3 -V 2>&1; python3 -c 'import ray; print("ray", ray.__version__)' 2>&1 | tail -1

echo "######## DONE — paste this whole output back"
