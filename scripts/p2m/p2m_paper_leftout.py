"""Flood map: the test of Bao et al. (2025) against observations - control points left out.

The paper leaves two control points out, computes their water level from the others with the mapping model and compares it
with the observations, beside the numerical model. Here every control point is left out in turn. A control point lies in
water, so its cell is a Type 1 location and gets Model-1 (linear regression on the whole series), from its --k nearest other
control points, as p2m_paper.py does for a cell.
    Ida        inputs = observed levels of the other control points; compared with the observations, beside the hindcast
    Francine   inputs = observed levels (lead 0) or forecasts issued 1 .. 6 h before, and the mean of the six (the paper's
               ensemble mean); compared with the observations, beside the direct forecast of the water-level model
Two trainings (hindcast of Ida only; the eleven other runs), each as in the paper (--noise 0) and with an assumed error of the inputs.
Input : --sums DIR (sums_<run>.npz with X, xref.npy, controls_used.csv), --ida-obs DIR of observed_inputs.py (x_observed.npy, series.npz),
        --francine DIR of forecast_map_check.py (inputs.npz, series.npz)
Output: --out DIR: stations.csv (one row per control point, training, regression, storm and input), summary.csv, series.npz
Usage : python p2m_paper_leftout.py --sums DIR --ida-obs DIR --francine DIR --out DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HIND = "Exp1_fully_coupled"
OTHERS = ["Exp2_no_wind", "Exp3_no_precipitation", "Exp4_river_only", "Exp5_Ida_base", "Exp6_absolute_base", "Exp7_wind_base", "Exp8_precipitation_base",
          "drought_river_storm", "drought_river_no_storm", "flood_river_storm", "flood_river_no_storm"]
TRAIN = {"hindcast of Ida only": [HIND], "eleven other runs": OTHERS}
IDA_STORM = ("2021-08-28 12:00", "2021-08-31 12:00")
KX, KY = np.cos(np.deg2rad(29.7)) * 111.2, 111.2


def rmse(e) -> float:
    e = e[np.isfinite(e)]
    return float(np.sqrt((e ** 2).mean())) if len(e) >= 12 else np.nan


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--sums", required=True); ap.add_argument("--ida-obs", required=True); ap.add_argument("--francine", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=8); ap.add_argument("--noise", type=float, default=0.12)
    a = ap.parse_args(); sums, out = Path(a.sums), Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "stations.csv").exists(), f"{out} has results already"
    c = pd.read_csv(sums / "controls_used.csv", dtype={"station_id": str}); used = c.used.to_numpy(bool); xref = np.load(sums / "xref.npy"); U = np.where(used)[0]
    lat, lon = c.lat.to_numpy(float), c.lon.to_numpy(float); Xr = {r: np.load(sums / f"sums_{r}.npz")["X"].astype(np.float64) for r in [HIND] + OTHERS}
    xi = np.load(Path(a.ida_obs) / "x_observed.npy").astype(np.float64); si = np.load(Path(a.ida_obs) / "series.npz"); ti = pd.DatetimeIndex(si["times"]); storm_i = np.asarray((ti >= IDA_STORM[0]) & (ti <= IDA_STORM[1]))
    fz = np.load(Path(a.francine) / "inputs.npz"); sf = np.load(Path(a.francine) / "series.npz"); tf = pd.DatetimeIndex(fz["times"]); storm_f = np.asarray(fz["storm"], bool); XL = {L: fz[f"lead{L}"].astype(np.float64) for L in range(7)}
    recs = []; ser = {"times_ida": si["times"], "times_francine": fz["times"]}
    for s in U:
        sid = c.station_id[s]; oth = U[U != s]; d2 = ((lon[oth] - lon[s]) * KX) ** 2 + ((lat[oth] - lat[s]) * KY) ** 2; cols = np.sort(oth[np.argsort(d2)[:a.k]]); far = float(np.sqrt(np.sort(d2)[a.k - 1]))
        oi = si[f"obs_{sid}"].astype(np.float64) - xref[s]; hi = Xr[HIND][:, s]                                     # Ida: observed and hindcast, on the level of the numerical model
        of_raw = sf[f"obs_{sid}"].astype(np.float64); of = np.where(np.isfinite(of_raw), XL[0][:, s], np.nan)        # Francine: observed, same level
        base = {"source": c.source[s], "station_id": sid, "name": c["name"][s], "lat": lat[s], "lon": lon[s], "farthest_input_km": far}
        ser[f"ida_obs_{sid}"] = (oi + xref[s]).astype(np.float32); ser[f"ida_hindcast_{sid}"] = (hi + xref[s]).astype(np.float32); ser[f"francine_obs_{sid}"] = (of + xref[s]).astype(np.float32)
        ok = np.isfinite(oi)
        recs.append({**base, "training": "", "regression": "", "storm": "Ida", "inputs": "numerical model (hindcast)", "hours": int(ok.sum()), "rmse_m": rmse(hi - oi), "rmse_storm_days_m": rmse((hi - oi)[storm_i]),
                     "peak_observed_m": float(np.nanmax(oi) + xref[s]), "peak_m": float(hi[ok].max() + xref[s])})
        for L in range(1, 7):                                                # the direct forecast of the water-level model at the control point itself
            f_ = sf[f"fc{L}_{sid}"].astype(np.float64) - of_raw
            recs.append({**base, "training": "", "regression": "", "storm": "Francine", "inputs": f"direct forecast {L} h before", "hours": int(np.isfinite(f_).sum()), "rmse_m": rmse(f_), "rmse_storm_days_m": rmse(f_[storm_f])})
        for tname, runs in TRAIN.items():
            X = np.concatenate([Xr[r] for r in runs]); A = np.concatenate([np.ones((len(X), 1)), X[:, cols]], 1); y = X[:, s]; q = A.shape[1]; D = np.eye(q); D[0, 0] = 0.0
            for rname, noise in (("as in the paper", 0.0), ("with an assumed error of the inputs", a.noise)):
                b = np.linalg.solve(A.T @ A + len(A) * noise ** 2 * D + 1e-9 * np.eye(q), A.T @ y); pr = lambda Xin: b[0] + Xin[:, cols] @ b[1:]
                tag = {"training": tname, "regression": rname, "sum_abs_weights": float(np.abs(b[1:]).sum())}

                def add(storm, inputs, p, o, st, key=None):
                    okk = np.isfinite(o) & np.isfinite(p)
                    recs.append({**base, **tag, "storm": storm, "inputs": inputs, "hours": int(okk.sum()), "rmse_m": rmse(p - o), "rmse_storm_days_m": rmse((p - o)[st]),
                                 "peak_observed_m": float(np.nanmax(o) + xref[s]) if okk.any() else np.nan, "peak_m": float(p[okk].max() + xref[s]) if okk.any() else np.nan})
                    if key:
                        ser[key] = (p + xref[s]).astype(np.float32)

                short = ("exp1" if runs == [HIND] else "11runs") + ("_paper" if noise == 0 else "_error")
                add("Ida", "observed levels of the other control points", pr(xi), oi, storm_i, f"ida_{short}_{sid}")
                P = {L: pr(XL[L]) for L in range(7)}
                add("Francine", "observed levels of the other control points", P[0], of, storm_f, f"francine_{short}_lead0_{sid}")
                for L in range(1, 7):
                    add("Francine", f"forecasts {L} h before", P[L], of, storm_f, f"francine_{short}_lead{L}_{sid}" if L in (1, 3, 6) else None)
                add("Francine", "mean of the forecasts 1 to 6 h before", np.mean([P[L] for L in range(1, 7)], 0), of, storm_f)
    t = pd.DataFrame(recs); t.to_csv(out / "stations.csv", index=False); np.savez_compressed(out / "series.npz", **ser)
    g = t.groupby(["storm", "inputs", "training", "regression"], sort=False)
    sm = g.agg(control_points=("rmse_m", "count"), rmse_median_m=("rmse_m", "median"), rmse_storm_days_median_m=("rmse_storm_days_m", "median"), rmse_worst_m=("rmse_m", "max"),
               sum_abs_weights_median=("sum_abs_weights", "median")).reset_index()
    pk = t.dropna(subset=["peak_m"]).assign(e=lambda x: x.peak_m - x.peak_observed_m).groupby(["storm", "inputs", "training", "regression"], sort=False).e.agg(peak_error_mean_m="mean", peak_error_rms_m=lambda e: float(np.sqrt((e ** 2).mean()))).reset_index()
    sm = sm.merge(pk, how="left", on=["storm", "inputs", "training", "regression"]); sm.to_csv(out / "summary.csv", index=False)
    # the paper's statement: the mapping against the numerical model, station by station (Ida)
    h = t[(t.storm == "Ida") & (t.inputs == "numerical model (hindcast)")].set_index("station_id").rmse_m; L = []
    for (tn, rn), x in t[(t.storm == "Ida") & (t.training != "")].groupby(["training", "regression"], sort=False):
        dlt = x.set_index("station_id").rmse_m - h; L.append(f"Ida, {tn}, {rn}: RMSE of the mapping minus RMSE of the hindcast, median {dlt.median():+.3f} m; mapping closer to the observations at {int((dlt < 0).sum())} of {len(dlt)} control points")
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 200); txt = sm.round(3).to_string(index=False) + chr(10) + chr(10).join(L)
    (out / "summary.txt").write_text(txt, encoding="utf-8"); print(txt); print("->", out)


if __name__ == "__main__":
    main()
