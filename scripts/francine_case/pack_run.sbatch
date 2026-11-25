#!/bin/bash
#SBATCH -J pack_francine
#SBATCH -A loni_zxue_lonl
#SBATCH -p single
#SBATCH -N 1
#SBATCH -n 16
#SBATCH -t 02:00:00
#SBATCH -o /work/yixuan97/Francine_case/logs/pack_%j.out
#SBATCH -e /work/yixuan97/Francine_case/logs/pack_%j.err
# The hourly water level of the Francine run in the layout of the Ida archive. The output of the run is only read;
# only /work/yixuan97/Francine_case/packed is written.
cd /work/yixuan97/Francine_case/packed
R=/work/yixuan97/Louisiana/Louisiana100m/Subgrid
/work/yixuan97/conda_envs/cfml/bin/python ../code/pack_run.py --run $R --grid $R/ROMS/hires_roms_grid_sub_smooth.nc --out water_level_Francine_hindcast.nc --workers 12
echo "finished"
