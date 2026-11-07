"""Stream the CIMS Full_Continuous_Hydrographic export (20 GB CSV inside the zip)
into per-station hourly NAVD88 parquet files.

Water level column preference:
  Adjusted Water Elevation to Datum (ft)  -> NAVD88 (GEOID99 before 2013-10-01, GEOID12B after)
  Adjusted Water Level (ft)               -> sensor datum, used only when the datum column is absent
Timestamps are local standard time (Time Zone column, normally CST = UTC-6).
"""
from __future__ import annotations

import argparse
import subprocess
import sys

import pandas as pd

from common import DATA_ROOT, FT, START_YEAR, log, to_hourly, write_hourly

SRC = "CRMS"
ZIP = DATA_ROOT / "raw" / "CRMS" / "Full_Continuous_Hydrographic_latest.zip"
MEMBER = "Full_Continuous_Hydrographic.csv"
COLS = {
    "Station ID": "station",
    "Date (mm/dd/yyyy)": "date",
    "Time (hh:mm:ss)": "time",
    "Time Zone": "tz",
    "Adjusted Water Elevation to Datum (ft)": "elev_ft",
    "Raw Water Elevation to Datum (ft)": "elev_raw_ft",
    "Adjusted Water Level (ft)": "wl_ft",
    "Raw Water Level (ft)": "wl_raw_ft",
    "Geoid": "geoid",
    "Latitude": "lat",
    "Longitude": "lon",
}
TZ_OFFSET = {"CST": 6, "CDT": 5, "UTC": 0, "GMT": 0}
# preference order: adjusted NAVD88 elevation, raw NAVD88 elevation, adjusted sensor level, raw sensor level
VALUE_COLS = ["elev_ft", "elev_raw_ft", "wl_ft", "wl_raw_ft"]
DATUM_LABEL = {"elev_ft": "NAVD88(adjusted)", "elev_raw_ft": "NAVD88(raw)",
               "wl_ft": "sensor_datum(adjusted)", "wl_raw_ft": "sensor_datum(raw)"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunksize", type=int, default=2_000_000)
    ap.add_argument("--limit-chunks", type=int, default=0, help="debug: stop after N chunks")
    a = ap.parse_args()

    proc = subprocess.Popen(["unzip", "-p", str(ZIP), MEMBER], stdout=subprocess.PIPE)
    reader = pd.read_csv(proc.stdout, usecols=list(COLS), dtype=str, chunksize=a.chunksize,
                         encoding="latin-1", on_bad_lines="warn")
    parts: dict[str, list[pd.DataFrame]] = {}
    tz_seen: set[str] = set()
    n_rows = 0
    for i, chunk in enumerate(reader):
        chunk = chunk.rename(columns=COLS)
        # cheap year filter on the string date before parsing
        yr = pd.to_numeric(chunk["date"].str[-4:], errors="coerce")
        chunk = chunk[yr >= START_YEAR]
        n_rows += len(chunk)
        if chunk.empty:
            continue
        tz_seen |= set(chunk["tz"].dropna().unique())
        t = pd.to_datetime(chunk["date"] + " " + chunk["time"], format="%m/%d/%Y %H:%M:%S", errors="coerce")
        off = chunk["tz"].map(TZ_OFFSET).fillna(6).astype(int)
        chunk = chunk.assign(t_utc=t + pd.to_timedelta(off, unit="h"),
                             **{c: pd.to_numeric(chunk[c], errors="coerce") for c in VALUE_COLS})
        for st, g in chunk.groupby("station", sort=False):
            parts.setdefault(st, []).append(g[["t_utc", *VALUE_COLS, "geoid", "lat", "lon"]])
        if i % 10 == 0:
            log.info("chunk %d: %d rows kept so far, %d stations", i, n_rows, len(parts))
        if a.limit_chunks and i + 1 >= a.limit_chunks:
            break
    proc.stdout.close()
    log.info("time zones seen: %s", sorted(tz_seen))

    for st, lst in parts.items():
        df = pd.concat(lst, ignore_index=True).dropna(subset=["t_utc"])
        counts = {c: int(df[c].notna().sum()) for c in VALUE_COLS}
        col = next((c for c in VALUE_COLS if counts[c] >= 0.5 * max(counts.values()) and counts[c] > 0), None)
        if col is None:
            continue
        s = pd.Series((df[col] * FT).values, index=df["t_utc"].values)
        h = to_hourly(s)
        if h.dropna().empty:
            continue
        geoids = sorted(df["geoid"].dropna().unique())
        write_hourly(SRC, st, h, {"name": st, "lat": float(df["lat"].iloc[-1]), "lon": float(df["lon"].iloc[-1]),
                                  "datum": f"{DATUM_LABEL[col]}|geoid={'/'.join(geoids)}", "value_column": col,
                                  "column_counts": counts, "realtime": st.endswith("-RT"),
                                  "native_units": "ft", "native_interval": "hourly", "domains": "Louisiana100m"})
    log.info("done: %d stations", len(parts))


if __name__ == "__main__":
    main()
