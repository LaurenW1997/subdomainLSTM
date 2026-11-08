"""Global LSTM: shared recurrent weights, per-station embedding, direct multi-horizon head.
Optional `future` vector (e.g. forecast wind for the 6 target hours) is concatenated to the head input."""
from __future__ import annotations

import torch
import torch.nn as nn


class GlobalLSTM(nn.Module):
    def __init__(self, n_stations: int, n_feat: int = 6, emb_dim: int = 16, hidden: int = 128,
                 layers: int = 2, horizon: int = 6, dropout: float = 0.1, n_future: int = 0):
        super().__init__()
        self.n_feat, self.n_future = n_feat, n_future
        self.emb = nn.Embedding(n_stations, emb_dim)
        self.inp = nn.Linear(n_feat + emb_dim, hidden)
        self.lstm = nn.LSTM(hidden, hidden, num_layers=layers, batch_first=True,
                            dropout=dropout if layers > 1 else 0.0)
        self.head = nn.Sequential(nn.Linear(hidden + emb_dim + n_future, hidden), nn.GELU(), nn.Dropout(dropout),
                                  nn.Linear(hidden, horizon))

    def forward(self, feats: torch.Tensor, station: torch.Tensor, future: torch.Tensor | None = None) -> torch.Tensor:
        e = self.emb(station)                                   # [B, E]
        x = torch.cat([feats, e[:, None, :].expand(-1, feats.shape[1], -1)], -1)
        h, _ = self.lstm(torch.relu(self.inp(x)))
        parts = [h[:, -1], e]
        if self.n_future:
            parts.append(future)
        delta = self.head(torch.cat(parts, -1))
        return feats[:, -1, 0:1] + delta                        # residual from the last observation
