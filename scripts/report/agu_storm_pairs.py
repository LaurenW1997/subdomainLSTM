"""Every forecast of a run in the two hurricane periods with its observation, for scatter plots (AGU slides).

Same periods, stations and forecast times as eval_storm_station.py (Beryl, 7-11 July 2024, Texas and Galveston domains;
Francine, 10-14 September 2024, Louisiana domain; stations with real-time data; every hour a forecast time), but the
forecasts and observations themselves are kept instead of the RMSE per station.
Output: --out NPZ: station (row in stations.csv), source, station_id, type, storm, origin (time of the forecast), level0 (m, the level
        the forecast starts from), forecast [n, 6] and observed [n, 6] (m, leads 1..6 h), valid [n, 6] (observation present)
Usage (sv7, CPU): python agu_storm_pairs.py --repo REPO --run REPO/runs/v15r_mean5 --dataset DATA/dataset_v6 --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--run", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True); ap.add_argument("--batch", type=int, default=4096)
    a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    repo = Path(a.repo); sys.path.insert(0, str(repo / "scripts" / "train")); sys.path.insert(0, str(repo / "scripts" / "report"))
    from data import HORIZON, to_torch
    from eval_stale_origin import STORMS
    from station_compare import load
    device = torch.device("cpu"); torch.set_num_threads(16)
    sm, model = load(Path(a.run), Path(a.dataset), device)
    st = sm.stations.reset_index(drop=True)
    g = pd.read_csv(repo / "config" / "station_groups.csv", dtype={"station_id": str})
    typ = st[["source", "station_id"]].astype(str).merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left").type.fillna("other").to_numpy()
    oper = np.where((st.source != "CRMS").to_numpy())[0]; dom = st.domains.astype(str).to_numpy()
    S, T0, W = [], [], []
    for name, d0, d1, doms in STORMS:
        i0, i1 = np.searchsorted(sm.time.values, np.datetime64(d0)), np.searchsorted(sm.time.values, np.datetime64(d1))
        for s in oper:
            if any(x in dom[s] for x in doms):
                t = np.arange(i0, i1); t = t[sm.mask[s, t]]
                S.append(np.full(len(t), s)); T0.append(t); W.append(np.full(len(t), str(name)))
    S, T0, W = np.concatenate(S), np.concatenate(T0), np.concatenate(W)
    std, mean = st.std_m.to_numpy(np.float32), st.mean_m.to_numpy(np.float32)
    fc = np.zeros((len(S), HORIZON), np.float32); ob = np.zeros((len(S), HORIZON), np.float32); ok = np.zeros((len(S), HORIZON), bool); l0 = np.zeros(len(S), np.float32)
    with torch.no_grad():
        for i in range(0, len(S), a.batch):
            s, t0 = S[i:i + a.batch], T0[i:i + a.batch]
            feats, fut, s, y, ym = sm.window(s, t0)
            f, fu, sx, _, _ = to_torch((feats, fut, s, y, ym), device)
            fc[i:i + a.batch] = model(f, sx, fu).cpu().numpy() * std[s][:, None] + mean[s][:, None]
            ob[i:i + a.batch] = y * std[s][:, None] + mean[s][:, None]; ok[i:i + a.batch] = ym
            l0[i:i + a.batch] = np.asarray(sm.values[s, t0], np.float32)
    e = (fc - ob)[:, 5][ok[:, 5]]
    print(len(S), "forecasts,", len(np.unique(S)), "stations; 6 h RMSE of all", round(100 * float(np.sqrt((e ** 2).mean())), 2), "cm; storms", dict(zip(*np.unique(W, return_counts=True))), flush=True)
    np.savez_compressed(a.out, station=S.astype(np.int32), source=st.source.to_numpy(str)[S], station_id=st.station_id.astype(str).to_numpy()[S], type=typ[S].astype(str), storm=W, origin=sm.time.values[T0],
                        level0=l0, forecast=fc, observed=ob, valid=ok)
    print("->", a.out)


if __name__ == "__main__":
    main()
