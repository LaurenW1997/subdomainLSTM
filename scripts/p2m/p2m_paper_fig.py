"""Flood map, figure of the mapping model implemented as in Bao et al. (2025), trained on the hindcast of Ida.

(a) which model every cell of the prediction area got (the paper's model selection), (b) Ida, numerical model: peak depth on
land, (c) Ida, the mapping model fed with the observed water levels at the control points, (d) Francine, fed with forecasts
issued 6 h before; dots: observed at the marsh gauges, same colours. Panels (b) to (d): land cells that have a model.
Input : deliverables/35_floodmap/p2m_paper_exp1_<variant>_coarse.npz (p2m_paper_coarse.py), marsh_map_sites.csv (observed depths)
Output: deliverables/35_floodmap/p2m_paper_exp1_<variant>.png
Usage : python p2m_paper_fig.py [--variant with_input_error|as_in_the_paper]
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
from matplotlib.patches import Patch

from mapping_fig import DEPTH, DEPTH_B, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
EXT = [-92.5, -88.4, 28.85, 30.6]
CL = [(1, "#9ec5ea", "Type 1: flooded in every hour (Model-1, linear)"), (2, "#2f9e5b", "Type 2: Model-2, linear on the flooded hours"), (3, "#d6690f", "Type 2: Model-3, hurdle"), (4, "#7a4fb5", "Type 2: Model-4, Tobit"),
      (5, "#e9c46a", "low flood risk: no model"), (6, "#f1efe9", "never flooded in the training run: no model")]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--variant", default="with_input_error", choices=["with_input_error", "as_in_the_paper"]); a = ap.parse_args()
    z = np.load(D / f"p2m_paper_exp1_{a.variant}_coarse.npz"); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; cls = z["class"]; water = z["water_frac"] >= 0.5
    s = pd.read_csv(D / "marsh_map_sites.csv"); s = s[s.field.str.startswith("the site's own fit") & s.field.str.endswith("6 h before")].dropna(subset=["storm_observed_largest_depth_m"])
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.3)); fig.subplots_adjust(left=0.04, right=0.965, top=0.95, bottom=0.05, wspace=0.14, hspace=0.20)
    dcm = ListedColormap(DEPTH); dn = BoundaryNorm(DEPTH_B, dcm.N); base = np.where(water, 1.0, 0.0); bcm = ListedColormap([DRY, WATER])

    def frame(ax, title):
        ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7))); ax.set_title(title, loc="left", fontsize=10.5, pad=4)
        ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N")

    ax = axes[0, 0]; cols = ["#ffffff"] + [c[1] for c in CL]
    ax.imshow(np.where(cls == 0, np.nan, cls), extent=ext, origin="lower", cmap=ListedColormap(cols), vmin=0, vmax=6, aspect="auto", interpolation="nearest"); frame(ax, "(a) The model every cell of the prediction area got")
    ax.legend(handles=[Patch(facecolor=c[1], edgecolor="#bdbbb3", linewidth=0.4, label=c[2]) for c in CL], loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, fontsize=8.2, ncol=2, columnspacing=1.0, handlelength=1.2)
    fig.colorbar(plt.cm.ScalarMappable(), ax=ax, fraction=0.03, pad=0.015, shrink=0.85).ax.set_visible(False)
    lab = "with an assumed error of the inputs" if a.variant == "with_input_error" else "regressions as in the paper"
    for ax, (title, key, dots) in zip(axes.ravel()[1:], [("(b) Ida, numerical model (hindcast): peak depth on land (m)", "peak_truth | ida_hindcast_inputs", False),
                                                           (f"(c) Ida, mapping model from the observed water levels, {lab} (m)", "peak | ida_observed_inputs", False),
                                                           ("(d) Francine, from forecasts issued 6 h before (m); dots: observed at the marsh gauges", "peak | francine_lead6", True)]):
        f = z[key]; ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        im = ax.imshow(np.where(~water & (f > DEPTH_B[0]), f, np.nan), extent=ext, origin="lower", cmap=dcm, norm=dn, aspect="auto", interpolation="nearest")
        if dots:
            o = s.storm_observed_largest_depth_m; ax.scatter(s.lon, s.lat, c=np.where(o > DEPTH_B[0], o, np.nan), cmap=dcm, norm=dn, s=15, edgecolor=INK, linewidth=0.45, zorder=5)
        frame(ax, title); cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015, shrink=0.85, ticks=DEPTH_B[:-1], spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    out = D / f"p2m_paper_exp1_{a.variant}.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
