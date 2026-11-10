"""Publication-style figures (deliverable 11).

  station  : one station, three 4-day windows side by side; observation + forecasts valid at each hour for
             1 h, 3 h and 6 h lead (continuous lines), 24 h around the window peak shaded; RMSE in a corner box.
             Input: deliverables/11_figures/data/<prefix>_<station>.csv from extract_windows.py.
  lead     : RMSE vs lead time (1-6 h) by station type, median and interquartile band, with and without
             wind + discharge inputs. Input: runs/*/per_station_test.csv + config/station_groups.csv.
Usage:
  python paper_figs.py station deliverables/11_figures/data/la_8747437.csv --title "Bay Waveland, Mississippi Sound (NOAA 8747437)"
  python paper_figs.py lead
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.ticker
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "deliverables" / "11_figures"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
                     "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.spines.top": False, "axes.spines.right": False})
LEAD_COL = {1: "#9ecae1", 3: "#3182bd", 6: "#08306b"}
TYPE_ORDER = ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]
TYPE_LABEL = {"tide gauge": "tide gauge", "marsh": "marsh (USGS)", "estuary / tidal channel": "estuary / tidal channel", "lake": "lake",
              "river / canal": "river", "urban creek (Houston)": "urban creek (Houston)"}
TYPE_COL = {"tide gauge": "#0072B2", "marsh": "#009E73", "estuary / tidal channel": "#CC79A7", "lake": "#56B4E9", "river / canal": "#E69F00", "urban creek (Houston)": "#D55E00"}
WIN_LABEL = {"hurricane": "Hurricane", "high water": "High water", "normal": "Normal"}


def rmse(a, b):
    d = (a - b).dropna()
    return float(np.sqrt((d ** 2).mean())) * 100 if len(d) else np.nan


def station_fig(csv: Path, title: str, out: Path | None = None, leads=(1, 3, 6)) -> Path:
    df = pd.read_csv(csv, parse_dates=["time"])
    wins = list(dict.fromkeys(df.window))
    fig, axes = plt.subplots(1, len(wins), figsize=(12.5, 3.6))
    for k, (ax, w) in enumerate(zip(np.atleast_1d(axes), wins)):
        d = df[df.window == w].set_index("time")
        # shade 24 h around the peak
        if d.obs.notna().any():
            pk = d.obs.idxmax(); ax.axvspan(pk - pd.Timedelta(hours=12), pk + pd.Timedelta(hours=12), color="#000000", alpha=0.05, lw=0)
        ax.plot(d.index, d.obs, color="k", lw=1.0, label="observed", zorder=5)
        for h in leads:
            ax.plot(d.index, d[f"f{h}"], color=LEAD_COL[h], lw=0.9, label=f"{h} h ahead", zorder=4)
        kind = next((x for x in WIN_LABEL if w.startswith(x)), w)
        name = w.replace("hurricane ", "").replace(" (highest level outside the hurricane)", "").replace(" (typical 4 days)", "")
        label = f"Hurricane {name}" if kind == "hurricane" else WIN_LABEL[kind]
        t0, t1 = d.index[0], d.index[-1]
        span = f"{t0.day} {t0:%b}–{t1.day} {t1:%b %Y}"
        txt = "RMSE " + ", ".join(f"{h} h {rmse(d[f'f{h}'], d.obs):.1f}" for h in leads) + " cm"
        ax.set_title(f"({'abc'[k]}) {label}, {span}" + "\n" + txt, loc="left", fontsize=9, linespacing=1.4)
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))
        ax.grid(axis="y", color="#dddddd", lw=0.5); ax.set_axisbelow(True)
        if k == 0:
            ax.set_ylabel("Water level (m)")
    handles, labels = np.atleast_1d(axes)[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.suptitle(title, x=0.012, ha="left", fontsize=10.5, y=1.03)
    out = out or OUT / f"station_{csv.stem.split('_', 1)[1]}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def lead_fig(run_a: str = "v6_wind_q", run_b: str = "v3_obs", min_n: int = 720, label_a: str | None = None, label_b: str | None = None) -> Path:
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    a = pd.read_csv(REPO / "runs" / run_a / "per_station_test.csv", dtype={"station_id": str})
    b = pd.read_csv(REPO / "runs" / run_b / "per_station_test.csv", dtype={"station_id": str})
    ok = (a.n_6h >= min_n) & (b.n_6h >= min_n) & (a.source != "CRMS")   # CRMS stations are training-only (not operational)
    a, b = a[ok].merge(g[["source", "station_id", "type"]], on=["source", "station_id"]), b[ok].merge(g[["source", "station_id", "type"]], on=["source", "station_id"])
    leads = np.arange(1, 7)
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    for t in TYPE_ORDER:
        sa, sb = a[a.type == t], b[b.type == t]
        if len(sa) < 5:
            continue
        med = [sa[f"rmse_{h}h_cm"].median() for h in leads]
        q1 = [sa[f"rmse_{h}h_cm"].quantile(.25) for h in leads]; q3 = [sa[f"rmse_{h}h_cm"].quantile(.75) for h in leads]
        medb = [sb[f"rmse_{h}h_cm"].median() for h in leads]
        ax.fill_between(leads, q1, q3, color=TYPE_COL[t], alpha=0.08, lw=0)
        ax.plot(leads, med, color=TYPE_COL[t], lw=1.6, marker="o", ms=3.2, label=f"{TYPE_LABEL[t]} (n = {len(sa)})")
        ax.plot(leads, medb, color=TYPE_COL[t], lw=1.0, ls=(0, (3, 2)), alpha=0.9)
    ax.set_yscale("log"); ax.set_yticks([1, 2, 5, 10, 20, 40]); ax.set_yticklabels(["1", "2", "5", "10", "20", "40"])
    ax.set_xticks(leads); ax.set_xlabel("Lead time (h)"); ax.set_ylabel("RMSE (cm), median over stations")
    ax.grid(axis="y", color="#dddddd", lw=0.5, which="both"); ax.set_axisbelow(True)
    from matplotlib.lines import Line2D
    h1, l1 = ax.get_legend_handles_labels()
    extra = [Line2D([], [], color="k", lw=1.6, marker="o", ms=3.2), Line2D([], [], color="k", lw=1.0, ls=(0, (3, 2)))]
    leg1 = ax.legend(h1, l1, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, title="station type" + "\n" + "(band: interquartile range)", title_fontsize=8.5, alignment="left")
    ax.add_artist(leg1)
    leg2 = ax.legend(extra, [(label_a or "water level + wind | + upstream discharge").replace(" | ", "\n"), (label_b or "water level only").replace(" | ", "\n")], loc="upper left", bbox_to_anchor=(1.01, 0.38), frameon=False, title="inputs", title_fontsize=8.5, alignment="left")
    ax.set_title(f"Test period Jan 2024 – Dec 2025, {len(a)} stations (CRMS marsh stations excluded)", loc="left")
    fig.tight_layout()
    out = OUT / "rmse_vs_lead.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05, bbox_extra_artists=[leg1, leg2]); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05, bbox_extra_artists=[leg1, leg2]); plt.close(fig)
    return out


def map_fig(run: str = "v6_wind_q", min_n: int = 720, rep: Path | None = None, label: str | None = None) -> Path:
    """All test stations coloured by 6 h RMSE; representative stations outlined."""
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    from matplotlib.colors import LogNorm
    a = pd.read_csv(REPO / "runs" / run / "per_station_test.csv", dtype={"station_id": str})
    a = a[(a.n_6h >= min_n) & (a.source != "CRMS")]   # CRMS stations are training-only (not operational)
    doms = {"Louisiana100m": (-94.11, -88.39, 28.74, 31.14), "Texas100m": (-99.03, -95.24, 25.85, 29.13), "Galveston100m": (-96.71, -94.04, 28.74, 31.16)}
    fig = plt.figure(figsize=(11, 4.8))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([-99.3, -88.0, 25.6, 31.4])
    ax.add_feature(cf.LAND, facecolor="#f3f3f3"); ax.add_feature(cf.COASTLINE, lw=.5); ax.add_feature(cf.STATES, lw=.35, edgecolor="#888888")
    for dom, (x0, x1, y0, y1) in doms.items():
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="k", lw=.7, ls=(0, (4, 3)), transform=ccrs.PlateCarree())
        ax.text(x0 + .08, y1 - .1, dom, fontsize=9, va="top", transform=ccrs.PlateCarree())
    a = a.sort_values("rmse_6h_cm")
    sc = ax.scatter(a.lon, a.lat, c=a.rmse_6h_cm.clip(1, 40), s=12, cmap="viridis", norm=LogNorm(1, 40), edgecolor="none", transform=ccrs.PlateCarree(), zorder=5)
    if rep is not None and rep.exists():
        r = pd.read_csv(rep, dtype={"station_id": str})
        ax.scatter(r.lon, r.lat, s=60, facecolor="none", edgecolor="k", lw=0.9, marker="s", transform=ccrs.PlateCarree(), zorder=6, label=f"{len(r)} representative stations")
        ax.legend(loc="lower right", frameon=False)
    cb = fig.colorbar(sc, ax=ax, shrink=.8, pad=.015, ticks=[1, 2, 5, 10, 20, 40]); cb.ax.set_yticklabels(["1", "2", "5", "10", "20", "40"])
    cb.set_label("6 h RMSE (cm), Jan 2024 – Dec 2025")
    ax.set_title(f"{len(a)} stations (CRMS excluded), LSTM with {label or 'water level, wind and upstream discharge'}", loc="left")
    fig.tight_layout()
    out = OUT / "rmse_map.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def box_fig(run_a: str = "v6_wind_q", run_b: str = "v3_obs", min_n: int = 720, label_a: str | None = None, label_b: str | None = None) -> Path:
    """Per-station 6 h RMSE by station type, with and without wind + discharge."""
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    a = pd.read_csv(REPO / "runs" / run_a / "per_station_test.csv", dtype={"station_id": str})
    b = pd.read_csv(REPO / "runs" / run_b / "per_station_test.csv", dtype={"station_id": str})
    ok = (a.n_6h >= min_n) & (b.n_6h >= min_n) & (a.source != "CRMS")   # CRMS stations are training-only (not operational)
    a, b = a[ok].merge(g[["source", "station_id", "type"]], on=["source", "station_id"]), b[ok].merge(g[["source", "station_id", "type"]], on=["source", "station_id"])
    types = [t for t in TYPE_ORDER if (a.type == t).sum() >= 5]
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    pos = np.arange(len(types))
    for off, df, fc, lab in ((-0.18, b, "white", (label_b or "water level only").replace(" | ", " ")), (0.18, a, "#4d4d4d", (label_a or "water level + wind + upstream discharge").replace(" | ", " "))):
        data = [df[df.type == t].rmse_6h_cm.to_numpy() for t in types]
        bp = ax.boxplot(data, positions=pos + off, widths=0.3, showfliers=False, patch_artist=True,
                        medianprops=dict(color="k" if fc == "white" else "white", lw=1.2), boxprops=dict(facecolor=fc, color="k", lw=0.7),
                        whiskerprops=dict(color="k", lw=0.7), capprops=dict(color="k", lw=0.7))
        bp["boxes"][0].set_label(lab)
    ax.set_yscale("log"); ax.set_yticks([1, 2, 5, 10, 20, 50]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50"])
    ax.set_xticks(pos); ax.set_xticklabels([TYPE_LABEL[t] + "\n" + f"(n = {(a.type == t).sum()})" for t in types])
    ax.set_ylabel("6 h RMSE (cm), per station"); ax.grid(axis="y", color="#dddddd", lw=0.5, which="both"); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title(f"Test period Jan 2024 – Dec 2025, {len(a)} stations (CRMS excluded); box = interquartile range, whiskers = 1.5 IQR, outliers hidden", loc="left")
    fig.tight_layout()
    out = OUT / "rmse_box_by_type.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("station"); s.add_argument("csv"); s.add_argument("--title", default=""); s.add_argument("--out")
    for name in ("lead", "map", "box"):       # model pair and legend labels (" | " = line break in the lead-time legend)
        q = sub.add_parser(name); q.add_argument("--run-a", default="v6_wind_q"); q.add_argument("--run-b", default="v3_obs")
        q.add_argument("--label-a"); q.add_argument("--label-b")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "station":
        print("->", station_fig(Path(a.csv), a.title, Path(a.out) if a.out else None))
    elif a.cmd == "lead":
        print("->", lead_fig(a.run_a, a.run_b, label_a=a.label_a, label_b=a.label_b))
    elif a.cmd == "map":
        print("->", map_fig(a.run_a, rep=REPO / "deliverables" / "10_representative" / "stations.csv", label=a.label_a))
    else:
        print("->", box_fig(a.run_a, a.run_b, label_a=a.label_a, label_b=a.label_b))


if __name__ == "__main__":
    main()
