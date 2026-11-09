"""Export, for chosen stations and windows, the observation and the forecast VALID at each hour for
every lead (1..6 h), so that figures can be drawn elsewhere (no torch needed there).

For each station a CSV  <out>/<prefix>_<station>.csv  with columns
  window, time, obs, f1..f6            (f_h = forecast issued h hours earlier and valid at `time`, metres)
and, when --run-b is given, b1..b6 for the second model.
Windows: as in event_plots.py (hurricane NAME:DATE -> hurricane / high water / normal; else flood / worst / typical).
Usage (sv7):
  python extract_windows.py --dataset DATA/dataset_v4 --run RUNS/v4_wind_q [--run-b RUNS/v3_obs] --out DIR
         --stations NOAA_COOPS:8747437 ... [--hurricane Francine:2024-09-10] [--days 4] [--prefix la]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from event_plots import forecasts, pick_windows
from station_compare import load, series
from data import HORIZON  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--run", required=True); ap.add_argument("--run-b"); ap.add_argument("--dataset-b")
    ap.add_argument("--out", required=True); ap.add_argument("--stations", nargs="+", required=True)
    ap.add_argument("--days", type=float, default=4); ap.add_argument("--hurricane"); ap.add_argument("--prefix", default="win")
    ap.add_argument("--test-end", default="2025-12-31T17")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    sm, model = load(Path(a.run), Path(a.dataset), device)
    sm_b = model_b = None
    if a.run_b:
        sm_b, model_b = load(Path(a.run_b), Path(a.dataset_b or a.dataset), device)
    st = sm.stations.reset_index(); st["station_id"] = st.station_id.astype(str)
    lo, hi = sm.split_range("test")
    hi = min(hi, int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))) + HORIZON
    time = pd.DatetimeIndex(sm.time[lo:hi])
    hours = int(a.days * 24)
    for key in a.stations:
        src, sid = key.split(":")
        m = st[(st.source == src) & (st.station_id == sid)]
        if m.empty:
            print("missing", key); continue
        s = int(m.row.iloc[0]); name = m.name.iloc[0]
        obs = np.asarray(sm.values[s, lo:hi], np.float32)
        f6 = series(model, sm, device, s, lo, hi)
        if a.hurricane:
            hname, hdate = a.hurricane.split(":")
            wins = pick_windows(time, obs, f6, hours, hurricane=(hname, int(np.searchsorted(time.values, np.datetime64(hdate)))))
        else:
            wins = pick_windows(time, obs, f6, hours)
        rows = []
        for wname, i0 in wins.items():
            i1 = min(i0 + hours, len(time) - HORIZON - 1)
            # origins from i0-6 so that every valid hour in [i0, i1) has all leads
            t0s = np.arange(lo + i0 - HORIZON, lo + i1)
            fc = forecasts(model, sm, device, s, t0s)
            fcb = forecasts(model_b, sm_b, device, s, t0s) if model_b is not None else None
            for j in range(i0, i1):
                r = {"window": wname, "time": time[j], "obs": float(obs[j])}
                for h in range(1, HORIZON + 1):
                    k = j - h - (i0 - HORIZON)              # origin index in t0s for the forecast valid at j with lead h
                    r[f"f{h}"] = float(fc[k, h - 1]) if 0 <= k < len(t0s) else np.nan
                    if fcb is not None:
                        r[f"b{h}"] = float(fcb[k, h - 1]) if 0 <= k < len(t0s) else np.nan
                rows.append(r)
        df = pd.DataFrame(rows)
        df.to_csv(out / f"{a.prefix}_{sid}.csv", index=False)
        print(key, name, {k: str(time[v])[:13] for k, v in wins.items()})


if __name__ == "__main__":
    main()
