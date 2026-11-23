"""Flood map, figures of the test with control points left out (p2m_paper_leftout.py).

Rows: control points; columns: the four versions of the mapping model (two trainings, each as in the paper and with an
assumed error of the inputs). Every control point shown is left out and computed from its eight nearest other control points.
  Ida       black: observed; blue: numerical model (hindcast); orange: mapping model fed with the observed levels of the others
  Francine  black: observed; pale to vivid: mapping model fed with the forecasts issued 1, 3 and 6 h earlier
Input : deliverables/35_floodmap/p2m_paper_leftout_series.npz, p2m_paper_leftout_stations.csv
Output: deliverables/35_floodmap/p2m_paper_leftout_ida.png, p2m_paper_leftout_francine.png
Usage : python p2m_paper_leftout_fig.py
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
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "axes.linewidth": 0.6})
INK = "#111111"; LEAD_COL = {1: "#f6cdb8", 3: "#ee9468", 6: "#d6450c"}; MODEL = "#3a7bbf"; MAP = "#d6450c"
STATIONS = [("8761927", "New Canal Station, Lake Pontchartrain"), ("8761724", "Grand Isle"), ("07381600", "Lower Atchafalaya River at Morgan City"), ("07374000", "Mississippi River at Baton Rouge")]
VERS = [("exp1_paper", "Trained on the hindcast of Ida only," + "\n" + "regression as in the paper"), ("exp1_error", "Trained on the hindcast of Ida only," + "\n" + "with an assumed error of the inputs"),
        ("11runs_paper", "Trained on the eleven other runs," + "\n" + "regression as in the paper"), ("11runs_error", "Trained on the eleven other runs," + "\n" + "with an assumed error of the inputs")]
WIN = {"ida": ("2021-08-27 12:00", "2021-08-31 12:00"), "francine": ("2024-09-10 00:00", "2024-09-13 23:00")}


def rm(p, o) -> float:
    e = (p - o)[np.isfinite(p) & np.isfinite(o)]
    return float(np.sqrt((e ** 2).mean()) * 100) if len(e) else np.nan


def draw(storm: str) -> Path:
    z = np.load(D / "p2m_paper_leftout_series.npz"); t = pd.DatetimeIndex(z[f"times_{storm}"]); w = np.asarray((t >= WIN[storm][0]) & (t <= WIN[storm][1])); tw = t[w]
    fig, axes = plt.subplots(len(STATIONS), len(VERS), figsize=(13.0, 8.6), sharey="row", sharex=True, gridspec_kw={"wspace": 0.10, "hspace": 0.16})
    for i, (sid, name) in enumerate(STATIONS):
        o = z[f"{storm}_obs_{sid}"][w]; pk = tw[int(np.nanargmax(o))]
        for j, (key, title) in enumerate(VERS):
            ax = axes[i, j]; ax.axvspan(pk - pd.Timedelta(hours=12), pk + pd.Timedelta(hours=12), color="#000000", alpha=0.05, lw=0)
            if storm == "ida":
                m = z[f"ida_hindcast_{sid}"][w]; p = z[f"ida_{key}_{sid}"][w]
                ax.plot(tw, m, color=MODEL, lw=0.9, zorder=3); ax.plot(tw, p, color=MAP, lw=0.9, zorder=4); lab = f"RMSE (cm)" + "\n" + f"numerical model {rm(m, o):.1f}   mapping model {rm(p, o):.1f}"
            else:
                P = {L: z[f"francine_{key}_lead{L}_{sid}"][w] for L in (1, 3, 6)}
                for L in (1, 3, 6):
                    ax.plot(tw, P[L], color=LEAD_COL[L], lw=0.9, zorder=4)
                lab = "RMSE (cm)" + "\n" + "   ".join(f"{L} h {rm(P[L], o):.1f}" for L in (1, 3, 6))
            ax.plot(tw, o, color=INK, lw=1.1, zorder=5)
            if j == len(VERS) - 1:
                lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.30 * (hi - lo))
            ax.text(0.03, 0.96, lab, transform=ax.transAxes, va="top", ha="left", fontsize=7.8, color=INK, linespacing=1.25, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
            ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(labelsize=8, length=2.5); ax.set_xlim(tw[0], tw[-1])
            if i == 0:
                ax.set_title(title, loc="left", fontsize=8.8, linespacing=1.25)
            if j == 0:
                ax.set_ylabel(name.replace(", ", "," + "\n").replace(" at ", "\n" + "at ") + "\n" + "water level (m)", fontsize=8.3, linespacing=1.25)
    if storm == "ida":
        h = [Line2D([], [], color=INK, lw=1.1), Line2D([], [], color=MODEL, lw=1.2), Line2D([], [], color=MAP, lw=1.2)]; lb = ["observed", "numerical model (hindcast)", "mapping model, from the observed levels of the eight nearest other control points"]
        ttl = "Hurricane Ida, 2021: control points left out, one at a time. Levels on the reference level of the numerical model."
    else:
        h = [Line2D([], [], color=INK, lw=1.1)] + [Line2D([], [], color=LEAD_COL[L], lw=1.2) for L in (1, 3, 6)]; lb = ["observed"] + [f"mapping model, from forecasts issued {L} h earlier" for L in (1, 3, 6)]
        ttl = "Hurricane Francine, 2024: control points left out, one at a time; the mapping model is fed with forecasts of the eight nearest other control points."
    fig.legend(h, lb, loc="lower center", ncol=len(h), frameon=False, bbox_to_anchor=(0.5, 0.035)); fig.suptitle(ttl, x=0.012, ha="left", fontsize=10.5, y=0.965)
    out = D / f"p2m_paper_leftout_{storm}.png"; fig.savefig(out, dpi=250, bbox_inches="tight", pad_inches=0.05); plt.close(fig); return out


if __name__ == "__main__":
    import matplotlib.ticker  # noqa: F401
    for s in ("ida", "francine"):
        print("->", draw(s))
