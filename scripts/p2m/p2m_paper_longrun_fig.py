"""Flood map on ordinary days, figures (p2m_paper_longrun_score.py).

p2m_paper_ordinary_days.png          columns: ordinary days, high water outside Francine, Francine. Top: every marsh gauge, the mean
                                     depth of the map minus the observed one (map from forecasts issued 6 h before). Bottom: the same
                                     gauge by gauge, map against observation, gauges west and east of 90.8 W apart.
p2m_paper_ordinary_days_gauges.png   rows: five marsh gauges from west to east; columns: four days of each kind. Black: observed depth
                                     on the marsh; pale to vivid: the map from forecasts issued 1, 3 and 6 h before.
Input : deliverables/35_floodmap/p2m_paper_ordinary_days_sites.csv, _summary.csv, _fig_data.npz, p2m_paper_11runs_with_input_error_coarse.npz (land and water)
Usage : python p2m_paper_longrun_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

from mapping_fig import DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
EXT = [-92.5, -88.4, 28.85, 30.6]; SPLIT = -90.8; WEST, EAST = "#c2410c", "#2f6fb5"; LEAD_COL = {1: "#f6cdb8", 3: "#ee9468", 6: "#d6450c"}
KINDS = [("ordinary days", "Ordinary days"), ("high water outside Francine", "High water outside Francine"), ("Francine", "Hurricane Francine, 10 to 13 September 2024")]
DIV = ["#8c4a0a", "#c9812a", "#e8c48a", "#ececea", "#a9cfe3", "#4f97c4", "#1f5f99"]; DIV_B = [-0.6, -0.2, -0.1, -0.03, 0.03, 0.1, 0.2, 0.6]      # too dry (brown) - neutral - too wet (blue)


def summary_fig() -> Path:
    z = np.load(D / "p2m_paper_11runs_with_input_error_coarse.npz"); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; base = np.where(z["water_frac"] >= 0.5, 1.0, 0.0); bcm = ListedColormap([DRY, WATER])
    s = pd.read_csv(D / "p2m_paper_ordinary_days_sites.csv"); s = s[s.inputs == "forecast 6 h before"]; sm = pd.read_csv(D / "p2m_paper_ordinary_days_summary.csv"); sm = sm[(sm.inputs == "forecast 6 h before") & (sm.gauges == "all")].set_index("kind_of_day")
    cm = ListedColormap(DIV); nm = BoundaryNorm(DIV_B, cm.N); fig = plt.figure(figsize=(13.6, 7.9)); gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.55], left=0.05, right=0.985, top=0.905, bottom=0.07, wspace=0.16, hspace=0.20)
    for k, (kind, title) in enumerate(KINDS):
        x = s[s.kind_of_day == kind]; q = sm.loc[kind]; ax = fig.add_subplot(gs[0, k]); ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        sc = ax.scatter(x.lon, x.lat, c=x.mean_depth_map_m - x.mean_depth_observed_m, cmap=cm, norm=nm, s=20, edgecolor=INK, linewidth=0.4, zorder=5); ax.axvline(SPLIT, color=INK, lw=0.5, ls=(0, (4, 3)), zorder=4)
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7))); ax.set_title(f"{title}" + "\n" + f"{int(q.hours):,} hours, {int(q.n_gauges)} marsh gauges", loc="left", fontsize=10.5, pad=4, linespacing=1.25)
        ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5); ax.xaxis.set_major_formatter(lambda v, p: f"{-v:.0f}°W"); ax.yaxis.set_major_formatter(lambda v, p: f"{v:.1f}°N")
        if k == 0:
            ax.text(SPLIT - 0.03, 28.88, "90.8°W", ha="right", va="bottom", fontsize=8.5, color=INK)
        bx = fig.add_subplot(gs[1, k]); top = 1.0 if k else 0.6; w = (x.lon < SPLIT).to_numpy(); o, p = x.mean_depth_observed_m.to_numpy(), x.mean_depth_map_m.to_numpy()
        bx.plot([0, top], [0, top], color="#8a8a86", lw=0.8, zorder=1); bx.scatter(o[~w], p[~w], s=24, color=EAST, edgecolor="white", linewidth=0.5, zorder=3); bx.scatter(o[w], p[w], s=24, color=WEST, edgecolor="white", linewidth=0.5, zorder=4)
        bx.set_xlim(0, top); bx.set_ylim(0, top); bx.set_aspect("equal"); bx.grid(color="#e3e3df", lw=0.5); bx.set_axisbelow(True); bx.tick_params(labelsize=8.5, length=2.5); bx.set_xlabel("observed: mean depth on the marsh (m)", fontsize=9.5)
        bx.text(0.03, 0.97, f"RMSE of the depth, hour by hour (median per gauge) {q.rmse_depth_median_m:.2f} m" + "\n" + f"mean depth: observed {q.mean_depth_observed_m:.2f} m, map {q.mean_depth_map_m:.2f} m" + "\n"
                + f"hours with more than 0.1 m of water: observed {100 * q.flooded_share_observed:.0f}%, map {100 * q.flooded_share_map:.0f}%", transform=bx.transAxes, va="top", ha="left", fontsize=8.8, color=INK, linespacing=1.35,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.88), zorder=6)
        if k == 0:
            bx.set_ylabel("flood map: mean depth (m)", fontsize=9.5)
            bx.legend(handles=[Line2D([], [], marker="o", ls="", color=WEST, ms=5, label="marsh gauge west of 90.8°W"), Line2D([], [], marker="o", ls="", color=EAST, ms=5, label="east of 90.8°W")], loc="upper left", bbox_to_anchor=(0.0, 0.80), frameon=False, fontsize=8.8, handletextpad=0.2)
    cax = fig.add_axes([0.35, 0.598, 0.30, 0.011]); cb = fig.colorbar(sc, cax=cax, orientation="horizontal", ticks=DIV_B[1:-1], spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    cb.set_label("mean depth, map minus observed (m): brown = the map is too dry, blue = too wet", fontsize=9, labelpad=2)
    fig.suptitle("Flood map from forecasts issued 6 h before, 2024 to 2025, against the marsh gauges, by kind of day", x=0.012, ha="left", fontsize=11.5, y=0.975)
    out = D / "p2m_paper_ordinary_days.png"; fig.savefig(out, dpi=220); plt.close(fig); return out


def gauges_fig() -> Path:
    z = np.load(D / "p2m_paper_ordinary_days_fig_data.npz"); st, lon = z["station"], z["lon"]; n = len(st); rm = lambda p, o: float(np.sqrt(np.nanmean((p - o) ** 2)) * 100)
    fig, axes = plt.subplots(n, 3, figsize=(13.0, 2.05 * n + 1.1), sharey="row", gridspec_kw={"wspace": 0.08, "hspace": 0.20, "top": 0.925, "bottom": 0.075, "left": 0.07, "right": 0.99})
    for j, (kind, title) in enumerate(KINDS):
        key = kind.replace(" ", "_"); t = pd.DatetimeIndex(z[f"times | {key}"])
        for i in range(n):
            ax = axes[i, j]; o = z[f"observed | {key}"][:, i]; pk = t[int(np.nanargmax(o))]; ax.axvspan(pk - pd.Timedelta(hours=12), pk + pd.Timedelta(hours=12), color="#000000", alpha=0.05, lw=0)
            P = {L: z[f"lead{L} | {key}"][:, i] for L in (1, 3, 6)}
            for L in (1, 3, 6):
                ax.plot(t, P[L], color=LEAD_COL[L], lw=0.9, zorder=4)
            ax.plot(t, o, color=INK, lw=1.1, zorder=5)
            if j == 2:
                lo, hi = ax.get_ylim(); ax.set_ylim(min(lo, -0.02), hi + 0.34 * (hi - lo))
            ax.text(0.03, 0.95, "RMSE (cm)   " + "   ".join(f"{L} h {rm(P[L], o):.1f}" for L in (1, 3, 6)), transform=ax.transAxes, va="top", ha="left", fontsize=7.8, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
            ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}")); ax.set_xlim(t[0], t[-1])
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(labelsize=8, length=2.5)
            if i < n - 1:
                ax.set_xticklabels([])
            if i == 0:
                ax.set_title(f"{title.split(',')[0]}, {t[0].year}", loc="left", fontsize=9.5)
            if j == 0:
                ax.set_ylabel(f"{st[i].split('-')[0]}, {-lon[i]:.2f}°W" + "\n" + "depth on the marsh (m)", fontsize=8.3, linespacing=1.25)
    h = [Line2D([], [], color=INK, lw=1.1)] + [Line2D([], [], color=LEAD_COL[L], lw=1.2) for L in (1, 3, 6)]
    fig.legend(h, ["observed"] + [f"flood map, from forecasts issued {L} h earlier" for L in (1, 3, 6)], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.012))
    fig.suptitle("Depth on the marsh at five marsh gauges, west to east: observed and the flood map from the forecasts of the water-level model", x=0.012, ha="left", fontsize=10.8, y=0.975)
    out = D / "p2m_paper_ordinary_days_gauges.png"; fig.savefig(out, dpi=230); plt.close(fig); return out


if __name__ == "__main__":
    print("->", summary_fig()); print("->", gauges_fig())
