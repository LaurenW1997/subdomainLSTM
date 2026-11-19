"""Flood map, control points chosen with the set-up of the numerical model in mind (wetting and drying, interface, boundary).

control_points.py took, for every gauge, the cell within 2 km whose hindcast correlates best with the observations, whatever
the cell is. This script looks at what those cells are and chooses again among cells that can stand for a gauge:
  always water   the cell holds at least --min-depth of water in every hour of every run (ocean-model cells that fall dry are
                 masked in the archive and count as dry; land-model cells must be channel or lake cells, not flooded land)
  interface      not within --interface-cells cells of the interface at which the two models exchange water
  boundary       not within --edge-cells cells of the edge of the grid
Among these cells within --radius cells of the gauge, the best-correlated one is found and then the nearest cell whose
correlation is within --tolerance of it is taken (a far cell is not preferred for a gain in the third decimal).
Output columns best_* are those of control_points.py, so mapping_fit.py reads the file unchanged; old_* keep the earlier
choice and what kind of cell it was, for comparison.
Input : --ida DIR (grid with domain_mask and coupling_interface), --cache hindcast float32 [T, lat, lon], --dataset DIR,
        --table config/operational_stations_grid_datum.csv, --sums-dir DIR (sums_<run>.npz with the smallest depth of every cell),
        --old CSV of control_points.py
Output: --out CSV, one row per station with observations in the run
Usage : python control_cells.py --ida DIR --cache FILE --dataset DIR --table FILE --sums-dir DIR --old FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import RUNS  # noqa: E402


def grow(mask: np.ndarray, k: int) -> np.ndarray:
    """The mask widened by k cells in every direction (8 neighbours)."""
    m = mask.copy()
    for _ in range(k):
        n = m.copy()
        n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
        n[1:, 1:] |= m[:-1, :-1]; n[:-1, :-1] |= m[1:, 1:]; n[1:, :-1] |= m[:-1, 1:]; n[:-1, 1:] |= m[1:, :-1]
        m = n
    return m


def score(obs, mod):
    ok = np.isfinite(obs) & np.isfinite(mod)
    if ok.sum() < 48 or np.std(mod[ok]) < 1e-4 or np.std(obs[ok]) < 1e-4:
        return np.nan, np.nan, np.nan, np.nan
    o, m = obs[ok], mod[ok]; bias = float((m - o).mean())
    return float(np.corrcoef(o, m)[0, 1]), bias, float(np.sqrt(((m - bias - o) ** 2).mean())), float(np.std(m) / np.std(o))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True); ap.add_argument("--cache", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--table", required=True)
    ap.add_argument("--sums-dir", required=True); ap.add_argument("--old", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--radius", type=int, default=20); ap.add_argument("--min-depth", type=float, default=0.1); ap.add_argument("--interface-cells", type=int, default=3)
    ap.add_argument("--edge-cells", type=int, default=10); ap.add_argument("--tolerance", type=float, default=0.02)
    a = ap.parse_args()
    g = netCDF4.Dataset(Path(a.ida) / "grid_lower_mississippi_100m.nc")
    h = np.asarray(np.ma.filled(g["h"][:], np.nan), np.float32); roms = np.asarray(g["domain_mask"][:]) == 1; iface = np.asarray(g["coupling_interface"][:]) != 0; g.close()
    NY, NX = h.shape
    dmin = np.min([np.load(Path(a.sums_dir) / f"sums_{r}.npz")["dmin"] for r in RUNS], 0).reshape(NY, NX)       # smallest depth of every cell over all runs
    always = dmin > a.min_depth
    near_if = grow(iface, a.interface_cells)
    jj, ii = np.mgrid[0:NY, 0:NX]; edge = np.minimum(np.minimum(jj, NY - 1 - jj), np.minimum(ii, NX - 1 - ii)); del jj, ii
    valid = always & ~near_if & (edge >= a.edge_cells)
    print(f"grid {NY} x {NX}: always water {int(always.sum())} cells ({100 * always.mean():.1f}%), interface cells {int(iface.sum())}, within {a.interface_cells} cells of it {int(near_if.sum())}, "
          f"valid for a control point {int(valid.sum())}")

    wl = np.load(a.cache, mmap_mode="r"); T = wl.shape[0]
    d = netCDF4.Dataset(Path(a.ida) / "water_level_Exp1_fully_coupled.nc"); times = pd.DatetimeIndex(netCDF4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)); d.close()
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"].set_index(["source", "station_id"])
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy"))
    vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r"); row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    i0 = int(tm.get_indexer([times[0]])[0])
    old = pd.read_csv(a.old, dtype={"station_id": str}); old = old[old.obs_hours >= 200]

    recs = []; R = a.radius
    for r in old.itertuples():
        key = (r.source, r.station_id); t_ = tab.loc[key]; add = float(t_.to_navd88_add_m) if t_.to_navd88_add_m != "" else 0.0
        obs = np.asarray(vals[row[key], i0:i0 + T], np.float64) + add; j, i = int(r.j), int(r.i)
        j0, j1, i0_, i1 = max(0, j - R), min(NY, j + R + 1), max(0, i - R), min(NX, i + R + 1)
        blk = np.asarray(wl[:, j0:j1, i0_:i1], np.float64); hh = h[j0:j1, i0_:i1]; rr = roms[j0:j1, i0_:i1]; vv = valid[j0:j1, i0_:i1]
        dist = np.hypot(np.arange(j0, j1)[:, None] - j, np.arange(i0_, i1)[None, :] - i); vv = vv & (dist <= R + 0.5)
        rec = {c: getattr(r, c) for c in ("source", "station_id", "name", "lat", "lon", "station_datum", "datum_known", "obs_hours", "obs_range_m", "j", "i")}
        oj, oi = int(r.best_j), int(r.best_i)                                 # what the earlier choice was
        os_ = np.asarray(wl[:, oj, oi], np.float64)
        rec.update({"old_j": oj, "old_i": oi, "old_r": r.best_r, "old_std_ratio": r.best_std_ratio, "old_dist_cells": r.best_dist_cells, "old_model": r.best_model,
                    "old_always_water": bool(always[oj, oi]), "old_min_depth_m": float(dmin[oj, oi]), "old_missing_hours": int(np.isnan(os_).sum()), "old_near_interface": bool(near_if[oj, oi]),
                    "old_edge_cells": int(edge[oj, oi]), "old_valid": bool(valid[oj, oi]), "own_always_water": bool(always[j, i]), "own_near_interface": bool(near_if[j, i]), "edge_cells": int(edge[j, i]),
                    "valid_cells_within_radius": int(vv.sum())})
        best = None
        if vv.any():
            cand = np.argwhere(vv); sc = []
            for cj, ci in cand:
                x = blk[:, cj, ci]; x = x if rr[cj, ci] else x - float(hh[cj, ci])          # always water: no gaps to fill
                sc.append(score(obs, x))
            sc = np.array(sc); rr_ = sc[:, 0]
            if np.isfinite(rr_).any():
                top = np.nanmax(rr_); ok = np.where(rr_ >= top - a.tolerance)[0]; k = ok[np.argmin(dist[cand[ok, 0], cand[ok, 1]])]
                cj, ci = cand[k]; best = (int(cj + j0), int(ci + i0_), sc[k], float(dist[cj, ci]), float(top))
                kn = int(np.argmin(dist[cand[:, 0], cand[:, 1]])); rec.update({"nearest_valid_dist_cells": float(dist[cand[kn, 0], cand[kn, 1]]), "nearest_valid_r": float(sc[kn, 0]), "nearest_valid_std_ratio": float(sc[kn, 3])})
        if best is not None:
            bj, bi, s_, dd, top = best
            rec.update({"best_j": bj, "best_i": bi, "best_dist_cells": dd, "best_model": "ROMS" if roms[bj, bi] else "WRF-Hydro", "best_h_m": float(h[bj, bi]), "best_min_depth_m": float(dmin[bj, bi]),
                        "best_r": s_[0], "best_bias_m": s_[1], "best_rmse_unbiased_m": s_[2], "best_std_ratio": s_[3], "best_r_any_valid_cell": top, "best_edge_cells": int(edge[bj, bi])})
        else:
            rec.update({"best_j": -1, "best_i": -1, "best_r": np.nan, "best_std_ratio": np.nan})
        recs.append(rec)
    out = pd.DataFrame(recs); out.to_csv(a.out, index=False)
    o8 = out.old_r >= 0.8; n8 = out.best_r >= 0.8; amp = lambda c: (out[c] >= 0.5) & (out[c] <= 2.0)
    print(f"{len(out)} stations with observations")
    print(f"earlier choice (best cell of any kind): correlation >= 0.8 at {int(o8.sum())}; of these the cell is always water at {int((o8 & out.old_always_water).sum())}, "
          f"falls dry or is flooded land at {int((o8 & ~out.old_always_water).sum())}, within {a.interface_cells} cells of the interface at {int((o8 & out.old_near_interface).sum())}, "
          f"valid at {int((o8 & out.old_valid).sum())}")
    print(f"new choice (valid cells only): a valid cell within {R} cells at {int((out.valid_cells_within_radius > 0).sum())} stations; correlation >= 0.8 at {int(n8.sum())}; "
          f"and amplitude 0.5 to 2 at {int((n8 & amp('best_std_ratio')).sum())}; median distance {out.best_dist_cells[n8].median():.1f} cells (earlier {out.old_dist_cells[o8].median():.1f})")
    print("->", a.out)


if __name__ == "__main__":
    main()
