"""Flood map, figure of the two mapping models on one grid, Hurricane Francine (largest depth of 10 to 13 September 2024).

(a) the combined map from forecasts issued 6 h before, dots: observed at the marsh gauges in the same colours;
(b) which answer every piece of land gets: from observations, from the Ida runs, or no map and why.
Input : deliverables/35_floodmap/combined_map_coarse.npz (combined_map.py), marsh_map_sites.csv (observed depths at the sites)
Output: deliverables/35_floodmap/combined_map_francine.png
Usage : python combined_map_fig.py
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

from mapping_fig import DEPTH, DEPTH_B, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
EXT = [-92.5, -88.4, 28.85, 31.15]
CL = [("from observations", "#2a78d6", "from observations of 2016 to 2023 (marsh within 10 km of a marsh gauge)"), ("from the Ida runs", "#d6450c", "from the model runs of Ida (flooded there without rainfall)"),
      ("no map: flooded in the Ida runs only with rainfall", "#e9c46a", "no map: in the Ida runs flooded only when it rains"), ("no map: dry in all Ida runs", "#f1efe9", "no map: dry in all twelve Ida runs")]


def main() -> None:
    z = np.load(D / "combined_map_coarse.npz"); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]
    water = z["water_frac"] >= 0.5; fr = np.stack([z[f"class_frac | {c[0]}"] for c in CL]); cls = fr.argmax(0); any_ = fr.sum(0) > 0.25
    pk = z["peak | inputs forecast 6 h before"]; mapped = any_ & (cls <= 1)
    s = pd.read_csv(D / "marsh_map_sites.csv"); s = s[s.field.str.startswith("the site's own fit") & s.field.str.endswith("6 h before")].dropna(subset=["storm_observed_largest_depth_m"])
    fig, axes = plt.subplots(1, 2, figsize=(14.2, 5.1)); fig.subplots_adjust(left=0.035, right=0.985, top=0.93, bottom=0.07, wspace=0.17)
    base = np.where(water, 1.0, 0.0); bcm = ListedColormap([DRY, WATER]); dcm = ListedColormap(DEPTH); dn = BoundaryNorm(DEPTH_B, dcm.N)

    def frame(ax, title):
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.9))); ax.set_title(title, loc="left", fontsize=10.8, pad=4)
        ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31.5, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N")

    ax = axes[0]; ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    im = ax.imshow(np.where(mapped & ~water & (pk > DEPTH_B[0]), pk, np.nan), extent=ext, origin="lower", cmap=dcm, norm=dn, aspect="auto", interpolation="nearest")
    o = s.storm_observed_largest_depth_m; ax.scatter(s.lon, s.lat, c=np.where(o > DEPTH_B[0], o, np.nan), cmap=dcm, norm=dn, s=15, edgecolor=INK, linewidth=0.45, zorder=5)
    frame(ax, "(a) Largest depth on land, Francine, from forecasts issued 6 h before (m); dots: observed at the marsh gauges")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.85, ticks=DEPTH_B[:-1], spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    ax = axes[1]; cc = np.where(water, 4, np.where(any_, cls, 3)).astype(float); cols = [c[1] for c in CL] + [WATER]
    ax.imshow(cc, extent=ext, origin="lower", cmap=ListedColormap(cols), vmin=0, vmax=4, aspect="auto", interpolation="nearest"); frame(ax, "(b) Where the depth comes from")
    ax.legend(handles=[Patch(facecolor=c[1], edgecolor="#bdbbb3", linewidth=0.4, label=c[2]) for c in CL], loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.85).ax.set_visible(False)
    out = D / "combined_map_francine.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
