"""Train the global LSTM and report per-horizon RMSE on val/test.

Usage: python train.py --dataset DIR --out DIR [--epochs 20 --steps 2000 --batch 1024 ...]
                       [--wind] [--future-wind] [--discharge] [--test-end 2025-12-31T23] [--stations config/stations_river.csv]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from data import HORIZON, StationMatrix, to_torch
from model import GlobalLSTM


def evaluate(model, sm: StationMatrix, split: str, device, batch: int = 4096, stride: int = 6, t_hi: int | None = None):
    model.eval()
    S, T0 = sm.eval_origins(split, stride, t_hi=t_hi)
    std = sm.stations["std_m"].to_numpy(np.float32)
    se = np.zeros((sm.S, HORIZON)); n = np.zeros((sm.S, HORIZON))
    with torch.no_grad():
        for i in range(0, len(S), batch):
            feats, fut, s, y, ym = sm.window(S[i:i + batch], T0[i:i + batch])
            f, fu, st, _, _ = to_torch((feats, fut, s, y, ym), device)
            pred = model(f, st, fu).cpu().numpy()
            err = (pred - y) * std[s][:, None]
            for h in range(HORIZON):
                np.add.at(se[:, h], s, np.where(ym[:, h], err[:, h] ** 2, 0))
                np.add.at(n[:, h], s, ym[:, h])
    rmse = np.sqrt(se.sum(0) / n.sum(0))
    per_station = pd.DataFrame({f"rmse_{h+1}h_cm": 100 * np.sqrt(se[:, h] / np.maximum(n[:, h], 1)) for h in range(HORIZON)})
    per_station["n_6h"] = n[:, -1]
    return {"rmse_model_m": rmse.tolist(), "n_samples": int(n[:, -1].sum())}, per_station


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--lookback", type=int, default=72)
    ap.add_argument("--eval-stride", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--wind", action="store_true", help="add 10 m wind (past hours) as input")
    ap.add_argument("--future-wind", action="store_true", help="also feed the wind of the 6 target hours to the head")
    ap.add_argument("--discharge", action="store_true", help="add upstream discharge as input")
    ap.add_argument("--test-end", help="last test origin (UTC hour), e.g. 2025-12-31T17, for like-for-like comparisons")
    ap.add_argument("--stations", help="CSV (source, station_id) restricting the model to one station group")
    ap.add_argument("--no-wind-stations", help="CSV (source, station_id) of stations whose wind input is set to zero")
    ap.add_argument("--rain", action="store_true", help="EXPERIMENT: add hourly rain (past hours) as input")
    ap.add_argument("--future-rain", action="store_true", help="also feed the rain of the 6 target hours to the head")
    ap.add_argument("--rain-var", default="p15", choices=["p", "p15"], help="rain at the station cell (p) or 15 km box mean (p15)")
    ap.add_argument("--rain-fc", help="future rain from a forecast product instead of observed: file stem in the dataset dir, e.g. hrrr_lag1_p45")
    ap.add_argument("--future-rain-form", default="hourly", choices=["hourly", "total"], help="future rain as 6 hourly values or one 6 h total")
    ap.add_argument("--fill", default="zero", choices=["zero", "ffill"], help="EXPERIMENT: fill missing hours with the station mean (zero) or the last valid value (ffill)")
    ap.add_argument("--delta-norm", action="store_true", help="EXPERIMENT: predict and score the change in units of each station's typical 6 h change")
    ap.add_argument("--delta-power", type=float, default=1.0, help="EXPERIMENT: 1 = scale by the 6 h-change std, 0 = by the level std, in between = geometric mix")
    ap.add_argument("--delta-feat", action="store_true", help="EXPERIMENT: extra input channel, recent level relative to the last hour in 6 h-change units")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(a.seed); rng = np.random.default_rng(a.seed)

    sm = StationMatrix(Path(a.dataset), lookback=a.lookback, use_wind=a.wind, use_future_wind=a.future_wind, use_q=a.discharge, stations=a.stations, no_wind_stations=a.no_wind_stations,
                       use_rain=a.rain, use_future_rain=a.future_rain, rain_var=a.rain_var, rain_fc=a.rain_fc, future_rain_form=a.future_rain_form,
                       fill=a.fill, delta_norm=a.delta_norm, delta_feat=a.delta_feat, delta_power=a.delta_power)
    sm.stations.reset_index().to_csv(out / "stations.csv", index=False)   # embedding order of this run
    n_val = len(sm.eval_origins("val", a.eval_stride)[0])
    assert n_val > 0, "no usable validation origins - check the input availability / origin alignment"
    print(f"validation (station, origin) pairs: {n_val}", flush=True)
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end))) if a.test_end else None
    print(f"device={device} stations={sm.S} hours={sm.T} lookback={sm.lookback} n_feat={sm.n_feat} n_future={sm.n_future} "
          f"train_end_idx={sm.t_train_end} t_end={sm.t_end} test_t_hi={t_hi}", flush=True)
    model = GlobalLSTM(sm.S, n_feat=sm.n_feat, hidden=a.hidden, layers=a.layers, n_future=sm.n_future, delta_scale=a.delta_norm).to(device)
    if a.delta_norm:
        model.rscale.copy_(torch.from_numpy(sm.rscale).to(device))
    print(f"params={sum(p.numel() for p in model.parameters()):,}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=a.epochs * a.steps, pct_start=0.1)

    best, history = np.inf, []
    for ep in range(a.epochs):
        model.train(); t0 = time.time(); losses = []
        for _ in range(a.steps):
            f, fu, s, y, ym = to_torch(sm.sample_train(a.batch, rng), device)
            pred = model(f, s, fu)
            err = (pred - y) / model.rscale[s][:, None] if a.delta_norm else pred - y      # error in 6 h-change units or in level-std units
            loss = (err ** 2 * ym).sum() / ym.sum().clamp(min=1)
            opt.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); losses.append(loss.item())
        val, _ = evaluate(model, sm, "val", device, stride=a.eval_stride)
        rec = {"epoch": ep, "train_loss": float(np.mean(losses)), "val_rmse_m": val["rmse_model_m"], "sec": round(time.time() - t0)}
        history.append(rec)
        print(json.dumps(rec), flush=True)
        if val["rmse_model_m"][-1] < best:
            best = val["rmse_model_m"][-1]
            torch.save({"state_dict": model.state_dict(), "args": vars(a), "n_stations": sm.S,
                        "n_feat": sm.n_feat, "n_future": sm.n_future}, out / "best.pt")
        torch.save({"state_dict": model.state_dict(), "args": vars(a), "n_stations": sm.S,
                    "n_feat": sm.n_feat, "n_future": sm.n_future}, out / "last.pt")      # never lose a finished training
        (out / "history.json").write_text(json.dumps(history, indent=1))

    model.load_state_dict(torch.load(out / "best.pt", map_location=device)["state_dict"])
    results = {}
    for split in ("val", "test"):
        m, per = evaluate(model, sm, split, device, stride=a.eval_stride, t_hi=t_hi if split == "test" else None)
        results[split] = m
        per = pd.concat([sm.stations[["source", "station_id", "domains", "lat", "lon"]].reset_index(drop=True), per], axis=1)
        per.to_csv(out / f"per_station_{split}.csv", index=False)
        print(split, json.dumps(m), flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
