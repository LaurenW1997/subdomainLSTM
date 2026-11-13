"""Mean of several models that were trained with the same settings and differ only in the random seed.

The forecast is the mean of the members' forecasts. Evaluated on the same test origins as train.py (every 6 h up to
--test-end) and, hour by hour, in the hurricane periods (eval_storm_station.py).
Output in <out>/:
  per_station_test.csv         mean of all members, same columns as train.py writes for one model
  per_station_test_mean<k>.csv mean of the first k members (k = 1 is the first member alone)
  members.csv                  pooled test RMSE of every member alone and of the mean of the first k members
  storm_station.csv            mean of all members in the hurricane periods, per station
Usage (GPU or CPU): python eval_ensemble.py --runs-dir RUNS --runs v14_stale25 v15_seed1 v15_seed2 --dataset DATA/dataset_v6 --out RUNS/v15_mean3
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
from eval_storm_station import run as storm_run  # noqa: E402
from model import GlobalLSTM  # noqa: E402
from station_compare import load  # noqa: E402

SAME = ("lookback", "wind", "future_wind", "discharge", "rain", "future_rain", "rain_var", "rain_fc", "future_rain_form", "fill",
        "delta_norm", "delta_power", "delta_feat", "long_feat", "downstream", "upstream_stage", "stations")   # inputs every member must share


class Mean(torch.nn.Module):
    def __init__(self, models):
        super().__init__(); self.models = torch.nn.ModuleList(models)

    def forward(self, feats, station, future=None):
        return torch.stack([m(feats, station, future) for m in self.models]).mean(0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True); ap.add_argument("--runs", nargs="+", required=True); ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--test-end", default="2025-12-31T17"); ap.add_argument("--stride", type=int, default=6)
    ap.add_argument("--batch", type=int, default=4096)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    runs = [Path(a.runs_dir) / r for r in a.runs]
    sm, first = load(runs[0], Path(a.dataset), device)                       # inputs are built once, from the first member
    ref = torch.load(runs[0] / "best.pt", map_location="cpu")["args"]
    ids = pd.read_csv(runs[0] / "stations.csv", dtype=str).station_id.to_numpy()
    models = [first]
    for r in runs[1:]:
        ck = torch.load(r / "best.pt", map_location=device)
        diff = [k for k in SAME if ck["args"].get(k) != ref.get(k)]
        assert not diff, f"{r.name} was trained with other inputs: {diff}"
        assert (pd.read_csv(r / "stations.csv", dtype=str).station_id.to_numpy() == ids).all(), f"{r.name}: other station order"
        m = GlobalLSTM(ck["n_stations"], n_feat=ck.get("n_feat", 6), hidden=ck["args"]["hidden"], layers=ck["args"]["layers"], n_future=ck.get("n_future", 0),
                       delta_scale=ck["args"].get("delta_norm", False), init_state=ck["args"].get("init_state", False)).to(device)
        m.load_state_dict(ck["state_dict"]); m.eval(); models.append(m)
    N = len(models)
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))
    S, T0 = sm.eval_origins("test", a.stride, t_hi=t_hi)
    std = sm.stations["std_m"].to_numpy(np.float32)
    se_one, se_mean, n = np.zeros((N, sm.S, HORIZON)), np.zeros((N, sm.S, HORIZON)), np.zeros((sm.S, HORIZON))
    with torch.no_grad():
        for i in range(0, len(S), a.batch):
            feats, fut, s, y, ym = sm.window(S[i:i + a.batch], T0[i:i + a.batch])
            f, fu, st, _, _ = to_torch((feats, fut, s, y, ym), device)
            p = torch.stack([m(f, st, fu) for m in models]).cpu().numpy().astype(np.float64)      # [N, B, H]
            pm = np.cumsum(p, 0) / np.arange(1, N + 1)[:, None, None]                              # mean of the first k members
            w = (std[s][:, None] * ym) ** 2                                                         # 0 where the target is missing
            for h in range(HORIZON):
                n[:, h] += np.bincount(s, weights=ym[:, h], minlength=sm.S)
                for k in range(N):
                    se_one[k, :, h] += np.bincount(s, weights=(p[k, :, h] - y[:, h]) ** 2 * w[:, h], minlength=sm.S)
                    se_mean[k, :, h] += np.bincount(s, weights=(pm[k, :, h] - y[:, h]) ** 2 * w[:, h], minlength=sm.S)
    head = sm.stations[["source", "station_id", "domains", "lat", "lon"]].reset_index(drop=True)
    for k in range(N):
        per = pd.DataFrame({f"rmse_{h+1}h_cm": 100 * np.sqrt(se_mean[k, :, h] / np.maximum(n[:, h], 1)) for h in range(HORIZON)})
        per["n_6h"] = n[:, -1]
        per = pd.concat([head, per], axis=1)
        per.to_csv(out / f"per_station_test_mean{k + 1}.csv", index=False)
        if k == N - 1:
            per.to_csv(out / "per_station_test.csv", index=False)
    rows = []
    for k in range(N):
        one, mean = 100 * np.sqrt(se_one[k].sum(0) / n.sum(0)), 100 * np.sqrt(se_mean[k].sum(0) / n.sum(0))
        rows.append({"member": a.runs[k], **{f"alone_{h+1}h_cm": round(float(one[h]), 3) for h in range(HORIZON)},
                     "members_in_mean": k + 1, **{f"mean_{h+1}h_cm": round(float(mean[h]), 3) for h in range(HORIZON)}})
    d = pd.DataFrame(rows); d.to_csv(out / "members.csv", index=False)
    print(f"{len(S)} test origins, all stations (cm)")
    print(d[["member", "alone_1h_cm", "alone_3h_cm", "alone_6h_cm", "members_in_mean", "mean_1h_cm", "mean_3h_cm", "mean_6h_cm"]].to_string(index=False), flush=True)
    storm_run(sm, Mean(models), out / "storm_station.csv", device, f"mean of {N}", a.batch)


if __name__ == "__main__":
    main()
