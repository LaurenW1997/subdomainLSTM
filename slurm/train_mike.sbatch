#!/bin/bash
#SBATCH -J subdomainLSTM
#SBATCH -A hpc_you3a02
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH -n 16
#SBATCH --gres=gpu:1
#SBATCH -t 01:30:00
#SBATCH -o /work/yixuan97/subdomainLSTM/logs/%x_%j.out
#SBATCH -e /work/yixuan97/subdomainLSTM/logs/%x_%j.err

# Global LSTM training on SuperMike-3 (same layout as train_qbd.sbatch; the pytorch/2.10.0 module
# conflicts with conda/python modules, so purge first). gpu partition: 8 nodes x 4 A100, QoS gpu,
# billed 64 SU per GPU-hour on allocation hpc_you3a02.
set -euo pipefail
module purge
module load pytorch/2.10.0
ROOT=/work/yixuan97/subdomainLSTM
RUN=${RUN_NAME:-v0_gpu}
DATASET=${DATASET:-dataset_v4}
cd $ROOT/repo/scripts/train
export OMP_NUM_THREADS=16
nvidia-smi -L || true
python -c "import torch, pandas; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'pandas', pandas.__version__)"
python train.py --dataset $ROOT/data/$DATASET --out $ROOT/runs/$RUN \
  --epochs ${EPOCHS:-20} --steps ${STEPS:-2000} --batch ${BATCH:-1024} \
  --hidden ${HIDDEN:-128} --layers ${LAYERS:-2} --lr ${LR:-1e-3} --lookback ${LOOKBACK:-72} ${EXTRA:-}
