"""Flood map, the two mapping models side by side on one grid: each where it has something to stand on.

Every land cell (dry throughout the run without a hurricane) east of --west-limit gets one of four answers:
  from observations     within --radius km of a marsh gauge and outside the leveed areas: the level fitted on observations at the
                        nearest sites minus the ground of the grid (marsh_map.py)
  from the Ida runs     elsewhere, if the cell is flooded in a run WITHOUT rainfall (Exp3_no_precipitation or Exp7_wind_base): the
                        water comes from the coast there, which the gauges can see; mapping model of mapping_fit.py.
                        One storm, not checked against observations.
  no map: rainfall      flooded in the Ida runs only when it rains: the gauges do not see the rain (the map would repeat Ida)
  no map: never wet     dry in all twelve runs: the mapping model fitted on them cannot say anything here
Where both models exist (the first class), they are compared, as a check of the seam.
Input : --levels levels.npz of marsh_obs_variants.py, --ida DIR, --eval eval_<run>.npz (hindcast), --fit DIR of mapping_fit.py with the sums of all runs,
        --inputs inputs.npz of forecast_map_check.py, --leveed leveed_area_mask.npz
Output: --out DIR: combined_coarse.npz, areas.csv, summary.txt
Usage : python combined_map.py --levels FILE --ida DIR --eval FILE --fit DIR --inputs FILE --leveed FILE --out DIR
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
from marsh_obs_fit import FR_STORM  # noqa: E402

KX, KY = np.cos(np.deg2rad(29.7)) * 111.2, 111.2
CLASSES = ["from observations", "from the Ida runs", "no map: flooded in the Ida runs only with rainfall", "no map: dry in all Ida runs"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", required=True); ap.add_argument("--ida", required=True); ap.add_argument("--eval", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--inputs", required=True); ap.add_argument("--leveed", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--train-runs", nargs="+"); ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--no-rain-runs", nargs="+", default=["Exp3_no_precipitation", "Exp7_wind_base"])
    ap.add_argument("--radius", type=float, default=10.0); ap.add_argument("--neighbours", type=int, default=4); ap.add_argument("--west-limit", type=float, default=-92.5); ap.add_argument("--step", type=int, default=4); ap.add_argument("--chunk", type=int, default=40000)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "summary.txt").exists(), f"{out} has results already"
    t00 = time.time(); fit = Path(a.fit); h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; ground = -h
    ev = np.load(a.eval); land = ev["dmax_no_storm"] <= 0.1; water = ev["dmin_all_runs"] > 0.1; ever = ev["dmax_all_runs"] > 0.1
    coast = np.max([np.load(fit / f"sums_{r}.npz")["dmax"] for r in a.no_rain_runs], 0).reshape(NY, NX) > 0.1          # flooded without rainfall
    lm = np.load(a.leveed)["mask"]
    z = np.load(a.levels, allow_pickle=False); ok = z["fitted"] & np.isfinite(z["level_francine_inputs_observed"]).all(0); slat, slon = z["lat"][ok], z["lon"][ok]
    tF = pd.DatetimeIndex(z["times_francine"]); storm = np.asarray((tF >= FR_STORM[0]) & (tF < FR_STORM[1])); L = {"inputs observed": z["level_francine_inputs_observed"][:, ok].astype(np.float32), "inputs forecast 6 h before": z["level_francine_inputs_forecast_6h"][:, ok].astype(np.float32)}

    jj, ii = np.where(land & (lon[None, :] >= a.west_limit)); N = len(jj); g = ground[jj, ii].astype(np.float32)
    nb = np.zeros((N, a.neighbours), np.int32); dn = np.full((N, a.neighbours), 1e9, np.float32); sx, sy = (slon * KX).astype(np.float32), (slat * KY).astype(np.float32)
    band = np.where((lat[jj] >= slat.min() - 0.15) & (lat[jj] <= slat.max() + 0.15))[0]
    for c in range(0, len(band), a.chunk):
        q = band[c:c + a.chunk]; d2 = ((lon[ii[q]] * KX).astype(np.float32)[:, None] - sx[None, :]) ** 2 + ((lat[jj[q]] * KY).astype(np.float32)[:, None] - sy[None, :]) ** 2
        k = np.argpartition(d2, a.neighbours - 1, 1)[:, :a.neighbours]; nb[q] = k; dn[q] = np.sqrt(np.take_along_axis(d2, k, 1))
    cls = np.full(N, 3, np.int8); cls[ever[jj, ii]] = 2; cls[coast[jj, ii]] = 1; cls[(dn.min(1) <= a.radius) & ~lm[jj, ii]] = 0
    w = 1.0 / np.maximum(dn, 0.1) ** 2; w /= w.sum(1, keepdims=True); A = np.where(cls == 0)[0]

    _, name = training(a); B = np.load(fit / f"coef_{name}.npy"); m_ = np.load(fit / f"fitmeta_{name}.npz"); xm, ym = m_["xm"], m_["ym"]; zi = np.load(a.inputs); idx = jj * NX + ii
    add = np.where(roms, h, 0).astype(np.float32).ravel()[idx]; Bc = B[:, idx]; del B; ymc = ym[idx]
    obs, mod = {}, {}
    for lab, key in (("inputs observed", "lead0"), ("inputs forecast 6 h before", "lead6")):
        p = np.zeros(N, np.float32); Lh = L[lab][storm]
        for c in range(0, len(A), a.chunk):
            q = A[c:c + a.chunk]; p[q] = np.maximum(np.einsum("tnk,nk->tn", Lh[:, nb[q]], w[q]).max(0) - g[q], 0)
        obs[lab] = p
        X = (zi[key][zi["storm"]] - xm[None, :]).astype(np.float32); p = np.zeros(N, np.float32)
        for c in range(0, N, 400000):
            for k in range(0, len(X), 24):
                p[c:c + 400000] = np.maximum(p[c:c + 400000], np.maximum(X[k:k + 24] @ Bc[:, c:c + 400000] + ymc[c:c + 400000][None, :] + add[c:c + 400000][None, :], 0).max(0))
        mod[lab] = p
    comb = {lab: np.where(cls == 0, obs[lab], np.where(cls == 1, mod[lab], np.nan)).astype(np.float32) for lab in obs}
    print(f"fields done, {time.time() - t00:.0f} s", flush=True)

    rows = []; lev = lm[jj, ii]
    for k, nm in enumerate(CLASSES):
        m = cls == k; r = {"class": nm, "land (km2)": m.sum() / 100, "of it in a leveed area (km2)": (m & lev).sum() / 100}
        if k < 2:
            for lab in comb:
                for t in (0.3, 1.0):
                    r[f"above {t} m, {lab} (km2)"] = float((comb[lab][m] > t).sum()) / 100
        rows.append(r)
    ar = pd.DataFrame(rows); ar.to_csv(out / "areas.csv", index=False); pd.set_option("display.width", 250)
    lines = [f"land east of {-a.west_limit} W: {N / 100:.0f} km2; runs without rainfall: {', '.join(a.no_rain_runs)}", ar.round(0).to_string(index=False)]
    lonc = lon[ii]; both = (cls == 0) & coast[jj, ii]                                                    # the seam: cells where both models have something to say
    for lab in obs:
        for nm, m in (("all", both), ("east of 90.8 W", both & (lonc >= -90.8)), ("west of 90.8 W", both & (lonc < -90.8))):
            o, p = obs[lab][m], mod[lab][m]; f = (o > 0.1) | (p > 0.1)
            lines.append(f"both models, {lab}, {nm}: {int(m.sum()) / 100:.0f} km2; largest depth from observations {o[f].mean():.2f} m, from the Ida runs {p[f].mean():.2f} m (mean over cells either floods); "
                         f"difference RMS {np.sqrt(((o - p)[f] ** 2).mean()):.2f} m; correlation {np.corrcoef(o[f], p[f])[0, 1]:.2f}; above 0.3 m: {int((o > 0.3).sum()) / 100:.0f} against {int((p > 0.3).sum()) / 100:.0f} km2")
    # the step across the border between the two sources: neighbouring cells, one of each class
    G = np.full((NY, NX), np.nan, np.float32); G[jj, ii] = comb["inputs forecast 6 h before"]; C = np.full((NY, NX), -1, np.int8); C[jj, ii] = cls
    st = [];
    for dj, di in ((0, 1), (1, 0)):
        a1, a2 = C[:NY - dj, :NX - di], C[dj:, di:]; m = ((a1 == 0) & (a2 == 1)) | ((a1 == 1) & (a2 == 0)); st.append((G[:NY - dj, :NX - di][m] - G[dj:, di:][m]) * np.where(a1[m] == 0, 1, -1))
    st = np.concatenate(st); lines.append(f"border between the two sources: {len(st)} pairs of neighbouring cells; depth from observations minus depth from the Ida runs across the border: mean {st.mean():+.2f} m, median absolute {np.median(np.abs(st)):.2f} m, "
                                         f"more than 0.5 m apart at {100 * (np.abs(st) > 0.5).mean():.0f}% of the pairs")
    s_ = a.step; ny, nx = NY // s_, NX // s_; blk = lambda x, fn: fn(fn(x[:ny * s_, :nx * s_].reshape(ny, s_, nx, s_), 3), 1)
    def to_grid(v, fillv=0.0):
        o = np.full((NY, NX), fillv, np.float32); o[jj, ii] = v; return o
    o = {"lat": lat[:ny * s_].reshape(ny, s_).mean(1), "lon": lon[:nx * s_].reshape(nx, s_).mean(1), "land_frac": blk(land.astype(np.float32), np.mean), "water_frac": blk(water.astype(np.float32), np.mean),
         "site_lat": slat, "site_lon": slon, **{f"class_frac | {nm}": blk(to_grid((cls == k).astype(np.float32)), np.mean) for k, nm in enumerate(CLASSES)}}
    for lab in comb:
        o["peak | " + lab] = blk(to_grid(np.nan_to_num(comb[lab], nan=0.0)), np.max)
    np.savez_compressed(out / "combined_coarse.npz", **o)
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print(f"-> {out}, {time.time() - t00:.0f} s")


if __name__ == "__main__":
    main()
