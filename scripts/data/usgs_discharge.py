"""USGS NWIS instantaneous discharge (00060) for the upstream control gauges
in config/discharge_gauges.csv -> hourly m^3/s under hourly/USGS_Q/<gauge>.parquet.
Usage: python usgs_discharge.py [--gauges ID ...] [--workers 4] [--refresh]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from common import CONFIG, END, get, load_raw, log, raw_path, save_raw, to_hourly, write_hourly, years

URL = "https://waterservices.usgs.gov/nwis/iv/"
SRC = "USGS_Q"
CFS = 0.028316846592   # ft^3/s -> m^3/s


def fetch_year(site: str, year: int, refresh: bool) -> str:
    p = raw_path(SRC, site, str(year))
    if p.exists() and not refresh and year < END.year:
        return load_raw(p)
    end = min(pd.Timestamp(f"{year}-12-31T23:59"), END)
    r = get(URL, {"format": "json", "sites": site, "parameterCd": "00060",
                  "startDT": f"{year}-01-01T00:00Z", "endDT": end.strftime("%Y-%m-%dT%H:%MZ"), "siteStatus": "all"})
    if r.status_code == 404:
        save_raw(p, "{}"); return "{}"
    r.raise_for_status(); save_raw(p, r.text); return r.text


def parse(text: str) -> pd.Series:
    j = json.loads(text) if text.strip() else {}
    parts = []
    for ts in (j.get("value") or {}).get("timeSeries") or []:
        nodata = ts.get("variable", {}).get("noDataValue")
        for block in ts.get("values", []):
            vals = block.get("value", [])
            if not vals:
                continue
            df = pd.DataFrame(vals)
            t = pd.to_datetime(df["dateTime"], utc=True).dt.tz_convert(None)
            v = pd.to_numeric(df["value"], errors="coerce")
            if nodata is not None:
                v = v.mask(v == float(nodata))
            parts.append(pd.Series(v.values, index=t))
    return pd.concat(parts) if parts else pd.Series(dtype=float)


def run_gauge(row: pd.Series, refresh: bool) -> dict | None:
    site = row["gauge_id"]
    series = []
    for y in years():
        try:
            series.append(parse(fetch_year(site, y, refresh)))
        except Exception as e:  # noqa: BLE001
            log.error("%s %d: %s", site, y, e)
    s = pd.concat([x for x in series if not x.empty]) if any(not x.empty for x in series) else pd.Series(dtype=float)
    if s.empty:
        log.warning("%s: no data", site); return None
    s = s[s >= -1000] * CFS          # negative flows (tidal reversal) are real at a few coastal gauges; drop fill values only
    return write_hourly(SRC, site, to_hourly(s), {"name": row["gauge_name"], "lat": float(row["lat"]), "lon": float(row["lon"]),
                                                  "huc8": row["huc8"], "drain_area_mi2": row["drain_area_mi2"],
                                                  "units": "m3/s", "native_units": "cfs", "domains": row["domain"]})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gauges", nargs="*"); ap.add_argument("--workers", type=int, default=4); ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    df = pd.read_csv(CONFIG / "discharge_gauges.csv", dtype=str)
    if a.gauges:
        df = df[df.gauge_id.isin(a.gauges)]
    log.info("USGS_Q: %d gauges x %d years", len(df), len(years()))
    with ThreadPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(run_gauge, r, a.refresh) for _, r in df.iterrows()]):
            f.result()


if __name__ == "__main__":
    main()
