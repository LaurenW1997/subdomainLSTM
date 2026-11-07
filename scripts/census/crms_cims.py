"""CPRA/CRMS continuous hydrographic stations from the CIMS 'Data Collection Stations' shapefile.

Source zip (downloaded 2026-11-07 with user approval):
  https://cims.coastal.louisiana.gov/viewer/metadata/zips/Data_Collection_Stations.zip
extracted to data/census/raw/crms_download/Data_Collection_Stations/shapefile/.

Keeps DATA_TYPE == Hydrography with hourly/15-minute frequency (continuous
water level), all project types (CRMS, CWPPRA, SWAMP, STATE, ...).
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd

from common import RAW, finalize, load_domains

SHP = RAW / "crms_download" / "Data_Collection_Stations" / "shapefile" / "CPRA_monitoring.shp"


def main() -> None:
    domains = load_domains()
    g = gpd.read_file(SHP).to_crs(4326)
    hyd = g[g["DATA_TYPE"] == "Hydrography"].copy()
    print("Hydrography frequency:", hyd["FREQUENCY"].value_counts().to_dict(), file=sys.stderr)
    print("Hydrography measures:", hyd["Measures"].value_counts().head(12).to_dict(), file=sys.stderr)
    cont = hyd[hyd["FREQUENCY"].str.contains("Hourly|15 Minute", na=False)].copy()
    cont = cont.drop_duplicates("STATION_ID")
    out = pd.DataFrame({
        "source": "CRMS",
        "station_id": cont["STATION_ID"],
        "name": cont["STATION_ID"] + " (" + cont["BASIN"].fillna("") + ")",
        "lat": cont.geometry.y,
        "lon": cont.geometry.x,
        "state": "LA",
        "site_type": cont["SENSOR_ENV"].fillna(""),
        "parameter": "water_level",
        "datum": "NAVD88",  # CIMS continuous hydrographic water level is reported in NAVD88 (GEOID12B after 2013-10-01)
        "units": "ft",
        "interval_min": cont["FREQUENCY"].map(lambda f: 15 if "15 Minute" in f else 60),
        "record_start": "",
        "record_end": "",
        "active": cont["STATUS"].eq("Active"),
        "extra": "proj_type=" + cont["PROJ_TYPE"].fillna("") + "|proj=" + cont["PROJ_ID"].fillna("")
                 + "|crms_site=" + cont["CRMS_SITE"].fillna("") + "|measures=" + cont["Measures"].fillna("").str.slice(0, 60),
    })
    out = finalize(out, domains)
    out.to_csv(RAW / "crms_cims.csv", index=False)
    print(f"CRMS/CIMS: {len(out)} continuous hydrographic stations in domains ({int(out['active'].sum())} active)", file=sys.stderr)
    print(out.groupby(out["extra"].str.extract(r"proj_type=([^|]*)")[0])["active"].agg(["size", "sum"]).to_string(), file=sys.stderr)


if __name__ == "__main__":
    main()
