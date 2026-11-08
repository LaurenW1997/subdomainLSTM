"""Operational 10 m wind at the stations from NOAA HRRR (3 km, hourly) on AWS.

Training used AORC (1 km hourly reanalysis). HRRR is the closest operational substitute:
hourly analyses (f00) for the past hours, the newest available cycle's f01..f06 for the
6 target hours, complete public archive at s3://noaa-hrrr-bdp-pds (no account, ~1 h latency).
Only the UGRD/VGRD "10 m above ground" GRIB messages are downloaded (byte ranges from the
.idx file, ~1 MB each) and only the station cells are kept, cached per valid hour in
  <cache>/hrrr/<YYYYMMDDTHH>_f<FF>.npz        (u, v float32 [S] in m/s, station key)
  <cache>/hrrr_cells.csv                      (nearest HRRR cell per station)

Usage as a module:
  u_past, v_past, u_fut, v_fut, prov = station_wind(stations, past_index, future_index, cache_dir)
Standalone check:
  python hrrr_wind.py --stations RUN_DIR/stations.csv --cycle 2026-11-08T16 --cache DIR
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

log = logging.getLogger("hrrr")
BASE = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"
VARS = ("UGRD:10 m above ground", "VGRD:10 m above ground")
MAX_FHR_PAST = 6        # past hours: analysis preferred, else the shortest available forecast
MAX_FHR_FUTURE = 12
TIMEOUT = 60
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "LSU_subdomainLSTM_operational"


def _url(cycle: pd.Timestamp, fhr: int) -> str:
    return f"{BASE}/hrrr.{cycle:%Y%m%d}/conus/hrrr.t{cycle:%H}z.wrfsfcf{fhr:02d}.grib2"


def _ranges(idx_text: str) -> dict[str, tuple[int, int | None]]:
    """Byte range (start, end) of the wanted messages from a GRIB .idx listing."""
    lines = idx_text.strip().splitlines()
    starts = [int(l.split(":")[1]) for l in lines]
    out = {}
    for i, l in enumerate(lines):
        for v in VARS:
            if f":{v}:" in l:
                out[v] = (starts[i], starts[i + 1] - 1 if i + 1 < len(starts) else None)
    return out


def fetch_messages(cycle: pd.Timestamp, fhr: int) -> bytes | None:
    """The UGRD+VGRD 10 m GRIB messages of one file, or None if the file is not (yet) there."""
    url = _url(cycle, fhr)
    r = SESSION.get(url + ".idx", timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    rng = _ranges(r.text)
    if len(rng) != 2:
        log.warning("%s: wind messages missing from idx", url); return None
    buf = b""
    for v in VARS:
        s, e = rng[v]
        h = {"Range": f"bytes={s}-{e if e is not None else ''}"}
        rr = SESSION.get(url, headers=h, timeout=TIMEOUT)
        if rr.status_code not in (200, 206):
            log.warning("%s: HTTP %s on byte range", url, rr.status_code); return None
        buf += rr.content
    return buf


def decode(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """GRIB bytes -> (u, v, lat, lon) 2-D arrays (m/s, deg; lon in -180..180)."""
    import pygrib
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as f:
        f.write(buf); path = f.name
    try:
        grbs = pygrib.open(path)
        u = v = None
        for g in grbs:
            arr = np.ma.filled(g.values.astype(np.float32), np.nan)
            if g.shortName in ("10u", "u10") or g.parameterName.startswith("u-component"):
                u = arr; lat, lon = g.latlons()
            elif g.shortName in ("10v", "v10") or g.parameterName.startswith("v-component"):
                v = arr
        grbs.close()
    finally:
        Path(path).unlink(missing_ok=True)
    if u is None or v is None:
        raise ValueError("u/v message not found in GRIB bytes")
    lon = ((lon + 180) % 360) - 180
    return u, v, lat.astype(np.float32), lon.astype(np.float32)


def nearest_cells(st: pd.DataFrame, lat: np.ndarray, lon: np.ndarray) -> pd.DataFrame:
    """Nearest HRRR grid cell (iy, ix) for every station row (lat, lon)."""
    flat_lat, flat_lon = lat.ravel(), lon.ravel()
    iy, ix, dist = [], [], []
    for i in range(0, len(st), 25):
        s = st.iloc[i:i + 25]
        c = np.cos(np.deg2rad(s.lat.to_numpy(np.float32)))[:, None]
        d2 = (flat_lat[None, :] - s.lat.to_numpy(np.float32)[:, None]) ** 2 + ((flat_lon[None, :] - s.lon.to_numpy(np.float32)[:, None]) * c) ** 2
        k = d2.argmin(1)
        iy.append(k // lat.shape[1]); ix.append(k % lat.shape[1]); dist.append(np.sqrt(d2[np.arange(len(s)), k]) * 111.0)
    out = st[["source", "station_id", "lat", "lon"]].copy()
    out["iy"], out["ix"], out["dist_km"] = np.concatenate(iy), np.concatenate(ix), np.concatenate(dist)
    out["cell_lat"] = lat[out.iy, out.ix]; out["cell_lon"] = lon[out.iy, out.ix]
    return out


def station_key(st: pd.DataFrame) -> str:
    return hashlib.md5("|".join(st.source + ":" + st.station_id.astype(str)).encode()).hexdigest()[:10]


class HRRRWind:
    def __init__(self, stations: pd.DataFrame, cache_dir: Path):
        self.st = stations.reset_index(drop=True)
        self.key = station_key(self.st)
        self.cache = Path(cache_dir); (self.cache / "hrrr").mkdir(parents=True, exist_ok=True)
        self.cells: pd.DataFrame | None = None
        p = self.cache / "hrrr_cells.csv"
        if p.exists():
            c = pd.read_csv(p, dtype={"station_id": str})
            if len(c) == len(self.st) and (c.station_id.to_numpy() == self.st.station_id.astype(str).to_numpy()).all():
                self.cells = c

    def _cache_path(self, valid: pd.Timestamp, fhr: int) -> Path:
        return self.cache / "hrrr" / f"{valid:%Y%m%dT%H}_f{fhr:02d}.npz"

    def _cached(self, valid: pd.Timestamp, fhr: int):
        p = self._cache_path(valid, fhr)
        if p.exists():
            z = np.load(p)
            if str(z["key"]) == self.key:
                return z["u"], z["v"]
        return None

    def _download(self, valid: pd.Timestamp, fhr: int):
        cycle = valid - pd.Timedelta(hours=fhr)
        buf = fetch_messages(cycle, fhr)
        if buf is None:
            return None
        u2, v2, lat, lon = decode(buf)
        if self.cells is None:
            self.cells = nearest_cells(self.st, lat, lon)
            self.cells.to_csv(self.cache / "hrrr_cells.csv", index=False)
            log.info("HRRR cells: %d stations, cell distance median %.2f km max %.2f km", len(self.cells), self.cells.dist_km.median(), self.cells.dist_km.max())
        iy, ix = self.cells.iy.to_numpy(), self.cells.ix.to_numpy()
        u, v = u2[iy, ix].astype(np.float32), v2[iy, ix].astype(np.float32)
        np.savez(self._cache_path(valid, fhr), u=u, v=v, key=self.key, cycle=str(cycle), fhr=fhr)
        return u, v

    def hour(self, valid: pd.Timestamp, fhrs: list[int]):
        """Wind for one valid hour: the first candidate forecast hour (in the given order of preference)
        that is cached or can be downloaded, so a past hour upgrades to the analysis once it is published."""
        for fhr in fhrs:
            c = self._cached(valid, fhr)
            if c is not None:
                return c[0], c[1], fhr
            try:
                d = self._download(valid, fhr)
            except Exception as e:            # noqa: BLE001
                log.warning("HRRR %s f%02d: %s", valid, fhr, e); d = None
            if d is not None:
                return d[0], d[1], fhr
        return None

    def series(self, hours: pd.DatetimeIndex, fhrs_for) -> tuple[np.ndarray, np.ndarray, dict]:
        """u, v [S, len(hours)] (NaN where unavailable) and provenance {hour: fhr}."""
        S = len(self.st)
        u = np.full((S, len(hours)), np.nan, np.float32); v = u.copy(); prov = {}
        # the first hour is fetched alone so that the cells file exists before threads start
        order = list(range(len(hours)))
        first = self.hour(hours[0], fhrs_for(hours[0]))
        if first is not None:
            u[:, 0], v[:, 0], prov[str(hours[0])] = first[0], first[1], first[2]
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(lambda i: self.hour(hours[i], fhrs_for(hours[i])), order[1:]))
        for i, r in zip(order[1:], res):
            if r is not None:
                u[:, i], v[:, i], prov[str(hours[i])] = r
        return u, v, prov


def station_wind(stations: pd.DataFrame, past: pd.DatetimeIndex, future: pd.DatetimeIndex, cache_dir: Path, now: pd.Timestamp | None = None):
    """Past hours: analysis (f00) else shortest forecast up to MAX_FHR_PAST.
    Future hours: newest cycle not after `now` (default: last past hour + 1) whose file exists."""
    hw = HRRRWind(stations, cache_dir)
    newest = (now if now is not None else past[-1] + pd.Timedelta(hours=1)).floor("h")
    u_p, v_p, prov_p = hw.series(past, lambda t: list(range(0, MAX_FHR_PAST + 1)))

    def fut_fhrs(t):
        f0 = max(0, int((t - newest) / pd.Timedelta(hours=1)))      # analysis if the hour is already past
        return list(range(f0, MAX_FHR_FUTURE + 1))
    u_f, v_f, prov_f = hw.series(future, fut_fhrs)
    prov = {"past": prov_p, "future": prov_f, "cells": str(hw.cache / "hrrr_cells.csv")}
    return u_p, v_p, u_f, v_f, prov


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True); ap.add_argument("--cycle", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--lookback", type=int, default=72)
    a = ap.parse_args()
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    t0 = pd.Timestamp(a.cycle)
    past = pd.date_range(t0 - pd.Timedelta(hours=a.lookback - 1), t0, freq="1h")
    fut = pd.date_range(t0 + pd.Timedelta(hours=1), periods=6, freq="1h")
    u_p, v_p, u_f, v_f, prov = station_wind(st, past, fut, Path(a.cache))
    print("past valid fraction", np.isfinite(u_p).mean().round(3), "future valid fraction", np.isfinite(u_f).mean().round(3))
    print("past fhr used:", pd.Series(list(prov["past"].values())).value_counts().to_dict())
    print("future fhr used:", prov["future"])
    spd = np.hypot(u_f, v_f)
    print("6 h-ahead wind speed over stations: median %.1f max %.1f m/s" % (np.nanmedian(spd), np.nanmax(spd)))


if __name__ == "__main__":
    main()
