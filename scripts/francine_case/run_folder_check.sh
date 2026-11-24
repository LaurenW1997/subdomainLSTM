#!/bin/bash
# Francine run, last look before submitting. Reads only.
R=/work/yixuan97/Louisiana/Louisiana100m/Subgrid
cd $R || exit 1
echo "== ocean_hires.in, lines that matter"
grep -nE '^\s*(NtileI|NtileJ|NTIMES|DT|NDTFAST|NRREC|NHIS|NDEFHIS|NRST|DSTART|TIDE_START|TIME_REF|GRDNAME|ININAME|BRYNAME|NFFILES|FRCNAME|HISNAME|RSTNAME|VARNAME)\b' ROMS/ocean_hires.in | cut -c1-170
echo "== continuation lines of FRCNAME"
awk '/^\s*FRCNAME/{p=1} p{print NR": "$0} p&&!/\\\s*$/{p=0}' ROMS/ocean_hires.in | cut -c1-170
echo "== every absolute path named in ocean_hires.in (uncommented part of the line)"
sed 's/!.*//' ROMS/ocean_hires.in | grep -oE '/[A-Za-z0-9_./-]+' | sort -u | while read p; do if [ -e "$p" ]; then echo "  there   $(stat -c %s "$p" 2>/dev/null)  $p"; else echo "  MISSING $p"; fi; done
echo "== relative names in ocean_hires.in"
sed 's/!.*//' ROMS/ocean_hires.in | grep -E '^\s*(GRDNAME|ININAME|VARNAME|HISNAME|RSTNAME|SPOSNAM|APARNAM|SPARNAM|BPARNAM|FPOSNAM|USRNAME)\b' | cut -c1-170
echo "== namelist.hrldas"
grep -nE '^\s*(HRLDAS_SETUP_FILE|INDIR|SPATIAL_FILENAME|OUTDIR|START_YEAR|START_MONTH|START_DAY|START_HOUR|START_MIN|KHOUR|KDAY|RESTART_FILENAME_REQUESTED|FORCING_TIMESTEP|NOAH_TIMESTEP|OUTPUT_TIMESTEP|RESTART_FREQUENCY_HOURS|FORC_TYP)\b' namelist.hrldas | cut -c1-170
echo "== hydro.namelist"
grep -nE '^\s*(RESTART_FILE|GEO_STATIC_FLNM|GEO_FINEGRID_FLNM|HYDROTBL_F|LAND_SPATIAL_META_FLNM|rst_dt|out_dt|GW_RESTART|route_link_f|udmap_file|GWBUCKPARM_file)\b' hydro.namelist | cut -c1-170
grep -niE 'hydro_restart|hydro_obs' hydro.namelist ROMS/ocean_hires.in couple.in 2>/dev/null | cut -c1-170
echo "== files named in the two land namelists"
for f in namelist.hrldas hydro.namelist; do sed 's/!.*//' $f | grep -oE "[\"'][^\"']+[\"']" | tr -d "\"'" | grep -E '[./]' | sort -u | while read p; do [ -z "$p" ] && continue; if [ -e "$p" ]; then echo "  there   $p"; else echo "  MISSING $p   ($f)"; fi; done; done
echo "== couple.in"
sed 's/!.*//' couple.in | grep -vE '^\s*$' | cut -c1-170
echo "== executable"
ls -la coawstM model_compile/coawstM | cut -c1-200
ls -laL coawstM | cut -c1-200
echo "== inflow"
md5sum hydro_obs.txt; head -3 hydro_obs.txt; sed -n '866,868p' hydro_obs.txt; tail -1 hydro_obs.txt; wc -l hydro_obs.txt
echo "== forcing folders"
ls /work/yixuan97/Francine_case/forcing_francine_interp | wc -l; ls /work/yixuan97/Francine_case/forcing_francine_interp | head -1; ls /work/yixuan97/Francine_case/forcing_francine_interp | tail -1
ls -la /work/yixuan97/Francine_case/HRRR_on_roms /work/yixuan97/Francine_case/boundary | cut -c25-200
echo "== output folders and logs now"
for d in OUTPUT OUTPUT/ROMS HYDROOUT LDASOUT; do [ -d $d ] && echo "$d: $(ls $d | wc -l) entries" || echo "$d: no such folder"; done
ls -la francine.* 2>/dev/null; ls -lat | head -25 | cut -c25-200
echo "== sub_subgrid"
cat sub_subgrid
echo "== queue and allocation"
squeue -u yixuan97 -o '%.10i %.9P %.20j %.8T %.10M %.10l %.5D %R'
sinfo -p checkpt -o '%.10P %.5a %.11l %.6D %.10T' | head
(showquota 2>/dev/null || true) | head -8
(balance 2>/dev/null || sbalance 2>/dev/null || true) | head -8
df -h /work | tail -1
