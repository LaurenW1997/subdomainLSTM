"""Flood map, the level zero: the inputs of the mapping model raised by one amount, scored against the marsh gauges (CRMS).

The numerical model lacks the sea level of the month of the storm (about 0.35 m above NAVD88 by the monthly mean sea level NOAA
publishes, level_zero_check.py); the chain moves the observations down to the level of the model before the mapping model sees
them. Test: one amount is added back to the inputs at every control point and hour (`p2m_paper.py apply --add`), nothing is fitted,
and the depth on the marsh is compared with the observed depth, on the gauges that have a map with every training.
Input : --dir DIR with apply_<training>_plus_<amount>/crms_check.csv (p2m_paper_crms.py), --trainings KEY=LABEL ...
Output: --out CSV (one row per training, field, amount and group of gauges) and --fig PNG
Usage : python p2m_level_zero_shift_score.py --dir DIR --trainings ida11_with_input_error="eleven Ida runs" --out FILE --fig FILE
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SPLIT = -90.8
FIELDS = ["Francine, inputs forecast 6 h before", "Francine, inputs observed", "Ida, inputs observed"]
COL = {"all": "#1a1a1a", "west of 90.8W": "#c2410c", "east of 90.8W": "#2f6fb5"}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--trainings", nargs="+", required=True); ap.add_argument("--out", required=True); ap.add_argument("--fig", required=True)
    ap.add_argument("--published", type=float, default=0.35, help="the amount the published mean sea level gives (m), marked in the figure"); a = ap.parse_args(); tr = dict(t.split("=", 1) for t in a.trainings); X = []
    for d in sorted(Path(a.dir).glob("apply_*_plus_*")):
        m = re.fullmatch(r"apply_(.+)_plus_([0-9.]+)", d.name)
        if m and m.group(1) in tr and (d / "crms_check.csv").exists():
            X.append(pd.read_csv(d / "crms_check.csv").assign(training=tr[m.group(1)], amount=float(m.group(2))))
    X = pd.concat(X); X = X[X.field.isin(FIELDS)].dropna(subset=["storm_map_largest_depth_m", "storm_observed_largest_depth_m"]); rows = []
    for f in FIELDS:                                                        # the gauges that have a map with every training and amount
        x = X[X.field == f]; n = x.groupby("station").size(); keep = n.index[n == n.max()]; x = x[x.station.isin(keep)]
        for (t, c), g in x.groupby(["training", "amount"], sort=False):
            for nm, w in (("all", np.ones(len(g), bool)), ("west of 90.8W", (g.lon < SPLIT).to_numpy()), ("east of 90.8W", (g.lon >= SPLIT).to_numpy())):
                y = g[w]; e = y.storm_map_largest_depth_m - y.storm_observed_largest_depth_m
                rows.append({"field": f, "training": t, "amount_added_m": c, "gauges": nm, "n": len(y), "depth_hour_by_hour_rmse_median_per_gauge_m": y.rmse_depth_m.median(),
                             "quiet_days_flooded_share_observed": y.calm_observed_flooded_share.mean(), "quiet_days_flooded_share_map": y.calm_map_flooded_share.mean(),
                             "quiet_days_mean_depth_observed_median_m": y.calm_observed_mean_depth_m.median(), "quiet_days_mean_depth_map_median_m": y.calm_map_mean_depth_m.median(),
                             "storm_days_mean_depth_observed_median_m": y.storm_observed_mean_depth_m.median(), "storm_days_mean_depth_map_median_m": y.storm_map_mean_depth_m.median(),
                             "largest_depth_observed_median_m": y.storm_observed_largest_depth_m.median(), "largest_depth_map_median_m": y.storm_map_largest_depth_m.median(),
                             "largest_depth_mean_error_m": e.mean(), "largest_depth_rmse_m": float(np.sqrt((e ** 2).mean())), "largest_depth_correlation": float(np.corrcoef(y.storm_observed_largest_depth_m, y.storm_map_largest_depth_m)[0, 1])})
    T = pd.DataFrame(rows).sort_values(["field", "training", "gauges", "amount_added_m"]); T.to_csv(a.out, index=False); pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
    print(T[T.gauges == "all"][["field", "training", "amount_added_m", "n", "depth_hour_by_hour_rmse_median_per_gauge_m", "quiet_days_flooded_share_observed", "quiet_days_flooded_share_map", "largest_depth_mean_error_m", "largest_depth_rmse_m", "largest_depth_correlation"]].round(3).to_string())

    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 13, "mathtext.fontset": "stix"}); t = list(tr.values())[-1]          # the figure shows the last training given; the others are in the table
    panels = [("largest_depth_mean_error_m", "Largest depth in the storm days:\nmean error (m)"), ("largest_depth_rmse_m", "Largest depth in the storm days:\nRMSE (m)"), ("depth_hour_by_hour_rmse_median_per_gauge_m", "Depth hour by hour:\nRMSE, median over gauges (m)")]
    fig, axs = plt.subplots(len(panels), len(FIELDS), figsize=(4.6 * len(FIELDS), 3.2 * len(panels)), sharex=True, sharey="row", squeeze=False)
    for c, f in enumerate(FIELDS):
        g = T[(T.field == f) & (T.training == t)]
        for r, (key, lab) in enumerate(panels):
            ax = axs[r, c]
            for nm, col in COL.items():
                y = g[g.gauges == nm]; ax.plot(y.amount_added_m, y[key], "-o", color=col, lw=2.2 if nm == "all" else 1.5, ms=5, label=f"{nm} ({int(y.n.iloc[0])} gauges)" if r == 0 else None)
            ax.axvline(a.published, color="0.45", ls="--", lw=1.1); ax.grid(alpha=0.3); ax.spines[["top", "right"]].set_visible(False)
            if key == "largest_depth_mean_error_m":
                ax.axhline(0, color="0.2", lw=0.8)
            if c == 0:
                ax.set_ylabel(lab)
            if r == 0:
                ax.set_title(f, fontsize=13); ax.legend(frameon=False, fontsize=10, loc="upper left")
            if r == len(panels) - 1:
                ax.set_xlabel("Amount added to the inputs (m)")
    axs[0, 0].set_ylim(float(T[T.training == t].largest_depth_mean_error_m.min()) - 0.04, 0.3)                    # room for the legend above the lines
    fig.suptitle(f"Flood map against the observed depth at the marsh gauges, inputs raised by one amount; trained on {t}\n(dashed: {a.published} m, the mean sea level of the month that the numerical model lacks)", fontsize=13.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985)); fig.savefig(a.fig, dpi=170); print("->", a.out, a.fig)


if __name__ == "__main__":
    main()
