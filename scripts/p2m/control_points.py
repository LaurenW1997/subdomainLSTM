"""Flood map, step 1: which gauges can serve as control points of the mapping model (after Bao et al. 2025, npj Nat. Hazards).

A control point needs two things: observations in real time (the stations the LSTM forecasts) and a cell of the numerical
model whose water level behaves like the gauge. For every station with real-time data inside the Louisiana 100 m grid this
script takes the hindcast of Hurricane Ida (Exp1, hourly, 25 August to 5 September 2021), turns it into water surface
elevation, and compares the model series with the observed one at the gauge:
  at the cell of the station, and at the cell within --radius cells that correlates best with the observations
  (a gauge on a channel narrower than 100 m usually lies on a cell that the model treats as land).
water_level of the archive: ocean-model cells = free surface (NAVD88); land-model cells = depth above the ground, so the
water surface elevation there is water_level - h (h positive down).
Input : --ida DIR with grid_lower_mississippi_100m.nc and water_level_Exp1_fully_coupled.nc; --dataset (hourly observations);
        --table config/operational_stations_grid_datum.csv
Output: --out control_points_check.csv, one row per station; a cache of the hindcast as float32 (--cache) for the next steps
Usage : python control_points.py --ida DIR --dataset DIR --table FILE --out FILE [--radius 5]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd


def load_run(f: Path, cache: Path | None) -> tuple[np.ndarray, np.ndarray]:
    """water_level [T, lat, lon] float32 with NaN where missing, and the times."""
    d = netCDF4.Dataset(f); v = d["water_level"]; t = netCDF4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    times = pd.DatetimeIndex(t)
    if cache is not None and cache.exists():
        d.close(); return np.load(cache, mmap_mode="r"), times
    out = np.empty(v.shape, np.float32)
    for k in range(v.shape[0]):
        out[k] = np.ma.filled(v[k], np.nan)
    d.close()
    if cache is not None:
        np.save(cache, out)
    return out, times


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--table", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--run", default="Exp1_fully_coupled"); ap.add_argument("--radius", type=int, default=5); ap.add_argument("--cache")
    a = ap.parse_args()
    ida = Path(a.ida)
    g = netCDF4.Dataset(ida / "grid_lower_mississippi_100m.nc")
    h = np.asarray(np.ma.filled(g["h"][:], np.nan), np.float32); roms = np.asarray(g["domain_mask"][:]) == 1; g.close()
    wl, times = load_run(ida / f"water_level_{a.run}.nc", Path(a.cache) if a.cache else None)
    T, NY, NX = wl.shape
    print(f"{a.run}: {T} hours {times[0]} .. {times[-1]}, grid {NY} x {NX}")

    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"].copy()
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str})
    tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy"))
    vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    i0 = int(tm.get_indexer([times[0]])[0]); assert i0 >= 0 and tm[i0 + T - 1] == times[-1], "the dataset does not cover the run"

    def wse(j, i):                                   # water surface elevation series of cell (j, i)
        x = np.asarray(wl[:, j, i], np.float64)
        return x if roms[j, i] else x - float(h[j, i])

    def score(obs, mod):
        ok = np.isfinite(obs) & np.isfinite(mod)
        if ok.sum() < 48 or np.std(mod[ok]) < 1e-4 or np.std(obs[ok]) < 1e-4:
            return np.nan, np.nan, np.nan, np.nan, int(ok.sum())
        o, m = obs[ok], mod[ok]
        r = float(np.corrcoef(o, m)[0, 1]); bias = float((m - o).mean())
        return r, bias, float(np.sqrt(((m - bias - o) ** 2).mean())), float(np.std(m) / np.std(o)), int(ok.sum())

    recs = []
    for r in tab.itertuples():
        key = (r.source, r.station_id)
        if key not in row:
            continue
        obs = np.asarray(vals[row[key], i0:i0 + T], np.float64)
        add = float(r.to_navd88_add_m) if r.to_navd88_add_m != "" else np.nan
        obs_n = obs + (add if np.isfinite(add) else 0.0)
        j, i = int(r.j_eta), int(r.i_xi)
        own = score(obs_n, wse(j, i))
        best = (-2.0, j, i, None)
        R = a.radius
        for jj in range(max(0, j - R), min(NY, j + R + 1)):
            for ii in range(max(0, i - R), min(NX, i + R + 1)):
                sc = score(obs_n, wse(jj, ii))
                if np.isfinite(sc[0]) and sc[0] > best[0]:
                    best = (sc[0], jj, ii, sc)
        rec = {"source": r.source, "station_id": r.station_id, "name": r.name, "lat": r.lat, "lon": r.lon, "station_datum": r.station_datum, "datum_known": bool(np.isfinite(add)),
               "obs_hours": int(np.isfinite(obs).sum()), "obs_range_m": float(np.nanmax(obs) - np.nanmin(obs)) if np.isfinite(obs).any() else np.nan,
               "j": j, "i": i, "own_model": "ROMS" if roms[j, i] else "WRF-Hydro", "own_h_m": float(h[j, i]),
               "own_r": own[0], "own_bias_m": own[1], "own_rmse_unbiased_m": own[2], "own_std_ratio": own[3]}
        if best[3] is not None:
            sc = best[3]; jj, ii = best[1], best[2]
            rec.update({"best_j": jj, "best_i": ii, "best_dist_cells": float(np.hypot(jj - j, ii - i)), "best_model": "ROMS" if roms[jj, ii] else "WRF-Hydro", "best_h_m": float(h[jj, ii]),
                        "best_r": sc[0], "best_bias_m": sc[1], "best_rmse_unbiased_m": sc[2], "best_std_ratio": sc[3], "n_hours": sc[4]})
        recs.append(rec)
    out = pd.DataFrame(recs); out.to_csv(a.out, index=False)
    ok = out[out.obs_hours >= 200]
    print(f"stations in the grid with a row in the dataset: {len(out)}; with at least 200 observed hours in the run: {len(ok)}")
    for thr in (0.9, 0.8, 0.6):
        print(f"  correlation at least {thr}: own cell {int((ok.own_r >= thr).sum())}, best cell within {a.radius} cells {int((ok.best_r >= thr).sum())}")
    print("->", a.out)


if __name__ == "__main__":
    main()
