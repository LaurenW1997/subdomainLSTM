"""Observed water level around one forecast cycle at a few stations, for the figure that shows a live forecast next to
what was observed before and after it.

Pulls the hourly level from the same live services as forecast.py for [cycle - HOURS_BEFORE, cycle + 6 h] and writes
  <cycle dir>/series.csv   source, station_id, time, obs_m   (hourly, UTC)
together with a count of missing hours per station (stations with gaps should not be drawn).
Usage: python cycle_series.py --dir OUT/20261111T20 --stations 8771450 8761724 08117500 ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forecast import HORIZON, fetch_levels, to_hourly  # noqa: E402

HOURS_BEFORE = 48


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--stations", nargs="+", required=True)
    a = ap.parse_args()
    d = Path(a.dir)
    f = pd.read_csv(d / "forecast.csv", dtype={"station_id": str}, parse_dates=["cycle_utc"])
    cycle = f.cycle_utc.iloc[0]
    st = f[f.station_id.isin(a.stations) & (f.status == "ok")].reset_index(drop=True)
    raw = d / "raw_series"; raw.mkdir(exist_ok=True)
    hours = pd.date_range(cycle - pd.Timedelta(hours=HOURS_BEFORE), cycle + pd.Timedelta(hours=HORIZON), freq="1h")
    series = fetch_levels(st, ["USGS", "NOAA_COOPS"], hours[0] - pd.Timedelta(hours=1), hours[-1] + pd.Timedelta(minutes=59), raw)
    rows = []
    for r in st.itertuples():
        s = series.get((r.source, r.station_id))
        h = to_hourly(s).reindex(hours) if s is not None and not s.empty else pd.Series(index=hours, dtype=float)
        print(f"{r.station_id:>16s}  missing hours {int(h.isna().sum()):3d} of {len(hours)}   {r.name}")
        rows.append(pd.DataFrame({"source": r.source, "station_id": r.station_id, "time": hours, "obs_m": h.to_numpy()}))
    pd.concat(rows).to_csv(d / "series.csv", index=False)
    print("->", d / "series.csv")


if __name__ == "__main__":
    main()
