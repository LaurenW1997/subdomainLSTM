"""Re-test the rain model with HRRR *forecast* rain in the future-6-h slot instead of AORC observed rain.

The rain experiment (deliverable 13) gave the model the next 6 h of AORC observed rain, i.e. a perfect rain forecast.
Here the same trained model is evaluated on the same 6-hourly test origins with the future rain replaced by
  - HRRR forecast rain from the cycle issued at the origin (lag 0, optimistic: that cycle is really available ~1 h later)
  - HRRR forecast rain from the cycle issued 1 h before the origin (lag 1, realistic)
  - zero future rain (what the model does when told "no rain coming")
and, for reference on exactly the same origins, the unchanged model (AORC future rain) and the current operational model (no rain).
Origins are restricted to those where every variant has its inputs (all 6 HRRR hours present for every lag).

Writes runs/<name>/per_station_test.csv + results.json for each variant so compare_variants.py can be used:
  <run>_sameorig (AORC future), <run>_hrrr0, <run>_hrrr1, <run>_norain, <ref>_sameorig
Usage (sv7, CPU): python eval_hrrr_rain.py --run v7_rain_p15 --ref v6_wind_q --dataset DATA/dataset_v5 --hrrr-dir DATA/precip --lags 0 1 --test-end 2025-12-31T17
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HORIZON, to_torch  # noqa: E402
from station_compare import load  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def per_station(model, sm, S, T0, device, patch=None, batch=4096):
    """RMSE per station and horizon over the given (station, origin) pairs; patch(future, s, t0) may edit the future vector."""
    std = sm.stations["std_m"].to_numpy(np.float32)
    se = np.zeros((sm.S, HORIZON)); n = np.zeros((sm.S, HORIZON))
    with torch.no_grad():
        for i in range(0, len(S), batch):
            s, t0 = S[i:i + batch], T0[i:i + batch]
            feats, fut, s, y, ym = sm.window(s, t0)
            if patch is not None:
                fut = patch(fut, s, t0)
            f, fu, st, _, _ = to_torch((feats, fut, s, y, ym), device)
            err = (model(f, st, fu).cpu().numpy() - y) * std[s][:, None]
            for h in range(HORIZON):
                np.add.at(se[:, h], s, np.where(ym[:, h], err[:, h] ** 2, 0)); np.add.at(n[:, h], s, ym[:, h])
    per = pd.DataFrame({f"rmse_{h+1}h_cm": 100 * np.sqrt(se[:, h] / np.maximum(n[:, h], 1)) for h in range(HORIZON)})
    per["n_6h"] = n[:, -1]
    per = pd.concat([sm.stations[["source", "station_id", "domains"]].reset_index(drop=True), per], axis=1)
    return {"rmse_model_m": np.sqrt(se.sum(0) / n.sum(0)).tolist(), "n_samples": int(n[:, -1].sum())}, per


def save(name: str, res: dict, per: pd.DataFrame, note: str) -> None:
    d = REPO / "runs" / name; d.mkdir(parents=True, exist_ok=True)
    per.to_csv(d / "per_station_test.csv", index=False)
    (d / "results.json").write_text(json.dumps({"test": res, "note": note}, indent=1))
    print(f"{name:28s} 6 h RMSE {100 * res['rmse_model_m'][-1]:.2f} cm  n={res['n_samples']}  [{note}]", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="v7_rain_p15"); ap.add_argument("--ref", default="v6_wind_q")
    ap.add_argument("--dataset", required=True); ap.add_argument("--hrrr-dir", required=True)
    ap.add_argument("--lags", type=int, nargs="+", default=[0, 1]); ap.add_argument("--stride", type=int, default=6)
    ap.add_argument("--test-end", default="2025-12-31T17")
    a = ap.parse_args()
    device = torch.device("cpu"); torch.set_num_threads(32)
    sm, model = load(REPO / "runs" / a.run, Path(a.dataset), device)
    smr, ref = load(REPO / "runs" / a.ref, Path(a.dataset), device)
    assert (sm.stations.station_id.to_numpy() == smr.stations.station_id.to_numpy()).all()
    assert sm.use_future_rain, "the run must use future rain"
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))
    S, T0 = sm.eval_origins("test", a.stride, t_hi=t_hi)
    S2, T02 = smr.eval_origins("test", a.stride, t_hi=t_hi)
    both = pd.MultiIndex.from_arrays([S, T0]).isin(pd.MultiIndex.from_arrays([S2, T02]))
    S, T0 = S[both], T0[both]
    # HRRR forecast rain by valid hour, mm over the hour -> same log1p scaling as the model's AORC rain
    idx_out = T0[:, None] + np.arange(1, HORIZON + 1)[None, :]
    fc = {}
    keep = np.ones(len(S), bool)
    for lag in a.lags:
        r = np.load(Path(a.hrrr_dir) / f"hrrr_lag{lag}_{sm.rain_var}.npy", mmap_mode="r")[sm.rows]
        fc[lag] = np.log1p(np.nan_to_num(np.clip(r, 0, None), nan=np.nan))
        keep &= np.isfinite(fc[lag][S[:, None], idx_out]).all(1)
    S, T0 = S[keep], T0[keep]
    orig = pd.Series(T0).nunique()
    print(f"{len(S)} (station, origin) pairs on {orig} origins with HRRR lags {a.lags} complete; dropped {int((~keep).sum())} for missing HRRR", flush=True)
    nf = HORIZON   # the future rain is the last HORIZON entries of the future vector

    def patch_with(arr):
        def patch(fut, s, t0):
            fut = fut.copy()
            fut[:, -nf:] = np.nan_to_num(arr[s[:, None], t0[:, None] + np.arange(1, HORIZON + 1)[None, :]], nan=0.0)
            return fut
        return patch

    def patch_zero(fut, s, t0):
        fut = fut.copy(); fut[:, -nf:] = 0.0; return fut

    res, per = per_station(model, sm, S, T0, device); save(f"{a.run}_sameorig", res, per, "AORC observed future rain (perfect forecast), common origins")
    for lag in a.lags:
        res, per = per_station(model, sm, S, T0, device, patch_with(fc[lag])); save(f"{a.run}_hrrr{lag}", res, per, f"HRRR forecast rain, cycle {lag} h before the origin")
    res, per = per_station(model, sm, S, T0, device, patch_zero); save(f"{a.run}_norain", res, per, "future rain set to zero")
    res, per = per_station(ref, smr, S, T0, device); save(f"{a.ref}_sameorig", res, per, "operational model (no rain), common origins")


if __name__ == "__main__":
    main()
