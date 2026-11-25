#!/bin/bash
#SBATCH -J fields_francine
#SBATCH -A loni_zxue_lonl
#SBATCH -p single
#SBATCH -N 1
#SBATCH -n 16
#SBATCH -t 00:40:00
#SBATCH -o /work/yixuan97/Francine_case/logs/fields_%j.out
#SBATCH -e /work/yixuan97/Francine_case/logs/fields_%j.err
# Hourly fields of the Francine run for animations, 9 to 14 September 2024. The output of the run is only read;
# only /work/yixuan97/Francine_case/run_fields is written.
cd /work/yixuan97/Francine_case/run_fields
R=/work/yixuan97/Louisiana/Louisiana100m/Subgrid
/work/yixuan97/conda_envs/cfml/bin/python ../code/run_fields.py --run $R --grid $R/ROMS/hires_roms_grid_sub_smooth.nc --hrrr ../hrrr/hrrr_f00 \
  --start "2024-09-09 00:00" --end "2024-09-14 00:00" --base-start "2024-09-05 21:00" --base-end "2024-09-08 23:00" --out francine_run_fields.npz --workers 16
echo "finished"
