"""Flood map from observations: the levels fitted at the marsh gauges (marsh_obs_variants.py) spread over the grid.

For a land cell (dry throughout the run without a hurricane) near the CRMS sites:
    water level of the cell = mean of the levels at the --neighbours nearest sites, weights 1 / distance^2
    depth                   = water level - ground level of the grid, not below zero
Where the map is given (the rest stays empty):
    near      the nearest site is within --radius km
    not behind a levee or bank. No levee data is used; two signs from the grid and the hindcast of Ida stand in for it:
              the ground lies below --low m and the cell is dry in normal conditions, or
              in Ida the level of the sites around the cell was --ida-level m or more above its ground while the numerical
              model, whose grid has the levees, kept the cell dry.
The same field from the mapping model fitted on the Ida runs (mapping_fit.py) is computed for the same cells.
Check against the sites: the level of a site taken from the nearest OTHER sites and the ground of the grid cells next to it
(what a cell without a gauge gets), compared with the observed depth on the marsh.
Input : --levels levels.npz of marsh_obs_variants.py, --ida DIR, --eval eval_<run>.npz of mapping_fit.py (hindcast), --fit DIR and --inputs inputs.npz (for the earlier mapping model)
Output: --out DIR: map_coarse.npz, areas.csv, sites.csv, summary.txt
Usage : python marsh_map.py --levels FILE --ida DIR --eval FILE --fit DIR --inputs FILE --out DIR
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid, training  # noqa: E402
from marsh_obs_fit import FR_CALM, FR_STORM, IDA_STORM, metrics  # noqa: E402

KX, KY = np.cos(np.deg2rad(29.7)) * 111.2, 111.2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", required=True); ap.add_argument("--ida", required=True); ap.add_argument("--eval", required=True); ap.add_argument("--fit"); ap.add_argument("--inputs"); ap.add_argument("--out", required=True)
    ap.add_argument("--train-runs", nargs="+"); ap.add_argument("--holdout", default="Exp1_fully_coupled")
    ap.add_argument("--radius", type=float, default=10.0); ap.add_argument("--neighbours", type=int, default=4); ap.add_argument("--low", type=float, default=-0.2); ap.add_argument("--ida-level", type=float, default=0.5)
    ap.add_argument("--west-limit", type=float, default=-92.5); ap.add_argument("--step", type=int, default=4); ap.add_argument("--chunk", type=int, default=40000); ap.add_argument("--wet", type=float, default=0.1)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "summary.txt").exists(), f"{out} has results already"
    t00 = time.time(); h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; ground = -h
    ev = np.load(a.eval); land = ev["dmax_no_storm"] <= 0.1; water = ev["dmin_all_runs"] > 0.1; hind = ev["peak_true"]
    z = np.load(a.levels, allow_pickle=False); ok = z["fitted"] & np.isfinite(z["level_francine_inputs_observed"]).all(0) & np.isfinite(z["level_ida_left_out"]).all(0)
    slat, slon = z["lat"][ok], z["lon"][ok]; sid = z["site"][ok]; S = int(ok.sum())
    tF = pd.DatetimeIndex(z["times_francine"]); tI = pd.DatetimeIndex(z["times_ida"]); stormF = np.asarray((tF >= FR_STORM[0]) & (tF < FR_STORM[1])); calmF = np.asarray(tF < FR_CALM); stormI = np.asarray((tI >= IDA_STORM[0]) & (tI <= IDA_STORM[1]))
    L0, L6, LI = (z[k][:, ok].astype(np.float32) for k in ("level_francine_inputs_observed", "level_francine_inputs_forecast_6h", "level_ida_left_out"))

    jj, ii = np.where(land & (lon[None, :] >= a.west_limit) & (lat[:, None] >= slat.min() - 0.15) & (lat[:, None] <= slat.max() + 0.15)); N = len(jj)
    nb = np.zeros((N, a.neighbours), np.int32); dn = np.zeros((N, a.neighbours), np.float32); sx, sy = (slon * KX).astype(np.float32), (slat * KY).astype(np.float32)
    for c in range(0, N, a.chunk):
        d2 = ((lon[ii[c:c + a.chunk]] * KX).astype(np.float32)[:, None] - sx[None, :]) ** 2 + ((lat[jj[c:c + a.chunk]] * KY).astype(np.float32)[:, None] - sy[None, :]) ** 2
        k = np.argpartition(d2, a.neighbours - 1, 1)[:, :a.neighbours]; nb[c:c + a.chunk] = k; dn[c:c + a.chunk] = np.sqrt(np.take_along_axis(d2, k, 1))
    near = dn.min(1) <= a.radius; w = 1.0 / np.maximum(dn, 0.1) ** 2; w /= w.sum(1, keepdims=True); g = ground[jj, ii].astype(np.float32)
    print(f"{N} land cells in the latitude band of the sites, {int(near.sum())} within {a.radius} km of a site; neighbours found in {time.time() - t00:.0f} s", flush=True)

    def peak(L, hours):
        """Largest depth of every cell over the given hours."""
        p = np.zeros(N, np.float32); Lh = L[hours]
        for c in range(0, N, a.chunk):
            ws = np.einsum("tnk,nk->tn", Lh[:, nb[c:c + a.chunk]], w[c:c + a.chunk]); p[c:c + a.chunk] = np.maximum(ws.max(0) - g[c:c + a.chunk], 0)
        return p

    pI = peak(LI, stormI); below = g < a.low; kept_dry = (pI >= a.ida_level) & (hind[jj, ii] <= 0.1); cover = near & ~below & ~kept_dry
    f = {"from observations, inputs observed": peak(L0, stormF), "from observations, inputs forecast 6 h before": peak(L6, stormF), "from observations, inputs observed, calm hours before the storm": peak(L0, calmF)}
    lines = [f"{S} sites; land cells east of {-a.west_limit} W: {int((land & (lon[None, :] >= a.west_limit)).sum()) / 100:.0f} km2; within {a.radius} km of a site: {near.sum() / 100:.0f} km2",
             f"taken out as behind a levee or bank: ground below {a.low} m yet dry in normal conditions {int((near & below).sum()) / 100:.0f} km2; kept dry by the numerical model in Ida while the sites around stood {a.ida_level} m or more above the ground "
             f"{int((near & ~below & kept_dry).sum()) / 100:.0f} km2; the map covers {cover.sum() / 100:.0f} km2"]
    full = lambda v, m: np.where(m, v, 0).astype(np.float32)
    def to_grid(v):
        o = np.zeros((NY, NX), np.float32); o[jj, ii] = v; return o
    if a.fit and a.inputs:                                                # the mapping model fitted on the Ida runs, same hours
        _, name = training(a); B = np.load(Path(a.fit) / f"coef_{name}.npy"); m_ = np.load(Path(a.fit) / f"fitmeta_{name}.npz"); xm, ym = m_["xm"], m_["ym"]; zi = np.load(a.inputs); idx = jj * NX + ii
        add = np.where(roms, h, 0).astype(np.float32).ravel()[idx]; Bc = B[:, idx]; del B
        for lab, key in (("fitted on the Ida runs, inputs observed", "lead0"), ("fitted on the Ida runs, inputs forecast 6 h before", "lead6")):
            X = (zi[key][zi["storm"]] - xm[None, :]).astype(np.float32); p = np.zeros(N, np.float32)
            for k in range(0, len(X), 24):
                p = np.maximum(p, np.maximum(X[k:k + 24] @ Bc + ym[idx][None, :] + add[None, :], 0).max(0))
            f[lab] = p
    rows = []
    for lab, v in f.items():
        rows.append({"field": lab, **{f"above {t} m (km2)": float(((v > t) & cover).sum()) / 100 for t in (0.1, 0.3, 0.5, 1.0, 2.0)}, "mean depth where above 0.1 m (m)": float(v[(v > 0.1) & cover].mean())})
    ar = pd.DataFrame(rows); ar.to_csv(out / "areas.csv", index=False); pd.set_option("display.width", 250); lines += ["", f"flooded land inside the {cover.sum() / 100:.0f} km2 the map covers, largest depth of 10 to 13 September 2024:", ar.round(2).to_string(index=False)]

    s_ = a.step; ny, nx = NY // s_, NX // s_; blk = lambda x, fn: fn(fn(x[:ny * s_, :nx * s_].reshape(ny, s_, nx, s_), 3), 1)
    o = {"lat": lat[:ny * s_].reshape(ny, s_).mean(1), "lon": lon[:nx * s_].reshape(nx, s_).mean(1), "land_frac": blk(land.astype(np.float32), np.mean), "water_frac": blk(water.astype(np.float32), np.mean),
         "cover_frac": blk(to_grid(cover.astype(np.float32)), np.mean), "behind_levee_frac": blk(to_grid((near & (below | kept_dry)).astype(np.float32)), np.mean), "site_lat": slat, "site_lon": slon, "site": sid}
    for lab, v in f.items():
        o["peak | " + lab] = blk(to_grid(full(v, cover)), np.max)
    np.savez_compressed(out / "map_coarse.npz", **o)

    # check at the sites: the level from the nearest other sites, the ground of the grid cells next to the site
    dss = np.hypot((slon[:, None] - slon[None, :]) * KX, (slat[:, None] - slat[None, :]) * KY); np.fill_diagonal(dss, np.inf); nbs = np.argsort(dss, 1)[:, :a.neighbours]
    wss = 1.0 / np.maximum(np.take_along_axis(dss, nbs, 1), 0.1) ** 2; wss /= wss.sum(1, keepdims=True); others = lambda L: np.einsum("tsk,sk->ts", L[:, nbs], wss)
    cell_j = np.abs(lat[:, None] - slat[None, :]).argmin(0); cell_i = np.abs(lon[:, None] - slon[None, :]).argmin(0); gcell = np.full(S, np.nan); incov = np.zeros(S, bool); flagged = np.zeros(S, bool); cg = to_grid(cover.astype(np.float32)) > 0
    pg = to_grid((near & (below | kept_dry)).astype(np.float32)) > 0
    for s in range(S):
        j0, j1, i0, i1 = max(cell_j[s] - 3, 0), cell_j[s] + 4, max(cell_i[s] - 3, 0), cell_i[s] + 4; m = land[j0:j1, i0:i1]
        if m.any():
            gcell[s] = float(np.median(ground[j0:j1, i0:i1][m])); incov[s] = bool((cg[j0:j1, i0:i1] & m).any()); flagged[s] = bool((pg[j0:j1, i0:i1] & m).mean() > 0.5)
    om, od, gs = z["observed_to_marsh_francine"][:, ok], z["observed_level_francine"][:, ok], z["marsh_surface_francine"][ok]; meta = pd.DataFrame({"station_id": sid, "lat": slat, "lon": slon}); recs = []
    for lab, L, gg in (("the site's own fit, surveyed marsh surface | inputs observed", L0, gs), ("the site's own fit, surveyed marsh surface | inputs forecast 6 h before", L6, gs),
                       ("level from the nearest other sites, surveyed marsh surface | inputs forecast 6 h before", others(L6), gs),
                       ("level from the nearest other sites, ground of the grid | inputs observed", others(L0), gcell), ("level from the nearest other sites, ground of the grid | inputs forecast 6 h before", others(L6), gcell)):
        for s in range(S):
            if np.isfinite(gg[s]) and np.isfinite(gcell[s]) and incov[s]:
                r = metrics(lab, meta.iloc[s], om[:, s], L[:, s] - gg[s], od[:, s], L[:, s], calmF, stormF, a.wet)
                if r:
                    r.update({"ground_grid_m": gcell[s], "marsh_surface_m": float(gs[s])}); recs.append(r)
    t = pd.DataFrame(recs); t.to_csv(out / "sites.csv", index=False); t["pe"] = t.storm_map_largest_depth_m - t.storm_observed_largest_depth_m
    sm_ = t.groupby("field", sort=False).apply(lambda y: pd.Series({"sites": len(y), "rmse_depth_median_m": y.rmse_depth_m.median(), "calm_flooded_observed": np.average(y.calm_observed_flooded_share.dropna(), weights=y.calm_hours.dropna()),
                                                                    "calm_flooded_map": np.average(y.calm_map_flooded_share.dropna(), weights=y.calm_hours.dropna()), "largest_mean_error_m": y.pe.mean(), "largest_rms_error_m": np.sqrt((y.pe ** 2).mean()),
                                                                    "largest_corr": y[["storm_observed_largest_depth_m", "storm_map_largest_depth_m"]].dropna().corr().iloc[0, 1]}), include_groups=False)
    oi = np.nanmax(np.where(stormI[:, None], np.maximum(z["observed_to_marsh_ida"][:, ok], 0), np.nan), 0)
    lines += ["", f"sites with land cells of the map next to them: {int(incov.sum())} of {S}; sites whose cells were taken out as behind a levee: {int(flagged.sum())}, "
              f"of them with 0.5 m or more observed on the marsh in Ida: {int((flagged & (oi >= 0.5)).sum())} (these are wrongly taken out)",
              "", "check at the sites, Francine (depth on the marsh, observed = water level relative to the surveyed marsh surface):", sm_.round(3).to_string()]
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print(f"-> {out}, {time.time() - t00:.0f} s")


if __name__ == "__main__":
    main()
