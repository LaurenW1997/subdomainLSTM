#!/bin/bash
# Shadow runs on a schedule: the version that is run and the version with partner stations, every 6 hours, unattended,
# in a folder of their own under the user's account (sv7). Nothing is written to the group's operational system.
#
# One call per step, started by cron (see the crontab lines at the end of this file):
#   shadow_run.sh t31     31 min after a 00/06/12/18 UTC hour: both models on the data that have arrived  -> run_t31, partners_t31
#   shadow_run.sh t65     65 min after the hour: the same forecast time once more                          -> run_t65, partners_t65
#   shadow_run.sh score   7 h 20 min after the hour: the forecast time once more with the data complete
#                         (run_after, partners_after), then every forecast time scored so far              -> verification/<forecast time>/
# In every pair the model with partner stations reads the water levels and discharge the other run saved.
# status.csv gets one line per step: when, forecast time, step, exit codes of the two runs, stations with a forecast.
# The script does nothing after STOP, so the schedule ends by itself even if the crontab lines are left in place.
set -u
R=/data/ywan245/subdomainLSTM
T=${SHADOW_DIR:-$R/shadow_20261117}             # SHADOW_DIR and SHADOW_CYCLE (YYYY-MM-DDTHH) only for a trial by hand in another folder
P=$R/partner_test_20261117                      # HRRR / MRMS cell files (new hours are added, nothing is replaced)
PY=$R/venv/bin/python
STOP="2026-11-21 06:00"                         # UTC: the night after the group meeting of Friday 20 November
MODE=${1:?t31, t65 or score}

now=$(date -u +%s)
[ "$now" -gt "$(date -u -d "$STOP" +%s)" ] && exit 0
mkdir -p $T/log
exec 9> $T/log/lock.$MODE; flock -n 9 || exit 0  # never two of the same step at once

ref=$now; [ "$MODE" = score ] && ref=$((now - 7 * 3600))
c=$((ref / 21600 * 21600))                      # the 6-hourly forecast time this step belongs to
[ -n "${SHADOW_CYCLE:-}" ] && c=$(date -u -d "${SHADOW_CYCLE/T/ }:00" +%s)
C=$(date -u -d "@$c" +%Y-%m-%dT%H); D=$(date -u -d "@$c" +%Y%m%dT%H)
L=$T/log/$D.log
cd $R/repo/scripts/operational
echo "=== $MODE for $C, started $(date -u '+%Y-%m-%d %H:%M:%S') UTC" >> $L

n_ok() { [ -e "$1" ] && $PY -c "import pandas as pd, sys; print(int((pd.read_csv(sys.argv[1]).status == 'ok').sum()))" "$1" 2>/dev/null || echo 0; }

pair() {                                        # $1 = tag
  timeout 1500 $PY forecast.py --model $R/runs/v15r_mean5 --cycle $C --out $T/run_$1 --wind-cache $P/wind --rain-cache $P/rain >> $L 2>&1; a=$?
  b=-1
  if [ -e $T/run_$1/$D/forecast.csv ]; then
    timeout 900 $PY forecast.py --model $R/runs/v21_behaviour_mean5 --cycle $C --out $T/partners_$1 --inputs-from $T/run_$1 --wind-cache $P/wind --rain-cache $P/rain >> $L 2>&1; b=$?
  fi
  [ -e $T/status.csv ] || echo "written_utc,forecast_time,step,exit_no_partners,exit_partners,stations_no_partners,stations_partners" > $T/status.csv
  echo "$(date -u +%Y-%m-%dT%H:%M:%S),$D,$1,$a,$b,$(n_ok $T/run_$1/$D/forecast.csv),$(n_ok $T/partners_$1/$D/forecast.csv)" >> $T/status.csv
}

case $MODE in
  t31|t65) pair $MODE ;;
  score)
    [ -e $T/run_t31/$D/forecast.csv ] || [ -e $T/run_t65/$D/forecast.csv ] || { echo "no real-time run of $C, nothing to score" >> $L; exit 0; }
    pair after
    args=()                                     # only the folders that exist: a step that never ran must not stop the scoring
    for g in "no partners, run 31 min after the hour=$T/run_t31" "partners, run 31 min after the hour=$T/partners_t31"              "no partners, run 65 min after the hour=$T/run_t65" "partners, run 65 min after the hour=$T/partners_t65"              "no partners, data complete=$T/run_after" "partners, data complete=$T/partners_after"; do
      [ -d "${g#*=}" ] && args+=("$g")
    done
    timeout 1500 $PY verify_cycles.py --dirs "${args[@]}" --out $T/verification/$D >> $L 2>&1
    echo "scored: exit $?" >> $L ;;
  *) echo "unknown step $MODE" >> $L; exit 2 ;;
esac

# crontab of the user on sv7 (the server clock is UTC-6; the hours below are local, the minutes are the same in UTC):
#   31 0,6,12,18 * * * /bin/bash /data/ywan245/subdomainLSTM/shadow_20261117/shadow_run.sh t31
#   5 1,7,13,19 * * *  /bin/bash /data/ywan245/subdomainLSTM/shadow_20261117/shadow_run.sh t65
#   20 1,7,13,19 * * * /bin/bash /data/ywan245/subdomainLSTM/shadow_20261117/shadow_run.sh score
# to end it earlier:  crontab -e  and delete the three lines
