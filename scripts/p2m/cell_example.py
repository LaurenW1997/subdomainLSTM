"""Flood map, one cell as an example of the mapping model: its formula and what it gives during Hurricane Ida.

Picks a land cell near a given place that is dry in normal conditions and flooded in the hindcast, and writes
  the control points with the largest weight in the formula of this cell (coefficient, and coefficient times the spread
  of the control point in the training runs, which is how much the control point moves the cell),
  the hourly depth of the hindcast at the cell, of the mapping model driven by the hindcast's own control-point series,
  and of the mapping model driven by the observed water levels.
Input : --ida DIR (grid), --fit DIR (coef, fitmeta, controls_used.csv, eval npz), --sums-dir DIR (sums_<run>.npz, xref),
        --observed x_observed.npy, --cache hindcast float32 [T, lat, lon], --near LAT LON
Output: --out JSON
Usage : python cell_example.py --ida DIR --fit DIR --sums-dir DIR --observed FILE --cache FILE --near 30.07 -90.48 --out FILE
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import RUNS, grid  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--sums-dir", required=True); ap.add_argument("--observed", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--near", nargs=2, type=float, required=True); ap.add_argument("--radius", type=int, default=60); ap.add_argument("--peak", nargs=2, type=float, default=[0.6, 1.5])
    ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--out", required=True)
    a = ap.parse_args(); fit, sd = Path(a.fit), Path(a.sums_dir)
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape
    z = np.load(fit / f"eval_{a.holdout}.npz"); pk, dry = z["peak_true"], z["dmax_no_storm"] <= 0.1
    j0, i0 = int(np.abs(lat - a.near[0]).argmin()), int(np.abs(lon - a.near[1]).argmin())
    sl = (slice(max(0, j0 - a.radius), min(NY, j0 + a.radius + 1)), slice(max(0, i0 - a.radius), min(NX, i0 + a.radius + 1)))
    ok = dry[sl] & ~roms[sl] & (pk[sl] >= a.peak[0]) & (pk[sl] <= a.peak[1])
    assert ok.any(), "no land cell with such a peak near this place"
    jj, ii = np.where(ok); k = int(np.hypot(jj - (j0 - sl[0].start), ii - (i0 - sl[1].start)).argmin()); j, i = int(jj[k] + sl[0].start), int(ii[k] + sl[1].start); idx = j * NX + i
    c = pd.read_csv(fit / "controls_used.csv", dtype={"station_id": str}); used = c.used.to_numpy(bool) if "used" in c.columns else np.ones(len(c), bool)
    B = np.load(fit / f"coef_without_{a.holdout}.npy", mmap_mode="r"); b = np.asarray(B[:, idx], np.float64)
    m = np.load(fit / f"fitmeta_without_{a.holdout}.npz"); xm, ym = m["xm"], float(m["ym"][idx])
    n = 0; Sx = np.zeros(len(c)); Sxx = np.zeros(len(c))
    for r in RUNS:
        if r != a.holdout:
            s = np.load(sd / f"sums_{r}.npz"); n += int(s["n"]); Sx += s["Sx"]; Sxx += np.diag(s["Sxx"])
    sdx = np.sqrt(np.maximum(Sxx / n - (Sx / n) ** 2, 0))                  # spread of every control point in the training runs
    X = np.load(sd / f"sums_{a.holdout}.npz")["X"]; Xo = np.load(a.observed)
    wl = np.load(a.cache, mmap_mode="r"); truth = pd.Series(np.asarray(wl[:, j, i], np.float64)).ffill().fillna(0.0).to_numpy()
    f = lambda x: np.maximum((x - xm[None, :]) @ b + ym, 0)
    order = np.argsort(-np.abs(b * sdx)); top = [k for k in order if used[k]][:6]
    out = {"lat": float(lat[j]), "lon": float(lon[i]), "j": j, "i": i, "ground_m": float(-h[j, i]), "constant_m": ym, "n_controls": int(used.sum()),
           "top": [{"station_id": c.station_id[k], "name": c.name[k], "lat": float(c.lat[k]), "lon": float(c.lon[k]), "coefficient": float(b[k]), "spread_m": float(sdx[k]), "moves_cell_m": float(b[k] * sdx[k])} for k in top],
           "share_of_top": float(np.abs(b * sdx)[top].sum() / np.abs(b * sdx)[used].sum()),
           "hindcast_depth_m": np.round(np.maximum(truth, 0), 4).tolist(), "mapping_model_inputs_m": np.round(f(X), 4).tolist(), "mapping_observed_inputs_m": np.round(f(Xo), 4).tolist()}
    Path(a.out).write_text(json.dumps(out), encoding="utf-8")
    print(f"cell j={j} i={i} at {out['lat']:.4f} N {out['lon']:.4f} E, ground {out['ground_m']:.2f} m; peak depth: hindcast {max(out['hindcast_depth_m']):.2f}, mapping {max(out['mapping_model_inputs_m']):.2f}, "
          f"mapping from observations {max(out['mapping_observed_inputs_m']):.2f} m; the six largest of {out['n_controls']} control points carry {100 * out['share_of_top']:.0f}% of the weight")
    for t in out["top"]:
        print(f"   {t['coefficient']:+.2f} x {t['name'][:45]:45s} spread {t['spread_m']:.2f} m -> {t['moves_cell_m']:+.2f} m")


if __name__ == "__main__":
    main()
