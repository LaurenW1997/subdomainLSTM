"""HRRR *forecast* precipitation at every station, for the 6-hourly test origins - EXPERIMENT (rain input).

Purpose: the rain experiment (deliverable 13) fed the model the next 6 h of AORC *observed* rain. Operationally that
slot would hold the HRRR forecast. This script pulls, for each test origin t0 (00/06/12/18 UTC), the HRRR cycle issued
`lag` hours before t0 and its hourly precipitation for the valid hours t0+1 .. t0+6 (leads lag+1 .. lag+6).

Source: s3://noaa-hrrr-bdp-pds/hrrr.YYYYMMDD/conus/hrrr.tHHz.wrfsfcfFF.grib2, message "APCP:surface:(k-1)-k hour acc fcst"
        read by byte range through the .idx file (about 210 kB per message).
Output: <out>/hrrr_lag<L>_p.npy, hrrr_lag<L>_p15.npy  float32 [n_stations, n_hours] indexed by VALID hour on the dataset time axis
        (same axis as precip/aorc_p.npy); hours that are not a test-origin valid hour, or whose message failed, are NaN.
        p = station's 3 km cell, p15 = mean of the 5 x 5 cells (15 km) around it. Also <out>/hrrr_cells.csv, hrrr_lag<L>_log.csv.
Usage (sv7 venv has pygrib + requests): python hrrr_precip.py --stations DIR/stations.csv --start 2024-01-01 --end 2025-12-31 --lag 0 [--lag 1] [--threads 16]
"""
from __future__ import annotations

import argparse
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import pygrib
import requests

from common import DATA_ROOT, log

BASE = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"
START_AXIS = pd.Timestamp("2010-01-01 00:00")
END_AXIS = pd.Timestamp("2026-11-07 00:00")
HORIZON = 6
BOX = 5          # 5 x 5 cells of 3 km = 15 km


def url(cycle: pd.Timestamp, lead: int) -> str:
    return f"{BASE}/hrrr.{cycle:%Y%m%d}/conus/hrrr.t{cycle:%H}z.wrfsfcf{lead:02d}.grib2"


def fetch_apcp(cycle: pd.Timestamp, lead: int, sess: requests.Session, retries: int = 3) -> bytes | None:
    """Bytes of the 1-hour-accumulation APCP message of one HRRR file, or None."""
    u = url(cycle, lead)
    want = f"APCP:surface:{lead - 1}-{lead} hour acc"
    for k in range(retries):
        try:
            idx = sess.get(u + ".idx", timeout=30)
            if idx.status_code != 200:
                return None
            lines = idx.text.splitlines()
            for n, line in enumerate(lines):
                if want in line:
                    start = int(line.split(":")[1])
                    end = int(lines[n + 1].split(":")[1]) - 1 if n + 1 < len(lines) else ""
                    r = sess.get(u, headers={"Range": f"bytes={start}-{end}"}, timeout=60)
                    if r.status_code in (200, 206):
                        return r.content
                    break
            else:
                return None
        except requests.RequestException:
            time.sleep(2 * (k + 1))
    return None


def values(msg_bytes: bytes) -> np.ndarray:
    g = pygrib.fromstring(msg_bytes)
    return np.asarray(g.values, np.float32)       # [1059, 1799], mm (kg/m^2) over the hour


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True)
    ap.add_argument("--start", default="2024-01-01"); ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--stride", type=int, default=6, help="hours between origins (eval stride)")
    ap.add_argument("--lag", type=int, nargs="+", default=[0], help="hours between the HRRR cycle and the origin (0 = cycle at t0, 1 = previous hour's cycle)")
    ap.add_argument("--out", default=str(DATA_ROOT / "precip"))
    ap.add_argument("--threads", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    axis = pd.date_range(START_AXIS, END_AXIS, freq="1h")
    S, T = len(st), len(axis)
    origins = pd.date_range(pd.Timestamp(a.start), pd.Timestamp(a.end) + pd.Timedelta(hours=23), freq=f"{a.stride}h")

    # ---- grid -> station cells (one full message)
    sess = requests.Session()
    b = fetch_apcp(origins[0], 1, sess)
    g = pygrib.fromstring(b)
    lat, lon = g.latlons()
    lon = np.where(lon > 180, lon - 360, lon)
    ny, nx = lat.shape
    iy = np.empty(S, int); ix = np.empty(S, int)
    for k, (la, lo) in enumerate(zip(st.lat.to_numpy(), st.lon.to_numpy())):
        d2 = (lat - la) ** 2 + ((lon - lo) * np.cos(np.deg2rad(la))) ** 2
        j, i = np.unravel_index(int(d2.argmin()), lat.shape)
        iy[k], ix[k] = j, i
    pd.DataFrame({"source": st.source, "station_id": st.station_id, "lat": st.lat, "lon": st.lon, "iy": iy, "ix": ix,
                  "cell_lat": lat[iy, ix], "cell_lon": lon[iy, ix]}).to_csv(out / "hrrr_cells.csv", index=False)
    off = np.arange(-(BOX // 2), BOX // 2 + 1)
    jb = np.clip(iy[:, None, None] + off[None, :, None], 0, ny - 1)
    ib = np.clip(ix[:, None, None] + off[None, None, :], 0, nx - 1)
    jb, ib = np.broadcast_arrays(jb, ib)
    log(f"HRRR grid {ny} x {nx}; {S} stations mapped; {len(origins)} origins {origins[0]} .. {origins[-1]}; lags {a.lag}")

    for lag in a.lag:
        p = np.full((S, T), np.nan, np.float32); p15 = np.full((S, T), np.nan, np.float32)
        jobs = [(t0, t0 - pd.Timedelta(hours=lag), lead + lag, lead) for t0 in origins for lead in range(1, HORIZON + 1)]
        rows = []; t_start = time.time(); done = 0

        def work(job):
            t0, cyc, flead, lead = job
            with requests.Session() as s2:
                bb = fetch_apcp(cyc, flead, s2)
            return job, bb

        with ThreadPoolExecutor(a.threads) as ex:
            futs = [ex.submit(work, j) for j in jobs]
            for f in as_completed(futs):
                (t0, cyc, flead, lead), bb = f.result()
                valid = t0 + pd.Timedelta(hours=lead)
                ok = bb is not None
                if ok:
                    try:
                        v = values(bb)
                        ti = int((valid - START_AXIS) / pd.Timedelta(hours=1))
                        if 0 <= ti < T:
                            p[:, ti] = v[iy, ix]
                            p15[:, ti] = v[jb, ib].mean((1, 2))
                    except Exception as e:  # noqa: BLE001
                        ok = False; log(f"bad message {cyc} f{flead:02d}: {e}")
                rows.append((t0, cyc, flead, valid, ok))
                done += 1
                if done % 2000 == 0:
                    log(f"lag {lag}: {done}/{len(jobs)} messages, {time.time() - t_start:.0f} s")
        lg = pd.DataFrame(rows, columns=["origin", "cycle", "lead", "valid", "ok"]).sort_values(["origin", "lead"])
        lg.to_csv(out / f"hrrr_lag{lag}_log.csv", index=False)
        np.save(out / f"hrrr_lag{lag}_p.npy", p); np.save(out / f"hrrr_lag{lag}_p15.npy", p15)
        n_full = lg.groupby("origin").ok.all().sum()
        log(f"lag {lag}: {lg.ok.mean():.3%} messages ok, {n_full}/{len(origins)} origins complete -> {out}/hrrr_lag{lag}_p*.npy")


if __name__ == "__main__":
    main()
