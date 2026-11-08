#!/bin/bash
#SBATCH -J subdomainLSTM
#SBATCH -A loni_zxue_lonl
#SBATCH -p gpu2
#SBATCH --qos=gpu2
#SBATCH -N 1
#SBATCH -n 8
#SBATCH --gres=gpu:1
#SBATCH -t 12:00:00
#SBATCH -o /work/yixuan97/subdomainLSTM/logs/%x_%j.out
#SBATCH -e /work/yixuan97/subdomainLSTM/logs/%x_%j.err

# Global LSTM training on QBD. The pytorch/2.10.0 module provides a singularity
# wrapper named `python` (binds /work, /project, /scratch; --nv for the GPU);
# it only works on compute nodes and conflicts with the default conda module.
set -euo pipefail
module purge
module load pytorch/2.10.0
ROOT=/work/yixuan97/subdomainLSTM
RUN=${RUN_NAME:-v0_gpu}
DATASET=${DATASET:-dataset}
cd $ROOT/repo/scripts/train
export OMP_NUM_THREADS=8
nvidia-smi -L || true
python -c "import torch, pandas; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'pandas', pandas.__version__)"
python train.py --dataset $ROOT/data/$DATASET --out $ROOT/runs/$RUN \
  --epochs ${EPOCHS:-20} --steps ${STEPS:-2000} --batch ${BATCH:-1024} \
  --hidden ${HIDDEN:-128} --layers ${LAYERS:-2} --lr ${LR:-1e-3}
