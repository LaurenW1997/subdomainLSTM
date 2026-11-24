"""Keep the 72-hour forecasts of the operational Louisiana100m model before the archive is purged.

Every forecast cycle of the group's operational system holds 73 hourly files of the ocean model (zeta) and 73 of the land model
(sfcheadsubrt, depth of surface water in mm) on the same 100 m grid as the runs of Hurricane Ida. They are packed here, one
file per cycle, in the layout of the Ida archive (water_level_<run>.nc), so that the mapping model can read them as it reads the runs:
    ocean-model cells (mask_rho = 1)   free-surface elevation (m); missing where the cell is dry (zeta + h <= 0.25 m)
    land-model cells                    depth of surface water above the ground (m)
Nothing is quality controlled or removed beyond that. The archive of the operational system is only read.
Until 2026-08-30 the ocean files carry all 2680 rows of the grid, from 2026-08-31 the southern 1837 rows; the two grids agree
in mask and depth on the common rows and the northern rows hold no ocean cell, so the southern 1837 rows are taken in both.
Input : --archive DIR with <cycle>/<branch>/ocean_his_000NN.nc and hydro_YYYYMMDDHH.nc, --grid ROMS grid file of the operational model
Output: --out DIR: water_level_operational_<cycle>.nc (time, lat, lon, water_level [m], 1 mm precision), grid_operational.nc (h and mask of the
        ocean-model rows, written once), cycles.csv (one row per cycle: hours packed, first and last valid time)
Usage : python operational_water_level.py --archive DIR --grid FILE --out DIR [--cycles 20260705 ...] [--workers 8] [--max-hours N]
        A cycle whose file exists is skipped; nothing is overwritten.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from multiprocessing import Pool
from pathlib import Path

import netCDF4 as nc
import numpy as np

DRY = 0.25                                                                 # an ocean-model cell with less total depth than this counts as dry (as in the Ida archive)
NY = 2680


def load_grid(path: str):
    g = nc.Dataset(path); mask = np.ma.filled(g["mask_rho"][:], 0) > 0.5; h = np.ma.filled(g["h"][:], np.nan).astype("f4")
    lon2 = np.ma.filled(g["lon_rho"][:], np.nan); lat2 = np.ma.filled(g["lat_rho"][:], np.nan); g.close()
    no, nx = mask.shape; merc = lambda p: np.log(np.tan(np.pi / 4 + np.radians(p) / 2)); y0 = merc(lat2[0, 0]); dy = (merc(lat2[-1, 0]) - y0) / (no - 1)   # the grid is evenly spaced on a Mercator map
    lat = np.degrees(2 * np.arctan(np.exp(y0 + dy * np.arange(NY))) - np.pi / 2)
    return mask, h, lon2[0].astype("f8"), lat.astype("f8")


def pack(job) -> str:
    cycle, folder, grid, out, max_hours = job; target = Path(out) / f"water_level_operational_{cycle}.nc"
    if target.exists():
        return f"{cycle},exists,,,"
    mask, h, lon, lat = load_grid(grid); no, nx = mask.shape; pairs = []
    for f in sorted(Path(folder).glob("ocean_his_*.nc")):
        try:
            d = nc.Dataset(f); t = d["ocean_time"]; when = nc.num2date(t[0], t.units, only_use_cftime_datetimes=False); d.close()
        except Exception:
            continue
        when = dt.datetime(when.year, when.month, when.day, when.hour) + dt.timedelta(hours=1 if when.minute >= 30 else 0); hf = Path(folder) / f"hydro_{when:%Y%m%d%H}.nc"
        if hf.exists():
            pairs.append((when, f, hf))
    pairs.sort(); pairs = pairs[:max_hours] if max_hours else pairs
    if len(pairs) < 2:
        return f"{cycle},too few hours ({len(pairs)}),,,"
    tmp = target.with_suffix(f".part{os.getpid()}"); o = nc.Dataset(tmp, "w", format="NETCDF4")                     # a name of its own: nothing is overwritten
    o.createDimension("time", None); o.createDimension("lat", NY); o.createDimension("lon", nx)
    tv = o.createVariable("time", "f8", ("time",)); tv.units = "hours since 1970-01-01 00:00:00"; tv.calendar = "standard"; tv.long_name = "valid time (UTC)"
    v = o.createVariable("lat", "f8", ("lat",)); v.units = "degrees_north"; v[:] = lat
    v = o.createVariable("lon", "f8", ("lon",)); v.units = "degrees_east"; v[:] = lon
    wl = o.createVariable("water_level", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, shuffle=True, chunksizes=(1, 335, 551), least_significant_digit=3)
    wl.units = "m"; wl.long_name = "combined water level of the coupled WRF-Hydro-ROMS model, operational forecast, not quality controlled"
    wl.comment = ("Composite of the two coupled models, as in the archive of the runs of Hurricane Ida. Ocean-model cells (mask_rho = 1): free-surface elevation; "
                  "missing where the cell is dry (zeta + h <= %.2f m). Land-model cells: depth of surface water above the ground. Stored at 1 mm precision." % DRY)
    o.title = f"Operational forecast of the Louisiana100m model, cycle {cycle}: hourly water level"; o.source_folder = str(folder); o.grid_file = grid
    o.history = "Packed from ocean_his_*.nc (zeta) and hydro_*.nc (sfcheadsubrt) by operational_water_level.py; the source files were only read."
    level = np.empty((NY, nx), "f4"); n = 0; bad = 0
    for when, of, hf in pairs:
        try:
            d = nc.Dataset(of); z = np.ma.filled(d["zeta"][0], np.nan).astype("f4")[:no]; d.close()                  # cycles before 2026-08-31 carry all 2680 rows; the rows north of the ocean-model rows hold no ocean cell
            x = nc.Dataset(hf); dep = np.ma.filled(x["sfcheadsubrt"][0], np.nan).astype("f4") / 1000.0; x.close()
        except Exception:
            bad += 1; continue
        level[:] = dep; level[no:][~np.isfinite(dep[no:])] = np.nan
        wet = mask & (np.abs(z) < 1e30) & (z + h > DRY); sea = np.full((no, nx), np.nan, "f4"); sea[wet] = z[wet]; level[:no] = np.where(mask, sea, dep[:no])
        ok = np.isfinite(level) & (np.abs(level) < 1e30); wl[n] = np.ma.array(np.where(ok, level, 0.0), mask=~ok); tv[n] = nc.date2num(when, tv.units, tv.calendar); n += 1
    o.hours = n; o.close(); os.replace(tmp, target)
    return f"{cycle},packed,{n},{pairs[0][0]:%Y-%m-%d %H:%M},{pairs[-1][0]:%Y-%m-%d %H:%M}" + (f",{bad} unreadable hours" if bad else "")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--archive", required=True); ap.add_argument("--grid", required=True); ap.add_argument("--out", required=True); ap.add_argument("--branch", default="NAM")
    ap.add_argument("--cycles", nargs="*"); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--min-hours", type=int, default=24); ap.add_argument("--max-hours", type=int, default=0)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if not (out / "grid_operational.nc").exists():
        mask, h, lon, lat = load_grid(a.grid); g = nc.Dataset(out / "grid_operational.nc", "w"); g.createDimension("lat_ocean_rows", mask.shape[0]); g.createDimension("lat", NY); g.createDimension("lon", mask.shape[1])
        g.createVariable("lat", "f8", ("lat",))[:] = lat; g.createVariable("lon", "f8", ("lon",))[:] = lon
        v = g.createVariable("h", "f4", ("lat_ocean_rows", "lon"), zlib=True); v.long_name = "bathymetry of the ocean-model rows, positive down (m)"; v[:] = h
        v = g.createVariable("mask_rho", "i1", ("lat_ocean_rows", "lon"), zlib=True); v.long_name = "1 = cell computed by the ocean model, 0 = by the land model"; v[:] = mask.astype("i1"); g.source = a.grid; g.close()
    jobs = []
    for c in sorted(os.listdir(a.archive)):
        if not re.fullmatch(r"20\d{6}", c) or (a.cycles and c not in a.cycles):
            continue
        folder = Path(a.archive) / c / a.branch
        try:                                                               # some old cycles cannot be opened by other users
            full = folder.is_dir() and len(list(folder.glob("ocean_his_*.nc"))) >= a.min_hours and len(list(folder.glob("hydro_*.nc"))) >= a.min_hours
        except OSError:
            full = False
        if full:
            jobs.append((c, str(folder), a.grid, str(out), a.max_hours))
    print(f"{len(jobs)} cycles to look at, oldest first: {jobs[0][0] if jobs else '-'} .. {jobs[-1][0] if jobs else '-'}", flush=True)
    with Pool(a.workers) as pool, open(out / "cycles.csv", "a") as log:
        for line in pool.imap(pack, jobs):
            print(line, flush=True); log.write(line + "\n"); log.flush()


if __name__ == "__main__":
    main()
