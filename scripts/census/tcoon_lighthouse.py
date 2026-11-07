"""CBI Lighthouse (ex-TCOON) stations: scrape overview pages for coordinates and
probe the pd endpoint for recent primary water level (pwl) data.

TCOON itself has been unfunded since 2014-08-31; most legacy TCOON gauges are
now operated by NOAA CO-OPS and appear in noaa_coops.csv. This source only adds
the CBI/CCWD/hydro stations that still report through Lighthouse.
"""
from __future__ import annotations

import html
import re
import sys

import pandas as pd
import requests

from common import RAW, finalize, load_domains

BASE = "https://lighthouse.tamucc.edu"
DMS = re.compile(r"(\d+)\D+(\d+)'\s*(\d+)\"\s*([NS])\D+(\d+)\D+(\d+)'\s*(\d+)\"\s*([EW])")


def dms2dd(d, m, s, h) -> float:
    v = int(d) + int(m) / 60 + int(s) / 3600
    return -v if h in "SW" else v


def text(url: str) -> str:
    t = requests.get(url, timeout=60).text
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))


def main() -> None:
    domains = load_domains()
    idx = requests.get(f"{BASE}/overview/", timeout=60).text
    names = {sid: html.unescape(nm.strip()) for sid, nm in re.findall(r'/overview/(\d{3})["\'][^>]*>\s*([^<]+?)\s*<', idx)}
    ids = sorted(names)
    print(f"{len(ids)} stations listed", file=sys.stderr)
    rows = []
    for sid in ids:
        t = text(f"{BASE}/overview/{sid}")
        m = DMS.search(t)
        if not m:
            continue
        lat = dms2dd(*m.groups()[:4])
        lon = dms2dd(*m.groups()[4:])
        name = names.get(sid, "")
        noaa = re.search(r"\b(\d{7})\b", t[: t.find("Station Information")] if "Station Information" in t else t)
        unfunded = "not been funded" in t or "no longer funded" in t
        # recent pwl probe: last 30 days, hourly
        r = requests.get(f"{BASE}/pd", params={"stnlist": sid, "serlist": "pwl", "when": "now,-30d",
                                               "whentz": "UTC", "-action": "csv", "unit": "metric",
                                               "elev": "navd88", "interval": "60"}, timeout=60)
        body = r.text
        nvalid = len(re.findall(r",\s*-?\d+\.?\d*\s*$", body, flags=re.M))
        last_valid = ""
        for line in body.splitlines()[::-1]:
            mm = re.match(r'"?(\d{4})(\d{3})\+(\d{2})(\d{2})"?,\s*(-?\d+\.?\d*)', line)
            if mm:
                last_valid = f"{mm.group(1)}-doy{mm.group(2)} {mm.group(3)}:{mm.group(4)}"
                break
        rows.append({
            "source": "TCOON",
            "station_id": sid,
            "name": name,
            "lat": lat, "lon": lon,
            "state": "TX",
            "site_type": "unfunded_tcoon" if unfunded else "cbi",
            "parameter": "pwl",
            "datum": "NAVD88",
            "units": "m",
            "interval_min": 6,
            "record_start": "", "record_end": last_valid,
            "active": nvalid > 24 and not unfunded,
            "extra": f"noaa_id={noaa.group(1) if noaa else ''}|valid30d={nvalid}",
        })
        print(f"  {sid} {name[:35]:35s} valid30d={nvalid:4d} {'UNFUNDED' if unfunded else ''}", file=sys.stderr)
    out = finalize(pd.DataFrame(rows), domains)
    out.to_csv(RAW / "tcoon_lighthouse.csv", index=False)
    print(f"TCOON/Lighthouse: {len(out)} in domains, {int(out['active'].sum())} with recent pwl", file=sys.stderr)


if __name__ == "__main__":
    main()
