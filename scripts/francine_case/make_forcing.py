"""Francine case, atmospheric forcing, step 2: the files the two models read, from the HRRR pieces of hrrr_fetch.py.

Made the way the files of the Ida run were made (checked field by field against them for 2021-08-29 17:00):
    ocean model   seven files on the 2680 x 5510 grid: wind (Uwind, Vwind as HRRR gives them, along its own grid), pair (hPa),
                  tair (deg C), qair, rain, swrad, lwrad; one record an hour; bilinear from the HRRR grid
    land model    one file an hour, YYYYMMDDHH.LDASIN_DOMAIN1, on the 268 x 551 grid: T2D (K), Q2D, PSFC (Pa), U2D, V2D, SWDOWN, LWDOWN,
                  RAINRATE; LQFRAC 0; each file is a copy of an Ida file with the fields and the time replaced
    rain of hour t = precipitation rate of the 1-hour forecast of the HRRR cycle that starts at t (folder --rain); the other
    fields are the analysis of hour t (folder --hrrr)
Layout, names, chunking, compression and attributes of the ocean files are copied from the Ida files (--roms-template DIR).
The Lambert projection of HRRR is written out here, so that nothing beyond numpy, pandas and netCDF4 is needed.
Usage : python make_forcing.py --what wind|pair|tair|qair|rain|swrad|lwrad|ldasin --hrrr DIR --rain DIR --start "2024-08-14 00:00" --end "2024-09-19 00:00"
                               --roms-template DIR --ldasin-template FILE --out-roms DIR --out-ldasin DIR
        A file already there is never overwritten.
"""
from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd

ROMS = {"wind": (["Uwind", "Vwind"], "wind_time", 1.0, 0.0), "pair": (["Pair"], "pair_time", 0.01, 0.0), "tair": (["Tair"], "tair_time", 1.0, -273.15), "qair": (["Qair"], "qair_time", 1.0, 0.0),
        "rain": (["rain"], "rain_time", 1.0, 0.0), "swrad": (["swrad"], "srf_time", 1.0, 0.0), "lwrad": (["lwrad"], "lrf_time", 1.0, 0.0)}
LDAS = {"T2D": "Tair", "Q2D": "Qair", "PSFC": "Pair", "U2D": "Uwind", "V2D": "Vwind", "SWDOWN": "swrad", "LWDOWN": "lwrad", "RAINRATE": "rain"}
R_EARTH, LAT0, LON0 = 6371229.0, 38.5, -97.5


def lcc(lon, lat):
    """Lambert conformal conic of HRRR (one standard parallel 38.5 N, central meridian 97.5 W, sphere): metres east and north of its origin."""
    p0 = np.deg2rad(LAT0); n = np.sin(p0); F = np.cos(p0) * np.tan(np.pi / 4 + p0 / 2) ** n / n
    rho = R_EARTH * F / np.tan(np.pi / 4 + np.deg2rad(np.asarray(lat, "f8")) / 2) ** n; rho0 = R_EARTH * F / np.tan(np.pi / 4 + p0 / 2) ** n; th = n * np.deg2rad(np.asarray(lon, "f8") - LON0)
    return rho * np.sin(th), rho0 - rho * np.cos(th)


class Source:
    def __init__(self, hrrr: str, rain: str):
        self.h, self.r = Path(hrrr), Path(rain); b = np.load(self.h / "box.npz"); self.x0, self.y0 = lcc(float(b["first_point_lon"]), float(b["first_point_lat"])); self.dx = float(b["dx"])
        self.jb, self.ib = int(b["first_row"]), int(b["first_col"]); self.shape = b["lon"].shape
        x, y = lcc(b["lon"], b["lat"]); i = (x - self.x0) / self.dx - self.ib; j = (y - self.y0) / self.dx - self.jb                # the box must sit where the projection says
        assert np.abs(i - np.arange(self.shape[1])[None, :]).max() < 0.02 and np.abs(j - np.arange(self.shape[0])[:, None]).max() < 0.02, "projection and HRRR coordinates disagree"

    def weights(self, lon, lat):
        x, y = lcc(lon, lat); fx = (x - self.x0) / self.dx - self.ib; fy = (y - self.y0) / self.dx - self.jb; i = np.floor(fx).astype(np.int32); j = np.floor(fy).astype(np.int32)
        assert i.min() >= 0 and j.min() >= 0 and i.max() < self.shape[1] - 1 and j.max() < self.shape[0] - 1, "the grid reaches outside the HRRR box"
        return j, i, (fy - j).astype(np.float32), (fx - i).astype(np.float32)

    def field(self, name: str, when: pd.Timestamp) -> np.ndarray:
        f = (self.r if name == "rain" else self.h) / f"{when:%Y%m%d%H}.npz"; a = np.load(f)[name].astype(np.float32); assert a.shape == self.shape and np.isfinite(a).all(), f"{f} {name}"
        return a


def interp(f, w):
    j, i, wy, wx = w
    return (1 - wy) * ((1 - wx) * f[j, i] + wx * f[j, i + 1]) + wy * ((1 - wx) * f[j + 1, i] + wx * f[j + 1, i + 1])


def roms(what: str, a, src: Source, hours) -> None:
    names, tname, scale, offset = ROMS[what]; out = Path(a.out_roms) / f"{what}_on_roms.nc"; assert not out.exists(), f"{out} exists"; out.parent.mkdir(parents=True, exist_ok=True)
    tpl = nc.Dataset(Path(a.roms_template) / f"{what}_on_roms.nc"); lon = np.array(tpl["lon"][:]); lat = np.array(tpl["lat"][:]); w = src.weights(lon, lat); ny, nx = lon.shape
    tmp = out.with_suffix(f".part{os.getpid()}"); o = nc.Dataset(tmp, "w", format=tpl.data_model); o.createDimension(tname, None); o.createDimension("y", ny); o.createDimension("x", nx)
    tv = o.createVariable(tname, "f8", (tname,))
    for k in tpl[tname].ncattrs():
        tv.setncattr(k, tpl[tname].getncattr(k))
    for c, x in (("lon", lon), ("lat", lat)):
        v = o.createVariable(c, tpl[c].dtype, ("y", "x"), zlib=True, complevel=4, shuffle=True)
        for k in tpl[c].ncattrs():
            v.setncattr(k, tpl[c].getncattr(k))
        v[:] = x
    V = {}
    for nme in names:
        ch = tpl[nme].chunking(); ch = (1, min(ch[1], ny), min(ch[2], nx)) if ch != "contiguous" else None; v = o.createVariable(nme, "f4", (tname, "y", "x"), zlib=True, complevel=4, shuffle=True, chunksizes=ch)
        for k in tpl[nme].ncattrs():
            if k != "_FillValue":
                v.setncattr(k, tpl[nme].getncattr(k))
        V[nme] = v
    for k in tpl.ncattrs():
        o.setncattr(k, tpl.getncattr(k))
    o.description = (f"Hurricane Francine case, {hours[0]} to {hours[-1]} UTC, from HRRR as the files of the Ida run: " + ("precipitation rate of the 1-hour forecast of the cycle starting at each hour" if what == "rain" else "analysis of each hour")
                     + "; values as in the Ida files (Pair in hPa, Tair in deg C) whatever the units attribute says.")
    t0 = time.time(); mjd = ((hours - pd.Timestamp("1858-11-17")) / pd.Timedelta(days=1)).to_numpy()
    for n, when in enumerate(hours):
        tv[n] = mjd[n]
        for nme in names:
            r = interp(src.field(nme, when), w) * scale + offset; V[nme][n] = r.astype(np.float32)
        if n % 48 == 0:
            print(f"{what} {when}  {names[-1]} {float(r.min()):.5g} .. {float(r.max()):.5g}  ({time.time() - t0:.0f} s)", flush=True)
    o.close(); tpl.close(); os.replace(tmp, out); print(f"{what} DONE: {len(hours)} hours in {time.time() - t0:.0f} s -> {out}", flush=True)


def ldasin(a, src: Source, hours) -> None:
    out = Path(a.out_ldasin); out.mkdir(parents=True, exist_ok=True); g = nc.Dataset(a.ldasin_template); w = src.weights(np.array(g["lon"][:], "f8"), np.array(g["lat"][:], "f8")); g.close(); t0 = time.time(); made = 0
    for n, when in enumerate(hours):
        f = out / f"{when:%Y%m%d%H}.LDASIN_DOMAIN1"
        if f.exists():
            continue
        tmp = out / f".{f.name}.part{os.getpid()}"; shutil.copyfile(a.ldasin_template, tmp); os.chmod(tmp, 0o644)
        with nc.Dataset(tmp, "r+") as o:
            for name, srcname in LDAS.items():
                o[name][0, :, :] = interp(src.field(srcname, when), w).astype(np.float64)
            o["LQFRAC"][0, :, :] = 0.0; sec = int((when - pd.Timestamp("1970-01-01")).total_seconds()); o["valid_time"][0] = sec; o["time"][0] = sec // 60
            o["Times"][:] = np.array([c.encode() for c in when.strftime("%Y-%m-%d_%H:%M:%S")], dtype="S1")
        os.replace(tmp, f); made += 1
        if n % 96 == 0:
            print(f"ldasin {f.name}  ({time.time() - t0:.0f} s)", flush=True)
    print(f"ldasin DONE: {made} files written, {len(hours)} hours, {time.time() - t0:.0f} s -> {out}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--what", required=True, choices=list(ROMS) + ["ldasin"]); ap.add_argument("--hrrr", required=True); ap.add_argument("--rain", required=True); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
    ap.add_argument("--roms-template"); ap.add_argument("--ldasin-template"); ap.add_argument("--out-roms"); ap.add_argument("--out-ldasin"); a = ap.parse_args()
    src = Source(a.hrrr, a.rain); hours = pd.date_range(a.start, a.end, freq="h")
    miss = [str(h) for h in hours if not (Path(a.hrrr) / f"{h:%Y%m%d%H}.npz").exists() or not (Path(a.rain) / f"{h:%Y%m%d%H}.npz").exists()]; assert not miss, f"HRRR pieces missing for {miss[:5]}"
    ldasin(a, src, hours) if a.what == "ldasin" else roms(a.what, a, src, hours)


if __name__ == "__main__":
    main()
