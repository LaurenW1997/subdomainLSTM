"""Figures for the version comparison (deliverable 17): every model version side by side.

  bars     : 6 h RMSE of each version, one panel per station type (pooled RMSE for all stations, median station per type)
  lead     : median RMSE vs lead time for the six main versions, three station types
  maps     : 6 h RMSE at every station for the six main versions, and the change at every station for three steps
  stations : one figure per station in deliverables/17_versions/data: two event windows (rows) x six versions (columns),
             observation and the forecast valid at each hour for 1, 3 and 6 h lead (continuous lines, hourly origins)
Stations: operational only (CRMS excluded), >= 720 test samples in every version.
Usage: python versions_figs.py bars | lead | maps | stations
Also writes deliverables/17_versions/versions_table.csv (bars) for the slides.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "deliverables" / "17_versions"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
                     "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 9, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREY, INK = "#2a78d6", "#a3a39c", "#1a1a19"
# every version in the order it was built: (run, label, usable in real time).
# "6 h-change scaling + gap filling" = gaps filled with the last valid value + change and loss scaled half-way to the station's 6 h change + change-unit input channel
LADDER = [("v3_obs", "Water level only", True),
          ("v3_wind_past", "+ wind, past 72 h", True),
          ("v3_wind", "+ wind, next 6 h (forecast)", True),
          ("v3_wind_q", "+ upstream discharge", True),
          ("v6_wind_q", "discharge from the same river, wind off at 15 inland rivers", True),
          ("v7_rain_p15_past", "+ rainfall of the past 72 h only", True),
          ("v9_fc1_t45", "+ rainfall: past 72 h and HRRR forecast for the next 6 h", True),
          ("v7_rain_p15", "+ rainfall: past 72 h and observed next 6 h  [not available in real time]", False),
          ("v10_dnorm_x_p50", "no rainfall; error scaled by the 6 h change, gaps filled with the last observation", True),
          ("v11_fc1_t45", "scaling + gap filling + rainfall: past 72 h and HRRR forecast for the next 6 h", True),
          ("v14_stale25", "scaling + gap filling + rainfall (past 72 h, HRRR next 6 h), trained with missing hours", True),
          ("v11_rain_obs", "scaling + gap filling + rainfall: past 72 h and observed next 6 h  [not available in real time]", False)]
CURRENT, CURRENT_KEY = "v14_stale25", "base_fc"          # the version in use; drawn in bold / highlighted everywhere
HILITE = "#fbe3d3"
# the six versions drawn at the stations: key in the data files, run, column title, colour (categorical slots 1-6, validated)
MAIN = [("wl", "v3_obs", "Water level only", "#2a78d6"),
        ("wind", "v3_wind", "Water level + wind", "#eb6834"),
        ("q", "v6_wind_q", "Water level + wind\n+ discharge\n(no rainfall)", "#1baf7a"),
        ("base", "v10_dnorm_x_p50", "6 h-change scaling,\ngap filling\n(no rainfall)", "#eda100"),
        ("base_fc", "v14_stale25", "6 h-change scaling,\ngap filling + HRRR rainfall,\ntrained with missing hours", "#e87ba4"),
        ("base_obs", "v11_rain_obs", "6 h-change scaling,\ngap filling + observed rainfall\n(upper bound, not real time)", "#008300")]
TYPES = [("tide gauge", "Tide gauges"), ("estuary / tidal channel", "Estuaries"), ("lake", "Lakes"),
         ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks (Houston)")]


def load_runs(runs: list[str], min_n: int = 720) -> dict[str, pd.DataFrame]:
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    d = {r: pd.read_csv(REPO / "runs" / r / "per_station_test.csv", dtype={"station_id": str}) for r in runs}
    ref = d[runs[0]]
    ok = (ref.source != "CRMS").to_numpy()
    for r in runs:
        assert (d[r].station_id.to_numpy() == ref.station_id.to_numpy()).all(), r
        ok &= d[r].n_6h.to_numpy() >= min_n
    typ = ref[["source", "station_id"]].merge(g[["source", "station_id", "type", "name"]], on=["source", "station_id"], how="left")
    out = {}
    for r in runs:
        x = d[r][ok].copy(); x["type"] = typ.type.to_numpy()[ok]; x["name"] = typ["name"].to_numpy()[ok]; out[r] = x
    return out


def pooled(x: pd.DataFrame, h: int = 6) -> float:
    return float(np.sqrt((x.n_6h * x[f"rmse_{h}h_cm"] ** 2).sum() / x.n_6h.sum()))


def bars() -> Path:
    d = load_runs([r for r, _, _ in LADDER])
    n_all = len(next(iter(d.values())))
    panels = [("all", f"All stations (n = {n_all})", "RMSE over all forecasts")] + [(t, f"{lab} (n = {(d['v3_obs'].type == t).sum()})", "median station") for t, lab in TYPES]
    rows = []
    for r, lab, rt in LADDER:
        row = {"run": r, "version": lab, "real_time": rt, "all": pooled(d[r])}
        for t, _ in TYPES:
            row[t] = float(d[r][d[r].type == t].rmse_6h_cm.median())
        rows.append(row)
    tab = pd.DataFrame(rows); tab["n_stations"] = n_all
    OUT.mkdir(parents=True, exist_ok=True); tab.to_csv(OUT / "versions_table.csv", index=False)
    fig, axes = plt.subplots(1, len(panels), figsize=(13.0, 4.5), sharey=True, gridspec_kw={"wspace": 0.12})
    y = np.arange(len(LADDER))[::-1]
    for ax, (key, title, sub) in zip(axes, panels):
        v = tab[key].to_numpy()
        yc = y[list(tab.run).index(CURRENT)]
        ax.axhspan(yc - 0.5, yc + 0.5, color=HILITE, lw=0, zorder=0)
        ax.barh(y, v, height=0.62, color=[BLUE if rt else GREY for rt in tab.real_time], edgecolor="none")
        for yy, vv in zip(y, v):
            ax.text(vv + v.max() * 0.03, yy, f"{vv:.1f}", va="center", ha="left", fontsize=8.5, color=INK)
        ax.set_xlim(0, v.max() * 1.25); ax.set_title(title + "\n" + sub, loc="left", fontsize=9, linespacing=1.3)
        ax.set_yticks(y); ax.set_yticklabels(tab.version, fontsize=9)
        for lbl, r_ in zip(ax.get_yticklabels(), tab.run):
            if r_ == CURRENT:
                lbl.set_fontweight("bold")
        ax.tick_params(axis="y", length=0); ax.grid(axis="x", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
        ax.set_xlabel("6 h RMSE (cm)")
    out = OUT / "versions_bars.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    print(tab.drop(columns=["run"]).round(2).to_string(index=False))
    return out


def lead() -> Path:
    d = load_runs([r for _, r, _, _ in MAIN])
    leads = np.arange(1, 7)
    sel = [("tide gauge", "Tide gauges"), ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks (Houston)")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6), gridspec_kw={"wspace": 0.22})
    for ax, (t, lab) in zip(axes, sel):
        for key, r, title, col in MAIN:
            x = d[r][d[r].type == t]
            ax.plot(leads, [x[f"rmse_{h}h_cm"].median() for h in leads], color=col, lw=3.0 if key == CURRENT_KEY else 1.6, marker="o", ms=5.5 if key == CURRENT_KEY else 3.5,
                    zorder=5 if key == CURRENT_KEY else 3, label=title.replace("\n", " "))
        ax.set_title(f"{lab} (n = {(d['v3_obs'].type == t).sum()})", loc="left"); ax.set_xticks(leads); ax.set_xlabel("Lead time (h)")
        ax.set_ylim(bottom=0); ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
    axes[0].set_ylabel("RMSE (cm), median station")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.16))
    out = OUT / "versions_lead.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


LEAD_COL = {1: "#f6cdb8", 3: "#ee9468", 6: "#d6450c"}        # one warm hue, pale -> vivid with lead time; the 6 h line must stand apart from the black observation


def window_rmse(fc: pd.DataFrame, obs: pd.Series, key: str, lead_h: int = 6) -> float:
    x = fc[(fc.lead == lead_h) & fc.valid.isin(obs.index)]
    e = x[key].to_numpy() - obs.reindex(x.valid).to_numpy()
    e = e[np.isfinite(e)]
    return float(np.sqrt((e ** 2).mean()) * 100) if len(e) else np.nan


def station_fig(sid: str, title: str, whole: dict | None = None, vers: list | None = None, figsize=(13.0, 4.9), out: Path | None = None,
                data_dir: Path | None = None, bold_key: str | None = None) -> Path:
    """Two event windows (rows) x versions (columns). Black: observation. Blue lines, light to dark: the forecast valid at
    each hour that was issued 1, 3 and 6 h earlier (hourly origins). Grey band: 24 h around the observed peak."""
    data_dir = data_dir or OUT / "data"
    obs = pd.read_csv(data_dir / f"{sid}_obs.csv", parse_dates=["time"])
    fc = pd.read_csv(data_dir / f"{sid}_fc.csv", parse_dates=["origin", "valid"])
    wins = list(dict.fromkeys(obs.window))
    vers = vers or MAIN
    leads = (1, 3, 6)
    fig, axes = plt.subplots(len(wins), len(vers), figsize=figsize, sharey="row", gridspec_kw={"wspace": 0.12, "hspace": 0.32})
    for i, w in enumerate(wins):
        o = obs[obs.window == w].set_index("time").obs
        f = fc[(fc.window == w) & fc.valid.isin(o.index)]
        pk = o.idxmax()
        for j, (key, _, col_title, _) in enumerate(vers):
            ax = axes[i, j]
            ax.axvspan(pk - pd.Timedelta(hours=12), pk + pd.Timedelta(hours=12), color="#000000", alpha=0.05, lw=0)
            for h in leads:
                g = f[f.lead == h].sort_values("valid")
                ax.plot(g.valid, g[key], color=LEAD_COL[h], lw=0.9, zorder=4, label=f"{h} h ahead")
            ax.plot(o.index, o.values, color=INK, lw=1.1, zorder=5, label="observed")
            if j == len(vers) - 1:                      # head-room so the RMSE label never sits on the data (row shares the y axis)
                lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 0.30 * (hi_ - lo_))
            ax.text(0.03, 0.96, "RMSE (cm)" + "\n" + "   ".join(f"{h} h {window_rmse(f, o, key, h):.1f}" for h in leads), transform=ax.transAxes, va="top", ha="left",
                    fontsize=7.8, color=INK, linespacing=1.25, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
            ax.xaxis.set_minor_locator(mdates.DayLocator())
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
            if i == 0:
                extra = "" if not whole else "\n" + f"whole test period, 6 h: {whole[key]:.1f} cm"
                ax.set_title(col_title + extra, loc="left", fontsize=8.8, linespacing=1.25, fontweight="bold" if (key == bold_key or (key == CURRENT_KEY and len(vers) > 3)) else "normal")
            if j == 0:
                name = w.replace("hurricane ", "Hurricane ").replace("high water", "Highest water outside the hurricane")
                ax.set_ylabel(f"{name}, {o.index[0].year}" + "\n" + "water level (m)", fontsize=8.5, linespacing=1.3)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=INK, lw=1.1)] + [Line2D([], [], color=LEAD_COL[h], lw=1.2) for h in leads]
    fig.legend(handles, ["observed"] + [f"forecast issued {h} h earlier" for h in leads], loc="lower center", ncol=4 if len(vers) > 2 else 2, frameon=False,
               bbox_to_anchor=(0.5, (-0.01 if len(vers) > 3 else -0.04) if len(vers) > 2 else -0.07))
    fig.suptitle(title, x=0.012, ha="left", fontsize=10.5, y=1.0)
    out = out or OUT / f"station_{sid}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def stations() -> None:
    scr = pd.read_csv(OUT / "data" / "station_screen.csv", dtype={"station_id": str}).set_index("station_id")
    per = load_runs([r for _, r, _, _ in MAIN])
    for f in sorted((OUT / "data").glob("*_fc.csv")):
        sid = f.stem[:-3]; r = scr.loc[sid]
        whole = {k: float(per[run].loc[per[run].station_id == sid, "rmse_6h_cm"].iloc[0]) for k, run, _, _ in MAIN}
        print("->", station_fig(sid, f"{str(r['name']).title() if str(r['name']).isupper() else r['name']} ({r.source.replace('NOAA_COOPS', 'NOAA')} {sid})", whole))


REF_VERS = [("base", "v10_dnorm_x_p50", "6 h-change scaling,\ngap filling", ""),
            ("ds", "v13_ds", "+ water level at the next\ngauge downstream", ""),
            ("ds_us", "v13_ds_us", "+ next gauge downstream\nand next gauge upstream", "")]


def refgauge(sid: str = "08076700", name: str = "Greens Bayou at Ley Rd, Houston, TX") -> Path:
    """One station that has a gauge upstream on the same river: forecasts without and with the reference-gauge inputs."""
    per = load_runs([r for _, r, _, _ in REF_VERS])
    whole = {k: float(per[run].loc[per[run].station_id == sid, "rmse_6h_cm"].iloc[0]) for k, run, _, _ in REF_VERS}
    return station_fig(sid, f"{name} (USGS {sid})", whole, vers=REF_VERS, figsize=(7.6, 4.9), out=OUT / f"refgauge_{sid}.png",
                       data_dir=REPO / "deliverables" / "19_reference_gauge" / "data_lag")


EXTENT = [-99.3, -88.0, 25.6, 31.4]
SEQ = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]            # one hue, light -> dark (magnitude)
DIV = ["#104281", "#3987e5", "#9ec5f4", "#d6d5cf", "#f3b08f", "#eb6834", "#9c3a12"]   # blue = better, grey = no change, orange = worse


def _base(ax):
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
    ax.add_feature(cf.LAND, facecolor="#f4f4f1"); ax.add_feature(cf.COASTLINE, lw=0.4, edgecolor="#7a7a74")
    ax.add_feature(cf.STATES, lw=0.3, edgecolor="#a3a39c")
    for sp in ax.spines.values():
        sp.set_linewidth(0.5); sp.set_edgecolor("#7a7a74")


# one colour per station type, the same in every figure (categorical slots in fixed order)
TYPE_COL = {"tide gauge": "#2a78d6", "estuary / tidal channel": "#1baf7a", "lake": "#eda100", "river / canal": "#eb6834",
            "urban creek (Houston)": "#e87ba4", "marsh": "#008300"}
TYPE_LAB = {"tide gauge": "Tide gauge", "estuary / tidal channel": "Estuary / tidal channel", "lake": "Lake", "river / canal": "River",
            "urban creek (Houston)": "Urban creek (Houston)", "marsh": "Marsh"}
DOMAINS = [("Louisiana100m", -94.11, -88.39, 28.74, 31.14), ("Texas100m", -99.03, -95.24, 25.85, 29.13), ("Galveston100m", -96.71, -94.04, 28.74, 31.16)]


def stationmap() -> Path:
    """Where the stations are: (a) all stations the model is trained on, (b) the stations with a real-time feed, which are
    the ones a forecast is issued for. Same colours in both panels; the three 100 m model domains as boxes."""
    import cartopy.crs as ccrs
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    st = pd.read_csv(REPO / "runs" / "v6_wind_q" / "stations.csv", dtype={"station_id": str})
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    st = st.merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left")
    rt = st.source.isin(["USGS", "NOAA_COOPS"])
    pc = ccrs.PlateCarree()
    fig = plt.figure(figsize=(13.0, 4.6))
    panels = [(st, f"(a) Training: {len(st)} stations  (USGS {int((st.source == 'USGS').sum())}, NOAA {int((st.source == 'NOAA_COOPS').sum())}, "
                   f"CRMS {int((st.source == 'CRMS').sum())}, USACE {int((st.source == 'USACE_MVN').sum())})"),
              (st[rt], f"(b) Forecast in real time: {int(rt.sum())} stations  (USGS {int((st.source == 'USGS').sum())}, NOAA {int((st.source == 'NOAA_COOPS').sum())})")]
    for k, (x, title) in enumerate(panels):
        ax = fig.add_subplot(1, 2, k + 1, projection=pc); _base(ax)
        for name, x0, x1, y0, y1 in DOMAINS:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="#52524e", lw=0.8, ls=(0, (4, 2)), transform=pc, zorder=3))
            ax.text(x0 + 0.08, y0 + 0.08, name, transform=pc, fontsize=8, color="#52524e", ha="left", va="bottom", zorder=6,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.0, alpha=0.8))
        for t in ["marsh", "river / canal", "urban creek (Houston)", "estuary / tidal channel", "lake", "tide gauge"]:      # rarer types on top
            y = x[x.type == t]
            ax.scatter(y.lon, y.lat, s=11, color=TYPE_COL[t], edgecolor="white", linewidth=0.25, transform=pc, zorder=5)
        ax.set_title(title, loc="left", fontsize=10)
    order = ["tide gauge", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)", "marsh"]
    h = [Line2D([], [], marker="o", ls="", markerfacecolor=TYPE_COL[t], markeredgecolor="white", markeredgewidth=0.3, markersize=6.5) for t in order]
    lab = [f"{TYPE_LAB[t]}  ({int((st.type == t).sum())} / {int(((st.type == t) & rt).sum())})" for t in order]
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.17, wspace=0.03)
    fig.legend(h, lab, loc="lower center", ncol=6, frameon=False, fontsize=9.5, handletextpad=0.2, columnspacing=1.5, bbox_to_anchor=(0.5, 0.045))
    fig.text(0.5, 0.012, "Numbers in the legend: stations used for training / stations forecast in real time.  Dashed boxes: the three 100 m model domains.",
             ha="center", fontsize=9, color=INK)
    out = OUT / "stations_map.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def maps() -> tuple[Path, Path]:
    """(1) 6 h RMSE at every station for the six main versions; (2) change at every station for four steps."""
    import cartopy.crs as ccrs
    from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
    d = load_runs([r for _, r, _, _ in MAIN])
    pc = ccrs.PlateCarree()
    n = len(next(iter(d.values())))
    # ---- (1) absolute RMSE, one map per version
    # Six classes with boundaries where the stations are (half of them lie between 2.5 and 7.5 cm), one hue light -> dark,
    # and a marker that grows with the class: a station that moves to another class changes both colour and size.
    from matplotlib.colors import BoundaryNorm, ListedColormap
    edges = [0, 2.5, 5, 7.5, 10, 20, 1e9]
    cols = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]      # wide steps at the low end, where most stations are
    sizes = np.array([7, 10, 14, 19, 27, 38])
    labels = ["< 2.5", "2.5 - 5", "5 - 7.5", "7.5 - 10", "10 - 20", "> 20"]
    cmap = ListedColormap(cols); norm = BoundaryNorm(edges, cmap.N)
    names = {"wl": "Water level only", "wind": "Water level + wind", "q": "Water level + wind + discharge (no rainfall)",
             "base": "6 h-change scaling + gap filling (no rainfall)",
             "base_fc": "Scaling + gap filling + HRRR rainfall, trained with missing hours",
             "base_obs": "Scaling + gap filling + observed rainfall (upper bound, not real time)"}
    fig = plt.figure(figsize=(13.0, 6.5))
    for k, (key, run, title, _) in enumerate(MAIN):
        ax = fig.add_subplot(2, 3, k + 1, projection=pc); _base(ax)
        x = d[run].sort_values("rmse_6h_cm")
        cls = np.clip(np.digitize(x.rmse_6h_cm.to_numpy(), edges[1:-1]), 0, len(cols) - 1)
        ax.scatter(x.lon, x.lat, c=[cols[c] for c in cls], s=sizes[cls], edgecolor="#1a1a19", linewidth=0.2, transform=pc, zorder=5)
        n10 = int((x.rmse_6h_cm > 10).sum()); n5 = int((x.rmse_6h_cm < 5).sum())
        ax.set_title(names[key], loc="left", fontsize=9.5, fontweight="bold" if key == CURRENT_KEY else "normal", pad=16)
        ax.text(0.0, 1.02, f"{n10} stations above 10 cm, {n5} below 5 cm", transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color=INK)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.12, wspace=0.03, hspace=0.24)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", markerfacecolor=c, markeredgecolor="#1a1a19", markeredgewidth=0.3, markersize=np.sqrt(sz) * 1.15) for c, sz in zip(cols, sizes)]
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(0.10, 0.015), ncol=6, frameon=False, fontsize=10, handletextpad=0.2, columnspacing=1.6,
               title="6 h RMSE (cm), January 2024 to December 2025", title_fontsize=10)
    fig.text(0.62, 0.05, f"{n} USGS and NOAA stations (CRMS excluded)." + "\n" + "Darker and larger = larger error; stations with larger error drawn on top.", fontsize=9.5, va="center", linespacing=1.4)
    out1 = OUT / "versions_map_rmse.png"
    fig.savefig(out1, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    # ---- (2) change maps
    # every panel against the same base, water level only, so that the four maps can be compared with each other
    steps = [("v6_wind_q", "v3_obs", "(a) Water level + wind + upstream discharge"),
             ("v10_dnorm_x_p50", "v3_obs", "(b) 6 h-change scaling + gap filling, no rainfall"),
             ("v14_stale25", "v3_obs", "(c) Scaling + gap filling + HRRR rainfall, trained with missing hours"),
             ("v11_rain_obs", "v3_obs", "(d) Scaling + gap filling + observed rainfall (upper bound, not real time)")]
    cmap = LinearSegmentedColormap.from_list("div", DIV); norm = Normalize(-5, 5)
    fig = plt.figure(figsize=(13.0, 6.6))
    for k, (a, b, title) in enumerate(steps):
        ax = fig.add_subplot(2, 2, k + 1, projection=pc); _base(ax)
        diff = d[a].rmse_6h_cm.to_numpy() - d[b].rmse_6h_cm.to_numpy()
        o = np.argsort(np.abs(diff))
        sc = ax.scatter(d[a].lon.to_numpy()[o], d[a].lat.to_numpy()[o], c=np.clip(diff[o], -5, 5), s=16, cmap=cmap, norm=norm, edgecolor="#1a1a19", linewidth=0.15, transform=pc, zorder=5)
        ax.set_title(title + "\n" + f"{(diff <= -0.5).sum()} stations better, {(diff >= 0.5).sum()} worse by 0.5 cm or more", loc="left", fontsize=10.5, linespacing=1.3, fontweight="bold" if a == CURRENT else "normal")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.12, wspace=0.03, hspace=0.2)
    cax = fig.add_axes([0.30, 0.06, 0.40, 0.022])
    cb = fig.colorbar(sc, cax=cax, orientation="horizontal", extend="both", ticks=[-5, -2.5, 0, 2.5, 5]); cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(labelsize=10); cb.set_label("6 h RMSE minus that of water level only (cm): blue = smaller error, orange = larger error", fontsize=10.5)
    out2 = OUT / "versions_map_change.png"
    fig.savefig(out2, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out1, out2


def detail_btr() -> Path:
    """Mississippi River at Baton Rouge (USGS 07374000): 6 h-ahead forecast of the water-level-only and the operational
    version, valid at every hour, in three 4-day periods. Input: data/btr_07374000_series.csv (hourly, from sv7)."""
    d = pd.read_csv(OUT / "data" / "btr_07374000_series.csv", parse_dates=["time"]).set_index("time")
    wins = [("2024-01-07", "(a) Storm surge reaching Baton Rouge at low river stage"),
            ("2024-11-01", "(b) Low river: the tide is visible at Baton Rouge"),
            ("2025-04-30", "(c) High river: slow and smooth")]
    series = [("wl", "Water level only", "#2a78d6"), ("oper", "Water level + wind + upstream discharge", "#1baf7a")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.5), gridspec_kw={"wspace": 0.2})
    for ax, (t0, title) in zip(axes, wins):
        w = d.loc[pd.Timestamp(t0):pd.Timestamp(t0) + pd.Timedelta(days=4)]
        ax.plot(w.index, w.obs, color=INK, lw=1.2, label="observed", zorder=5)
        txt = []
        for key, lab, col in series:
            ax.plot(w.index, w[key], color=col, lw=1.3, label=lab + ", 6 h ahead", zorder=4)
            txt.append(f"{lab.split(' (')[0].split(' + ')[-1] if key == 'oper' else 'water level only'}: {np.sqrt(((w[key] - w.obs) ** 2).mean()) * 100:.1f} cm")
        ax.set_title(f"{title}" + "\n" + f"6 h RMSE  water level only {np.sqrt(((w.wl - w.obs) ** 2).mean()) * 100:.1f} cm,  water level + wind + discharge {np.sqrt(((w.oper - w.obs) ** 2).mean()) * 100:.1f} cm",
                     loc="left", fontsize=9, linespacing=1.35)
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
        ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
        lo_, hi_ = w.obs.min(), w.obs.max(); pad = max(0.08, 0.15 * (hi_ - lo_)); ax.set_ylim(min(lo_, w.wl.min(), w.oper.min()) - pad, max(hi_, w.wl.max(), w.oper.max()) + pad)
        ax.text(0.02, 0.03, f"{w.index[0].year}", transform=ax.transAxes, fontsize=8.5, color="#55554f")
    axes[0].set_ylabel("Water level (m, NAVD88)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle("Mississippi River at Baton Rouge, LA (USGS 07374000)", x=0.012, ha="left", fontsize=10.5, y=1.06)
    out = OUT / "detail_07374000.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def explain() -> Path:
    """Mississippi River at Baton Rouge for the slide that explains the 6 h-change scaling and gap filling: water level + wind + discharge,
    those inputs with scaling and gap filling, and scaling + gap filling + HRRR rainfall trained with missing hours (the model that is run).
    Data: deliverables/17_versions/data_btr (extract_versions_hourly.py on sv7, keys q, base, inuse)."""
    runs = [("q", "v6_wind_q", "Water level + wind" + "\n" + "+ discharge"),
            ("base", "v10_dnorm_x_p50", "Water level + wind + discharge," + "\n" + "6 h-change scaling, gap filling"),
            ("inuse", "v14_stale25", "Scaling + gap filling + HRRR rainfall," + "\n" + "trained with missing hours")]
    whole = {}
    for k, run, _ in runs:
        d_ = pd.read_csv(REPO / "runs" / run / "per_station_test.csv", dtype={"station_id": str})
        whole[k] = float(d_.loc[d_.station_id == "07374000", "rmse_6h_cm"].iloc[0])
    vers = [(k, run, title, None) for k, run, title in runs]
    return station_fig("07374000", "Mississippi River at Baton Rouge, LA (USGS 07374000)", whole, vers=vers, figsize=(9.4, 4.9), out=OUT / "explain_scaling.png",
                       data_dir=OUT / "data_btr", bold_key="inuse")


def main() -> None:
    import matplotlib.ticker  # noqa: F401
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["bars", "lead", "stations", "maps", "btr", "explain", "refgauge", "stationmap"]); a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "bars":
        print("->", bars())
    elif a.cmd == "lead":
        print("->", lead())
    elif a.cmd == "maps":
        print("->", maps())
    elif a.cmd == "btr":
        print("->", detail_btr())
    elif a.cmd == "explain":
        print("->", explain())
    elif a.cmd == "refgauge":
        print("->", refgauge())
    elif a.cmd == "stationmap":
        print("->", stationmap())
    else:
        stations()


if __name__ == "__main__":
    main()
