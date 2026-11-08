"""Train the global LSTM and report per-horizon RMSE on val/test.

Usage: python train.py --dataset DIR --out DIR [--epochs 20 --steps 2000 --batch 1024 ...]
                       [--wind] [--future-wind] [--discharge] [--test-end 2025-12-31T23]
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
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(a.seed); rng = np.random.default_rng(a.seed)

    sm = StationMatrix(Path(a.dataset), lookback=a.lookback, use_wind=a.wind, use_future_wind=a.future_wind, use_q=a.discharge)
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end))) if a.test_end else None
    print(f"device={device} stations={sm.S} hours={sm.T} lookback={sm.lookback} n_feat={sm.n_feat} n_future={sm.n_future} "
          f"train_end_idx={sm.t_train_end} t_end={sm.t_end} test_t_hi={t_hi}", flush=True)
    model = GlobalLSTM(sm.S, n_feat=sm.n_feat, hidden=a.hidden, layers=a.layers, n_future=sm.n_future).to(device)
    print(f"params={sum(p.numel() for p in model.parameters()):,}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=a.epochs * a.steps, pct_start=0.1)

    best, history = np.inf, []
    for ep in range(a.epochs):
        model.train(); t0 = time.time(); losses = []
        for _ in range(a.steps):
            f, fu, s, y, ym = to_torch(sm.sample_train(a.batch, rng), device)
            pred = model(f, s, fu)
            loss = ((pred - y) ** 2 * ym).sum() / ym.sum().clamp(min=1)
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
