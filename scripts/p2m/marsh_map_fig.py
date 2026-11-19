"""Flood map, figure of the gridded map made from observations, Hurricane Francine (largest depth of 10 to 13 September 2024).

(a) the map from the levels fitted at the marsh gauges and spread over the grid, inputs = forecasts issued 6 h before;
(b) the mapping model fitted on the model runs of Ida, same cells, same inputs; in (a) and (b) the dots are the marsh gauges
with the observed largest depth in the same colours; (c) a minus b; (d) where the map is given.
Input : deliverables/35_floodmap/marsh_map_map_coarse.npz, marsh_map_sites.csv (marsh_map.py)
Output: deliverables/35_floodmap/marsh_map_francine.png
Usage : python marsh_map_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

from mapping_fig import DEPTH, DEPTH_B, DIFF, DIFF_B, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
EXT = [-92.5, -88.9, 28.9, 30.6]


def main() -> None:
    z = np.load(D / "marsh_map_map_coarse.npz"); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]
    water = z["water_frac"] >= 0.5; land = z["land_frac"] >= 0.5; cover = z["cover_frac"] > 0.25; levee = (z["behind_levee_frac"] > 0.25) & ~cover
    new, old = z["peak | from observations, inputs forecast 6 h before"], z["peak | fitted on the Ida runs, inputs forecast 6 h before"]
    s = pd.read_csv(D / "marsh_map_sites.csv"); s = s[s.field.str.startswith("the site's own fit") & s.field.str.endswith("6 h before")].dropna(subset=["storm_observed_largest_depth_m"])
    base = np.where(water, 1.0, np.where(land, 0.0, 0.5)); bcm = ListedColormap([DRY, "#eceae4", WATER]); dcm = ListedColormap(DEPTH); dn = BoundaryNorm(DEPTH_B, dcm.N)
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.9)); fig.subplots_adjust(left=0.04, right=0.965, top=0.95, bottom=0.05, wspace=0.14, hspace=0.20)

    def frame(ax, title):
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7))); ax.set_title(title, loc="left", fontsize=10.5, pad=4)
        ax.set_xticks(np.arange(-92, -88.5, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N")

    for ax, (title, f) in zip(axes[0], [("(a) From observations of 2016 to 2023, spread over the grid: largest depth on land (m)", new), ("(b) Mapping model fitted on the model runs of Ida, same cells (m)", old)]):
        ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        im = ax.imshow(np.where(cover & (f > DEPTH_B[0]), f, np.nan), extent=ext, origin="lower", cmap=dcm, norm=dn, aspect="auto", interpolation="nearest")
        o = s.storm_observed_largest_depth_m; ax.scatter(s.lon, s.lat, c=np.where(o > DEPTH_B[0], o, np.nan), cmap=dcm, norm=dn, s=20, edgecolor=INK, linewidth=0.5, zorder=5)
        ax.scatter(s.lon[o <= DEPTH_B[0]], s.lat[o <= DEPTH_B[0]], s=20, color="white", edgecolor=INK, linewidth=0.5, zorder=5)
        frame(ax, title); cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.85, ticks=DEPTH_B[:-1], spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    axes[0, 0].text(0.01, 0.03, "dots: observed at the marsh gauges, same colours; inputs: forecasts issued 6 h before", transform=axes[0, 0].transAxes, fontsize=9, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))
    ax = axes[1, 0]; ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    im = ax.imshow(np.where(cover & ((new > 0.1) | (old > 0.1)), new - old, np.nan), extent=ext, origin="lower", cmap=DIFF, norm=BoundaryNorm(DIFF_B, 256), aspect="auto", interpolation="nearest")
    frame(ax, "(c) Difference, a minus b (m)"); cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.85, ticks=DIFF_B, spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    ax = axes[1, 1]; cls = np.where(water, 3, np.where(cover, 1, np.where(levee, 2, np.where(land, 0, 4)))).astype(float)
    cols = [DRY, "#5b9ad9", "#d6690f", WATER, "#eceae4"]; ax.imshow(cls, extent=ext, origin="lower", cmap=ListedColormap(cols), vmin=0, vmax=4, aspect="auto", interpolation="nearest")
    ax.scatter(z["site_lon"], z["site_lat"], s=7, color=INK, zorder=5); frame(ax, "(d) Where the map is given")
    ax.legend(handles=[Patch(facecolor=cols[1], label="map given: land within 10 km of a marsh gauge"), Patch(facecolor=cols[2], label="taken out: behind a levee or bank"), Patch(facecolor=cols[0], edgecolor="#cfcfcd", label="no map: no marsh gauge near"),
                       plt.Line2D([], [], marker="o", ls="", color=INK, markersize=3.5, label="marsh gauges (CRMS)")], loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.9, fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.85).ax.set_visible(False)       # keeps the panel the size of the others
    out = D / "marsh_map_francine.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
