"""Flood map, step 3: numbers and coarse fields of the evaluation of the mapping model on the left-out run.

Reads eval_<run>.npz of mapping_fit.py and writes, for the trusted part of the grid (east of --west-limit):
  metrics_<run>.csv  per class of cell (water in normal conditions / land flooded in the run / land never wet) and input
                     (exact control-point series of the run / the same with noise / the observed series): cells, RMSE over all hours, peak depth
                     of the model and of the mapping, RMSE and correlation of the peak, flooded area above several depths
  coarse_<run>.npz   the fields on every --step-th cell block for drawing (peak: block maximum, RMSE: block mean)
Classes: 'water' = depth above 0.1 m in every hour of every run; 'land' = dry (below 0.1 m) throughout the run without the
hurricane (Exp6); land is 'flooded' if the left-out run reaches 0.1 m there.
Usage : python mapping_eval_summary.py --work DIR --run Exp1_fully_coupled [--west-limit -92.5 --step 4]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--work", required=True); ap.add_argument("--run", default="Exp1_fully_coupled")
    ap.add_argument("--west-limit", type=float, default=-92.5); ap.add_argument("--step", type=int, default=4)
    a = ap.parse_args(); w = Path(a.work)
    z = np.load(w / f"eval_{a.run}.npz"); lat, lon = z["lat"], z["lon"]; T = int(z["hours"])
    pt = z["peak_true"]; east = np.broadcast_to(lon[None, :] >= a.west_limit, pt.shape)
    water = z["dmin_all_runs"] > 0.1; land = z["dmax_no_storm"] <= 0.1
    cls = {"water in normal conditions": water & east, "land, flooded in the run (peak above 0.1 m)": land & (pt > 0.1) & east, "land, dry in the run": land & (pt <= 0.1) & east,
           "all cells east of the limit": east}
    rows = []
    inputs = [k[5:] for k in z.files if k.startswith("rmse_")]
    for inp in inputs:
        rm, pp = z[f"rmse_{inp}"], z[f"peak_{inp}"]
        for name, m in cls.items():
            n = int(m.sum())
            if n == 0:
                continue
            r = {"input": inp, "cells": name, "n_cells": n, "area_km2": round(n * 0.01, 1), "rmse_all_hours_m": float(np.sqrt((rm[m].astype(np.float64) ** 2).mean())),
                 "peak_model_mean_m": float(pt[m].mean()), "peak_mapping_mean_m": float(pp[m].mean()), "peak_rmse_m": float(np.sqrt(((pp[m] - pt[m]).astype(np.float64) ** 2).mean())),
                 "peak_bias_m": float((pp[m] - pt[m]).mean()), "peak_corr": float(np.corrcoef(pt[m], pp[m])[0, 1]) if pt[m].std() > 0 else np.nan}
            rows.append(r)
        ml = land & east
        for thr in (0.1, 0.3, 0.5, 1.0, 2.0):
            a_t, a_p = (pt > thr) & ml, (pp > thr) & ml; hit = int((a_t & a_p).sum())
            rows.append({"input": inp, "cells": f"land with peak depth above {thr} m", "n_cells": int(a_t.sum()), "area_km2": round(int(a_t.sum()) * 0.01, 1), "area_mapping_km2": round(int(a_p.sum()) * 0.01, 1),
                         "hit_km2": round(hit * 0.01, 1), "missed_km2": round((int(a_t.sum()) - hit) * 0.01, 1), "false_km2": round((int(a_p.sum()) - hit) * 0.01, 1),
                         "csi": hit / max(int((a_t | a_p).sum()), 1)})
    m = pd.DataFrame(rows); m.to_csv(w / f"metrics_{a.run}.csv", index=False)
    pd.set_option("display.width", 250); print(m.round(3).to_string(index=False))
    s = a.step; ny, nx = (pt.shape[0] // s) * s, (pt.shape[1] // s) * s
    blk = lambda x, f: f(f(x[:ny, :nx].reshape(ny // s, s, nx // s, s), 3), 1)
    out = {"lat": lat[:ny].reshape(-1, s).mean(1), "lon": lon[:nx].reshape(-1, s).mean(1), "step": s, "hours": T,
           "water_frac": blk(water.astype(np.float32), np.mean), "land_frac": blk(land.astype(np.float32), np.mean)}
    for k in ["peak_true"] + [f"peak_{i}" for i in inputs]:
        out[k] = blk(np.where(land, z[k], 0).astype(np.float32), np.max)      # flood depth on land only
    for k in [f"rmse_{i}" for i in inputs]:
        out[k] = blk(z[k], np.mean)
    np.savez_compressed(w / f"coarse_{a.run}.npz", **out)
    print("->", w / f"coarse_{a.run}.npz")


if __name__ == "__main__":
    main()
