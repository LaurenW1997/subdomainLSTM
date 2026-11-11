"""Figures for the version comparison (deliverable 17): every model version side by side.

  bars     : 6 h RMSE of each version, one panel per station type (pooled RMSE for all stations, median station per type)
  lead     : median RMSE vs lead time for the six main versions, three station types
  maps     : 6 h RMSE at every station for the six main versions, and the change at every station for three steps
  stations : one figure per station in deliverables/17_versions/data: two event windows (rows) x six versions (columns),
             observation and the 1-6 h forecast issued at every 00/06/12/18 UTC origin
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
          ("v6_wind_q", "discharge from the same river, wind off at 15 inland rivers  [operational]", True),
          ("v7_rain_p15_past", "+ rainfall, past 72 h (observed)", True),
          ("v9_fc1_t45", "+ rainfall, next 6 h from HRRR forecast", True),
          ("v7_rain_p15", "+ rainfall, next 6 h observed  [not available in real time]", False),
          ("v10_dnorm_x_p50", "operational inputs; error scaled by the 6 h change, gaps filled with the last observation", True),
          ("v11_fc1_t45", "the same + rainfall, next 6 h from HRRR forecast", True),
          ("v11_rain_obs", "the same + rainfall, next 6 h observed  [not available in real time]", False)]
# the six versions drawn at the stations: key in the data files, run, column title, colour (categorical slots 1-6, validated)
MAIN = [("wl", "v3_obs", "Water level only", "#2a78d6"),
        ("wind", "v3_wind", "+ wind", "#eb6834"),
        ("q", "v6_wind_q", "+ upstream discharge\n(current operational)", "#1baf7a"),
        ("base", "v10_dnorm_x_p50", "operational inputs with\n6 h-change scaling,\ngap filling", "#eda100"),
        ("base_fc", "v11_fc1_t45", "6 h-change scaling,\ngap filling + rainfall\nfrom HRRR forecast", "#e87ba4"),
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
        ax.barh(y, v, height=0.62, color=[BLUE if rt else GREY for rt in tab.real_time], edgecolor="none")
        for yy, vv in zip(y, v):
            ax.text(vv + v.max() * 0.03, yy, f"{vv:.1f}", va="center", ha="left", fontsize=8.5, color=INK)
        ax.set_xlim(0, v.max() * 1.25); ax.set_title(title + "\n" + sub, loc="left", fontsize=9, linespacing=1.3)
        ax.set_yticks(y); ax.set_yticklabels(tab.version, fontsize=9)
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
            ax.plot(leads, [x[f"rmse_{h}h_cm"].median() for h in leads], color=col, lw=1.8, marker="o", ms=4, label=title.replace("\n", " "))
        ax.set_title(f"{lab} (n = {(d['v3_obs'].type == t).sum()})", loc="left"); ax.set_xticks(leads); ax.set_xlabel("Lead time (h)")
        ax.set_ylim(bottom=0); ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
    axes[0].set_ylabel("RMSE (cm), median station")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.16))
    out = OUT / "versions_lead.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def window_rmse(fc: pd.DataFrame, obs: pd.Series, key: str, lead_h: int = 6) -> float:
    x = fc[fc.lead == lead_h]
    e = x[key].to_numpy() - obs.reindex(x.valid).to_numpy()
    e = e[np.isfinite(e)]
    return float(np.sqrt((e ** 2).mean()) * 100) if len(e) else np.nan


def station_fig(sid: str, title: str, whole: dict | None = None, vers: list | None = None, figsize=(13.0, 4.9), out: Path | None = None) -> Path:
    obs = pd.read_csv(OUT / "data" / f"{sid}_obs.csv", parse_dates=["time"])
    fc = pd.read_csv(OUT / "data" / f"{sid}_fc.csv", parse_dates=["origin", "valid"])
    wins = list(dict.fromkeys(obs.window))
    vers = vers or MAIN
    fig, axes = plt.subplots(len(wins), len(vers), figsize=figsize, sharey="row", gridspec_kw={"wspace": 0.12, "hspace": 0.32})
    for i, w in enumerate(wins):
        o = obs[obs.window == w].set_index("time").obs
        f = fc[fc.window == w]
        for j, (key, _, col_title, _) in enumerate(vers):
            ax = axes[i, j]
            for org, g in f.groupby("origin"):
                g = g.sort_values("lead")
                t = [org] + list(g.valid); v = [o.get(org, np.nan)] + list(g[key])
                if org < o.index[0]:
                    t, v = t[1:], v[1:]
                ax.plot(t, v, color=BLUE, lw=0.9, zorder=3, solid_capstyle="round")
                ax.plot(t[-1], v[-1], "o", color=BLUE, ms=2.6, zorder=4)
            ax.plot(o.index, o.values, color=INK, lw=1.1, zorder=5)
            if j == len(vers) - 1:                      # head-room so the RMSE label never sits on the data (row shares the y axis)
                lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 0.20 * (hi_ - lo_))
            ax.text(0.03, 0.95, f"6 h RMSE {window_rmse(f, o, key):.1f} cm", transform=ax.transAxes, va="top", ha="left", fontsize=8.5, color=INK,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.8), zorder=6)
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
            ax.xaxis.set_minor_locator(mdates.DayLocator())
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
            if i == 0:
                extra = "" if not whole else "\n" + f"whole test period: {whole[key]:.1f} cm"
                ax.set_title(col_title + extra, loc="left", fontsize=8.8, linespacing=1.25)
            if j == 0:
                name = w.replace("hurricane ", "Hurricane ").replace("high water", "Highest water outside the hurricane")
                ax.set_ylabel(f"{name}, {o.index[0].year}" + "\n" + "water level (m)", fontsize=8.5, linespacing=1.3)
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], color=INK, lw=1.1), Line2D([], [], color=BLUE, lw=0.9, marker="o", ms=2.6, markevery=[1])],
               ["observed", "forecast for the next 1 to 6 h, issued every 6 h (dot = 6 h ahead)"], loc="lower center", ncol=2 if len(vers) > 2 else 1, frameon=False, bbox_to_anchor=(0.5, -0.01 if len(vers) > 2 else -0.07))
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


def maps() -> tuple[Path, Path]:
    """(1) 6 h RMSE at every station for the six main versions; (2) change at every station for four steps."""
    import cartopy.crs as ccrs
    from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
    d = load_runs([r for _, r, _, _ in MAIN])
    pc = ccrs.PlateCarree()
    n = len(next(iter(d.values())))
    # ---- (1) absolute RMSE, one map per version
    cmap = LinearSegmentedColormap.from_list("seq", SEQ); norm = LogNorm(1, 40)
    fig = plt.figure(figsize=(13.0, 6.0))
    for k, (key, run, title, _) in enumerate(MAIN):
        ax = fig.add_subplot(2, 3, k + 1, projection=pc); _base(ax)
        x = d[run].sort_values("rmse_6h_cm")
        sc = ax.scatter(x.lon, x.lat, c=x.rmse_6h_cm.clip(1, 40), s=11, cmap=cmap, norm=norm, edgecolor="#1a1a19", linewidth=0.15, transform=pc, zorder=5)
        ax.set_title(title.replace("\n", " ") + f"   —   {(x.rmse_6h_cm > 10).sum()} above 10 cm", loc="left", fontsize=9)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.13, wspace=0.03, hspace=0.12)
    cax = fig.add_axes([0.20, 0.07, 0.28, 0.025])
    cb = fig.colorbar(sc, cax=cax, orientation="horizontal", ticks=[1, 2, 5, 10, 20, 40]); cb.ax.set_xticklabels(["1", "2", "5", "10", "20", "40"])
    cb.set_label("6 h RMSE (cm), January 2024 to December 2025"); cb.outline.set_linewidth(0.5)
    fig.text(0.53, 0.085, f"{n} operational stations (CRMS excluded)." + "\n" + "Darker = larger error; stations with larger error drawn on top.", fontsize=9, va="center", linespacing=1.4)
    out1 = OUT / "versions_map_rmse.png"
    fig.savefig(out1, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    # ---- (2) change maps
    steps = [("v6_wind_q", "v3_obs", "(a) Wind and upstream discharge: operational minus water level only"),
             ("v10_dnorm_x_p50", "v6_wind_q", "(b) 6 h-change scaling and gap filling, same inputs, minus operational"),
             ("v11_fc1_t45", "v6_wind_q", "(c) 6 h-change scaling, gap filling + HRRR rainfall, minus operational"),
             ("v11_rain_obs", "v6_wind_q", "(d) 6 h-change scaling, gap filling + observed rainfall (upper bound), minus operational")]
    cmap = LinearSegmentedColormap.from_list("div", DIV); norm = Normalize(-5, 5)
    fig = plt.figure(figsize=(13.0, 6.6))
    for k, (a, b, title) in enumerate(steps):
        ax = fig.add_subplot(2, 2, k + 1, projection=pc); _base(ax)
        diff = d[a].rmse_6h_cm.to_numpy() - d[b].rmse_6h_cm.to_numpy()
        o = np.argsort(np.abs(diff))
        sc = ax.scatter(d[a].lon.to_numpy()[o], d[a].lat.to_numpy()[o], c=np.clip(diff[o], -5, 5), s=16, cmap=cmap, norm=norm, edgecolor="#1a1a19", linewidth=0.15, transform=pc, zorder=5)
        ax.set_title(title + "\n" + f"{(diff <= -0.5).sum()} stations better, {(diff >= 0.5).sum()} worse by 0.5 cm or more", loc="left", fontsize=10.5, linespacing=1.3)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.12, wspace=0.03, hspace=0.2)
    cax = fig.add_axes([0.30, 0.06, 0.40, 0.022])
    cb = fig.colorbar(sc, cax=cax, orientation="horizontal", extend="both", ticks=[-5, -2.5, 0, 2.5, 5]); cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(labelsize=10); cb.set_label("change in 6 h RMSE (cm): blue = smaller error, orange = larger error", fontsize=10.5)
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
    series = [("wl", "Water level only", "#2a78d6"), ("oper", "Water level + wind + upstream discharge (operational)", "#1baf7a")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.5), gridspec_kw={"wspace": 0.2})
    for ax, (t0, title) in zip(axes, wins):
        w = d.loc[pd.Timestamp(t0):pd.Timestamp(t0) + pd.Timedelta(days=4)]
        ax.plot(w.index, w.obs, color=INK, lw=1.2, label="observed", zorder=5)
        txt = []
        for key, lab, col in series:
            ax.plot(w.index, w[key], color=col, lw=1.3, label=lab + ", 6 h ahead", zorder=4)
            txt.append(f"{lab.split(' (')[0].split(' + ')[-1] if key == 'oper' else 'water level only'}: {np.sqrt(((w[key] - w.obs) ** 2).mean()) * 100:.1f} cm")
        ax.set_title(f"{title}" + "\n" + f"6 h RMSE  water level only {np.sqrt(((w.wl - w.obs) ** 2).mean()) * 100:.1f} cm,  operational {np.sqrt(((w.oper - w.obs) ** 2).mean()) * 100:.1f} cm",
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
    """Before / after picture for the slide that explains the 6 h-change scaling and gap filling: Mississippi River at Baton Rouge."""
    per = load_runs([MAIN[2][1], MAIN[3][1]])
    whole = {k: float(per[run].loc[per[run].station_id == "07374000", "rmse_6h_cm"].iloc[0]) for k, run in (("q", MAIN[2][1]), ("base", MAIN[3][1]))}
    vers = [("q", MAIN[2][1], "Operational version", None),
            ("base", MAIN[3][1], "Same inputs, error scaled by the 6 h change," + "\n" + "gaps filled with the last observation", None)]
    return station_fig("07374000", "Mississippi River at Baton Rouge, LA (USGS 07374000)", whole, vers=vers, figsize=(6.6, 4.9), out=OUT / "explain_scaling.png")


def main() -> None:
    import matplotlib.ticker  # noqa: F401
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["bars", "lead", "stations", "maps", "btr", "explain"]); a = ap.parse_args()
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
    else:
        stations()


if __name__ == "__main__":
    main()
