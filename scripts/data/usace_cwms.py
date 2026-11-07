"""USACE CWMS time series for census locations with sub-daily stage/elevation series."""
from __future__ import annotations

import argparse
import json

import pandas as pd

from common import END, FT, census, extra, get, load_raw, log, raw_path, save_raw, to_hourly, write_hourly, years

BASE = "https://cwms-data.usace.army.mil/cwms-data"
HEAD = {"Accept": "application/json;version=2"}


def fetch_year(office: str, ts_name: str, station: str, year: int, refresh: bool) -> dict:
    p = raw_path(f"USACE_{office}", station, str(year))
    if p.exists() and not refresh and year < END.year:
        return json.loads(load_raw(p))
    end = min(pd.Timestamp(f"{year}-12-31T23:59"), END)
    r = get(f"{BASE}/timeseries", {"office": office, "name": ts_name, "unit": "m",
                                   "begin": f"{year}-01-01T00:00:00Z", "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "page-size": 500000}, timeout=300)
    r.headers  # noqa
    j = r.json() if r.status_code == 200 else {"error": r.status_code, "text": r.text[:200]}
    save_raw(p, json.dumps(j))
    return j


def parse(j: dict) -> pd.Series:
    vals = j.get("values") or []
    if not vals:
        return pd.Series(dtype=float)
    df = pd.DataFrame(vals, columns=["t", "v", "q"][: len(vals[0])])
    t = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert(None)
    return pd.Series(pd.to_numeric(df["v"], errors="coerce").values, index=t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", nargs="*")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    df = census("USACE")
    df = df[~df["interval_min"].astype(str).str.contains("Day", case=False, na=False)]
    if a.stations:
        df = df[df["station_id"].isin(a.stations)]
    log.info("USACE: %d sub-daily locations", len(df))
    for _, row in df.iterrows():
        office = row["source"].split("_")[1]
        ts_name = extra(row, "ts")
        parts = []
        for y in years():
            try:
                parts.append(parse(fetch_year(office, ts_name, row["station_id"], y, a.refresh)))
            except Exception as e:
                log.error("%s %d: %s", row["station_id"], y, e)
        s = pd.concat([x for x in parts if not x.empty]) if any(not x.empty for x in parts) else pd.Series(dtype=float)
        if s.empty:
            log.warning("%s: no data", row["station_id"])
            continue
        write_hourly(row["source"], row["station_id"], to_hourly(s),
                     {"name": row["name"], "lat": float(row["lat"]), "lon": float(row["lon"]),
                      "datum": f"CWMS_native({row['datum']})", "native_units": "m (unit=m requested)",
                      "native_interval": row["interval_min"], "ts_name": ts_name, "domains": row["domains"]})


if __name__ == "__main__":
    main()
