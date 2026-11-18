"""One wrong reading and what it did to the forecast: USGS 02481510 (Wolf River nr Landon, MS), 17 November 2026.

Top: the readings of the gauge as they came from the service (15 minutes apart), with the single reading of 8.281 m.
Bottom, in the style of the station figures: observed hourly level and the forecasts issued 1, 3 and 6 h earlier (a forecast
from every hour, the version that is run), left with every reading used, right with single outlying readings removed first.
Input : deliverables/33_partner_live_test/despike_readings_02481510.csv, despike_fc_02481510.csv
Output: deliverables/33_partner_live_test/despike_02481510.png
Usage : python despike_fig.py
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

from versions_figs import INK, LEAD_COL  # also sets the figure style (Times New Roman, thin axes)

D = Path(__file__).resolve().parents[2] / "deliverables" / "33_partner_live_test"
LEADS = (1, 3, 6)
RED = "#b3261e"


def main() -> None:
    r = pd.read_csv(D / "despike_readings_02481510.csv", parse_dates=["time_utc"]).set_index("time_utc").level_m
    f = pd.read_csv(D / "despike_fc_02481510.csv"); f["valid"] = pd.to_datetime(f.valid, format="mixed")
    b, e = pd.Timestamp("2026-11-17 00:00"), pd.Timestamp("2026-11-18 06:00")
    f = f[(f.valid >= b) & (f.valid <= e)]
    fig = plt.figure(figsize=(11.0, 6.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.25], hspace=0.5, wspace=0.06, left=0.065, right=0.99, top=0.895, bottom=0.115)

    ax = fig.add_subplot(gs[0, :])
    w = r["2026-11-17 06:00":"2026-11-17 16:00"]
    ax.plot(w.index, w.values, color=INK, lw=1.0, marker="o", ms=2.6, zorder=3)
    t_bad = w.idxmax()
    ax.plot([t_bad], [w.max()], marker="o", ms=6, color=RED, zorder=4)
    ax.annotate(f"{t_bad:%H:%M} UTC: {w.max():.3f} m\nthe readings before and after: {w[t_bad - pd.Timedelta(minutes=15)]:.3f} and {w[t_bad + pd.Timedelta(minutes=15)]:.3f} m",
                xy=(t_bad, w.max()), xytext=(t_bad + pd.Timedelta(minutes=35), w.max() - 1.6), fontsize=9.6, color=RED, va="center", linespacing=1.3)
    ax.set_ylim(0, 9.2); ax.set_ylabel("water level (m)", fontsize=9)
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 2))); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
    ax.set_title("Readings of the gauge as they came from the USGS service, 17 November 2026 (UTC), one every 15 minutes", loc="left", fontsize=9.8, pad=6)
    ax.text(0.0, 1.16, "Wolf River nr Landon, MS  (USGS 02481510)", transform=ax.transAxes, fontsize=10.6, fontweight="bold", color=INK, va="bottom")

    left = None
    for j, (key, title) in enumerate([("off", "Every reading used"), ("on", "Single outlying readings removed before the hourly values are made")]):
        ax = fig.add_subplot(gs[1, j], sharey=left)
        o = f.drop_duplicates("valid").set_index("valid").obs.sort_index().dropna()
        rm = []
        for h in LEADS:
            g = f[f.lead == h].sort_values("valid")
            ax.plot(g.valid, g[key], color=LEAD_COL[h], lw=1.0, zorder=4)
            rm.append(100 * float(np.sqrt(((g[key] - g.obs).dropna() ** 2).mean())))
        ax.plot(o.index, o.values, color=INK, lw=1.15, zorder=5)
        if j == 0:
            left = ax; ax.set_ylabel("water level (m)", fontsize=9); ax.set_ylim(0.9, 5.4)
        else:
            ax.tick_params(labelleft=False)
        ax.text(0.02, 0.96, "RMSE (cm)" + "\n" + "   ".join(f"{h} h {v:.1f}" for h, v in zip(LEADS, rm)), transform=ax.transAxes, va="top", ha="left", fontsize=8.6, color=INK, linespacing=1.25,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
        ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
        ax.set_xlim(b - pd.Timedelta(hours=1), e + pd.Timedelta(hours=1))
        ax.set_title(title, loc="left", fontsize=9.8, fontweight="bold" if key == "on" else "normal", pad=6)
    h = [Line2D([], [], color=INK, lw=1.15)] + [Line2D([], [], color=LEAD_COL[v], lw=1.3) for v in LEADS]
    fig.legend(h, ["observed (hourly)"] + [f"forecast issued {v} h earlier" for v in LEADS], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.0), fontsize=9.5)
    out = D / "despike_02481510.png"; fig.savefig(out, dpi=250); plt.close(fig)
    print("->", out)


if __name__ == "__main__":
    main()
