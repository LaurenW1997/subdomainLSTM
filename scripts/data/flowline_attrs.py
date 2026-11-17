"""Attributes of the river segment (NHDPlus flowline) each USGS station sits on, from the public USGS geoserver.

For the comid of every station in config/station_river_network.csv: name of the water body, feature type (stream / canal /
artificial path / coastline), stream order, total drainage area, the NHDPlus tidal flag, the main-stem id (levelpathid),
the id of the outlet the segment drains to (terminalpathid), distance to that outlet along the network, slope, elevation.
Output: config/station_flowline_attrs.csv
Usage : python flowline_attrs.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
URL = "https://api.water.usgs.gov/geoserver/wmadata/ows"
COLS = "comid,gnis_name,ftype,fcode,streamorde,totdasqkm,tidal,levelpathi,terminalpa,pathlength,slope,minelevsmo,qa_ma"


def main() -> None:
    net = pd.read_csv(REPO / "config" / "station_river_network.csv", dtype=str).fillna("")
    net["comid"] = net.comid.str.split(".").str[0]
    ids = sorted({c for c in net.comid if c})
    rows = []
    for i in range(0, len(ids), 50):
        p = {"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": "wmadata:nhdflowline_network", "outputFormat": "application/json",
             "CQL_FILTER": "comid IN (%s)" % ",".join(ids[i:i + 50]), "propertyName": COLS}
        r = requests.get(URL, params=p, headers={"User-Agent": "python-requests"}, timeout=180); r.raise_for_status()
        rows += [f["properties"] for f in r.json()["features"]]
        print(f"{min(i + 50, len(ids))} of {len(ids)} segments", flush=True)
    a = pd.DataFrame(rows); a["comid"] = a.comid.astype(int).astype(str)
    a = a.rename(columns={"streamorde": "stream_order", "totdasqkm": "drainage_km2", "tidal": "nhd_tidal", "levelpathi": "levelpathid", "terminalpa": "terminalpathid",
                          "pathlength": "km_to_outlet", "minelevsmo": "elev_cm", "qa_ma": "mean_flow_cfs"})
    for c in ("levelpathid", "terminalpathid"):
        a[c] = a[c].astype("Int64").astype(str)
    d = net[["source", "station_id", "name", "type", "comid", "indexed"]].merge(a, on="comid", how="left")
    out = REPO / "config" / "station_flowline_attrs.csv"; d.to_csv(out, index=False)
    print(f"{len(d)} stations, {int(d.ftype.notna().sum())} with segment attributes; NHDPlus tidal flag set at {int((d.nhd_tidal == 1).sum())}")
    print(pd.crosstab(d.type, d.ftype.fillna("none")).to_string())
    print("->", out)


if __name__ == "__main__":
    main()
