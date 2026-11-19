"""Flood map, numbers and figure of the check against the storm-tide sensors of Hurricane Ida (USGS, temporary deployments).

The peaks of storm_tide_check.py are on the level of the numerical model; the sensors are in NAVD88. One offset is used for
all sites: the median of (numerical model minus observed, hours before the storm) over the NOAA tide gauges among the
control points, which have a surveyed NAVD88 datum and stand in open water. The model and mapping peaks are moved to NAVD88
with it. (The offset of the nearest control point was tried first; at river gauges it contains local misfits of the model.) The four sensors at Grand Isle are kept apart: the hindcast is
about 2 m lower than the sensors there. Two stand on the fishing pier of the State Park on the Gulf side, two on a pier by
Bridgeside Marina at Caminada Pass (the west end of the island). The regular gauges agree that the hindcast is low here:
NOAA Grand Isle on the bay side peaked at 1.65 m above MSL (6-minute data) against 0.82 m in the hindcast, and USGS Caminada
Pass at 2.36 m NAVD88 (hourly) against 0.82 m, three hours after the hindcast peak. The Gulf side stood about 1.6 m higher
than the bay side; why the hindcast shows neither is not established here.
Input : deliverables/35_floodmap/ida_storm_tide_check.csv, observed_inputs_stations.csv, controls_used_39_points.csv
Output: deliverables/35_floodmap/ida_storm_tide_compare.csv, ida_storm_tide_summary.txt, ida_storm_tide_peaks.png
Usage : python storm_tide_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10.5, "axes.linewidth": 0.6})
INK, MODEL, MAP = "#1a1a19", "#2a78d6", "#d6690f"
BEACH = {"LAJEF27108", "LAJEF27112", "LAJEF27133", "LAJEF27136"}       # Grand Isle: State Park fishing pier (Gulf side) and a pier by Bridgeside Marina (Caminada Pass)
PLACE = {"LAJEF06563": "Lake Pontchartrain, south shore", "LAJEF27108": "Grand Isle, pier at Caminada Pass", "LAJEF27112": "Grand Isle, pier at Caminada Pass (second sensor)", "LAJEF27133": "Grand Isle State Park pier, Gulf side",
         "LAJEF27136": "Grand Isle State Park pier, Gulf side (second sensor)", "LAPLA27142": "Breton Sound Marina", "LAPLA27153": "Bay Pomme d'Or", "LASTB00004": "Mississippi River Gulf Outlet",
         "LASTT23298": "Rigolets", "LASTT27187": "Lake Pontchartrain, north shore", "LATAN23291": "Pass Manchac", "MSHAN06615": "East Pearl River", "MSHAR25057": "Mississippi Sound, Harrison County",
         "MSJAC25056": "Bayou Cumbest"}


def main() -> None:
    s = pd.read_csv(D / "ida_storm_tide_check.csv")
    st = pd.read_csv(D / "observed_inputs_stations.csv", dtype={"station_id": str}); cu = pd.read_csv(D / "controls_used_39_points.csv", dtype={"station_id": str})
    c = st[st.group.str.startswith("control")].merge(cu[["station_id", "datum_known"]], on="station_id"); c = c[c.datum_known & (c.source == "NOAA_COOPS") & (c.offset_from == "hours before the storm")]
    off = float(c.offset_m.median()); print(f"offset: median of {len(c)} NOAA tide gauges {off:+.3f} m (from {c.offset_m.min():+.2f} to {c.offset_m.max():+.2f} m)")
    rows = []
    for r in s.itertuples():
        rows.append({"site_number": r.site_number, "place": PLACE.get(r.site_number, r.waterbody), "latitude_dd": r.latitude_dd, "longitude_dd": r.longitude_dd, "grand_isle": r.site_number in BEACH,
                     "sensor_peak_m": r.peak_m, "offset_m": off,
                     "hindcast_peak_m": r.hindcast_peak_m - off, "mapping_model_inputs_peak_m": r.mapping_model_inputs_peak_m - off, "mapping_observed_inputs_peak_m": r.mapping_observed_inputs_peak_m - off,
                     "hindcast_peak_as_archived_m": r.hindcast_peak_m})
    t = pd.DataFrame(rows).sort_values(["grand_isle", "sensor_peak_m"], ascending=[True, True]).reset_index(drop=True); t.round(3).to_csv(D / "ida_storm_tide_compare.csv", index=False)
    lines = []
    for lab, x in (("sites away from Grand Isle (bays, lakes, passes, rivers)", t[~t.grand_isle]), ("Grand Isle (Gulf side and Caminada Pass)", t[t.grand_isle])):
        f = lambda col: f"{(x[col] - x.sensor_peak_m).mean():+.2f} / {np.sqrt(((x[col] - x.sensor_peak_m) ** 2).mean()):.2f}"
        lines.append(f"{lab}: {len(x)} sensors, measured peak {x.sensor_peak_m.min():.2f} to {x.sensor_peak_m.max():.2f} m NAVD88. Error of the peak, mean / RMS (m): hindcast {f('hindcast_peak_m')}, "
                     f"mapping from the model's own series {f('mapping_model_inputs_peak_m')}, mapping from observed water levels {f('mapping_observed_inputs_peak_m')}; "
                     f"hindcast as archived, without the offset {f('hindcast_peak_as_archived_m')}; offset {off:+.2f} m (median of {len(c)} NOAA tide gauges)")
    (D / "ida_storm_tide_summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines))
    pd.set_option("display.width", 220); print(t.drop(columns=["latitude_dd", "longitude_dd"]).round(2).to_string(index=False))

    fig, ax = plt.subplots(figsize=(10.5, 6.0)); fig.subplots_adjust(left=0.36, right=0.975, top=0.90, bottom=0.14)
    y = np.arange(len(t))
    for k in y:
        v = [t.sensor_peak_m[k], t.hindcast_peak_m[k], t.mapping_observed_inputs_peak_m[k]]; ax.plot([min(v), max(v)], [k, k], color="#cfcfcd", lw=1.0, zorder=1)
    ax.scatter(t.hindcast_peak_m, y, s=46, color=MODEL, zorder=3, label="numerical model (hindcast)")
    ax.scatter(t.mapping_observed_inputs_peak_m, y, s=46, color=MAP, zorder=4, label="mapping model driven by observed water levels")
    ax.scatter(t.sensor_peak_m, y, s=58, color=INK, marker="D", zorder=5, label="storm-tide sensor (USGS)")
    ax.set_yticks(y); ax.set_yticklabels([f"{p}  ({n})" for p, n in zip(t.place, t.site_number)], fontsize=10)
    nb = int((~t.grand_isle).sum()); ax.axhline(nb - 0.5, color="#888", lw=0.7, ls=(0, (4, 3)))
    ax.text(2.25, nb + 1.5, "Grand Isle: the hindcast is about 2 m lower than the sensors,\nand the mapping model follows the hindcast", ha="center", va="center", fontsize=9.5, color="#444",
            bbox=dict(facecolor="white", edgecolor="none", pad=2.0), zorder=2)
    ax.set_xlabel("peak water level during Hurricane Ida (m, NAVD88)"); ax.set_xlim(0.5, 4.0); ax.set_ylim(-0.6, len(t) - 0.4); ax.grid(axis="x", color="#dcdcda", lw=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=2.5)
    ax.set_title("Peak water level at 14 temporary storm-tide sensors that are in none of the inputs", loc="left", fontsize=12, x=-0.55, pad=12)
    fig.legend(loc="lower center", ncol=3, frameon=False, fontsize=10.5, handletextpad=0.3, columnspacing=1.6)
    out = D / "ida_storm_tide_peaks.png"; fig.savefig(out, dpi=220); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
