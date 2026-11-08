"""Train the global LSTM and evaluate against persistence on val/test.

Usage: python train.py --dataset DIR --out DIR [--epochs 20 --steps 2000 --batch 1024 ...]
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


def evaluate(model, sm: StationMatrix, split: str, device, batch: int = 4096, stride: int = 6):
    model.eval()
    S, T0 = sm.eval_origins(split, stride)
    std = sm.stations["std_m"].to_numpy(np.float32)
    se_model = np.zeros((sm.S, HORIZON)); se_pers = np.zeros((sm.S, HORIZON)); n = np.zeros((sm.S, HORIZON))
    with torch.no_grad():
        for i in range(0, len(S), batch):
            feats, s, y, ym = sm.window(S[i:i + batch], T0[i:i + batch])
            f, st, yy, mm = to_torch((feats, s, y, ym), device)
            pred = model(f, st).cpu().numpy()
            last = feats[:, -1, 0:1]
            err_m = (pred - y) * std[s][:, None]; err_p = (last - y) * std[s][:, None]
            for h in range(HORIZON):
                np.add.at(se_model[:, h], s, np.where(ym[:, h], err_m[:, h] ** 2, 0))
                np.add.at(se_pers[:, h], s, np.where(ym[:, h], err_p[:, h] ** 2, 0))
                np.add.at(n[:, h], s, ym[:, h])
    rmse_model = np.sqrt(se_model.sum(0) / n.sum(0)); rmse_pers = np.sqrt(se_pers.sum(0) / n.sum(0))
    per_station = pd.DataFrame({
        "rmse_6h_model": np.sqrt(se_model[:, -1] / np.maximum(n[:, -1], 1)),
        "rmse_6h_persist": np.sqrt(se_pers[:, -1] / np.maximum(n[:, -1], 1)),
        "n_6h": n[:, -1],
    })
    return {"rmse_model_m": rmse_model.tolist(), "rmse_persistence_m": rmse_pers.tolist(),
            "n_samples": int(n[:, -1].sum())}, per_station


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
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(a.seed); rng = np.random.default_rng(a.seed)

    sm = StationMatrix(Path(a.dataset), lookback=a.lookback)
    print(f"device={device} stations={sm.S} hours={sm.T} lookback={sm.lookback} train_end_idx={sm.t_train_end}", flush=True)
    model = GlobalLSTM(sm.S, hidden=a.hidden, layers=a.layers).to(device)
    print(f"params={sum(p.numel() for p in model.parameters()):,}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=a.epochs * a.steps, pct_start=0.1)

    best, history = np.inf, []
    for ep in range(a.epochs):
        model.train(); t0 = time.time(); losses = []
        for _ in range(a.steps):
            f, s, y, ym = to_torch(sm.sample_train(a.batch, rng), device)
            pred = model(f, s)
            loss = ((pred - y) ** 2 * ym).sum() / ym.sum().clamp(min=1)
            opt.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); losses.append(loss.item())
        val, _ = evaluate(model, sm, "val", device, stride=a.eval_stride)
        rec = {"epoch": ep, "train_loss": float(np.mean(losses)), "val_rmse_m": val["rmse_model_m"],
               "val_persist_m": val["rmse_persistence_m"], "sec": round(time.time() - t0)}
        history.append(rec)
        print(json.dumps(rec), flush=True)
        if val["rmse_model_m"][-1] < best:
            best = val["rmse_model_m"][-1]
            torch.save({"state_dict": model.state_dict(), "args": vars(a), "n_stations": sm.S}, out / "best.pt")
        (out / "history.json").write_text(json.dumps(history, indent=1))

    model.load_state_dict(torch.load(out / "best.pt", map_location=device)["state_dict"])
    results = {}
    for split in ("val", "test"):
        m, per = evaluate(model, sm, split, device, stride=a.eval_stride)
        results[split] = m
        per = pd.concat([sm.stations[["source", "station_id", "domains", "lat", "lon"]], per], axis=1)
        per.to_csv(out / f"per_station_{split}.csv", index=False)
        print(split, json.dumps(m), flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
