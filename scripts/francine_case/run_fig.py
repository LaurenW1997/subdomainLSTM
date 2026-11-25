"""Francine case: station figure, the Ida hindcast and the Francine run side by side against the observed water level.

Rows: the five fixed stations of Louisiana100m and three more along the coast, west to east. Columns: the 265 hours of the Ida
hindcast (25 Aug .. 5 Sep 2021) and the 265 hours of the Francine run placed the same way around the landfall (7 .. 18 Sep 2024).
Black: observed. Blue: the model at the cell chosen for the gauge, moved by its mean difference from the observations in the
window (the model has its own zero), so that the shape is compared; the mean difference taken out is written in the panel.
Input : --francine _series.npz of run_score.py, --ida ida_hindcast_at_gauges.npz, --dataset DIR, --table config/operational_stations_grid_datum.csv
Output: --out PNG and, beside it, _fig_data.npz with the plotted series
Usage : python run_fig.py --francine FILE --ida FILE --dataset DIR --table FILE --out deliverables/35_floodmap/francine_run_at_gauges_stations.png
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
SHOW = [("NOAA_COOPS", "8768094", "Calcasieu Pass"), ("USGS", "07387050", "Vermilion Bay"), ("NOAA_COOPS", "8764227", "Amerada Pass"), ("USGS", "07381590", "Wax Lake Outlet at Calumet"),
        ("USGS", "07374000", "Mississippi R. at Baton Rouge"), ("NOAA_COOPS", "8761927", "New Canal Station"), ("NOAA_COOPS", "8761724", "Grand Isle"), ("NOAA_COOPS", "8761305", "Shell Beach")]
STORM = ("2024-09-07 00:00", "2024-09-18 00:00")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("francine", "ida", "dataset", "table", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    F = np.load(a.francine, allow_pickle=True); tf = pd.DatetimeIndex(F["time"]); wf = np.asarray((tf >= STORM[0]) & (tf <= STORM[1])); kf = {(s, i): k for k, (s, i) in enumerate(zip(F["source"], F["station_id"]))}
    I = np.load(a.ida, allow_pickle=True); ti = pd.DatetimeIndex(I["time"]); ki = {(s, i): k for k, (s, i) in enumerate(zip(I["source"], I["station_id"]))}
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; i0 = int(tm.get_indexer([ti[0]])[0]); assert tm[i0 + len(ti) - 1] == ti[-1]
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"].set_index(["source", "station_id"])
    fig, axes = plt.subplots(len(SHOW), 2, figsize=(10.5, 1.55 * len(SHOW) + 0.9), sharex="col"); fd = {}
    for n, (src, sid, label) in enumerate(SHOW):
        key = (src, sid); add = tab.loc[key].to_navd88_add_m; add = float(add) if add != "" else 0.0
        P = [(ti, np.asarray(vals[row[key], i0:i0 + len(ti)], "f8") + add, I["model"][:, ki[key]].astype("f8")), (tf[wf], F["observed"][wf, kf[key]].astype("f8"), F["model"][wf, kf[key]].astype("f8"))]; span = 0.0; mid = []
        for c, (t, o, m) in enumerate(P):
            ok = np.isfinite(o) & np.isfinite(m); b = float((m - o)[ok].mean()) if ok.sum() >= 48 else np.nan; ms = m - b; rm = float(np.sqrt(((ms - o)[ok] ** 2).mean())) if ok.sum() >= 48 else np.nan
            ax = axes[n, c]; ax.plot(t, o, color=INK, lw=1.0, zorder=5); ax.plot(t, ms, color=MODEL, lw=1.0, zorder=4)
            lo, hi = np.nanmin(np.r_[o, ms]), np.nanmax(np.r_[o, ms]); span = max(span, hi - lo); mid.append(0.5 * (lo + hi))
            ax.text(0.012, 0.9, label if c == 0 else "", transform=ax.transAxes, va="top", ha="left", fontsize=9.5, fontweight="bold")
            ax.text(0.988, 0.9, f"RMSE {rm:.2f} m   (mean difference {b:+.2f} m taken out)", transform=ax.transAxes, va="top", ha="right", fontsize=8.5)
            ax.grid(True, lw=0.3, color="#cccccc"); ax.tick_params(length=2.5, width=0.5); ax.xaxis.set_major_locator(mdates.DayLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.margins(x=0)
            fd[f"time | {'Ida' if c == 0 else 'Francine'}"] = np.asarray(t.strftime("%Y-%m-%d %H:%M")); fd[f"observed | {'Ida' if c == 0 else 'Francine'} | {sid}"] = o.astype("f4"); fd[f"model_mean_difference_removed | {'Ida' if c == 0 else 'Francine'} | {sid}"] = ms.astype("f4")
        for c in range(2):
            axes[n, c].set_ylim(mid[c] - 0.62 * span, mid[c] + 0.78 * span)
        axes[n, 0].set_ylabel("water level (m)")
    axes[0, 0].set_title("Hurricane Ida hindcast, 25 August to 5 September 2021"); axes[0, 1].set_title("Hurricane Francine run, 7 to 18 September 2024")
    fig.legend([Line2D([], [], color=INK, lw=1.2), Line2D([], [], color=MODEL, lw=1.2)], ["observed", "numerical model at the cell of the gauge"], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.025, 1, 1), h_pad=0.25, w_pad=1.0); fig.savefig(a.out, dpi=200); np.savez_compressed(str(Path(a.out).with_suffix("")) + "_fig_data.npz", **fd); print("->", a.out)


if __name__ == "__main__":
    main()
