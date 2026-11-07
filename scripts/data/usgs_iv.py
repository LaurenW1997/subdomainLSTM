"""USGS NWIS instantaneous gage height (00065) -> hourly NAVD88 metres.

00065 is referenced to the gauge datum; the site's alt_va/alt_datum_cd (from the
census 'extra' field and the expanded site file) gives the datum elevation.
Sites whose datum is not NAVD88 keep gauge-datum values with datum flagged.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from common import FT, END, census, extra, get, load_raw, log, raw_path, save_raw, to_hourly, write_hourly, years

URL = "https://waterservices.usgs.gov/nwis/iv/"
SRC = "USGS"


def fetch_year(site: str, year: int, refresh: bool) -> str:
    p = raw_path(SRC, site, str(year))
    if p.exists() and not refresh and year < END.year:
        return load_raw(p)
    end = min(pd.Timestamp(f"{year}-12-31T23:59"), END)
    r = get(URL, {"format": "json", "sites": site, "parameterCd": "00065",
                  "startDT": f"{year}-01-01T00:00Z", "endDT": end.strftime("%Y-%m-%dT%H:%MZ"), "siteStatus": "all"})
    if r.status_code == 404:
        save_raw(p, "{}")
        return "{}"
    r.raise_for_status()
    save_raw(p, r.text)
    return r.text


def parse(text: str) -> pd.Series:
    j = json.loads(text) if text.strip() else {}
    ts_list = (j.get("value") or {}).get("timeSeries") or []
    parts = []
    for ts in ts_list:
        for block in ts.get("values", []):
            vals = block.get("value", [])
            if not vals:
                continue
            df = pd.DataFrame(vals)
            t = pd.to_datetime(df["dateTime"], utc=True).dt.tz_convert(None)
            v = pd.to_numeric(df["value"], errors="coerce")
            nodata = ts.get("variable", {}).get("noDataValue")
            if nodata is not None:
                v = v.mask(v == float(nodata))
            parts.append(pd.Series(v.values, index=t))
    if not parts:
        return pd.Series(dtype=float)
    return pd.concat(parts)


def run_site(row: pd.Series, refresh: bool) -> dict | None:
    site = row["station_id"]
    series = []
    for y in years():
        try:
            series.append(parse(fetch_year(site, y, refresh)))
        except Exception as e:  # keep the station, lose the year
            log.error("%s %d: %s", site, y, e)
    s = pd.concat([x for x in series if not x.empty]) if any(not x.empty for x in series) else pd.Series(dtype=float)
    if s.empty:
        log.warning("%s: no data", site)
        return None
    s = s * FT  # gauge-datum metres
    alt_ft = extra(row, "alt_ft")
    datum_cd = str(row.get("datum", ""))
    if alt_ft and datum_cd == "NAVD88":
        s = s + float(alt_ft) * FT
        datum = "NAVD88"
    else:
        datum = f"gauge_datum({datum_cd or 'unknown'};alt_ft={alt_ft or 'NA'})"
    h = to_hourly(s)
    return write_hourly(SRC, site, h, {"name": row["name"], "lat": float(row["lat"]), "lon": float(row["lon"]),
                                        "datum": datum, "native_units": "ft", "native_interval": "15min",
                                        "site_type": row["site_type"], "domains": row["domains"]})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", nargs="*", help="subset of station ids")
    ap.add_argument("--all", action="store_true", help="include inactive stations")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    df = census(SRC, only_active=not a.all)
    if a.stations:
        df = df[df["station_id"].isin(a.stations)]
    log.info("USGS: %d stations x %d years", len(df), len(years()))
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_site, row, a.refresh) for _, row in df.iterrows()]
        for f in as_completed(futs):
            f.result()


if __name__ == "__main__":
    main()
