"""Francine case: hourly fields of the run for animations (the raw output is only read).

One quantity W per cell of the 2680 x 5510 grid and hour:
    ocean-model cell   free surface when the cell is wet (zeta + h > 0.25 m), the ground (-h) when it is dry
    land-model cell    depth of surface water (sfcheadsubrt, mm -> m)
and its change from the mean of the hours --base-start .. --base-end (before the storm). For a cell that is dry before the
storm the change is the depth of water that comes to stand on it; for a cell under water it is the rise or fall of the level.
The change is averaged over blocks of --coarse cells for the whole grid, and of --zoom-coarse cells inside --zoom.
Winds and pressure of the forcing (HRRR pieces of hrrr_fetch.py) for the same hours are added as they are.
Input : --run DIR (hires_ocean_his_*.nc, OUTPUT/HYDROOUT/hydro_*.nc; file 1 = --first-hour), --grid ROMS grid file, --hrrr DIR
Output: --out NPZ: time, change [T, y, x] and zoom_change [T, y, x] (float16, m), lon/lat of both, open_water (share of a block
        that is water before the storm), zoom_open_water, wind_u, wind_v, pair, wind_lon, wind_lat
Usage : python run_fields.py --run DIR --grid FILE --hrrr DIR --start "2024-09-09 00:00" --end "2024-09-14 00:00"
                             --base-start "2024-09-05 21:00" --base-end "2024-09-08 23:00" --out FILE [--workers 16]
"""
from __future__ import annotations

import argparse
import os
import time
from multiprocessing import Pool

import netCDF4 as nc
import numpy as np
import pandas as pd

DRY, NY = 0.25, 2680
G = {}


def field(when: pd.Timestamp) -> np.ndarray:
    k = int((when - G["first"]) / pd.Timedelta(hours=1)) + 1; d = nc.Dataset(os.path.join(G["run"], f"hires_ocean_his_{k:05d}.nc")); t = d["ocean_time"]
    got = pd.Timestamp(nc.num2date(t[0], t.units, only_use_cftime_datetimes=False)).round("h"); assert got == when, f"file {k} holds {got}, not {when}"
    z = np.ma.filled(d["zeta"][0], np.nan).astype("f4"); d.close()
    x = nc.Dataset(os.path.join(G["run"], "OUTPUT", "HYDROOUT", f"hydro_{when:%Y%m%d%H}.nc")); w = np.ma.filled(x["sfcheadsubrt"][0], np.nan).astype("f4") / 1000.0; x.close(); w[np.abs(w) > 1e5] = np.nan
    mask, h = G["mask"], G["h"]; no = mask.shape[0]; wet = mask & (np.abs(z) < 1e30) & (z + h > DRY); w[:no][mask] = np.where(wet, z, -h)[mask]
    return w


def block(a: np.ndarray, c: int) -> np.ndarray:
    ny, nx = (a.shape[0] // c) * c, (a.shape[1] // c) * c; b = a[:ny, :nx].reshape(ny // c, c, nx // c, c); n = np.isfinite(b).sum((1, 3))
    return np.where(n > 0, np.nansum(b, (1, 3)) / np.maximum(n, 1), np.nan).astype("f4")


def frame(when: pd.Timestamp):
    ch = field(when) - G["base"]; j0, j1, i0, i1 = G["zoom"]
    return np.clip(block(ch, G["coarse"]), -30, 30).astype("f2"), np.clip(block(ch[j0:j1, i0:i1], G["zcoarse"]), -30, 30).astype("f2")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); ap.add_argument("--grid", required=True); ap.add_argument("--hrrr", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--base-start", required=True); ap.add_argument("--base-end", required=True); ap.add_argument("--first-hour", default="2024-08-14 00:00")
    ap.add_argument("--coarse", type=int, default=8); ap.add_argument("--zoom", default="-91.6,-89.4,28.95,30.45"); ap.add_argument("--zoom-coarse", type=int, default=4); ap.add_argument("--workers", type=int, default=16); a = ap.parse_args()
    assert not os.path.exists(a.out), f"{a.out} exists"; t0 = time.time()
    g = nc.Dataset(a.grid); mask = np.ma.filled(g["mask_rho"][:], 0) > 0.5; h = np.ma.filled(g["h"][:], np.nan).astype("f4"); lon = np.ma.filled(g["lon_rho"][0, :], np.nan).astype("f8"); lat2 = np.ma.filled(g["lat_rho"][:, 0], np.nan).astype("f8"); g.close()
    no = mask.shape[0]; merc = lambda p: np.log(np.tan(np.pi / 4 + np.radians(p) / 2)); y0 = merc(lat2[0]); dy = (merc(lat2[-1]) - y0) / (no - 1); lat = np.degrees(2 * np.arctan(np.exp(y0 + dy * np.arange(NY))) - np.pi / 2)
    zl = [float(v) for v in a.zoom.split(",")]; i0, i1 = int(np.searchsorted(lon, zl[0])), int(np.searchsorted(lon, zl[1])); j0, j1 = int(np.searchsorted(lat, zl[2])), int(np.searchsorted(lat, zl[3]))
    G.update(run=a.run, mask=mask, h=h, first=pd.Timestamp(a.first_hour), coarse=a.coarse, zcoarse=a.zoom_coarse, zoom=(j0, j1, i0, i1))
    base_hours = pd.date_range(a.base_start, a.base_end, freq="h"); hours = pd.date_range(a.start, a.end, freq="h"); print(f"grid {NY} x {len(lon)}, ocean-model rows {no}; baseline {len(base_hours)} hours, frames {len(hours)}; zoom rows {j0}:{j1} columns {i0}:{i1}", flush=True)
    s = np.zeros((NY, len(lon)), "f8"); n = np.zeros((NY, len(lon)), "i4"); wetn = np.zeros(mask.shape, "i4")
    with Pool(a.workers) as pool:
        for k, w in enumerate(pool.imap_unordered(field, list(base_hours))):
            ok = np.isfinite(w); s[ok] += w[ok]; n += ok; wetn += (w[:no] > -h + 1e-3) & mask
    base = np.where(n > 0, s / np.maximum(n, 1), np.nan).astype("f4"); G["base"] = base; print(f"baseline done ({time.time() - t0:.0f} s)", flush=True)
    water = base > 0.5; water[:no][mask] = (wetn >= 0.5 * len(base_hours))[mask]                                # open water before the storm: ocean cell wet most of the time, land-model cell with more than 0.5 m of water
    with Pool(a.workers) as pool:                                                                              # started after the baseline exists, so that the workers hold it
        res = pool.map(frame, list(hours), chunksize=1)
    print(f"frames done ({time.time() - t0:.0f} s)", flush=True)
    c, zc = a.coarse, a.zoom_coarse; cen = lambda v, k: v[: (len(v) // k) * k].reshape(-1, k).mean(1)
    H = os.path.join(a.hrrr, "box.npz"); b = np.load(H); U = []; V = []; P = []
    for when in hours:
        z = np.load(os.path.join(a.hrrr, f"{when:%Y%m%d%H}.npz")); U.append(z["Uwind"].astype("f2")); V.append(z["Vwind"].astype("f2")); P.append((z["Pair"] / 100.0).astype("f4"))
    np.savez_compressed(a.out, time=np.asarray(hours.strftime("%Y-%m-%d %H:%M")), change=np.array([r[0] for r in res]), zoom_change=np.array([r[1] for r in res]), lon=cen(lon, c), lat=cen(lat, c), zoom_lon=cen(lon[i0:i1], zc), zoom_lat=cen(lat[j0:j1], zc),
                        open_water=block(water.astype("f4"), c), zoom_open_water=block(water[j0:j1, i0:i1].astype("f4"), zc), ocean_model=block(np.vstack([mask, np.zeros((NY - no, len(lon)), bool)]).astype("f4"), c),
                        wind_u=np.array(U), wind_v=np.array(V), pair=np.array(P), wind_lon=b["lon"], wind_lat=b["lat"], baseline=f"{a.base_start} .. {a.base_end}")
    print(f"done in {time.time() - t0:.0f} s -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
