"""Does the model still work when the rainfall of the PAST 72 h comes from HRRR instead of AORC?

The model was trained with AORC rainfall (a reanalysis, not available in real time) in the look-back window and the HRRR
forecast total in the 6 target hours. Operationally the look-back rainfall has to come from a real-time product. Here the
trained model is evaluated on the test origins with the look-back rainfall replaced by
  - HRRR short-range forecast rainfall (leads 1-6 h of the 00/06/12/18 UTC cycles; hrrr_lag0_p15.npy) - what HRRR can
    give in real time; pessimistic, because operationally each past hour would use the 1 h lead of the hourly cycles
  - no rainfall information at all (rain 0, mask 0)
on exactly the same (station, origin) pairs as the unchanged model.
Writes runs/<run>_pastaorc, runs/<run>_past<tag>, runs/<run>_pastnone (per_station_test.csv + results.json). With another
product (--past PATH --tag mrms --only) the pairs are those where that product covers the look-back window, and the
unchanged model on the same pairs goes to runs/<run>_pastaorc_on<tag>.
Usage (sv7, CPU): python eval_past_rain.py --run v11_fc1_t45 --dataset DATA/dataset_v6 --past hrrr_lag0_p15 --test-end 2025-12-31T17
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import MIN_INPUT_VALID  # noqa: E402
from eval_hrrr_rain import per_station, save  # noqa: E402
from station_compare import load  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="v11_fc1_t45"); ap.add_argument("--dataset", required=True)
    ap.add_argument("--past", default="hrrr_lag0_p15", help="file stem in the dataset dir, or path of a .npy: rainfall by valid hour, mm/h")
    ap.add_argument("--tag", default="hrrr", help="name of the alternative product: results go to runs/<run>_past<tag>")
    ap.add_argument("--only", action="store_true", help="only the alternative product (skip the AORC and no-rainfall reference runs)")
    ap.add_argument("--test-end", default="2025-12-31T17"); ap.add_argument("--stride", type=int, default=6)
    a = ap.parse_args()
    device = torch.device("cpu"); torch.set_num_threads(32)
    sm, model = load(REPO / "runs" / a.run, Path(a.dataset), device)
    assert sm.use_rain
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))
    S, T0 = sm.eval_origins("test", a.stride, t_hi=t_hi)
    alt = np.load(a.past if a.past.endswith(".npy") else Path(a.dataset) / f"{a.past}.npy", mmap_mode="r")[sm.rows].astype(np.float32)
    amask = np.isfinite(alt)
    idx_in = T0[:, None] + np.arange(-sm.lookback + 1, 1)[None, :]
    keep = np.concatenate([amask[S[i:i + 20000, None], idx_in[i:i + 20000]].mean(1) >= MIN_INPUT_VALID for i in range(0, len(S), 20000)])
    print(f"{len(S)} pairs, {int(keep.sum())} with the alternative past rainfall", flush=True)
    S, T0 = S[keep], T0[keep]
    aorc_rain, aorc_mask = sm.rain, sm.rmask
    # how different are the two products where both exist (test period, hourly, all stations)
    lo = sm.split_range("test")[0]
    x = np.expm1(aorc_rain[:, lo:t_hi]); y = np.nan_to_num(np.clip(alt[:, lo:t_hi], 0, None)); ok = aorc_mask[:, lo:t_hi] & amask[:, lo:t_hi]
    print(f"hourly rainfall, AORC vs alternative: mean {x[ok].mean():.3f} vs {y[ok].mean():.3f} mm/h, correlation {np.corrcoef(x[ok], y[ok])[0, 1]:.2f}; "
          f"72 h totals correlation {np.corrcoef(np.add.reduceat(np.where(ok, x, 0), np.arange(0, x.shape[1], 72), 1).ravel(), np.add.reduceat(np.where(ok, y, 0), np.arange(0, y.shape[1], 72), 1).ravel())[0, 1]:.2f}", flush=True)
    res, per = per_station(model, sm, S, T0, device)
    save(f"{a.run}_pastaorc" + ("" if a.tag == "hrrr" else f"_on{a.tag}"), res, per, "unchanged: AORC rainfall in the look-back window")
    sm.rain = np.log1p(np.nan_to_num(np.clip(alt, 0, None))); sm.rmask = amask
    res, per = per_station(model, sm, S, T0, device)
    save(f"{a.run}_past{a.tag}", res, per, f"look-back rainfall from {a.past}")
    if a.only:
        return
    sm.rain = np.zeros_like(aorc_rain); sm.rmask = np.zeros_like(aorc_mask)
    res, per = per_station(model, sm, S, T0, device)
    save(f"{a.run}_pastnone", res, per, "no look-back rainfall (0, masked)")


if __name__ == "__main__":
    main()
