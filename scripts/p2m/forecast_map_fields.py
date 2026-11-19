"""Flood map, step 7: the map itself from forecasts - peak flood depth of every cell over the days around a landfall,
once from the observed water levels at the control points and once from the forecasts issued 1, 3 and 6 hours before.

No numerical model of this storm is used, so nothing here says whether the map is right; the comparison with observations is
forecast_map_check.py. This shows how far the map from forecasts departs from the map made once the water levels are known.
Land = cells that stay dry in the run without the hurricane (as mapping_eval_summary.py), east of --west-limit.
Input : --inputs inputs.npz of forecast_map_check.py, --fit DIR of mapping_fit.py (--sums-dir if the sums are elsewhere), --ida DIR
Output: --out DIR: peak_coarse.npz (every --step x --step cells: largest peak depth per lead, share of land and water),
        areas.csv (flooded land per depth and lead, and the overlap with the map from observed levels)
Usage : python forecast_map_fields.py --inputs FILE --fit DIR --sums-dir DIR --ida DIR --out DIR
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import RUNS, grid, training  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--sums-dir"); ap.add_argument("--ida", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--train-runs", nargs="+"); ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--leads", type=int, nargs="+", default=[0, 1, 3, 6])
    ap.add_argument("--west-limit", type=float, default=-92.5); ap.add_argument("--step", type=int, default=4)
    a = ap.parse_args()
    fit, out = Path(a.fit), Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "areas.csv").exists(), f"{out} has results already"
    sd = Path(a.sums_dir) if a.sums_dir else fit
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; N = h.size
    _, name = training(a); B = np.load(fit / f"coef_{name}.npy"); m = np.load(fit / f"fitmeta_{name}.npz"); xm, ym = m["xm"], m["ym"]
    add = np.where(roms, h, 0).astype(np.float32).ravel()
    z = np.load(a.inputs); storm = z["storm"]; print(f"{int(storm.sum())} hours around the landfall: {z['times'][storm][0]} .. {z['times'][storm][-1]}")
    pk = {}
    for L in a.leads:
        t0 = time.time(); X = (z[f"lead{L}"][storm] - xm[None, :]).astype(np.float32); p = np.zeros(N, np.float32)
        for k in range(0, len(X), 24):
            p = np.maximum(p, np.maximum(X[k:k + 24] @ B + ym[None, :] + add[None, :], 0).max(0))
        pk[L] = p.reshape(NY, NX); print(f"lead {L}: {time.time() - t0:.0f} s", flush=True)
    dry = np.load(sd / "sums_Exp6_absolute_base.npz")["dmax"].reshape(NY, NX) <= 0.1
    lon2 = lon if lon.ndim == 2 else np.broadcast_to(lon[None, :], (NY, NX)); east = lon2 >= a.west_limit
    water = np.min([np.load(sd / f"sums_{r}.npz")["dmin"] for r in RUNS], 0).reshape(NY, NX) > 0.1          # water in every hour of every run
    land = dry & east; rows = []
    for thr in (0.1, 0.3, 0.5, 1.0, 2.0):
        ref = land & (pk[a.leads[0]] > thr)
        for L in a.leads:
            f = land & (pk[L] > thr); hit = int((f & ref).sum()); un = int((f | ref).sum()); e = (pk[L] - pk[a.leads[0]])[f | ref]
            rows.append({"depth_above_m": thr, "lead_h": L, "flooded_land_km2": f.sum() / 100, "also_in_map_from_observed_levels_km2": hit / 100, "only_in_this_map_km2": (int(f.sum()) - hit) / 100,
                         "only_in_map_from_observed_levels_km2": (int(ref.sum()) - hit) / 100, "overlap_csi": hit / un if un else np.nan,
                         "peak_depth_rms_difference_m": float(np.sqrt((e ** 2).mean())) if len(e) else np.nan, "peak_depth_mean_difference_m": float(e.mean()) if len(e) else np.nan})
    t = pd.DataFrame(rows); t.to_csv(out / "areas.csv", index=False); pd.set_option("display.width", 220); print(t.round(3).to_string(index=False))
    s = a.step; ny, nx = NY // s, NX // s; blk = lambda f, fn: fn(fn(f[:ny * s, :nx * s].reshape(ny, s, nx, s), 3), 1)
    lat1 = lat if lat.ndim == 1 else lat[:, 0]; lon1 = lon if lon.ndim == 1 else lon[0]
    o = {"lat": lat1[:ny * s].reshape(ny, s).mean(1), "lon": lon1[:nx * s].reshape(nx, s).mean(1), "land_frac": blk(dry.astype(np.float32), np.mean), "water_frac": blk(water.astype(np.float32), np.mean)}
    for L in a.leads:
        o[f"peak_lead{L}"] = blk(np.where(dry, pk[L], 0), np.max)
    np.savez_compressed(out / "peak_coarse.npz", **o); print("->", out)


if __name__ == "__main__":
    main()
