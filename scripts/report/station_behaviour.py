"""How every station actually behaves, from its own water level: how much tide, and how fast it rises.

Training period, hourly water level in cm. Per station:
  tide_rms_cm   RMS of a harmonic fit (M2, S2, N2, K2, K1, O1, P1, Q1) to the level minus its 25 h running mean,
                fitted year by year (mean over the years with at least 2000 valid hours)
  tide_share    share of the variance of that high-passed level which the fit explains (same years)
  tide_share_6h share of the variance of the 6 h change of the level explained by the 6 h change of the fitted tide
  d6_p50, d6_p99, d6_p999   quantiles of the absolute 6 h change (cm)
  rise_p999     99.9 % quantile of the 6 h rise (cm)
  flash         d6_p99 / d6_p50
  std_cm        standard deviation of the level
Output: <out>/station_behaviour.csv
Usage : python station_behaviour.py --dataset DATA/dataset_v6 --out OUT
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HOURS = {"M2": 12.4206012, "S2": 12.0, "N2": 12.65834751, "K2": 11.96723606, "K1": 23.93447213, "O1": 25.81933871, "P1": 24.06588766, "Q1": 26.868350}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
    d = Path(a.dataset)
    st = pd.read_csv(d / "stations.csv", index_col="row", dtype={"station_id": str}).reset_index(drop=True)
    meta = json.loads((d / "meta.json").read_text())
    time = pd.to_datetime(np.load(d / "time.npy"))
    t_end = int(np.searchsorted(time.values, np.datetime64(meta["train_end"])))
    v = 100 * np.asarray(np.load(d / "values.npy", mmap_mode="r")[:, :t_end], dtype=np.float64)       # cm
    time = time[:t_end]; hrs = np.arange(t_end, dtype=np.float64)
    X = np.column_stack([f(2 * np.pi * hrs / p) for p in HOURS.values() for f in (np.cos, np.sin)] + [np.ones(t_end)])
    years = time.year.to_numpy()
    rows = []
    for s in range(len(st)):
        x = pd.Series(v[s])
        hp = (x - x.rolling(25, center=True, min_periods=20).mean()).to_numpy()
        fit = np.full(t_end, np.nan)
        for y in np.unique(years):
            m = (years == y) & np.isfinite(hp)
            if m.sum() < 2000:
                continue
            w = np.linalg.lstsq(X[m], hp[m], rcond=None)[0]
            fit[years == y] = X[years == y] @ w
        ok = np.isfinite(fit) & np.isfinite(hp)
        r = {"source": st.source[s], "station_id": st.station_id[s], "name": st.name[s], "n_hours": int(np.isfinite(v[s]).sum())}
        if ok.sum() >= 2000:
            r["tide_rms_cm"] = float(np.std(fit[ok])); r["tide_share"] = float(np.var(fit[ok]) / max(np.var(hp[ok]), 1e-12))
            d6 = v[s, 6:] - v[s, :-6]; f6 = fit[6:] - fit[:-6]; k = np.isfinite(d6) & np.isfinite(f6)
            if k.sum() >= 2000:
                r["tide_share_6h"] = float(1 - np.var(d6[k] - f6[k]) / max(np.var(d6[k]), 1e-12))
        d6 = v[s, 6:] - v[s, :-6]; d6 = d6[np.isfinite(d6)]
        if len(d6) >= 2000:
            ad = np.abs(d6)
            r.update(d6_p50=float(np.quantile(ad, .5)), d6_p99=float(np.quantile(ad, .99)), d6_p999=float(np.quantile(ad, .999)), rise_p999=float(np.quantile(d6, .999)),
                     flash=float(np.quantile(ad, .99) / max(np.quantile(ad, .5), 0.05)), std_cm=float(np.nanstd(v[s])))
        rows.append(r)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).round(4).to_csv(out / "station_behaviour.csv", index=False)
    print("->", out / "station_behaviour.csv", len(rows))


if __name__ == "__main__":
    main()
