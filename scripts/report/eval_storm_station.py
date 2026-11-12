"""Per-station error in the hurricane periods, every hourly forecast, for one run.

Same periods and stations as eval_stale_origin.py (Beryl, 7-11 July 2024, Texas and Galveston domains; Francine,
10-14 September 2024, Louisiana domain; stations with real-time data), but every hour is a forecast time and the
result is kept per station, so that two runs can be compared station by station.
Output: runs/<run>/storm_station.csv  (source, station_id, type, n, rmse_1h_cm, rmse_3h_cm, rmse_6h_cm, bias_6h_cm,
        obs_range_cm = range of the observed level over the forecast targets)
Usage (sv7, CPU): python eval_storm_station.py --run v14_stale25 --dataset DATA/dataset_v6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HORIZON, to_torch  # noqa: E402
from eval_stale_origin import STORMS  # noqa: E402
from station_compare import load  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--batch", type=int, default=4096)
    a = ap.parse_args()
    device = torch.device("cpu"); torch.set_num_threads(16)
    sm, model = load(REPO / "runs" / a.run, Path(a.dataset), device)
    st = sm.stations.reset_index(drop=True)
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    typ = st[["source", "station_id"]].astype(str).merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left").type.fillna("other").to_numpy()
    oper = np.where((st.source != "CRMS").to_numpy())[0]
    dom = st.domains.astype(str).to_numpy()
    S, T0 = [], []
    for _, d0, d1, doms in STORMS:
        i0, i1 = np.searchsorted(sm.time.values, np.datetime64(d0)), np.searchsorted(sm.time.values, np.datetime64(d1))
        for s in oper:
            if any(x in dom[s] for x in doms):
                t = np.arange(i0, i1); t = t[sm.mask[s, t]]              # forecast times with an observation in hand
                S.append(np.full(len(t), s)); T0.append(t)
    S, T0 = np.concatenate(S), np.concatenate(T0)
    std, mean = st.std_m.to_numpy(np.float32), st.mean_m.to_numpy(np.float32)
    err = np.zeros((len(S), HORIZON), np.float32); ok = np.zeros((len(S), HORIZON), bool); obs = np.zeros((len(S), HORIZON), np.float32)
    with torch.no_grad():
        for i in range(0, len(S), a.batch):
            s, t0 = S[i:i + a.batch], T0[i:i + a.batch]
            feats, fut, s, y, ym = sm.window(s, t0)
            f, fu, sx, _, _ = to_torch((feats, fut, s, y, ym), device)
            err[i:i + a.batch] = (model(f, sx, fu).numpy() - y) * std[s][:, None]; ok[i:i + a.batch] = ym
            obs[i:i + a.batch] = y * std[s][:, None] + mean[s][:, None]
    rows = []
    for s in np.unique(S):
        m = S == s
        r = {"source": st.source[s], "station_id": str(st.station_id[s]), "type": typ[s], "n": int(ok[m, 5].sum())}
        if r["n"] < 48:
            continue
        for h in (1, 3, 6):
            r[f"rmse_{h}h_cm"] = round(100 * float(np.sqrt((err[m, h - 1][ok[m, h - 1]] ** 2).mean())), 2)
        r["bias_6h_cm"] = round(100 * float(err[m, 5][ok[m, 5]].mean()), 2)
        o = obs[m, 5][ok[m, 5]]; r["obs_range_cm"] = round(100 * float(o.max() - o.min()), 1)
        rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(REPO / "runs" / a.run / "storm_station.csv", index=False)
    print(a.run, len(d), "stations;", len(S), "forecasts; pooled 6 h RMSE", round(100 * float(np.sqrt((err[:, 5][ok[:, 5]] ** 2).mean())), 2), "cm", flush=True)


if __name__ == "__main__":
    main()
