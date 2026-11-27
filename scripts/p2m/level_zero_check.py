"""Flood map, the level zero: what the 0.4 m between the numerical model and the observations is, and how much of it reaches the marsh.

1. Control points that are NOAA tide stations: the difference (model minus observed, quiet 72 hours before Hurricane Ida) set beside
   what NOAA publishes for the station - mean sea level of the 1983-2001 epoch above NAVD88, the mean sea level of the year and of
   the month of the storm above NAVD88 - and beside the mean level of the model itself in those hours.
2. Marsh gauges (CRMS): the water level of the hindcast (Ida, Francine) at the gauge against the observed water level, apart from
   the ground: on the cells that are not land (channels, ponds) and on the flooded land cells; the ground of the grid against the
   surveyed marsh surface; the depth on the marsh.
Input : --offsets CSV (p2m_paper_too_dry_level_offsets.csv), --series NPZ (series.npz of observed_inputs.py: mod_<id> = model level),
        --noaa DIR (datums_<id>.json, monthly_<year>_<id>.json of the NOAA CO-OPS API, datum STND), --levels levels.npz of
        marsh_obs_variants.py, --ida-run / --francine-run NPZ of p2m_run_level_at_sites.py
Output: --out DIR: level_zero_control_points.csv, level_zero_marsh_gauges.csv, level_zero_marsh_gauges_summary.csv
Usage : python level_zero_check.py --offsets FILE --series FILE --noaa DIR --levels FILE --ida-run FILE --francine-run FILE --out DIR
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from marsh_obs_fit import FR_CALM, FR_STORM, IDA_STORM

SPLIT = -90.8


def control_points(a) -> pd.DataFrame:
    O = pd.read_csv(a.offsets, dtype={"station_id": str}); z = np.load(a.series); rows = []
    for r in O[O.source == "NOAA_COOPS"].itertuples():
        s = r.station_id; dj = json.loads((Path(a.noaa) / f"datums_{s}.json").read_text()); d = {x["name"]: x["value"] for x in dj["datums"]}; nav, msl = d.get("NAVD88"), d.get("MSL"); ref = nav if nav is not None else msl
        rec = {"station_id": s, "name": r.name, "lon": r.lon, "levels_relative_to": "NAVD88" if nav is not None else f"mean sea level {dj.get('epoch')} (no NAVD88 published)", "epoch_of_mean_sea_level": dj.get("epoch"),
               "model_minus_observed_quiet_hours_m": r.numerical_model_minus_observed_calm_hours_before_ida_m, "model_mean_level_quiet_hours_m": float(np.nanmean(z["mod_" + s][:72])),
               "epoch_mean_sea_level_m": msl - ref}
        rec["observed_mean_level_quiet_hours_m"] = rec["model_mean_level_quiet_hours_m"] - rec["model_minus_observed_quiet_hours_m"]
        for y, m, k in ((2021, 8, "aug_2021"), (2024, 9, "sep_2024")):
            mm = json.loads((Path(a.noaa) / f"monthly_{y}_{s}.json").read_text()).get("data", []); v = {int(x["month"]): float(x["MSL"]) for x in mm if x["MSL"] != ""}
            rec[f"mean_sea_level_{y}_m"] = float(np.mean(list(v.values()))) - ref if len(v) >= 10 else np.nan; rec[f"mean_sea_level_{k}_m"] = v[m] - ref if m in v else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def marsh(a) -> pd.DataFrame:
    z = np.load(a.levels); site = list(z["site"]); rows = []
    for storm, f, start, gap in (("Ida", a.ida_run, "2021-08-25 00:00", a.gap_ida), ("Francine", a.francine_run, "2024-09-06 22:00", a.gap_francine)):
        key = storm.lower(); t = pd.DatetimeIndex(z[f"times_{key}"]); om, ol, g = z[f"observed_to_marsh_{key}"], z[f"observed_level_{key}"], z[f"marsh_surface_{key}"]; r = np.load(f)
        pos = pd.date_range(start, periods=r["depth_land"].shape[0], freq="h").get_indexer(t); inr = pos >= 0; pos = np.maximum(pos, 0)   # hours of the observations outside the run are left out
        win = {"quiet days": np.asarray(t < (t[0] + pd.Timedelta(hours=72) if storm == "Ida" else pd.Timestamp(FR_CALM))), "storm days": np.asarray((t >= (IDA_STORM if storm == "Ida" else FR_STORM)[0]) & (t < (IDA_STORM if storm == "Ida" else FR_STORM)[1]))}
        for k, name in enumerate(r["station"]):
            if name not in site:
                continue
            s = site.index(name); dl, ll, sl, lw = (r[x][pos, k] for x in ("depth_land", "level_land_flooded", "share_land_flooded", "level_water_cells")); o, lev = om[:, s], ol[:, s]
            for wn, w in win.items():
                q = w & inr & np.isfinite(o) & np.isfinite(lev) & np.isfinite(dl)
                if q.sum() < 12:
                    continue
                qw = q & np.isfinite(lw); ql = q & (sl >= 0.5) & (o > 0.05) & np.isfinite(ll)
                rows.append({"storm": storm, "days": wn, "station": name, "lat": float(z["lat"][s]), "lon": float(z["lon"][s]), "hours": int(q.sum()), "observed_level_mean_m": float(lev[q].mean()),
                             "level_cells_not_land_minus_observed_m": float(np.median((lw - lev)[qw])) if qw.sum() >= 12 else np.nan, "hours_cells_not_land": int(qw.sum()),
                             "level_flooded_land_minus_observed_m": float(np.median((ll - lev)[ql])) if ql.sum() >= 6 else np.nan, "hours_both_flooded": int(ql.sum()),
                             "ground_of_grid_minus_marsh_surface_m": float(r["ground_land"][k] - g[s]), "observed_depth_mean_m": float(np.maximum(o[q], 0).mean()), "model_depth_mean_m": float(dl[q].mean()),
                             "depth_mean_if_only_the_level_were_lower_m": float(np.maximum(o[q] - gap, 0).mean()), "largest_depth_if_only_the_level_were_lower_m": float(np.maximum(o[q] - gap, 0).max()),
                             "observed_largest_depth_m": float(np.maximum(o[q], 0).max()), "model_largest_depth_m": float(dl[q].max())})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("offsets", "series", "noaa", "levels", "ida-run", "francine-run", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--gap-ida", type=float, default=0.38, help="observed minus model water level (m) in the Ida hindcast, for the column 'if only the level were lower'"); ap.add_argument("--gap-francine", type=float, default=0.30)
    a = ap.parse_args(); out = Path(a.out); pd.set_option("display.width", 250)
    c = control_points(a); c.to_csv(out / "level_zero_control_points.csv", index=False); print(c.drop(columns=["name", "levels_relative_to"]).round(3).to_string())
    n = c[c.levels_relative_to == "NAVD88"]; print("\nNOAA stations with NAVD88, mean:"); print(n.select_dtypes("number").drop(columns="lon").mean().round(3).to_string())
    m = marsh(a); m.to_csv(out / "level_zero_marsh_gauges.csv", index=False); rows = []
    for (st, dy), g in m.groupby(["storm", "days"], sort=False):
        for nm, w in (("all", np.ones(len(g), bool)), ("west of 90.8W", (g.lon < SPLIT).to_numpy()), ("east of 90.8W", (g.lon >= SPLIT).to_numpy())):
            y = g[w]; e = y.model_depth_mean_m - y.observed_depth_mean_m; p = y.model_largest_depth_m - y.observed_largest_depth_m
            rows.append({"storm": st, "days": dy, "gauges": nm, "n": len(y), "level_cells_not_land_minus_observed_median_m": y.level_cells_not_land_minus_observed_m.median(), "n_with_cells_not_land": int(y.level_cells_not_land_minus_observed_m.notna().sum()),
                         "level_flooded_land_minus_observed_median_m": y.level_flooded_land_minus_observed_m.median(), "n_both_flooded": int(y.level_flooded_land_minus_observed_m.notna().sum()),
                         "ground_of_grid_minus_marsh_surface_median_m": y.ground_of_grid_minus_marsh_surface_m.median(), "observed_depth_mean_median_m": y.observed_depth_mean_m.median(), "model_depth_mean_median_m": y.model_depth_mean_m.median(), "depth_mean_if_only_the_level_were_lower_median_m": y.depth_mean_if_only_the_level_were_lower_m.median(),
                         "observed_largest_depth_median_m": y.observed_largest_depth_m.median(), "model_largest_depth_median_m": y.model_largest_depth_m.median(), "largest_depth_if_only_the_level_were_lower_median_m": y.largest_depth_if_only_the_level_were_lower_m.median(),
                         "depth_mean_model_minus_observed_median_m": e.median(), "largest_depth_model_minus_observed_median_m": p.median()})
    t = pd.DataFrame(rows); t.to_csv(out / "level_zero_marsh_gauges_summary.csv", index=False); print(); print(t.round(3).T.to_string())


if __name__ == "__main__":
    main()
