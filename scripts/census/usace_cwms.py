"""USACE CWMS Data API: locations with stage/elevation time series, MVN and SWG offices."""
from __future__ import annotations

import json
import sys

import pandas as pd
import requests

from common import RAW, finalize, load_domains

BASE = "https://cwms-data.usace.army.mil/cwms-data"
OFFICES = ["MVN", "SWG", "MVK", "SWF"]  # New Orleans, Galveston, Vicksburg, Fort Worth
HEAD = {"Accept": "application/json;version=2"}


def catalog(office: str) -> list[dict]:
    items, page = [], None
    while True:
        p = {"office": office, "like": r".*\.(Stage|Elev)\..*", "page-size": 5000}
        if page:
            p["page"] = page
        r = requests.get(f"{BASE}/catalog/TIMESERIES", params=p, headers=HEAD, timeout=180)
        r.raise_for_status()
        j = r.json()
        items += j.get("entries", [])
        page = j.get("next-page")
        if not page:
            return items


def locations(office: str) -> dict[str, dict]:
    r = requests.get(f"{BASE}/locations", params={"office": office, "format": "json"}, timeout=180)
    r.raise_for_status()
    # payload contains raw control characters inside strings
    locs = json.loads(r.text, strict=False)["locations"]["locations"]
    return {l["identity"]["name"]: l for l in locs}


def extent(e: dict) -> tuple[str, str]:
    ex = e.get("extents") or [{}]
    return (ex[0].get("earliest-time") or ""), (ex[0].get("latest-time") or "")


def main() -> None:
    domains = load_domains()
    rows = []
    for off in OFFICES:
        try:
            cat = catalog(off)
            locs = locations(off)
        except Exception as e:  # keep going with other offices
            print(f"{off}: {e}", file=sys.stderr)
            continue
        (RAW / f"usace_cwms_{off}_catalog.json").write_text(json.dumps(cat))
        print(f"{off}: {len(cat)} stage/elev series, {len(locs)} locations", file=sys.stderr)
        by_loc: dict[str, list[dict]] = {}
        for e in cat:
            loc = e["name"].split(".")[0]
            by_loc.setdefault(loc, []).append(e)
        for loc, series in by_loc.items():
            L = locs.get(loc)
            if not L:
                continue
            geo = L.get("geolocation") or {}
            if not geo.get("latitude"):
                continue
            pol = L.get("political") or {}
            lab = L.get("label") or {}
            # prefer an instantaneous/hourly series for the interval & record end
            series.sort(key=lambda e: extent(e)[1], reverse=True)
            s0 = series[0]
            t0, t1 = extent(s0)
            interval = s0.get("interval", "")
            rows.append({
                "source": f"USACE_{off}",
                "station_id": loc,
                "name": lab.get("public-name") or lab.get("long-name") or loc,
                "lat": geo["latitude"],
                "lon": geo["longitude"],
                "state": pol.get("state", ""),
                "site_type": (L.get("classification") or {}).get("location-kind", ""),
                "parameter": s0["name"].split(".")[1],
                "datum": (geo.get("elevation") or {}).get("datum", ""),
                "units": s0.get("units", ""),
                "interval_min": interval,
                "record_start": t0[:10],
                "record_end": t1[:10],
                "active": t1 >= "2026-10",
                "extra": f"nseries={len(series)}|ts={s0['name']}|nearest={pol.get('nearest-city','')}"
                         f"|alt={';'.join((L.get('identity') or {}).get('alternate-names') or [])}",
            })
    out = finalize(pd.DataFrame(rows), domains)
    out.to_csv(RAW / "usace_cwms.csv", index=False)
    print(f"USACE CWMS: {len(out)} locations in domains ({int(out['active'].sum())} active)", file=sys.stderr)


if __name__ == "__main__":
    main()
