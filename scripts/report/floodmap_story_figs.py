"""Diagram for the flood map deck: the chain from gauges to map, with the two sources the mapping can be learned from.

Output: deliverables/35_floodmap/explain_pipeline_two_sources.png
Usage : python floodmap_story_figs.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 13})
INK, BLUE, ORANGE, GREY = "#1a1a19", "#2a78d6", "#d6690f", "#8a8a84"


def box(ax, x, y, w, h, title, lines, edge=INK, face="white", lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.06", facecolor=face, edgecolor=edge, linewidth=lw))
    ax.text(x + w / 2, y + h - 0.30, title, ha="center", va="center", fontsize=13, fontweight="bold", color=INK)
    for k, s in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.68 - 0.33 * k, s, ha="center", va="center", fontsize=12.5, color=INK)


def arrow(ax, p, q, color=INK):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=16, linewidth=1.3, color=color))


def main() -> None:
    fig, ax = plt.subplots(figsize=(13.2, 4.6)); ax.set_xlim(0, 13.2); ax.set_ylim(0, 4.6); ax.axis("off")
    w, h, y = 2.95, 1.35, 3.0; xs = [0.1, 3.45, 6.8, 10.15]
    box(ax, xs[0], y, w, h, "Gauges", ["water level observed", "in real time"])
    box(ax, xs[1], y, w, h, "Water-level model (LSTM)", ["level at every gauge,", "1 to 6 h ahead"])
    box(ax, xs[2], y, w, h, "Mapping", ["from the levels at the", "gauges to every place"], edge=ORANGE, face="#fdf1e7", lw=2.0)
    box(ax, xs[3], y, w, h, "Flood map", ["water depth on land,", "1 to 6 h ahead"])
    for k in range(3):
        arrow(ax, (xs[k] + w + 0.05, y + h / 2), (xs[k + 1] - 0.05, y + h / 2))
    ax.text(xs[1] + w / 2, y - 0.22, "exists", ha="center", fontsize=11.5, color=GREY); ax.text(xs[2] + w / 2, y + h + 0.16, "this work", ha="center", fontsize=13, color=ORANGE, fontweight="bold")
    bw = 3.9
    box(ax, 4.2, 0.25, bw, 1.45, "Learned from a numerical model", ["12 runs of Hurricane Ida", "(first attempt, after Bao et al. 2025)"], edge=BLUE, face="#eef4fb")
    box(ax, 8.5, 0.25, bw, 1.45, "Learned from observations", ["marsh gauges, 2016 to 2023,", "many storms (what is used now)"], edge=BLUE, face="#eef4fb")
    arrow(ax, (4.2 + bw / 2, 1.72), (xs[2] + 0.9, y - 0.05), BLUE); arrow(ax, (8.5 + bw / 2, 1.72), (xs[2] + w - 0.9, y - 0.05), BLUE)
    ax.text(5.9, 2.35, "two ways to get the mapping", ha="right", fontsize=12, color=BLUE)
    out = D / "explain_pipeline_two_sources.png"; fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.05); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
