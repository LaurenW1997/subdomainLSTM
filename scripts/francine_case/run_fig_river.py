"""Francine case: the gauges along the Mississippi River, the Ida hindcast and the Francine run side by side, and their numbers.

Rows: the five gauges on the river with a model cell, from Baton Rouge down to the mouth. Columns: the 265 hours of the Ida
hindcast (25 Aug .. 5 Sep 2021) and five days before to five days after the landfall of Francine (6 .. 16 Sep 2024).
The two panels of a row span the same height in metres, so that the size of the signal can be compared between the storms.
Black: observed. Blue: the model at the cell of the gauge, moved by its mean difference from the observations in the window.
Numbers per station and storm: RMSE, mean difference, and the series split into a slow part (25-hour running mean) and the
rest (tide): standard deviation of the tide, range of the slow part, observed and modelled.
Input : --francine _series.npz of run_score.py, --ida ida_hindcast_at_gauges.npz, --dataset DIR, --table config/operational_stations_grid_datum.csv
Output: --out PNG, and beside it _numbers.csv and _fig_data.npz
Usage : python run_fig_river.py --francine FILE --ida FILE --dataset DIR --table FILE --out deliverables/35_floodmap/francine_run_mississippi_river.png
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

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "axes.linewidth": 0.6})
INK, MODEL = "#111111", "#3a7bbf"
SHOW = [("USGS", "07374000", "Baton Rouge"), ("NOAA_COOPS", "8761955", "Carrollton (New Orleans)"), ("USGS", "07374525", "Belle Chasse"), ("NOAA_COOPS", "8760721", "Pilottown"), ("NOAA_COOPS", "8760922", "Pilots Station East, Southwest Pass")]
LANDFALL = pd.Timestamp("2024-09-11 22:00")


def split(x):
    s = pd.Series(x); slow = s.rolling(25, center=True, min_periods=20).mean()
    return slow.to_numpy(), (s - slow).to_numpy()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("francine", "ida", "dataset", "table", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    F = np.load(a.francine, allow_pickle=True); tf = pd.DatetimeIndex(F["time"]); wf = np.asarray((tf >= LANDFALL - pd.Timedelta(days=5)) & (tf <= LANDFALL + pd.Timedelta(days=5))); kf = {(s, i): k for k, (s, i) in enumerate(zip(F["source"], F["station_id"]))}
    I = np.load(a.ida, allow_pickle=True); ti = pd.DatetimeIndex(I["time"]); ki = {(s, i): k for k, (s, i) in enumerate(zip(I["source"], I["station_id"]))}
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; i0 = int(tm.get_indexer([ti[0]])[0]); assert tm[i0 + len(ti) - 1] == ti[-1]
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"].set_index(["source", "station_id"])
    fig, axes = plt.subplots(len(SHOW), 2, figsize=(10.5, 1.75 * len(SHOW) + 0.9), sharex="col"); fd = {}; recs = []
    for n, (src, sid, label) in enumerate(SHOW):
        key = (src, sid); add = tab.loc[key].to_navd88_add_m; add = float(add) if add != "" else 0.0
        P = [("Ida", ti, np.asarray(vals[row[key], i0:i0 + len(ti)], "f8") + add, I["model"][:, ki[key]].astype("f8")), ("Francine", tf[wf], F["observed"][wf, kf[key]].astype("f8"), F["model"][wf, kf[key]].astype("f8"))]; span = 0.0; mid = []
        for c, (storm, t, o, m) in enumerate(P):
            ok = np.isfinite(o) & np.isfinite(m); b = float((m - o)[ok].mean()); ms = m - b; rm = float(np.sqrt(((ms - o)[ok] ** 2).mean())); so, to = split(o); sm, tmo = split(m); k2 = np.isfinite(to) & np.isfinite(tmo)
            ax = axes[n, c]; ax.plot(t, o, color=INK, lw=1.0, zorder=5); ax.plot(t, ms, color=MODEL, lw=1.0, zorder=4)
            lo, hi = np.nanmin(np.r_[o, ms]), np.nanmax(np.r_[o, ms]); span = max(span, hi - lo); mid.append(0.5 * (lo + hi))
            ax.text(0.012, 0.93, label if c == 0 else "", transform=ax.transAxes, va="top", ha="left", fontsize=9.5, fontweight="bold")
            ax.text(0.988, 0.93, f"RMSE {rm:.2f} m   (mean difference {b:+.2f} m taken out)", transform=ax.transAxes, va="top", ha="right", fontsize=8.5)
            ax.grid(True, lw=0.3, color="#cccccc"); ax.tick_params(length=2.5, width=0.5); ax.xaxis.set_major_locator(mdates.DayLocator(interval=2 if c == 0 else 1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.margins(x=0)
            recs.append({"station": label, "storm": storm, "hours": int(ok.sum()), "observed_mean_level_m": float(o[ok].mean()), "mean_difference_model_minus_observed_m": b, "rmse_mean_difference_removed_m": rm,
                         "correlation": float(np.corrcoef(o[ok], m[ok])[0, 1]), "observed_range_m": float(o[ok].max() - o[ok].min()), "tide_std_observed_m": float(np.std(to[k2])), "tide_std_model_m": float(np.std(tmo[k2])),
                         "slow_part_range_observed_m": float(np.nanmax(so[k2]) - np.nanmin(so[k2])), "slow_part_range_model_m": float(np.nanmax(sm[k2]) - np.nanmin(sm[k2]))})
            fd[f"time | {storm}"] = np.asarray(t.strftime("%Y-%m-%d %H:%M")); fd[f"observed | {storm} | {sid}"] = o.astype("f4"); fd[f"model_mean_difference_removed | {storm} | {sid}"] = ms.astype("f4")
        for c in range(2):
            axes[n, c].set_ylim(mid[c] - 0.6 * span, mid[c] + 0.8 * span)
        axes[n, 0].set_ylabel("water level (m)")
    axes[0, 0].set_title("Hurricane Ida hindcast, 25 August to 5 September 2021\nriver flow at Baton Rouge about 10 300 m$^3$/s"); axes[0, 1].set_title("Hurricane Francine run, 6 to 16 September 2024\nriver flow at Baton Rouge about 5 500 m$^3$/s")
    fig.legend([Line2D([], [], color=INK, lw=1.2), Line2D([], [], color=MODEL, lw=1.2)], ["observed", "numerical model at the cell of the gauge"], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.03, 1, 1), h_pad=0.25, w_pad=1.0); fig.savefig(a.out, dpi=200); stem = str(Path(a.out).with_suffix("")); np.savez_compressed(stem + "_fig_data.npz", **fd)
    d = pd.DataFrame(recs); d.to_csv(stem + "_numbers.csv", index=False); pd.set_option("display.width", 250); print(d.round(3).to_string(index=False)); print("->", a.out)


if __name__ == "__main__":
    main()
