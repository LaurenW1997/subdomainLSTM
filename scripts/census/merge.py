"""Merge per-source census CSVs into config/stations_census.csv.

Adds a coarse 'coastal' flag, a 'years' record length and a 'training_eligible'
flag (>= MIN_YEARS of record and active). Cross-source duplicates (same gauge
served by USGS and NOAA, or USACE mirroring USGS) are kept as separate rows but
flagged with 'dup_group' when within DUP_KM of each other.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import COLUMNS, CONFIG, RAW

MIN_YEARS = 3
DUP_KM = 0.3

SOURCES = ["usgs_nwis.csv", "noaa_coops.csv", "usace_cwms.csv", "tcoon_lighthouse.csv", "crms_cims.csv"]

# USGS site types: ST stream, ST-TS tidal stream, ES estuary, LK lake, OC ocean, OC-CO coastal, WE wetland
COASTAL_USGS = {"ST-TS", "ES", "LK", "OC", "OC-CO", "WE"}


def coastal_flag(row: pd.Series) -> bool:
    src, st = row["source"], str(row["site_type"])
    if src == "NOAA_COOPS":
        return True
    if src == "USGS":
        return st in COASTAL_USGS
    if src.startswith("USACE"):
        return st not in {"STREAM_LOCATION"}  # river gauges flagged inland; reviewed manually
    return True


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def main() -> None:
    frames = []
    for f in SOURCES:
        p = RAW / f
        if p.exists():
            df = pd.read_csv(p, dtype=str)
            frames.append(df)
            print(f"{f:24s} {len(df):5d}", file=sys.stderr)
    df = pd.concat(frames, ignore_index=True)[COLUMNS]
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    df["active"] = df["active"].astype(str).str.lower().isin(["true", "1"])
    start = pd.to_datetime(df["record_start"], errors="coerce")
    end = pd.to_datetime(df["record_end"], errors="coerce").fillna(pd.Timestamp("2026-11-07"))
    df["years"] = ((end - start).dt.days / 365.25).round(1)
    df["coastal"] = df.apply(coastal_flag, axis=1)
    df["training_eligible"] = df["active"] & (df["years"] >= MIN_YEARS)

    # cross-source duplicate groups
    df["dup_group"] = ""
    lat, lon = df["lat"].to_numpy(), df["lon"].to_numpy()
    gid = 0
    assigned = np.full(len(df), -1)
    for i in range(len(df)):
        if assigned[i] >= 0:
            continue
        d = haversine_km(lat[i], lon[i], lat, lon)
        near = np.where((d < DUP_KM) & (assigned < 0))[0]
        if len(near) > 1 and len(set(df["source"].iloc[near])) > 1:
            assigned[near] = gid
            gid += 1
    df.loc[assigned >= 0, "dup_group"] = ["G%03d" % g for g in assigned[assigned >= 0]]

    df = df.sort_values(["source", "station_id"]).reset_index(drop=True)
    out = CONFIG / "stations_census.csv"
    df.to_csv(out, index=False)

    print(f"\nwrote {out} ({len(df)} rows)", file=sys.stderr)
    print(df.groupby("source").agg(n=("station_id", "size"), active=("active", "sum"),
                                   eligible=("training_eligible", "sum")).to_string(), file=sys.stderr)
    dom = df["domains"].str.get_dummies(";")
    print("\nper domain (all / active / eligible):", file=sys.stderr)
    for c in dom.columns:
        m = dom[c] == 1
        print(f"  {c:14s} {m.sum():4d} {int(df.loc[m, 'active'].sum()):4d} {int(df.loc[m, 'training_eligible'].sum()):4d}", file=sys.stderr)
    print(f"\ndup groups: {gid}", file=sys.stderr)


if __name__ == "__main__":
    main()
