"""Lag of the 6 h forecast behind the observation, per station window and model version (deliverable 19).

Lag = the shift k (0 .. 8 h) that minimises the RMSE between the forecast valid at hour t and the observation at t - k:
0 h means the forecast rises and falls with the observation, 6 h means it only repeats what was seen at the origin.
Windows with missing forecasts or observations are left out.
Input : <dir>/<station>_obs.csv, <dir>/<station>_fc.csv (extract_versions_hourly.py), <windows>.csv, config/station_downstream_map.csv
Output: <dir>/../lag_table.csv, printed summary
Usage : python lag_check.py --dir deliverables/19_reference_gauge/data_lag --windows deliverables/19_reference_gauge/windows_lag.csv --keys base ds ds_us
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
MAXLAG = 8


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--windows", required=True)
    ap.add_argument("--keys", nargs="+", required=True); ap.add_argument("--lead", type=int, default=6)
    a = ap.parse_args()
    d = Path(a.dir)
    win = pd.read_csv(a.windows, dtype={"station_id": str})
    m = pd.read_csv(REPO / "config" / "station_downstream_map.csv", dtype=str).fillna("").set_index(["source", "station_id"])
    rows = []
    for (src, sid), w in win.groupby(["source", "station_id"], sort=False):
        obs = pd.read_csv(d / f"{sid}_obs.csv", parse_dates=["time"])
        fc = pd.read_csv(d / f"{sid}_fc.csv", parse_dates=["valid"])
        fc = fc[fc.lead == a.lead]
        info = m.loc[(src, sid)]
        for wn in w.window:
            o = obs[obs.window == wn].set_index("time").obs
            f = fc[fc.window == wn].set_index("valid")
            f = f[f.index.isin(o.index)]
            if o.isna().any() or f[a.keys].isna().any().any() or len(f) < 72:
                print("skipped (missing data):", sid, wn)
                continue
            row = {"source": src, "station_id": sid, "name": info["name"], "type": info["type"], "window": wn,
                   "downstream_ref": info["ds_name"], "ref_rule": info["rule"], "upstream_ref": info["us_name"],
                   "range_cm": round(100 * float(o.max() - o.min()), 1)}
            for k in a.keys:
                err = []
                for s in range(MAXLAG + 1):
                    oo = o.reindex(f.index - pd.Timedelta(hours=s))
                    e = f[k].to_numpy() - oo.to_numpy()
                    err.append(np.sqrt(np.nanmean(e ** 2)))
                row[f"lag_{k}"] = int(np.argmin(err)); row[f"rmse_{k}"] = round(100 * err[0], 2)
            rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(d.parent / "lag_table.csv", index=False)
    pd.set_option("display.width", 250)
    print(t[["station_id", "name", "window", "range_cm"] + [f"lag_{k}" for k in a.keys] + [f"rmse_{k}" for k in a.keys]].to_string(index=False))
    big = t[t.range_cm >= 30]
    for lab, x in (("all windows", t), ("windows with a rise or fall of 30 cm or more", big),
                   ("  of these: station has an upstream gauge", big[big.upstream_ref != ""]),
                   ("  of these: downstream gauge on the same river", big[big.ref_rule == "same river"]),
                   ("  of these: tide gauge as reference", big[big.ref_rule == "nearest tide gauge"]),
                   ("  of these: no reference", big[(big.ref_rule == "") & (big.upstream_ref == "")])):
        print(f"{lab}: n={len(x)}  mean lag h: " + ", ".join(f"{k} {x[f'lag_{k}'].mean():.1f}" for k in a.keys)
              + "   mean RMSE cm: " + ", ".join(f"{k} {x[f'rmse_{k}'].mean():.1f}" for k in a.keys))


if __name__ == "__main__":
    main()
