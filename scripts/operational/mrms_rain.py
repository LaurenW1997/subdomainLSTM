"""Operational rainfall of the PAST hours at the stations from MRMS (radar + gauges, 1 km, hourly) on AWS.

The rainfall model was trained with AORC rainfall in the look-back window. AORC does not exist in real time; MRMS
"MultiSensor QPE 01H Pass1" is published about 16 minutes after every hour and agrees with AORC far better than a
short-range HRRR forecast does (see deliverables/20_operational_rain.md). For each past hour:
  1. MultiSensor_QPE_01H_Pass1   (radar corrected with gauges)
  2. RadarOnly_QPE_01H           (if Pass1 is missing)
Hours with neither are returned as NaN; forecast.py fills those from HRRR (hrrr_rain.py).
Only the station boxes are kept, cached per hour in
  <cache>/mrms/<YYYYMMDDTHH>_b<cells>.npz     (v float32 [S] in mm, product, station key)
  <cache>/mrms_cells.csv                      (nearest MRMS cell per station)

Usage as a module:
  past, prov = station_mrms(stations, past_index, cache_dir, cells=15)
Standalone check:
  python mrms_rain.py --stations RUN_DIR/stations.csv --cycle 2026-11-08T16 --cache DIR
"""
from __future__ import annotations

import argparse
import logging
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "data"))
from hrrr_wind import station_key  # noqa: E402
from mrms_precip import box_index, box_mean, fetch_field, grid_cells  # noqa: E402

log = logging.getLogger("mrms")
PRODUCTS = ("MultiSensor_QPE_01H_Pass1_00.00", "RadarOnly_QPE_01H_00.00")
_G: dict = {}


def _init(jb, ib):
    _G["jb"], _G["ib"] = jb, ib


def _hour(t):
    for product in PRODUCTS:
        try:
            r = fetch_field(t, product)
        except Exception:      # noqa: BLE001
            r = None
        if r is not None:
            return t, product, box_mean(r[0], _G["jb"], _G["ib"])
    return t, None, None


def station_mrms(stations: pd.DataFrame, past: pd.DatetimeIndex, cache_dir: Path, cells: int = 15, procs: int = 8):
    """Rainfall [S, len(past)] in mm per hour ending at each time (NaN where no file or no radar coverage), provenance."""
    st = stations.reset_index(drop=True)
    key = station_key(st)
    cache = Path(cache_dir); (cache / "mrms").mkdir(parents=True, exist_ok=True)
    out = np.full((len(st), len(past)), np.nan, np.float32); used: dict[str, str] = {}

    def path(t):
        return cache / "mrms" / f"{t:%Y%m%dT%H}_b{cells}.npz"

    todo = []
    for i, t in enumerate(past):
        p = path(t)
        if p.exists():
            z = np.load(p)
            if str(z["key"]) == key:
                out[:, i] = z["v"]; used[str(t)] = str(z["product"]); continue
        todo.append(i)
    if todo:
        cf = cache / "mrms_cells.csv"
        iy = ix = None
        if cf.exists():
            c = pd.read_csv(cf, dtype={"station_id": str})
            if len(c) == len(st) and (c.station_id.to_numpy() == st.station_id.astype(str).to_numpy()).all():
                iy, ix, shape = c.iy.to_numpy(), c.ix.to_numpy(), (int(c.ny.iloc[0]), int(c.nx.iloc[0]))
        if iy is None:      # one field in this process to learn the grid
            for i in todo[::-1]:
                r = None
                for product in PRODUCTS:
                    r = fetch_field(past[i], product)
                    if r is not None:
                        break
                if r is not None:
                    iy, ix = grid_cells(r[1], st.lat.to_numpy(), st.lon.to_numpy()); shape = r[0].shape
                    pd.DataFrame({"source": st.source, "station_id": st.station_id, "iy": iy, "ix": ix, "ny": shape[0], "nx": shape[1]}).to_csv(cf, index=False)
                    break
        if iy is not None:
            jb, ib = box_index(iy, ix, shape, cells)
            hours = [past[i] for i in todo]
            if len(hours) > 2:
                with Pool(min(procs, len(hours)), initializer=_init, initargs=(jb, ib)) as pool:
                    res = pool.map(_hour, hours)
            else:
                _init(jb, ib); res = [_hour(t) for t in hours]
            for i, (t, product, v) in zip(todo, res):
                if v is not None:
                    out[:, i] = v; used[str(t)] = product
                    np.savez(path(t), v=v, product=product, key=key)
    prov = {"products": pd.Series(list(used.values())).value_counts().to_dict() if used else {},
            "hours_missing": [str(t) for t in past if str(t) not in used], "box_km": cells, "cells": str(cache / "mrms_cells.csv")}
    return out, prov


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True); ap.add_argument("--cycle", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--lookback", type=int, default=72)
    a = ap.parse_args()
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    t0 = pd.Timestamp(a.cycle)
    past = pd.date_range(t0 - pd.Timedelta(hours=a.lookback - 1), t0, freq="1h")
    p, prov = station_mrms(st, past, Path(a.cache))
    print("products:", prov["products"], "missing hours:", len(prov["hours_missing"]))
    print("valid fraction", np.isfinite(p).mean().round(3), "stations without coverage:", int((~np.isfinite(p).any(1)).sum()))
    print("72 h total over stations: median %.1f max %.1f mm" % (np.nanmedian(np.nansum(p, 1)), np.nanmax(np.nansum(p, 1))))


if __name__ == "__main__":
    main()
