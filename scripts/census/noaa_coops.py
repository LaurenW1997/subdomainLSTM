"""NOAA CO-OPS water level stations in the domain bboxes (metadata API)."""
from __future__ import annotations

import json
import sys

import pandas as pd
import requests

from common import RAW, finalize, load_domains, union_bbox

BASE = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"


def main() -> None:
    domains = load_domains()
    lon0, lat0, lon1, lat1 = union_bbox(domains)
    r = requests.get(f"{BASE}/stations.json", params={"type": "waterlevels"}, timeout=120)
    r.raise_for_status()
    stations = r.json()["stations"]
    (RAW / "noaa_coops_stations_all.json").write_text(json.dumps(stations))
    rows = []
    for s in stations:
        if not (lon0 <= s["lng"] <= lon1 and lat0 <= s["lat"] <= lat1):
            continue
        det = requests.get(f"{BASE}/stations/{s['id']}/details.json", timeout=60).json()
        sens = requests.get(f"{BASE}/stations/{s['id']}/sensors.json", timeout=60).json()
        wl_sensors = [x for x in sens.get("sensors", []) if "water level" in (x.get("name") or "").lower()
                      or (x.get("name") or "").upper().startswith(("A1", "N1", "Y1", "B1"))]
        datums = requests.get(f"{BASE}/stations/{s['id']}/datums.json", timeout=60).json()
        datum_names = [d["name"] for d in datums.get("datums", [])]
        rows.append({
            "source": "NOAA_COOPS",
            "station_id": s["id"],
            "name": s["name"],
            "lat": s["lat"],
            "lon": s["lng"],
            "state": s.get("state", ""),
            "site_type": "tidal" if s.get("tidal") else "nontidal",
            "parameter": "water_level",
            "datum": "NAVD88" if "NAVD" in datum_names else ("MLLW" if "MLLW" in datum_names else ";".join(datum_names[:3])),
            "units": "m",
            "interval_min": 6,
            "record_start": (det.get("established") or "")[:10],
            "record_end": (det.get("removed") or "")[:10],
            "active": not det.get("removed"),
            "extra": f"affil={s.get('affiliations')}|shef={s.get('shefcode')}|stormsurge={s.get('stormsurge')}"
                     f"|datums={','.join(datum_names)}|sensors={len(wl_sensors)}",
        })
        print(f"  {s['id']} {s['name']}", file=sys.stderr)
    out = finalize(pd.DataFrame(rows), domains)
    out.to_csv(RAW / "noaa_coops.csv", index=False)
    print(f"NOAA CO-OPS: {len(out)} water level stations in domains", file=sys.stderr)


if __name__ == "__main__":
    main()
