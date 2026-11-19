"""Flood map, feasibility for the river valleys: what the grid and the river gauges have at the high-water marks of 2016.

The valleys of the north flood by rainfall, which the gauges on the coast do not see. The river gauges there do. Before
anything is built, this collects what is needed to judge whether "level at the river gauges -> depth on the valley floor"
can work, using the high-water marks USGS surveyed after the floods of March and August 2016 (flood event viewer):
  marks     for every mark: its grid cell, the ground level of the grid there and around it, whether the cell is land, in a
            leveed area, flooded in the model runs of Ida with or without rainfall
  gauges    for every gauge with a known NAVD88 datum: highest observed level in the two floods, the level before, the share
            of hours observed, whether it reports in real time
Input : --marks CSV (event, hwm_id, lat, lon, elev_ft, height_above_ground_ft, ...), --ida DIR, --eval eval_<run>.npz, --fit DIR (sums of all runs),
        --leveed NPZ, --dataset DIR, --table config/operational_stations_grid_datum.csv, --live FILE
Output: --out DIR: marks_grid.csv, gauges_2016.csv
Usage : python valley_feasibility.py --marks FILE --ida DIR --eval FILE --fit DIR --leveed FILE --dataset DIR --table FILE --live FILE --out DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402

FT = 0.3048
EVENTS = {"2016 Aug LA Flood": ("2016-08-10", "2016-08-31"), "2016 Mar LA Flood": ("2016-03-08", "2016-03-31")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marks", required=True); ap.add_argument("--ida", required=True); ap.add_argument("--eval", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--leveed", required=True)
    ap.add_argument("--dataset", required=True); ap.add_argument("--table", required=True); ap.add_argument("--live", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--no-rain-runs", nargs="+", default=["Exp3_no_precipitation", "Exp7_wind_base"])
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "marks_grid.csv").exists(), f"{out} has results already"
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; ground = -h
    ev = np.load(a.eval); land = ev["dmax_no_storm"] <= 0.1; ever = ev["dmax_all_runs"] > 0.1; hind = ev["peak_true"]
    coast = np.max([np.load(Path(a.fit) / f"sums_{r}.npz")["dmax"] for r in a.no_rain_runs], 0).reshape(NY, NX) > 0.1; lm = np.load(a.leveed)["mask"]
    m = pd.read_csv(a.marks); jj = np.abs(lat[:, None] - m.lat.to_numpy()[None, :]).argmin(0); ii = np.abs(lon[:, None] - m.lon.to_numpy()[None, :]).argmin(0)
    m["j"], m["i"] = jj, ii; m["elev_m"] = m.elev_ft * FT; m["height_above_ground_m"] = m.height_above_ground_ft * FT; m["ground_surveyed_m"] = m.elev_m - m.height_above_ground_m
    m["ground_grid_m"] = ground[jj, ii]; m["cell_is_land"] = land[jj, ii]; m["cell_model"] = np.where(roms[jj, ii], "ROMS", "WRF-Hydro"); m["leveed"] = lm[jj, ii]
    m["ida_runs"] = np.where(coast[jj, ii], "flooded without rainfall", np.where(ever[jj, ii], "flooded only with rainfall", "dry in all runs")); m["ida_hindcast_peak_depth_m"] = hind[jj, ii]
    for R in (1, 3, 10):                                                   # the ground of the grid around the mark: lowest and median
        lo_, md = [], []
        for j, i in zip(jj, ii):
            g = ground[max(j - R, 0):j + R + 1, max(i - R, 0):i + R + 1]; lo_.append(float(np.nanmin(g))); md.append(float(np.nanmedian(g)))
        m[f"ground_grid_lowest_within_{R}_cells_m"] = lo_; m[f"ground_grid_median_within_{R}_cells_m"] = md
    m.to_csv(out / "marks_grid.csv", index=False)

    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[(tab.domain == "Louisiana100m_full") & (tab.to_navd88_add_m != "")]
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; live = set(Path(a.live).read_text().split()); rows = []
    for r in tab.itertuples():
        key = (r.source, r.station_id)
        if key not in row:
            continue
        add = float(r.to_navd88_add_m); rec = {"source": r.source, "station_id": r.station_id, "name": r.name, "lat": float(r.lat), "lon": float(r.lon), "to_navd88_add_m": add, "real_time": r.station_id in live}
        for nm, (d0, d1) in EVENTS.items():
            i0, i1 = tm.get_indexer([pd.Timestamp(d0), pd.Timestamp(d1)]); v = np.asarray(vals[row[key], i0:i1], float) + add; b = np.asarray(vals[row[key], i0 - 720:i0], float) + add; k = nm.split()[1].lower()
            rec.update({f"{k}_peak_navd88_m": float(np.nanmax(v)) if np.isfinite(v).any() else np.nan, f"{k}_observed_share": float(np.isfinite(v).mean()), f"{k}_level_before_m": float(np.nanmedian(b)) if np.isfinite(b).sum() > 100 else np.nan,
                        f"{k}_peak_time": str(tm[i0 + int(np.nanargmax(v))]) if np.isfinite(v).any() else ""})
        j, i = int(np.abs(lat - rec["lat"]).argmin()), int(np.abs(lon - rec["lon"]).argmin()); rec.update({"ground_grid_m": float(ground[j, i]), "cell_is_land": bool(land[j, i])}); rows.append(rec)
    g = pd.DataFrame(rows); g.to_csv(out / "gauges_2016.csv", index=False)
    print(len(m), "marks;", len(g), "gauges with a NAVD88 datum;", int(g.real_time.sum()), "of them in real time;", "with a peak in August 2016:", int(g.aug_peak_navd88_m.notna().sum())); print("->", out)


if __name__ == "__main__":
    main()
