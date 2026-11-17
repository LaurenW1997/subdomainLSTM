#!/bin/bash
#SBATCH -J eval_protocol
#SBATCH -A hpc_you3a02
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH -n 16
#SBATCH --gres=gpu:1
#SBATCH -t 00:45:00
#SBATCH -o /work/yixuan97/subdomainLSTM/logs/%x_%j.out
#SBATCH -e /work/yixuan97/subdomainLSTM/logs/%x_%j.err

# Events, hurricanes and timing of the rises for groups of models that differ only in the seed (scripts/report/eval_protocol.py).
# EVAL_GROUPS="name1=runA,runB,... name2=runC,runD,..." sbatch slurm/eval_protocol_mike.sbatch   -> runs/protocol_<name>/protocol_station.csv
# A name may carry the hours of data that have not arrived: name@P (partner stations) or name@P@O (partner stations, the station itself),
# e.g. river50_late2@2=runA,runB  or  river50_both1@1@1=runA,runB. EVAL_ARGS: further options for every group (e.g. "--rt-fill partners").
set -euo pipefail
ROOT=/work/yixuan97/subdomainLSTM
cd $ROOT/repo/scripts/report
export OMP_NUM_THREADS=16
# the container is called directly, not through the module's python launcher (see train_mike.sbatch)
PY="singularity exec -B /work,/project,/usr/local/packages,/var/scratch, --nv --pwd $PWD /project/containers/images/pytorch-2.10.0.sif python"
for G in $EVAL_GROUPS; do   # not GROUPS: that name is a bash built-in (the group ids of the user)
  SPEC=${G%%=*}; RUNS=$(echo ${G#*=} | tr ',' ' ')
  IFS=@ read -r NAME PLATE OLATE <<< "$SPEC"
  echo "=== $NAME (newest hours removed: partner stations ${PLATE:-0}, own ${OLATE:-0}): $RUNS"
  $PY eval_protocol.py --runs-dir $ROOT/runs --runs $RUNS --dataset $ROOT/data/${DATASET:-dataset_v6} --out $ROOT/runs/protocol_$NAME --partner-late ${PLATE:-0} --own-late ${OLATE:-0} ${EVAL_ARGS:-}
done
