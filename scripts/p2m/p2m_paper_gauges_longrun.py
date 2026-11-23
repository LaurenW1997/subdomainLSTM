"""Flood map against the water-level gauges that are not control points, hour by hour over the two test years.

Gauges: USGS / NOAA stations of the dataset inside the grid, not a control point, with at least --min-hours observations in the
period. A gauge stands in a channel, creek, river or bay; its cell on the 100 m grid is the nearest cell within --radius cells
that the mapping model has a model for, a cell that is always under water (Type 1) before one that is dry at times (Type 2).
Water level of the map there = depth of the cell + ground of the cell. A gauge outside the prediction area, or with no such
cell, has no map. Inputs of the mapping model: those of p2m_paper_longrun.py (observed, and forecasts issued 1, 3, 6 h before).
Input : --series series.npz of p2m_paper_longrun.py, --sums DIR (controls_used.csv), --model model.npz, --ida DIR, --dataset DIR
Output: --out DIR: gauges.csv (every gauge inside the grid: cell, type, has a map), series.npz (times, level_observed [T, G], depth_map_lead<L>,
        level_map_lead<L> for the gauges with a map), stations_for_forecasts.csv (source, station_id of the gauges with a map)
Usage : python p2m_paper_gauges_longrun.py --series FILE --sums DIR --model FILE --ida DIR --dataset DIR --out DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
from p2m_paper import predict  # noqa: E402

LEADS = (0, 1, 3, 6)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("series", "sums", "model", "ida", "dataset", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--radius", type=int, default=3); ap.add_argument("--min-hours", type=int, default=7200); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "series.npz").exists(), f"{out} has results already"
    z = np.load(a.series); t = pd.DatetimeIndex(z["times"]); T = len(t); X = {L: z[f"inputs_lead{L}"].astype(np.float64) for L in LEADS}
    c = pd.read_csv(Path(a.sums) / "controls_used.csv", dtype={"station_id": str}); used = set(c[c.used].station_id)
    m = np.load(a.model); model = {k: m[k] for k in m.files}; jj, ii = model["jj"], model["ii"]; typ = model["type"]; has = model["model"] > 0; mused = model["used"]
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; idx = np.full((NY, NX), -1, np.int64); idx[jj, ii] = np.arange(len(jj))
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r"); ti = tm.get_indexer(t); assert (ti >= 0).all()
    g = st[(st.source != "CRMS") & ~st.station_id.isin(used)].copy(); g["lat"] = g.lat.astype(float); g["lon"] = g.lon.astype(float)
    g = g[(g.lat > lat[0]) & (g.lat < lat[-1]) & (g.lon > lon[0]) & (g.lon < lon[-1])].reset_index(drop=True); R = a.radius; rows = []; obs = []; cells = []
    for r in g.itertuples():
        o = np.asarray(vals[int(r.row), ti], np.float64); n = int(np.isfinite(o).sum())
        if n < a.min_hours:
            continue
        j, i = int(np.abs(lat - r.lat).argmin()), int(np.abs(lon - r.lon).argmin()); js, is_ = np.meshgrid(np.arange(max(j - R, 0), min(j + R + 1, NY)), np.arange(max(i - R, 0), min(i + R + 1, NX)), indexing="ij")
        d = np.hypot(js - j, is_ - i); q = idx[js, is_]; inarea = bool(idx[j, i] >= 0); ok = (d <= R + 0.5) & (q >= 0); ok[ok] &= has[q[ok]]; best = -1; kind = "outside the prediction area" if not inarea else "no cell with a model within reach"
        if inarea and ok.any():
            t1 = ok.copy(); t1[ok] &= typ[q[ok]] == 1; pick = t1 if t1.any() else ok; w = np.where(pick, d, 1e9); k = int(w.argmin()); best = int(q.ravel()[k]); kind = "always under water (Type 1)" if t1.any() else "dry at times (Type 2)"
        rows.append({"source": r.source, "station_id": r.station_id, "name": r.name, "lat": r.lat, "lon": r.lon, "datum": r.datum, "observed_hours": n, "in_prediction_area": inarea, "cell": kind, "has_a_map": best >= 0,
                     "cell_j": int(jj[best]) if best >= 0 else -1, "cell_i": int(ii[best]) if best >= 0 else -1, "cell_distance_m": float(100 * np.hypot(jj[best] - j, ii[best] - i)) if best >= 0 else np.nan,
                     "cell_ground_m": float(-h[jj[best], ii[best]]) if best >= 0 else np.nan, "cell_in_ocean_model": bool(roms[jj[best], ii[best]]) if best >= 0 else False, "cell_model": int(model["model"][best]) if best >= 0 else 0})
        if best >= 0:
            obs.append(o.astype(np.float32)); cells.append(best)
    G = pd.DataFrame(rows); G.to_csv(out / "gauges.csv", index=False); M = G[G.has_a_map].reset_index(drop=True); cells = np.array(cells); ground = M.cell_ground_m.to_numpy(); o_ = {}
    for L in LEADS:
        ok = np.isfinite(X[L]).all(1); p = np.full((T, len(cells)), np.nan, np.float32); p[ok] = predict(model, X[L][ok][:, mused], cells); o_[f"depth_map_lead{L}"] = p; o_[f"level_map_lead{L}"] = (p + ground[None, :]).astype(np.float32)
    np.savez_compressed(out / "series.npz", times=z["times"], source=M.source.to_numpy(str), station_id=M.station_id.to_numpy(str), level_observed=np.stack(obs, 1), **o_)
    M[["source", "station_id"]].to_csv(out / "stations_for_forecasts.csv", index=False)
    print(f"gauges inside the grid with at least {a.min_hours} h: {len(G)}; in the prediction area {int(G.in_prediction_area.sum())}; with a map {len(M)}: " + ", ".join(f"{k} {v}" for k, v in M.cell.value_counts().items())); print("->", out)


if __name__ == "__main__":
    main()
