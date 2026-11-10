"""Screen operational (non-CRMS) stations for complete observation records in the test period, for the
version-comparison figures (deliverable 17): a station is usable only if nothing is missing in the windows drawn.

For every station: fraction of valid hours in the test period, longest gap, and for two 4-day windows
(hurricane: fixed start per domain; high water: around the highest level outside the hurricane window)
the fraction of valid hours. Windows start at 00 UTC so that 6-hourly forecast origins fit.
Output: <out>/station_screen.csv (one row per station) - printed summary by type.
Usage (sv7): python screen_complete_stations.py --dataset DATA/dataset_v5 --out DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
HURR = {"Louisiana100m": ("Francine", "2024-09-10"), "Galveston100m": ("Beryl", "2024-07-07"), "Texas100m": ("Beryl", "2024-07-07")}
DAYS = 4


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = Path(a.dataset); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(d / "stations.csv", dtype={"station_id": str})
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    st = st.merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left")
    per = pd.read_csv(REPO / "runs" / "v6_wind_q" / "per_station_test.csv", dtype={"station_id": str})
    st["r6"] = per.rmse_6h_cm.to_numpy(); st["n6"] = per.n_6h.to_numpy()
    vals = np.load(d / "values.npy", mmap_mode="r"); t = pd.DatetimeIndex(np.load(d / "time.npy"))
    i0 = int(t.searchsorted(pd.Timestamp("2024-01-01"))); i1 = int(t.searchsorted(pd.Timestamp("2026-01-01")))
    hours = DAYS * 24
    rows = []
    for k, r in st.iterrows():
        if r.source == "CRMS":
            continue
        v = np.asarray(vals[k, i0:i1], np.float64); ok = np.isfinite(v)
        if ok.mean() < 0.5:
            continue
        gaps = np.diff(np.flatnonzero(np.concatenate(([True], ok, [True])))) - 1          # runs of missing hours
        dom = str(r.domains).split(";")[0].split(",")[0].strip()
        dom = next((x for x in HURR if x in str(r.domains)), dom)
        hname, hdate = HURR.get(dom, ("", "2024-07-07"))
        h0 = int(t.searchsorted(pd.Timestamp(hdate))) - i0
        hw = v[h0:h0 + hours]
        # highest level outside the hurricane window (+- 2 days), window starts at 00 UTC 36-60 h before the peak
        vv = v.copy(); vv[max(h0 - 48, 0):h0 + hours + 48] = np.nan; vv[:72] = np.nan; vv[-(hours + 24):] = np.nan
        if not np.isfinite(vv).any():
            continue
        pk = int(np.nanargmax(vv))
        w0 = ((pk - 36) // 24) * 24                                                       # 00 UTC, peak falls 36-60 h into the window
        ww = v[w0:w0 + hours]
        rows.append({"source": r.source, "station_id": r.station_id, "name": r["name"], "type": r.type, "domain": dom, "lat": r.lat, "lon": r.lon,
                     "r6_cm": round(float(r.r6), 2), "frac_test": round(float(ok.mean()), 4), "longest_gap_h": int(gaps.max()) if len(gaps) else 0,
                     "hurricane": hname, "hurr_start": str(t[i0 + h0])[:13], "hurr_frac": round(float(np.isfinite(hw).mean()), 3),
                     "hurr_range_m": round(float(np.nanmax(hw) - np.nanmin(hw)), 2) if np.isfinite(hw).any() else np.nan,
                     "high_start": str(t[i0 + w0])[:13], "high_frac": round(float(np.isfinite(ww).mean()), 3),
                     "high_range_m": round(float(np.nanmax(ww) - np.nanmin(ww)), 2) if np.isfinite(ww).any() else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(out / "station_screen.csv", index=False)
    full = df[(df.hurr_frac == 1) & (df.high_frac == 1) & (df.frac_test >= 0.98)]
    print(f"{len(df)} non-CRMS stations; {len(full)} with both windows complete and >= 98% of the test period")
    print(full.groupby(["type", "domain"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
