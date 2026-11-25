"""Francine case: the run against the observed water level at the gauges, the way the Ida hindcast was compared (control_points.py).

Same stations and the same model cell per station as in the comparison of the Ida hindcast (control_cells.csv: the cell chosen
for the gauge, always under water, away from the edge and from the line where the two models meet). Water surface elevation of
the run at a cell: ocean-model cell = free surface, missing when the cell is dry (zeta + h <= 0.25 m); land-model cell =
depth of surface water minus h of the Ida grid (h positive down), as in the Ida archive. Observations: hourly dataset, moved to
NAVD88 where the datum of the station is known.
Scores per station (model minus observed): correlation, mean difference, RMSE after taking the mean difference out, ratio of the
standard deviations; for
    storm   2024-09-07 00:00 .. 09-18 00:00  (265 hours placed around the landfall as the 265 hours of the Ida hindcast, 25 Aug .. 5 Sep 2021)
    calm    2024-08-20 00:00 .. 09-07 00:00  (after the first six days of the cold start)
and, for the storm, the highest level above the mean of the calm weeks, observed and modelled.
Input : --run NPZ of run_at_gauges.py, --cells control_cells.csv, --used controls_used_30_points.csv, --dataset DIR, --table config/operational_stations_grid_datum.csv
Output: --out PREFIX: _stations.csv (one row per station, the scores of the Ida hindcast beside those of Francine), _summary.csv, _series.npz
Usage : python run_score.py --run FILE --cells FILE --used FILE --dataset DIR --table FILE --out deliverables/35_floodmap/francine_run_at_gauges
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DRY = 0.25
STORM = ("2024-09-07 00:00", "2024-09-18 00:00"); CALM = ("2024-08-20 00:00", "2024-09-07 00:00")


def score(o, m):
    ok = np.isfinite(o) & np.isfinite(m)
    if ok.sum() < 48 or np.std(m[ok]) < 1e-4 or np.std(o[ok]) < 1e-4:
        return np.nan, np.nan, np.nan, np.nan, int(ok.sum())
    o, m = o[ok], m[ok]; b = float((m - o).mean())
    return float(np.corrcoef(o, m)[0, 1]), b, float(np.sqrt(((m - b - o) ** 2).mean())), float(np.std(m) / np.std(o)), int(ok.sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("run", "cells", "used", "dataset", "table", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    z = np.load(a.run, allow_pickle=True); t = pd.to_datetime(np.round(z["time"]).astype("int64") * 3600, unit="s"); T = len(t); assert (np.diff(z["time"]) == 1).all(), "the hours of the run are not consecutive"
    c = pd.read_csv(a.cells, dtype={"station_id": str}).set_index(["source", "station_id"]); used = pd.read_csv(a.used, dtype={"station_id": str}); used = set(zip(used.source[used.used], used.station_id[used.used]))
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"].set_index(["source", "station_id"])
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; i0 = int(tm.get_indexer([t[0]])[0]); assert i0 >= 0 and tm[i0 + T - 1] == t[-1], "the dataset does not cover the run"
    ws = np.asarray((t >= STORM[0]) & (t <= STORM[1])); wc = np.asarray((t >= CALM[0]) & (t < CALM[1])); print(f"run: {T} hours {t[0]} .. {t[-1]}; storm window {int(ws.sum())} hours, calm window {int(wc.sum())} hours")
    recs = []; OBS = []; MOD = []
    for s, key in enumerate(zip(z["source"], z["station_id"])):
        key = (str(key[0]), str(key[1])); r = c.loc[key]; ocean = int(z["mask_ocean"][s]) == 1
        if ocean:
            m = z["zeta"][:, s].astype("f8"); m[~(m + float(z["h_ocean"][s]) > DRY)] = np.nan
        else:
            m = z["depth"][:, s].astype("f8") - float(r.best_h_m)
        add = tab.loc[key].to_navd88_add_m if key in tab.index else ""; add = float(add) if add != "" else np.nan
        o = np.asarray(vals[row[key], i0:i0 + T], "f8") + (add if np.isfinite(add) else 0.0) if key in row else np.full(T, np.nan)
        S_, C_ = score(o[ws], m[ws]), score(o[wc], m[wc]); okc = wc & np.isfinite(o) & np.isfinite(m); oks = ws & np.isfinite(o) & np.isfinite(m)
        rise_o = rise_m = np.nan; when_o = when_m = ""
        if okc.sum() >= 240 and oks.sum() >= 200:
            ko = int(np.nanargmax(np.where(oks, o, np.nan))); km = int(np.nanargmax(np.where(oks, m, np.nan))); rise_o = float(o[ko] - o[okc].mean()); rise_m = float(m[km] - m[okc].mean()); when_o, when_m = f"{t[ko]:%m-%d %H:%M}", f"{t[km]:%m-%d %H:%M}"
        recs.append({"source": key[0], "station_id": key[1], "name": r["name"], "lat": r.lat, "lon": r.lon, "j": int(z["j"][s]), "i": int(z["i"][s]), "cell_model": "ROMS" if ocean else "WRF-Hydro", "cell_model_in_ida_table": r.best_model,
                     "control_point": key in used, "datum_known": bool(np.isfinite(add)), "model_hours_dry_or_missing": int((~np.isfinite(m)).sum()),
                     "ida_r": r.best_r, "ida_mean_difference_m": r.best_bias_m, "ida_rmse_mean_difference_removed_m": r.best_rmse_unbiased_m, "ida_std_ratio": r.best_std_ratio,
                     "francine_storm_r": S_[0], "francine_storm_mean_difference_m": S_[1], "francine_storm_rmse_mean_difference_removed_m": S_[2], "francine_storm_std_ratio": S_[3], "francine_storm_hours": S_[4],
                     "francine_calm_r": C_[0], "francine_calm_mean_difference_m": C_[1], "francine_calm_rmse_mean_difference_removed_m": C_[2], "francine_calm_std_ratio": C_[3], "francine_calm_hours": C_[4],
                     "francine_highest_above_calm_mean_observed_m": rise_o, "francine_highest_above_calm_mean_model_m": rise_m, "francine_time_of_highest_observed": when_o, "francine_time_of_highest_model": when_m})
        OBS.append(o.astype("f4")); MOD.append(m.astype("f4"))
    d = pd.DataFrame(recs); d.to_csv(a.out + "_stations.csv", index=False)
    np.savez_compressed(a.out + "_series.npz", time=np.asarray(t.strftime("%Y-%m-%d %H:%M")), observed=np.array(OBS).T, model=np.array(MOD).T, source=d.source.to_numpy(str), station_id=d.station_id.to_numpy(str), name=d.name.to_numpy(str))
    print(f"stations: {len(d)}; cell model agrees with the Ida table at {int((d.cell_model == d.cell_model_in_ida_table).sum())}")
    both = d[(d.francine_storm_hours >= 200) & d.ida_r.notna() & d.francine_storm_r.notna()]; rows = []
    groups = {"all stations scored in both storms": both, "ocean-model cells": both[both.cell_model == "ROMS"], "land-model cells": both[both.cell_model == "WRF-Hydro"], "the 30 control points": both[both.control_point],
              "stations with correlation at least 0.8 in the Ida hindcast": both[both.ida_r >= 0.8]}
    for name, g in groups.items():
        k = g[g.datum_known]
        rows.append({"group": name, "stations": len(g),
                     "ida_correlation_median": g.ida_r.median(), "francine_storm_correlation_median": g.francine_storm_r.median(), "francine_calm_correlation_median": g.francine_calm_r.median(),
                     "ida_stations_correlation_at_least_0.8": int((g.ida_r >= 0.8).sum()), "francine_storm_stations_correlation_at_least_0.8": int((g.francine_storm_r >= 0.8).sum()),
                     "ida_rmse_median_m": g.ida_rmse_mean_difference_removed_m.median(), "francine_storm_rmse_median_m": g.francine_storm_rmse_mean_difference_removed_m.median(), "francine_calm_rmse_median_m": g.francine_calm_rmse_mean_difference_removed_m.median(),
                     "ida_std_ratio_median": g.ida_std_ratio.median(), "francine_storm_std_ratio_median": g.francine_storm_std_ratio.median(), "francine_calm_std_ratio_median": g.francine_calm_std_ratio.median(),
                     "stations_with_known_datum": len(k), "ida_mean_difference_median_m": k.ida_mean_difference_m.median(), "francine_storm_mean_difference_median_m": k.francine_storm_mean_difference_m.median(), "francine_calm_mean_difference_median_m": k.francine_calm_mean_difference_m.median(),
                     "francine_highest_above_calm_mean_observed_median_m": g.francine_highest_above_calm_mean_observed_m.median(), "francine_highest_above_calm_mean_model_median_m": g.francine_highest_above_calm_mean_model_m.median()})
    s = pd.DataFrame(rows); s.to_csv(a.out + "_summary.csv", index=False); pd.set_option("display.width", 250)
    print(s.set_index("group").T.round(3).to_string()); print("->", a.out + "_stations.csv, _summary.csv, _series.npz")


if __name__ == "__main__":
    main()
