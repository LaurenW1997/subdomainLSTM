"""The example of the partner-station idea: the observed water level at Calcasieu Pass and at Lake Charles.

The tide reaches the pass on the coast first and Lake Charles, 52 km inland, later. Two observed lines (6-minute readings
of the live service), each minus its own mean over the days shown, and the delay that brings them closest together.
Input : deliverables/33_partner_live_test/example_tide_levels.csv  (station_id, name, time_utc, level_m)
Output: deliverables/33_partner_live_test/example_tide.png
Usage : python partner_example_fig.py [--begin 2026-11-15T00 --end 2026-11-17T12]
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
D = REPO / "deliverables" / "33_partner_live_test"
BLUE = "#0d3f8a"


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--begin", default="2026-11-15T00"); ap.add_argument("--end", default="2026-11-17T12")
    a = ap.parse_args()
    d = pd.read_csv(D / "example_tide_levels.csv", dtype={"station_id": str}, parse_dates=["time_utc"])
    s = d.pivot(index="time_utc", columns="name", values="level_m").asfreq("6min").interpolate(limit=5)
    p, l = s["Calcasieu Pass"], s["Lake Charles"]
    # delay of Lake Charles behind the pass: the shift with the highest correlation, over all readings of the file
    lags = np.arange(0, 121)                                      # 0 .. 12 h in steps of 6 min
    r = [float(l.corr(p.shift(int(k)))) for k in lags]
    k = int(lags[int(np.argmax(r))]); lag_h = k * 0.1
    w = (s.index >= pd.Timestamp(a.begin)) & (s.index <= pd.Timestamp(a.end))
    pw, lw_ = p[w] - p[w].mean(), l[w] - l[w].mean()
    ratio = float(lw_.std() / pw.std())
    print(f"delay {lag_h:.1f} h, correlation {max(r):.3f} (without shift {r[0]:.3f}), range ratio {ratio:.2f}, {len(s)} readings")

    fig, ax = plt.subplots(figsize=(11.0, 3.3))
    ax.plot(pw.index, pw.values, color=BLUE, lw=1.4, label="Calcasieu Pass, on the coast  (the partner)")
    ax.plot(lw_.index, lw_.values, color=INK, lw=1.4, label="Lake Charles, 52 km inland")
    ax.plot(pw.index + pd.Timedelta(minutes=6 * k), pw.values, color=BLUE, lw=0.9, ls=(0, (3, 2)), alpha=0.75, label=f"Calcasieu Pass, moved {lag_h:.1f} h later")
    ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
    ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
    ax.set_xlim(pd.Timestamp(a.begin) - pd.Timedelta(hours=1), pd.Timestamp(a.end) + pd.Timedelta(hours=1))
    ax.set_ylabel("observed water level\nminus its mean over these days (m)", fontsize=9)
    lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.22 * (hi - lo))
    ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=9.5, handlelength=2.4, columnspacing=1.8, borderaxespad=0.2)
    ax.text(0.995, 0.04, f"Lake Charles follows the pass about {lag_h:.1f} h later  (correlation {max(r):.2f} with that delay, {r[0]:.2f} without)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))
    fig.subplots_adjust(left=0.085, right=0.99, top=0.97, bottom=0.11)
    out = D / "example_tide.png"; fig.savefig(out, dpi=250); plt.close(fig)
    print("->", out)


if __name__ == "__main__":
    main()
