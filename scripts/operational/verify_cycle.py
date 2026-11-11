"""Score one finished forecast cycle against what was observed afterwards.

Pulls the water level of the hours after the origin from the same live APIs as forecast.py (same unit and datum
handling), compares it with fcst_1h_m .. fcst_6h_m of the stations with status "ok", and writes
  <cycle dir>/verification.csv   per station: observed and forecast level and the error at every lead already observed
  <cycle dir>/verification.json  RMSE per lead over all stations and by station type
Leads whose valid hour has not been observed yet are left empty, so the script can be run again later.
Usage: python verify_cycle.py --dir OUT/20261111T20 [--groups REPO/config/station_groups.csv]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forecast import HORIZON, REPO, fetch_levels, to_hourly  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="cycle output dir with forecast.csv")
    ap.add_argument("--groups", default=str(REPO / "config" / "station_groups.csv"))
    a = ap.parse_args()
    d = Path(a.dir)
    f = pd.read_csv(d / "forecast.csv", dtype={"station_id": str}, parse_dates=["cycle_utc"])
    f = f[f.status == "ok"].reset_index(drop=True)
    cycle = f.cycle_utc.iloc[0]
    raw = d / "raw_verify"; raw.mkdir(exist_ok=True)
    hours = pd.date_range(cycle + pd.Timedelta(hours=1), periods=HORIZON, freq="1h")
    series = fetch_levels(f, ["USGS", "NOAA_COOPS"], cycle - pd.Timedelta(hours=1), hours[-1] + pd.Timedelta(minutes=59), raw)
    g = pd.read_csv(a.groups, dtype={"station_id": str})
    out = f[["source", "station_id", "name", "domains", "last_obs_m"]].merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left")
    for h in range(1, HORIZON + 1):
        obs = np.full(len(f), np.nan)
        for i, r in f.iterrows():
            s = series.get((r.source, r.station_id))
            if s is not None and not s.empty:
                v = to_hourly(s).reindex([hours[h - 1]]).iloc[0]
                obs[i] = v
        out[f"obs_{h}h_m"] = obs
        out[f"fcst_{h}h_m"] = f[f"fcst_{h}h_m"].to_numpy()
        out[f"err_{h}h_cm"] = 100 * (out[f"fcst_{h}h_m"] - obs)
    out.round(4).to_csv(d / "verification.csv", index=False)
    res = {"cycle_utc": str(cycle), "scored_utc": str(pd.Timestamp.now("UTC").tz_localize(None).floor("min")), "leads": {}}
    print(f"cycle {cycle} UTC, {len(out)} stations with a forecast")
    for h in range(1, HORIZON + 1):
        e = out[f"err_{h}h_cm"].dropna()
        if len(e) < 10:
            print(f"  +{h} h ({hours[h - 1]:%H:%M} UTC): not observed yet"); continue
        r = {"n": int(len(e)), "rmse_cm": round(float(np.sqrt((e ** 2).mean())), 2), "median_abs_cm": round(float(e.abs().median()), 2),
             "by_type": {t: {"n": int(x.notna().sum()), "rmse_cm": round(float(np.sqrt((x.dropna() ** 2).mean())), 2)}
                         for t, x in out.groupby("type")[f"err_{h}h_cm"] if x.notna().sum() >= 5}}
        res["leads"][str(h)] = r
        print(f"  +{h} h ({hours[h - 1]:%H:%M} UTC): n={r['n']}  RMSE {r['rmse_cm']} cm  median |error| {r['median_abs_cm']} cm   "
              + "  ".join(f"{t} {v['rmse_cm']}" for t, v in r["by_type"].items()))
    (d / "verification.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
