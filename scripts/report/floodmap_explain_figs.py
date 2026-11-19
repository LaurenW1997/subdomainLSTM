"""Figures that explain the flood map work, for the deck of slides_floodmap.py.

  explain_pipeline.png      the chain from the gauges to the flood map, and where the numerical model comes in
  explain_cell_example.png  one grid cell: the control points with the largest weight in its formula, and the depth during
                            Hurricane Ida (numerical model, mapping from the model's own series, mapping from observations)
  explain_cell_miss.png     a cell the mapping does not reproduce (flooded by local rain in the numerical model)
  explain_csi.png           what the critical success index counts
Input : deliverables/35_floodmap/cell_example_manchac.json, cell_example_laplace.json (scripts/p2m/cell_example.py on sv7)
Output: deliverables/35_floodmap/explain_*.png
Usage : python floodmap_explain_figs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11, "axes.linewidth": 0.6})
INK, MODEL, MAP, GREY = "#1a1a19", "#2a78d6", "#d6690f", "#8a8a88"


def box(ax, x, y, w, h, lines, edge=INK, face="white", lw=1.0, size=11.5, bold_first=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.06", fc=face, ec=edge, lw=lw))
    n = len(lines)
    for k, s in enumerate(lines):
        ax.text(x + w / 2, y + h - (k + 0.9) * h / (n + 0.8), s, ha="center", va="center", fontsize=size, color=INK, fontweight="bold" if (k == 0 and bold_first) else "normal")


def arrow(ax, x0, y0, x1, y1, color=INK):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14, lw=1.1, color=color, shrinkA=0, shrinkB=0))


def pipeline() -> None:
    fig, ax = plt.subplots(figsize=(12.3, 3.5)); ax.set_xlim(0, 12.3); ax.set_ylim(0, 3.5); ax.axis("off"); fig.subplots_adjust(0, 0, 1, 1)
    w, h, y = 2.55, 1.2, 1.9; xs = [0.1, 3.3, 6.5, 9.65]
    box(ax, xs[0], y, w, h, ["Gauges", "water level observed", "in real time"])
    box(ax, xs[1], y, w, h, ["Prediction model (LSTM)", "water level at the control", "points, 1 to 6 h ahead"])
    box(ax, xs[2], y, w, h, ["Mapping model", "one formula for", "every grid cell"], edge=MAP, face="#fdf1e7", lw=1.8)
    box(ax, xs[3], y, w, h, ["Flood map", "water depth in every", "100 m cell, 1 to 6 h ahead"])
    for k in range(3):
        arrow(ax, xs[k] + w + 0.04, y + h / 2, xs[k + 1] - 0.04, y + h / 2)
    box(ax, xs[2], 0.12, w, 1.0, ["Numerical model", "coupled land and ocean model,", "12 runs of Hurricane Ida"], edge=MODEL, face="#eef4fc")
    arrow(ax, xs[2] + w / 2, 1.14, xs[2] + w / 2, y - 0.04, color=MODEL)
    ax.text(xs[2] + w / 2 + 0.12, 1.56, "the formulas are learned from its output", fontsize=10.5, color=MODEL, va="center")
    ax.text(xs[1] + w / 2, y - 0.2, "exists: forecasts for 458 gauges", fontsize=10.5, color=GREY, ha="center")
    ax.text(xs[2] + w / 2, y + h + 0.17, "this work", fontsize=12, color=MAP, ha="center", va="center", fontweight="bold")
    ax.text(xs[3] + w / 2, y - 0.2, "the product to put online", fontsize=10.5, color=GREY, ha="center")
    fig.savefig(D / "explain_pipeline.png", dpi=220); plt.close(fig)


def series_axis(ax, t):
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.xaxis.set_minor_locator(mdates.DayLocator())
    ax.set_xlim(t[0], t[-1]); ax.grid(axis="y", color="#dcdcda", lw=0.5); ax.tick_params(labelsize=10, length=2.5); ax.set_ylabel("water depth at the cell (m)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def cell_example() -> None:
    z = json.loads((D / "cell_example_manchac.json").read_text(encoding="utf-8")); t = pd.date_range("2021-08-25 00:00", periods=len(z["hindcast_depth_m"]), freq="h")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.6, 3.9), gridspec_kw={"width_ratios": [1.0, 1.25]}); fig.subplots_adjust(left=0.265, right=0.985, top=0.88, bottom=0.17, wspace=0.2)
    top = z["top"][::-1]; y = np.arange(len(top)); c = [t_["coefficient"] for t_ in top]
    a1.barh(y, c, color=[MAP if v > 0 else GREY for v in c], height=0.62); a1.axvline(0, color=INK, lw=0.7)
    a1.set_yticks(y); a1.set_yticklabels([t_["name"].replace(", LA", "").replace(" near Mandeville", "").replace(" near Stephensville", "")[:38] for t_ in top], fontsize=10)
    for k, v in zip(y, c):
        a1.text(v + (0.006 if v > 0 else -0.006), k, f"{v:+.2f}", va="center", ha="left" if v > 0 else "right", fontsize=10)
    a1.set_xlim(min(c) - 0.06, max(c) + 0.06); a1.set_xlabel("weight in the formula (m of depth per m at the gauge)"); a1.tick_params(length=2.5, labelsize=10)
    for s in ("top", "right", "left"):
        a1.spines[s].set_visible(False)
    a1.set_title(f"The six largest weights of {z['n_controls']} (they carry {100 * z['share_of_top']:.0f}% of the total)", loc="left", fontsize=11, x=-0.62)
    a2.plot(t, z["hindcast_depth_m"], color=MODEL, lw=1.6, label="numerical model"); a2.plot(t, z["mapping_model_inputs_m"], color=MAP, lw=1.6, label="formula, fed with the model's own levels at the gauges")
    a2.plot(t, z["mapping_observed_inputs_m"], color=MAP, lw=1.4, ls=(0, (4, 2)), label="formula, fed with the observed levels")
    series_axis(a2, t); a2.set_title("Depth at this cell during Hurricane Ida", loc="left", fontsize=11); a2.legend(frameon=False, fontsize=10, loc="upper right", handlelength=1.8); a2.set_ylim(-0.03, 1.32 * max(z["hindcast_depth_m"]))
    fig.savefig(D / "explain_cell_example.png", dpi=220); plt.close(fig)


def cell_miss() -> None:
    z = json.loads((D / "cell_example_laplace.json").read_text(encoding="utf-8")); t = pd.date_range("2021-08-25 00:00", periods=len(z["hindcast_depth_m"]), freq="h")
    fig, ax = plt.subplots(figsize=(6.4, 3.5)); fig.subplots_adjust(left=0.115, right=0.955, top=0.86, bottom=0.14)
    ax.plot(t, z["hindcast_depth_m"], color=MODEL, lw=1.6, label="numerical model"); ax.plot(t, z["mapping_model_inputs_m"], color=MAP, lw=1.6, label="formula, the model's own series")
    ax.plot(t, z["mapping_observed_inputs_m"], color=MAP, lw=1.4, ls=(0, (4, 2)), label="formula, observed water levels")
    series_axis(ax, t); ax.set_title(f"A cell at LaPlace (ground {z['ground_m']:.1f} m): the peak of the numerical model is a pulse of one or two hours", loc="left", fontsize=10.5, x=-0.1); ax.legend(frameon=False, fontsize=10, loc="upper right")
    fig.savefig(D / "explain_cell_miss.png", dpi=220); plt.close(fig)


def csi() -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.5)); ax.set_xlim(0, 6.4); ax.set_ylim(0, 3.5); ax.axis("off"); fig.subplots_adjust(0, 0, 1, 1)
    ax.add_patch(Ellipse((2.45, 2.1), 3.0, 1.9, fc="#2a78d633", ec=MODEL, lw=1.6)); ax.add_patch(Ellipse((3.95, 2.1), 3.0, 1.9, fc="#d6690f33", ec=MAP, lw=1.6))
    ax.text(1.45, 2.1, "missed", ha="center", va="center", fontsize=11.5); ax.text(3.2, 2.1, "both", ha="center", va="center", fontsize=11.5, fontweight="bold"); ax.text(4.95, 2.1, "false\nalarm", ha="center", va="center", fontsize=11.5)
    ax.text(1.5, 3.22, "flooded in the numerical model", color=MODEL, ha="center", fontsize=11); ax.text(4.9, 3.22, "flooded in the mapping", color=MAP, ha="center", fontsize=11)
    ax.text(3.2, 0.52, "CSI  =  both  /  (both + missed + false alarm)", ha="center", fontsize=12.5)
    ax.text(3.2, 0.14, "1 = the two areas are the same;  0 = they do not overlap", ha="center", fontsize=10.5, color=GREY)
    fig.savefig(D / "explain_csi.png", dpi=220); plt.close(fig)


if __name__ == "__main__":
    pipeline(); cell_example(); cell_miss(); csi()
    print("->", D / "explain_*.png")
