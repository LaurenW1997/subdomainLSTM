"""Flood map, diagnosis: is the flooding the mapping model shows in the river valleys of the north carried over from the training runs?

The map made for Hurricane Francine shows flooded valleys north of the lakes that look like those of Hurricane Ida. Three checks,
on land (cells dry throughout the run without a hurricane) east of --west-limit, north and south of --north-lat:
  runs      flooded land per training run: which runs flood the valleys (with or without rainfall, with or without the storm)
  calm      the mapping model fed with the observed water levels of Francine: flooded land in the calm hours before the storm,
            at the peak, and with every input at its training mean (the constant term alone)
  observed  the range of the observed water level at the gauges of the north in the Ida period and in the Francine period
Input : --ida DIR, --fit DIR of mapping_fit.py, --inputs inputs.npz of forecast_map_check.py, --ida-eval eval_<run>.npz of mapping_fit.py (hindcast),
        --ida-eval-observed eval_<run>.npz (mapping from observed levels, Ida), --cells CSV of control_cells.py, --fc NPZ of forecast_inputs.py, --dataset DIR
Output: --out DIR: runs.csv, mapping.csv, gauges.csv, summary.txt
Usage : python valley_check.py --ida DIR --fit DIR --inputs FILE --ida-eval FILE --ida-eval-observed FILE --cells FILE --fc FILE --dataset DIR --out DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import RUNS, grid, training  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--sums-dir"); ap.add_argument("--inputs", required=True); ap.add_argument("--ida-eval", required=True)
    ap.add_argument("--ida-eval-observed", required=True); ap.add_argument("--cells", required=True); ap.add_argument("--fc", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--train-runs", nargs="+"); ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--north-lat", type=float, default=30.5); ap.add_argument("--west-limit", type=float, default=-92.5)
    ap.add_argument("--calm-until", default="2024-09-09 00:00")
    a = ap.parse_args()
    fit, out = Path(a.fit), Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "summary.txt").exists(), f"{out} has results already"
    sd = Path(a.sums_dir) if a.sums_dir else fit
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; N = h.size
    dry = np.load(sd / "sums_Exp6_absolute_base.npz")["dmax"].reshape(NY, NX) <= 0.1
    east = np.broadcast_to(lon[None, :] >= a.west_limit, (NY, NX)); north = np.broadcast_to(lat[:, None] >= a.north_lat, (NY, NX))
    reg = {"north of %.1f N" % a.north_lat: dry & east & north, "south of %.1f N" % a.north_lat: dry & east & ~north}
    lines = [f"land = dry throughout the run without a hurricane, east of {-a.west_limit} W; " + "; ".join(f"{k}: {int(m.sum()) / 100:.0f} km2" for k, m in reg.items())]
    area = lambda f, m, thr: float((f[m] > thr).sum()) / 100

    rows = []                                                              # 1. which runs flood the valleys
    for r in RUNS:
        dm = np.load(sd / f"sums_{r}.npz")["dmax"].reshape(NY, NX)
        rows.append({"run": r, **{f"{k}, above {t} m (km2)": area(dm, m, t) for k, m in reg.items() for t in (0.1, 0.3, 1.0)}})
    t1 = pd.DataFrame(rows); t1.to_csv(out / "runs.csv", index=False); pd.set_option("display.width", 250)
    lines += ["", "flooded land per run (largest depth of the run):", t1.round(0).to_string(index=False)]

    _, name = training(a); B = np.load(fit / f"coef_{name}.npy"); m_ = np.load(fit / f"fitmeta_{name}.npz"); xm, ym = m_["xm"], m_["ym"]      # 2. the mapping model
    add = np.where(roms, h, 0).astype(np.float32).ravel()
    z = np.load(a.inputs); tv = pd.DatetimeIndex(z["times"]); X = z["lead0"]; storm = z["storm"]; calm = np.asarray(tv < a.calm_until)

    def peak(xs):
        p = np.zeros(N, np.float32); xs = (xs - xm[None, :]).astype(np.float32)
        for k in range(0, len(xs), 24):
            p = np.maximum(p, np.maximum(xs[k:k + 24] @ B + ym[None, :] + add[None, :], 0).max(0))
        return p.reshape(NY, NX)

    def lowest(xs):
        p = np.full(N, np.inf, np.float32); xs = (xs - xm[None, :]).astype(np.float32)
        for k in range(0, len(xs), 24):
            p = np.minimum(p, np.maximum(xs[k:k + 24] @ B + ym[None, :] + add[None, :], 0).min(0))
        return p.reshape(NY, NX)

    f = {"Ida: numerical model (hindcast), peak": np.load(a.ida_eval)["peak_true"], "Ida: mapping from observed levels, peak": np.load(a.ida_eval_observed)["peak_observed"],
         "Francine: mapping from observed levels, peak of 10 to 13 September": peak(X[storm]),
         f"Francine: mapping from observed levels, largest depth in the {int(calm.sum())} calm hours before": peak(X[calm]),
         "Francine: mapping from observed levels, smallest depth of the ten days": lowest(X),
         "every input at its training mean (the constant term alone)": peak(xm[None, :])}
    rows = [{"field": k, **{f"{rk}, above {t} m (km2)": area(v, m, t) for rk, m in reg.items() for t in (0.1, 0.3, 1.0)}} for k, v in f.items()]
    t2 = pd.DataFrame(rows); t2.to_csv(out / "mapping.csv", index=False); lines += ["", "flooded land in the maps:", t2.round(0).to_string(index=False)]
    pkF, clF = f["Francine: mapping from observed levels, peak of 10 to 13 September"], list(f.values())[3]
    for rk, m in reg.items():                                             # how much of the peak is there before the storm
        w = m & (pkF > 0.3)
        lines.append(f"{rk}: of the land above 0.3 m at the peak of Francine, {100 * float((clF[w] > 0.3).mean()):.0f}% is above 0.3 m in the calm hours already; "
                     f"mean depth there {float(pkF[w].mean()):.2f} m at the peak, {float(clF[w].mean()):.2f} m in the calm hours")
    pI = f["Ida: mapping from observed levels, peak"]
    for rk, m in reg.items():
        w = m & ((pkF > 0.3) | (pI > 0.3)); both = m & (pkF > 0.3) & (pI > 0.3)
        lines.append(f"{rk}: land above 0.3 m in the map of Francine and in the map of Ida (both from observed levels): overlap {float(both.sum()) / float(w.sum()):.2f}; "
                     f"correlation of the two peak depths over that land {float(np.corrcoef(pkF[w], pI[w])[0, 1]):.2f}")

    c = pd.read_csv(a.cells, dtype={"station_id": str}); c = c[(c.lat >= a.north_lat) & (c.lon >= a.west_limit)]      # 3. what the gauges of the north saw
    zf = np.load(a.fc); col = {(s, i): k for k, (s, i) in enumerate(zip(zf["source"], zf["station_id"]))}; OF = zf["observed"]
    d = netCDF4.Dataset(Path(a.ida) / f"water_level_{a.holdout}.nc"); ti = pd.DatetimeIndex(netCDF4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)); d.close()
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy"))
    vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r"); row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; i0 = int(tm.get_indexer([ti[0]])[0])
    rows = []
    for r in c.itertuples():
        key = (r.source, r.station_id)
        if key not in col or key not in row:
            continue
        oi = np.asarray(vals[row[key], i0:i0 + len(ti)], np.float64); of = OF[:, col[key]].astype(np.float64)
        if np.isfinite(oi).sum() < 100 or np.isfinite(of).sum() < 100:
            continue
        rows.append({"source": r.source, "station_id": r.station_id, "name": r.name, "lat": r.lat, "lon": r.lon, "rise_ida_m": float(np.nanmax(oi) - np.nanmin(oi)), "rise_francine_m": float(np.nanmax(of) - np.nanmin(of))})
    t3 = pd.DataFrame(rows).sort_values("rise_ida_m", ascending=False); t3.to_csv(out / "gauges.csv", index=False)
    lines += ["", f"gauges north of {a.north_lat} N with observations in both periods: {len(t3)}; range of the observed level (highest minus lowest), median: Ida {t3.rise_ida_m.median():.2f} m, Francine {t3.rise_francine_m.median():.2f} m; "
              f"Francine below half of Ida at {int((t3.rise_francine_m < 0.5 * t3.rise_ida_m).sum())} gauges", t3.round(2).to_string(index=False)]
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print("->", out)


if __name__ == "__main__":
    main()
