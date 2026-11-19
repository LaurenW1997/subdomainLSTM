"""Flood map, figure: largest depth on the marsh, observed against fitted, before and after the changes of marsh_obs_variants.py.

Rows: Francine (forecasts issued 6 h before; after the training years) and Ida (the fit leaves this storm out).
Columns: the first fit (all gauges alike) and the fit chosen on the left-out storms of the training years (near gauges
favoured, steeper at high water, wind at the site). One dot per CRMS site; the line is observed = fitted.
Input : deliverables/35_floodmap/marsh_obs_variants_sites.csv
Output: deliverables/35_floodmap/marsh_obs_variants_largest_depth.png
Usage : python marsh_obs_variants_fig.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10.5, "axes.linewidth": 0.6})
INK, LOW, HIGH = "#1a1a19", "#2a78d6", "#d6450c"
COLS = [("gauges", "First fit: all gauges alike"), ("near gauges favoured + steeper at high water + wind", "Near gauges favoured, steeper at high water, wind at the site")]
ROWS = [("Francine, inputs forecast 6 h before", "Francine, September 2024, from forecasts issued 6 h before"), ("Ida, inputs observed (the fit leaves this storm out)", "Ida, August 2021, left out of the fit")]


def main() -> None:
    t = pd.read_csv(D / "marsh_obs_variants_sites.csv")
    fig, axes = plt.subplots(2, 2, figsize=(10.6, 10.2)); fig.subplots_adjust(left=0.075, right=0.985, top=0.93, bottom=0.065, wspace=0.16, hspace=0.24)
    for i, (test, rlab) in enumerate(ROWS):
        for j, (v, clab) in enumerate(COLS):
            ax = axes[i, j]; x = t[(t.test == test) & (t.variant == v)].dropna(subset=["storm_map_largest_depth_m"]); o, p = x.storm_observed_largest_depth_m, x.storm_map_largest_depth_m; hi = o > 1.2
            ax.plot([0, 3.2], [0, 3.2], color="#a3a39c", lw=0.9, zorder=1)
            ax.scatter(o[~hi], p[~hi], s=16, color=LOW, edgecolor="white", linewidth=0.4, zorder=3); ax.scatter(o[hi], p[hi], s=18, color=HIGH, edgecolor="white", linewidth=0.4, zorder=4)
            ax.axvline(1.2, color="#cfcfcd", lw=0.7, ls=(0, (4, 3)), zorder=0)
            e = p - o
            ax.text(0.03, 0.97, f"all {len(x)} sites: RMS error {np.sqrt((e ** 2).mean()):.2f} m\nobserved above 1.2 m ({int(hi.sum())} sites): mean error {e[hi].mean():+.2f} m\nthe others: mean error {e[~hi].mean():+.2f} m, RMS {np.sqrt((e[~hi] ** 2).mean()):.2f} m",
                    transform=ax.transAxes, va="top", ha="left", fontsize=9.8, linespacing=1.35, bbox=dict(facecolor="white", edgecolor="none", pad=2, alpha=0.9), zorder=10)
            ax.set_xlim(0, 3.2); ax.set_ylim(0, 3.2); ax.set_aspect("equal"); ax.grid(color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(length=2.5)
            ax.set_xlabel("observed largest depth on the marsh (m)"); ax.set_ylabel("fitted (m)" if j == 0 else "")
            ax.set_title(rlab if j == 0 else "", loc="left", fontsize=11, pad=4)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
    for j, (_, clab) in enumerate(COLS):
        fig.text(0.075 + (0.985 - 0.075) * (0.24 + 0.52 * j), 0.962, clab, ha="center", va="bottom", fontsize=12)
    out = D / "marsh_obs_variants_largest_depth.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
