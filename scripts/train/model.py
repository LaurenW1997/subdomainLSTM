"""Global LSTM: shared recurrent weights, per-station embedding, direct multi-horizon head.
Optional `future` vector (e.g. forecast wind for the 6 target hours) is concatenated to the head input."""
from __future__ import annotations

import torch
import torch.nn as nn


class GlobalLSTM(nn.Module):
    def __init__(self, n_stations: int, n_feat: int = 6, emb_dim: int = 16, hidden: int = 128,
                 layers: int = 2, horizon: int = 6, dropout: float = 0.1, n_future: int = 0, delta_scale: bool = False,
                 init_state: bool = False):
        super().__init__()
        self.n_feat, self.n_future = n_feat, n_future
        # EXPERIMENT (--delta-norm): the head predicts the change in units of each station's typical 6 h change;
        # rscale[s] = std of the 6 h change / std of the level (set from the training data, saved with the weights)
        self.delta_scale = delta_scale
        if delta_scale:
            self.register_buffer("rscale", torch.ones(n_stations))
        self.emb = nn.Embedding(n_stations, emb_dim)
        # EXPERIMENT (--init-state): the LSTM starts each window from a state of its own for every station (made from the
        # station embedding) instead of from zero
        self.layers, self.hidden = layers, hidden
        self.init = nn.Linear(emb_dim, 2 * layers * hidden) if init_state else None
        self.inp = nn.Linear(n_feat + emb_dim, hidden)
        self.lstm = nn.LSTM(hidden, hidden, num_layers=layers, batch_first=True,
                            dropout=dropout if layers > 1 else 0.0)
        self.head = nn.Sequential(nn.Linear(hidden + emb_dim + n_future, hidden), nn.GELU(), nn.Dropout(dropout),
                                  nn.Linear(hidden, horizon))

    def forward(self, feats: torch.Tensor, station: torch.Tensor, future: torch.Tensor | None = None) -> torch.Tensor:
        e = self.emb(station)                                   # [B, E]
        x = torch.cat([feats, e[:, None, :].expand(-1, feats.shape[1], -1)], -1)
        state = None
        if self.init is not None:
            z = torch.tanh(self.init(e)).view(-1, 2, self.layers, self.hidden).permute(1, 2, 0, 3).contiguous()   # [2, layers, B, H]
            state = (z[0], z[1])
        h, _ = self.lstm(torch.relu(self.inp(x)), state)
        parts = [h[:, -1], e]
        if self.n_future:
            parts.append(future)
        delta = self.head(torch.cat(parts, -1))
        if self.delta_scale:
            delta = delta * self.rscale[station][:, None]
        return feats[:, -1, 0:1] + delta                        # residual from the last observation
