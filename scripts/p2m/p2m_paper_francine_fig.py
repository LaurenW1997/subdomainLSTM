"""Flood map, the whole chain in Hurricane Francine: forecasts of the water-level model at the control points, through the
mapping model implemented as in Bao et al. (2025), against the observations at the marsh gauges (CRMS).

Rows: forecasts issued 1, 3 and 6 h before. Left: the largest depth of the storm days on land, dots: the largest depth
observed at the marsh gauges, same colours (squares: gauges where the mapping model gives no map - no model for the land around them, or outside the prediction area). Right: the same per gauge,
map against observation, gauges west and east of 90.8 W apart.
Mapping model: trained on the eleven runs other than the hindcast of Ida, with an assumed error of the inputs.
Input : deliverables/35_floodmap/p2m_paper_11runs_with_input_error_coarse_francine_leads.npz (p2m_paper_coarse.py),
        p2m_paper_11runs_with_input_error_crms.csv (p2m_paper_crms.py), p2m_paper_11runs_with_input_error_sites.csv (p2m_paper.py apply), marsh_map_sites.csv (observed depths at all gauges)
Output: deliverables/35_floodmap/p2m_paper_francine_forecast_map.png, p2m_paper_francine_forecast_map_by_lead.csv
Usage : python p2m_paper_francine_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

from mapping_fig import DEPTH, DEPTH_B, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
EXT = [-92.5, -88.4, 28.85, 30.6]; SPLIT = -90.8; WEST, EAST = "#c2410c", "#2f6fb5"; LEADS = (1, 3, 6)


def main() -> None:
    z = np.load(D / "p2m_paper_11runs_with_input_error_coarse_francine_leads.npz"); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; water = z["water_frac"] >= 0.5
    c = pd.read_csv(D / "p2m_paper_11runs_with_input_error_crms.csv"); a = pd.read_csv(D / "marsh_map_sites.csv")
    a = a[a.field.str.startswith("the site's own fit") & a.field.str.endswith("6 h before")].dropna(subset=["storm_observed_largest_depth_m"])
    info = pd.read_csv(D / "p2m_paper_11runs_with_input_error_sites.csv").set_index("station").with_a_model      # land cells around the gauge that have a model; a gauge not listed lies outside the prediction area
    a = a.assign(model=[bool(info.get(s_, 0) > 0) for s_ in a.station])
    dcm = ListedColormap(DEPTH); dn = BoundaryNorm(DEPTH_B, dcm.N); bcm = ListedColormap([DRY, WATER]); base = np.where(water, 1.0, 0.0)
    fig = plt.figure(figsize=(12.6, 12.6)); gs = fig.add_gridspec(3, 2, width_ratios=[2.05, 1.0], left=0.055, right=0.985, top=0.925, bottom=0.085, wspace=0.13, hspace=0.20)
    cf = c[c.field.str.startswith("Francine, inputs forecast")]; top = max(float(cf.storm_observed_largest_depth_m.max()), float(cf.storm_map_largest_depth_m.max())) * 1.06; rows = []
    for k, L in enumerate(LEADS):
        ax = fig.add_subplot(gs[k, 0]); f = z[f"peak | francine_lead{L}"]
        ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        im = ax.imshow(np.where(~water & (f > DEPTH_B[0]), f, np.nan), extent=ext, origin="lower", cmap=dcm, norm=dn, aspect="auto", interpolation="nearest")
        for m, mk, sz in ((a[a.model], "o", 22), (a[~a.model], "s", 26)):
            o = m.storm_observed_largest_depth_m; ax.scatter(m.lon, m.lat, c=np.where(o > DEPTH_B[0], o, np.nan), cmap=dcm, norm=dn, s=sz, marker=mk, edgecolor=INK, linewidth=0.45 if mk == "o" else 0.9, zorder=5, plotnonfinite=False)
            dry = m[o <= DEPTH_B[0]]; ax.scatter(dry.lon, dry.lat, c=DRY, s=sz, marker=mk, edgecolor=INK, linewidth=0.45 if mk == "o" else 0.9, zorder=5)
        ax.axvline(SPLIT, color=INK, lw=0.5, ls=(0, (4, 3)), zorder=4)
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7))); ax.set_title(f"Forecast issued {L} h before: largest depth on land (m); dots: observed at the marsh gauges", loc="left", fontsize=11, pad=4)
        ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N")
        if k == 0:
            ax.legend(handles=[Line2D([], [], marker="o", ls="", mfc=DEPTH[3], mec=INK, mew=0.45, ms=5, label="observed at a marsh gauge"),
                               Line2D([], [], marker="s", ls="", mfc=DEPTH[3], mec=INK, mew=0.9, ms=5, label="observed, where the mapping model gives no map")],
                      loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, fontsize=8.8, handletextpad=0.3, borderpad=0.3)
            ax.text(SPLIT - 0.03, 28.88, "90.8°W", ha="right", va="bottom", fontsize=8.5, color=INK)
        x = c[c.field == f"Francine, inputs forecast {L} h before"].dropna(subset=["storm_observed_largest_depth_m", "storm_map_largest_depth_m"]); o, p = x.storm_observed_largest_depth_m.to_numpy(), x.storm_map_largest_depth_m.to_numpy(); w = x.lon.to_numpy() < SPLIT
        r = lambda m: float(np.sqrt(((p - o)[m] ** 2).mean())); rows.append({"forecast_issued_h_before": L, "marsh_gauges_with_a_model": len(x), "west_of_90.8W": int(w.sum()), "east_of_90.8W": int((~w).sum()),
                     "depth_hour_by_hour_rmse_median_per_gauge_m": x.rmse_depth_m.median(), "largest_depth_rmse_m": r(np.ones(len(x), bool)), "largest_depth_rmse_west_m": r(w), "largest_depth_rmse_east_m": r(~w),
                     "largest_depth_observed_median_west_m": float(np.median(o[w])), "largest_depth_map_median_west_m": float(np.median(p[w])), "largest_depth_observed_median_east_m": float(np.median(o[~w])), "largest_depth_map_median_east_m": float(np.median(p[~w]))})
        bx = fig.add_subplot(gs[k, 1]); bx.plot([0, top], [0, top], color="#8a8a86", lw=0.8, zorder=1)
        bx.scatter(o[~w], p[~w], s=24, color=EAST, edgecolor="white", linewidth=0.5, zorder=3); bx.scatter(o[w], p[w], s=24, color=WEST, edgecolor="white", linewidth=0.5, zorder=4)
        bx.set_xlim(0, top); bx.set_ylim(0, top); bx.set_aspect("equal"); bx.grid(color="#e3e3df", lw=0.5); bx.set_axisbelow(True); bx.tick_params(labelsize=8.5, length=2.5)
        bx.set_ylabel("flood map: largest depth (m)", fontsize=9.5); bx.set_title(f"Forecast issued {L} h before, gauge by gauge", loc="left", fontsize=11, pad=4)
        if k == len(LEADS) - 1:
            bx.set_xlabel("observed: largest depth on the marsh (m)", fontsize=9.5)
        if k == 0:
            bx.legend(handles=[Line2D([], [], marker="o", ls="", color=WEST, ms=5, label="marsh gauge west of 90.8°W"), Line2D([], [], marker="o", ls="", color=EAST, ms=5, label="east of 90.8°W")],
                      loc="upper left", bbox_to_anchor=(0.0, 0.80), frameon=False, fontsize=8.8, handletextpad=0.2)
        q = rows[-1]; bx.text(0.03, 0.97, f"RMSE (m), {len(x)} gauges" + "\n" + f"depth, hour by hour (median per gauge) {q['depth_hour_by_hour_rmse_median_per_gauge_m']:.2f}" + "\n"
                              + f"largest depth: all {q['largest_depth_rmse_m']:.2f}, west {q['largest_depth_rmse_west_m']:.2f}, east {q['largest_depth_rmse_east_m']:.2f}",
                              transform=bx.transAxes, va="top", ha="left", fontsize=8.6, color=INK, linespacing=1.3, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
    cax = fig.add_axes([0.16, 0.038, 0.36, 0.011]); cb = fig.colorbar(im, cax=cax, ticks=DEPTH_B[:-1], spacing="uniform", orientation="horizontal"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5); cb.set_label("largest depth (m)", fontsize=9, labelpad=2)
    fig.suptitle("Hurricane Francine, 10 to 13 September 2024: flood map from the forecasts of the water-level model through the mapping model, against the marsh gauges", x=0.012, ha="left", fontsize=11.5, y=0.975)
    out = D / "p2m_paper_francine_forecast_map.png"; fig.savefig(out, dpi=220); plt.close(fig)
    t = pd.DataFrame(rows); t.to_csv(D / "p2m_paper_francine_forecast_map_by_lead.csv", index=False); pd.set_option("display.width", 250); print(t.round(3).T.to_string())
    n = a[~a.model]; print(f"gauges drawn: {len(a)}, without a map: {len(n)}, of them observed above 0.3 m: {int((n.storm_observed_largest_depth_m > 0.3).sum())}"); print("->", out)


if __name__ == "__main__":
    main()
