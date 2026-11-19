"""Flood map, step 8: is the water the map puts on the marsh real? Compared with the marsh gauges (CRMS).

The CIMS export gives, for every CRMS site and hour, the water level relative to the surveyed marsh surface next to the
gauge ("Adjusted Water Elevation to Marsh"). Positive = the marsh is under water, and by that much. This is an observation
of flood depth on land. It is compared, hour by hour, with the depth the maps give on the land cells next to the site:
  Francine (September 2024): mapping model from the observed water levels at the control points, and from forecasts issued 1, 3 and 6 h before
  Ida (August 2021):         numerical model (hindcast), and mapping model from the observed water levels
Land cells = cells that stay dry in the run without a hurricane; the site gets the land cells within --radius cells
(median depth over them; a site without such a cell is left out). CRMS sites are not inputs of any model here.
Input : --crms CSV (rows of the CIMS export for the two periods), --ida DIR, --fit DIR of mapping_fit.py, --inputs inputs.npz of forecast_map_check.py,
        --ida-inputs x_observed.npy of observed_inputs.py, --cache hindcast float32 [T, lat, lon]
Output: --out DIR: sites.csv (one row per site and period), hours.npz (series), summary.txt
Usage : python crms_marsh_check.py --crms FILE --ida DIR --fit DIR --inputs FILE --ida-inputs FILE --cache FILE --out DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid, training  # noqa: E402

FT = 0.3048
TZ = {"CST": 6, "CDT": 5, "UTC": 0, "GMT": 0}
C = {"Station ID": "station", "Date (mm/dd/yyyy)": "date", "Time (hh:mm:ss)": "time", "Time Zone": "tz", "Adjusted Water Elevation to Marsh (ft)": "to_marsh_ft",
     "Adjusted Water Elevation to Datum (ft)": "to_datum_ft", "Latitude": "lat", "Longitude": "lon"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crms", required=True); ap.add_argument("--ida", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--sums-dir"); ap.add_argument("--inputs", required=True)
    ap.add_argument("--ida-inputs", required=True); ap.add_argument("--cache", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--train-runs", nargs="+"); ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--radius", type=int, default=3); ap.add_argument("--west-limit", type=float, default=-92.5)
    ap.add_argument("--francine-calm-until", default="2024-09-09 00:00"); ap.add_argument("--ida-calm-hours", type=int, default=72); ap.add_argument("--wet", type=float, default=0.1, help="depth that counts as flooded (m)")
    a = ap.parse_args()
    fit, out = Path(a.fit), Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "summary.txt").exists(), f"{out} has results already"
    sd = Path(a.sums_dir) if a.sums_dir else fit
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape
    dry = np.load(sd / "sums_Exp6_absolute_base.npz")["dmax"].reshape(NY, NX) <= 0.1

    d = pd.read_csv(a.crms, usecols=list(C), dtype=str, encoding="latin-1", on_bad_lines="skip").rename(columns=C)
    d = d[d.station.str.startswith("CRMS")]
    t = pd.to_datetime(d.date + " " + d.time, format="%m/%d/%Y %H:%M:%S", errors="coerce") + pd.to_timedelta(d.tz.map(TZ).fillna(6).astype(int), unit="h")
    d = d.assign(t=t, to_marsh=pd.to_numeric(d.to_marsh_ft, errors="coerce") * FT, to_datum=pd.to_numeric(d.to_datum_ft, errors="coerce") * FT, lat=pd.to_numeric(d.lat, errors="coerce"), lon=pd.to_numeric(d.lon, errors="coerce"))
    d = d.dropna(subset=["t", "to_marsh"]); d = d[d.t.dt.minute == 0]
    print(f"CRMS rows with a water level relative to the marsh: {len(d)}, stations {d.station.nunique()}")

    # times of the two periods
    zi = np.load(a.inputs); tF = pd.DatetimeIndex(zi["times"]); XF = {"Francine, mapping from observed water levels": zi["lead0"], **{f"Francine, mapping from forecasts issued {L} h before": zi[f"lead{L}"] for L in (1, 3, 6)}}
    nc = netCDF4.Dataset(Path(a.ida) / f"water_level_{a.holdout}.nc"); tI = pd.DatetimeIndex(netCDF4.num2date(nc["time"][:], nc["time"].units, only_use_cftime_datetimes=False)); nc.close()
    XI = np.load(a.ida_inputs); wl = np.load(a.cache, mmap_mode="r"); assert len(XI) == len(tI) == wl.shape[0]
    _, name = training(a); B = np.load(fit / f"coef_{name}.npy", mmap_mode="r"); m_ = np.load(fit / f"fitmeta_{name}.npz"); xm, ym = m_["xm"], m_["ym"]
    calmF = np.asarray(tF < a.francine_calm_until); stormF = zi["storm"]; calmI = np.arange(len(tI)) < a.ida_calm_hours; stormI = np.asarray((tI >= "2021-08-28 12:00") & (tI <= "2021-08-31 12:00"))

    sites = d.groupby("station").agg(lat=("lat", "median"), lon=("lon", "median")).reset_index()
    R = a.radius; recs = []; ser = {"times_francine": np.array(tF.strftime("%Y-%m-%d %H:%M"), dtype=str), "times_ida": np.array(tI.strftime("%Y-%m-%d %H:%M"), dtype=str)}; n_out = n_noland = 0
    for s in sites.itertuples():
        if not (lat[0] <= s.lat <= lat[-1] and max(lon[0], a.west_limit) <= s.lon <= lon[-1]):
            n_out += 1; continue
        j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin())
        j0, j1, i0, i1 = max(0, j - R), min(NY, j + R + 1), max(0, i - R), min(NX, i + R + 1)
        jj, ii = np.mgrid[j0:j1, i0:i1]; ok = dry[j0:j1, i0:i1] & (np.hypot(jj - j, ii - i) <= R + 0.5)
        if not ok.any():
            n_noland += 1; continue
        cj, ci = jj[ok], ii[ok]; idx = cj * NX + ci; order = np.argsort(idx); idx, cj, ci = idx[order], cj[order], ci[order]
        b = np.asarray(B[:, idx], np.float64); c0 = ym[idx].astype(np.float64) + np.where(roms[cj, ci], h[cj, ci], 0)
        g = d[d.station == s.station].drop_duplicates("t").set_index("t")
        ground_crms = float((g.to_datum - g.to_marsh).median()) if g.to_datum.notna().any() else np.nan       # surveyed marsh surface, NAVD88
        fields = {k: (tF, np.median(np.maximum((X - xm[None, :]) @ b + c0[None, :], 0), 1), calmF, stormF) for k, X in XF.items()}
        fields["Ida, mapping from observed water levels"] = (tI, np.median(np.maximum((XI - xm[None, :]) @ b + c0[None, :], 0), 1), calmI, stormI)
        w = np.asarray(wl[:, cj.min():cj.max() + 1, ci.min():ci.max() + 1], np.float64)[:, cj - cj.min(), ci - ci.min()]
        w = np.where(roms[cj, ci][None, :], np.where(np.isnan(w), 0.0, w + h[cj, ci][None, :]), pd.DataFrame(w).ffill().fillna(0.0).to_numpy())      # depth, as mapping_fit.Reader
        fields["Ida, numerical model (hindcast)"] = (tI, np.median(np.maximum(w, 0), 1), calmI, stormI)
        for k, (tt, dep, calm, storm) in fields.items():
            o = g.to_marsh.reindex(tt).to_numpy(float); fin = np.isfinite(o)
            if fin.sum() < 48:
                continue
            od = np.maximum(o, 0); e = dep - od; ser[f"{k}|{s.station}"] = np.stack([o, dep]).astype(np.float32)
            rec = {"field": k, "station": s.station, "lat": s.lat, "lon": s.lon, "land_cells": int(len(idx)), "cell_model": "ROMS" if roms[cj, ci].mean() > 0.5 else "WRF-Hydro",
                   "ground_model_m": float(np.median(-h[cj, ci])), "marsh_surface_crms_navd88_m": ground_crms, "hours": int(fin.sum()),
                   "rmse_depth_m": float(np.sqrt(np.mean(e[fin] ** 2))), "bias_depth_m": float(e[fin].mean())}
            for nm, msk in (("calm", calm), ("storm", storm)):
                q = fin & msk
                if q.sum() >= 12:
                    rec.update({f"{nm}_hours": int(q.sum()), f"{nm}_observed_flooded_share": float((o[q] > a.wet).mean()), f"{nm}_map_flooded_share": float((dep[q] > a.wet).mean()),
                                f"{nm}_observed_largest_depth_m": float(od[q].max()), f"{nm}_map_largest_depth_m": float(dep[q].max()), f"{nm}_observed_mean_depth_m": float(od[q].mean()), f"{nm}_map_mean_depth_m": float(dep[q].mean()),
                                f"{nm}_observed_lowest_level_m": float(o[q].min())})
            recs.append(rec)
    t_ = pd.DataFrame(recs); t_.to_csv(out / "sites.csv", index=False); np.savez_compressed(out / "hours.npz", **ser)
    lines = [f"CRMS sites in the export: {len(sites)}; outside the grid or west of {-a.west_limit} W: {n_out}; without a land cell within {R} cells: {n_noland}; depth that counts as flooded: {a.wet} m"]
    for k, x in t_.groupby("field", sort=False):
        lines.append(""); lines.append(f"{k}: {len(x)} sites; depth on the marsh, all hours: RMSE median per site {x.rmse_depth_m.median():.2f} m, mean error median {x.bias_depth_m.median():+.2f} m")
        for nm in ("calm", "storm"):
            y = x.dropna(subset=[f"{nm}_map_largest_depth_m"])
            if y.empty:
                continue
            of, mf = y[f"{nm}_observed_largest_depth_m"] > a.wet, y[f"{nm}_map_largest_depth_m"] > a.wet; pe = y[f"{nm}_map_largest_depth_m"] - y[f"{nm}_observed_largest_depth_m"]
            lines.append(f"  {nm} hours, {len(y)} sites: share of site hours flooded, observed {np.average(y[f'{nm}_observed_flooded_share'], weights=y[f'{nm}_hours']):.2f}, map {np.average(y[f'{nm}_map_flooded_share'], weights=y[f'{nm}_hours']):.2f}; "
                         f"mean depth observed {np.average(y[f'{nm}_observed_mean_depth_m'], weights=y[f'{nm}_hours']):.2f} m, map {np.average(y[f'{nm}_map_mean_depth_m'], weights=y[f'{nm}_hours']):.2f} m; "
                         f"sites flooded at some hour: observed {int(of.sum())}, map {int(mf.sum())}, both {int((of & mf).sum())}, map only {int((mf & ~of).sum())}, observed only {int((of & ~mf).sum())}; "
                         f"largest depth, map minus observed: mean {pe.mean():+.2f} m, RMS {np.sqrt((pe ** 2).mean()):.2f} m, median observed {y[f'{nm}_observed_largest_depth_m'].median():.2f} m, median map {y[f'{nm}_map_largest_depth_m'].median():.2f} m")
    g1 = t_.drop_duplicates("station"); dz = g1.ground_model_m - g1.marsh_surface_crms_navd88_m
    lines += ["", f"ground level of the land cells in the grid minus the surveyed marsh surface (NAVD88), {int(dz.notna().sum())} sites: median {dz.median():+.2f} m, quartiles {dz.quantile(0.25):+.2f} / {dz.quantile(0.75):+.2f} m "
              f"(surveyed marsh surface: median {g1.marsh_surface_crms_navd88_m.median():+.2f} m; grid: median {g1.ground_model_m.median():+.2f} m)"]
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print("->", out)


if __name__ == "__main__":
    main()
