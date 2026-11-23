"""Flood map over a long period of ordinary days: the forecasts of the water-level model at the control points, through the
mapping model of p2m_paper.py, at the marsh gauges (CRMS), hour by hour, next to the observed depth on the marsh.

For every valid hour v the inputs of the mapping model are the observations of the control points at v (lead 0) or the
forecasts issued 1, 3 and 6 h before for v, moved to the level of the numerical model with the offset of each station
(observed_inputs.py); a control point without a value is filled with its expectation given the others (as forecast_map_check.py).
At every marsh gauge the depth is the median over the land cells around it that have a model (as `p2m_paper.py apply`).
Observed depth on the marsh = observed level (NAVD88, the dataset) minus the surveyed marsh surface of the site.
Input : --fc NPZ of forecast_inputs.py (hourly issue times), --sums DIR (controls_used.csv, xref.npy, sums_<run>.npz), --offsets stations.csv of observed_inputs.py,
        --table config/operational_stations_grid_datum.csv, --model model.npz of p2m_paper.py, --sites CSV station, lat, lon, --land eval_<run>.npz,
        --ida DIR (grid), --levels levels.npz of marsh_obs_variants.py (marsh surface per site), --dataset DIR
Output: --out DIR: series.npz (times, depth_observed [T, S], depth_map_lead<L> [T, S], level_observed, sites, cells with a model per site,
        inputs_lead<L> [T, control points], control-point ids), sites.csv
Usage : python p2m_paper_longrun.py --fc FILE --sums DIR --offsets FILE --table FILE --model FILE --sites FILE --land FILE --ida DIR --levels FILE --dataset DIR --out DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
from observed_inputs import conditional  # noqa: E402
from p2m_paper import predict  # noqa: E402

LEADS = (0, 1, 3, 6)
OTHERS = ["Exp2_no_wind", "Exp3_no_precipitation", "Exp4_river_only", "Exp5_Ida_base", "Exp6_absolute_base", "Exp7_wind_base", "Exp8_precipitation_base",
          "drought_river_storm", "drought_river_no_storm", "flood_river_storm", "flood_river_no_storm"]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("fc", "sums", "offsets", "table", "model", "sites", "land", "ida", "levels", "dataset", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--noise", type=float, default=0.12); ap.add_argument("--radius", type=int, default=3)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "series.npz").exists(), f"{out} has results already"
    sums = Path(a.sums); c = pd.read_csv(sums / "controls_used.csv", dtype={"station_id": str}); P = len(c); used = c.used.to_numpy(bool); xref = np.load(sums / "xref.npy")
    z = np.load(a.fc); F, O = z["forecast"].astype(np.float64), z["observed"].astype(np.float64); valid = pd.DatetimeIndex(z["valid"]); T0, H = F.shape[0], F.shape[1]
    assert len(valid) == T0 + H, "the forecasts must have an issue time every hour"; col = {(s, i): k for k, (s, i) in enumerate(zip(z["source"], z["station_id"]))}
    V = np.arange(H, T0); tv = valid[V]; T = len(V)
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"]; add = {(r.source, r.station_id): float(r.to_navd88_add_m) for r in tab.itertuples() if r.to_navd88_add_m != ""}
    of = pd.read_csv(a.offsets, dtype={"station_id": str}); off_of = {(r.source, r.station_id): float(r.offset_m) for r in of.itertuples()}
    keys = [(r.source, r.station_id) for r in c.itertuples()]; off = np.array([off_of.get(k, np.nan) for k in keys]); assert np.isfinite(off[used]).all() and all(keys[s] in col for s in np.where(used)[0])
    n = 0; Sx = np.zeros(P); Sxx = np.zeros((P, P))
    for r in OTHERS:
        s_ = np.load(sums / f"sums_{r}.npz"); n += int(s_["n"]); Sx += s_["Sx"]; Sxx += s_["Sxx"]
    xm = Sx / n; C = Sxx - n * np.outer(xm, xm); lam = n * a.noise ** 2

    def level(key, lead):
        k = col[key]
        return (O[V, k] if lead == 0 else F[V - lead, lead - 1, k]) + add.get(key, 0.0)

    X = {}; missing = {}
    for L in LEADS:
        x = np.full((T, P), np.nan)
        for s in np.where(used)[0]:
            x[:, s] = level(keys[s], L) + off[s] - xref[s]
        xf = x.copy(); xf[:, ~used] = xm[None, ~used]; miss = ~np.isfinite(xf); missing[L] = float(miss[:, used].mean())
        for s in np.where(miss.any(0))[0]:
            use = used.copy(); use[s] = False; xf[miss[:, s], s] = conditional(C, xm, lam, x[miss[:, s]], use, C[:, [s]], xm[[s]])[:, 0]
        few = ~np.isfinite(xf).all(1); xf[few] = np.nan; X[L] = xf          # hours with fewer than five control points: no map
        print(f"lead {L}: control-point hours without a value {100 * missing[L]:.1f}%, hours without a map {int(few.sum())} of {T}", flush=True)

    m = np.load(a.model); model = {k: m[k] for k in m.files}; jj, ii = model["jj"], model["ii"]; has = model["model"] > 0; mused = model["used"]
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; land = np.load(a.land)["dmax_no_storm"] <= 0.1; idx = np.full((NY, NX), -1, np.int64); idx[jj, ii] = np.arange(len(jj))
    lv = np.load(a.levels); surf = dict(zip(lv["site"], lv["marsh_surface_francine"]))
    st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy")); vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r")
    row = {i: k for k, (s, i) in enumerate(zip(st.source, st.station_id)) if s == "CRMS"}; ti = tm.get_indexer(tv); assert (ti >= 0).all()
    sites = pd.read_csv(a.sites); R = a.radius; info = []; dobs = []; lobs = []; dmap = {L: [] for L in LEADS}
    for s in sites.itertuples():
        j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin()); js, is_ = np.meshgrid(np.arange(max(j - R, 0), min(j + R + 1, NY)), np.arange(max(i - R, 0), min(i + R + 1, NX)), indexing="ij")
        near = (np.hypot(js - j, is_ - i) <= R + 0.5) & land[js, is_]; ids = idx[js[near], is_[near]]; ids = ids[ids >= 0]; w = ids[has[ids]]
        ms = float(surf.get(s.station, np.nan)); ob = np.asarray(vals[row[s.station], ti], np.float64) if s.station in row else np.full(T, np.nan)
        info.append({"station": s.station, "lat": s.lat, "lon": s.lon, "land_cells": int(near.sum()), "in_prediction_area": len(ids), "with_a_model": len(w), "marsh_surface_m": ms, "ground_grid_m": float(np.median(-h[js[near], is_[near]])) if near.any() else np.nan,
                     "observed_hours": int(np.isfinite(ob).sum())})
        lobs.append(ob.astype(np.float32)); dobs.append((ob - ms).astype(np.float32))
        for L in LEADS:
            if len(w):
                ok = np.isfinite(X[L]).all(1); p = np.full(T, np.nan, np.float32); p[ok] = np.nanmedian(predict(model, X[L][ok][:, mused], w), 1); dmap[L].append(p)
            else:
                dmap[L].append(np.full(T, np.nan, np.float32))
    pd.DataFrame(info).to_csv(out / "sites.csv", index=False)
    np.savez_compressed(out / "series.npz", times=np.array(tv.strftime("%Y-%m-%d %H:%M"), dtype=str), station=sites.station.to_numpy(str), depth_observed=np.stack(dobs, 1), level_observed=np.stack(lobs, 1),
                        control_source=c.source.to_numpy(str), control_station_id=c.station_id.to_numpy(str), control_used=used,
                        **{f"depth_map_lead{L}": np.stack(dmap[L], 1) for L in LEADS}, **{f"inputs_lead{L}": X[L].astype(np.float32) for L in LEADS})
    t = pd.DataFrame(info); print(f"{len(t)} sites, {int((t.with_a_model > 0).sum())} with a model, {int(((t.with_a_model > 0) & (t.observed_hours > 24 * 60)).sum())} of them with more than 60 days of observations; {T} hours {tv[0]} .. {tv[-1]}"); print("->", out)


if __name__ == "__main__":
    main()
