"""Flood map, figures: depth on the marsh during Hurricane Francine from two mapping models, against the marsh gauges (CRMS).

The two models get the same inputs (forecasts of the water-level model at gauges with data in real time):
  fitted on the model runs of Ida            mapping_fit.py (per grid cell, 30 control points; here the land cells next to the site)
  fitted on observations of 2016 to 2023     marsh_obs_fit.py (per CRMS site, 140 gauges)
Figure 1 (marsh_obs_francine_sites.png): largest depth on the marsh, 10 to 13 September 2024, at the sites both models cover:
  (a) observed, (b) fitted on the Ida runs, (c) fitted on observations, both from forecasts issued 6 h before, (d) medians by longitude.
Figure 2 (marsh_obs_francine_series.png): five sites, the two models in columns; observed in black, one continuous line per
  lead time (forecasts issued 1, 3 and 6 h before).
Input : deliverables/35_floodmap/crms_marsh_check_sites_all_leads.csv, crms_marsh_check_hours_all_leads.npz, marsh_obs_sites.csv, marsh_obs_series.npz,
        francine_forecast_map_peak_coarse.npz (background)
Usage : python marsh_obs_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

from mapping_fig import DEPTH, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
LEAD_COL = {1: "#f6cdb8", 3: "#ee9468", 6: "#d6450c"}
OLD = "Francine, mapping from forecasts issued {L} h before"; NEW = "Francine, inputs forecast {L} h before"
WEST, EXT = -92.5, [-92.5, -88.9, 28.9, 30.6]; DB = [0, 0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 5]; BANDS = [-92.5, -91.5, -90.8, -90.2, -89.6, -88.0]
SITES = [("CRMS0532-H01", "west of the landfall"), ("CRMS5035-H01", "near the landfall, inland"), ("CRMS0303-H01", "Terrebonne coast, where the surge was highest"),
         ("CRMS0034-H01", "west shore of Lake Pontchartrain"), ("CRMS0253-H01", "Barataria basin")]


def main() -> None:
    old = pd.read_csv(D / "crms_marsh_check_sites_all_leads.csv"); new = pd.read_csv(D / "marsh_obs_sites.csv")
    a = old[old.field == OLD.format(L=6)].set_index("station"); b = new[new.field == NEW.format(L=6)].set_index("station")
    j = a[["lat", "lon", "storm_observed_largest_depth_m", "storm_map_largest_depth_m"]].join(b[["storm_map_largest_depth_m"]], rsuffix="_obsfit", how="inner").dropna()
    j.columns = ["lat", "lon", "observed", "ida_runs", "observations"]
    z = np.load(D / "francine_forecast_map_peak_coarse.npz"); lat, lon = z["lat"], z["lon"]; k = lon >= WEST
    base = np.where(z["water_frac"][:, k] >= 0.5, 1.0, np.where(z["land_frac"][:, k] >= 0.5, 0.0, 0.5)); ext = [lon[k][0], lon[k][-1], lat[0], lat[-1]]
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.9)); fig.subplots_adjust(left=0.04, right=0.965, top=0.95, bottom=0.07, wspace=0.14, hspace=0.22)
    cmap = ListedColormap(["#ffffff"] + DEPTH[1:]); norm = BoundaryNorm(DB, cmap.N)
    for ax, (title, col) in zip(axes.ravel()[:3], [(f"(a) Observed at {len(j)} marsh gauges: largest depth on the marsh, 10 to 13 September 2024 (m)", "observed"),
                                                    ("(b) Mapping model fitted on the model runs of Ida, from forecasts issued 6 h before (m)", "ida_runs"),
                                                    ("(c) Fitted on observations of 2016 to 2023, from forecasts issued 6 h before (m)", "observations")]):
        ax.imshow(base, extent=ext, origin="lower", cmap=ListedColormap([DRY, "#eceae4", WATER]), vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        sc = ax.scatter(j.lon, j.lat, c=j[col], cmap=cmap, norm=norm, s=30, edgecolor=INK, linewidth=0.45, zorder=5)
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7))); ax.set_title(title, loc="left", fontsize=10.5, pad=4)
        ax.set_xticks(np.arange(-92, -88.5, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N")
        cb = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.015, shrink=0.85, ticks=DB[:-1], spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    ax = axes[1, 1]; g = j.assign(band=pd.cut(j.lon, BANDS)).groupby("band", observed=True)[["observed", "ida_runs", "observations"]].median(); n = j.assign(band=pd.cut(j.lon, BANDS)).groupby("band", observed=True).size()
    x = np.arange(len(g)); wbar = 0.26
    for i, (col, c, lab) in enumerate((("observed", INK, "observed"), ("ida_runs", "#2a78d6", "fitted on the model runs of Ida"), ("observations", "#d6690f", "fitted on observations of 2016 to 2023"))):
        bars = ax.bar(x + (i - 1) * wbar, g[col], wbar - 0.03, color=c, label=lab, zorder=3)
        for r_, v in zip(bars, g[col]):
            ax.text(r_.get_x() + r_.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8.3, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([f"{-b.left:.1f}–{-b.right:.1f}°W\n{int(n[b])} sites" for b in g.index], fontsize=9)
    ax.set_ylabel("median of the largest depth on the marsh (m)"); ax.set_ylim(0, 1.45); ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(length=2.5)
    ax.set_title("(d) By longitude (Francine made landfall near 91.3°W)", loc="left", fontsize=10.5, pad=4); ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    out = D / "marsh_obs_francine_sites.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)

    zo = np.load(D / "crms_marsh_check_hours_all_leads.npz"); zn = np.load(D / "marsh_obs_series.npz"); to = pd.DatetimeIndex(zo["times_francine"]); tn = pd.DatetimeIndex(zn["times_francine"])
    win = ("2024-09-09 00:00", "2024-09-15 00:00"); ko = np.asarray((to >= win[0]) & (to <= win[1])); kn = np.asarray((tn >= win[0]) & (tn <= win[1]))
    fig, axes = plt.subplots(len(SITES), 2, figsize=(11.5, 11.6), sharex=True); fig.subplots_adjust(left=0.065, right=0.985, top=0.915, bottom=0.085, wspace=0.10, hspace=0.32)
    for i, (sid, place) in enumerate(SITES):
        o = np.maximum(zn[f"{NEW.format(L=6)}|{sid}"][0][kn], 0); hi = np.nanmax(o)
        for jx, (zz, fmt, kk, tt, tab) in enumerate(((zo, OLD, ko, to, old), (zn, NEW, kn, tn, new))):
            ax = axes[i, jx]; rm = []
            for L in (1, 3, 6):
                v = np.maximum(zz[f"{fmt.format(L=L)}|{sid}"][1][kk], 0); ax.plot(tt[kk], v, color=LEAD_COL[L], lw=1.1, zorder=3 + L); hi = max(hi, np.nanmax(v))
                rm.append(float(tab[(tab.field == fmt.format(L=L)) & (tab.station == sid)].rmse_depth_m.iloc[0]))
            ax.plot(tn[kn], o, color=INK, lw=1.2, zorder=10)
            ax.text(0.985, 0.94, "RMSE 1 / 3 / 6 h: " + " / ".join(f"{v:.2f}" for v in rm) + " m", transform=ax.transAxes, ha="right", va="top", fontsize=9.5, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.9), zorder=20)
            ax.set_title(f"{sid[:8]}, {place}" if jx == 0 else "", loc="left", fontsize=10.8, pad=3); ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(length=2.5, labelsize=9)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        for jx in range(2):
            axes[i, jx].set_ylim(-0.04 * hi, 1.35 * hi)
        axes[i, 0].set_ylabel("depth on the marsh (m)", fontsize=9.5); axes[i, 1].tick_params(labelleft=False)
    for ax in axes[-1]:
        ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.set_xlabel("2024 (UTC)")
    fig.text(0.065 + 0.225, 0.94, "Mapping model fitted on the model runs of Ida", ha="center", va="bottom", fontsize=11.5); fig.text(0.985 - 0.225, 0.94, "Fitted on observations of 2016 to 2023", ha="center", va="bottom", fontsize=11.5)
    h = [Line2D([], [], color=INK, lw=1.3)] + [Line2D([], [], color=LEAD_COL[L], lw=1.5) for L in (1, 3, 6)]
    fig.legend(h, ["observed (marsh gauge)", "issued 1 h before", "issued 3 h before", "issued 6 h before"], loc="lower center", ncol=4, frameon=False, fontsize=11, handlelength=2.6, columnspacing=2.2)
    out = D / "marsh_obs_francine_series.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
