"""For every station, the water-level gauge that sees the tide / surge first: the next gauge DOWNSTREAM on the same
river, or - for the last gauge on a river and for estuary / lake stations - the nearest NOAA tide gauge.

EXPERIMENT (downstream water level as model input). The 6 h forecast at tidal rivers lags the observation because the
signal travels up the river and nothing in the inputs sees it coming; the upstream-discharge input does the same job for
flood waves coming down.

Rules (reference gauges are operational stations only: USGS or NOAA, never CRMS):
  1. same river : stations whose name starts with the same water-body name; the reference is the nearest one that lies
                  lower (mean level over the training period, both in NAVD88) within MAX_RIVER_KM.
  2. tide gauge : if rule 1 finds nothing and the station is a river / estuary / lake / urban creek station, the nearest
                  NOAA tide gauge within MAX_TIDE_KM.
Input : runs/v6_wind_q/stations.csv (source, station_id, name, lat, lon, datum, mean_m), config/station_groups.csv
Output: config/station_downstream_map.csv  (source, station_id, name, type, ds_* = downstream reference, rule, dist_km,
        us_* = next gauge UPSTREAM on the same river (sees a flood wave first), river)
Usage : python downstream_map.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
MAX_RIVER_KM = 150.0
MAX_TIDE_KM = 50.0
SPLIT = re.compile(r"\s+(?:at|near|nr|above|abv|below|blw|bl|ab|@|in|north|south|east|west|n|s|e|w)\s+", re.I)
NORM = [(r"\briver\b", "rv"), (r"\bcreek\b", "ck"), (r"\bbayou\b", "byu"), (r"\bfork\b", "fk"), (r"\blake\b", "lk"), (r"\bcanal\b", "cnl"),
        (r"\bck\.", "ck"), (r"\br\.", "rv"), (r"\bcr\.", "ck"), (r"[.,]", " ")]


def river_name(name: str) -> str:
    s = SPLIT.split(str(name), maxsplit=1)[0].lower()
    for a, b in NORM:
        s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()


def km(lat1, lon1, lat2, lon2):
    p = np.deg2rad(lat1); q = np.deg2rad(lat2)
    a = np.sin((q - p) / 2) ** 2 + np.cos(p) * np.cos(q) * np.sin(np.deg2rad(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def main() -> None:
    st = pd.read_csv(REPO / "runs" / "v6_wind_q" / "stations.csv", dtype={"station_id": str})
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    st = st.merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left")
    st["river"] = st["name"].map(river_name)
    ref = st[st.source.isin(["USGS", "NOAA_COOPS"])].copy()
    tide = ref[(ref.source == "NOAA_COOPS")]
    rows = []
    for r in st.itertuples():
        out = {"source": r.source, "station_id": r.station_id, "name": r.name, "type": r.type, "ds_source": "", "ds_station_id": "", "ds_name": "", "rule": "", "dist_km": np.nan,
               "us_source": "", "us_station_id": "", "us_name": "", "us_dist_km": np.nan, "river": r.river}
        if r.source in ("USGS", "NOAA_COOPS") and r.type != "tide gauge":
            c = ref[(ref.river == r.river) & (ref.station_id != r.station_id) & (ref.datum == "NAVD88")] if r.datum == "NAVD88" else ref.iloc[0:0]
            if len(c) and len(r.river) >= 5:
                c = c.assign(d=km(r.lat, r.lon, c.lat.to_numpy(), c.lon.to_numpy()))
                up = c[(c.mean_m > r.mean_m + 0.05) & (c.d <= MAX_RIVER_KM)].sort_values("d")     # next gauge upstream: sees a flood wave first
                if len(up):
                    k = up.iloc[0]
                    out.update(us_source=k.source, us_station_id=k.station_id, us_name=k["name"], us_dist_km=round(float(k.d), 1))
                c = c[(c.mean_m < r.mean_m - 0.05) & (c.d <= MAX_RIVER_KM)].sort_values("d")
                if len(c):
                    k = c.iloc[0]
                    out.update(ds_source=k.source, ds_station_id=k.station_id, ds_name=k["name"], rule="same river", dist_km=round(float(k.d), 1))
            if not out["rule"] and r.type in ("river / canal", "estuary / tidal channel", "lake", "urban creek (Houston)"):
                d = km(r.lat, r.lon, tide.lat.to_numpy(), tide.lon.to_numpy())
                j = int(np.argmin(d))
                if d[j] <= MAX_TIDE_KM:
                    k = tide.iloc[j]
                    out.update(ds_source=k.source, ds_station_id=k.station_id, ds_name=k["name"], rule="nearest tide gauge", dist_km=round(float(d[j]), 1))
        rows.append(out)
    m = pd.DataFrame(rows)
    m.to_csv(REPO / "config" / "station_downstream_map.csv", index=False)
    has = m[m.rule != ""]
    print(f"{len(has)} of {len(m)} stations get a downstream reference ({(m.source != 'CRMS').sum()} operational stations)")
    print(has.groupby(["rule", "type"]).size().unstack(fill_value=0).to_string())
    print("stations with an upstream gauge on the same river:", int((m.us_station_id != "").sum()))


if __name__ == "__main__":
    main()
