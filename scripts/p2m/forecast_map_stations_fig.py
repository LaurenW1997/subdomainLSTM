"""Flood map, figure of the whole chain against observations at gauges, Hurricane Francine (September 2024).

Rows: gauges. Left column: the water level the mapping model gives at the gauge when the gauge itself is left out and the
other control points are fed with the forecasts issued 1, 3 and 6 hours before. Right column: the forecast of the
water-level model at the gauge itself. Black: observed. Each lead time is one continuous line (a forecast from every hour).
Input : deliverables/35_floodmap/francine_forecast_map_series.npz, francine_forecast_map_stations.csv (forecast_map_check.py)
Output: deliverables/35_floodmap/francine_forecast_map_stations.png
Usage : python forecast_map_stations_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10.5, "axes.linewidth": 0.6})
INK = "#1a1a19"
LEAD_COL = {1: "#f6cdb8", 3: "#ee9468", 6: "#d6450c"}       # as in the forecast figures of the project
STATIONS = [("8761724", "Grand Isle"), ("8761927", "New Canal Station, Lake Pontchartrain"), ("8747437", "Bay Waveland Yacht Club, Mississippi Sound"),
            ("07387040", "Vermilion Bay near Cypremort Point"), ("07381600", "Lower Atchafalaya River at Morgan City"), ("07374000", "Mississippi River at Baton Rouge")]
WINDOW = ("2024-09-09 00:00", "2024-09-15 00:00")


def main() -> None:
    z = np.load(D / "francine_forecast_map_series.npz"); t = pd.DatetimeIndex(z["times"]); k = np.asarray((t >= WINDOW[0]) & (t <= WINDOW[1]))
    st = pd.read_csv(D / "francine_forecast_map_stations.csv", dtype={"station_id": str}); st = st[st.group.str.startswith("control")].set_index(["station_id", "lead_h"])
    fig, axes = plt.subplots(len(STATIONS), 2, figsize=(11.5, 13.2), sharex=True); fig.subplots_adjust(left=0.065, right=0.985, top=0.925, bottom=0.075, wspace=0.10, hspace=0.30)
    for i, (sid, name) in enumerate(STATIONS):
        o = z[f"obs_{sid}"][k]; lo, hi = np.nanmin(o), np.nanmax(o)
        for j, (pre, col) in enumerate((("map", "rmse_mapping_m"), ("fc", "rmse_direct_forecast_m"))):
            ax = axes[i, j]
            for L in (1, 3, 6):
                v = z[f"{pre}{L}_{sid}"][k]; ax.plot(t[k], v, color=LEAD_COL[L], lw=1.1, zorder=3 + L); lo, hi = min(lo, np.nanmin(v)), max(hi, np.nanmax(v))
            ax.plot(t[k], o, color=INK, lw=1.2, zorder=10)
            r = [st.loc[(sid, L), col] for L in (1, 3, 6)]
            ax.text(0.985, 0.94, "RMSE 1 / 3 / 6 h: " + " / ".join(f"{x:.2f}" for x in r) + " m", transform=ax.transAxes, ha="right", va="top", fontsize=9.5,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.9), zorder=20)
            ax.set_title(name if j == 0 else "", loc="left", fontsize=10.8, pad=3)
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(length=2.5, labelsize=9)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        pad = 0.12 * (hi - lo)
        for j in range(2):
            axes[i, j].set_ylim(lo - pad, hi + 3.2 * pad)
        axes[i, 0].set_ylabel("water level (m)", fontsize=9.5); axes[i, 1].tick_params(labelleft=False)
    for ax in axes[-1]:
        ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.set_xlabel("2024 (UTC)")
    fig.text(0.065 + 0.225, 0.945, "Mapping model, this gauge left out:\nforecasts at the other 29 control points go in", ha="center", va="bottom", fontsize=11.5, linespacing=1.25)
    fig.text(0.985 - 0.225, 0.945, "Water-level model at the gauge itself\n(what one has where a gauge exists)", ha="center", va="bottom", fontsize=11.5, linespacing=1.25)
    h = [Line2D([], [], color=INK, lw=1.3)] + [Line2D([], [], color=LEAD_COL[L], lw=1.5) for L in (1, 3, 6)]
    fig.legend(h, ["observed", "issued 1 h before", "issued 3 h before", "issued 6 h before"], loc="lower center", ncol=4, frameon=False, fontsize=11, handlelength=2.6, columnspacing=2.2)
    out = D / "francine_forecast_map_stations.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
