"""Forecasts of several model versions at the same stations, windows and origins (deliverable 17: version comparison).

For every station and each of two 4-day windows (hurricane: start from screen_complete_stations.py; high water: the highest
level outside the hurricane for which the observation and every version's inputs are complete) every
version issues a forecast at each 00/06/12/18 UTC origin (the window start minus 6 h up to the window end), leads 1-6 h.
Output per station:
  <out>/<station>_obs.csv   window, time, obs                      hourly observation (m)
  <out>/<station>_fc.csv    window, origin, lead, valid, <version keys>   forecast (m); NaN where a version's inputs are missing
Usage (sv7): python extract_versions.py --screen DIR/station_screen.csv --out DIR --stations USGS:07379050 ...
             --version wl:RUNS/v3_obs:DATA/dataset_v3 --version wind:RUNS/v3_wind:DATA/dataset_v3 ...
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from event_plots import forecasts
from station_compare import load
from data import HORIZON  # noqa: E402

DAYS = 4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--stations", nargs="+", required=True)
    ap.add_argument("--version", action="append", required=True, help="key:run_dir:dataset_dir")
    ap.add_argument("--test-end", default="2025-12-25")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    scr = pd.read_csv(a.screen, dtype={"station_id": str}).set_index(["source", "station_id"])
    models = {}
    for spec in a.version:
        key, run, ds = spec.split(":")
        models[key] = load(Path(run), Path(ds), device)
        print("loaded", key, run, flush=True)
    sm0 = next(iter(models.values()))[0]
    time = pd.DatetimeIndex(sm0.time)
    st = sm0.stations.reset_index(); st["station_id"] = st.station_id.astype(str)
    hours = DAYS * 24
    for key in a.stations:
        src, sid = key.split(":")
        m = st[(st.source == src) & (st.station_id == sid)]
        if m.empty or (src, sid) not in scr.index:
            print("missing", key); continue
        s = int(m.row.iloc[0]); r = scr.loc[(src, sid)]
        i_h = int(time.searchsorted(pd.Timestamp(r.hurr_start))); assert time[i_h].hour == 0
        lo, hi = int(time.searchsorted(pd.Timestamp("2024-01-01"))), int(time.searchsorted(pd.Timestamp(a.test_end)))
        allobs = np.asarray(sm0.values[s, lo:hi], np.float64)

        def run_window(i0):
            """Observation and all versions' forecasts for the window starting at index i0; None if anything is missing."""
            ob = np.asarray(sm0.values[s, i0:i0 + hours + 1], np.float32)
            t0s = np.arange(i0 - HORIZON, i0 + hours, HORIZON)          # 00/06/12/18 UTC
            fc = {k: forecasts(mod, sm, device, s, t0s) for k, (sm, mod) in models.items()}
            complete = np.isfinite(ob).all() and all(np.isfinite(v).all() for v in fc.values())
            return (ob, t0s, fc) if complete else None

        wins = {}
        got = run_window(i_h)
        if got is None:
            print(key, "hurricane window incomplete - station skipped"); continue
        wins[f"hurricane {r.hurricane}"] = (i_h, got)
        # high water: highest level outside the hurricane window for which every version has a complete forecast
        vv = allobs.copy(); vv[max(i_h - lo - 48, 0):i_h - lo + hours + 48] = np.nan; vv[:72] = np.nan; vv[-(hours + 24):] = np.nan
        for _ in range(12):
            if not np.isfinite(vv).any():
                break
            pk = int(np.nanargmax(vv)); i0 = lo + ((pk - 36) // 24) * 24
            got = run_window(i0)
            if got is not None:
                wins["high water"] = (i0, got); break
            vv[max(i0 - lo - 24, 0):i0 - lo + hours + 24] = np.nan
        if "high water" not in wins:
            print(key, "no complete high-water window - station skipped"); continue
        obs_rows, fc_rows = [], []
        for wname, (i0, (ob, t0s, fc)) in wins.items():
            obs_rows += [{"window": wname, "time": time[i0 + j], "obs": float(ob[j])} for j in range(hours + 1)]
            for n, t0 in enumerate(t0s):
                for h in range(1, HORIZON + 1):
                    fc_rows.append({"window": wname, "origin": time[t0], "lead": h, "valid": time[t0 + h], **{k: float(v[n, h - 1]) for k, v in fc.items()}})
        pd.DataFrame(obs_rows).to_csv(out / f"{sid}_obs.csv", index=False)
        f = pd.DataFrame(fc_rows); f.to_csv(out / f"{sid}_fc.csv", index=False)
        print(key, m.name.iloc[0], {w: str(time[i0])[:10] for w, (i0, _) in wins.items()}, flush=True)


if __name__ == "__main__":
    main()
