"""One station, one or more forecast cycles from the real-time services next to what was observed (deliverable 20).

Reads deliverables/20_operational_rain/<tag>_{forecast.csv, series.csv} for every tag (forecast.py and cycle_series.py on
sv7); one panel per cycle: observed level before and after the forecast time, the 1-6 h forecast, and - when the forecast
is a mean of several models - the lowest and highest member. Hours not observed yet are simply not drawn.
Usage: python live_station_fig.py --station 07374000 --tags 20261114T09_mean_of_5 20261114T15_mean_of_5 --out 20261114_baton_rouge_mean_of_5.png
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

from versions_figs import INK  # also sets the figure style (Times New Roman, thin axes)

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "deliverables" / "20_operational_rain"
FC, BAND = "#d6450c", "#f6cdb8"      # forecast: vivid end of the warm ramp; range of the members: its pale end


def main() -> None:
    import matplotlib.ticker  # noqa: F401
    ap = argparse.ArgumentParser()
    ap.add_argument("--station", required=True); ap.add_argument("--tags", nargs="+", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--hours-before", type=int, default=24)
    a = ap.parse_args()
    fig, axes = plt.subplots(1, len(a.tags), figsize=(6.3 * len(a.tags), 3.9), sharey=True, gridspec_kw={"wspace": 0.08}, squeeze=False)
    name = datum = ""
    for k, (ax, tag) in enumerate(zip(axes[0], a.tags)):
        f = pd.read_csv(SRC / f"{tag}_forecast.csv", dtype={"station_id": str}).set_index("station_id").loc[a.station]
        assert f.status == "ok", f"{tag}: no forecast at {a.station} ({f.status})"
        s = pd.read_csv(SRC / f"{tag}_series.csv", dtype={"station_id": str}, parse_dates=["time"])
        o = s[s.station_id.str.lstrip("0") == a.station.lstrip("0")].set_index("time").obs_m
        cycle = pd.Timestamp(f.cycle_utc); name, datum = str(f["name"]), str(f.datum)
        o = o[o.index >= cycle - pd.Timedelta(hours=a.hours_before)]
        ft = [cycle + pd.Timedelta(hours=h) for h in range(0, 7)]
        fv = np.array([f.last_obs_m] + [f[f"fcst_{h}h_m"] for h in range(1, 7)], float)
        ax.axvspan(cycle, ft[-1], color="#000000", alpha=0.05, lw=0)
        ax.axvline(cycle, color="#7a7a74", lw=0.6)
        if "member_min_1h_m" in f.index and np.isfinite(f.member_min_1h_m):
            lo = [f.last_obs_m] + [f[f"member_min_{h}h_m"] for h in range(1, 7)]; hi = [f.last_obs_m] + [f[f"member_max_{h}h_m"] for h in range(1, 7)]
            ax.fill_between(ft, lo, hi, color=BAND, lw=0, zorder=3, label="lowest to highest of the 5 models")
        ax.plot(ft, fv, color=FC, lw=1.8, marker="o", ms=3.2, zorder=5, label="forecast, mean of 5 models")
        ax.plot(o.index, o.values, color=INK, lw=1.3, marker="o", ms=2.2, zorder=6, label="observed")
        e = {h: round(100 * (fv[h] - o.get(ft[h], np.nan)), 1) + 0.0 for h in range(1, 7)}       # + 0.0: no "-0.0" in the label
        seen = [h for h in range(1, 7) if np.isfinite(e[h])]
        if len(seen) == 6:
            note = "error (cm)   " + "   ".join(f"{h} h {e[h]:+.1f}" for h in range(1, 7))
        else:
            note = "error (cm)   " + ("   ".join(f"{h} h {e[h]:+.1f}" for h in seen) if seen else "") + f"   hours {len(seen) + 1} to 6 not observed yet"
        ax.set_title(f"({'ab'[k] if k < 2 else k + 1}) Forecast from {cycle:%H:%M} UTC, {cycle.day} {cycle:%B %Y}" + "\n" + note, loc="left", fontsize=9.5, linespacing=1.4)
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18])); ax.xaxis.set_minor_locator(mdates.HourLocator())
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x):%H}:00" + ("\n" + f"{mdates.num2date(x).day} {mdates.num2date(x):%b}" if mdates.num2date(x).hour == 0 else "")))
        ax.set_xlim(cycle - pd.Timedelta(hours=a.hours_before), ft[-1] + pd.Timedelta(minutes=30))
        ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.set_xlabel("time (UTC)")
    axes[0, 0].set_ylabel(f"water level (m, {datum})")
    h, l = axes[0, 0].get_legend_handles_labels()
    from matplotlib.patches import Patch
    order = [l.index("observed"), l.index("forecast, mean of 5 models")] + ([l.index("lowest to highest of the 5 models")] if "lowest to highest of the 5 models" in l else [])
    fig.legend([h[i] for i in order] + [Patch(facecolor="#000000", alpha=0.08)], [l[i] for i in order] + ["the 6 hours that are forecast"], loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, -0.09))
    nice = name.title() if name.isupper() else name
    fig.suptitle(f"{nice} (USGS {a.station})", x=0.012, ha="left", fontsize=10.5, y=1.06)
    out = SRC / a.out
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    print("->", out)


if __name__ == "__main__":
    main()
