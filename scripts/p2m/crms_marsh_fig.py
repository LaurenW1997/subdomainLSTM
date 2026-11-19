"""Flood map, figure of the comparison with the marsh gauges (CRMS), Hurricane Francine.

At every CRMS site the observation is the water level relative to the surveyed marsh surface (positive = the marsh is flooded).
(a) observed: largest depth on the marsh, 10 to 13 September 2024, (b) the same from the mapping model fed with the observed
water levels at the control points, (c) b minus a, (d) share of the calm hours before the storm (7 and 8 September) in which
the marsh is flooded by more than 0.1 m, observed against map, one dot per site.
Input : deliverables/35_floodmap/crms_marsh_check_sites.csv (crms_marsh_check.py), francine_forecast_map_peak_coarse.npz (background), controls_used_30_points.csv
Output: deliverables/35_floodmap/crms_marsh_check_francine.png
Usage : python crms_marsh_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap

from mapping_fig import DEPTH, DIFF, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
WEST, EXT = -92.5, [-92.5, -88.9, 28.9, 30.6]
DB = [0, 0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 5]; DFB = [-2, -1, -0.5, -0.2, -0.1, 0.1, 0.2, 0.5, 1, 2]


def main() -> None:
    t = pd.read_csv(D / "crms_marsh_check_sites.csv"); t = t[t.field == "Francine, mapping from observed water levels"].dropna(subset=["storm_map_largest_depth_m"])
    z = np.load(D / "francine_forecast_map_peak_coarse.npz"); lat, lon = z["lat"], z["lon"]; k = lon >= WEST
    base = np.where(z["water_frac"][:, k] >= 0.5, 1.0, np.where(z["land_frac"][:, k] >= 0.5, 0.0, 0.5)); ext = [lon[k][0], lon[k][-1], lat[0], lat[-1]]
    c = pd.read_csv(D / "controls_used_30_points.csv"); c = c[c.used]
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.9)); fig.subplots_adjust(left=0.04, right=0.965, top=0.95, bottom=0.07, wspace=0.14, hspace=0.22)
    o, m = t.storm_observed_largest_depth_m, t.storm_map_largest_depth_m
    panels = [(f"(a) Observed at {len(t)} marsh gauges: largest depth on the marsh, 10 to 13 September 2024 (m)", o, ListedColormap(["#ffffff"] + DEPTH[1:]), DB),
              ("(b) Mapping model from the observed water levels at the control points, same sites (m)", m, ListedColormap(["#ffffff"] + DEPTH[1:]), DB),
              ("(c) Difference, map minus observed (m)", m - o, DIFF, DFB)]
    for ax, (title, v, cmap, bnd) in zip(axes.ravel()[:3], panels):
        ax.imshow(base, extent=ext, origin="lower", cmap=ListedColormap([DRY, "#eceae4", WATER]), vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        norm = BoundaryNorm(bnd, cmap.N if isinstance(cmap, ListedColormap) else 256)
        sc = ax.scatter(t.lon, t.lat, c=v, cmap=cmap, norm=norm, s=30, edgecolor=INK, linewidth=0.45, zorder=5)
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7))); ax.set_title(title, loc="left", fontsize=10.5, pad=4)
        ax.set_xticks(np.arange(-92, -88.5, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N")
        cb = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.015, shrink=0.85, ticks=bnd[:-1] if bnd[-1] > 4 else bnd, spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
        if title.startswith("(b)"):
            ax.scatter(c.lon, c.lat, s=26, marker="^", color="#d6450c", edgecolor="white", linewidth=0.5, zorder=6)
            ax.text(0.01, 0.03, "triangles: the control points", transform=ax.transAxes, fontsize=9, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))
    ax = axes[1, 1]; y = t.dropna(subset=["calm_map_flooded_share"]); west = y.lon < -90.8
    ax.plot([0, 1], [0, 1], color="#a3a39c", lw=0.8, zorder=1)
    ax.scatter(y.calm_observed_flooded_share[~west], y.calm_map_flooded_share[~west], s=26, color="#2a78d6", edgecolor="white", linewidth=0.5, zorder=3, label=f"east of 90.8°W ({int((~west).sum())} sites)")
    ax.scatter(y.calm_observed_flooded_share[west], y.calm_map_flooded_share[west], s=26, color="#d6690f", edgecolor="white", linewidth=0.5, zorder=3, label=f"west of 90.8°W ({int(west.sum())} sites)")
    ax.set_xlabel("observed: share of the calm hours with the marsh flooded"); ax.set_ylabel("map: share of the calm hours with the marsh flooded")
    ax.set_title("(d) Calm hours before the storm (7 and 8 September): share of the hours" + chr(10) + "with the marsh flooded by more than 0.1 m, one dot per site", loc="left", fontsize=10.5, pad=4, x=-0.55)
    ax.set_xlim(-0.03, 1.03); ax.set_ylim(-0.03, 1.03); ax.set_aspect("equal"); ax.grid(color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.legend(loc="center left", bbox_to_anchor=(0.01, 0.38), frameon=True, facecolor="white", edgecolor="none", framealpha=0.9, fontsize=9.5, handletextpad=0.2)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    out = D / "crms_marsh_check_francine.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
