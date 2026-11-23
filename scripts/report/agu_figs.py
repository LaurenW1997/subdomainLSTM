"""Figures of the two AGU slides on the water-level model that is run: the mean of five LSTMs with the inputs water level,
wind, upstream discharge and rainfall (run folder v15r_mean5).

  agu_gauges_map.png     the gauges: with data in real time (forecast) and marsh gauges used for training only; the three 100 m domains
  agu_architecture.png   inputs, network and output as a block diagram
  agu_validation.png     observed water level and the forecasts issued 1, 3 and 6 h earlier at six gauges (test years 2024-2025)
  agu_numbers.json       the numbers the slides quote, read from the run folders
Input : runs/v14_stale25/stations.csv, runs/v15r_mean5/per_station_test.csv, runs/v14_stale25/history.json,
        deliverables/17_versions/data and deliverables/37_agu/data (<station>_obs.csv, <station>_fc.csv of extract_versions_hourly.py; column base_fc)
Output: deliverables/37_agu/
Usage : python agu_figs.py
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
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from versions_figs import DOMAINS, INK, LEAD_COL, REPO, load_runs, pooled, window_rmse

OUT = REPO / "deliverables" / "37_agu"
DATA = [REPO / "deliverables" / "17_versions" / "data", OUT / "data"]
KEY = "base_fc"                                             # column of the mean of five models in the forecast files
GREY, LIGHT, RULE = "#8a8a84", "#efefec", "#b9b9b3"
plt.rcParams.update({"font.family": "Times New Roman", "mathtext.fontset": "stix", "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False})

# the six panels of the validation figure: station, window in the data files, panel title, second line of the title
PANELS = [("02481660", "hurricane Francine", "Jourdan River near Bay St. Louis, Mississippi", "tidal river, Hurricane Francine, Sep 2024"),
          ("07380260", "hurricane Francine", "Empire Waterway, Louisiana", "tidal channel, Hurricane Francine, Sep 2024"),
          ("08162500", "hurricane Beryl", "Colorado River near Bay City, Texas", "river, Hurricane Beryl, Jul 2024"),
          ("07375650", "hurricane Francine", "Tangipahoa River near Ponchatoula, Louisiana", "river flood after Hurricane Francine, Sep 2024"),
          ("08072050", "high water", "San Jacinto River near Sheldon, Texas", "river flood, May 2024"),
          ("8773259", "high water", "Port Lavaca, Matagorda Bay, Texas", "tide gauge, Nov 2024")]


def numbers() -> dict:
    st = pd.read_csv(REPO / "runs" / "v14_stale25" / "stations.csv", dtype={"station_id": str})
    per = load_runs(["v15r_mean5"])["v15r_mean5"]; hist = json.loads((REPO / "runs" / "v14_stale25" / "history.json").read_text())
    n = {"gauges": len(st), "by_source": {k: int(v) for k, v in st.source.value_counts().items()}, "gauges_real_time": int(st.source.isin(["USGS", "NOAA_COOPS"]).sum()),
         "observations_train_2010_2022": int(st.n_train.sum()), "observations_all_2010_2025": int(st[["n_train", "n_val", "n_test"]].sum().sum()),
         "epochs": len(hist), "training_minutes_per_model": round(sum(e["sec"] for e in hist) / 60), "samples_per_model": len(hist) * 2000 * 1024,
         "test_gauges": len(per), "test_forecasts": int(per.n_6h.sum()),
         "rmse_all_forecasts_cm": {h: round(pooled(per, h), 3) for h in (1, 3, 6)}, "rmse_median_gauge_cm": {h: round(float(per[f"rmse_{h}h_cm"].median()), 3) for h in (1, 3, 6)}}
    (OUT / "agu_numbers.json").write_text(json.dumps(n, indent=1)); return n


def gauges_map() -> Path:
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    st = pd.read_csv(REPO / "runs" / "v14_stale25" / "stations.csv", dtype={"station_id": str}); rt = st.source.isin(["USGS", "NOAA_COOPS"]); pc = ccrs.PlateCarree()
    fig = plt.figure(figsize=(5.6, 3.25)); ax = fig.add_axes([0.005, 0.13, 0.99, 0.865], projection=pc); ax.set_extent([-99.3, -88.1, 25.6, 31.4], crs=pc)
    ax.add_feature(cf.LAND, facecolor="#f4f4f1"); ax.add_feature(cf.COASTLINE, lw=0.4, edgecolor=GREY); ax.add_feature(cf.STATES, lw=0.3, edgecolor=RULE)
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_linewidth(0.5); sp.set_edgecolor(GREY)
    for (name, x0, x1, y0, y1), (tx, ty, ha, va) in zip(DOMAINS, [(-88.5, 28.82, "right", "bottom"), (-98.93, 25.93, "left", "bottom"), (-96.6, 31.06, "left", "top")]):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=INK, lw=0.8, ls=(0, (4, 2)), transform=pc, zorder=3))
        ax.text(tx, ty, name.replace("100m", ""), transform=pc, fontsize=9.5, color=INK, ha=ha, va=va, zorder=6, bbox=dict(facecolor="white", edgecolor="none", pad=1.0, alpha=0.85))
    ax.scatter(st.lon[~rt], st.lat[~rt], s=5, color="#a9a9a3", linewidth=0, transform=pc, zorder=4)
    ax.scatter(st.lon[rt], st.lat[rt], s=7, color=INK, linewidth=0, transform=pc, zorder=5)
    h = [Line2D([], [], marker="o", ls="", color=INK, markersize=4), Line2D([], [], marker="o", ls="", color="#a9a9a3", markersize=4), Line2D([], [], color=INK, lw=0.8, ls=(0, (4, 2)))]
    fig.legend(h, [f"{int(rt.sum())} gauges with data in real time (USGS, NOAA)", f"{int((~rt).sum())} more gauges, training only (CRMS marsh gauges, USACE)", "100 m model domains"], loc="lower center", ncol=2, frameon=False,
               fontsize=9.5, handletextpad=0.4, columnspacing=1.2, bbox_to_anchor=(0.5, -0.025), labelspacing=0.25)
    out = OUT / "agu_gauges_map.png"; fig.savefig(out, dpi=300); plt.close(fig); return out


def architecture() -> Path:
    """Block diagram: inputs of the past 72 h -> two LSTM layers (unrolled) -> last state joined with the gauge embedding and the
    forecast forcing of the next 6 h -> fully connected head -> water level 1 to 6 h ahead; five such networks, averaged."""
    fig = plt.figure(figsize=(7.4, 4.3)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 7.4); ax.set_ylim(0, 4.3); ax.axis("off")

    def box(x, y, w, h, label, fc="white", fs=10.5, lw=0.9, bold=False, ls="-", va="center", color=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", facecolor=fc, edgecolor=INK, linewidth=lw, linestyle=ls, zorder=2))
        if label:
            ax.text(x + w / 2, y + h / 2 if va == "center" else y + h - 0.09, label, ha="center", va=va if va != "top" else "top", fontsize=fs, color=color, fontweight="bold" if bold else "normal", linespacing=1.15, zorder=3)

    def arrow(x0, y0, x1, y1, lw=0.9):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9, linewidth=lw, color=INK, shrinkA=0, shrinkB=0, zorder=4))

    # ---- inputs of the past 72 h
    ax.text(0.95, 4.12, "Past 72 hours, hourly", ha="center", va="center", fontsize=11, fontweight="bold")
    rows = [("Water level", "at the gauge"), ("Wind", "10 m, at the gauge"), ("Rainfall", "around the gauge"), ("River discharge", "upstream gauge")]
    for k, (a, b) in enumerate(rows):
        y = 3.42 - k * 0.56; box(0.12, y, 1.66, 0.46, "", fc=LIGHT)
        ax.text(0.95, y + 0.30, a, ha="center", va="center", fontsize=10.5); ax.text(0.95, y + 0.12, b, ha="center", va="center", fontsize=9.5, color="#55554f")
    box(0.12, 0.62, 1.66, 0.62, "", fc="white"); ax.text(0.95, 1.03, "Gauge embedding", ha="center", va="center", fontsize=10.5)
    ax.text(0.95, 0.80, "16 numbers learned\nfor each of 1,010 gauges", ha="center", va="center", fontsize=9.5, color="#55554f", linespacing=1.1)

    # ---- the recurrent part, unrolled in time
    x0, cw, gap = 2.36, 0.48, 0.15; xs = [x0, x0 + cw + gap, x0 + 2 * (cw + gap) + 0.40, x0 + 3 * (cw + gap) + 0.40]; labs = ["t − 71", "t − 70", "t − 1", "t"]
    ax.add_patch(FancyBboxPatch((2.22, 1.62), 3.05, 2.30, boxstyle="round,pad=0,rounding_size=0.08", facecolor="white", edgecolor=RULE, linewidth=0.8, zorder=1))
    ax.text(3.73, 4.12, "LSTM: 2 layers × 128 units", ha="center", va="center", fontsize=11, fontweight="bold")
    BUS = 1.80                                                                 # the inputs of one hour run along this line into the lower layer
    for x, lab in zip(xs, labs):
        for y in (2.02, 2.92):
            box(x, y, cw, 0.50, "LSTM", fc=LIGHT, fs=9.5)
        arrow(x + cw / 2, 2.52, x + cw / 2, 2.92); arrow(x + cw / 2, BUS, x + cw / 2, 2.02)
        ax.text(x + cw / 2, 1.44, lab, ha="center", va="center", fontsize=9.5, style="italic")
    for y in (2.27, 3.17):
        arrow(xs[0] + cw, y, xs[1], y); arrow(xs[2] + cw, y, xs[3], y)
        ax.plot([xs[1] + cw, xs[1] + cw + 0.10], [y, y], color=INK, lw=0.9); arrow(xs[2] - 0.12, y, xs[2], y)
        ax.text((xs[1] + cw + xs[2]) / 2, y, "· · ·", ha="center", va="center", fontsize=11)
    ax.text((xs[1] + cw + xs[2]) / 2, 1.44, "· · ·", ha="center", va="center", fontsize=11)
    for k in range(4):                                                         # the four inputs and the embedding gathered on one line
        ax.plot([1.78, 2.00], [3.65 - k * 0.56] * 2, color=INK, lw=0.9)
    ax.plot([1.78, 2.00], [0.93, 0.93], color=INK, lw=0.9); ax.plot([2.00, 2.00], [0.93, 3.65], color=INK, lw=0.9)
    ax.plot([2.00, xs[3] + cw / 2], [BUS, BUS], color=INK, lw=0.9)

    # ---- the head
    box(5.62, 2.70, 1.62, 0.92, "", fc="white"); ax.text(6.43, 3.42, "Next 6 hours", ha="center", va="center", fontsize=10.5, fontweight="bold")
    ax.text(6.43, 3.03, "forecast wind\nforecast rainfall (HRRR)", ha="center", va="center", fontsize=9.5, color="#55554f", linespacing=1.15)
    box(5.62, 1.72, 1.62, 0.60, "Fully connected\nlayers", fc=LIGHT, fs=10.5)
    arrow(xs[3] + cw, 3.17, 5.44, 3.17); ax.plot([5.44, 5.44], [3.17, 2.02], color=INK, lw=0.9); arrow(5.44, 2.02, 5.62, 2.02)
    arrow(6.43, 2.70, 6.43, 2.32)
    ax.plot([0.95, 0.95], [0.62, 0.40], color=INK, lw=0.9); ax.plot([0.95, 5.30], [0.40, 0.40], color=INK, lw=0.9); ax.plot([5.30, 5.30], [0.40, 1.90], color=INK, lw=0.9); arrow(5.30, 1.90, 5.62, 1.90)
    arrow(6.43, 1.72, 6.43, 1.30)
    box(5.62, 0.66, 1.62, 0.64, "", fc="white", lw=1.3); ax.text(6.43, 1.08, "Water level", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(6.43, 0.85, "t + 1, t + 2, … , t + 6 h", ha="center", va="center", fontsize=9.5, style="italic")
    ax.text(3.15, 0.52, "gauge embedding", ha="center", va="center", fontsize=9.5, color="#55554f")
    ax.text(3.70, 0.14, "Five networks of this form, trained from different random starts; the forecast is their mean.", ha="center", va="center", fontsize=10.5)
    out = OUT / "agu_architecture.png"; fig.savefig(out, dpi=300); plt.close(fig); return out


def read(sid: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = next(p for p in DATA if (p / f"{sid}_fc.csv").exists())
    return pd.read_csv(d / f"{sid}_obs.csv", parse_dates=["time"]), pd.read_csv(d / f"{sid}_fc.csv", parse_dates=["origin", "valid"])


def validation(panels=PANELS, out: Path | None = None, ncol: int = 3, figsize=(12.6, 4.3)) -> Path:
    nrow = int(np.ceil(len(panels) / ncol)); fig, axes = plt.subplots(nrow, ncol, figsize=figsize, gridspec_kw={"wspace": 0.17, "hspace": 0.50}); leads = (1, 3, 6)
    for ax, (sid, w, name, what) in zip(axes.ravel(), panels):
        obs, fc = read(sid); o = obs[obs.window == w].set_index("time").obs; f = fc[(fc.window == w) & fc.valid.isin(o.index)]
        for h in leads:
            g = f[f.lead == h].sort_values("valid"); ax.plot(g.valid, g[KEY], color=LEAD_COL[h], lw=1.2, zorder=4)
        ax.plot(o.index, o.values, color=INK, lw=1.4, zorder=5)
        lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.22 * (hi - lo))
        ax.text(0.025, 0.965, "RMSE   " + "    ".join(f"{h} h: {window_rmse(f, o, KEY, h):.1f} cm" for h in leads), transform=ax.transAxes, va="top", ha="left", fontsize=10, color=INK, zorder=6)
        ax.set_title(name, loc="left", fontsize=11.5, fontweight="bold", pad=17); ax.text(0, 1.035, what, transform=ax.transAxes, ha="left", va="bottom", fontsize=10, color="#55554f")
        ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
        ax.tick_params(labelsize=9.5, length=3, width=0.6); ax.grid(axis="y", color="#e6e6e2", lw=0.5); ax.set_axisbelow(True); ax.margins(x=0.01)
    for ax in axes[:, 0]:
        ax.set_ylabel("Water level (m)", fontsize=10.5)
    for ax in axes.ravel()[len(panels):]:
        ax.axis("off")
    h = [Line2D([], [], color=INK, lw=1.6)] + [Line2D([], [], color=LEAD_COL[k], lw=1.8) for k in leads]
    fig.legend(h, ["Observed"] + [f"Forecast issued {k} h earlier" for k in leads], loc="lower center", ncol=4, frameon=False, fontsize=11, bbox_to_anchor=(0.5, -0.035), columnspacing=2.2)
    out = out or OUT / "agu_validation.png"; fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.04); plt.close(fig); return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(json.dumps(numbers(), indent=1)); print("->", gauges_map()); print("->", architecture()); print("->", validation())


if __name__ == "__main__":
    main()
