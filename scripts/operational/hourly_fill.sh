#!/bin/bash
# Forecasts from every hour, for the station figures (observed level and continuous lines for 1, 3 and 6 h lead need a
# forecast from every hour; the runs on a schedule are every 6 hours). Both models, run afterwards with the data complete:
# one fetch of the water levels, every forecast time takes only the readings up to itself, the model with partner stations
# reads the inputs the other run saved. Fills every hour from START to two hours ago that has no forecast yet.
#   output: $T/run/<forecast time>/, $T/partners/<forecast time>/, $T/levels/ (one file per call), $T/fill.log, $T/status.csv
# Started by cron every 6 hours next to shadow_run.sh, or by hand. Does nothing after STOP.
#   crontab (server clock UTC-6):  45 1,7,13,19 * * * /bin/bash /data/ywan245/subdomainLSTM/shadow_20261117/hourly_fill_v1.sh
set -u
R=/data/ywan245/subdomainLSTM
T=${HOURLY_DIR:-$R/shadow_20261117/hourly}
P=$R/partner_test_20261117                      # HRRR / MRMS cell files (new hours are added, nothing is replaced)
PY=$R/venv/bin/python
START="2026-11-17 07:00"                        # the hourly test before it ends with 17 November 06 UTC
STOP="2026-11-21 06:00"                         # UTC

now=$(date -u +%s)
[ "$now" -gt "$(date -u -d "$STOP" +%s)" ] && exit 0
mkdir -p $T/levels
exec 9> $T/lock; flock -n 9 || exit 0
cd $R/repo/scripts/operational
L=$T/fill.log

e=$(( (now - 7200) / 3600 * 3600 ))             # newest forecast time: two hours ago, the readings of that hour have arrived
miss=()
for ((t = $(date -u -d "$START" +%s); t <= e; t += 3600)); do
  D=$(date -u -d "@$t" +%Y%m%dT%H)
  [ -e $T/partners/$D/forecast.csv ] || miss+=($t)
done
[ ${#miss[@]} -eq 0 ] && exit 0
echo "=== $(date -u '+%Y-%m-%d %H:%M:%S') UTC: ${#miss[@]} forecast times to fill, $(date -u -d "@${miss[0]}" +%Y-%m-%dT%H) .. $(date -u -d "@$e" +%Y-%m-%dT%H)" >> $L

B=$(date -u -d "@$((miss[0] - 100 * 3600))" +%Y-%m-%dT%H)      # 72 h of input and 24 h before it for the gap filling
E=$(date -u -d "@$((e + 3540))" +%Y-%m-%dT%H:%M)
LV=$T/levels/levels_$(date -u -d "@$((miss[0] - 100 * 3600))" +%Y%m%dT%H)_$(date -u -d "@$e" +%Y%m%dT%H).pkl
for n in 1 2 3 4 5 6; do                        # the USGS service drops connections: several attempts
  [ -e $LV ] && break
  timeout 1500 $PY fetch_levels_span.py --model $R/runs/v15r_mean5 --begin $B --end $E --out $LV 2>&1 | tail -1 | cut -c1-220 >> $L
  [ -e $LV ] || sleep 90
done
[ -e $LV ] || { echo "the water levels could not be fetched" >> $L; exit 1; }

ok=0
for t in "${miss[@]}"; do
  C=$(date -u -d "@$t" +%Y-%m-%dT%H); D=$(date -u -d "@$t" +%Y%m%dT%H)
  timeout 900 $PY forecast.py --model $R/runs/v15r_mean5 --cycle $C --out $T/run --levels-all $LV --wind-cache $P/wind --rain-cache $P/rain 2>&1 | grep "Error\|Traceback" >> $L
  [ -e $T/run/$D/forecast.csv ] && timeout 600 $PY forecast.py --model $R/runs/v21_behaviour_mean5 --cycle $C --out $T/partners --inputs-from $T/run --wind-cache $P/wind --rain-cache $P/rain 2>&1 | grep "Error\|Traceback" >> $L
  [ -e $T/partners/$D/forecast.csv ] && ok=$((ok + 1))
done
[ -e $T/status.csv ] || echo "written_utc,first_forecast_time,last_forecast_time,to_fill,filled,levels_file" > $T/status.csv
echo "$(date -u +%Y-%m-%dT%H:%M:%S),$(date -u -d "@${miss[0]}" +%Y%m%dT%H),$(date -u -d "@$e" +%Y%m%dT%H),${#miss[@]},$ok,$(basename $LV)" >> $T/status.csv
echo "    filled $ok of ${#miss[@]}, finished $(date -u '+%H:%M:%S')" >> $L
