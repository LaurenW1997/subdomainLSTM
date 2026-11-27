"""Flood map in Hurricane Francine without and with the step for the level zero, against the marsh gauges (CRMS).

The numerical model lacks the sea level of the time (level_zero_check.py); the chain moves the inputs down to the level of the model.
The step adds one amount back to the inputs at every control point and hour (`p2m_paper.py apply --add`). Columns: the inputs as
before; the inputs with the amount added. Top: largest depth of the storm days on land from the forecast issued --lead hours before,
dots: largest depth observed at the marsh gauges, same colours (squares: no map there). Bottom: the same gauge by gauge.
Input : deliverables/35_floodmap/ <stem>_coarse_francine_leads.npz (p2m_paper_coarse.py), <stem>_crms.csv (p2m_paper_crms.py) of both,
        <stem>_sites.csv of the training (p2m_paper.py apply), marsh_map_sites.csv (observed depths at all gauges)
Output: deliverables/35_floodmap/p2m_level_zero_francine_forecast_map.png
Usage : python p2m_level_zero_map_fig.py [--lead 6] [--amount 0.35]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

from mapping_fig import DEPTH, DEPTH_B, DRY, INK, WATER
from p2m_more_data_francine_fig import EAST, EXT, FIELDS, SPLIT, WEST, stats

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
TRAINING = "ida11_operational_francine_with_input_error"; TRAINED_ON = "eleven runs of Hurricane Ida, the operational forecasts and the hindcast of Hurricane Francine"


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--lead", type=int, default=6); ap.add_argument("--amount", default="0.35"); a_ = ap.parse_args(); L = a_.lead
    cols = {"Inputs moved down to the level of the numerical model": f"p2m_more_data_{TRAINING}", f"Inputs with {a_.amount} m added back:\nthe sea level the numerical model lacks": f"p2m_level_zero_plus_{a_.amount}_{TRAINING}"}
    a = pd.read_csv(D / "marsh_map_sites.csv"); a = a[a.field.str.startswith("the site's own fit") & a.field.str.endswith("6 h before")].dropna(subset=["storm_observed_largest_depth_m"])
    info = pd.read_csv(D / f"p2m_more_data_{TRAINING}_sites.csv").set_index("station").with_a_model; m_ = a.assign(model=[bool(info.get(s_, 0) > 0) for s_ in a.station])
    dcm = ListedColormap(DEPTH); dn = BoundaryNorm(DEPTH_B, dcm.N); bcm = ListedColormap([DRY, WATER])
    C = {n: pd.read_csv(D / (s + "_crms.csv")) for n, s in cols.items()}; C = {n: c[c.field == FIELDS[L]].dropna(subset=["storm_observed_largest_depth_m", "storm_map_largest_depth_m"]) for n, c in C.items()}
    top = max(max(float(c.storm_observed_largest_depth_m.max()), float(c.storm_map_largest_depth_m.max())) for c in C.values()) * 1.06
    fig = plt.figure(figsize=(12.2, 9.6)); gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.45], left=0.06, right=0.985, top=0.885, bottom=0.14, wspace=0.12, hspace=0.06)
    for k, (n, s) in enumerate(cols.items()):
        z = np.load(D / (s + "_coarse_francine_leads.npz")); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; water = z["water_frac"] >= 0.5; f = z[f"peak | francine_lead{L}"]
        ax = fig.add_subplot(gs[0, k]); ax.imshow(np.where(water, 1.0, 0.0), extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        im = ax.imshow(np.where(~water & (f > DEPTH_B[0]), f, np.nan), extent=ext, origin="lower", cmap=dcm, norm=dn, aspect="auto", interpolation="nearest")
        for m, mk, sz in ((m_[m_.model], "o", 15), (m_[~m_.model], "s", 19)):
            o = m.storm_observed_largest_depth_m; ax.scatter(m.lon, m.lat, c=np.where(o > DEPTH_B[0], o, np.nan), cmap=dcm, norm=dn, s=sz, marker=mk, edgecolor=INK, linewidth=0.4 if mk == "o" else 0.85, zorder=5, plotnonfinite=False)
            dry = m[o <= DEPTH_B[0]]; ax.scatter(dry.lon, dry.lat, c=DRY, s=sz, marker=mk, edgecolor=INK, linewidth=0.4 if mk == "o" else 0.85, zorder=5)
        ax.axvline(SPLIT, color=INK, lw=0.5, ls=(0, (4, 3)), zorder=4); ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7)))
        ax.set_title(n, loc="left", fontsize=10.5, pad=4, linespacing=1.15); ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N"); ax.text(SPLIT - 0.03, 28.88, "90.8°W", ha="right", va="bottom", fontsize=8, color=INK)
        x = C[n]; o, p = x.storm_observed_largest_depth_m.to_numpy(), x.storm_map_largest_depth_m.to_numpy(); w = x.lon.to_numpy() < SPLIT; q = stats(x)
        bx = fig.add_subplot(gs[1, k]); bx.plot([0, top], [0, top], color="#8a8a86", lw=0.8, zorder=1)
        bx.scatter(o[~w], p[~w], s=24, color=EAST, edgecolor="white", linewidth=0.5, zorder=3); bx.scatter(o[w], p[w], s=24, color=WEST, edgecolor="white", linewidth=0.5, zorder=4)
        bx.set_xlim(0, top); bx.set_ylim(0, top); bx.set_aspect("equal"); bx.grid(color="#e3e3df", lw=0.5); bx.set_axisbelow(True); bx.tick_params(labelsize=8.5, length=2.5); bx.set_xlabel("observed: largest depth on the marsh (m)", fontsize=9.5)
        if k == 0:
            bx.set_ylabel("flood map: largest depth (m)", fontsize=9.5)
        bx.text(0.03, 0.975, f"largest depth, {len(x)} gauges with a map" + "\n" + f"mean error {q['largest_depth_mean_error_m']:+.2f} m; RMSE all {q['largest_depth_rmse_m']:.2f}, west {q['largest_depth_rmse_west_m']:.2f}, east {q['largest_depth_rmse_east_m']:.2f} m" + "\n"
                + f"correlation {q['largest_depth_correlation']:.2f}; median west {q['largest_depth_map_median_west_m']:.2f} m (observed {q['largest_depth_observed_median_west_m']:.2f}), east {q['largest_depth_map_median_east_m']:.2f} m (observed {q['largest_depth_observed_median_east_m']:.2f})"
                + "\n" + f"depth hour by hour, RMSE, median per gauge: {q['depth_hour_by_hour_rmse_median_per_gauge_m']:.2f} m",
                transform=bx.transAxes, va="top", ha="left", fontsize=8.6, color=INK, linespacing=1.3, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.88), zorder=6)
    cax = fig.add_axes([0.34, 0.04, 0.32, 0.012]); cb = fig.colorbar(im, cax=cax, ticks=DEPTH_B[:-1], spacing="uniform", orientation="horizontal"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5); cb.set_label("largest depth (m)", fontsize=9, labelpad=2)
    fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc=DEPTH[3], mec=INK, mew=0.45, ms=5, label="observed at a marsh gauge"), Line2D([], [], marker="s", ls="", mfc=DEPTH[3], mec=INK, mew=0.9, ms=5, label="observed, where there is no map")],
               loc="lower left", bbox_to_anchor=(0.06, 0.005), frameon=False, fontsize=8.8, ncol=1, handletextpad=0.3, title="maps", title_fontsize=8.8, alignment="left")
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=WEST, ms=5, label="marsh gauge west of 90.8°W"), Line2D([], [], marker="o", ls="", color=EAST, ms=5, label="marsh gauge east of 90.8°W")],
               loc="lower right", bbox_to_anchor=(0.97, 0.005), frameon=False, fontsize=8.8, ncol=1, handletextpad=0.3, title="gauge by gauge", title_fontsize=8.8, alignment="left")
    src = "forecast issued %d h before" % L if L else "observed water levels"
    fig.suptitle(f"Hurricane Francine, 10 to 13 September 2024: largest depth on land from the {src} at the control points, against the marsh gauges" + "\n" + f"Mapping model trained on {TRAINED_ON} (with an assumed error of the inputs)",
                 x=0.012, ha="left", fontsize=11, y=0.985, linespacing=1.3)
    out = D / ("p2m_level_zero_francine_forecast_map.png" if L == 6 else f"p2m_level_zero_francine_forecast_map_lead{L}.png"); fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
