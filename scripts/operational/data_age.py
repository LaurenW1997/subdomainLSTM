"""How old is the newest water-level reading at each real-time station right now?

The forecast for hour H can only use readings that have arrived. This script asks the USGS and NOAA services for the
most recent readings of every real-time station and records the time of the newest one, so that repeated snapshots
show how many stations have the reading of the last full hour 5, 10, 20 ... minutes after it.

Usage: python data_age.py --stations ../../deliverables/20_operational_rain/20261112T12_forecast.csv --out data_age.csv --repeat 12 --every 5
One stream only: NOAA CO-OPS refuses concurrent clients from the same host.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

USGS_URL = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UA = {"User-Agent": "water-level-data-age-check"}


def usgs_newest(sites: list[str]) -> dict[str, pd.Timestamp]:
    out = {}
    for i in range(0, len(sites), 80):
        r = requests.get(USGS_URL, params={"format": "json", "sites": ",".join(sites[i:i + 80]), "parameterCd": "00065", "period": "PT6H", "siteStatus": "all"},
                         headers=UA, timeout=60)
        if r.status_code != 200:
            print("USGS HTTP", r.status_code); continue
        for ts in (r.json().get("value") or {}).get("timeSeries") or []:
            site = ts["sourceInfo"]["siteCode"][0]["value"]
            nodata = ts.get("variable", {}).get("noDataValue")
            for block in ts.get("values", []):
                vals = [v for v in block.get("value", []) if nodata is None or float(v["value"]) != float(nodata)]
                if vals:
                    t = pd.to_datetime(vals[-1]["dateTime"], utc=True).tz_convert(None)
                    out[site] = max(out.get(site, t), t)
    return out


def noaa_newest(stations: list[str]) -> dict[str, pd.Timestamp]:
    out = {}
    for s in stations:
        for attempt in range(3):
            try:
                j = requests.get(NOAA_URL, params={"product": "water_level", "application": "water_level_data_age_check", "station": s, "datum": "STND",
                                                   "units": "metric", "time_zone": "gmt", "format": "json", "range": 3}, headers=UA, timeout=60).json()
            except Exception as e:      # noqa: BLE001
                print("NOAA", s, e); j = {}
            time.sleep(0.3)
            if j.get("message") != "Forbidden":
                break
            time.sleep(5 * (attempt + 1))
        d = [x for x in j.get("data", []) if x.get("v") not in ("", None)]
        if d:
            out[s] = pd.to_datetime(d[-1]["t"], format="%Y-%m-%d %H:%M")
    return out


def snapshot(st: pd.DataFrame) -> pd.DataFrame:
    rows = []
    t0 = pd.Timestamp.now("UTC").tz_localize(None)
    u = usgs_newest(st[st.source == "USGS"].station_id.tolist())
    tu = pd.Timestamp.now("UTC").tz_localize(None)
    n = noaa_newest(st[st.source == "NOAA_COOPS"].station_id.tolist())
    tn = pd.Timestamp.now("UTC").tz_localize(None)
    for src, got, asked in (("USGS", u, t0 + (tu - t0) / 2), ("NOAA_COOPS", n, tu + (tn - tu) / 2)):
        for sid in st[st.source == src].station_id:
            new = got.get(sid)
            rows.append({"snapshot_utc": t0.strftime("%Y-%m-%d %H:%M:%S"), "asked_utc": asked.strftime("%Y-%m-%d %H:%M:%S"), "source": src, "station_id": sid,
                         "newest_utc": new, "age_min": None if new is None else round((asked - new).total_seconds() / 60, 1)})
    return pd.DataFrame(rows)


def report(d: pd.DataFrame) -> None:
    t0 = pd.Timestamp(d.snapshot_utc.iloc[0]); hour = t0.floor("h")
    line = f"{t0:%H:%M} UTC ({int((t0 - hour).total_seconds() // 60)} min past {hour:%H}:00)"
    for src, g in d.groupby("source"):
        a = g.age_min.dropna(); new = pd.to_datetime(g.newest_utc)
        line += (f" | {src}: {len(a)}/{len(g)} answered, newest reading median {a.median():.0f} min old, 90% within {a.quantile(0.9):.0f} min, "
                 f"reading at or after {hour:%H}:00 at {100 * (new >= hour).sum() / len(g):.0f}%, at or after {hour - pd.Timedelta(hours=1):%H}:00 at {100 * (new >= hour - pd.Timedelta(hours=1)).sum() / len(g):.0f}%")
    print(line, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", required=True, help="a forecast.csv; stations with status no_realtime_source are left out")
    ap.add_argument("--out", required=True); ap.add_argument("--repeat", type=int, default=1); ap.add_argument("--every", type=float, default=5, help="minutes between snapshots")
    a = ap.parse_args()
    st = pd.read_csv(a.stations, dtype={"station_id": str})
    st = st[st.status != "no_realtime_source"][["source", "station_id"]]
    out = Path(a.out)
    for k in range(a.repeat):
        start = time.time()
        d = snapshot(st)
        d.to_csv(out, mode="a", header=not out.exists(), index=False)
        report(d)
        if k + 1 < a.repeat:
            time.sleep(max(0, a.every * 60 - (time.time() - start)))
