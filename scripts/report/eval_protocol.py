"""Evaluation of a group of models that differ only in the random seed: every member and their mean, per station.

Next to the RMSE over all forecasts this writes what a small change in the average hides:
  events      forecasts whose observed 6 h change is among the largest of that station: |change| >= the --event-q quantile
              (default 99%) of the station's |6 h change| in the TRAINING period; rises and falls also separately
  hurricanes  forecast times in the hurricane periods of the test years (eval_stale_origin.STORMS)
  timing      on the rises (change >= the --rise-q quantile, default 95%): the shift k (0 .. 8 h) that minimises the RMSE
              between the 6 h forecast valid at hour t and the observation at t - k, as in lag_check.py. 0 h = the forecast
              rises with the observation, 6 h = it only repeats the level at the forecast time. Also the mean observed and
              forecast 6 h rise.
All of it on the test origins of train.py at 00/06/12/18 UTC (the hours the forecast rainfall was extracted for), stations
with real-time data (no CRMS). RMSE in cm.
Output: <out>/protocol_station.csv   one row per model (each member, "mean") and station
Usage (GPU or CPU): python eval_protocol.py --runs-dir RUNS --runs v14_stale25 v15r_seed1 ... --dataset DATA/dataset_v6 --out RUNS/protocol_<name>
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
from eval_ensemble import SAME  # noqa: E402
from eval_stale_origin import STORMS  # noqa: E402
from station_compare import build, load  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
MAXLAG = 8


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True); ap.add_argument("--runs", nargs="+", required=True); ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--test-end", default="2025-12-31T17"); ap.add_argument("--stride", type=int, default=6)
    ap.add_argument("--batch", type=int, default=4096); ap.add_argument("--event-q", type=float, default=0.99); ap.add_argument("--rise-q", type=float, default=0.95)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(32)
    runs = [Path(a.runs_dir) / r for r in a.runs]
    sm, first = load(runs[0], Path(a.dataset), device)
    ref = torch.load(runs[0] / "best.pt", map_location="cpu")["args"]
    ids = pd.read_csv(runs[0] / "stations.csv", dtype=str).station_id.to_numpy()
    models = [first]
    for r in runs[1:]:
        ck = torch.load(r / "best.pt", map_location=device)
        diff = [k for k in SAME if (ck["args"].get(k) or None) != (ref.get(k) or None)]
        assert not diff, f"{r.name} was trained with other inputs: {diff}"
        assert (pd.read_csv(r / "stations.csv", dtype=str).station_id.to_numpy() == ids).all(), f"{r.name}: other station order"
        models.append(build(ck, device))
    N = len(models); names = list(a.runs) + ["mean"]

    st = sm.stations.reset_index(drop=True)
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    typ = st[["source", "station_id"]].astype(str).merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left").type.fillna("other").to_numpy()
    oper = (st.source != "CRMS").to_numpy()
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))
    lo = sm.split_range("test")[0]; t_lo = -(-lo // a.stride) * a.stride          # 00/06/12/18 UTC for every group
    S, T0 = sm.eval_origins("test", a.stride, t_lo=t_lo, t_hi=t_hi)
    S, T0 = S[oper[S]], T0[oper[S]]
    n = len(S)
    std = 100 * st.std_m.to_numpy(np.float64)                                     # z-score -> cm

    # thresholds of a large 6 h change, per station, from the training period (z-score units)
    thr_ev, thr_rise = np.full(sm.S, np.inf), np.full(sm.S, np.inf)
    for s in np.where(oper)[0]:
        x = sm.norm[s, :sm.t_train_end]
        d = np.abs(x[HORIZON:] - x[:-HORIZON]); d = d[np.isfinite(d)]
        if len(d) >= 1000:
            thr_ev[s], thr_rise[s] = np.quantile(d, a.event_q), np.quantile(d, a.rise_q)

    pred = np.zeros((N + 1, n, HORIZON), np.float32); y = np.zeros((n, HORIZON), np.float32); ym = np.zeros((n, HORIZON), bool)
    with torch.no_grad():
        for i in range(0, n, a.batch):
            feats, fut, s, yy, mm = sm.window(S[i:i + a.batch], T0[i:i + a.batch])
            f, fu, sx, _, _ = to_torch((feats, fut, s, yy, mm), device)
            p = torch.stack([m(f, sx, fu) for m in models]).cpu().numpy()
            pred[:N, i:i + a.batch] = p; pred[N, i:i + a.batch] = p.mean(0); y[i:i + a.batch] = yy; ym[i:i + a.batch] = mm
    print(f"{len(a.runs)} models, {n} forecasts at {len(np.unique(S))} stations", flush=True)

    last = sm.norm[S, T0]                                                         # NaN when the newest hour is missing
    d6 = np.where(ym[:, -1], y[:, -1], np.nan) - last
    event = np.abs(d6) >= thr_ev[S]
    rise, fall = event & (d6 > 0), event & (d6 < 0)
    obs_lag = np.stack([sm.norm[S, T0 + HORIZON - k] for k in range(MAXLAG + 1)], 1)          # observation at valid time - k h
    timing = (d6 >= thr_rise[S]) & np.isfinite(obs_lag).all(1)
    storm = np.zeros(n, bool)
    dom = st.domains.astype(str).to_numpy()
    for _, d0, d1, doms in STORMS:
        i0, i1 = np.searchsorted(sm.time.values, np.datetime64(d0)), np.searchsorted(sm.time.values, np.datetime64(d1))
        storm |= (T0 >= i0) & (T0 < i1) & np.array([any(x in dd for x in doms) for dd in dom])[S]
    print(f"events {int(event.sum())} (rises {int(rise.sum())}, falls {int(fall.sum())}), rises used for the timing {int(timing.sum())}, in the hurricane periods {int(storm.sum())}", flush=True)

    def per_station(v, w):          # sum of v over the forecasts in w, per station
        return np.bincount(S[w], weights=v[w], minlength=sm.S)

    head = st[["source", "station_id", "domains"]].copy(); head["type"] = typ
    keep = np.where(oper)[0]
    frames = []
    for j, name in enumerate(names):
        e = (pred[j].astype(np.float64) - y) * std[S][:, None]                    # cm
        r = head.copy(); r.insert(0, "model", name)
        cnt = lambda w: np.bincount(S[w], minlength=sm.S)
        with np.errstate(all="ignore"):
            for h in range(1, HORIZON + 1):
                w = ym[:, h - 1]
                r[f"rmse_{h}h_cm"] = np.sqrt(per_station(e[:, h - 1] ** 2, w) / cnt(w))
            r["n_6h"] = cnt(ym[:, -1])
            for lab, sel, leads in (("event", event, (1, 3, 6)), ("rise", rise, (6,)), ("fall", fall, (6,)), ("storm", storm, (1, 3, 6))):
                for h in leads:
                    w = sel & ym[:, h - 1]
                    r[f"rmse_{lab}_{h}h_cm"] = np.sqrt(per_station(e[:, h - 1] ** 2, w) / cnt(w))
                w = sel & ym[:, -1]
                r[f"n_{lab}"] = cnt(w); r[f"bias_{lab}_6h_cm"] = per_station(e[:, -1], w) / cnt(w)
            # timing on the rises: squared error of the 6 h forecast against the observation k hours earlier
            el = (pred[j][:, -1:].astype(np.float64) - obs_lag) * std[S][:, None]
            sse = np.stack([per_station(el[:, k] ** 2, timing) for k in range(MAXLAG + 1)], 1)
            r["n_timing"] = cnt(timing)
            for k in range(MAXLAG + 1):
                r[f"lag_sse_{k}"] = sse[:, k]
            r["lag_h"] = np.where(r.n_timing > 0, sse.argmin(1), np.nan)
            r["rise_obs_cm"] = per_station(d6 * std[S], timing) / cnt(timing)
            r["rise_fc_cm"] = per_station((pred[j][:, -1].astype(np.float64) - last) * std[S], timing) / cnt(timing)
        frames.append(r.iloc[keep])
    d = pd.concat(frames, ignore_index=True)
    d.round(4).to_csv(out / "protocol_station.csv", index=False)
    for name in names:
        x = d[(d.model == name) & (d.n_6h >= 720)]
        pool = lambda c, nn: float(np.sqrt((x[nn] * x[c] ** 2).sum() / x[nn].sum()))
        lag = x.lag_h[x.n_timing >= 10]
        print(f"{name:26s} {len(x)} stations  6 h RMSE all {pool('rmse_6h_cm', 'n_6h'):6.2f}  events {pool('rmse_event_6h_cm', 'n_event'):6.2f}  "
              f"hurricanes {pool('rmse_storm_6h_cm', 'n_storm'):6.2f}  lag {lag.mean():.2f} h ({len(lag)} stations)", flush=True)


if __name__ == "__main__":
    main()
