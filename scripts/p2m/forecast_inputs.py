"""Flood map, step 5: the forecasts of the water-level model at the control points, for a period the model has not been trained on.

For every hour t0 of the period and every station of the list that the forecast model covers, the forecast issued at t0 for
t0 + 1 .. t0 + 6 h is saved in metres (station datum), next to the observations. Nothing is fitted here.
Input : --repo DIR (scripts/train and scripts/report of the forecast model), --run DIR (best.pt and member_*.pt), --dataset DIR,
        --stations CSV with columns source, station_id (stations the model does not cover get observations only)
Output: --out NPZ: t0 [T] (issue times, every --stride hours), observed_at_valid [T, 6, S], forecast [T, 6, S] (NaN where there is no observation at the issue time), valid [T + 6] (hours),
        observed [T + 6, S] (dataset values, station datum), source [S], station_id [S], covered [S]
Usage (sv7, CPU): python forecast_inputs.py --repo ../repo --run ../runs/v15r_mean5 --dataset ../data/dataset_v6 --stations FILE
                  --start 2024-09-07 --end 2024-09-17 --out FILE
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
    ap.add_argument("--repo", required=True); ap.add_argument("--run", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--stations", required=True)
    ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", required=True); ap.add_argument("--threads", type=int, default=16); ap.add_argument("--stride", type=int, default=1, help="hours between issue times (long periods)")
    ap.add_argument("--cycles-only", action="store_true", help="only the issue times the training used (00/06/12/18 UTC with forecast rainfall); default: every hour with an observation in hand")
    a = ap.parse_args()
    assert not Path(a.out).exists(), f"{a.out} exists"
    for d in ("train", "report"):
        sys.path.insert(0, str(Path(a.repo).resolve() / "scripts" / d))
    from data import HORIZON, to_torch  # noqa: E402
    from station_compare import load  # noqa: E402

    torch.set_num_threads(a.threads); device = torch.device("cpu")
    sm, model = load(Path(a.run), Path(a.dataset), device)
    st = sm.stations.reset_index(drop=True); row = {(s, str(i)): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    lo_t, hi_t = sm.split_range("test"); print(f"forecast model: {len(st)} stations; test period {sm.time[lo_t]} .. {sm.time[hi_t - 1]}")
    want = pd.read_csv(a.stations, dtype={"station_id": str})[["source", "station_id"]].drop_duplicates().reset_index(drop=True)
    i0, i1 = int(np.searchsorted(sm.time.values, np.datetime64(a.start))), int(np.searchsorted(sm.time.values, np.datetime64(a.end)))
    assert lo_t <= i0 and i1 + HORIZON <= hi_t, "the period is not inside the test period of the forecast model"
    t0 = np.arange(i0, i1, a.stride); T, S = len(t0), len(want)
    F = np.full((T, HORIZON, S), np.nan, np.float32); O = np.full((i1 - i0 + HORIZON, S), np.nan, np.float32); cov = np.zeros(S, bool)

    ds = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); assert tm[i0] == sm.time[i0], "the time axis of the dataset differs from the one of the model"
    drow = {(s, str(i)): k for k, (s, i) in enumerate(zip(ds.source, ds.station_id))}
    with torch.no_grad():
        for k, r in enumerate(want.itertuples()):
            key = (r.source, r.station_id)
            if key in drow:
                O[:, k] = np.asarray(vals[drow[key], i0:i1 + HORIZON], np.float32)
            if key not in row:
                continue
            s = row[key]; cov[k] = True; ss = np.full(T, s)
            ok = sm._ok(ss, t0) if a.cycles_only else sm.mask[s, t0].copy()      # as eval_storm_station.py: every hour with an observation in hand
            if not ok.any():
                continue
            feats, fut, sx, y, ym = sm.window(ss[ok], t0[ok]); f, fu, sxx, _, _ = to_torch((feats, fut, sx, y, ym), device)
            F[ok, :, k] = model(f, sxx, fu).cpu().numpy() * float(st.std_m[s]) + float(st.mean_m[s])
    n_ok = np.isfinite(F[:, 0]).sum(0)
    print(f"{S} stations asked, {int(cov.sum())} covered by the forecast model; {T} issue times {sm.time[i0]} .. {sm.time[i1 - 1]}; "
          f"issue times with a forecast per covered station: median {int(np.median(n_ok[cov]))}, fewest {int(n_ok[cov].min())}")
    for h in (1, 3, 6):                                                    # the error of the forecasts themselves, for reference
        e = F[:, h - 1] - O[(t0 - i0) + h]; print(f"  lead {h} h: RMSE of the forecasts at the covered stations {100 * float(np.sqrt(np.nanmean(e[:, cov] ** 2))):.1f} cm")
    np.savez_compressed(a.out, t0=np.array(sm.time[t0].strftime("%Y-%m-%d %H:%M"), dtype=str), observed_at_valid=np.stack([O[(t0 - i0) + h] for h in range(1, HORIZON + 1)], 1), valid=np.array(sm.time[i0:i1 + HORIZON].strftime("%Y-%m-%d %H:%M"), dtype=str),
                        forecast=F, observed=O, source=want.source.to_numpy(str), station_id=want.station_id.to_numpy(str), covered=cov)
    print("->", a.out)


if __name__ == "__main__":
    main()
