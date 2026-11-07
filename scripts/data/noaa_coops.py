"""NOAA CO-OPS water level -> hourly NAVD88 metres (MSL fallback), plus hourly tide predictions.

Verified hourly heights (product=hourly_height, 1 year per call) for complete
years; 6-minute preliminary water_level (31 days per call) for the current
year, averaged to the hour. Predictions use product=predictions, interval=h.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from common import END, HOURLY, census, get, load_raw, log, raw_path, save_raw, to_hourly, write_hourly, years

URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
SRC = "NOAA_COOPS"


def call(station: str, product: str, begin: pd.Timestamp, end: pd.Timestamp, datum: str, tag: str,
         refresh: bool, interval: str | None = None) -> dict:
    p = raw_path(SRC, station, tag)
    if p.exists() and not refresh and end < END - pd.Timedelta(days=2):
        return json.loads(load_raw(p))
    params = {"product": product, "application": "LSU_subdomainLSTM", "station": station, "datum": datum,
              "units": "metric", "time_zone": "gmt", "format": "json",
              "begin_date": begin.strftime("%Y%m%d %H:%M"), "end_date": end.strftime("%Y%m%d %H:%M")}
    if interval:
        params["interval"] = interval
    r = get(URL, params)
    j = r.json()
    save_raw(p, json.dumps(j))
    return j


def series(j: dict, key: str) -> pd.Series:
    rows = j.get("data") or j.get("predictions") or []
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    t = pd.to_datetime(df["t"])
    v = pd.to_numeric(df[key], errors="coerce")
    return pd.Series(v.values, index=t)


def pick_datum(station: str) -> str:
    """NAVD if the station has it, otherwise MSL."""
    j = call(station, "hourly_height", pd.Timestamp(f"{END.year - 1}-06-01"), pd.Timestamp(f"{END.year - 1}-06-02"),
             "NAVD", "datum_probe", refresh=True)
    return "MSL" if "error" in j else "NAVD"


def run_station(row: pd.Series, refresh: bool) -> None:
    st = row["station_id"]
    datum = pick_datum(st)
    obs, pred = [], []
    for y in years():
        y0, y1 = pd.Timestamp(f"{y}-01-01"), min(pd.Timestamp(f"{y}-12-31 23:00"), END)
        try:
            if y < END.year:
                obs.append(series(call(st, "hourly_height", y0, y1, datum, f"hh_{y}", refresh), "v"))
            else:  # current year: 6-minute preliminary data in monthly chunks
                m0 = y0
                while m0 <= y1:
                    m1 = min(m0 + pd.offsets.MonthEnd(0) + pd.Timedelta(hours=23, minutes=54), y1)
                    obs.append(series(call(st, "water_level", m0, m1, datum, f"wl_{m0:%Y%m}", refresh), "v"))
                    m0 = (m0 + pd.offsets.MonthBegin(1)).normalize()
            pred.append(series(call(st, "predictions", y0, y1, datum, f"pred_{y}", refresh, interval="h"), "v"))
        except Exception as e:
            log.error("%s %d: %s", st, y, e)
    o = pd.concat([x for x in obs if not x.empty]) if any(not x.empty for x in obs) else pd.Series(dtype=float)
    if o.empty:
        log.warning("%s: no observations", st)
        return
    h = to_hourly(o)
    meta = write_hourly(SRC, st, h, {"name": row["name"], "lat": float(row["lat"]), "lon": float(row["lon"]),
                                     "datum": "NAVD88" if datum == "NAVD" else "MSL", "native_units": "m",
                                     "native_interval": "6min/hourly_height", "domains": row["domains"]})
    p = pd.concat([x for x in pred if not x.empty]) if any(not x.empty for x in pred) else pd.Series(dtype=float)
    if not p.empty:
        ph = to_hourly(p).rename("pred_m")
        ph.index.name = "time"
        ph.to_frame().to_parquet(HOURLY / SRC / f"{st}.pred.parquet")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", nargs="*")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    df = census(SRC)
    if a.stations:
        df = df[df["station_id"].isin(a.stations)]
    log.info("NOAA: %d stations", len(df))
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_station, row, a.refresh) for _, row in df.iterrows()]
        for f in as_completed(futs):
            f.result()


if __name__ == "__main__":
    main()
