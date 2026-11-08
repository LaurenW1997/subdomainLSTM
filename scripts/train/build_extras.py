"""Add the wind and discharge inputs to a water-level dataset -> a new dataset dir.

  wind_u.npy / wind_v.npy : AORC 10 m wind at each station (m/s), from DATA_ROOT/wind
  q.npy                   : upstream discharge of the station's mapped gauge
                            (config/station_discharge_map.csv), log1p(m^3/s) z-scored per
                            gauge over the training period; NaN where no gauge / no data
values.npy, time.npy, stations.csv, meta.json are copied unchanged.
Usage: python build_extras.py --src dataset_v2 --out dataset_v3 [--wind-dir DATA_ROOT/wind]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data/ywan245/subdomainLSTM/data"))
REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="dataset_v2"); ap.add_argument("--out", default="dataset_v3")
    ap.add_argument("--wind-dir", default=str(DATA_ROOT / "wind"))
    ap.add_argument("--map", default=str(REPO / "config" / "station_discharge_map.csv"))
    a = ap.parse_args()
    src, out, wdir = DATA_ROOT / a.src, DATA_ROOT / a.out, Path(a.wind_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in ("values.npy", "time.npy", "stations.csv", "excluded.csv"):
        if (src / f).exists() and not (out / f).exists():
            shutil.copy(src / f, out / f)
    meta = json.loads((src / "meta.json").read_text())
    st = pd.read_csv(src / "stations.csv", dtype={"station_id": str})
    time_index = pd.to_datetime(np.load(src / "time.npy"))
    S, T = len(st), len(time_index)

    # ---- wind: produced on the same station order and hour axis; verify
    cells = pd.read_csv(wdir / "cells.csv", dtype={"station_id": str})
    assert (cells.station_id.to_numpy() == st.station_id.to_numpy()).all(), "wind cells.csv station order != stations.csv"
    assert (np.load(wdir / "time.npy") == np.load(src / "time.npy")).all(), "wind time axis != dataset time axis"
    u = np.load(wdir / "aorc_u10.npy"); v = np.load(wdir / "aorc_v10.npy")
    np.save(out / "wind_u.npy", u.astype(np.float32)); np.save(out / "wind_v.npy", v.astype(np.float32))
    wmeta = json.loads((wdir / "meta.json").read_text())
    print(f"wind: valid fraction {np.isfinite(u).mean():.3f}, last valid hour {wmeta.get('last_valid_hour')}")

    # ---- discharge
    m = pd.read_csv(a.map, dtype=str)
    assert (m.station_id.to_numpy() == st.station_id.to_numpy()).all(), "discharge map station order != stations.csv"
    train_end = pd.Timestamp(meta["train_end"])
    gauges = {}
    for gid in m.gauge_id.dropna().unique():
        p = DATA_ROOT / "hourly" / "USGS_Q" / f"{gid}.parquet"
        if not p.exists():
            print("no discharge file for gauge", gid); continue
        s = pd.read_parquet(p)["value_m"].reindex(time_index)
        s = s.where(s > -1000)
        x = np.log1p(s.clip(lower=0))                     # log discharge; negative (tidal reversal) -> 0
        tr = x[:train_end]
        mu, sd = float(tr.mean()), float(tr.std())
        if not np.isfinite(sd) or sd < 1e-3:
            print("flat discharge at", gid); continue
        gauges[gid] = ((x - mu) / sd).to_numpy(np.float32)
    q = np.full((S, T), np.nan, np.float32)
    n_with = 0
    for i, gid in enumerate(m.gauge_id):
        if isinstance(gid, str) and gid in gauges:
            q[i] = gauges[gid]; n_with += 1
    np.save(out / "q.npy", q)
    print(f"discharge: {len(gauges)} gauges, {n_with}/{S} stations with a series, valid fraction {np.isfinite(q).mean():.3f}")

    meta.update({"extras": {"wind": wmeta, "discharge": {"map": a.map, "n_gauges": len(gauges), "n_stations_with_q": n_with,
                                                        "transform": "log1p(m3/s) z-scored per gauge over train period"}},
                 "source_dataset": a.src})
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print("->", out)


if __name__ == "__main__":
    main()
