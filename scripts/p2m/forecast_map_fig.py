"""Flood map, figure of the map made from forecasts, Hurricane Francine (10 to 13 September 2024).

Peak flood depth on land (cells that are dry in the run without a hurricane), east of 92.5 W:
(a) mapping model fed with the observed water levels at the control points (known only afterwards),
(b) fed with the forecasts issued 6 hours before, (c) b minus a, (d) the same difference for the forecasts issued 3 hours before.
There is no numerical model of this storm and no survey of the flooded area: the figure shows how the map changes with the
lead time, not whether it is right. The comparison with observations is at gauges (forecast_map_stations_fig.py).
Input : deliverables/35_floodmap/francine_forecast_map_peak_coarse.npz (forecast_map_fields.py), controls_used_30_points.csv
Output: deliverables/35_floodmap/francine_forecast_map_peak_depth.png
Usage : python forecast_map_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap

from mapping_fig import DEPTH, DEPTH_B, DIFF, DIFF_B, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
WEST = -92.5


def main() -> None:
    z = np.load(D / "francine_forecast_map_peak_coarse.npz"); lat, lon = z["lat"], z["lon"]; k = lon >= WEST; lon = lon[k]
    land = z["land_frac"][:, k] >= 0.5; water = z["water_frac"][:, k] >= 0.5
    p0, p3, p6 = (z[f"peak_lead{L}"][:, k] for L in (0, 3, 6))
    c = pd.read_csv(D / "controls_used_30_points.csv"); c = c[c.used]; n_cp = len(c); c = c[c.lon.astype(float) >= WEST]
    ext = [lon[0], lon[-1], lat[0], lat[-1]]; base = np.where(water, 1.0, np.where(land, 0.0, 0.5))
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.6)); fig.subplots_adjust(left=0.035, right=0.965, top=0.955, bottom=0.035, wspace=0.14, hspace=0.17)
    either = lambda a, b: land & ((a > 0.1) | (b > 0.1))
    panels = [(f"(a) Mapping model from the observed water levels at {n_cp} gauges: peak flood depth on land (m)", np.where(land & (p0 > DEPTH_B[0]), p0, np.nan), ListedColormap(DEPTH), DEPTH_B),
              ("(b) Mapping model from the forecasts issued 6 hours before (m)", np.where(land & (p6 > DEPTH_B[0]), p6, np.nan), ListedColormap(DEPTH), DEPTH_B),
              ("(c) Difference, from 6 h forecasts minus from observed water levels (m)", np.where(either(p0, p6), p6 - p0, np.nan), DIFF, DIFF_B),
              ("(d) Difference, from 3 h forecasts minus from observed water levels (m)", np.where(either(p0, p3), p3 - p0, np.nan), DIFF, DIFF_B)]
    for ax, (title, f, cmap, bnd) in zip(axes.ravel(), panels):
        ax.imshow(base, extent=ext, origin="lower", cmap=ListedColormap([DRY, "#eceae4", WATER]), vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        norm = BoundaryNorm(bnd, cmap.N if isinstance(cmap, ListedColormap) else 256, extend="neither")
        im = ax.imshow(f, extent=ext, origin="lower", cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_aspect(1 / np.cos(np.deg2rad(29.9))); ax.set_title(title, loc="left", fontsize=10.5, pad=4)
        ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31.5, 1)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda v, p: f"{-v:.0f}°W"); ax.yaxis.set_major_formatter(lambda v, p: f"{v:.0f}°N")
        cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.82, ticks=bnd[:-1] if len(bnd) > 8 or bnd[-1] > 10 else bnd, spacing="uniform")
        cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
        if title.startswith("(a)"):
            ax.scatter(c.lon.astype(float), c.lat.astype(float), s=13, color=INK, edgecolor="white", linewidth=0.5, zorder=5)
            ax.text(0.01, 0.02, "dots: the control points; Hurricane Francine, 10 to 13 September 2024", transform=ax.transAxes, fontsize=9, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))
    out = D / "francine_forecast_map_peak_depth.png"; fig.savefig(out, dpi=220); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
