"""Flood map, figures of the first check of the mapping model: the hindcast of Ida rebuilt from 60 control points.

Four maps of the trusted part of the grid (east of 92.5 W), flood depth on land (cells that are dry in the run without the
hurricane): (a) peak depth of the numerical model, (b) peak depth of the mapping model, which was fitted without this run,
(c) their difference, (d) RMSE of the mapping over all 265 hours. Control points as dots.
Input : deliverables/35_floodmap/coarse_Exp1_fully_coupled.npz (mapping_eval_summary.py), controls_used.csv
Output: deliverables/35_floodmap/ida_peak_flood_depth.png
Usage : python mapping_fig.py [--input exact|noisy|observed --coarse FILE]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
INK = "#1a1a19"
WATER, DRY = "#dfe6ee", "#f6f5f1"
DEPTH = ["#eaf2fb", "#c6dcf3", "#93bfe8", "#5b9ad9", "#2a78d6", "#1a56a6", "#0d3570"]           # one hue, light to dark
DEPTH_B = [0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 20]
DIFF = LinearSegmentedColormap.from_list("d", ["#1a56a6", "#5b9ad9", "#c6dcf3", "#ececea", "#f6cdb8", "#ee9468", "#b8400e"])   # two hues, neutral in the middle
DIFF_B = [-2, -1, -0.5, -0.2, -0.1, 0.1, 0.2, 0.5, 1, 2]
ERR = ["#fdf1e7", "#f9d9bf", "#f3b98f", "#ea9460", "#d6690f", "#a8480a"]
ERR_B = [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 5]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--input", choices=["exact", "noisy", "observed"], default="exact"); ap.add_argument("--coarse", default=str(D / "coarse_Exp1_fully_coupled.npz")); ap.add_argument("--controls", default=str(D / "controls_used.csv")); ap.add_argument("--out", help="file name in the deliverable folder, if not the default of the input"); ap.add_argument("--west", type=float, default=-92.5)
    a = ap.parse_args()
    z = np.load(a.coarse); lat, lon = z["lat"], z["lon"]
    k = lon >= a.west; lon = lon[k]
    land = z["land_frac"][:, k] >= 0.5; water = z["water_frac"][:, k] >= 0.5
    pt, pp, rm = z["peak_true"][:, k], z[f"peak_{a.input}"][:, k], z[f"rmse_{a.input}"][:, k]
    c = pd.read_csv(a.controls); c = c[c.used] if "used" in c.columns else c; n_cp = len(c); c = c[c.lon.astype(float) >= a.west]
    ext = [lon[0], lon[-1], lat[0], lat[-1]]
    base = np.where(water, 1.0, np.where(land, 0.0, 0.5))
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.6)); fig.subplots_adjust(left=0.035, right=0.965, top=0.955, bottom=0.035, wspace=0.14, hspace=0.17)
    panels = [("(a) Numerical model: peak flood depth on land during Hurricane Ida (m)", np.where(land & (pt > DEPTH_B[0]), pt, np.nan), ListedColormap(DEPTH), DEPTH_B),
              (f"(b) Mapping model from {n_cp} control points, fitted without this run (m)", np.where(land & (pp > DEPTH_B[0]), pp, np.nan), ListedColormap(DEPTH), DEPTH_B),
              ("(c) Difference, mapping minus numerical model (m)", np.where(land & ((pt > 0.1) | (pp > 0.1)), pp - pt, np.nan), DIFF, DIFF_B),
              ("(d) RMSE of the mapping over the 265 hours, land (m)", np.where(land & (rm > ERR_B[0]), rm, np.nan), ListedColormap(ERR), ERR_B)]
    if a.input == "observed":                                 # the inputs are observations: the difference from the hindcast is not an error of the mapping alone
        for k, t_ in enumerate(["(a) Numerical model (hindcast): peak flood depth on land during Hurricane Ida (m)", f"(b) Mapping model driven by the observed water levels at the {n_cp} gauges (m)",
                                "(c) Difference, mapping from observations minus hindcast (m)", "(d) RMS difference from the hindcast over the 265 hours, land (m)"]):
            panels[k] = (t_,) + panels[k][1:]
    for ax, (title, f, cmap, bnd) in zip(axes.ravel(), panels):
        ax.imshow(base, extent=ext, origin="lower", cmap=ListedColormap([DRY, "#eceae4", WATER]), vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        norm = BoundaryNorm(bnd, cmap.N if isinstance(cmap, ListedColormap) else 256, extend="neither")
        im = ax.imshow(f, extent=ext, origin="lower", cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_aspect(1 / np.cos(np.deg2rad(29.9))); ax.set_title(title, loc="left", fontsize=10.5, pad=4)
        ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31.5, 1)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda v, p: f"{-v:.0f}°W"); ax.yaxis.set_major_formatter(lambda v, p: f"{v:.0f}°N")
        cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.82, ticks=bnd[:-1] if len(bnd) > 8 or bnd[-1] > 10 else bnd, spacing="uniform")
        cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
        if title.startswith("(b)"):
            ax.scatter(c.lon.astype(float), c.lat.astype(float), s=13, color=INK, edgecolor="white", linewidth=0.5, zorder=5)
            ax.text(0.01, 0.02, "dots: the control points", transform=ax.transAxes, fontsize=9, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))
    out = D / {"exact": "ida_peak_flood_depth.png", "noisy": "ida_peak_flood_depth_noisy_input.png", "observed": "ida_peak_flood_depth_observed_inputs.png"}[a.input]; out = D / a.out if a.out else out; fig.savefig(out, dpi=220); plt.close(fig)
    print("->", out)


if __name__ == "__main__":
    main()
