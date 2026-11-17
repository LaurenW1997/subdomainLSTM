"""Map of the partner stations: every station with real-time data and the stations whose water level it is given as input.

A line joins a station to each of its partners. Colour of the line = why the partner is allowed:
  orange  the partner lies upstream of the station on the river network
  grey    the partner lies downstream on the river network (only stations with tide take those)
  blue    the partner is not on the same network but is tidal itself
Dot = station, coloured by what its own water level does (no tide / weakly tidal / tidal, config/station_behaviour.csv);
a hollow dot is a station without partner. In the two enlarged panels the links along the river network carry an arrowhead
that points from the partner to the station.
CRMS stations (training only, no forecast) are not drawn.
Input : --map (config/station_partners_behaviour.csv), runs/v6_wind_q/stations.csv, config/station_behaviour.csv,
        config/station_river_network.csv
Output: --out (deliverables/31_partner_map.png)
Usage : python partner_map_fig.py [--map config/station_partners_behaviour.csv --out deliverables/31_partner_map.png --layout tall|wide|talk]
--layout talk: one map for presenting. Orange arrows: every link from a partner upstream on the river network. Blue arrows:
for the tidally influenced stations (tidal and weakly tidal together) only the first of their up to four partners
(--tidal-links none: no blue arrows). Two examples are drawn thick and named.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import cartopy.crs as ccrs
import cartopy.feature as cf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle

REPO = Path(__file__).resolve().parents[2]
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.titlesize": 10, "legend.fontsize": 9.5})
BLUE, ORANGE, GREEN, INK, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#1a1a19", "#6f6f69"
BEH = {"no tide": (ORANGE, "No tide"), "weakly tidal": (GREEN, "Weakly tidal"), "tidal": (BLUE, "Tidal")}
KIND = {"up": (ORANGE, "Partner upstream on the river network"), "down": (GREY, "Partner downstream on the river network"),
        "tidal": (BLUE, "Partner outside the network, tidal itself")}
FULL = [-99.3, -88.0, 25.6, 31.4]
ZOOMS = [("(b) Houston and Galveston Bay", [-96.35, -94.25, 28.85, 30.55],
          [("08073700", "Buffalo Bayou\nat Piney Point", (-0.30, -0.13)), ("08068090", "W Fk San Jacinto\nabove Lake Houston", (0.05, 0.10)), ("8771450", "Galveston Pier 21", (0.06, -0.10))]),
         ("(c) Southeast Louisiana", [-91.75, -89.15, 28.95, 31.05],
          [("07374000", "Mississippi River\nat Baton Rouge", (-0.50, 0.06)), ("8761927", "New Canal Station", (0.05, 0.06)), ("02491800", "Bogue Chitto\nat Enon", (0.06, 0.05))])]


def base(ax, extent, detail: bool) -> None:
    pc = ccrs.PlateCarree(); ax.set_extent(extent, crs=pc)
    ax.add_feature(cf.NaturalEarthFeature("physical", "land", "10m"), facecolor="#f4f4f1", edgecolor="none", zorder=0)
    ax.add_feature(cf.NaturalEarthFeature("physical", "lakes", "10m"), facecolor="white", edgecolor="#9a9a94", linewidth=0.3, zorder=1)
    ax.add_feature(cf.NaturalEarthFeature("physical", "coastline", "10m"), facecolor="none", edgecolor="#7a7a74", linewidth=0.4, zorder=1)
    ax.add_feature(cf.NaturalEarthFeature("physical", "rivers_lake_centerlines", "10m"), facecolor="none", edgecolor="#b9c7d6", linewidth=0.9 if detail else 0.6, zorder=1)
    ax.add_feature(cf.STATES, linewidth=0.3, edgecolor="#a3a39c", zorder=1)
    for sp in ax.spines.values():
        sp.set_linewidth(0.5); sp.set_edgecolor("#7a7a74")


EX_TIDE = [("NOAA_COOPS", "8768094", "Calcasieu Pass"), ("NOAA_COOPS", "8767816", "Lake Charles")]
EX_RIVER = [("USGS", "08183500", "Falls City"), ("USGS", "08188060", "Runge"), ("USGS", "08188500", "Goliad")]
DARK_BLUE, DARK_ORANGE = "#0d3f8a", "#9c3208"


def talk(st: pd.DataFrame, links: dict, pos: dict, out: Path, first: list | None = None) -> None:
    """One map for a slide: colour = tide or no tide, arrows = partner upstream on the river, two named examples."""
    plt.rcParams.update({"font.size": 12})
    pc = ccrs.PlateCarree()
    fig = plt.figure(figsize=(13.0, 6.72)); ax = fig.add_axes([0.004, 0.006, 0.992, 0.988], projection=pc)
    base(ax, FULL, False); tr = pc._as_mpl_transform(ax)
    for (x0, y0), (x1, y1) in links["up"]:
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), transform=tr, arrowstyle="-|>,head_length=0.5,head_width=0.2", mutation_scale=8, color=ORANGE, lw=0.9, alpha=0.9,
                                     shrinkA=0, shrinkB=2.0, zorder=3, clip_on=True))
    for (x0, y0), (x1, y1) in first or []:                      # tidally influenced stations: only the first partner of each, so the lines can be followed
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), transform=tr, arrowstyle="-|>,head_length=0.5,head_width=0.2", mutation_scale=7, color=BLUE, lw=0.8, alpha=0.75,
                                     shrinkA=0, shrinkB=2.0, zorder=2, clip_on=True))
    tide = st.behaviour != "no tide"; has = st.n_partners > 0
    for m, col in ((~tide, ORANGE), (tide, BLUE)):
        ax.scatter(st.lon[m & has], st.lat[m & has], s=22, color=col, edgecolor="white", linewidth=0.4, transform=pc, zorder=5)
        ax.scatter(st.lon[m & ~has], st.lat[m & ~has], s=17, facecolor="white", edgecolor=col, linewidth=0.8, transform=pc, zorder=4)

    def chain(ex, col):
        pts = [pos[(s_, i_)] for s_, i_, _ in ex]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            ax.add_patch(FancyArrowPatch(p0, p1, transform=tr, arrowstyle="-|>,head_length=0.6,head_width=0.3", mutation_scale=14, color=col, lw=3.0, shrinkA=0, shrinkB=4, zorder=8))
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=62, color=col, edgecolor="white", linewidth=0.9, transform=pc, zorder=9)
        return pts

    box = dict(facecolor="white", edgecolor="none", pad=2.0, alpha=0.92)
    lead = lambda col: dict(arrowstyle="-", color=col, lw=0.9, shrinkA=2, shrinkB=5)
    pts = chain(EX_TIDE, DARK_BLUE)
    ax.annotate("Tide: Calcasieu Pass to Lake Charles\nThe tide reaches the pass first, the lake 52 km inland later.\nLake Charles, 6 h RMSE in the test years: 5.4 to 3.6 cm",
                xy=pts[0], xytext=(-94.35, 28.25), xycoords=tr, textcoords=tr, fontsize=12, color=DARK_BLUE, ha="left", va="top", linespacing=1.3, zorder=10, bbox=box, arrowprops=lead(DARK_BLUE))
    pts = chain(EX_RIVER, DARK_ORANGE)
    ax.annotate("River: San Antonio River, Falls City to Runge to Goliad\nA flood wave passes the gauge upstream first.\nGoliad, 6 h RMSE in the test years: 7.3 to 5.2 cm",
                xy=pts[-1], xytext=(-97.0, 27.0), xycoords=tr, textcoords=tr, fontsize=12, color=DARK_ORANGE, ha="left", va="top", linespacing=1.3, zorder=10, bbox=box, arrowprops=lead(DARK_ORANGE))
    n = lambda m: int(m.sum())
    arrow = lambda col: Line2D([], [], marker=r"$\rightarrow$", ls="", color=col, markersize=15)
    dot = lambda col: Line2D([], [], marker="o", ls="", markerfacecolor=col, markeredgecolor="white", markersize=9)
    h = [dot(ORANGE), arrow(ORANGE), dot(BLUE)]
    lab = [f"No tide  ({n(~tide)} stations): partners only from upstream on its own river",
           f"From the partner upstream to the station  ({len(links['up'])} links)",
           f"Tidally influenced  ({n(tide)} stations): partners are tidal stations along the coast\nand the stations on its own river" + ("" if first else "  (these links are not drawn)")]
    if first:
        h.append(arrow(BLUE)); lab.append(f"From the first partner to the station  ({len(first)} links). The other partners\nof these stations, up to four each, are not drawn")
    h.append(Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=INK, markersize=8))
    lab.append(f"Hollow: no partner  ({n(~has)} stations, {n(~has & ~tide)} of them without tide), forecast as before")
    ax.legend(h, lab, loc="lower right", bbox_to_anchor=(0.995, 0.012), frameon=True, framealpha=0.94, edgecolor="none", fontsize=12, handletextpad=0.5, labelspacing=0.7, borderpad=0.6)
    fig.savefig(out, dpi=220); plt.close(fig)
    print(f"{len(st)} stations, {len(links['up'])} links from upstream ->", out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(REPO / "config" / "station_partners_behaviour.csv")); ap.add_argument("--out", default=str(REPO / "deliverables" / "31_partner_map.png"))
    ap.add_argument("--layout", choices=["tall", "wide", "talk"], default="tall", help="wide: for a slide (overview and legend left, the two enlarged panels right); talk: one simplified map for presenting")
    ap.add_argument("--tidal-links", choices=["first", "none"], default="first", help="talk layout: draw the first partner of every tidally influenced station, or none of their links")
    a = ap.parse_args()
    K = ["source", "station_id"]
    st = pd.read_csv(REPO / "runs" / "v6_wind_q" / "stations.csv", dtype={"station_id": str})
    st = st[st.source != "CRMS"]
    beh = pd.read_csv(REPO / "config" / "station_behaviour.csv", dtype={"station_id": str})[K + ["behaviour"]]
    pm = pd.read_csv(a.map, dtype=str).fillna("")
    st = st.merge(beh, on=K, how="left").merge(pm.drop(columns=["name", "type"]), on=K, how="left").fillna({"behaviour": "no tide"})
    st["n_partners"] = pd.to_numeric(st.n_partners, errors="coerce").fillna(0).astype(int)
    pos = {(s, i): (lo, la) for s, i, lo, la in zip(st.source, st.station_id, st.lon, st.lat)}
    net = pd.read_csv(REPO / "config" / "station_river_network.csv", dtype=str).fillna("")
    ids = lambda s: set(re.findall(r"(\S+) \(", s))
    up = {r.station_id: ids(r.up) for r in net.itertuples()}; down = {r.station_id: ids(r.down) for r in net.itertuples()}
    k = sum(c.endswith("_km") for c in pm.columns)
    links = {"up": [], "down": [], "tidal": []}
    first = []
    for r in st.itertuples():
        for j in range(1, k + 1):
            ps, pi = getattr(r, f"p{j}_source"), getattr(r, f"p{j}_station_id")
            if not isinstance(pi, str) or not pi or (ps, pi) not in pos:
                continue
            kind = "up" if pi in up.get(r.station_id, ()) else "down" if pi in down.get(r.station_id, ()) else "tidal"
            links[kind].append((pos[(ps, pi)], (r.lon, r.lat)))                 # from the partner to the station
            if j == 1 and kind != "up":
                first.append((pos[(ps, pi)], (r.lon, r.lat)))                   # the first partner of a tidally influenced station
    n_links = {q: len(v) for q, v in links.items()}

    if a.layout == "talk":
        talk(st, links, pos, Path(a.out), first if a.tidal_links == "first" else None); return
    pc = ccrs.PlateCarree()
    wide = a.layout == "wide"
    if wide:
        plt.rcParams.update({"font.size": 10.5, "axes.titlesize": 12, "legend.fontsize": 11})
        fig = plt.figure(figsize=(13.0, 6.7))
        gs = fig.add_gridspec(2, 2, width_ratios=[1.75, 1.0], height_ratios=[1.0, 1.0], hspace=0.12, wspace=0.03, left=0.005, right=0.995, top=0.955, bottom=0.01)
        axes = [(fig.add_subplot(gs[0, 0], projection=pc), "(a) All stations with real-time data and their partner stations", FULL, [], False)]
        axes[0][0].set_anchor("NW")
        axes += [(fig.add_subplot(gs[i, 1], projection=pc), t, e, lab, True) for i, (t, e, lab) in enumerate(ZOOMS)]
    else:
        fig = plt.figure(figsize=(13.0, 12.6))
        gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.25], hspace=0.07, wspace=0.04, left=0.01, right=0.99, top=0.965, bottom=0.085)
        axes = [(fig.add_subplot(gs[0, :], projection=pc), "(a) All stations with real-time data and their partner stations", FULL, [], False)]
        axes += [(fig.add_subplot(gs[1, i], projection=pc), t, e, lab, True) for i, (t, e, lab) in enumerate(ZOOMS)]
    for ax, title, ext, labels, detail in axes:
        base(ax, ext, detail)
        tr = pc._as_mpl_transform(ax)
        for q in ("tidal", "down", "up"):                                       # river links on top
            col = KIND[q][0]; river = q != "tidal"
            near = [s for s in links[q] if any(ext[0] - 0.05 < x < ext[1] + 0.05 and ext[2] - 0.05 < y < ext[3] + 0.05 for x, y in s)]
            if detail and river:                                                # arrowhead at the station: the information runs from the partner to it
                for (x0, y0), (x1, y1) in near:
                    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), transform=tr, arrowstyle="-|>,head_length=0.55,head_width=0.22", mutation_scale=9, color=col, lw=1.1,
                                                 alpha=0.95, shrinkA=0, shrinkB=3.2, zorder=3, clip_on=True))
            else:
                ax.add_collection(LineCollection([list(s) for s in near], colors=col, linewidths=(1.0 if detail else 0.9) if river else (0.5 if detail else 0.35),
                                                 alpha=0.95 if river else (0.4 if detail else 0.35), transform=pc, zorder=3 if river else 2))
        size = 30 if detail else 11
        for b, (col, _) in BEH.items():
            x = st[st.behaviour == b]; has = x.n_partners > 0
            ax.scatter(x.lon[has], x.lat[has], s=size, color=col, edgecolor="white", linewidth=0.4, transform=pc, zorder=5)
            ax.scatter(x.lon[~has], x.lat[~has], s=size * 0.8, facecolor="white", edgecolor=col, linewidth=0.9 if detail else 0.6, transform=pc, zorder=4)
        for sid, text, (dx, dy) in labels:
            p = next((v for (s, i), v in pos.items() if i == sid), None)
            if p:
                ax.annotate(text, xy=p, xytext=(p[0] + dx, p[1] + dy), xycoords=pc._as_mpl_transform(ax), textcoords=pc._as_mpl_transform(ax), fontsize=9, color=INK,
                            ha="left", va="center", zorder=7, bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.85),
                            arrowprops=dict(arrowstyle="-", color=INK, lw=0.5, shrinkA=0, shrinkB=3))
        ax.set_title(title, loc="left")
    for _, e, _ in [(t, e, l) for t, e, l in ZOOMS]:
        axes[0][0].add_patch(Rectangle((e[0], e[2]), e[1] - e[0], e[3] - e[2], fill=False, edgecolor=INK, lw=0.8, ls=(0, (4, 2)), transform=pc, zorder=6))
    axes[0][0].text(ZOOMS[0][1][0] + 0.05, ZOOMS[0][1][3] + 0.06, "(b)", transform=pc, fontsize=9.5, zorder=7)
    axes[0][0].text(ZOOMS[1][1][0] + 0.05, ZOOMS[1][1][3] + 0.06, "(c)", transform=pc, fontsize=9.5, zorder=7)

    h1 = [Line2D([], [], color=KIND[q][0], lw=1.6) for q in ("up", "down", "tidal")]
    l1 = [f"{KIND[q][1]}  ({n_links[q]})" for q in ("up", "down", "tidal")]
    h2 = [Line2D([], [], marker="o", ls="", markerfacecolor=c, markeredgecolor="white", markersize=7) for c, _ in BEH.values()]
    l2 = [f"{lab}  ({int((st.behaviour == b).sum())} stations, {int(((st.behaviour == b) & (st.n_partners == 0)).sum())} without partner)" for b, (_, lab) in BEH.items()]
    h2.append(Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=INK, markersize=6.5)); l2.append("Hollow: station without partner")
    if wide:
        fig.legend(h1, l1, loc="upper left", ncol=1, frameon=False, bbox_to_anchor=(0.005, 0.40), handlelength=2.2, title_fontsize=11, alignment="left",
                   title="Line: a station and one of its partners, by the reason the partner\nis allowed (number of links). Arrowheads in (b), (c): partner to station")
        fig.legend(h2, l2, loc="upper left", ncol=1, frameon=False, bbox_to_anchor=(0.37, 0.40), handletextpad=0.2, title_fontsize=11, alignment="left",
                   title="Dot: a station, by what its own water level does")
    else:
        fig.legend(h1, l1, loc="lower left", ncol=3, frameon=False, bbox_to_anchor=(0.01, 0.045), handlelength=2.2, columnspacing=1.6, title="Line: a station and one of its partners, by the reason the partner is allowed (number of links). Arrowheads in (b) and (c): from the partner to the station",
                   title_fontsize=9.5, alignment="left")
        fig.legend(h2, l2, loc="lower left", ncol=4, frameon=False, bbox_to_anchor=(0.01, 0.0), handletextpad=0.2, columnspacing=1.4, title="Dot: a station, by what its own water level does",
                   title_fontsize=9.5, alignment="left")
    out = Path(a.out); fig.savefig(out, dpi=220, bbox_inches=None if wide else "tight", pad_inches=0.06); plt.close(fig)
    print(f"{len(st)} stations, links {n_links} ->", out)


if __name__ == "__main__":
    main()
