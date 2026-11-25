"""Flood map: get runs other than the twelve of Hurricane Ida ready for the mapping model of p2m_paper.py.

p2m_paper.py reads, per run, water_level_<run>.nc in --ida and the control-point series X of sums_<run>.npz in --sums.
The operational forecasts (operational_water_level.py) and the Francine hindcast (francine_case/pack_run.py) are packed in the
same layout; this script adds what is still missing, in new folders, without touching the old ones:
  subset   the hours --start .. --end of a packed run as a file of its own (same layout), e.g. landfall plus and minus five days
  folder   a folder that holds, as links, the grid and the runs of Ida plus the new runs under the names the fit expects
  series   sums_<run>.npz with X [T, control points] for the new runs: water surface elevation at the cells of the control
           points minus xref, exactly as mapping_fit.py makes it (ocean-model cell: free surface; land-model cell: depth minus
           h of the Ida grid; a dry ocean-model cell: bed level; a missing land value: the hour before); the sums of the Ida
           runs, xref.npy and controls_used.csv are linked / copied from --old-sums
  differ   which cells of a run's own grid differ from the Ida grid (ocean depth by more than --tol m): differ_<name>.npz
Usage : python prepare_more_runs.py subset --src FILE --start "2024-09-06 22:00" --end "2024-09-16 22:00" --out FILE
        python prepare_more_runs.py folder --ida DIR --new NAME=FILE ... --out DIR
        python prepare_more_runs.py series --ida DIR --old-sums DIR --runs NAME ... --out DIR [--workers 16]
        python prepare_more_runs.py differ --ida DIR --grid FILE --name NAME --out DIR
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import BLOCK, RUNS, Reader, control_series, grid  # noqa: E402


def cmd_subset(a) -> None:
    out = Path(a.out); assert not out.exists(), f"{out} exists"; s = netCDF4.Dataset(a.src); t = s["time"]; when = pd.DatetimeIndex(netCDF4.num2date(t[:], t.units, only_use_cftime_datetimes=False))
    k = np.where((when >= a.start) & (when <= a.end))[0]; assert len(k) and (np.diff(k) == 1).all(); tmp = out.with_suffix(f".part{os.getpid()}"); o = netCDF4.Dataset(tmp, "w", format="NETCDF4")
    o.createDimension("time", None); o.createDimension("lat", len(s["lat"])); o.createDimension("lon", len(s["lon"]))
    for name in ("time", "lat", "lon"):
        v = o.createVariable(name, "f8", (name,)); v.setncatts({x: s[name].getncattr(x) for x in s[name].ncattrs()}); v[:] = s[name][k] if name == "time" else s[name][:]
    w = o.createVariable("water_level", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, shuffle=True, chunksizes=(1, 335, 551), least_significant_digit=3); w.setncatts({x: s["water_level"].getncattr(x) for x in s["water_level"].ncattrs() if x not in ("_FillValue", "least_significant_digit")})
    for n, kk in enumerate(k):
        w[n] = s["water_level"][kk]
    o.setncatts({x: s.getncattr(x) for x in s.ncattrs()}); o.hours = len(k); o.subset_of = str(a.src); o.subset_hours = f"{when[k[0]]} .. {when[k[-1]]} UTC"; o.close(); os.replace(tmp, out); print(f"{len(k)} hours {when[k[0]]} .. {when[k[-1]]} -> {out}")


def cmd_folder(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); ida = Path(a.ida).resolve(); n = 0
    for f in [ida / "grid_lower_mississippi_100m.nc"] + [ida / f"water_level_{r}.nc" for r in RUNS]:
        if not (out / f.name).exists():
            os.symlink(f, out / f.name); n += 1
    for item in a.new:
        name, _, f = item.partition("="); f = Path(f).resolve(); assert f.exists(), f; link = out / f"water_level_{name}.nc"
        if not link.exists():
            os.symlink(f, link); n += 1
    print(f"{n} links made in {out}; it now holds {len(list(out.glob('water_level_*.nc')))} runs")


def series_one(job):
    ida, run, cj, ci, xref, out = job; f = Path(out) / f"sums_{run}.npz"
    if f.exists():
        return f"{run}: exists"
    t0 = time.time(); h, roms, _, _ = grid(Path(ida)); rd = Reader(Path(ida), run, h, roms); X = []
    for k0 in range(0, rd.T, BLOCK):
        X.append(control_series(rd.block(k0, min(k0 + BLOCK, rd.T)), cj, ci, h, roms) - xref[None, :])
    X = np.concatenate(X); assert np.isfinite(X).all(), f"{run}: control-point series has missing values"; np.savez(f, X=X, n=rd.T)
    return f"{run}: {rd.T} hours, level at the control points {X.min():+.2f} .. {X.max():+.2f} m relative to the reference, {time.time() - t0:.0f} s"


def cmd_series(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); old = Path(a.old_sums).resolve()
    for name in ("xref.npy", "controls_used.csv"):
        if not (out / name).exists():
            shutil.copyfile(old / name, out / name)
    for r in RUNS:
        if not (out / f"sums_{r}.npz").exists():
            os.symlink(old / f"sums_{r}.npz", out / f"sums_{r}.npz")
    c = pd.read_csv(out / "controls_used.csv", dtype={"station_id": str}); cj, ci = c.best_j.to_numpy(int), c.best_i.to_numpy(int); xref = np.load(out / "xref.npy"); assert len(xref) == len(c)
    with Pool(a.workers) as pool:
        for msg in pool.imap_unordered(series_one, [(a.ida, r, cj, ci, xref, str(out)) for r in a.runs]):
            print(msg, flush=True)


def cmd_differ(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); h, roms, _, _ = grid(Path(a.ida)); g = netCDF4.Dataset(a.grid); m = np.asarray(g["mask_rho"][:]) > 0; hr = np.ma.filled(g["h"][:], np.nan); no = m.shape[0]
    assert (m == roms[:no]).all() and not roms[no:].any(), "the ocean-model cells are not the same as in the Ida grid"; d = np.zeros(h.shape, bool); d[:no] = m & (np.abs(hr - h[:no]) > a.tol)
    np.savez_compressed(out / f"differ_{a.name}.npz", differ=d, tol=a.tol, grid=str(a.grid)); print(f"{a.name}: ocean depth differs from the Ida grid by more than {a.tol} m at {int(d.sum())} of {int(m.sum())} ocean-model cells ({100 * d.sum() / m.sum():.2f}%)")


def main() -> None:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("subset"); p.add_argument("--src", required=True); p.add_argument("--start", required=True); p.add_argument("--end", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("folder"); p.add_argument("--ida", required=True); p.add_argument("--new", nargs="+", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("series"); p.add_argument("--ida", required=True); p.add_argument("--old-sums", required=True); p.add_argument("--runs", nargs="+", required=True); p.add_argument("--out", required=True); p.add_argument("--workers", type=int, default=16)
    p = sub.add_parser("differ"); p.add_argument("--ida", required=True); p.add_argument("--grid", required=True); p.add_argument("--name", required=True); p.add_argument("--out", required=True); p.add_argument("--tol", type=float, default=0.01)
    a = ap.parse_args(); {"subset": cmd_subset, "folder": cmd_folder, "series": cmd_series, "differ": cmd_differ}[a.cmd](a)


if __name__ == "__main__":
    main()
