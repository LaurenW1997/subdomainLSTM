"""Flood map in Hurricane Francine: the numerical model itself against the marsh gauges (CRMS), beside the flood map.

The depth of the Francine hindcast at the land cells around every marsh gauge (p2m_paper_hindcast_at_sites.py: the same cells,
taken the same way, as the mapping model is scored on) is scored against the observed depth on the marsh exactly as the flood
map is (p2m_paper_crms.py). It tells how close a perfect mapping model could come: the mapping model learns the numerical model.
Beside it, on the same gauges: the mapping model fed the water levels of that run itself (one file per training), and the flood
map of one training from observed water levels and from the forecast issued 6 h before.
Input : --run-at-sites NPZ (p2m_paper_hindcast_at_sites.py; first hour --start), --levels levels.npz of marsh_obs_variants.py,
        --crms CSV of p2m_paper_crms.py for the training to set beside it, --own NPZ ... --own-names NAME ... (sites_<tag>.npz of
        `p2m_paper.py apply` with the control-point series of the run itself, same hours as the run)
Output: --out CSV (one row per gauge and field) and <out stem>_summary.csv (west and east of 90.8 W; quiet days and storm days)
Usage : python p2m_run_at_marsh_gauges_score.py --run-at-sites FILE --levels FILE --crms FILE --out FILE
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from marsh_obs_fit import FR_CALM, FR_STORM, metrics

SPLIT = -90.8


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--run-at-sites", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--crms", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--own", nargs="*", default=[]); ap.add_argument("--own-names", nargs="*", default=[]); ap.add_argument("--start", default="2024-09-06 22:00"); ap.add_argument("--wet", type=float, default=0.1); a = ap.parse_args()
    z = np.load(a.levels); site = list(z["site"]); lat, lon = z["lat"], z["lon"]; tF = pd.DatetimeIndex(z["times_francine"]); om, od = z["observed_to_marsh_francine"], z["observed_level_francine"]
    calm = np.asarray(tF < FR_CALM); storm = np.asarray((tF >= FR_STORM[0]) & (tF < FR_STORM[1]))
    r = np.load(a.run_at_sites); tr = pd.date_range(a.start, periods=r["depth_cells_with_a_model"].shape[0], freq="h"); pos = tr.get_indexer(tF); recs = []
    for k, name in enumerate(r["station"]):
        if name not in site:
            continue
        s = site.index(name); d = r["depth_cells_with_a_model"][:, k]; dep = np.where(pos >= 0, d[np.maximum(pos, 0)], np.nan).astype(np.float64)
        m = metrics("numerical model (Francine hindcast)", pd.Series({"station_id": name, "lat": lat[s], "lon": lon[s]}), om[:, s], dep, od[:, s], np.full(len(tF), np.nan), calm, storm, a.wet)
        if m:
            recs.append(m)
        for f, nm in zip(a.own, a.own_names):
            w = np.load(f)
            if name in w.files:
                dep = np.where(pos >= 0, w[name][np.maximum(pos, 0)], np.nan).astype(np.float64); m = metrics("mapping model fed the water levels of the Francine hindcast, trained on " + nm, pd.Series({"station_id": name, "lat": lat[s], "lon": lon[s]}), om[:, s], dep, od[:, s], np.full(len(tF), np.nan), calm, storm, a.wet)
                if m:
                    recs.append(m)
    x = pd.DataFrame(recs).dropna(subset=["storm_map_largest_depth_m", "storm_observed_largest_depth_m"]); c = pd.read_csv(a.crms); keep = {"Francine, inputs observed": "flood map from observed water levels", "Francine, inputs forecast 6 h before": "flood map from the forecast issued 6 h before"}
    c = c[c.field.isin(keep)].dropna(subset=["storm_map_largest_depth_m", "storm_observed_largest_depth_m"]); c = c.assign(field=c.field.map(keep)); both = set.intersection(*[set(g.station) for _, g in x.groupby('field')]) & set.intersection(*[set(c[c.field == f].station) for f in keep.values()])
    al = pd.concat([x, c]); al = al[al.station.isin(both)]; al.to_csv(a.out, index=False); rows = []
    for f, g in al.groupby("field", sort=False):
        for nm, w in (("all", np.ones(len(g), bool)), ("west of 90.8W", (g.lon < SPLIT).to_numpy()), ("east of 90.8W", (g.lon >= SPLIT).to_numpy())):
            y = g[w]; e = y.storm_map_largest_depth_m - y.storm_observed_largest_depth_m
            rows.append({"field": f, "gauges": nm, "n": len(y), "depth_hour_by_hour_rmse_median_per_gauge_m": y.rmse_depth_m.median(),
                         "quiet_days_mean_depth_observed_m": y.calm_observed_mean_depth_m.median(), "quiet_days_mean_depth_m": y.calm_map_mean_depth_m.median(), "quiet_days_flooded_share_observed": y.calm_observed_flooded_share.mean(), "quiet_days_flooded_share": y.calm_map_flooded_share.mean(),
                         "storm_days_mean_depth_observed_m": y.storm_observed_mean_depth_m.median(), "storm_days_mean_depth_m": y.storm_map_mean_depth_m.median(), "storm_days_flooded_share_observed": y.storm_observed_flooded_share.mean(), "storm_days_flooded_share": y.storm_map_flooded_share.mean(),
                         "largest_depth_observed_median_m": y.storm_observed_largest_depth_m.median(), "largest_depth_median_m": y.storm_map_largest_depth_m.median(), "largest_depth_mean_error_m": e.mean(), "largest_depth_rmse_m": float(np.sqrt((e ** 2).mean())),
                         "largest_depth_correlation": float(np.corrcoef(y.storm_observed_largest_depth_m, y.storm_map_largest_depth_m)[0, 1])})
    t = pd.DataFrame(rows); o = Path(a.out); t.to_csv(o.with_name(o.stem + "_summary.csv"), index=False); pd.set_option("display.width", 250); print(t.round(3).T.to_string()); print("->", o)


if __name__ == "__main__":
    main()
