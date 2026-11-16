"""River network of the stations: for every USGS station, the other stations downstream and upstream of it along the rivers.

Source: the USGS Network Linked Data Index (NLDI, NHDPlus flowlines). For every USGS station of the dataset the service is
asked for the USGS sites downstream of it (navigation "DD": downstream with diversions, up to --distance km along the
network); the stations of the dataset among them are kept. "Upstream of B" is the same relation read the other way.
A station the index does not know (HTTP 404) is located by its coordinates on the nearest flowline; it then has
downstream stations, but cannot be found as the downstream station of others.
NOAA tide gauges and CRMS sites are not on the index (no rows for them in the relations).
Responses are cached in data/nldi/ (not in git), so a second run does not query the service again.
Input : runs/v6_wind_q/stations.csv (source, station_id, name, lat, lon), config/station_groups.csv (type)
Output: config/station_river_network.csv   source, station_id, name, type, comid, mainstem, indexed,
                                           n_down, down (USGS ids, nearest first, with straight-line km), n_up, up
Usage : python river_network.py [--distance 500]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
API = "https://api.water.usgs.gov/nldi/linked-data"
HEAD = {"User-Agent": "python-requests"}


def km(lat, lon, la, lo):
    p = np.pi / 180
    a = np.sin((la - lat) * p / 2) ** 2 + np.cos(lat * p) * np.cos(la * p) * np.sin((lo - lon) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


def get(url: str, cache: Path, params: dict | None = None):
    """JSON of a request, from the cache when it is there. A 404 is cached as null."""
    if cache.exists():
        return json.loads(cache.read_text())
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=HEAD, timeout=180)
        except requests.RequestException:
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 404:
            cache.write_text("null"); return None
        if r.ok:
            try:
                j = r.json()
            except ValueError:
                j = {"features": []}          # the service answers an empty body when nothing is found
            cache.write_text(json.dumps(j)); time.sleep(0.2); return j
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"no answer from {url}")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--distance", type=int, default=500); a = ap.parse_args()
    cache = REPO / "data" / "nldi"; cache.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(REPO / "runs" / "v6_wind_q" / "stations.csv", dtype={"station_id": str})
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    st = st.merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left")
    us = st[st.source == "USGS"].reset_index(drop=True)
    ours = set(us.station_id); pos = {i: (la, lo) for i, la, lo in zip(us.station_id, us.lat, us.lon)}
    rows, down = [], {}
    for n, r in us.iterrows():
        sid = r.station_id
        f = get(f"{API}/nwissite/USGS-{sid}", cache / f"site_{sid}.json")
        indexed = bool(f and f.get("features"))
        if indexed:
            p = f["features"][0]["properties"]; comid, mainstem = p.get("comid"), (p.get("mainstem") or "").rsplit("/", 1)[-1]
            nav = get(f"{API}/nwissite/USGS-{sid}/navigation/DD/nwissite", cache / f"dd_{sid}_{a.distance}.json", {"distance": a.distance})
        else:
            c = get(f"{API}/comid/position", cache / f"pos_{sid}.json", {"coords": f"POINT({r.lon} {r.lat})"})
            comid = c["features"][0]["properties"].get("identifier") if c and c.get("features") else None; mainstem = ""
            nav = get(f"{API}/comid/{comid}/navigation/DD/nwissite", cache / f"dd_{sid}_{a.distance}.json", {"distance": a.distance}) if comid else None
        ids = {x["properties"]["identifier"].replace("USGS-", "") for x in (nav or {}).get("features", [])}
        down[sid] = sorted((ids & ours) - {sid}, key=lambda j: km(r.lat, r.lon, *pos[j]))
        rows.append({"source": "USGS", "station_id": sid, "name": r["name"], "type": r.type, "comid": comid, "mainstem": mainstem, "indexed": int(indexed)})
        if (n + 1) % 50 == 0:
            print(f"{n + 1} of {len(us)}", flush=True)
    up = {s: [] for s in down}
    for s, lst in down.items():
        for j in lst:
            up[j].append(s)
    d = pd.DataFrame(rows)
    fmt = lambda s, lst: " | ".join(f"{j} ({km(*pos[s], *pos[j]):.0f} km)" for j in sorted(lst, key=lambda j: km(*pos[s], *pos[j])))
    d["n_down"] = [len(down[s]) for s in d.station_id]; d["down"] = [fmt(s, down[s]) for s in d.station_id]
    d["n_up"] = [len(up[s]) for s in d.station_id]; d["up"] = [fmt(s, up[s]) for s in d.station_id]
    out = REPO / "config" / "station_river_network.csv"; d.to_csv(out, index=False)
    print(f"{len(d)} USGS stations; on the index {int(d.indexed.sum())}; with a station downstream {int((d.n_down > 0).sum())}, upstream {int((d.n_up > 0).sum())}, either {int(((d.n_down > 0) | (d.n_up > 0)).sum())}")
    print(d.assign(linked=(d.n_down > 0) | (d.n_up > 0)).groupby("type").agg(n=("linked", "size"), on_index=("indexed", "sum"), linked=("linked", "sum")).to_string())
    print("->", out)


if __name__ == "__main__":
    main()
