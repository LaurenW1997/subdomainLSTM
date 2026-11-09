"""Operational stations -> (i, j) in the three 100 m ROMS child grids + vertical datum information.

Inputs
  runs/v6_wind_q/stations.csv                         model station list (operational = USGS + NOAA_COOPS)
  config/gridmap/<domain>_grid_small.nc               lon_rho, lat_rho, mask_rho, h extracted from the ROMS grid files
                                                      (/project/zlei2/LSU_operational_system_qbd/grid/<domain>/<domain>_roms_grid.nc, read-only)
  config/gridmap/noaa_coops_datums.csv                CO-OPS datums (m above station datum STND) for NOAA stations
  config/gridmap/gauge_datum_ngvd29.csv               VDatum NGVD29 -> NAVD88 conversion of gauge zero for gauge-datum USGS stations
  config/gridmap/obs_means.csv                        observed mean level 2012-2016 and 2019-2023 in the station's own datum
Output
  config/operational_stations_grid_datum.csv          one row per (station, domain)
Index convention: i = xi_rho (column, 0-based), j = eta_rho (row, 0-based); Fortran/ROMS 1-based = +1.
Coupled-model convention: mask_rho = 1 -> ROMS computes the cell, 0 -> WRF-Hydro computes it; water = h > 0, land = h < 0.
Usage: python station_grid_map.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

REPO = Path(__file__).resolve().parents[2]
GM = REPO / "config" / "gridmap"
DOMS = ["Louisiana100m", "Louisiana100m_full", "Texas100m", "Galveston100m"]   # Louisiana100m = operational .sub grid (1837 x 5510); _full = 2680 x 5510
R_EARTH_KM = 6371.0


def nearest(lon2, lat2, lon0, lat0, valid=None):
    """Index of the nearest grid cell (optionally among valid cells) and its distance in km."""
    c = np.cos(np.deg2rad(lat0))
    d2 = ((lon2 - lon0) * c) ** 2 + (lat2 - lat0) ** 2
    if valid is not None:
        d2 = np.where(valid, d2, np.inf)
    k = int(np.nanargmin(d2))
    j, i = np.unravel_index(k, lon2.shape)
    dist = np.deg2rad(np.sqrt(d2.flat[k])) * R_EARTH_KM
    return int(i), int(j), float(dist)


def main() -> None:
    st = pd.read_csv(REPO / "runs" / "v6_wind_q" / "stations.csv", dtype={"station_id": str})
    op = st[st.source.isin(["USGS", "NOAA_COOPS"])].copy()
    rows = []
    for dom in DOMS:
        f = GM / f"{dom}_grid_small.nc"
        if not f.exists():
            print("missing", f); continue
        ds = xr.open_dataset(f)
        lon, lat, mask, h = ds.lon_rho.values, ds.lat_rho.values, ds.mask_rho.values, ds.h.values
        ny, nx = lon.shape
        inside = (op.lon >= lon.min()) & (op.lon <= lon.max()) & (op.lat >= lat.min()) & (op.lat <= lat.max())
        print(f"{dom}: grid {ny} x {nx} (eta x xi), {int(inside.sum())} operational stations in the bounding box")
        for _, r in op[inside].iterrows():
            i, j, d = nearest(lon, lat, r.lon, r.lat)
            # outside the curvilinear grid proper (bbox is larger than the grid): distance > ~0.2 km from the nearest centre
            if d > 0.25:
                continue
            # coupled system: mask_rho = 1 -> cell computed by ROMS, 0 -> by WRF-Hydro; water where h > 0, land where h < 0
            water = h[j, i] > 0
            roms = mask[j, i] > 0.5
            iw, jw, dw = (i, j, d) if water else nearest(lon, lat, r.lon, r.lat, valid=h > 0)
            ir, jr, dr = (i, j, d) if (water and roms) else nearest(lon, lat, r.lon, r.lat, valid=(h > 0) & (mask > 0.5))
            rows.append({"source": r.source, "station_id": r.station_id, "name": r["name"], "lat": r.lat, "lon": r.lon, "station_datum": r.datum,
                         "domain": dom, "i_xi": i, "j_eta": j, "dist_cell_km": round(d, 3), "h_cell_m": round(float(h[j, i]), 2),
                         "cell_is_water": bool(water), "cell_model": "ROMS" if roms else "WRF-Hydro",
                         "i_xi_water": iw, "j_eta_water": jw, "dist_water_km": round(dw, 3), "h_water_m": round(float(h[jw, iw]), 2),
                         "water_cell_model": "ROMS" if mask[jw, iw] > 0.5 else "WRF-Hydro",
                         "i_xi_roms": ir, "j_eta_roms": jr, "dist_roms_km": round(dr, 3), "h_roms_m": round(float(h[jr, ir]), 2),
                         "cell_lon": round(float(lon[j, i]), 5), "cell_lat": round(float(lat[j, i]), 5)})
    g = pd.DataFrame(rows)
    # ---- datum information
    cd = pd.read_csv(GM / "noaa_coops_datums.csv", dtype={"station_id": str})
    ng = pd.read_csv(GM / "gauge_datum_ngvd29.csv", dtype={"station_id": str})
    om = pd.read_csv(GM / "obs_means.csv", dtype={"station_id": str})
    g = g.merge(cd[["station_id", "coops_MSL_m_stnd", "coops_NAVD88_m_stnd", "coops_MLLW_m_stnd", "coops_epoch"]], on="station_id", how="left")
    g = g.merge(ng[["station_id", "gauge_zero_ngvd29_ft", "gauge_zero_navd88_m"]], on="station_id", how="left")
    g = g.merge(om[["station_id", "obs_mean_2012_2016_m", "obs_mean_2019_2023_m", "obs_frac_2019_2023"]], on="station_id", how="left")
    # offset to add to the station's values to express them in NAVD88
    off = np.where(g.station_datum == "NAVD88", 0.0,
          np.where(g.station_datum == "MSL", g.coops_NAVD88_m_stnd * -1 + g.coops_MSL_m_stnd,      # MSL value + (MSL - NAVD88) = NAVD88 value
                   g.gauge_zero_navd88_m))                                                           # stage + gauge zero (NAVD88) = NAVD88 value
    g["to_navd88_add_m"] = np.round(off.astype(float), 3)
    g["coops_msl_minus_navd88_m"] = np.round(g.coops_MSL_m_stnd - g.coops_NAVD88_m_stnd, 3)
    g["obs_mean_2019_2023_navd88_m"] = np.round(g.obs_mean_2019_2023_m + g.to_navd88_add_m, 3)
    g["obs_mean_2012_2016_navd88_m"] = np.round(g.obs_mean_2012_2016_m + g.to_navd88_add_m, 3)
    g["grid_vertical_reference_assumed"] = "NAVD88 (bathymetry from NCEI DEMs; to be confirmed by the group)"
    g["station_to_grid_ref_add_m"] = g.to_navd88_add_m        # equal to the NAVD88 conversion under that assumption
    cols = ["source", "station_id", "name", "lat", "lon", "domain", "i_xi", "j_eta", "dist_cell_km", "h_cell_m", "cell_is_water", "cell_model",
            "i_xi_water", "j_eta_water", "dist_water_km", "h_water_m", "water_cell_model", "i_xi_roms", "j_eta_roms", "dist_roms_km", "h_roms_m", "cell_lon", "cell_lat",
            "station_datum", "to_navd88_add_m", "grid_vertical_reference_assumed", "station_to_grid_ref_add_m",
            "obs_mean_2019_2023_navd88_m", "obs_mean_2012_2016_navd88_m", "obs_frac_2019_2023",
            "coops_msl_minus_navd88_m", "coops_MSL_m_stnd", "coops_NAVD88_m_stnd", "coops_MLLW_m_stnd", "coops_epoch",
            "gauge_zero_ngvd29_ft", "gauge_zero_navd88_m"]
    g = g[cols].sort_values(["domain", "source", "station_id"])
    out = REPO / "config" / "operational_stations_grid_datum.csv"
    g.to_csv(out, index=False)
    print(g.groupby("domain").agg(n=("station_id", "count"), water=("cell_is_water", "sum"), roms=("cell_model", lambda s: (s == "ROMS").sum()),
                                  dist_water_median_km=("dist_water_km", "median"), dist_roms_median_km=("dist_roms_km", "median")).round(2))
    print(g.groupby(["domain", "cell_is_water", "cell_model"]).size())
    print("stations in >= 1 domain:", g.station_id.nunique(), "of", len(op), "| NAVD88 conversion available:", g.to_navd88_add_m.notna().sum(), "rows")
    print("->", out)


if __name__ == "__main__":
    main()
