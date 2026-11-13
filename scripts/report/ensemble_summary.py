"""Numbers for the write-up on the mean of models that differ only in the random seed, and on the per-station initial state.

Reads runs/<run>/per_station_test.csv, runs/<mean>/per_station_test_mean<k>.csv and runs/<run>/storm_station.csv; stations with
real-time data only (the same station set as the version comparison). Prints tables; writes deliverables/24_seed_mean.csv.
Usage: python ensemble_summary.py
"""
from __future__ import annotations

import io
import sys

import numpy as np
import pandas as pd

from versions_figs import LADDER, REPO, TYPES, load_runs, pooled

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RUN, SEEDS, MEAN, INIT, WL = "v14_stale25", ["v15r_seed1", "v15r_seed2", "v15r_seed3", "v15r_seed4"], "v15r_mean5", "v15r_init_state", "v3_obs"


def main() -> None:
    d = load_runs([r for r, _, _ in LADDER] + SEEDS + [INIT, MEAN])
    idx = d[RUN].index
    n = len(idx)
    mk = {k: pd.read_csv(REPO / "runs" / MEAN / f"per_station_test_mean{k}.csv", dtype={"station_id": str}).loc[idx] for k in range(1, len(SEEDS) + 2)}
    assert np.allclose(mk[1].rmse_6h_cm, d[RUN].rmse_6h_cm, atol=0.02), "the first member is not the model that is run"
    rows = []
    print(f"test period, {n} stations with real-time data, RMSE over all forecasts (cm)")
    print(f"{'':44s}   1 h    3 h    6 h")
    for lab, x in [("model that is run (seed 0)", d[RUN])] + [(f"same settings, seed {i + 1}", d[s]) for i, s in enumerate(SEEDS)] + \
                  [(f"mean of {k} models", mk[k]) for k in range(2, len(SEEDS) + 2)] + [("station's own initial state (seed 0)", d[INIT])]:
        v = [pooled(x, h) for h in (1, 3, 6)]
        rows.append({"what": lab, "rmse_1h_cm": round(v[0], 2), "rmse_3h_cm": round(v[1], 2), "rmse_6h_cm": round(v[2], 2)})
        print(f"{lab:44s} {v[0]:6.2f} {v[1]:6.2f} {v[2]:6.2f}")
    pd.DataFrame(rows).to_csv(REPO / "deliverables" / "24_seed_mean.csv", index=False)

    print("\n6 h RMSE by station type: all forecasts (all stations) / median station (types)")
    print(f"{'':30s}     n   run   seeds min-max   mean of 5   own initial state")
    for t, lab in [(None, "All stations")] + list(TYPES):
        f = (lambda x: pooled(x, 6)) if t is None else (lambda x: float(x.rmse_6h_cm[(d[RUN].type == t).to_numpy()].median()))
        sv = [f(d[s]) for s in [RUN] + SEEDS]
        print(f"{lab:30s} {n if t is None else int((d[RUN].type == t).sum()):5d} {f(d[RUN]):5.2f}   {min(sv):5.2f}-{max(sv):5.2f}     {f(mk[len(SEEDS) + 1]):5.2f}        {f(d[INIT]):5.2f}")

    for lab, x in [("mean of 5", mk[len(SEEDS) + 1]), ("own initial state", d[INIT])] + [(f"seed {i + 1}", d[s]) for i, s in enumerate(SEEDS)]:
        dd = x.rmse_6h_cm.to_numpy() - d[RUN].rmse_6h_cm.to_numpy()
        print(f"\n{lab} against the model that is run, 6 h, per station: better at {int((dd < 0).sum())}, worse at {int((dd > 0).sum())}; "
              f"by more than 0.5 cm: {int((dd < -0.5).sum())} better, {int((dd > 0.5).sum())} worse; median change {np.median(dd):+.2f} cm")

    # hurricane periods, every hourly forecast
    st = {r: pd.read_csv(REPO / "runs" / r / "storm_station.csv", dtype={"station_id": str}).set_index(["source", "station_id"]) for r in (WL, RUN, MEAN)}
    wl = st[WL]; run, mean = st[RUN].reindex(wl.index), st[MEAN].reindex(wl.index)
    print(f"\nhurricane periods, {len(wl)} stations, {int(wl.n.sum()):,} forecasts")
    for h in (1, 3, 6):
        print(f"  {h} h, all forecasts: water level only {np.sqrt((wl.n * wl[f'rmse_{h}h_cm'] ** 2).sum() / wl.n.sum()):.1f}, "
              f"model that is run {np.sqrt((run.n * run[f'rmse_{h}h_cm'] ** 2).sum() / run.n.sum()):.1f}, mean of 5 {np.sqrt((mean.n * mean[f'rmse_{h}h_cm'] ** 2).sum() / mean.n.sum()):.1f} cm")
    for t in sorted(set(wl.type)):
        m = (wl.type == t).to_numpy()
        print(f"  {t:26s} n {int(m.sum()):3d}  6 h all forecasts: run {np.sqrt((run.n[m] * run.rmse_6h_cm[m] ** 2).sum() / run.n[m].sum()):5.1f}  mean of 5 {np.sqrt((mean.n[m] * mean.rmse_6h_cm[m] ** 2).sum() / mean.n[m].sum()):5.1f}")
    for lab, x in [("model that is run", run), ("mean of 5", mean)]:
        worse = x.rmse_6h_cm > wl.rmse_6h_cm
        clear = (x.rmse_6h_cm > wl.rmse_6h_cm + 1) & (x.rmse_6h_cm > 1.1 * wl.rmse_6h_cm)
        print(f"  {lab}: worse than water level only at {int(worse.sum())} stations ({100 * worse.mean():.0f}%), clearly worse at {int(clear.sum())}; "
              f"mean 6 h bias at the clearly worse stations {x.bias_6h_cm[clear].mean():+.1f} cm")
    ei = ("NOAA_COOPS", "8764314")
    print(f"  Eugene Island 6 h: water level only {wl.rmse_6h_cm[ei]:.1f}, model that is run {run.rmse_6h_cm[ei]:.1f}, mean of 5 {mean.rmse_6h_cm[ei]:.1f} cm")
    dd = mean.rmse_6h_cm - run.rmse_6h_cm
    print(f"  mean of 5 against the model that is run, per station: better at {int((dd < 0).sum())}, worse at {int((dd > 0).sum())}; by more than 1 cm: {int((dd < -1).sum())} better, {int((dd > 1).sum())} worse")


if __name__ == "__main__":
    main()
