"""Figures for the version comparison (deliverable 17): every model version side by side.

  bars     : 6 h RMSE of each version, one panel per station type (pooled RMSE for all stations, median station per type)
  lead     : median RMSE vs lead time for the five main versions, three station types
  stations : one figure per station in deliverables/17_versions/data: two event windows (rows) x five versions (columns),
             observation and the 1-6 h forecast issued at every 00/06/12/18 UTC origin
Stations: operational only (CRMS excluded), >= 720 test samples in every version.
Usage: python versions_figs.py bars | lead | stations
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
# every version in the order it was built: (run, label, usable in real time)
LADDER = [("v3_obs", "Water level only", True),
          ("v3_wind_past", "+ wind, past 72 h", True),
          ("v3_wind", "+ wind, next 6 h (forecast)", True),
          ("v3_wind_q", "+ upstream discharge", True),
          ("v6_wind_q", "discharge from the same river, wind off at 15 inland rivers  [operational]", True),
          ("v7_rain_p15_past", "+ rainfall, past 72 h (observed)", True),
          ("v9_fc1_t45", "+ rainfall, next 6 h from HRRR forecast", True),
          ("v7_rain_p15", "+ rainfall, next 6 h observed  [not available in real time]", False)]
# the five versions drawn at the stations: key in the data files, run, column title, colour (categorical slots 1-5, validated)
MAIN = [("wl", "v3_obs", "Water level only", "#2a78d6"),
        ("wind", "v3_wind", "+ wind", "#eb6834"),
        ("q", "v6_wind_q", "+ upstream discharge\n(current operational)", "#1baf7a"),
        ("rain_fc", "v9_fc1_t45", "+ rainfall, next 6 h\nfrom HRRR forecast", "#eda100"),
        ("rain_obs", "v7_rain_p15", "+ rainfall, next 6 h observed\n(upper bound, not real time)", "#e87ba4")]
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
    fig, axes = plt.subplots(1, len(panels), figsize=(13.0, 3.5), sharey=True, gridspec_kw={"wspace": 0.12})
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


def station_fig(sid: str, title: str) -> Path:
    obs = pd.read_csv(OUT / "data" / f"{sid}_obs.csv", parse_dates=["time"])
    fc = pd.read_csv(OUT / "data" / f"{sid}_fc.csv", parse_dates=["origin", "valid"])
    wins = list(dict.fromkeys(obs.window))
    fig, axes = plt.subplots(len(wins), len(MAIN), figsize=(13.0, 4.9), sharey="row", gridspec_kw={"wspace": 0.12, "hspace": 0.32})
    for i, w in enumerate(wins):
        o = obs[obs.window == w].set_index("time").obs
        f = fc[fc.window == w]
        for j, (key, _, col_title, _) in enumerate(MAIN):
            ax = axes[i, j]
            for org, g in f.groupby("origin"):
                g = g.sort_values("lead")
                t = [org] + list(g.valid); v = [o.get(org, np.nan)] + list(g[key])
                if org < o.index[0]:
                    t, v = t[1:], v[1:]
                ax.plot(t, v, color=BLUE, lw=0.9, zorder=3, solid_capstyle="round")
                ax.plot(t[-1], v[-1], "o", color=BLUE, ms=2.6, zorder=4)
            ax.plot(o.index, o.values, color=INK, lw=1.1, zorder=5)
            if j == len(MAIN) - 1:                      # head-room so the RMSE label never sits on the data (row shares the y axis)
                lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 0.20 * (hi_ - lo_))
            ax.text(0.03, 0.95, f"6 h RMSE {window_rmse(f, o, key):.1f} cm", transform=ax.transAxes, va="top", ha="left", fontsize=8.5, color=INK,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.8), zorder=6)
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
            ax.xaxis.set_minor_locator(mdates.DayLocator())
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
            if i == 0:
                ax.set_title(col_title, loc="left", fontsize=9, linespacing=1.25)
            if j == 0:
                name = w.replace("hurricane ", "Hurricane ").replace("high water", "Highest water outside the hurricane")
                ax.set_ylabel(f"{name}, {o.index[0].year}" + "\n" + "water level (m)", fontsize=8.5, linespacing=1.3)
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], color=INK, lw=1.1), Line2D([], [], color=BLUE, lw=0.9, marker="o", ms=2.6, markevery=[1])],
               ["observed", "forecast for the next 1 to 6 h, issued every 6 h (dot = 6 h ahead)"], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(title, x=0.012, ha="left", fontsize=10.5, y=1.0)
    out = OUT / f"station_{sid}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def stations() -> None:
    scr = pd.read_csv(OUT / "data" / "station_screen.csv", dtype={"station_id": str}).set_index("station_id")
    for f in sorted((OUT / "data").glob("*_fc.csv")):
        sid = f.stem[:-3]; r = scr.loc[sid]
        print("->", station_fig(sid, f"{str(r['name']).title() if str(r['name']).isupper() else r['name']} ({r.source.replace('NOAA_COOPS', 'NOAA')} {sid})"))


def main() -> None:
    import matplotlib.ticker  # noqa: F401
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["bars", "lead", "stations"]); a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "bars":
        print("->", bars())
    elif a.cmd == "lead":
        print("->", lead())
    else:
        stations()


if __name__ == "__main__":
    main()
