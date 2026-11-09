"""Hourly precipitation at every station from NOAA AORC v1.1 (1 km, hourly) on AWS - EXPERIMENT (rain input).

Source: s3://noaa-nws-aorc-v1-1-1km/<year>.zarr, variable APCP_surface (kg/m^2 per hour = mm/h).
Output: DATA_ROOT/precip/aorc_p.npy     float32 [n_stations, n_hours]  rain at the station's 1 km cell
        DATA_ROOT/precip/aorc_p15.npy   float32 [n_stations, n_hours]  mean over a 15 x 15 km box centred on the station
                                        (a crude stand-in for the catchment of small creeks)
        same station order as --stations, same hour axis as the training dataset; hours outside AORC = NaN.
        Also precip/cells.csv, precip/time.npy, precip/meta.json.
Usage: python aorc_precip.py --stations DIR/stations.csv [--years 2010 2025] [--out DIR] [--box 15]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from common import DATA_ROOT, log

BUCKET = "s3://noaa-nws-aorc-v1-1-1km"
START = pd.Timestamp("2010-01-01 00:00")
END = pd.Timestamp("2026-11-07 00:00")
VAR = "APCP_surface"


def open_year(year: int) -> xr.Dataset:
    return xr.open_zarr(f"{BUCKET}/{year}.zarr", consolidated=True, storage_options={"anon": True}, chunks={})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True)
    ap.add_argument("--years", nargs=2, type=int, default=[2010, 2025])
    ap.add_argument("--out", default=str(DATA_ROOT / "precip"))
    ap.add_argument("--box", type=int, default=15, help="box side in cells (km) for the area mean")
    ap.add_argument("--chunk", type=int, default=120, help="stations per extraction batch")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    time_index = pd.date_range(START, END, freq="1h")
    S, T = len(st), len(time_index)
    half = a.box // 2

    ds0 = open_year(a.years[0])
    lat, lon = ds0.latitude.values, ds0.longitude.values
    iy = np.abs(lat[None, :] - st.lat.to_numpy()[:, None]).argmin(1)
    ix = np.abs(lon[None, :] - st.lon.to_numpy()[:, None]).argmin(1)
    pd.DataFrame({"source": st.source, "station_id": st.station_id, "lat": st.lat, "lon": st.lon,
                  "cell_lat": lat[iy], "cell_lon": lon[ix], "iy": iy, "ix": ix}).to_csv(out / "cells.csv", index=False)
    off = np.arange(-half, half + 1)
    iy_box = np.clip(iy[:, None, None] + off[None, :, None], 0, len(lat) - 1)      # [S, box, 1]
    ix_box = np.clip(ix[:, None, None] + off[None, None, :], 0, len(lon) - 1)      # [S, 1, box]
    iy_box, ix_box = np.broadcast_arrays(iy_box, ix_box)                           # [S, box, box]

    p = np.full((S, T), np.nan, np.float32); p15 = np.full((S, T), np.nan, np.float32)
    for year in range(a.years[0], a.years[1] + 1):
        t0 = time.time()
        ds = ds0 if year == a.years[0] else open_year(year)
        t = pd.to_datetime(ds.time.values)
        ok = (t >= START) & (t <= END)
        if not ok.any():
            continue
        pos = time_index.get_indexer(t[ok]); keep = pos >= 0
        da = ds[VAR]
        for c0 in range(0, S, a.chunk):
            c1 = min(S, c0 + a.chunk)
            pts = da.isel(latitude=xr.DataArray(iy_box[c0:c1], dims=("station", "dy", "dx")),
                          longitude=xr.DataArray(ix_box[c0:c1], dims=("station", "dy", "dx")))
            arr = pts.transpose("station", "dy", "dx", "time").values.astype(np.float32)   # [s, box, box, T_year]
            arr[arr < 0] = np.nan
            p[c0:c1, pos[keep]] = arr[:, half, half, :][:, np.where(ok)[0][keep]]
            p15[c0:c1, pos[keep]] = np.nanmean(arr, axis=(1, 2))[:, np.where(ok)[0][keep]]
        valid = np.isfinite(p[:, pos[keep]]).mean()
        log.info("%d: %d hours, valid %.3f, mean %.3f mm/h, max %.1f, %.0f s", year, ok.sum(), valid,
                 np.nanmean(p[:, pos[keep]]), np.nanmax(p[:, pos[keep]]), time.time() - t0)
        np.save(out / "aorc_p.npy", p); np.save(out / "aorc_p15.npy", p15)        # checkpoint after every year
    np.save(out / "time.npy", time_index.values.astype("datetime64[ns]").astype(np.int64))
    meta = {"source": "NOAA AORC v1.1 1 km hourly (AWS)", "var": VAR, "units": "mm/h", "box_cells": a.box, "years": a.years,
            "stations": a.stations, "n_stations": S, "n_hours": T, "start": str(START), "end": str(END),
            "last_valid_hour": str(time_index[np.where(np.isfinite(p).any(0))[0].max()]), "valid_fraction": float(np.isfinite(p).mean())}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    log.info("done: %s", meta)


if __name__ == "__main__":
    main()
