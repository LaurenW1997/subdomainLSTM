"""Francine case: the hourly water level of the run packed in the layout of the Ida archive (water_level_<run>.nc).

Same composite and the same layout as the runs of Hurricane Ida and as the operational forecasts (operational_water_level.py),
so that the mapping model reads it as it reads those:
    ocean-model cells (mask_rho = 1)   free-surface elevation (m); missing where the cell is dry (zeta + h <= 0.25 m)
    land-model cells                    depth of surface water above the ground (m)
Nothing is quality controlled or removed. The output of the run is only read. All hours of the run are packed, the spin-up
of the cold start included (the attribute spin_up says so); which hours to use is decided where the file is read.
Input : --run DIR (hires_ocean_his_*.nc, OUTPUT/HYDROOUT/hydro_YYYYMMDDHH.nc), --grid ROMS grid file of the run
Output: --out FILE (time, lat, lon, water_level [m], 1 mm precision) and, beside it, grid_<name>.nc (h and mask of the ocean-model rows)
Usage : python pack_run.py --run DIR --grid FILE --out water_level_Francine_hindcast.nc [--workers 12]
        An existing file is never overwritten.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import time
from multiprocessing import Pool
from pathlib import Path

import netCDF4 as nc
import numpy as np

DRY, NY = 0.25, 2680
G = {}


def load_grid(path: str):
    g = nc.Dataset(path); mask = np.ma.filled(g["mask_rho"][:], 0) > 0.5; h = np.ma.filled(g["h"][:], np.nan).astype("f4")
    lon2 = np.ma.filled(g["lon_rho"][:], np.nan); lat2 = np.ma.filled(g["lat_rho"][:], np.nan); g.close()
    no, nx = mask.shape; merc = lambda p: np.log(np.tan(np.pi / 4 + np.radians(p) / 2)); y0 = merc(lat2[0, 0]); dy = (merc(lat2[-1, 0]) - y0) / (no - 1)   # the grid is evenly spaced on a Mercator map
    lat = np.degrees(2 * np.arctan(np.exp(y0 + dy * np.arange(NY))) - np.pi / 2)
    return mask, h, lon2[0].astype("f8"), lat.astype("f8")


def level(job):
    of, hf = job; mask, h = G["mask"], G["h"]; no, nx = mask.shape
    d = nc.Dataset(of); z = np.ma.filled(d["zeta"][0], np.nan).astype("f4")[:no]; d.close()
    x = nc.Dataset(hf); dep = np.ma.filled(x["sfcheadsubrt"][0], np.nan).astype("f4") / 1000.0; x.close()
    out = dep.copy(); out[no:][~np.isfinite(dep[no:])] = np.nan
    wet = mask & (np.abs(z) < 1e30) & (z + h > DRY); sea = np.full((no, nx), np.nan, "f4"); sea[wet] = z[wet]; out[:no] = np.where(mask, sea, dep[:no])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); ap.add_argument("--grid", required=True); ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--title", default="Hindcast of Hurricane Francine with the Louisiana100m model: hourly water level"); ap.add_argument("--spin-up", default="cold start on 2024-08-14 00:00 UTC (ocean at rest); landfall 2024-09-11 22:00 UTC"); a = ap.parse_args()
    target = Path(a.out); assert not target.exists(), f"{target} exists"; target.parent.mkdir(parents=True, exist_ok=True); t0 = time.time()
    mask, h, lon, lat = load_grid(a.grid); no, nx = mask.shape; G.update(mask=mask, h=h); gfile = target.parent / ("grid_" + target.stem.replace("water_level_", "") + ".nc")
    if not gfile.exists():
        g = nc.Dataset(gfile, "w"); g.createDimension("lat_ocean_rows", no); g.createDimension("lat", NY); g.createDimension("lon", nx); g.createVariable("lat", "f8", ("lat",))[:] = lat; g.createVariable("lon", "f8", ("lon",))[:] = lon
        v = g.createVariable("h", "f4", ("lat_ocean_rows", "lon"), zlib=True); v.long_name = "bathymetry of the ocean-model rows, positive down (m)"; v[:] = h
        v = g.createVariable("mask_rho", "i1", ("lat_ocean_rows", "lon"), zlib=True); v.long_name = "1 = cell computed by the ocean model, 0 = by the land model"; v[:] = mask.astype("i1"); g.source = a.grid; g.close()
    pairs = []
    for f in sorted(glob.glob(os.path.join(a.run, "hires_ocean_his_*.nc"))):
        d = nc.Dataset(f); t = d["ocean_time"]; when = nc.num2date(t[0], t.units, only_use_cftime_datetimes=False); d.close()
        when = dt.datetime(when.year, when.month, when.day, when.hour) + dt.timedelta(hours=1 if when.minute >= 30 else 0); hf = os.path.join(a.run, "OUTPUT", "HYDROOUT", f"hydro_{when:%Y%m%d%H}.nc")
        assert os.path.exists(hf), f"no land-model file for {when}"; pairs.append((when, f, hf))
    pairs.sort(); assert all((b[0] - a_[0]) == dt.timedelta(hours=1) for a_, b in zip(pairs, pairs[1:])), "the hours are not consecutive"; print(f"{len(pairs)} hours {pairs[0][0]} .. {pairs[-1][0]}; grid {NY} x {nx}, ocean-model rows {no}", flush=True)
    tmp = target.with_suffix(f".part{os.getpid()}"); o = nc.Dataset(tmp, "w", format="NETCDF4")
    o.createDimension("time", None); o.createDimension("lat", NY); o.createDimension("lon", nx)
    tv = o.createVariable("time", "f8", ("time",)); tv.units = "hours since 1970-01-01 00:00:00"; tv.calendar = "standard"; tv.long_name = "valid time (UTC)"
    v = o.createVariable("lat", "f8", ("lat",)); v.units = "degrees_north"; v[:] = lat
    v = o.createVariable("lon", "f8", ("lon",)); v.units = "degrees_east"; v[:] = lon
    wl = o.createVariable("water_level", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, shuffle=True, chunksizes=(1, 335, 551), least_significant_digit=3)
    wl.units = "m"; wl.long_name = "combined water level of the coupled WRF-Hydro-ROMS model, hindcast, not quality controlled"
    wl.comment = ("Composite of the two coupled models, as in the archive of the runs of Hurricane Ida. Ocean-model cells (mask_rho = 1): free-surface elevation; "
                  "missing where the cell is dry (zeta + h <= %.2f m). Land-model cells: depth of surface water above the ground. Stored at 1 mm precision." % DRY)
    o.title = a.title; o.source_folder = a.run; o.grid_file = a.grid; o.spin_up = a.spin_up
    o.inputs = ("atmosphere: HRRR; open boundary: HYCOM ESPC-D-V02, hourly, free surface + 0.045 m; river inflow: 1.0231 x discharge at Vicksburg 30 h earlier minus the Old River Outflow Channel "
                "(the runs of Hurricane Ida in the archive used the inflow without that subtraction)")
    o.history = "Packed from hires_ocean_his_*.nc (zeta) and hydro_*.nc (sfcheadsubrt) by pack_run.py; the source files were only read."
    with Pool(a.workers) as pool:
        for n, lev in enumerate(pool.imap(level, [(f, hf) for _, f, hf in pairs], chunksize=1)):
            ok = np.isfinite(lev) & (np.abs(lev) < 1e30); wl[n] = np.ma.array(np.where(ok, lev, 0.0), mask=~ok); tv[n] = nc.date2num(pairs[n][0], tv.units, tv.calendar)
            if n % 48 == 0:
                print(f"{pairs[n][0]}  ({time.time() - t0:.0f} s)", flush=True)
    o.hours = len(pairs); o.close(); os.replace(tmp, target); print(f"done: {len(pairs)} hours in {time.time() - t0:.0f} s -> {target} ({target.stat().st_size / 1e9:.2f} GB)", flush=True)


if __name__ == "__main__":
    main()
