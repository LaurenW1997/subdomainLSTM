"""Francine case, river inflow: the file hydro_obs.txt of the land model (Mississippi River at the northern edge of the grid).

The land model reads the inflow of the Mississippi at nine cells of the northern edge, hour by hour (m3/s per cell, negative =
southward). The version of the Ida run named '30 h lag' is, cell by cell,
    inflow(t) = share of the cell x FACTOR x discharge at Vicksburg (USGS 07289000) at t - 30 h
with the same nine shares at every hour; this was checked against the file (largest difference 0.04 m3/s). The same is written
here for another period, in the same layout: first line the number of cells, then per cell a line 'i j 1 n' and n lines 'YYYY-MM-DD HH:MM:SS value'.
With --diversion the water that leaves the Mississippi at Old River, a few kilometres below the edge of the grid, is taken out
(the model has no Old River): inflow(t) = FACTOR x Vicksburg(t - 30 h) - Old River Outflow Channel(t), USGS 07381482, hourly, gaps
filled linearly. For 14 Aug to 19 Sep 2024 this inflow agrees with the flow observed at Baton Rouge (mean difference -16 m3/s).
Input : --template the Ida file (cells and shares are read from it), --usgs CSV (time, value: hourly discharge in ft3/s, UTC)
Output: --out FILE, and a summary beside it
Usage : python make_hydro_obs.py --template ida_hydro_obs_yymmdd_30hlag.txt --usgs usgs_07289000_00060_2024.csv [--diversion usgs_07381482_00060_2024.csv]
                               --start "2024-08-14 00:00" --end "2024-09-19 00:00" --out FILE
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CFS = 0.028316846592


def parse(path: str):
    L = Path(path).read_text().split("\n"); n = int(L[0]); k = 1; cells = []; ser = []
    for _ in range(n):
        i, j, flag, nt = map(int, L[k].split()); k += 1; t = pd.to_datetime([x[:19] for x in L[k:k + nt]]); v = np.array([float(x[19:]) for x in L[k:k + nt]]); k += nt; cells.append((i, j, flag)); ser.append(pd.Series(v, index=t))
    return cells, pd.concat(ser, axis=1)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--template", required=True); ap.add_argument("--usgs", required=True); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--diversion", help="CSV as --usgs: discharge of the Old River Outflow Channel (ft3/s), subtracted hour by hour"); ap.add_argument("--lag-hours", type=int, default=30); ap.add_argument("--factor", type=float, default=1.0231, help="the Ida file is this factor times the discharge USGS serves today"); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    cells, S = parse(a.template); share = (S.div(S.sum(1), axis=0)).mean(0).to_numpy(); assert float((S.div(S.sum(1), axis=0)).std(0).max()) < 1e-6, "the shares of the cells change in time"
    q = pd.read_csv(a.usgs, index_col=0, parse_dates=True).value * CFS; gaps = int(q.isna().sum()); q = q.interpolate(limit=24); hours = pd.date_range(a.start, a.end, freq="h")
    src = q.reindex(hours - pd.Timedelta(hours=a.lag_hours)); assert src.notna().all(), f"discharge missing for {int(src.isna().sum())} hours"; total = a.factor * src.to_numpy(); div_note = "no diversion taken out"
    if a.diversion:
        d = pd.read_csv(a.diversion, index_col=0, parse_dates=True).value * CFS; d = d.reindex(pd.date_range(d.index[0], d.index[-1], freq="h")); miss = d.reindex(hours).isna(); d = d.interpolate(limit_area="inside").reindex(hours)
        assert d.notna().all(), "the diversion record does not cover the period"; total = total - d.to_numpy(); assert (total > 0).all()
        div_note = f"Old River outflow taken out: min {d.min():.0f}, mean {d.mean():.0f}, max {d.max():.0f} m3/s; {int(miss.sum())} of its hours filled linearly"
    L = [str(len(cells))]
    for (i, j, flag), s in zip(cells, share):
        L.append(f"{i}  {j}  {flag}  {len(hours)}"); L += [f"{t:%Y-%m-%d %H:%M:%S} {-s * v:.4f}" for t, v in zip(hours, total)]
    Path(a.out).write_text("\n".join(L) + "\n", newline="\n")
    info = [f"{len(cells)} cells {cells[0][:2]} .. {cells[-1][:2]}, shares {np.round(share, 4).tolist()}", f"{len(hours)} hours {hours[0]} .. {hours[-1]}; discharge at Vicksburg {a.lag_hours} h earlier times {a.factor}",
            div_note, f"total inflow (m3/s): first {total[0]:.0f}, min {total.min():.0f}, mean {total.mean():.0f}, max {total.max():.0f}; hours filled in the Vicksburg record: {gaps}"]
    Path(a.out).with_suffix(".summary.txt").write_text("\n".join(info), encoding="utf-8"); print("\n".join(info)); print("->", a.out)


if __name__ == "__main__":
    main()
