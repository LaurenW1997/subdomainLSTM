"""Stations of the test on past forecast times (deliverable 33): the two models side by side, in the style of the station
figures of the version comparison (versions_figs.station_fig).

One row per station, one column per model. Black: observed hourly level. Three lines in a warm ramp, pale to vivid: the
forecast valid at each hour that was issued 1, 3 and 6 h earlier (a forecast from every hour). Grey band: 24 h around the
observed peak. RMSE per lead over the window in every panel.
With --period given more than once the same stations are drawn for several periods next to each other (two columns per period).
Input : deliverables/33_partner_live_test/hourly_fc.csv (operational/extract_hourly_test.py on sv7)
Output: deliverables/33_partner_live_test/stations_<n>.png, four stations each (--per-figure 2 --prefix stations_wide: two each, for slides)
Usage : python partner_live_fig.py [--stations 07374000 8767816 ...] [--per-figure 2 --prefix stations_wide]
        python partner_live_fig.py --period "10 to 12 November 2026" A.csv 2026-11-11T00 2026-11-13T00 \
                                   --period "15 to 17 November 2026" B.csv 2026-11-15T00 2026-11-17T12 --prefix two_periods
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

from versions_figs import INK, LEAD_COL  # also sets the figure style (Times New Roman, thin axes)

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "33_partner_live_test"
DEFAULT = ["07374000", "8767816", "07387040", "08075500", "07381515", "08068500", "08073700", "07378000"]
COLS = [("run", "Scaling + gap filling + HRRR rainfall, trained with\nmissing hours, mean of 5 models  (the version that is run)"),
        ("partners", "With partner stations (by measured tide and\nupstream direction), mean of 5 models")]
COLS_NARROW = [("run", "Scaling + gap filling + HRRR rainfall,\ntrained with missing hours, mean of\n5 models  (the version that is run)"),
               ("partners", "With partner stations\n(by measured tide and upstream\ndirection), mean of 5 models")]
LEADS = (1, 3, 6)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", nargs="+", default=DEFAULT); ap.add_argument("--src", default=str(D / "hourly_fc.csv"))
    ap.add_argument("--begin", default="2026-11-15T00"); ap.add_argument("--end", default="2026-11-17T12"); ap.add_argument("--per-figure", type=int, default=4); ap.add_argument("--prefix", default="stations", help="file name: <prefix>_<n>.png")
    ap.add_argument("--period", nargs=4, action="append", metavar=("LABEL", "SRC", "BEGIN", "END"), help="several periods next to each other; replaces --src --begin --end")
    ap.add_argument("--narrow", action="store_true", help="with several periods: a figure as wide as a slide (13 in), column titles on three lines")
    a = ap.parse_args()
    periods = a.period or [["", a.src, a.begin, a.end]]
    pm = pd.read_csv(REPO / "config" / "station_partners_behaviour.csv", dtype=str)          # stations without partner are marked in the figure
    n_par = dict(zip(pm.station_id, pd.to_numeric(pm.n_partners, errors="coerce").fillna(0).astype(int)))
    cols = COLS_NARROW if a.narrow else COLS
    data = []
    for lab, src, b, e in periods:
        d = pd.read_csv(src, dtype={"station_id": str})
        d["origin"] = pd.to_datetime(d.origin, format="mixed"); d["valid"] = pd.to_datetime(d.valid, format="mixed")
        data.append((lab, d[(d.valid >= pd.Timestamp(b)) & (d.valid <= pd.Timestamp(e))], pd.Timestamp(b), pd.Timestamp(e)))
    nP, many = len(data), len(data) > 1
    head = many or any(lab for lab, *_ in data)        # a heading above the columns: the period, or the domain for a single period
    for k in range(0, len(a.stations), a.per_figure):
        ids = a.stations[k:k + a.per_figure]
        H = 2.45 * len(ids) + ((1.55 if a.narrow else 1.3) if head else 0.9)
        fig = plt.figure(figsize=(11.0 if not many else (13.0 if a.narrow else 9.6 * nP), H))
        wr = sum([[1, 1, 0.16] for _ in range(nP)], [])[:-1]              # two columns per period, a gap between periods
        gs = fig.add_gridspec(len(ids), len(wr), width_ratios=wr, wspace=0.06, hspace=0.36)
        for i, sid in enumerate(ids):
            for p, (plab, d, b, e) in enumerate(data):
                x = d[d.station_id == sid]
                assert len(x), f"no station {sid} in period {p + 1}"
                o = x.drop_duplicates("valid").set_index("valid").obs.sort_index().dropna()
                pk = o.idxmax()
                left = None
                for j, (key, title) in enumerate(cols):
                    ax = fig.add_subplot(gs[i, 3 * p + j], sharey=left)
                    ax.axvspan(pk - pd.Timedelta(hours=12), pk + pd.Timedelta(hours=12), color="#000000", alpha=0.05, lw=0)
                    rm = []
                    for h in LEADS:
                        g = x[x.lead == h].sort_values("valid")
                        ax.plot(g.valid, g[key], color=LEAD_COL[h], lw=1.0, zorder=4)
                        er = (g[key] - g.obs).dropna()
                        rm.append(100 * float(np.sqrt((er ** 2).mean())))
                    ax.plot(o.index, o.values, color=INK, lw=1.15, zorder=5)
                    if j == len(cols) - 1:                      # head-room so the RMSE label never sits on the data (the pair shares the y axis)
                        lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.30 * (hi - lo))
                        ax.tick_params(labelleft=False)
                    else:
                        left = ax
                    ax.text(0.02, 0.96, "RMSE (cm)" + "\n" + "   ".join(f"{h} h {r:.1f}" for h, r in zip(LEADS, rm)), transform=ax.transAxes, va="top", ha="left", fontsize=8.6,
                            color=INK, linespacing=1.25, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
                    ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
                    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
                    ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True)
                    ax.set_xlim(b - pd.Timedelta(hours=1), e + pd.Timedelta(hours=1))      # the same days in every panel of a period
                    if i == 0:
                        ax.set_title(title, loc="left", fontsize=9.6 if not many else (8.6 if a.narrow else 9.0), linespacing=1.25, fontweight="bold" if key == "run" else "normal", pad=22)
                        if head and plab and j == 0:
                            ax.text(0.0, 1.0, plab, transform=ax.transAxes + matplotlib.transforms.ScaledTranslation(0, (72 if a.narrow else 56) / 72, fig.dpi_scale_trans), fontsize=11.5, fontweight="bold", color=INK, va="bottom")
                    if j == 0:
                        ax.set_ylabel("water level (m)", fontsize=9)
                        name = str(x.name.iloc[0]); name = name.title() if name.isupper() else name
                        none = n_par.get(sid, 0) == 0
                        ax.text(0.0, 1.03, f"{name}  ({x.source.iloc[0].replace('NOAA_COOPS', 'NOAA')} {sid})" + ("   -   no partner station" if none else ""), transform=ax.transAxes,
                                fontsize=9.8, color=INK, va="bottom")
                    elif n_par.get(sid, 0) == 0:                # the right panel of a station without partner: say that nothing differs in the input
                        ax.text(0.98, 0.96, "no partner station:\nsame input as on the left", transform=ax.transAxes, va="top", ha="right", fontsize=8.6, color="#b3261e", linespacing=1.25,
                                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
        h = [Line2D([], [], color=INK, lw=1.15)] + [Line2D([], [], color=LEAD_COL[v], lw=1.3) for v in LEADS]
        fig.legend(h, ["observed"] + [f"forecast issued {v} h earlier" for v in LEADS], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.005), fontsize=9.5)
        fig.subplots_adjust(left=0.065 if not many else (0.055 if a.narrow else 0.04), right=0.99, top=1 - ((1.4 if a.narrow else 1.15) if head else 0.75) / H, bottom=0.62 / H)
        out = D / f"{a.prefix}_{k // a.per_figure + 1}.png"
        fig.savefig(out, dpi=250 if (not many or a.narrow) else 190); plt.close(fig)
        print("->", out)


if __name__ == "__main__":
    main()
