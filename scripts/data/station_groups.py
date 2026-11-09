"""Split the training stations into two physical groups for separate models (deliverable 09).

  tidal : tide gauges, marsh (CRMS), lakes, estuaries / tidal channels  -> model with wind, no discharge
  river : rivers / canals, Houston urban creeks                          -> model with discharge, no wind
Types come from error_split.station_type (census site_type + county + source).
Writes config/station_groups.csv (all stations, with group) and config/stations_tidal.csv /
config/stations_river.csv (the subset files taken by train.py --stations). Runs locally.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for n, attrs in (("torch", ()), ("data", ("HORIZON", "StationMatrix", "to_torch")), ("model", ("GlobalLSTM",)), ("common", ("HOURLY",))):
    if n not in sys.modules:
        mod = types.ModuleType(n)
        for a in attrs:
            setattr(mod, a, None)
        sys.modules[n] = mod
sys.path.insert(0, str(REPO / "scripts" / "report"))
from error_split import station_type  # noqa: E402

GROUP = {"tide gauge": "tidal", "marsh": "tidal", "lake": "tidal", "estuary / tidal channel": "tidal",
         "river / canal": "river", "urban creek (Houston)": "river", "other": "river"}


def main() -> None:
    st = pd.read_csv(REPO / "runs" / "v2_e40" / "stations.csv", dtype={"station_id": str})
    cen = pd.read_csv(REPO / "config" / "stations_census.csv", dtype=str).drop_duplicates(["source", "station_id"])
    cen["county"] = cen.extra.str.extract(r"county=(\d+)")
    st = st.merge(cen[["source", "station_id", "site_type", "county"]], on=["source", "station_id"], how="left")
    st["type"] = st.apply(station_type, axis=1)
    st["group"] = st.type.map(GROUP)
    out = st[["source", "station_id", "name", "domains", "type", "group"]]
    out.to_csv(REPO / "config" / "station_groups.csv", index=False)
    for g in ("tidal", "river"):
        out[out.group == g][["source", "station_id"]].to_csv(REPO / "config" / f"stations_{g}.csv", index=False)
    print(out.group.value_counts().to_dict())
    print(out.groupby(["group", "type"]).size())


if __name__ == "__main__":
    main()
