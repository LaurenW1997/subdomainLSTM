#!/bin/bash
#SBATCH -J eval_ensemble
#SBATCH -A hpc_you3a02
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH -n 16
#SBATCH --gres=gpu:1
#SBATCH -t 00:30:00
#SBATCH -o /work/yixuan97/subdomainLSTM/logs/%x_%j.out
#SBATCH -e /work/yixuan97/subdomainLSTM/logs/%x_%j.err

# Mean of several models that differ only in the random seed (scripts/report/eval_ensemble.py) on SuperMike-3.
# RUNS="v14_stale25 v15_seed1 ..." OUT=v15_mean5 sbatch slurm/eval_ensemble_mike.sbatch
set -euo pipefail
module purge
module load pytorch/2.10.0
ROOT=/work/yixuan97/subdomainLSTM
cd $ROOT/repo/scripts/report
export OMP_NUM_THREADS=16
# `module load pytorch` rewrites the launcher ~/.local/bin/modules/pytorch/2.10.0/python every time it is loaded. When several
# jobs start within the same minute the launcher ends up with its command line repeated, and a job that is already running then
# runs its python command again after it has finished (13 Nov 2026: five trainings ran twice and the second pass overwrote
# best.pt). So the container is called directly here and the launcher is not used.
PY="singularity exec -B /work,/project,/usr/local/packages,/var/scratch, --nv --pwd $PWD /project/containers/images/pytorch-2.10.0.sif python"
$PY eval_ensemble.py --runs-dir $ROOT/runs --runs $RUNS --dataset $ROOT/data/${DATASET:-dataset_v6} --out $ROOT/runs/$OUT
