"""10 m wind (u, v) at every station from NOAA AORC v1.1 (1 km, hourly) on AWS.

Source: s3://noaa-nws-aorc-v1-1-1km/<year>.zarr (public, anonymous), variables
UGRD_10maboveground / VGRD_10maboveground, 1979-2025.
Output: DATA_ROOT/wind/aorc_u10.npy, aorc_v10.npy  float32 [n_stations, n_hours]
        on the SAME station order as --stations and the SAME hour axis as the
        training dataset (2010-01-01 .. END); hours not covered by AORC = NaN.
        Also wind/meta.json and wind/cells.csv (grid cell used per station).
Usage: python aorc_wind.py --stations DIR/stations.csv [--years 2010 2025] [--out DIR]
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
VARS = {"u10": "UGRD_10maboveground", "v10": "VGRD_10maboveground"}


def open_year(year: int) -> xr.Dataset:
    return xr.open_zarr(f"{BUCKET}/{year}.zarr", consolidated=True, storage_options={"anon": True}, chunks={})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True)
    ap.add_argument("--years", nargs=2, type=int, default=[2010, 2025])
    ap.add_argument("--out", default=str(DATA_ROOT / "wind"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    time_index = pd.date_range(START, END, freq="1h")
    S, T = len(st), len(time_index)

    ds0 = open_year(a.years[0])
    lat, lon = ds0.latitude.values, ds0.longitude.values
    iy = np.abs(lat[None, :] - st.lat.to_numpy()[:, None]).argmin(1)
    ix = np.abs(lon[None, :] - st.lon.to_numpy()[:, None]).argmin(1)
    pd.DataFrame({"source": st.source, "station_id": st.station_id, "lat": st.lat, "lon": st.lon,
                  "cell_lat": lat[iy], "cell_lon": lon[ix], "iy": iy, "ix": ix}).to_csv(out / "cells.csv", index=False)
    y0, y1 = iy.min(), iy.max() + 1
    x0, x1 = ix.min(), ix.max() + 1
    log.info("%d stations -> grid box lat[%d:%d] lon[%d:%d] (%d x %d cells)", S, y0, y1, x0, x1, y1 - y0, x1 - x0)

    mats = {k: np.full((S, T), np.nan, np.float32) for k in VARS}
    for year in range(a.years[0], a.years[1] + 1):
        t0 = time.time()
        ds = ds0 if year == a.years[0] else open_year(year)
        t = pd.to_datetime(ds.time.values)
        ok = (t >= START) & (t <= END)
        if not ok.any():
            continue
        pos = time_index.get_indexer(t[ok])
        keep = pos >= 0
        sel = ds[list(VARS.values())].isel(latitude=slice(y0, y1), longitude=slice(x0, x1))
        # vectorised point extraction inside the box; dask reads only the chunks that cover the box
        pts = sel.isel(latitude=xr.DataArray(iy - y0, dims="station"), longitude=xr.DataArray(ix - x0, dims="station"))
        for k, v in VARS.items():
            arr = pts[v].transpose("station", "time").values.astype(np.float32)   # [S, T_year]
            arr[arr < -1000] = np.nan                                               # missing_value
            mats[k][:, pos[keep]] = arr[:, np.where(ok)[0][keep]]
        valid = np.isfinite(mats["u10"][:, pos[keep]]).mean()
        log.info("%d: %d hours, valid %.3f, %.0f s", year, ok.sum(), valid, time.time() - t0)
        for k in VARS:
            np.save(out / f"aorc_{k}.npy", mats[k])     # checkpoint after every year
    np.save(out / "time.npy", time_index.values.astype("datetime64[ns]").astype(np.int64))
    meta = {"source": "NOAA AORC v1.1 1 km hourly (AWS)", "vars": VARS, "years": a.years, "stations": a.stations,
            "n_stations": S, "n_hours": T, "start": str(START), "end": str(END),
            "last_valid_hour": str(time_index[np.where(np.isfinite(mats["u10"]).any(0))[0].max()]),
            "valid_fraction": float(np.isfinite(mats["u10"]).mean())}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    log.info("done: %s", meta)


if __name__ == "__main__":
    main()
