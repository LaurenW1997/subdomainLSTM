"""Windows from the station matrix for a global multi-station LSTM.

Base inputs per hour: normalised water level, its mask, 4 time features.
Optional extras (files next to values.npy, same [S, T] layout, NaN = missing):
  wind_u.npy / wind_v.npy   10 m wind at the station (m/s, scaled by WIND_SCALE)
  q.npy                     normalised log discharge of the station's upstream gauge
Flags: use_wind adds (u, v, wind mask) to every input hour and, with use_future_wind,
also the wind of the 6 target hours (fed to the head); use_q adds (q, q mask).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

LOOKBACK = 72   # hours of input
HORIZON = 6     # hours ahead
LONG_HOURS = 720  # length of the long-history summaries (--long-feat)
FC_STRIDE = 6   # hours between the origins a forecast-rain product was extracted for (hrrr_precip.py --stride)
MIN_INPUT_VALID = 0.7
WIND_SCALE = 10.0   # m/s -> O(1)


class StationMatrix:
    def __init__(self, dataset_dir: Path, lookback: int = LOOKBACK, use_wind: bool = False,
                 use_future_wind: bool = False, use_q: bool = False, stations: Path | str | None = None,
                 no_wind_stations: Path | str | None = None, use_rain: bool = False, use_future_rain: bool = False,
                 rain_var: str = "p15", rain_fc: str | None = None, future_rain_form: str = "hourly",
                 fill: str = "zero", delta_norm: bool = False, delta_feat: bool = False, delta_power: float = 1.0,
                 long_feat: bool = False, neighbor_map: Path | str | None = None, use_ds: bool = False, use_us: bool = False):
        d = Path(dataset_dir)
        self.lookback = int(lookback)
        self.use_wind, self.use_future_wind, self.use_q = use_wind, use_wind and use_future_wind, use_q
        self.use_rain, self.use_future_rain, self.rain_var = use_rain, use_rain and use_future_rain, rain_var
        self.rain_fc, self.future_rain_form = rain_fc, future_rain_form      # future-rain source (None = observed) and form (hourly / 6 h total)
        self.values = np.load(d / "values.npy", mmap_mode="r")          # [S, T] metres
        self.time = pd.to_datetime(np.load(d / "time.npy"))
        self.stations = pd.read_csv(d / "stations.csv", index_col="row", dtype={"station_id": str})
        self.meta = json.loads((d / "meta.json").read_text())
        # optional subset of stations (CSV with source, station_id): a separate model for one station group
        self.rows = np.arange(self.values.shape[0])
        if stations:
            sub = pd.read_csv(stations, dtype=str)
            key = set(zip(sub.source, sub.station_id))
            keep = np.array([(s, str(i)) in key for s, i in zip(self.stations.source, self.stations.station_id)])
            self.rows = np.where(keep)[0]
            self.values = np.asarray(self.values)[self.rows]
            self.stations = self.stations.iloc[self.rows].reset_index(drop=True)
            self.stations.index.name = "row"
            self.stations["dataset_row"] = self.rows
        self.S, self.T = self.values.shape
        mean = self.stations["mean_m"].to_numpy(np.float32)[:, None]
        std = self.stations["std_m"].to_numpy(np.float32)[:, None]
        self.norm = ((np.asarray(self.values) - mean) / std).astype(np.float32)   # in-memory, NaN kept
        self.mask = np.isfinite(self.norm)
        self.norm_filled = np.nan_to_num(self.norm, nan=0.0)
        self.fill, self.delta_norm, self.delta_feat = fill, delta_norm, delta_feat
        if fill == "ffill":   # EXPERIMENT: a missing hour takes the last valid value instead of the station mean (the mask channel still marks it)
            idx = np.where(self.mask, np.arange(self.T, dtype=np.int32)[None, :], 0).astype(np.int32)
            np.maximum.accumulate(idx, axis=1, out=idx)
            self.norm_filled = np.nan_to_num(np.take_along_axis(self.norm, idx, 1), nan=0.0)
            del idx
        hours = self.time.hour.to_numpy() + self.time.minute.to_numpy() / 60
        doy = self.time.day_of_year.to_numpy() + hours / 24
        self.tfeat = np.stack([np.sin(2 * np.pi * hours / 24), np.cos(2 * np.pi * hours / 24),
                               np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)], 1).astype(np.float32)
        self.t_train_end = int(np.searchsorted(self.time.values, np.datetime64(self.meta["train_end"])))
        self.t_val_end = int(np.searchsorted(self.time.values, np.datetime64(self.meta["val_end"])))
        self.t_end = self.T
        # typical 6 h change of each station in z-score units (train period): the scale of what a 6 h forecast has to get right
        dd = self.norm[:, HORIZON:self.t_train_end] - self.norm[:, :self.t_train_end - HORIZON]
        with np.errstate(all="ignore"):
            r = np.nanstd(dd, axis=1)
        del dd
        self.rscale = np.clip(np.where(np.isfinite(r) & (r > 0), r, 1.0), 1e-3, None).astype(np.float32)
        # delta_power < 1 moves the scale part of the way from the level std (0) to the 6 h-change std (1)
        self.rscale = (self.rscale ** float(delta_power)).astype(np.float32)
        # stations whose wind input is switched off (far-inland rivers where wind only adds noise):
        # u, v and the wind mask are set to 0 for them, and the wind-availability rule in _ok is skipped
        self.wind_off = np.zeros(self.S, bool)
        if no_wind_stations:
            sub = pd.read_csv(no_wind_stations, dtype=str)
            key = set(zip(sub.source, sub.station_id))
            self.wind_off = np.array([(s, str(i)) in key for s, i in zip(self.stations.source, self.stations.station_id)])
        if use_wind:
            u = np.load(d / "wind_u.npy", mmap_mode="r")[self.rows].astype(np.float32) / WIND_SCALE
            v = np.load(d / "wind_v.npy", mmap_mode="r")[self.rows].astype(np.float32) / WIND_SCALE
            self.wmask = np.isfinite(u) & np.isfinite(v)
            self.u, self.v = np.nan_to_num(u), np.nan_to_num(v)
            if self.wind_off.any():
                self.u[self.wind_off] = 0.0; self.v[self.wind_off] = 0.0; self.wmask[self.wind_off] = False
            # evaluation/training only where wind exists (AORC ends before the water-level record)
            has = np.where(self.wmask.any(0))[0]
            self.t_end = int(has.max()) + 1
        if use_q:
            q = np.load(d / "q.npy", mmap_mode="r")[self.rows].astype(np.float32)
            self.qmask = np.isfinite(q)
            self.q = np.nan_to_num(q)
        if use_rain:   # EXPERIMENT: hourly rain (mm/h) at the station cell ("p") or 15 km box mean ("p15"), log1p-scaled
            r = np.load(d / f"rain_{rain_var}.npy", mmap_mode="r")[self.rows].astype(np.float32)
            self.rmask = np.isfinite(r)
            self.rain = np.log1p(np.nan_to_num(np.clip(r, 0, None)))
            if not use_wind:
                has = np.where(self.rmask.any(0))[0]; self.t_end = int(has.max()) + 1
            if self.use_future_rain:
                # the rain fed for the 6 target hours: observed (same array, a perfect forecast) or a forecast product
                # (rain_fc = file stem, e.g. hrrr_lag1_p45.npy: HRRR rain by valid hour, NaN where no cycle was extracted)
                fut = np.load(d / f"{rain_fc}.npy", mmap_mode="r")[self.rows].astype(np.float32) if rain_fc else r
                self.futmask = np.isfinite(fut)
                self.fut_mm = np.nan_to_num(np.clip(fut, 0, None))
        # EXPERIMENT (--downstream / --upstream-stage): water level at a reference gauge that sees a change first -
        # the next gauge downstream (tide, surge travelling up the river) and / or upstream (flood wave coming down).
        # Per reference: its level (z-score), its level relative to the newest hour in its own 6 h-change units, its mask.
        self.nbr = []
        if neighbor_map and (use_ds or use_us):
            nm = pd.read_csv(neighbor_map, dtype=str).fillna("")
            row_of = {(a, str(b)): k for k, (a, b) in enumerate(zip(self.stations.source, self.stations.station_id))}
            for pref, on in (("ds", use_ds), ("us", use_us)):
                if not on:
                    continue
                rows = np.full(self.S, -1, np.int64)
                for a, b, c, d2 in zip(nm.source, nm.station_id, nm[f"{pref}_source"], nm[f"{pref}_station_id"]):
                    k, j = row_of.get((a, b)), row_of.get((c, d2))
                    if k is not None and j is not None:
                        rows[k] = j
                self.nbr.append(rows)
        self.n_feat = 6 + (3 if use_wind else 0) + (2 if use_q else 0) + (2 if use_rain else 0) + (1 if delta_feat else 0) + 3 * len(self.nbr)
        n_fr = 0 if not self.use_future_rain else (HORIZON if future_rain_form == "hourly" else 1)
        # EXPERIMENT (--long-feat): summaries of the last 7 and 30 days given to the head instead of a longer look-back:
        # mean level relative to the newest hour (in 6 h-change units) and, with rainfall, the rain totals. Placed FIRST
        # in the future vector so that the existing layout (wind, then rainfall last) stays valid for the other scripts.
        self.long_feat = long_feat
        self.n_long = 0 if not long_feat else (2 + (2 if use_rain else 0))
        self.n_future = self.n_long + (2 * HORIZON if self.use_future_wind else 0) + n_fr

    def split_range(self, split: str) -> tuple[int, int]:
        """Index range of forecast-origin times t0 (last observed hour) for a split."""
        if split == "train":
            return max(self.lookback, LONG_HOURS if getattr(self, "long_feat", False) else 0), self.t_train_end - HORIZON
        if split == "val":
            return self.t_train_end, self.t_val_end - HORIZON
        return self.t_val_end, min(self.T, self.t_end) - HORIZON - 1

    def window(self, s: np.ndarray, t0: np.ndarray):
        """Batch of windows. s, t0: int arrays [B]. t0 = index of the last observed hour.
        Returns feats [B, L, n_feat], future [B, n_future] (may be empty), s, y [B, H], ym [B, H]."""
        idx_in = t0[:, None] + np.arange(-self.lookback + 1, 1)[None, :]      # [B, L]
        idx_out = t0[:, None] + np.arange(1, HORIZON + 1)[None, :]             # [B, H]
        parts = [self.norm_filled[s[:, None], idx_in][..., None],
                 self.mask[s[:, None], idx_in].astype(np.float32)[..., None],
                 self.tfeat[idx_in]]
        if self.use_wind:
            parts += [self.u[s[:, None], idx_in][..., None], self.v[s[:, None], idx_in][..., None],
                      self.wmask[s[:, None], idx_in].astype(np.float32)[..., None]]
        if self.use_q:
            parts += [self.q[s[:, None], idx_in][..., None], self.qmask[s[:, None], idx_in].astype(np.float32)[..., None]]
        if self.use_rain:
            parts += [self.rain[s[:, None], idx_in][..., None], self.rmask[s[:, None], idx_in].astype(np.float32)[..., None]]
        if self.delta_feat:   # recent level relative to the last hour, in units of the station's typical 6 h change (kept last)
            rel = (self.norm_filled[s[:, None], idx_in] - self.norm_filled[s, t0][:, None]) / self.rscale[s][:, None]
            parts.append(np.clip(rel, -20, 20)[..., None])
        for rows in self.nbr:
            j = rows[s]; has = (j >= 0).astype(np.float32)[:, None]; jj = np.where(j >= 0, j, 0)
            lev = self.norm_filled[jj[:, None], idx_in]
            rel = np.clip((lev - lev[:, -1:]) / self.rscale[jj][:, None], -20, 20)
            parts += [(lev * has)[..., None], (rel * has)[..., None], (self.mask[jj[:, None], idx_in].astype(np.float32) * has)[..., None]]
        feats = np.concatenate(parts, -1)
        fut_parts = []
        if self.long_feat:
            idx_long = t0[:, None] + np.arange(-LONG_HOURS + 1, 1)[None, :]                    # [B, 720]
            lv = self.norm_filled[s[:, None], idx_long]; last = lv[:, -1:]
            r = self.rscale[s][:, None]
            fut_parts.append(np.clip((lv[:, -168:].mean(1, keepdims=True) - last) / r, -20, 20))
            fut_parts.append(np.clip((lv.mean(1, keepdims=True) - last) / r, -20, 20))
            if self.use_rain:
                mm = np.expm1(self.rain[s[:, None], idx_long])                                # rain is stored as log1p(mm/h)
                fut_parts.append(np.log1p(mm[:, -168:].sum(1, keepdims=True)) / 3.0)
                fut_parts.append(np.log1p(mm.sum(1, keepdims=True)) / 3.0)
        if self.use_future_wind:
            fut_parts += [self.u[s[:, None], idx_out], self.v[s[:, None], idx_out]]
        if self.use_future_rain:
            mm = self.fut_mm[s[:, None], idx_out]
            fut_parts.append(np.log1p(mm) if self.future_rain_form == "hourly" else np.log1p(mm.sum(1, keepdims=True)))
        future = np.concatenate(fut_parts, 1).astype(np.float32) if fut_parts else np.zeros((len(s), 0), np.float32)
        y = self.norm[s[:, None], idx_out]
        ym = np.isfinite(y)
        return feats, future, s, np.nan_to_num(y, nan=0.0), ym

    def _ok(self, s: np.ndarray, t0: np.ndarray) -> np.ndarray:
        idx_in = t0[:, None] + np.arange(-self.lookback + 1, 1)[None, :]
        ok = self.mask[s[:, None], idx_in].mean(1) >= MIN_INPUT_VALID
        ok &= self.mask[s[:, None], t0[:, None] + np.arange(1, HORIZON + 1)[None, :]].any(1)
        if self.use_wind:   # require the wind to exist over the window (and the target hours if fed to the head),
            need = ~self.wind_off[s]   # except at stations whose wind input is switched off
            ok &= (~need) | (self.wmask[s[:, None], idx_in].mean(1) >= MIN_INPUT_VALID)
            if self.use_future_wind:
                ok &= (~need) | self.wmask[s[:, None], t0[:, None] + np.arange(1, HORIZON + 1)[None, :]].all(1)
        if self.use_rain:   # rain comes from the same AORC grid as the wind: same availability rule
            ok &= self.rmask[s[:, None], idx_in].mean(1) >= MIN_INPUT_VALID
            if self.use_future_rain:
                ok &= self.futmask[s[:, None], t0[:, None] + np.arange(1, HORIZON + 1)[None, :]].all(1)
                if self.rain_fc:   # forecast product extracted for 6-hourly origins only: the valid hours of other origins would mix cycles
                    ok &= (t0 % FC_STRIDE) == 0      # time axis starts at 00 UTC, so this is 00/06/12/18 UTC
        return ok

    def sample_train(self, batch: int, rng: np.random.Generator):
        lo, hi = self.split_range("train")
        out_s, out_t, need = [], [], batch
        while need > 0:
            s = rng.integers(0, self.S, need * 2)
            if self.use_future_rain and self.rain_fc:      # forecast rain exists for the 6-hourly cycles only
                t0 = rng.integers(-(-lo // FC_STRIDE), hi // FC_STRIDE, need * 2) * FC_STRIDE
            else:
                t0 = rng.integers(lo, hi, need * 2)
            ok = self._ok(s, t0)
            out_s.append(s[ok][:need]); out_t.append(t0[ok][:need])
            need -= int(ok.sum())
        return self.window(np.concatenate(out_s)[:batch], np.concatenate(out_t)[:batch])

    def eval_origins(self, split: str, stride: int = 6, t_lo: int | None = None, t_hi: int | None = None):
        """All (station, t0) pairs on a regular stride with a usable input window."""
        lo, hi = self.split_range(split)
        if t_lo is not None:
            lo = max(lo, t_lo)
        if t_hi is not None:
            hi = min(hi, t_hi)
        if self.use_future_rain and self.rain_fc:
            # the split boundaries fall on 23 UTC; forecast rain is issued at 00/06/12/18 UTC -> start on a cycle hour
            assert stride % FC_STRIDE == 0, "eval stride must be a multiple of the forecast-rain cycle spacing"
            lo = -(-lo // FC_STRIDE) * FC_STRIDE
        t0 = np.arange(lo, hi, stride)
        S, T0 = [], []
        for s in range(self.S):
            ok = self._ok(np.full(len(t0), s), t0)
            S.append(np.full(int(ok.sum()), s)); T0.append(t0[ok])
        return np.concatenate(S), np.concatenate(T0)


def to_torch(batch, device):
    feats, future, s, y, ym = batch
    return (torch.from_numpy(feats).to(device), torch.from_numpy(future).to(device),
            torch.from_numpy(s).long().to(device), torch.from_numpy(y).to(device), torch.from_numpy(ym).to(device))
