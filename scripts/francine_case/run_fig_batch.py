"""Francine case: station figures for all gauges that can check the run, with the difference of datum taken into account.

Which gauges: those whose model cell followed the gauge in the hindcast of Hurricane Ida (correlation at least --min-ida-r there),
that is, chosen from another storm and not from this run. Every one of them is drawn, also those where the Francine run fails.
When: five days before to five days after the landfall (2024-09-11 22:00 UTC). The weeks before belong to the spin-up of the
cold start and are not used, neither for the scores nor for the datum.
Difference of datum: the model has its own zero and the gauges theirs, so for every station the model is moved by its mean
difference from the observations in these ten days.
Black: observed (NAVD88 where the datum of the station is known, else the datum of the station). Blue: the model at the cell of the gauge.
Input : --series, --stations (_series.npz and _stations.csv of run_score.py)
Output: --out PREFIX: _1.png, _2.png, ... (14 stations a page, west to east), _stations.csv (datum difference, RMSE, highest level per station), _fig_data.npz
Usage : python run_fig_batch.py --series FILE --stations FILE --out deliverables/35_floodmap/francine_run_validation
"""
from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "axes.linewidth": 0.6})
INK, MODEL = "#111111", "#3a7bbf"
LANDFALL, DAYS, MIN_HOURS, PER_PAGE, NCOL = pd.Timestamp("2024-09-11 22:00"), 5, 180, 14, 2


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--series", required=True); ap.add_argument("--stations", required=True); ap.add_argument("--out", required=True); ap.add_argument("--min-ida-r", type=float, default=0.8); a = ap.parse_args()
    z = np.load(a.series, allow_pickle=True); t = pd.DatetimeIndex(z["time"]); k = {(s, i): n for n, (s, i) in enumerate(zip(z["source"], z["station_id"]))}
    w = np.asarray((t >= LANDFALL - pd.Timedelta(days=DAYS)) & (t <= LANDFALL + pd.Timedelta(days=DAYS))); tv = t[w]; print(f"window {tv[0]} .. {tv[-1]}, {int(w.sum())} hours")
    d = pd.read_csv(a.stations, dtype={"station_id": str}); d = d[d.ida_r >= a.min_ida_r].sort_values("lon")
    enough = [int((np.isfinite(z["observed"][w, k[(r.source, r.station_id)]]) & np.isfinite(z["model"][w, k[(r.source, r.station_id)]])).sum()) >= MIN_HOURS for r in d.itertuples()]
    print("left out for too few observed hours in the window:", d[~np.array(enough)].name.tolist()); d = d[np.array(enough)].reset_index(drop=True)
    recs = []; fd = {"time": np.asarray(tv.strftime("%Y-%m-%d %H:%M"))}; pages = [d.iloc[p:p + PER_PAGE] for p in range(0, len(d), PER_PAGE)]
    for pn, page in enumerate(pages, 1):
        nrow = int(np.ceil(len(page) / NCOL)); fig, axes = plt.subplots(nrow, NCOL, figsize=(11, 1.6 * nrow + 1.0), sharex=True, squeeze=False)
        for q, r in enumerate(page.itertuples()):
            ax = axes[q % nrow, q // nrow]; n = k[(r.source, r.station_id)]; o = z["observed"][w, n].astype("f8"); m = z["model"][w, n].astype("f8"); ok = np.isfinite(o) & np.isfinite(m)
            dd = float((m - o)[ok].mean()); ms = m - dd; rm = float(np.sqrt(((ms - o)[ok] ** 2).mean())); cor = float(np.corrcoef(o[ok], m[ok])[0, 1]); sr = float(np.std(m[ok]) / np.std(o[ok]))
            ko = int(np.nanargmax(np.where(ok, o, np.nan))); km = int(np.nanargmax(np.where(ok, ms, np.nan)))
            ax.plot(tv, o, color=INK, lw=1.0, zorder=5); ax.plot(tv, ms, color=MODEL, lw=1.0, zorder=4)
            lo, hi = np.nanmin(np.r_[o, ms]), np.nanmax(np.r_[o, ms]); ax.set_ylim(lo - 0.08 * (hi - lo), hi + 0.42 * (hi - lo))
            name = r.name if len(r.name) <= 40 else r.name[:38] + ".."; ax.text(0.012, 0.95, name, transform=ax.transAxes, va="top", ha="left", fontsize=9, fontweight="bold")
            ax.text(0.012, 0.79, f"RMSE {rm:.2f} m    datum difference {dd:+.2f} m    " + ("NAVD88" if r.datum_known else "datum of the station"), transform=ax.transAxes, va="top", ha="left", fontsize=8.5)
            ax.grid(True, lw=0.3, color="#cccccc"); ax.tick_params(length=2.5, width=0.5); ax.xaxis.set_major_locator(mdates.DayLocator(interval=1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.margins(x=0)
            if q // nrow == 0:
                ax.set_ylabel("water level (m)")
            recs.append({"page": pn, "source": r.source, "station_id": r.station_id, "name": r.name, "lat": r.lat, "lon": r.lon, "cell_model": r.cell_model, "control_point": r.control_point, "datum_known": r.datum_known, "hours": int(ok.sum()),
                         "datum_difference_model_minus_observed_m": dd, "rmse_datum_difference_removed_m": rm, "correlation": cor, "std_ratio": sr,
                         "highest_observed_m": float(o[ko]), "highest_model_datum_difference_removed_m": float(ms[km]), "time_of_highest_observed": f"{tv[ko]:%m-%d %H:%M}", "time_of_highest_model": f"{tv[km]:%m-%d %H:%M}", "correlation_ida_hindcast": r.ida_r})
            fd[f"observed | {r.station_id}"] = o.astype("f4"); fd[f"model_datum_difference_removed | {r.station_id}"] = ms.astype("f4")
        for q in range(len(page), nrow * NCOL):
            axes[q % nrow, q // nrow].axis("off")
        fig.suptitle(f"Hurricane Francine run against the gauges, five days before to five days after the landfall, west to east: stations {(pn - 1) * PER_PAGE + 1} to {(pn - 1) * PER_PAGE + len(page)} of {len(d)}", fontsize=11, y=0.995)
        fig.legend([Line2D([], [], color=INK, lw=1.2), Line2D([], [], color=MODEL, lw=1.2)], ["observed", "numerical model at the cell of the gauge, moved by its mean difference from the observations in these ten days"],
                   loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.0))
        fig.tight_layout(rect=(0, 0.03, 1, 0.985), h_pad=0.25, w_pad=1.0); fig.savefig(f"{a.out}_{pn}.png", dpi=200); plt.close(fig); print("->", f"{a.out}_{pn}.png", len(page), "stations")
    s = pd.DataFrame(recs); s.to_csv(a.out + "_stations.csv", index=False); np.savez_compressed(a.out + "_fig_data.npz", **fd); kn = s[s.datum_known]; x = kn.datum_difference_model_minus_observed_m
    print(f"{len(s)} stations; RMSE: median {s.rmse_datum_difference_removed_m.median():.3f} m, at most 0.10 m at {int((s.rmse_datum_difference_removed_m <= 0.10).sum())}, at most 0.15 m at {int((s.rmse_datum_difference_removed_m <= 0.15).sum())}; "
          f"correlation median {s.correlation.median():.2f}, at least 0.8 at {int((s.correlation >= 0.8).sum())}, at least 0.9 at {int((s.correlation >= 0.9).sum())}; std ratio median {s.std_ratio.median():.2f}")
    print(f"datum difference at the {len(kn)} stations with known datum: median {x.median():+.3f} m, quartiles {x.quantile(.25):+.3f} .. {x.quantile(.75):+.3f}, min {x.min():+.2f}, max {x.max():+.2f}")
    pk = s.highest_model_datum_difference_removed_m - s.highest_observed_m; print(f"highest level, model minus observed: median {pk.median():+.3f} m, rms {np.sqrt((pk ** 2).mean()):.3f} m, within 0.15 m at {int((pk.abs() <= 0.15).sum())}")
    pd.set_option("display.width", 250); print(s.assign(nm=s.name.str[:32])[["page", "nm", "lon", "cell_model", "datum_known", "datum_difference_model_minus_observed_m", "rmse_datum_difference_removed_m", "correlation", "std_ratio", "highest_observed_m", "highest_model_datum_difference_removed_m"]]
          .rename(columns={"datum_difference_model_minus_observed_m": "datum_diff", "rmse_datum_difference_removed_m": "rmse", "correlation": "r", "std_ratio": "sd", "highest_observed_m": "pk_obs", "highest_model_datum_difference_removed_m": "pk_mod", "datum_known": "navd"}).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
