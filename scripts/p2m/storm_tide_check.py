"""Flood map, check against independent peaks: the storm-tide sensors USGS deployed for Hurricane Ida.

The sensors were temporary (USGS Flood Event Viewer, event '2021 Ida', peak summaries) and are in none of the inputs. For
every site this script reads, around the nearest cell of the grid, the peak water surface elevation of
  the numerical model (hindcast),
  the mapping model driven by the model's own control-point series,
  the mapping model driven by the observed water levels,
as the median over the cells within --radius cells that are flooded or water at the peak (depth above 0.1 m); sensors stand
on piers and poles at the water's edge, and one 100 m cell may be dry land.
Input : --sites CSV (site_number, latitude_dd, longitude_dd, peak_m ...), --ida DIR (grid), --eval-model FILE (eval npz of
        mapping_fit.py with peak_true and peak_exact), --eval-observed FILE (eval npz with peak_observed)
Output: --out CSV, the sites with the three peaks (m, on the level of the numerical model), the cell and the ground level
Usage : python storm_tide_check.py --sites FILE --ida DIR --eval-model FILE --eval-observed FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True); ap.add_argument("--ida", required=True); ap.add_argument("--eval-model", required=True); ap.add_argument("--eval-observed", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--radius", type=int, default=2)
    a = ap.parse_args()
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape
    zm, zo = np.load(a.eval_model), np.load(a.eval_observed)
    fields = {"hindcast": zm["peak_true"], "mapping_model_inputs": zm["peak_exact"], "mapping_observed_inputs": zo["peak_observed"]}      # peak depth (m)
    s = pd.read_csv(a.sites); recs = []
    for r in s.itertuples():
        j, i = int(np.abs(lat - r.latitude_dd).argmin()), int(np.abs(lon - r.longitude_dd).argmin())
        inside = (lat.min() <= r.latitude_dd <= lat.max()) and (lon.min() <= r.longitude_dd <= lon.max())
        rec = {"site_number": r.site_number, "inside_grid": inside, "j": j, "i": i, "cell_model": "ROMS" if roms[j, i] else "WRF-Hydro", "cell_ground_m": float(-h[j, i])}
        if inside:
            sl = (slice(max(0, j - a.radius), min(NY, j + a.radius + 1)), slice(max(0, i - a.radius), min(NX, i + a.radius + 1)))
            for k, d in fields.items():
                dep = d[sl]; wse = dep - h[sl]; wet = dep > 0.1
                rec[f"{k}_wet_cells"] = int(wet.sum()); rec[f"{k}_peak_m"] = float(np.median(wse[wet])) if wet.any() else np.nan
                rec[f"{k}_depth_nearest_m"] = float(d[j, i])
        recs.append(rec)
    out = s.merge(pd.DataFrame(recs), on="site_number"); out.to_csv(a.out, index=False)
    pd.set_option("display.width", 250); print(out.drop(columns=[c for c in ("description", "calc_notes") if c in out.columns]).round(2).to_string(index=False)); print("->", a.out)


if __name__ == "__main__":
    main()
