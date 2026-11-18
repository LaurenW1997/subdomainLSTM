"""Flood map, step 2: the mapping model (after Bao et al. 2025) - from the water level at the control points to every cell.

For every grid cell a linear model is fitted on the output of the numerical model:
    water_level(cell, t) = a(cell) + sum_p b(cell, p) * [ WSE(control point p, t) - mean_p ]
water_level is the variable of the archive (ocean-model cells: free surface; land-model cells: depth above the ground),
the depth follows as water_level + h on ocean-model cells and water_level on land-model cells, cut at zero.
The fit is a ridge regression that assumes the inputs carry an independent error of --noise metres (the control points
will be fed with forecasts and observations, which differ from the numerical model by about that much; without it the
many tide gauges that move together get large coefficients of opposite sign).
Stages (each can be run alone):
  sums      one pass over every run (in parallel): the sums the regression needs, saved per run, so any run can be left out
  fit       coefficients from all runs except --holdout (or from all with --holdout none)
  evaluate  the left-out run rebuilt from its own control-point series and compared with the model, cell by cell
Missing values of the archive: a dry ocean-model cell is given the bed level (depth 0); a removed spike on a land-model
cell takes the value of the hour before.
Input : --ida DIR (grid_lower_mississippi_100m.nc, water_level_<run>.nc), --controls CSV (control_points.py, with best_j, best_i, best_r),
        --live FILE (station ids that have a forecast in real time; optional)
Output: --work DIR: sums_<run>.npz / sxy_<run>.npy, coef_without_<run>.npy, eval_<run>.npz
Usage : python mapping_fit.py --ida DIR --controls CSV --work DIR --stage sums fit evaluate --holdout Exp1_fully_coupled
"""
from __future__ import annotations

import argparse
import os
import time
from multiprocessing import Pool
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

RUNS = ["Exp1_fully_coupled", "Exp2_no_wind", "Exp3_no_precipitation", "Exp4_river_only", "Exp5_Ida_base", "Exp6_absolute_base", "Exp7_wind_base", "Exp8_precipitation_base",
        "drought_river_storm", "drought_river_no_storm", "flood_river_storm", "flood_river_no_storm"]
BLOCK = 24


def grid(ida: Path):
    g = netCDF4.Dataset(ida / "grid_lower_mississippi_100m.nc")
    h = np.asarray(np.ma.filled(g["h"][:], np.nan), np.float32); roms = np.asarray(g["domain_mask"][:]) == 1
    lat = np.asarray(g["lat"][:]); lon = np.asarray(g["lon"][:]); g.close()
    return h, roms, lat, lon


def controls(a) -> pd.DataFrame:
    c = pd.read_csv(a.controls, dtype={"station_id": str})
    c = c[(c.obs_hours >= 200) & (c.best_r >= a.min_r)].copy()
    if a.live:
        live = set(Path(a.live).read_text().split()); c = c[c.station_id.isin(live)]
    return c.sort_values("station_id").reset_index(drop=True)


class Reader:
    """Hourly fields of one run as the regression sees them: water_level without missing values, in blocks of hours."""

    def __init__(self, ida: Path, run: str, h, roms):
        self.d = netCDF4.Dataset(ida / f"water_level_{run}.nc"); self.v = self.d["water_level"]; self.T = self.v.shape[0]
        self.h, self.roms = h, roms; self.prev = np.zeros(h.shape, np.float32); self.bed = -h

    def block(self, k0: int, k1: int) -> np.ndarray:
        y = np.ma.filled(self.v[k0:k1], np.nan).astype(np.float32)
        for k in range(y.shape[0]):
            m = np.isnan(y[k])
            if m.any():
                mr = m & self.roms; y[k][mr] = self.bed[mr]                 # dry ocean-model cell: bed level, depth 0
                ml = m & ~self.roms; y[k][ml] = self.prev[ml]               # removed spike on land: the hour before
            self.prev = y[k]
        return y


def control_series(y: np.ndarray, cj, ci, h, roms) -> np.ndarray:
    x = y[:, cj, ci].astype(np.float64)
    return np.where(roms[cj, ci][None, :], x, x - h[cj, ci][None, :].astype(np.float64))       # water surface elevation


def sums_one(args):
    ida, run, cj, ci, xref, work = args
    out = Path(work) / f"sums_{run}.npz"
    if out.exists():
        return f"{run}: exists"
    t0 = time.time(); h, roms, _, _ = grid(Path(ida)); rd = Reader(Path(ida), run, h, roms)
    N = h.size; P = len(cj)
    Sxy = np.zeros((P, N), np.float64); Sy = np.zeros(N, np.float64); Syy = np.zeros(N, np.float64); Sx = np.zeros(P); Sxx = np.zeros((P, P))
    dmin = np.full(N, np.inf, np.float32); dmax = np.full(N, -np.inf, np.float32); X = []
    add = np.where(roms, h, 0).astype(np.float32).ravel()                    # water_level + add = depth
    for k0 in range(0, rd.T, BLOCK):
        y = rd.block(k0, min(k0 + BLOCK, rd.T)); x = control_series(y, cj, ci, h, roms) - xref[None, :]
        Y = y.reshape(y.shape[0], -1)
        Sxy += (x.astype(np.float32).T @ Y); Sy += Y.sum(0, dtype=np.float64); Syy += np.einsum("ij,ij->j", Y, Y, dtype=np.float64)
        Sx += x.sum(0); Sxx += x.T @ x; X.append(x)
        dep = Y + add[None, :]; dmin = np.minimum(dmin, dep.min(0)); dmax = np.maximum(dmax, dep.max(0))
    np.save(Path(work) / f"sxy_{run}.npy", Sxy.astype(np.float32))
    np.savez(out, Sx=Sx, Sxx=Sxx, Sy=Sy, Syy=Syy, n=rd.T, X=np.concatenate(X), dmin=dmin, dmax=dmax)
    return f"{run}: {rd.T} hours, {time.time() - t0:.0f} s"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True); ap.add_argument("--controls", required=True); ap.add_argument("--live"); ap.add_argument("--work", required=True)
    ap.add_argument("--stage", nargs="+", default=["sums", "fit", "evaluate"]); ap.add_argument("--holdout", default="Exp1_fully_coupled")
    ap.add_argument("--min-r", type=float, default=0.8); ap.add_argument("--noise", type=float, default=0.12, help="assumed error of the inputs (m)"); ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    ida, work = Path(a.ida), Path(a.work); work.mkdir(parents=True, exist_ok=True)
    h, roms, lat, lon = grid(ida); N = h.size
    c = controls(a); cj, ci = c.best_j.to_numpy(int), c.best_i.to_numpy(int); P = len(c)
    c.to_csv(work / "controls_used.csv", index=False)
    print(f"{P} control points, {N} cells, noise {a.noise} m")
    ref = work / "xref.npy"
    if not ref.exists():                                                    # a fixed reference level per control point keeps the sums well conditioned
        rd = Reader(ida, "Exp6_absolute_base", h, roms); np.save(ref, control_series(rd.block(0, BLOCK), cj, ci, h, roms).mean(0))
    xref = np.load(ref)

    if "sums" in a.stage:
        os.environ.setdefault("OMP_NUM_THREADS", "8")
        with Pool(min(a.workers, len(RUNS))) as pool:
            for msg in pool.imap_unordered(sums_one, [(str(ida), r, cj, ci, xref, str(work)) for r in RUNS]):
                print("  sums", msg, flush=True)

    train = [r for r in RUNS if r != a.holdout]; tag = a.holdout if a.holdout in RUNS else "none"
    cf = work / f"coef_without_{tag}.npy"
    if "fit" in a.stage:
        t0 = time.time(); n = 0; Sx = np.zeros(P); Sxx = np.zeros((P, P)); Sy = np.zeros(N); Sxy = np.zeros((P, N))
        for r in train:
            z = np.load(work / f"sums_{r}.npz"); n += int(z["n"]); Sx += z["Sx"]; Sxx += z["Sxx"]; Sy += z["Sy"]; Sxy += np.load(work / f"sxy_{r}.npy")
        xm, ym = Sx / n, Sy / n
        Cxx = Sxx - n * np.outer(xm, xm); Cxy = Sxy - n * np.outer(xm, ym)
        B = np.linalg.solve(Cxx + n * a.noise ** 2 * np.eye(P), Cxy)        # ridge: inputs with an independent error of `noise`
        np.save(cf, B.astype(np.float32)); np.savez(work / f"fitmeta_without_{tag}.npz", xm=xm, ym=ym.astype(np.float32), n=n, runs=np.array(train), noise=a.noise)
        print(f"fit without {tag}: {n} hours of {len(train)} runs, {time.time() - t0:.0f} s; largest |coefficient| {np.abs(B).max():.2f}")

    if "evaluate" in a.stage and a.holdout in RUNS:
        t0 = time.time(); B = np.load(cf); m = np.load(work / f"fitmeta_without_{tag}.npz"); xm, ym = m["xm"], m["ym"]
        add = np.where(roms, h, 0).astype(np.float32).ravel(); rd = Reader(ida, a.holdout, h, roms)
        rng = np.random.default_rng(0)
        res = {k: {"se": np.zeros(N), "pk": np.zeros(N, np.float32), "wet_both": np.zeros(N, np.int32), "wet_pred": np.zeros(N, np.int32)} for k in ("exact", "noisy")}
        pk_true = np.zeros(N, np.float32); wet_true = np.zeros(N, np.int32); mean_true = np.zeros(N)
        for k0 in range(0, rd.T, BLOCK):
            y = rd.block(k0, min(k0 + BLOCK, rd.T)); x = control_series(y, cj, ci, h, roms) - xref[None, :]
            dt = np.maximum(y.reshape(y.shape[0], -1) + add[None, :], 0)
            pk_true = np.maximum(pk_true, dt.max(0)); wt = dt > 0.1; wet_true += wt.sum(0); mean_true += dt.sum(0, dtype=np.float64)
            for k, xx in (("exact", x), ("noisy", x + rng.normal(0, a.noise, x.shape))):
                dp = np.maximum((xx - xm[None, :]).astype(np.float32) @ B + ym[None, :] + add[None, :], 0)
                r = res[k]; r["se"] += ((dp - dt) ** 2).sum(0, dtype=np.float64); r["pk"] = np.maximum(r["pk"], dp.max(0)); wp = dp > 0.1; r["wet_pred"] += wp.sum(0); r["wet_both"] += (wp & wt).sum(0)
        T = rd.T; shp = h.shape
        z = np.load(work / "sums_Exp6_absolute_base.npz")                    # the run without the hurricane: which cells are water in normal conditions
        dmin_all = np.min([np.load(work / f"sums_{r}.npz")["dmin"] for r in RUNS], 0); dmax_all = np.max([np.load(work / f"sums_{r}.npz")["dmax"] for r in RUNS], 0)
        out = {"lat": lat, "lon": lon, "peak_true": pk_true.reshape(shp), "wet_hours_true": wet_true.reshape(shp).astype(np.int16), "mean_true": (mean_true / T).astype(np.float32).reshape(shp),
               "dmin_all_runs": dmin_all.reshape(shp), "dmax_all_runs": dmax_all.reshape(shp), "dmax_no_storm": z["dmax"].reshape(shp), "hours": T}
        for k, r in res.items():
            out[f"rmse_{k}"] = np.sqrt(r["se"] / T).astype(np.float32).reshape(shp); out[f"peak_{k}"] = r["pk"].reshape(shp)
            out[f"wet_hours_pred_{k}"] = r["wet_pred"].reshape(shp).astype(np.int16); out[f"wet_hours_both_{k}"] = r["wet_both"].reshape(shp).astype(np.int16)
        np.savez(work / f"eval_{tag}.npz", **out)
        print(f"evaluated {tag}: {T} hours, {time.time() - t0:.0f} s -> {work / f'eval_{tag}.npz'}")


if __name__ == "__main__":
    main()
