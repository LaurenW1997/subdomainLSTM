"""Flood map, step 4: the mapping model driven by observed water levels (Hurricane Ida) instead of the model's own series.

The mapping model was fitted on the numerical model alone. In use, its inputs are observations (and forecasts) at the control
points. This script prepares the observed inputs of the hindcast period and checks the mapping at the gauges themselves:
  offset     per station, the median of (hindcast - observed) over the first --calm-hours hours (before the storm); it is
             added to the observations, which puts them on the level of the numerical model (datum and mean-level offset)
  left out   every control point in turn is left out and its water level is predicted from the observations of the others
             (the same ridge regression as the mapping model, on the series of the control points of the training runs),
             then compared with its own observations - and with the hindcast at the same hours
  check      stations that pass the control-point check but have no forecast in real time are never an input: the full
             mapping model (all control points, coefficients of mapping_fit.py) is evaluated at their cells
  missing    hours without an observation at a control point are filled with the expectation given the other control
             points (training covariance); the filled series is saved as input of `mapping_fit.py --observed-inputs`
Input : --ida DIR, --dataset DIR (hourly observations), --table config/operational_stations_grid_datum.csv, --fit DIR of mapping_fit.py,
        --checks CSV of control_points.py (all stations), --cache hindcast as float32 [T, lat, lon] (control_points.py)
Output: --out DIR: x_observed.npy [T, P] (water surface elevation minus xref, as mapping_fit.py uses it), stations.csv,
        series.npz (observed, mapped and hindcast series per station), summary.txt
Usage : python observed_inputs.py --ida DIR --dataset DIR --table FILE --fit DIR --checks FILE --cache FILE --out DIR
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import RUNS, grid  # noqa: E402

STORM = ("2021-08-28 12:00", "2021-08-31 12:00")          # three days around the landfall (29 August, about 17 UTC)


def cell_wse(wl, j, i, h, roms) -> np.ndarray:
    """Water surface elevation of one cell of the hindcast; gaps of the archive filled as mapping_fit.Reader does."""
    s = np.asarray(wl[:, j, i], np.float64)
    if roms[j, i]:
        s[np.isnan(s)] = -float(h[j, i]); return s                         # dry ocean-model cell: bed level
    s = pd.Series(s).ffill().fillna(0.0).to_numpy()                        # removed spike on land: the hour before
    return s - float(h[j, i])


def conditional(C, xm, lam, X, use, ct, mt) -> np.ndarray:
    """Expectation of targets (covariance with the control points ct [P, K], mean mt [K]) given the finite columns of X among `use`."""
    T = X.shape[0]; out = np.full((T, ct.shape[1]), np.nan); fin = np.isfinite(X) & use[None, :]
    pat, inv = np.unique(fin, axis=0, return_inverse=True); inv = np.asarray(inv).ravel()
    for k, A in enumerate(pat):
        if A.sum() < 5:
            continue
        w = np.linalg.solve(C[np.ix_(A, A)] + lam * np.eye(int(A.sum())), ct[A])
        rows = np.where(inv == k)[0]; out[rows] = mt[None, :] + (X[np.ix_(rows, np.where(A)[0])] - xm[A][None, :]) @ w
    return out


def metrics(o, p, m, storm) -> dict:
    ok = np.isfinite(o) & np.isfinite(p) & np.isfinite(m); r = {"hours": int(ok.sum())}
    if ok.sum() < 24:
        return r
    rm = lambda a, k: float(np.sqrt(((a[k] - o[k]) ** 2).mean())) if k.sum() >= 6 else np.nan
    r.update({"rmse_mapping_m": rm(p, ok), "rmse_hindcast_m": rm(m, ok), "storm_hours": int((ok & storm).sum()), "rmse_mapping_storm_m": rm(p, ok & storm), "rmse_hindcast_storm_m": rm(m, ok & storm),
              "peak_observed_m": float(o[ok].max()), "peak_mapping_m": float(p[ok].max()), "peak_hindcast_m": float(m[ok].max()),
              "observed_at_hindcast_peak": bool(np.isfinite(o[int(np.nanargmax(m))]))})
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--table", required=True); ap.add_argument("--fit", required=True)
    ap.add_argument("--checks", required=True); ap.add_argument("--cache", required=True); ap.add_argument("--out", required=True); ap.add_argument("--sums-dir", help="sums_<run>.npz and xref.npy, if not in --fit")
    ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--calm-hours", type=int, default=72); ap.add_argument("--noise", type=float, default=0.12); ap.add_argument("--min-r", type=float, default=0.8)
    a = ap.parse_args()
    ida, fit, out = Path(a.ida), Path(a.fit), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    h, roms, lat, lon = grid(ida); NX = h.shape[1]
    d = netCDF4.Dataset(ida / f"water_level_{a.holdout}.nc"); times = pd.DatetimeIndex(netCDF4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)); d.close()
    wl = np.load(a.cache, mmap_mode="r"); T = wl.shape[0]; assert T == len(times)
    storm = np.asarray((times >= STORM[0]) & (times <= STORM[1]))

    sd = Path(a.sums_dir) if a.sums_dir else fit
    c = pd.read_csv(fit / "controls_used.csv", dtype={"station_id": str}); P = len(c); xref = np.load(sd / "xref.npy")
    used = c.used.to_numpy(bool) if "used" in c.columns else np.ones(P, bool)
    al = pd.read_csv(a.checks, dtype={"station_id": str})
    ck = al[(al.obs_hours >= 200) & (al.best_r >= a.min_r) & ~al.station_id.isin(c.station_id)].sort_values("station_id").reset_index(drop=True)
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"]
    add = {(r.source, r.station_id): float(r.to_navd88_add_m) for r in tab.itertuples() if r.to_navd88_add_m != ""}
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy"))
    vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r"); row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    i0 = int(tm.get_indexer([times[0]])[0]); assert i0 >= 0 and tm[i0 + T - 1] == times[-1]

    def series(tb):
        """Observed (NAVD88 where the datum is known) and hindcast water surface elevation at the cells of a station table, and the offsets."""
        obs = np.stack([np.asarray(vals[row[(r.source, r.station_id)], i0:i0 + T], np.float64) + add.get((r.source, r.station_id), 0.0) for r in tb.itertuples()], 1)
        mod = np.stack([cell_wse(wl, int(r.best_j), int(r.best_i), h, roms) for r in tb.itertuples()], 1)
        dif = mod - obs; n_calm = np.isfinite(dif[:a.calm_hours]).sum(0)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore"); off = np.where(n_calm >= 24, np.nanmedian(dif[:a.calm_hours], 0), np.nanmedian(dif, 0))
        return obs + off[None, :], mod, off, n_calm

    obs, mod, off, n_calm = series(c)                         # control points, on the level of the numerical model
    X = obs - xref[None, :]

    n = 0; Sx = np.zeros(P); Sxx = np.zeros((P, P))           # covariance of the control-point series in the training runs
    for r in RUNS:
        if r != a.holdout:
            z = np.load(sd / f"sums_{r}.npz"); n += int(z["n"]); Sx += z["Sx"]; Sxx += z["Sxx"]
    xm = Sx / n; C = Sxx - n * np.outer(xm, xm); lam = n * a.noise ** 2

    recs = []; ser = {"times": np.array(times.strftime("%Y-%m-%d %H:%M"), dtype=str)}
    everyone = used.copy()
    for s in np.where(used)[0]:                               # every control point left out in turn
        use = everyone.copy(); use[s] = False
        p = conditional(C, xm, lam, X, use, C[:, [s]], xm[[s]])[:, 0] + xref[s]
        r = c.iloc[s]; sid = r.station_id
        recs.append({"group": "control point, left out", "source": r.source, "station_id": sid, "name": r["name"], "lat": r.lat, "lon": r.lon, "cell_model": r.best_model, "offset_m": off[s],
                     "offset_from": "hours before the storm" if n_calm[s] >= 24 else "whole period", "observed_hours": int(np.isfinite(obs[:, s]).sum()), **metrics(obs[:, s], p, mod[:, s], storm)})
        ser[f"obs_{sid}"] = obs[:, s].astype(np.float32); ser[f"map_{sid}"] = p.astype(np.float32); ser[f"mod_{sid}"] = mod[:, s].astype(np.float32)

    Xf = X.copy(); Xf[:, ~used] = xm[None, ~used]             # a control point without weight: any finite value
    X = X[:, :].copy(); X[:, ~used] = np.nan; miss = ~np.isfinite(Xf)     # missing hours: expectation given the other control points
    for s in np.where(miss.any(0))[0]:
        use = everyone.copy(); use[s] = False
        Xf[miss[:, s], s] = conditional(C, xm, lam, X[miss[:, s]], use, C[:, [s]], xm[[s]])[:, 0]
    assert np.isfinite(Xf).all(), "an hour with fewer than five control points reporting"
    np.save(out / "x_observed.npy", Xf)

    ck["group"] = "check station, never an input"
    if not used.all():                                        # control points of the sums that carry no weight: listed apart
        cu = c[~used].copy(); cu["group"] = "not used, the model does not reproduce the amplitude"; ck = pd.concat([ck, cu[ck.columns.intersection(cu.columns)]], ignore_index=True)
    if len(ck):                                               # stations that are never an input: the full mapping model at their cells
        o2, m2, off2, nc2 = series(ck); idx = (ck.best_j.astype(int) * NX + ck.best_i.astype(int)).to_numpy()
        B = np.load(fit / f"coef_without_{a.holdout}.npy", mmap_mode="r"); ym = np.load(fit / f"fitmeta_without_{a.holdout}.npz")["ym"]
        Bc = np.stack([np.asarray(B[:, k], np.float64) for k in idx], 1); y = (Xf - xm[None, :]) @ Bc + ym[idx][None, :].astype(np.float64)
        for k, r in enumerate(ck.itertuples()):
            j, i = int(r.best_j), int(r.best_i)
            p = y[:, k] if roms[j, i] else np.maximum(y[:, k], 0) - float(h[j, i])
            recs.append({"group": r.group, "source": r.source, "station_id": r.station_id, "name": r.name, "lat": r.lat, "lon": r.lon, "cell_model": r.best_model, "offset_m": off2[k],
                         "offset_from": "hours before the storm" if nc2[k] >= 24 else "whole period", "observed_hours": int(np.isfinite(o2[:, k]).sum()), **metrics(o2[:, k], p, m2[:, k], storm)})
            ser[f"obs_{r.station_id}"] = o2[:, k].astype(np.float32); ser[f"map_{r.station_id}"] = p.astype(np.float32); ser[f"mod_{r.station_id}"] = m2[:, k].astype(np.float32)

    t = pd.DataFrame(recs); t.to_csv(out / "stations.csv", index=False); np.savez_compressed(out / "series.npz", **ser)
    miss = miss[:, used]; off = off[used]; P = int(used.sum())
    lines = [f"{P} control points, {T} hours {times[0]} .. {times[-1]}; offsets from the first {a.calm_hours} hours: median {np.median(off):+.2f} m, from {off.min():+.2f} to {off.max():+.2f} m",
             f"observations missing: {int(miss.sum())} of {miss.size} station hours ({100 * miss.mean():.1f}%), {int(miss[storm].sum())} of them in the three days around the landfall; "
             f"control points with a gap in those three days: {int(miss[storm].any(0).sum())}; fewest control points reporting in one hour: {int((~miss).sum(1).min())}"]
    for g, x in t.groupby("group", sort=False):
        x = x.dropna(subset=["rmse_mapping_m"]); w = x.hours.to_numpy(); ws = x.storm_hours.to_numpy()
        pool = lambda col, wt: float(np.sqrt(np.nansum(wt * x[col].to_numpy() ** 2) / wt[np.isfinite(x[col].to_numpy())].sum()))
        lines.append(f"{g}: {len(x)} stations. RMSE against the observations, all hours pooled: mapping {pool('rmse_mapping_m', w):.3f} m, hindcast {pool('rmse_hindcast_m', w):.3f} m; "
                     f"three days around the landfall: mapping {pool('rmse_mapping_storm_m', ws):.3f} m, hindcast {pool('rmse_hindcast_storm_m', ws):.3f} m; "
                     f"median per station: mapping {x.rmse_mapping_m.median():.3f} m, hindcast {x.rmse_hindcast_m.median():.3f} m; "
                     f"error of the peak, mean and RMS over stations: mapping {(x.peak_mapping_m - x.peak_observed_m).mean():+.2f} / {np.sqrt(((x.peak_mapping_m - x.peak_observed_m) ** 2).mean()):.2f} m, "
                     f"hindcast {(x.peak_hindcast_m - x.peak_observed_m).mean():+.2f} / {np.sqrt(((x.peak_hindcast_m - x.peak_observed_m) ** 2).mean()):.2f} m; "
                     f"mapping closer than the hindcast at {int((x.rmse_mapping_m < x.rmse_hindcast_m).sum())} of {len(x)} stations")
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print("->", out)


if __name__ == "__main__":
    main()
