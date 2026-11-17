"""Lakes and reservoirs between every pair of stations that lie on the same river network.

Public data: NHDPlus waterbodies and flowlines (USGS geoserver) and the USGS Network Linked Data Index.
  1. all lakes / reservoirs of the region with at least --min-km2 of surface (layer nhdwaterbody)
  2. the river segments that run through them (flowlines whose wbareacomi is one of those waterbodies)
  3. for every station with a station downstream: the segments of its downstream main path, in order (NLDI "DM")
  -> for every pair (upstream station, downstream station): the waterbodies the water passes on the way
A reservoir between two stations holds back the flood wave: the level below the dam follows the releases, not the
level upstream of the pool (Trinity River near Goodrich below Lake Livingston, deliverables/30_station_class_check.md).
Responses are cached in data/nldi/ (not in git).
Input : config/station_river_network.csv
Output: config/station_reservoirs_between.csv   up_station, down_station, on_main_path, n_waterbodies, max_km2, sum_km2, waterbodies
Usage : python reservoirs_between.py [--min-km2 1]
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
API = "https://api.water.usgs.gov/nldi/linked-data"
WFS = "https://api.water.usgs.gov/geoserver/wmadata/ows"
HEAD = {"User-Agent": "python-requests"}
BBOX = (-100.0, 25.5, -87.0, 34.0)          # lon / lat box around the three domains and their rivers


def wfs(layer: str, cql: str, props: str, cache: Path) -> list[dict]:
    """Attributes of the features of a layer that match a filter (one request; the caller keeps the requests small)."""
    if cache.exists():
        return json.loads(cache.read_text())
    p = {"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": layer, "outputFormat": "application/json", "CQL_FILTER": cql,
         "propertyName": props, "maxFeatures": 20000}
    for attempt in range(5):
        try:
            r = requests.get(WFS, params=p, headers=HEAD, timeout=300)
            if r.ok and r.text.startswith("{"):
                break
        except requests.RequestException:
            pass
        time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"no answer for {layer}")
    out = [x["properties"] for x in r.json()["features"]]
    cache.write_text(json.dumps(out)); return out


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--min-km2", type=float, default=1.0); ap.add_argument("--distance", type=int, default=500); a = ap.parse_args()
    cache = REPO / "data" / "nldi"; cache.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = BBOX
    tiles = [(x, y) for x in range(int(x0), int(x1), 2) for y in (25.5, 27.5, 29.5, 31.5)]
    wb = pd.DataFrame([w for x, y in tiles for w in wfs("wmadata:nhdwaterbody", f"BBOX(the_geom,{x},{y},{x + 2},{y + 2.5}) AND areasqkm >= {a.min_km2} AND ftype IN ('LakePond','Reservoir')",
                                                        "comid,gnis_name,areasqkm,ftype,lakevolume,meandepth", cache / f"waterbodies_{a.min_km2}_{x}_{y}.json")])
    wb = wb.drop_duplicates("comid")
    wb["comid"] = wb.comid.astype(int)
    print(f"{len(wb)} lakes / reservoirs of at least {a.min_km2} km2 in the region", flush=True)
    ids = sorted(wb.comid); seg = []
    for i in range(0, len(ids), 150):
        seg += wfs("wmadata:nhdflowline_network", "wbareacomi IN (%s)" % ",".join(map(str, ids[i:i + 150])), "comid,wbareacomi", cache / f"wbseg_{a.min_km2}_{i}.json")
    wb_of = {int(s["comid"]): int(s["wbareacomi"]) for s in seg}
    print(f"{len(wb_of)} river segments run through them", flush=True)
    info = wb.set_index("comid")

    net = pd.read_csv(REPO / "config" / "station_river_network.csv", dtype=str).fillna("")
    net["comid"] = net.comid.str.split(".").str[0]
    comid = dict(zip(net.station_id, net.comid)); ids_of = lambda s: re.findall(r"(\S+) \(", s)
    rows = []
    for n, r in enumerate(net[net.n_down.astype(int) > 0].itertuples()):
        f = cache / f"dmflow_{r.station_id}_{a.distance}.json"
        if f.exists():
            path = json.loads(f.read_text())
        else:
            src = f"nwissite/USGS-{r.station_id}" if r.indexed == "1" else f"comid/{r.comid}"
            for attempt in range(5):
                try:
                    q = requests.get(f"{API}/{src}/navigation/DM/flowlines", params={"distance": a.distance, "excludeGeometry": "true"}, headers=HEAD, timeout=300)
                    if q.ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(5 * (attempt + 1))
            else:
                raise RuntimeError(f"no answer for {r.station_id}")
            path = [int(x["properties"]["nhdplus_comid"]) for x in q.json()["features"]]
            f.write_text(json.dumps(path)); time.sleep(0.2)
        pos = {c: i for i, c in enumerate(path)}
        for d in ids_of(r.down):
            c = comid.get(d, "")
            on = c.isdigit() and int(c) in pos
            between = path[:pos[int(c)] + 1] if on else []            # the path is ordered from the station downstream
            w = list(dict.fromkeys(wb_of[s] for s in between if s in wb_of))
            ar = [float(info.areasqkm[k]) for k in w]
            rows.append({"up_station": r.station_id, "down_station": d, "on_main_path": int(on), "n_waterbodies": len(w), "max_km2": round(max(ar), 2) if ar else 0.0,
                         "sum_km2": round(sum(ar), 2), "waterbodies": " | ".join(f"{info.gnis_name[k] or 'unnamed'} ({info.areasqkm[k]:.1f} km2)" for k in w)})
        if (n + 1) % 50 == 0:
            print(f"{n + 1} stations", flush=True)
    d = pd.DataFrame(rows); out = REPO / "config" / "station_reservoirs_between.csv"; d.to_csv(out, index=False)
    print(f"{len(d)} pairs; downstream station on the main path of the upstream one: {int(d.on_main_path.sum())}; with a lake / reservoir between: "
          f"{int((d.n_waterbodies > 0).sum())}, of at least 10 km2: {int((d.max_km2 >= 10).sum())}, of at least 50 km2: {int((d.max_km2 >= 50).sum())}")
    print("->", out)


if __name__ == "__main__":
    main()
