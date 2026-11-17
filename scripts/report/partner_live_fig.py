"""Stations of the test on past forecast times (deliverable 33): what was observed and the 1-6 h forecasts of the two models.

One panel per station: the observed hourly level (black) and, from every forecast time (thin grey vertical lines, every
6 h), the forecast for the next 1 to 6 hours of the model without partner stations (blue) and with partner stations
(orange). Both read the same water levels; the observations after a forecast time were fetched afterwards.
Input : deliverables/33_partner_live_test/verification_long.csv (verify_cycles.py)
Output: deliverables/33_partner_live_test/stations.png
Usage : python partner_live_fig.py [--stations 07374000 8767816 ...] [--models "no partners" "partners"]
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
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "33_partner_live_test"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9.5, "axes.titlesize": 10.5, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, INK = "#2a78d6", "#eb6834", "#1a1a19"
DEFAULT = ["07374000", "8767816", "07387040", "08075500", "07381515", "08068500", "08073700", "07378000"]
TYPE = {"tide gauge": "tide gauge", "estuary / tidal channel": "estuary", "lake": "lake", "marsh": "marsh", "river / canal": "river", "urban creek (Houston)": "urban creek"}
LAB = {"no partners": "Scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models (the version that is run)",
       "partners": "With partner stations (by measured tide and upstream direction), mean of 5 models",
       "no partners, USGS 1 h late": "The version that is run, newest hour of the USGS gauges removed", "partners, USGS 1 h late": "With partner stations, newest hour of the USGS gauges removed"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", nargs="+", default=DEFAULT); ap.add_argument("--models", nargs=2, default=["no partners", "partners"])
    ap.add_argument("--out", default=str(D / "stations.png")); ap.add_argument("--src", default=str(D / "verification_long.csv"))
    a = ap.parse_args()
    d = pd.read_csv(a.src, dtype={"station_id": str})
    d["cycle_utc"] = pd.to_datetime(d.cycle_utc); d["last_obs_utc"] = pd.to_datetime(d.last_obs_utc, format="mixed")
    n = len(a.stations); ncol = 2; nrow = -(-n // ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(13.0, 2.75 * nrow + 0.7), squeeze=False)
    for ax, sid in zip(axes.ravel(), a.stations):
        x = d[d.station_id == sid]
        assert len(x), f"no station {sid}"
        ref = x[x.model == a.models[0]].sort_values("cycle_utc")
        obs = {}
        for r in ref.itertuples():                                   # every observed hour once: the hour of each forecast time and the six hours after it
            if pd.notna(r.last_obs_m) and r.last_obs_utc == r.cycle_utc:
                obs[r.cycle_utc] = r.last_obs_m
            for h in range(1, 7):
                v = getattr(r, f"obs_{h}h_m")
                if pd.notna(v):
                    obs[r.cycle_utc + pd.Timedelta(hours=h)] = v
        o = pd.Series(obs).sort_index().asfreq("1h")
        for c in ref.cycle_utc:
            ax.axvline(c, color="#d0cfc8", lw=0.6, zorder=1)
        rm = {}
        for m, col in zip(a.models, (BLUE, ORANGE)):
            y = x[x.model == m].sort_values("cycle_utc")
            for r in y.itertuples():
                t = [r.last_obs_utc] + [r.cycle_utc + pd.Timedelta(hours=h) for h in range(1, 7)]
                v = [r.last_obs_m] + [getattr(r, f"fcst_{h}h_m") for h in range(1, 7)]
                ax.plot(t, v, color=col, lw=1.25, zorder=4 if m == a.models[1] else 3, solid_capstyle="round")
            s = y[y.scored]
            rm[m] = float(np.sqrt((s.err_6h_cm ** 2).mean())) if len(s) else np.nan
        ax.plot(o.index, o.to_numpy(), color=INK, lw=1.7, zorder=2)
        r0 = ref.iloc[0]
        ax.set_title(f"{r0['name']}  ({TYPE.get(r0.type, r0.type)}; measured: {r0.behaviour})", loc="left", pad=14)
        ax.text(0.0, 1.015, f"6 h RMSE of the {int(x[(x.model == a.models[0]) & x.scored].shape[0])} forecasts:  {rm[a.models[0]]:.1f} cm without partner stations,  {rm[a.models[1]]:.1f} cm with",
                transform=ax.transAxes, fontsize=9.5, color=INK, va="bottom")
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H UTC"))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 18]))
        ax.set_ylabel("water level (m)"); ax.grid(axis="y", color="#ecebe6", lw=0.6); ax.set_axisbelow(True)
        ax.margins(x=0.01)
    for ax in axes.ravel()[n:]:
        ax.set_visible(False)
    h = [Line2D([], [], color=INK, lw=1.7), Line2D([], [], color=BLUE, lw=1.6), Line2D([], [], color=ORANGE, lw=1.6), Line2D([], [], color="#b9b8b0", lw=0.8)]
    fig.legend(h, ["Observed", LAB.get(a.models[0], a.models[0]), LAB.get(a.models[1], a.models[1]), "Forecast times (every 6 h); each coloured line is the forecast for the next 1 to 6 hours"],
               loc="upper left", ncol=1, frameon=False, bbox_to_anchor=(0.045, 1.0), fontsize=10, handlelength=2.4)
    fig.subplots_adjust(left=0.055, right=0.972, top=1 - (1.25 / (2.75 * nrow + 0.7)), bottom=0.055, hspace=0.62, wspace=0.14)
    fig.savefig(a.out, dpi=200); plt.close(fig)
    print("->", a.out)


if __name__ == "__main__":
    main()
