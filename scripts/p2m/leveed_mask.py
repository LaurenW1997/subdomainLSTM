"""Flood map: the leveed areas on the 100 m grid, from the data the grid was built with.

Source (read only): the leveed-area polygons of the National Levee Database and the list of grid cells inside them that was
written when the grid was built (hydro_ini_head_levee-ed.txt: xi, eta, head; 0-based). The polygons are put on the grid again
here as a check that the list belongs to this grid. For every CRMS site of the flood map it is noted whether it lies in a
leveed area and in which, with the depth observed on the marsh in Francine and Ida: a river levee does not keep a storm surge
out that comes from the other side, so a leveed area with flooded marsh gauges is not closed.
Input : --dir folder with LeveedArea/layers/POLYGON.shp and hydro_ini_head_levee-ed.txt, --grid NPZ with lat, lon of the grid,
        --sites CSV with station, lat, lon and observed depths (marsh_obs_variants_sites.csv)
Output: --out NPZ: mask [lat, lon] of the list, mask_polygons, area_id [lat, lon] (index of the polygon, -1 outside), area_name;
        --out-sites CSV: per site the leveed area and the observed largest depth in the two storms; a table per leveed area is printed
Usage : python leveed_mask.py --dir DIR --grid FILE --sites FILE --out FILE --out-sites FILE
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from shapely.validation import make_valid


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--grid", required=True); ap.add_argument("--sites", required=True); ap.add_argument("--out", required=True); ap.add_argument("--out-sites", required=True)
    a = ap.parse_args(); d = Path(a.dir); warnings.filterwarnings("ignore")
    z = np.load(a.grid); lat, lon = z["lat"], z["lon"]; NY, NX = len(lat), len(lon)
    c = np.loadtxt(d / "hydro_ini_head_levee-ed.txt"); xi, eta = c[:, 0].astype(int), c[:, 1].astype(int); assert xi.max() < NX and eta.max() < NY
    mask = np.zeros((NY, NX), bool); mask[eta, xi] = True
    g = gpd.read_file(d / "LeveedArea" / "layers" / "POLYGON.shp", engine="pyogrio", on_invalid="ignore"); g = g[g.geometry.notnull()].copy()
    g["geometry"] = g.geometry.apply(lambda q: q if q.is_valid else make_valid(q)); g = g.cx[lon[0]:lon[-1], lat[0]:lat[-1]].reset_index(drop=True)
    aid = np.full((NY, NX), -1, np.int16); dlon = float(lon[-1] - lon[0]) / (NX - 1); dlat = float(lat[-1] - lat[0]) / (NY - 1)
    for k, geom in enumerate(g.geometry):
        parts = [geom] if geom.geom_type == "Polygon" else [q for q in getattr(geom, "geoms", []) if q.geom_type == "Polygon"]
        for poly in parts:
            x0, y0, x1, y1 = poly.bounds; i0, i1 = max(int(np.searchsorted(lon, x0)) - 1, 0), min(int(np.searchsorted(lon, x1)) + 1, NX); j0, j1 = max(int(np.searchsorted(lat, y0)) - 1, 0), min(int(np.searchsorted(lat, y1)) + 1, NY)
            if i1 <= i0 or j1 <= j0:
                continue
            px = lambda xy: [((x - lon[i0]) / dlon, (y - lat[j0]) / dlat) for x, y in xy]            # cell centres sit at whole pixel coordinates
            im = Image.new("1", (i1 - i0, j1 - j0), 0); dr = ImageDraw.Draw(im); dr.polygon(px(poly.exterior.coords), fill=1)
            for hole in poly.interiors:
                dr.polygon(px(hole.coords), fill=0)
            ins = np.asarray(im, bool); sub = aid[j0:j1, i0:i1]; sub[ins & (sub < 0)] = k
    mp = aid >= 0
    print(f"grid {NY} x {NX}; cells in the list written with the grid: {int(mask.sum())} ({mask.sum() / 100:.0f} km2); cells inside the polygons put on this grid: {int(mp.sum())} ({mp.sum() / 100:.0f} km2); "
          f"in both: {int((mask & mp).sum())}; share of the list that the polygons confirm: {100 * (mask & mp).sum() / mask.sum():.1f}%")
    np.savez_compressed(a.out, mask=mask, mask_polygons=mp, area_id=aid, area_name=g.name.fillna("").to_numpy(str))

    s = pd.read_csv(a.sites); fr = s[s.test.str.startswith("Francine, inputs observed") & (s.variant == "gauges")].set_index("station"); ida = s[s.test.str.startswith("Ida") & (s.variant == "gauges")].set_index("station")
    st = fr[["lat", "lon"]].copy(); st["francine_observed_largest_depth_m"] = fr.storm_observed_largest_depth_m; st["ida_observed_largest_depth_m"] = ida.storm_observed_largest_depth_m.reindex(st.index)
    jj = np.abs(lat[:, None] - st.lat.to_numpy()[None, :]).argmin(0); ii = np.abs(lon[:, None] - st.lon.to_numpy()[None, :]).argmin(0)
    inside = (st.lat.to_numpy() >= lat[0]) & (st.lat.to_numpy() <= lat[-1]) & (st.lon.to_numpy() >= lon[0]) & (st.lon.to_numpy() <= lon[-1])
    st["in_grid"] = inside; st["in_list"] = mask[jj, ii] & inside; k = np.where(inside, aid[jj, ii], -1); st["leveed_area"] = [g.name[q] if q >= 0 else "" for q in k]
    st.to_csv(a.out_sites); pd.set_option("display.width", 250)
    print(f"CRMS sites in the grid: {int(inside.sum())}; in a leveed area: {int((st.leveed_area != '').sum())} (by the list: {int(st.in_list.sum())})")
    t = st[st.leveed_area != ""].groupby("leveed_area").agg(sites=("lat", "size"), francine_median=("francine_observed_largest_depth_m", "median"), francine_above_03=("francine_observed_largest_depth_m", lambda v: int((v > 0.3).sum())),
                                                           ida_median=("ida_observed_largest_depth_m", "median"), ida_above_03=("ida_observed_largest_depth_m", lambda v: int((v > 0.3).sum())))
    t["area_km2"] = [float((aid == int(np.where(g.name == n)[0][0])).sum()) / 100 for n in t.index]; print(t.sort_values("sites", ascending=False).round(2).to_string())
    o = st[(st.leveed_area == "") & inside]; print(f"sites outside every leveed area: {len(o)}; observed largest depth, median: Francine {o.francine_observed_largest_depth_m.median():.2f} m, Ida {o.ida_observed_largest_depth_m.median():.2f} m")
    ar = pd.Series({n: float((aid == q).sum()) / 100 for q, n in enumerate(g.name)}).sort_values(ascending=False); print("largest leveed areas on the grid (km2):"); print(ar.head(14).round(0).to_string())


if __name__ == "__main__":
    main()
