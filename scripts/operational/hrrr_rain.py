"""Operational rainfall at the stations from NOAA HRRR (3 km, hourly cycles) on AWS.

The rainfall model was trained with
  look-back window : AORC hourly rainfall, mean of the 15 km box around the station (not available in real time)
  6 target hours   : HRRR forecast total of the 45 km box, from the cycle issued `lag` h before the origin
Operationally both come from HRRR:
  past hour t      : the 1 h accumulation ending at t from the cycle issued 1 h earlier (f01); if that file is missing,
                     the cycle 2 h earlier (f02) ... up to MAX_LEAD_PAST
  6 target hours   : ONE cycle for all six hours - the cycle issued `lag` h before the origin (leads lag+1 .. lag+6),
                     as in training; if it is not published yet, the cycle before it (up to MAX_OLDER cycles back)
Only the "APCP:surface:(k-1)-k hour acc" GRIB message of each file is downloaded (byte range from the .idx file,
about 0.2 MB) and only the station boxes are kept, cached per file in
  <cache>/hrrr_rain/<cycle YYYYMMDDTHH>_f<FF>.npz    (one array [S] in mm per box size, station key)
  <cache>/hrrr_rain_cells.csv                         (nearest HRRR cell per station)

Usage as a module:
  past, total, prov = station_rain(stations, past_index, origin, cache_dir, past_cells=5, future_cells=15, lag=1)
Standalone check:
  python hrrr_rain.py --stations RUN_DIR/stations.csv --cycle 2026-11-08T16 --cache DIR
"""
from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "data"))
from hrrr_wind import nearest_cells, station_key  # noqa: E402

log = logging.getLogger("hrrr_rain")
HORIZON = 6
MAX_LEAD_PAST = 6       # a past hour falls back from f01 to at most this lead
MAX_OLDER = 5           # the 6 target hours fall back to at most this many older cycles (hourly cycles run to f18)
MAX_LEAD = 18


def box_cells(name: str | None) -> int:
    """Cells per side of the box a training rainfall variable stands for: 'p' = station cell, 'p15' = 15 km (5 x 5 HRRR
    cells of 3 km), 'p45' = 45 km (15 x 15). Accepts file stems such as 'hrrr_lag1_p45'."""
    tail = (name or "p15").split("_")[-1]
    km = int(tail[1:]) if len(tail) > 1 else 3
    n = max(1, round(km / 3))
    return n if n % 2 else n + 1


def lag_of(rain_fc: str | None) -> int:
    """'hrrr_lag1_p45' -> 1 (hours between the HRRR cycle and the forecast origin in training)."""
    for part in (rain_fc or "").split("_"):
        if part.startswith("lag") and part[3:].isdigit():
            return int(part[3:])
    return 1


class HRRRRain:
    def __init__(self, stations: pd.DataFrame, cache_dir: Path, boxes: tuple[int, ...]):
        self.st = stations.reset_index(drop=True)
        self.key = station_key(self.st)
        self.cache = Path(cache_dir); (self.cache / "hrrr_rain").mkdir(parents=True, exist_ok=True)
        self.boxes = tuple(sorted(set(boxes)))
        self.cells: pd.DataFrame | None = None
        self.idx: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        p = self.cache / "hrrr_rain_cells.csv"
        if p.exists():
            c = pd.read_csv(p, dtype={"station_id": str})
            if len(c) == len(self.st) and (c.station_id.to_numpy() == self.st.station_id.astype(str).to_numpy()).all():
                self.cells = c

    def _path(self, cycle: pd.Timestamp, lead: int) -> Path:
        return self.cache / "hrrr_rain" / f"{cycle:%Y%m%dT%H}_f{lead:02d}.npz"

    def _boxes(self, shape: tuple[int, int]) -> None:
        ny, nx = shape
        iy, ix = self.cells.iy.to_numpy(), self.cells.ix.to_numpy()
        for nb in self.boxes:
            off = np.arange(-(nb // 2), nb // 2 + 1)
            jb = np.clip(iy[:, None, None] + off[None, :, None], 0, ny - 1)
            ib = np.clip(ix[:, None, None] + off[None, None, :], 0, nx - 1)
            self.idx[nb] = np.broadcast_arrays(jb, ib)

    def message(self, cycle: pd.Timestamp, lead: int) -> dict[int, np.ndarray] | None:
        """Box-mean rainfall (mm in the hour ending at cycle + lead) per box size, or None if the file is not there."""
        p = self._path(cycle, lead)
        if p.exists():
            z = np.load(p)
            if str(z["key"]) == self.key and all(f"b{nb}" in z for nb in self.boxes):
                return {nb: z[f"b{nb}"] for nb in self.boxes}
        import pygrib
        from hrrr_precip import fetch_apcp
        with requests.Session() as s:
            s.headers["User-Agent"] = "subdomainLSTM_operational"
            b = fetch_apcp(cycle, lead, s)
        if b is None:
            return None
        g = pygrib.fromstring(b)
        v = np.ma.filled(np.asarray(g.values, np.float32), np.nan)
        if self.cells is None:
            lat, lon = g.latlons()
            lon = ((lon + 180) % 360) - 180
            self.cells = nearest_cells(self.st, lat.astype(np.float32), lon.astype(np.float32))
            self.cells.to_csv(self.cache / "hrrr_rain_cells.csv", index=False)
        if not self.idx:
            self._boxes(v.shape)
        out = {nb: v[self.idx[nb][0], self.idx[nb][1]].mean((1, 2)).astype(np.float32) for nb in self.boxes}
        np.savez(p, key=self.key, cycle=str(cycle), lead=lead, **{f"b{nb}": a for nb, a in out.items()})
        return out

    def past_hour(self, valid: pd.Timestamp, nb: int):
        for lead in range(1, MAX_LEAD_PAST + 1):
            try:
                m = self.message(valid - pd.Timedelta(hours=lead), lead)
            except Exception as e:      # noqa: BLE001
                log.warning("HRRR rain %s f%02d: %s", valid - pd.Timedelta(hours=lead), lead, e); m = None
            if m is not None:
                return m[nb], lead
        return None


def station_rain(stations: pd.DataFrame, past: pd.DatetimeIndex, origin: pd.Timestamp, cache_dir: Path,
                 past_cells: int = 5, future_cells: int = 15, lag: int = 1, want_future: bool = True):
    """past [S, len(past)] mm/h (NaN where no file), future [S, 6] mm/h for origin+1 .. origin+6 from one cycle
    (None if no cycle is available), provenance."""
    hr = HRRRRain(stations, cache_dir, (past_cells, future_cells) if want_future else (past_cells,))
    S = len(hr.st)
    out = np.full((S, len(past)), np.nan, np.float32); prov_p = {}
    first = hr.past_hour(past[-1], past_cells)       # alone first, so that the cells file exists before threads start
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda t: hr.past_hour(t, past_cells), past[:-1]))
    for i, r in enumerate(res + [first]):
        if r is not None:
            out[:, i] = r[0]; prov_p[str(past[i])] = r[1]
    fut = None; prov_f = {}
    if want_future:
        for older in range(0, MAX_OLDER + 1):
            cyc = origin - pd.Timedelta(hours=lag + older)
            leads = [lag + older + k for k in range(1, HORIZON + 1)]
            if leads[-1] > MAX_LEAD:
                break
            with ThreadPoolExecutor(6) as ex:
                ms = list(ex.map(lambda ld: hr.message(cyc, ld), leads))
            if all(m is not None for m in ms):
                fut = np.stack([m[future_cells] for m in ms], 1)
                prov_f = {"cycle": str(cyc), "leads": leads, "hours_before_origin": lag + older}
                break
    prov = {"past_lead_counts": pd.Series(list(prov_p.values())).value_counts().to_dict() if prov_p else {},
            "past_hours_missing": int(len(past) - len(prov_p)), "future": prov_f, "cells": str(hr.cache / "hrrr_rain_cells.csv"),
            "past_box_km": 3 * past_cells, "future_box_km": 3 * future_cells}
    return out, fut, prov


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True); ap.add_argument("--cycle", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--lookback", type=int, default=72); ap.add_argument("--lag", type=int, default=1)
    a = ap.parse_args()
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    t0 = pd.Timestamp(a.cycle)
    past = pd.date_range(t0 - pd.Timedelta(hours=a.lookback - 1), t0, freq="1h")
    p, f, prov = station_rain(st, past, t0, Path(a.cache), lag=a.lag)
    print("past valid fraction", np.isfinite(p).mean().round(3), "leads used:", prov["past_lead_counts"])
    print("72 h total over stations: median %.1f max %.1f mm" % (np.nanmedian(np.nansum(p, 1)), np.nanmax(np.nansum(p, 1))))
    print("future:", prov["future"], "" if f is None else "6 h total median %.1f max %.1f mm" % (np.median(f.sum(1)), f.sum(1).max()))


if __name__ == "__main__":
    main()
