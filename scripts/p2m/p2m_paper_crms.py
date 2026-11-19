"""Flood map: the paper's mapping model (p2m_paper.py) against the marsh gauges (CRMS).

The depth the mapping gives on the land cells around every CRMS site (median over the cells that have a model) is compared,
hour by hour, with the observed depth on the marsh, as crms_marsh_check.py does for the earlier mapping. A site whose cells
have no model (low flood risk or never flooded in the training run) has no map: these are counted, with what was observed there.
Input : --levels levels.npz of marsh_obs_variants.py (observed depth on the marsh of both storms, site list, times),
        --apply DIR of `p2m_paper.py apply` (sites_<tag>.npz, sites_<tag>.csv)
Output: --out CSV (one row per site and field) and a summary TXT beside it
Usage : python p2m_paper_crms.py --levels FILE --apply DIR --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marsh_obs_fit import FR_CALM, FR_STORM, IDA_STORM, metrics  # noqa: E402

BANDS = [-92.5, -91.5, -90.8, -90.2, -89.6, -88.0]
TAGS = {"francine_lead0": "Francine, inputs observed", "francine_lead1": "Francine, inputs forecast 1 h before", "francine_lead3": "Francine, inputs forecast 3 h before", "francine_lead6": "Francine, inputs forecast 6 h before",
        "ida_observed_inputs": "Ida, inputs observed", "ida_hindcast_inputs": "Ida, inputs from the hindcast itself"}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--levels", required=True); ap.add_argument("--apply", required=True); ap.add_argument("--out", required=True); ap.add_argument("--wet", type=float, default=0.1)
    a = ap.parse_args(); ad = Path(a.apply); z = np.load(a.levels, allow_pickle=False); site = list(z["site"]); lat, lon = z["lat"], z["lon"]
    tF = pd.DatetimeIndex(z["times_francine"]); tI = pd.DatetimeIndex(z["times_ida"]); recs = []; L = []
    per = {"francine": (z["observed_to_marsh_francine"], z["observed_level_francine"], np.asarray(tF < FR_CALM), np.asarray((tF >= FR_STORM[0]) & (tF < FR_STORM[1]))),
           "ida": (z["observed_to_marsh_ida"], z["observed_level_ida"], np.arange(len(tI)) < 72, np.asarray((tI >= IDA_STORM[0]) & (tI <= IDA_STORM[1])))}
    for tag, lab in TAGS.items():
        if not (ad / f"sites_{tag}.npz").exists():
            continue
        s = np.load(ad / f"sites_{tag}.npz"); info = pd.read_csv(ad / f"sites_{tag}.csv").set_index("station"); om, od, calm, storm = per[tag.split("_")[0]]; n_no = 0; obs_no = []
        for k, name in enumerate(site):
            if name not in info.index:
                continue
            o = om[:, k]
            if np.isfinite(o).sum() < 48:
                continue
            if name not in s.files:                                       # land cells there, but none with a model
                n_no += 1; obs_no.append(float(np.nanmax(np.where(storm, np.maximum(o, 0), np.nan)))); continue
            dep = s[name].astype(np.float64); dep = dep if len(dep) == len(o) else dep[-len(o):]              # the Francine inputs cover the valid hours only
            r = metrics(lab, pd.Series({"station_id": name, "lat": lat[k], "lon": lon[k]}), o, dep, od[:, k], np.full(len(o), np.nan), calm, storm, a.wet)
            if r:
                recs.append(r)
        x = pd.DataFrame([r for r in recs if r["field"] == lab])
        if x.empty:
            continue
        y = x.dropna(subset=["storm_map_largest_depth_m"]); e = y.storm_map_largest_depth_m - y.storm_observed_largest_depth_m; c = x.dropna(subset=["calm_map_flooded_share"]); ob = np.array(obs_no)
        L += ["", f"{lab}: {len(x)} sites with a model; {n_no} sites without one (largest observed depth there in the storm days: median {np.nanmedian(ob):.2f} m, above 0.3 m at {int((ob > 0.3).sum())})" if n_no else f"{lab}: {len(x)} sites with a model",
              f"  depth on the marsh, RMSE median per site {x.rmse_depth_m.median():.2f} m; calm hours flooded: observed {np.average(c.calm_observed_flooded_share, weights=c.calm_hours):.2f}, map {np.average(c.calm_map_flooded_share, weights=c.calm_hours):.2f}; "
              f"largest depth of the storm days: mean error {e.mean():+.2f} m, RMS {np.sqrt((e ** 2).mean()):.2f} m, correlation {np.corrcoef(y.storm_observed_largest_depth_m, y.storm_map_largest_depth_m)[0, 1]:.2f}, "
              f"median observed {y.storm_observed_largest_depth_m.median():.2f} m, map {y.storm_map_largest_depth_m.median():.2f} m; sites where the map is more than 1 m off: {int((e.abs() > 1).sum())}"]
        g = y.assign(band=pd.cut(y.lon, BANDS)).groupby("band", observed=True).agg(n=("station", "size"), obs=("storm_observed_largest_depth_m", "median"), mapped=("storm_map_largest_depth_m", "median"))
        L.append("  by longitude (sites, observed, map): " + "; ".join(f"{b}: {int(r.n)}, {r.obs:.2f}, {r.mapped:.2f}" for b, r in g.iterrows()))
    pd.DataFrame(recs).to_csv(a.out, index=False); Path(a.out).with_suffix(".txt").write_text(chr(10).join(L), encoding="utf-8"); print(chr(10).join(L)); print("->", a.out)


if __name__ == "__main__":
    main()
