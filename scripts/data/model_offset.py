"""Second part of the datum offset: observed mean level (NAVD88) minus ROMS mean zeta at the station's wet cell,
over the same hours (ROMS forecast archive, first 24 h of each cycle, Jul-Nov 2026).

Inputs: config/operational_stations_grid_datum.csv, config/gridmap/zeta/<domain>_zeta.csv (from roms_zeta_at_stations.py),
        the hourly observation matrix (dataset values.npy / time.npy / stations.csv; path via --dataset).
Adds to config/operational_stations_grid_datum.csv:
  n_hours_matched, cell_dry_frac, model_bad_frac, model_zeta_mean_m, obs_mean_matched_navd88_m,
  offset_obs_minus_model_m (median), offset_obs_minus_model_mean_m, corr_obs_model, rmse_model_after_offset_cm
Dry hours (zeta <= -h + 0.1 m at the wet cell) and impossible values (|zeta| > 5 m, blown-up cycles) are excluded. Station cells that are land in ROMS keep NaN here.
Usage: python model_offset.py --dataset DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
DCRIT = 0.1
MIN_HOURS = 200
ZMAX = 5.0      # |zeta| above this is not sea level


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); a = ap.parse_args()
    d = Path(a.dataset)
    vals = np.load(d / "values.npy", mmap_mode="r"); t = pd.to_datetime(np.load(d / "time.npy")); st = pd.read_csv(d / "stations.csv", dtype={"station_id": str})
    row_of = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    g = pd.read_csv(REPO / "config" / "operational_stations_grid_datum.csv", dtype={"station_id": str})
    out = {}
    for dom in ["Louisiana100m", "Texas100m", "Galveston100m"]:
        f = REPO / "config" / "gridmap" / "zeta" / f"{dom}_zeta.csv"
        if not f.exists():
            continue
        z = pd.read_csv(f, dtype={"station_id": str}, parse_dates=["time_utc"])
        gd = g[g.domain == dom].set_index("station_id")
        for sid, zz in z.groupby("station_id"):
            r = gd.loc[sid]
            if not bool(r.cell_is_wet) and r.dist_wet_km > 1.0:        # station is land in ROMS and the nearest water is > 1 km away
                continue
            h = float(r.h_wet_m)
            zz = zz.drop_duplicates("time_utc").set_index("time_utc").sort_index()
            dry = zz.zeta_wet_m <= (-h + DCRIT)
            bad = zz.zeta_wet_m.abs() > ZMAX                             # blown-up or fill values (e.g. Texas100m cycle 20260415)
            zw = zz.zeta_wet_m.where(~dry & ~bad)
            k = row_of.get((r.source, sid))
            if k is None:
                continue
            obs = pd.Series(np.asarray(vals[k]), index=t).reindex(zw.index)
            add = r.to_navd88_add_m
            if pd.isna(add):
                continue
            both = pd.DataFrame({"m": zw, "o": obs + add}).dropna()
            if len(both) < MIN_HOURS:
                continue
            out[(sid, dom)] = {"n_hours_matched": len(both), "cell_dry_frac": round(float(dry.mean()), 3), "model_bad_frac": round(float(bad.mean()), 3),
                               "model_zeta_mean_m": round(float(both.m.mean()), 3), "obs_mean_matched_navd88_m": round(float(both.o.mean()), 3),
                               "offset_obs_minus_model_m": round(float((both.o - both.m).median()), 3),   # median: robust to odd cycles
                               "offset_obs_minus_model_mean_m": round(float((both.o - both.m).mean()), 3),
                               "corr_obs_model": round(float(np.corrcoef(both.o, both.m)[0, 1]), 3),
                               "rmse_model_after_offset_cm": round(float(100 * np.sqrt(((both.o - both.m) - (both.o - both.m).median()) ** 2).mean()), 1)}
    res = pd.DataFrame.from_dict(out, orient="index")
    res.index = pd.MultiIndex.from_tuples(res.index, names=["station_id", "domain"])
    res = res.reset_index()
    for c in res.columns[2:]:
        if c in g.columns:
            g = g.drop(columns=c)
    g = g.merge(res, on=["station_id", "domain"], how="left")
    g.to_csv(REPO / "config" / "operational_stations_grid_datum.csv", index=False)
    done = g.dropna(subset=["offset_obs_minus_model_m"])
    print(f"{len(done)} (station, domain) rows with a model offset; by domain:")
    print(done.groupby("domain").agg(n=("station_id", "count"), offset_median=("offset_obs_minus_model_m", "median"), offset_p10=("offset_obs_minus_model_m", lambda s: s.quantile(.1)),
                                     offset_p90=("offset_obs_minus_model_m", lambda s: s.quantile(.9)), corr_median=("corr_obs_model", "median")).round(3))
    print(done[done.source == "NOAA_COOPS"][["station_id", "name", "domain", "n_hours_matched", "model_zeta_mean_m", "obs_mean_matched_navd88_m", "offset_obs_minus_model_m", "corr_obs_model"]].sort_values("domain").to_string(index=False))


if __name__ == "__main__":
    main()
