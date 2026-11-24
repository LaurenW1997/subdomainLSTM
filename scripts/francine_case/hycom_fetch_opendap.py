"""Francine case, open boundary: the 3-D HYCOM fields through OPeNDAP, as a second way beside the subset service (hycom_fetch_3d.sh).

Writes files with the same names and the same variables, so both ways can fill the same folder: a file already there is skipped.
    days   one file per day with the 3-hourly records of that day and the first of the next (as the subset service gives),
           going backward from --end, so that it meets the other download in the middle
    daily  one file with one record a day (00:00) for the whole period (temperature and salinity change slowly)
Usage : python hycom_fetch_opendap.py --dataset v3z --var water_v --mode days --out DIR
        python hycom_fetch_opendap.py --dataset t3z --var water_temp --mode daily --out DIR
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd

URL = "https://tds.hycom.org/thredds/dodsC/ESPC-D-V02/{}/2024"
BOX = (28.40, 30.72, -94.48, -88.08)


def write(path: Path, when, depth, lat, lon, var, data) -> None:
    tmp = path.with_suffix(f".part{os.getpid()}"); o = nc.Dataset(tmp, "w", format="NETCDF4")
    o.createDimension("time", len(when)); o.createDimension("depth", len(depth)); o.createDimension("lat", len(lat)); o.createDimension("lon", len(lon))
    t = o.createVariable("time", "f8", ("time",)); t.units = "hours since 2000-01-01 00:00:00"; t.calendar = "gregorian"; t[:] = nc.date2num(list(when), t.units, t.calendar)
    for k, x in (("depth", depth), ("lat", lat), ("lon", lon)):
        o.createVariable(k, "f8", (k,))[:] = x
    v = o.createVariable(var, "f4", ("time", "depth", "lat", "lon"), zlib=True, fill_value=np.float32(np.nan)); v[:] = data; o.source = "HYCOM ESPC-D-V02 through OPeNDAP"; o.close(); os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); ap.add_argument("--var", required=True); ap.add_argument("--mode", choices=["days", "daily"], required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--start", default="2024-08-13"); ap.add_argument("--end", default="2024-09-20"); a = ap.parse_args(); out = Path(a.out)
    d = nc.Dataset(URL.format(a.dataset)); lat = np.array(d["lat"][:]); lon = np.array(d["lon"][:]); depth = np.array(d["depth"][:]); t = d["time"]; tt = pd.DatetimeIndex(nc.num2date(t[:], t.units, only_use_cftime_datetimes=False))
    lo = np.where(lon > 180, lon - 360, lon); j0, j1 = int(np.searchsorted(lat, BOX[0] - 1e-6)), int(np.searchsorted(lat, BOX[1] + 1e-6)); i0, i1 = int(np.argmin(np.abs(lo - BOX[2]))), int(np.argmin(np.abs(lo - BOX[3]))) + 1
    v = d[a.var]; v.set_auto_maskandscale(True)

    def read(idx):
        for attempt in range(6):
            try:
                x = v[idx, :, j0:j1, i0:i1] if not isinstance(idx, np.ndarray) else np.ma.concatenate([v[int(k):int(k) + 1, :, j0:j1, i0:i1] for k in idx]); return np.ma.filled(x.astype(np.float32), np.nan)
            except Exception as e:                                         # noqa: BLE001
                print(f"  retry {attempt + 1}: {str(e)[:80]}", flush=True); time.sleep(30)
        raise RuntimeError("could not read")
    if a.mode == "daily":
        f = out / f"{a.dataset}_{a.start}_{a.end}_daily_opendap.nc"
        if f.exists():
            print(f.name, "there"); return
        idx = np.array([k for k, x in enumerate(tt) if a.start <= str(x)[:10] <= a.end and x.hour == 0]); t0 = time.time(); data = read(idx); write(f, tt[idx], depth, lat[j0:j1], lon[i0:i1], a.var, data)
        print(f"{pd.Timestamp.now():%H:%M} {f.name} ok, {len(idx)} records, {time.time() - t0:.0f} s", flush=True); return
    day = pd.Timestamp(a.end) - pd.Timedelta(days=1)
    while day >= pd.Timestamp(a.start):
        f = out / f"{a.dataset}_{day:%Y-%m-%d}_{day + pd.Timedelta(days=1):%Y-%m-%d}_every1.nc"
        if not f.exists():
            k = np.where((tt >= day) & (tt <= day + pd.Timedelta(days=1)))[0]; t0 = time.time(); data = read(slice(int(k[0]), int(k[-1]) + 1))
            if not f.exists():
                write(f, tt[k], depth, lat[j0:j1], lon[i0:i1], a.var, data); print(f"{pd.Timestamp.now():%H:%M} {f.name} ok, {len(k)} records, {time.time() - t0:.0f} s", flush=True)
        day -= pd.Timedelta(days=1)
    print(a.dataset, "finished")


if __name__ == "__main__":
    main()
