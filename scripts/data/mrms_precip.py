"""MRMS hourly rainfall (radar + gauges, 1 km) at every station - the real-time stand-in for AORC in the look-back window.

Purpose: the rainfall model is trained with AORC rainfall in the past 72 h. AORC is a reanalysis and does not exist in
real time; MRMS "MultiSensor QPE 01H Pass1" is published about 16 minutes after every hour. This script extracts it for
a period that overlaps the test set so that the trained model can be re-tested with MRMS in place of AORC
(scripts/report/eval_past_rain.py --past <out>/mrms_p15.npy).

Source: s3://noaa-mrms-pds/CONUS/MultiSensor_QPE_01H_Pass1_00.00/YYYYMMDD/MRMS_..._YYYYMMDD-HH0000.grib2.gz
        (archive from 2020-10-14; 0.01 deg grid 3500 x 7000; the file time is the END of the accumulation hour,
        the same convention as the AORC arrays; negative values = no coverage)
Output: <out>/mrms_p15.npy  float32 [n_stations, n_hours] on the dataset time axis (same as precip/aorc_p15.npy),
        mm in the hour ending at each time, mean of the 15 x 15 cells (about 15 km) around the station; NaN outside the
        requested period or where the file is missing. An existing array is loaded and filled in. Also mrms_cells.csv, mrms_log.csv.
Usage (sv7 venv): python mrms_precip.py --stations DIR/stations.csv --start 2023-12-28 --end 2025-12-31 [--procs 24]
"""
from __future__ import annotations

import argparse
import gzip
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from common import DATA_ROOT, log as _log

BASE = "https://noaa-mrms-pds.s3.amazonaws.com"
PRODUCT = "MultiSensor_QPE_01H_Pass1_00.00"
START_AXIS = pd.Timestamp("2010-01-01 00:00")
END_AXIS = pd.Timestamp("2026-11-07 00:00")
BOX = 15                      # cells per side (0.01 deg, about 1 km)
_G: dict = {}


def url(t: pd.Timestamp, product: str = PRODUCT) -> str:
    return f"{BASE}/CONUS/{product}/{t:%Y%m%d}/MRMS_{product}_{t:%Y%m%d-%H}0000.grib2.gz"


def fetch_field(t: pd.Timestamp, product: str = PRODUCT, retries: int = 3):
    """(values [ny, nx] float32 with NaN for no coverage, grib message) of the hour ending at t, or None."""
    import pygrib
    for k in range(retries):
        try:
            r = requests.get(url(t, product), timeout=60)
            if r.status_code == 404:
                return None
            if r.status_code == 200:
                g = pygrib.fromstring(gzip.decompress(r.content))
                v = np.ma.filled(np.asarray(g.values, np.float32), np.nan)
                v[v < 0] = np.nan
                return v, g
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def grid_cells(g, lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Nearest cell (iy, ix) of each station on the regular MRMS grid."""
    lats, lons = g.latlons()
    la, lo = lats[:, 0], np.where(lons[0] > 180, lons[0] - 360, lons[0])
    iy = np.abs(la[None, :] - lat[:, None]).argmin(1)
    ix = np.abs(lo[None, :] - lon[:, None]).argmin(1)
    return iy, ix


def box_index(iy: np.ndarray, ix: np.ndarray, shape: tuple[int, int], nb: int = BOX):
    off = np.arange(-(nb // 2), nb // 2 + 1)
    jb = np.clip(iy[:, None, None] + off[None, :, None], 0, shape[0] - 1)
    ib = np.clip(ix[:, None, None] + off[None, None, :], 0, shape[1] - 1)
    return np.broadcast_arrays(jb, ib)


def box_mean(v: np.ndarray, jb: np.ndarray, ib: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(v[jb, ib], axis=(1, 2)).astype(np.float32)


def _init(jb, ib):
    _G["jb"], _G["ib"] = jb, ib


def _work(t):
    try:
        r = fetch_field(t)
    except Exception:      # noqa: BLE001
        r = None
    return t, (None if r is None else box_mean(r[0], _G["jb"], _G["ib"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True)
    ap.add_argument("--start", default="2023-12-28"); ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--out", default=str(DATA_ROOT / "precip")); ap.add_argument("--procs", type=int, default=24)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    axis = pd.date_range(START_AXIS, END_AXIS, freq="1h")
    S, T = len(st), len(axis)
    hours = pd.date_range(pd.Timestamp(a.start), pd.Timestamp(a.end) + pd.Timedelta(hours=23), freq="1h")
    first = None
    for t in hours[:48]:
        first = fetch_field(t)
        if first is not None:
            break
    assert first is not None, "no MRMS file in the first 48 hours of the period"
    iy, ix = grid_cells(first[1], st.lat.to_numpy(), st.lon.to_numpy())
    lats, lons = first[1].latlons()
    pd.DataFrame({"source": st.source, "station_id": st.station_id, "lat": st.lat, "lon": st.lon, "iy": iy, "ix": ix,
                  "cell_lat": lats[iy, 0], "cell_lon": np.where(lons[0, ix] > 180, lons[0, ix] - 360, lons[0, ix])}).to_csv(out / "mrms_cells.csv", index=False)
    jb, ib = box_index(iy, ix, first[0].shape)
    del lats, lons
    f = out / "mrms_p15.npy"
    arr = np.load(f) if f.exists() else np.full((S, T), np.nan, np.float32)
    assert arr.shape == (S, T)
    _log.info("MRMS grid %s; %d stations; %d hours %s .. %s", first[0].shape, S, len(hours), hours[0], hours[-1])
    rows = []; t_start = time.time()
    with Pool(a.procs, initializer=_init, initargs=(jb, ib)) as pool:
        for n, (t, v) in enumerate(pool.imap_unordered(_work, list(hours), chunksize=4), 1):
            ti = int((t - START_AXIS) / pd.Timedelta(hours=1))
            if v is not None and 0 <= ti < T:
                arr[:, ti] = v
            rows.append((t, v is not None))
            if n % 1000 == 0:
                _log.info("%d/%d hours, %.0f s", n, len(hours), time.time() - t_start)
    lg = pd.DataFrame(rows, columns=["time", "ok"]).sort_values("time")
    lf = out / "mrms_log.csv"
    if lf.exists():
        lg = pd.concat([pd.read_csv(lf, parse_dates=["time"]), lg]).drop_duplicates("time", keep="last").sort_values("time")
    lg.to_csv(lf, index=False)
    np.save(f, arr)
    _log.info("%.2f%% of the hours found -> %s", 100 * np.mean([r[1] for r in rows]), f)


if __name__ == "__main__":
    main()
