"""Windows from the station matrix for a global multi-station LSTM."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

LOOKBACK = 72   # hours of input
HORIZON = 6     # hours ahead
MIN_INPUT_VALID = 0.7


class StationMatrix:
    def __init__(self, dataset_dir: Path, lookback: int = LOOKBACK):
        d = Path(dataset_dir)
        self.lookback = int(lookback)
        self.values = np.load(d / "values.npy", mmap_mode="r")          # [S, T] normalised later
        self.time = pd.to_datetime(np.load(d / "time.npy"))
        self.stations = pd.read_csv(d / "stations.csv", index_col="row")
        self.meta = json.loads((d / "meta.json").read_text())
        self.S, self.T = self.values.shape
        mean = self.stations["mean_m"].to_numpy(np.float32)[:, None]
        std = self.stations["std_m"].to_numpy(np.float32)[:, None]
        self.norm = ((np.asarray(self.values) - mean) / std).astype(np.float32)   # in-memory, NaN kept
        self.mask = np.isfinite(self.norm)
        self.norm_filled = np.nan_to_num(self.norm, nan=0.0)
        hours = self.time.hour.to_numpy() + self.time.minute.to_numpy() / 60
        doy = self.time.dayofyear.to_numpy() + hours / 24
        self.tfeat = np.stack([np.sin(2 * np.pi * hours / 24), np.cos(2 * np.pi * hours / 24),
                               np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)], 1).astype(np.float32)
        self.t_train_end = int(np.searchsorted(self.time.values, np.datetime64(self.meta["train_end"])))
        self.t_val_end = int(np.searchsorted(self.time.values, np.datetime64(self.meta["val_end"])))

    def split_range(self, split: str) -> tuple[int, int]:
        """Index range of forecast-origin times t0 (last observed hour) for a split."""
        if split == "train":
            return self.lookback, self.t_train_end - HORIZON
        if split == "val":
            return self.t_train_end, self.t_val_end - HORIZON
        return self.t_val_end, self.T - HORIZON - 1

    def window(self, s: np.ndarray, t0: np.ndarray):
        """Batch of windows. s, t0: int arrays [B]. t0 = index of the last observed hour."""
        idx_in = t0[:, None] + np.arange(-self.lookback + 1, 1)[None, :]      # [B, L]
        idx_out = t0[:, None] + np.arange(1, HORIZON + 1)[None, :]             # [B, H]
        x = self.norm_filled[s[:, None], idx_in]
        m = self.mask[s[:, None], idx_in].astype(np.float32)
        tf = self.tfeat[idx_in]                                                # [B, L, 4]
        feats = np.concatenate([x[..., None], m[..., None], tf], -1)           # [B, L, 6]
        y = self.norm[s[:, None], idx_out]
        ym = np.isfinite(y)
        return feats, s, np.nan_to_num(y, nan=0.0), ym

    def sample_train(self, batch: int, rng: np.random.Generator):
        lo, hi = self.split_range("train")
        out_s, out_t = [], []
        need = batch
        while need > 0:
            s = rng.integers(0, self.S, need * 2)
            t0 = rng.integers(lo, hi, need * 2)
            ok_in = self.mask[s[:, None], t0[:, None] + np.arange(-self.lookback + 1, 1)[None, :]].mean(1) >= MIN_INPUT_VALID
            ok_out = self.mask[s[:, None], t0[:, None] + np.arange(1, HORIZON + 1)[None, :]].any(1)
            ok = ok_in & ok_out
            out_s.append(s[ok][:need]); out_t.append(t0[ok][:need])
            need -= int(ok.sum())
        return self.window(np.concatenate(out_s)[:batch], np.concatenate(out_t)[:batch])

    def eval_origins(self, split: str, stride: int = 6) -> tuple[np.ndarray, np.ndarray]:
        """All (station, t0) pairs on a regular stride with a usable input window."""
        lo, hi = self.split_range(split)
        t0 = np.arange(lo, hi, stride)
        S, T0 = [], []
        for s in range(self.S):
            ok_in = self.mask[s][t0[:, None] + np.arange(-self.lookback + 1, 1)[None, :]].mean(1) >= MIN_INPUT_VALID
            ok_out = self.mask[s][t0[:, None] + np.arange(1, HORIZON + 1)[None, :]].any(1)
            tt = t0[ok_in & ok_out]
            S.append(np.full(len(tt), s)); T0.append(tt)
        return np.concatenate(S), np.concatenate(T0)


def to_torch(batch, device):
    feats, s, y, ym = batch
    return (torch.from_numpy(feats).to(device), torch.from_numpy(s).long().to(device),
            torch.from_numpy(y).to(device), torch.from_numpy(ym).to(device))
