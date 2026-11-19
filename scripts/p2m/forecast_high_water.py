"""Flood map: how much too high the water-level model is at high water, by lead time - measured on the years it was not trained on.

The mapping from gauges to the marsh is steeper at high water, so a forecast that is too high at a peak is made worse. Here
the part of a forecast above the 95th percentile of the gauge (training years) is compared with the same part of the
observation at the valid time, over the test years of the water-level model, with the storm that is used as the test of the
flood map left out (--exclude). Pooled over the gauges, per lead time:
    factor = sum(excess_forecast * excess_observed) / sum(excess_forecast^2)
A factor below 1 means that of every metre a forecast stands above the threshold, only that share was observed.
The correction of a forecast is then  f' = f - (1 - factor) * max(f - threshold, 0).
Input : --fc NPZ of forecast_inputs.py (t0, forecast, observed_at_valid, source, station_id), --dataset DIR
Output: --out CSV (lead_h, factor, hours, ...); --out-gauges CSV (per gauge and lead: RMSE of the forecasts above the threshold, used by
        marsh_obs_variants.py as the assumed error of that input); a table is printed
Usage : python forecast_high_water.py --fc FILE --dataset DIR --out FILE
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--fc", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True); ap.add_argument("--out-gauges", help="CSV per gauge and lead: error of the forecasts that stand above the threshold")
    ap.add_argument("--train", nargs=2, default=["2016-01-01", "2024-01-01"]); ap.add_argument("--exclude", nargs=2, default=["2024-09-03", "2024-09-21"]); ap.add_argument("--percentile", type=float, default=95.0)
    a = ap.parse_args(); ds = Path(a.dataset)
    z = np.load(a.fc); F, O = z["forecast"].astype(np.float64), z["observed_at_valid"].astype(np.float64); t0 = pd.DatetimeIndex(z["t0"])
    st = pd.read_csv(ds / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(ds / "time.npy")); vals = np.load(ds / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; i0, i1 = tm.get_indexer([pd.Timestamp(a.train[0]), pd.Timestamp(a.train[1])])
    q = np.array([np.nanpercentile(np.asarray(vals[row[(s, i)], i0:i1], float), a.percentile) for s, i in zip(z["source"], z["station_id"])])
    keep = ~np.asarray((t0 >= a.exclude[0]) & (t0 < a.exclude[1])); rows = []; gr = []
    for L in range(1, F.shape[1] + 1):
        f, o = F[keep, L - 1], O[keep, L - 1]; hf, ho = np.maximum(f - q[None, :], 0), np.maximum(o - q[None, :], 0); m = np.isfinite(f) & np.isfinite(o) & (hf > 0)
        for p in range(F.shape[2]):
            e = (f - o)[:, p]; mm = m[:, p]
            gr.append({"source": z["source"][p], "station_id": z["station_id"][p], "lead_h": L, "threshold_m": q[p], "forecasts_above_threshold": int(mm.sum()), "rmse_above_threshold_m": float(np.sqrt(np.mean(e[mm] ** 2))) if mm.sum() else np.nan,
                       "mean_error_above_threshold_m": float(e[mm].mean()) if mm.sum() else np.nan, "rmse_all_m": float(np.sqrt(np.nanmean(e ** 2)))})
        big = m & (hf > 0.3); per = np.array([(hf[m[:, p], p] * ho[m[:, p], p]).sum() / max((hf[m[:, p], p] ** 2).sum(), 1e-9) if m[:, p].sum() >= 30 else np.nan for p in range(F.shape[2])])
        rows.append({"lead_h": L, "forecasts_above_threshold": int(m.sum()), "factor": float((hf[m] * ho[m]).sum() / (hf[m] ** 2).sum()), "mean_forecast_minus_observed_m": float((f - o)[m].mean()),
                     "forecasts_more_than_0.3m_above": int(big.sum()), "factor_more_than_0.3m_above": float((hf[big] * ho[big]).sum() / (hf[big] ** 2).sum()) if big.sum() else np.nan,
                     "mean_forecast_minus_observed_more_than_0.3m_above_m": float((f - o)[big].mean()) if big.sum() else np.nan,
                     "factor_per_gauge_quartiles": " / ".join(f"{v:.2f}" for v in np.nanpercentile(per, [25, 50, 75])), "rmse_all_forecasts_m": float(np.sqrt(np.nanmean((f - o) ** 2)))})
    t = pd.DataFrame(rows); t.to_csv(a.out, index=False); pd.set_option("display.width", 250)
    print(f"{F.shape[2]} gauges, {int(keep.sum())} issue times {t0[keep][0]} .. {t0[keep][-1]} without {a.exclude[0]} .. {a.exclude[1]}; threshold: {a.percentile:.0f}th percentile of {a.train[0]} .. {a.train[1]}")
    print(t.round(3).to_string(index=False)); print("->", a.out)
    if a.out_gauges:
        pd.DataFrame(gr).to_csv(a.out_gauges, index=False); print("->", a.out_gauges)


if __name__ == "__main__":
    main()
