"""Flood map, figure of the check with observed inputs: the water level at gauges the mapping model was not given.

For each station three lines over the hindcast period of Hurricane Ida: the observations, the numerical model (hindcast) at
the cell of the station, and the mapping model driven by the observations of the other gauges (for a control point: all
control points but this one; for a check station: all control points). Observations are on the level of the numerical
model (offset of the hours before the storm, see observed_inputs.py).
Input : deliverables/35_floodmap/observed_inputs_series.npz, observed_inputs_stations.csv (observed_inputs.py on sv7)
Output: deliverables/35_floodmap/ida_observed_inputs_stations.png
Usage : python observed_inputs_fig.py [--stations ID ...]
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

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
INK, MODEL, MAP = "#1a1a19", "#2a78d6", "#d6690f"
DEFAULT = ["8761724", "8761305", "8761927", "8747437", "07374525", "07374000", "8761955", "301324090382400"]
# Grand Isle, Shell Beach, New Canal, Bay Waveland, Mississippi River at Belle Chasse and at Baton Rouge (control points, left out);
# Carrollton and CRMS0061 near Lake Maurepas (never an input)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--stations", nargs="*", default=DEFAULT); a = ap.parse_args()
    z = np.load(D / "observed_inputs_series.npz"); t = pd.date_range("2021-08-25 00:00", periods=len(z[f"obs_{a.stations[0]}"]), freq="h")      # the hours of the archive
    st = pd.read_csv(D / "observed_inputs_stations.csv", dtype={"station_id": str}).set_index("station_id")
    n = len(a.stations); rows = (n + 1) // 2
    fig, axes = plt.subplots(rows, 2, figsize=(13.0, 2.25 * rows + 0.6), squeeze=False); fig.subplots_adjust(left=0.055, right=0.985, top=0.955, bottom=0.115, wspace=0.13, hspace=0.52)
    for ax, sid in zip(axes.ravel(), a.stations):
        r = st.loc[sid]; o, p, m = z[f"obs_{sid}"], z[f"map_{sid}"], z[f"mod_{sid}"]
        ax.plot(t, m, color=MODEL, lw=1.3); ax.plot(t, p, color=MAP, lw=1.3); ax.plot(t, o, color=INK, lw=1.3)
        how = "left out of the inputs" if r.group.startswith("control") else "never an input"
        ax.set_title(f"{r['name']}  ({r.source.replace('_COOPS', '')} {sid}),  {how}", loc="left", fontsize=10.5, pad=4)
        ax.text(0.012, 0.955, f"RMSE against the observations (m)\nmapping {r.rmse_mapping_m:.2f}    numerical model {r.rmse_hindcast_m:.2f}", transform=ax.transAxes, va="top", fontsize=9.5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.xaxis.set_minor_locator(mdates.DayLocator())
        ax.set_xlim(t[0], t[-1]); ax.grid(axis="y", color="#dcdcda", lw=0.5); ax.tick_params(labelsize=9, length=2.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        lo, hi = np.nanmin([o, p, m]), np.nanmax([o, p, m]); ax.set_ylim(lo - 0.05 * (hi - lo), hi + 0.42 * (hi - lo))
    for ax in axes.ravel()[n:]:
        ax.set_visible(False)
    for ax in axes[:, 0]:
        ax.set_ylabel("water level (m)", fontsize=10)
    h = [plt.Line2D([], [], color=INK, lw=1.5), plt.Line2D([], [], color=MODEL, lw=1.5), plt.Line2D([], [], color=MAP, lw=1.5)]
    fig.legend(h, ["observed", "numerical model (hindcast of Hurricane Ida) at the cell of the station", "mapping model driven by the observations of the other gauges"], loc="lower center", ncol=3, frameon=False, fontsize=10.5)
    fig.text(0.055, 0.045, "25 August to 5 September 2021 (UTC). Observations moved to the level of the numerical model with the offset of the first three days.", fontsize=9.5, color="#555")
    out = D / "ida_observed_inputs_stations.png"; fig.savefig(out, dpi=200); plt.close(fig); print("->", out)


if __name__ == "__main__":
    main()
