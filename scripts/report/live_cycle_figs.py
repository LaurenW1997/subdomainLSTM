"""Figures of one live forecast cycle checked against what was observed afterwards (deliverable 20, deck 17).

Reads deliverables/20_operational_rain/<tag>_{forecast.csv, verification.csv, series.csv}
(forecast.py, verify_cycle.py and cycle_series.py on sv7) and writes into deliverables/17_versions:
  live_<tag>_stations.png   8 stations: observed level before and after the forecast time, the 1-6 h forecast on top
  live_<tag>_scatter.png    all stations: forecast change against observed change at 1, 3 and 6 h lead
Usage: python live_cycle_figs.py --tag 20261111T20 --stations 8771450 8747437 08116850 07387040 08164503 07374000 08117500 08115000
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

from versions_figs import INK, TYPE_COL, TYPE_LAB

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "deliverables" / "20_operational_rain"
OUT = REPO / "deliverables" / "17_versions"
FC = "#d6450c"       # the forecast: the vivid end of the warm ramp used for the 6 h line elsewhere


def stations_fig(tag: str, sids: list[str]) -> Path:
    v = pd.read_csv(SRC / f"{tag}_verification.csv", dtype={"station_id": str}).set_index("station_id")
    s = pd.read_csv(SRC / f"{tag}_series.csv", dtype={"station_id": str}, parse_dates=["time"])
    cycle = pd.Timestamp(pd.read_csv(SRC / f"{tag}_forecast.csv", nrows=1).cycle_utc.iloc[0])
    fig, axes = plt.subplots(2, 4, figsize=(13.0, 5.4), gridspec_kw={"wspace": 0.28, "hspace": 0.58})
    for ax, sid in zip(axes.ravel(), sids):
        o = s[s.station_id == sid].set_index("time").obs_m
        assert o.notna().all(), f"{sid} has missing hours - do not draw it"
        r = v.loc[sid]
        ft = [cycle + pd.Timedelta(hours=h) for h in range(0, 7)]
        fv = [r.last_obs_m] + [r[f"fcst_{h}h_m"] for h in range(1, 7)]
        ax.axvspan(cycle, ft[-1], color="#000000", alpha=0.05, lw=0)
        ax.axvline(cycle, color="#7a7a74", lw=0.6)
        ax.plot(o.index, o.values, color=INK, lw=1.2, zorder=4, label="observed")
        ax.plot(ft, fv, color=FC, lw=1.6, zorder=5, label=f"forecast from {cycle:%H:%M} UTC")
        name = str(r["name"]).title() if str(r["name"]).isupper() else str(r["name"])
        ax.set_title(name + chr(10) + TYPE_LAB.get(r["type"], r["type"]), loc="left", fontsize=8.6, linespacing=1.25)
        e = [abs(r[f"err_{h}h_cm"]) for h in (1, 3, 6)]
        lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.22 * (hi - lo))
        ax.text(0.03, 0.96, f"error (cm)   1 h {e[0]:.1f}   3 h {e[1]:.1f}   6 h {e[2]:.1f}", transform=ax.transAxes, va="top", ha="left", fontsize=8, color=INK,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
        ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
        ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
    for ax in axes[:, 0]:
        ax.set_ylabel("water level (m)")
    h, l = axes[0, 0].get_legend_handles_labels()
    from matplotlib.patches import Patch
    fig.legend(h + [Patch(facecolor="#000000", alpha=0.08)], l + ["the 6 hours that were forecast"], loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    out = OUT / f"live_{tag}_stations.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def scatter_fig(tag: str) -> Path:
    v = pd.read_csv(SRC / f"{tag}_verification.csv", dtype={"station_id": str})
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.3), gridspec_kw={"wspace": 0.24})
    order = ["river / canal", "urban creek (Houston)", "estuary / tidal channel", "lake", "tide gauge", "marsh"]
    for ax, h in zip(axes, (1, 3, 6)):
        x = 100 * (v[f"obs_{h}h_m"] - v.last_obs_m); y = 100 * (v[f"fcst_{h}h_m"] - v.last_obs_m)
        ok = x.notna() & y.notna()
        lim = float(np.ceil(max(x[ok].abs().max(), y[ok].abs().max()) / 10) * 10)
        ax.plot([-lim, lim], [-lim, lim], color="#a3a39c", lw=0.8, zorder=1)
        ax.axhline(0, color="#e3e3df", lw=0.6, zorder=0); ax.axvline(0, color="#e3e3df", lw=0.6, zorder=0)
        for t in order:
            m = ok & (v.type == t)
            ax.scatter(x[m], y[m], s=13, color=TYPE_COL[t], edgecolor="white", linewidth=0.3, zorder=3, label=f"{TYPE_LAB[t]} ({int(m.sum())})" if h == 1 else None)
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
        rmse = float(np.sqrt(((y - x)[ok] ** 2).mean()))
        ax.set_title(f"{h} h ahead:  RMSE {rmse:.1f} cm,  {int(ok.sum())} stations", loc="left", fontsize=10)
        ax.set_xlabel("observed change since forecast time (cm)")
    axes[0].set_ylabel("forecast change (cm)")
    fig.legend(loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, -0.07), handletextpad=0.1, columnspacing=1.4)
    out = OUT / f"live_{tag}_scatter.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return out


def main() -> None:
    import matplotlib.ticker  # noqa: F401
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="prefix of the files in deliverables/20_operational_rain, e.g. 20261112T12 or 20261112T12_mean_of_5")
    ap.add_argument("--stations", nargs="+", required=True)
    a = ap.parse_args()
    print("->", stations_fig(a.tag, a.stations))
    print("->", scatter_fig(a.tag))


if __name__ == "__main__":
    main()
