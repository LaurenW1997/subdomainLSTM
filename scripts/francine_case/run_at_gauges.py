"""Francine case: the water level of the run at the cells of the gauges, hour by hour.

For every station of --cells (columns source, station_id, j, i: cell of the 2680 x 5510 grid chosen for that gauge in the
comparison with the Ida hindcast, control_cells.csv) the script reads, from the raw output of the run,
    zeta          free surface of the ocean model at (j, i), if the row belongs to the ocean-model rows
    depth         depth of surface water of the land model at (j, i)  (sfcheadsubrt, mm -> m)
and from the grid of the ocean model its depth h and mask at the cell. Only single points are read; the output is only read.
Input : --run DIR (hires_ocean_his_*.nc and OUTPUT/HYDROOUT/hydro_YYYYMMDDHH.nc), --grid ROMS grid file, --cells CSV
Output: --out NPZ: time [T] (hours since 1970), zeta [T, S], depth [T, S], h_ocean [S], mask_ocean [S], source [S], station_id [S], j [S], i [S]
Usage : python run_at_gauges.py --run DIR --grid FILE --cells FILE --out FILE
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import time

import netCDF4 as nc
import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); ap.add_argument("--grid", required=True); ap.add_argument("--cells", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
    assert not os.path.exists(a.out), f"{a.out} exists"
    c = pd.read_csv(a.cells, dtype={"station_id": str}); J = c.j.to_numpy(int); I = c.i.to_numpy(int); S = len(c)
    g = nc.Dataset(a.grid); no, nx = g["mask_rho"].shape; inoc = J < no; h = np.full(S, np.nan); m = np.zeros(S, "i1")
    for s in np.where(inoc)[0]:
        h[s] = float(g["h"][J[s], I[s]]); m[s] = int(float(g["mask_rho"][J[s], I[s]]) > 0.5)
    g.close(); files = sorted(glob.glob(os.path.join(a.run, "hires_ocean_his_*.nc"))); T = len(files); print(f"{S} cells, {int(inoc.sum())} on ocean-model rows, {int(m.sum())} ocean-model cells; {T} hours", flush=True)
    zeta = np.full((T, S), np.nan, "f4"); depth = np.full((T, S), np.nan, "f4"); hours = np.zeros(T, "f8"); t0 = time.time(); epoch = dt.datetime(1970, 1, 1)
    for n, f in enumerate(files):
        d = nc.Dataset(f); t = d["ocean_time"]; when = nc.num2date(t[0], t.units, only_use_cftime_datetimes=False); when = dt.datetime(when.year, when.month, when.day, when.hour) + dt.timedelta(hours=1 if when.minute >= 30 else 0)
        z = d["zeta"]; z.set_auto_mask(False)
        for s in np.where(inoc)[0]:
            zeta[n, s] = z[0, J[s], I[s]]
        d.close(); hours[n] = (when - epoch).total_seconds() / 3600.0
        x = nc.Dataset(os.path.join(a.run, "OUTPUT", "HYDROOUT", f"hydro_{when:%Y%m%d%H}.nc")); v = x["sfcheadsubrt"]; v.set_auto_mask(False)
        if n == 0:
            print("sfcheadsubrt", v.shape, {k: v.getncattr(k) for k in v.ncattrs()}, flush=True)
        for s in range(S):
            depth[n, s] = v[0, J[s], I[s]] / 1000.0
        x.close()
        if n % 100 == 0:
            print(f"{when}  ({time.time() - t0:.0f} s)", flush=True)
    zeta[np.abs(zeta) > 1e30] = np.nan; depth[np.abs(depth) > 1e30] = np.nan
    np.savez_compressed(a.out, time=hours, zeta=zeta, depth=depth, h_ocean=h, mask_ocean=m, source=c.source.to_numpy(str), station_id=c.station_id.to_numpy(str), j=J, i=I)
    print(f"done in {time.time() - t0:.0f} s -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
