"""Shared helpers for historical data download.

Layout (DATA_ROOT, default /data/ywan245/subdomainLSTM/data):
  raw/<source>/<station>/<year>.json.gz      verbatim API payloads
  hourly/<source>/<station>.parquet          UTC hourly series, metres
  hourly/<source>/<station>.meta.json        datum, units, record span, counts
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data/ywan245/subdomainLSTM/data"))
RAW = DATA_ROOT / "raw"
HOURLY = DATA_ROOT / "hourly"

START_YEAR = int(os.environ.get("START_YEAR", "2010"))
END = pd.Timestamp.utcnow().tz_localize(None).floor("h")
FT = 0.3048

log = logging.getLogger("data")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "subdomainLSTM-census/0.1 (LSU coastal forecasting research)"


def census(source_prefix: str, only_active: bool = True) -> pd.DataFrame:
    df = pd.read_csv(CONFIG / "stations_census.csv", dtype=str)
    df = df[df["source"].str.startswith(source_prefix)]
    if only_active:
        df = df[df["active"].str.lower() == "true"]
    return df.reset_index(drop=True)


def extra(row: pd.Series, key: str) -> str:
    for part in str(row.get("extra", "")).split("|"):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return ""


def get(url: str, params: dict | None = None, tries: int = 5, timeout: int = 120) -> requests.Response:
    delay = 2.0
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code}", response=r)
            return r
        except (requests.RequestException, requests.HTTPError) as e:
            if i == tries - 1:
                raise
            log.warning("retry %d/%d %s: %s", i + 1, tries, url.split("?")[0], e)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")


def raw_path(source: str, station: str, tag: str) -> Path:
    p = RAW / source / station / f"{tag}.json.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_raw(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(text)


def load_raw(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return f.read()


def to_hourly(s: pd.Series) -> pd.Series:
    """Irregular UTC series -> hourly mean on the hour (NaN where no samples)."""
    s = s[~s.index.duplicated(keep="first")].sort_index()
    s = s[s.index >= pd.Timestamp(f"{START_YEAR}-01-01")]
    if s.empty:
        return s
    # a 'mean' over the centred hour [-30min, +30min) matches an instantaneous reading on the hour
    shifted = s.copy()
    shifted.index = shifted.index + pd.Timedelta(minutes=30)
    return shifted.resample("1h").mean().shift(0)


def write_hourly(source: str, station: str, s: pd.Series, meta: dict) -> dict:
    out = HOURLY / source
    out.mkdir(parents=True, exist_ok=True)
    s = s.rename("value_m")
    s.index.name = "time"
    df = s.to_frame()
    df.to_parquet(out / f"{station}.parquet")
    valid = s.dropna()
    meta = {
        **meta,
        "source": source, "station_id": station,
        "n_hours": int(len(s)), "n_valid": int(len(valid)),
        "first_valid": str(valid.index.min()) if len(valid) else None,
        "last_valid": str(valid.index.max()) if len(valid) else None,
        "years_valid": round(len(valid) / 8766, 2),
    }
    (out / f"{station}.meta.json").write_text(json.dumps(meta, indent=1))
    log.info("%s %s valid=%d (%.1f yr) %s..%s", source, station, meta["n_valid"], meta["years_valid"],
             (meta["first_valid"] or "")[:10], (meta["last_valid"] or "")[:10])
    return meta


def years() -> list[int]:
    return list(range(START_YEAR, END.year + 1))
