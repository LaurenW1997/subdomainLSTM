"""Extract ROMS sea level (zeta) at the operational stations' grid cells from the group's forecast archive (read-only).

Archive: /work/zlei2/output/LSU_operational_system_qbd/results/<domain>/<YYYYMMDD>/NAM/ocean_his_NNNNN.nc
         one hourly record per file, 00001.. (00001 = first forecast hour of the cycle).
For each cycle only the first --hours files are used (closest to the analysis, least forecast drift).
Output: <out>/<domain>_zeta.csv with columns cycle, hour, time_utc, station_id, zeta_wet_m, zeta_cell_m
Runs on QBD (python with netCDF4, e.g. /work/yixuan97/conda_envs/cfml/bin/python), from a batch job.
Usage: python roms_zeta_at_stations.py --map operational_stations_grid_datum.csv --out DIR [--hours 24] [--domains Louisiana100m ...]
"""
from __future__ import annotations

import argparse
import glob
import os
import time
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

ARCHIVE = "/work/zlei2/output/LSU_operational_system_qbd/results"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--domains", nargs="*", default=["Louisiana100m", "Texas100m", "Galveston100m"])
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(a.map, dtype={"station_id": str})
    for dom in a.domains:
        g = m[m.domain == dom]
        if g.empty:
            continue
        jw, iw = g.j_eta_wet.to_numpy(int), g.i_xi_wet.to_numpy(int)
        jc, ic = g.j_eta.to_numpy(int), g.i_xi.to_numpy(int)
        cycles = sorted(d for d in os.listdir(f"{ARCHIVE}/{dom}") if d.isdigit())
        rows = []
        t0 = time.time()
        for cyc in cycles:
            files = sorted(glob.glob(f"{ARCHIVE}/{dom}/{cyc}/NAM/ocean_his_*.nc"))[: a.hours]
            for f in files:
                try:
                    with netCDF4.Dataset(f) as ds:
                        tvar = ds.variables["ocean_time"]
                        tt = netCDF4.num2date(tvar[:], tvar.units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
                        z = ds.variables["zeta"]
                        zw = np.array([float(z[0, j, i]) for j, i in zip(jw, iw)])   # scattered point reads
                        zc = np.array([float(z[0, j, i]) for j, i in zip(jc, ic)])
                        fill = getattr(z, "_FillValue", 1e37)
                        zw[np.abs(zw) > 1e10] = np.nan; zc[np.abs(zc) > 1e10] = np.nan
                        zw[zw == fill] = np.nan; zc[zc == fill] = np.nan
                except Exception as e:  # noqa: BLE001
                    print("skip", f, e, flush=True); continue
                hour = int(Path(f).stem.split("_")[-1])
                for sid, a_, b_ in zip(g.station_id, zw, zc):
                    rows.append((cyc, hour, pd.Timestamp(tt[0]), sid, a_, b_))
            if cycles.index(cyc) % 10 == 0:
                print(dom, cyc, f"{len(rows)} rows, {time.time() - t0:.0f} s", flush=True)
        df = pd.DataFrame(rows, columns=["cycle", "hour", "time_utc", "station_id", "zeta_wet_m", "zeta_cell_m"])
        df.to_csv(out / f"{dom}_zeta.csv", index=False)
        print(dom, "done:", len(df), "rows,", df.cycle.nunique(), "cycles", flush=True)


if __name__ == "__main__":
    main()
