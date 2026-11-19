"""Flood map, feasibility for the river valleys: three questions answered with the high-water marks of 2016.

  1  Are there enough river gauges? Distance from every mark to the nearest gauge that reports in real time, has a NAVD88 datum
     and observed the flood.
  2  Can the level at a gauge be carried to the land around it? Elevation of the mark minus the highest level at the nearest
     gauge, by distance (a river surface slopes; a lake or a marsh does not).
  3  Is the ground of the 100 m grid good enough on a valley floor? Surveyed ground at the mark (elevation minus height above
     ground) against the ground of the grid cell.
And together: depth at the mark from "level of the nearest gauge minus ground", with the surveyed ground and with the grid's.
Input : deliverables/35_floodmap/valley_marks_2016_grid.csv, valley_gauges_2016.csv (valley_feasibility.py)
Output: deliverables/35_floodmap/valley_feasibility_marks.csv, valley_feasibility_summary.txt
Usage : python valley_feasibility_check.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
KX, KY = np.cos(np.deg2rad(30.5)) * 111.2, 111.2
BINS = [0, 2, 5, 10, 20, 500]


def rms(v) -> float:
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return float(np.sqrt((v ** 2).mean())) if len(v) else np.nan


def main() -> None:
    m = pd.read_csv(D / "valley_marks_2016_grid.csv"); g = pd.read_csv(D / "valley_gauges_2016.csv", dtype={"station_id": str}); pd.set_option("display.width", 250); L = []
    L.append(f"high-water marks inside the grid: {len(m)} ({m.event.value_counts().to_dict()}); with elevation (NAVD88) and height above ground: {int((m.elev_m.notna() & m.height_above_ground_m.notna() & (m.vertical_datum == 'NAVD88')).sum())}")
    L.append(f"their cells: land {100 * m.cell_is_land.mean():.0f}%; in a leveed area {100 * m.leveed.mean():.0f}%; in the model runs of Ida: {m.ida_runs.value_counts().to_dict()}")
    L.append(f"observed depth at the marks (height above ground): median {m.height_above_ground_m.median():.2f} m, quartiles {m.height_above_ground_m.quantile(0.25):.2f} / {m.height_above_ground_m.quantile(0.75):.2f} m")
    out = []
    for ev, key in (("2016 Aug LA Flood", "aug"), ("2016 Mar LA Flood", "mar")):
        x = m[(m.event == ev) & m.elev_m.notna() & m.height_above_ground_m.notna() & (m.vertical_datum == "NAVD88")].copy()
        gg = g[g.real_time & g[f"{key}_peak_navd88_m"].notna() & (g[f"{key}_observed_share"] >= 0.8)].reset_index(drop=True)
        d = np.hypot((x.lon.to_numpy()[:, None] - gg.lon.to_numpy()[None, :]) * KX, (x.lat.to_numpy()[:, None] - gg.lat.to_numpy()[None, :]) * KY); k = d.argmin(1)
        x["gauge"] = gg.station_id.to_numpy()[k]; x["gauge_name"] = gg.name.to_numpy()[k]; x["gauge_km"] = d.min(1); x["gauge_peak_m"] = gg[f"{key}_peak_navd88_m"].to_numpy()[k]
        x["gauge_rise_m"] = x.gauge_peak_m - gg[f"{key}_level_before_m"].to_numpy()[k]
        x["level_error_m"] = x.gauge_peak_m - x.elev_m                                    # the gauge's peak used as the water level at the mark
        x["ground_error_m"] = x.ground_grid_m - x.ground_surveyed_m
        x["depth_gauge_level_surveyed_ground_m"] = np.maximum(x.gauge_peak_m - x.ground_surveyed_m, 0); x["depth_gauge_level_grid_ground_m"] = np.maximum(x.gauge_peak_m - x.ground_grid_m, 0)
        x["depth_true_level_grid_ground_m"] = np.maximum(x.elev_m - x.ground_grid_m, 0); out.append(x)
        L += ["", f"===== {ev}: {len(x)} marks with elevation and height; {len(gg)} gauges in real time with a NAVD88 datum that observed the flood"]
        L.append("1  distance to the nearest such gauge: median %.1f km; within 2 / 5 / 10 km: %.0f%% / %.0f%% / %.0f%% of the marks" % (x.gauge_km.median(), 100 * (x.gauge_km <= 2).mean(), 100 * (x.gauge_km <= 5).mean(), 100 * (x.gauge_km <= 10).mean()))
        b = x.assign(bin=pd.cut(x.gauge_km, BINS)).groupby("bin", observed=True)
        t = b.agg(marks=("gauge_km", "size"), level_error_median=("level_error_m", "median"), level_error_median_abs=("level_error_m", lambda v: float(np.median(np.abs(v)))), level_error_rms=("level_error_m", rms),
                  depth_observed_median=("height_above_ground_m", "median"))
        t["depth_rmse_gauge_level_surveyed_ground"] = b.apply(lambda y: rms(y.depth_gauge_level_surveyed_ground_m - y.height_above_ground_m))
        t["depth_rmse_gauge_level_grid_ground"] = b.apply(lambda y: rms(y.depth_gauge_level_grid_ground_m - y.height_above_ground_m))
        L += ["2  the peak at the nearest gauge taken as the water level at the mark (m), by distance to the gauge (km):", t.round(2).to_string()]
        ge = x.ground_error_m
        L.append(f"3  ground of the grid cell minus surveyed ground at the mark: median {ge.median():+.2f} m, median absolute {np.median(np.abs(ge)):.2f} m, quartiles {ge.quantile(0.25):+.2f} / {ge.quantile(0.75):+.2f} m, RMS {rms(ge):.2f} m; "
                 f"within 0.3 m at {100 * (ge.abs() <= 0.3).mean():.0f}% of the marks, more than 1 m off at {100 * (ge.abs() > 1).mean():.0f}%")
        L.append(f"   depth with the surveyed water level and the ground of the grid: RMSE {rms(x.depth_true_level_grid_ground_m - x.height_above_ground_m):.2f} m; "
                 f"marks the grid would call dry although the water stood there: {100 * (x.depth_true_level_grid_ground_m <= 0).mean():.0f}%")
        near = x[x.gauge_km <= 5]
        L.append(f"   together, marks within 5 km of a gauge ({len(near)}): depth RMSE {rms(near.depth_gauge_level_surveyed_ground_m - near.height_above_ground_m):.2f} m with the surveyed ground, "
                 f"{rms(near.depth_gauge_level_grid_ground_m - near.height_above_ground_m):.2f} m with the ground of the grid (observed depth, median {near.height_above_ground_m.median():.2f} m)")
        top = x.groupby("gauge_name").agg(marks=("gauge_km", "size"), km=("gauge_km", "median"), level_error_median=("level_error_m", "median"), level_error_spread=("level_error_m", lambda v: float(v.quantile(0.75) - v.quantile(0.25)))).sort_values("marks", ascending=False).head(8)
        L += ["   the gauges with most marks around them:", top.round(2).to_string()]
    o = pd.concat(out); o.to_csv(D / "valley_feasibility_marks.csv", index=False)
    n_all = int((g.real_time).sum()); north = g[g.real_time & (g.lat >= 30.4)]
    L += ["", f"gauges with a NAVD88 datum in the grid: {len(g)}; in real time: {n_all}; of these north of 30.4 N: {len(north)}"]
    (D / "valley_feasibility_summary.txt").write_text(chr(10).join(L), encoding="utf-8"); print(chr(10).join(L))


if __name__ == "__main__":
    main()
