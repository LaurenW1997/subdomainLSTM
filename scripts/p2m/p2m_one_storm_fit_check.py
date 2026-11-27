"""Flood map: can one set of coefficients hold two storms? Trainings set against each other at the cells around the marsh gauges.

Every mapping model (--fits) is fed the control-point water levels of a run of the numerical model (--runs) and compared with the
depth of that run itself, on the land cells around the marsh gauges that have a model in every fit. If a model fitted to one storm
alone rebuilds that storm where the joint training does not, the joint training fails for lack of weight or because the two storms
need different coefficients - not because the control points say too little about that storm.
Scores, for all cells and west and east of 90.8 W: hour by hour over the cells (RMSE, NSE), largest depth of every cell, and
largest depth at every gauge (median of its cells, as the flood map is scored against the gauges).
Input : --ida DIR, --sums DIR (sums_<run>.npz), --fits model.npz ... --names NAME ..., --runs RUN ..., --sites CSV, --land eval_<run>.npz,
        --exclude NPZ:key (cells left out, e.g. those whose depth differs from the Ida grid in one of the runs)
Output: --out CSV
Usage : python p2m_one_storm_fit_check.py --ida DIR --sums DIR --fits A.npz B.npz --names "A" "B" --runs RUN1 RUN2 --sites FILE --land FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
from p2m_area_around_sites import cells_around  # noqa: E402
try:
    from p2m_paper_v3 import load_depth, predict  # noqa: E402  (name of the file on the server)
except ImportError:
    from p2m_paper import load_depth, predict  # noqa: E402

SPLIT = -90.8


def corr(x, y) -> float:
    return float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 and np.std(x) > 0 and np.std(y) > 0 else np.nan


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("ida", "sums", "sites", "land", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--fits", nargs="+", required=True); ap.add_argument("--names", nargs="+", required=True); ap.add_argument("--runs", nargs="+", required=True); ap.add_argument("--exclude"); ap.add_argument("--radius", type=int, default=3)
    a = ap.parse_args(); assert len(a.fits) == len(a.names) and not Path(a.out).exists(), "one name per fit; the output must not exist"
    ida = Path(a.ida); h, roms, lat, lon = grid(ida); NY, NX = h.shape; land = np.load(a.land)["dmax_no_storm"] <= 0.1; sites = pd.read_csv(a.sites); cj, ci, owner = cells_around(sites, lat, lon, land, a.radius)
    M = []; ok = np.ones(len(cj), bool); sels = []
    for f in a.fits:
        z = np.load(f); m = {k: z[k] for k in z.files}; idx = np.full((NY, NX), -1, np.int64); idx[m["jj"], m["ii"]] = np.arange(len(m["jj"])); q = idx[cj, ci]
        has = (q >= 0) & (m["model"][np.maximum(q, 0)] > 0); print(f"{f}: {int(has.sum())} of {len(cj)} land cells around the gauges have a model"); ok &= has; M.append(m); sels.append(q)
    if a.exclude:
        f, _, key = a.exclude.partition(":"); ex = np.load(f)[key][cj, ci]; print(f"left out by --exclude: {int((ok & ex).sum())} cells"); ok &= ~ex
    cj, ci, owner = cj[ok], ci[ok], owner[ok]; sels = [q[ok] for q in sels]; west = lon[ci] < SPLIT; gid = np.unique(owner); gw = sites.lon.to_numpy(float)[gid] < SPLIT
    print(f"{len(cj)} cells with a model in every fit, around {len(gid)} gauges ({int(gw.sum())} west, {int((~gw).sum())} east of 90.8 W)"); rows = []
    for run in a.runs:
        X = np.asarray(np.load(Path(a.sums) / f"sums_{run}.npz")["X"], np.float64); truth = load_depth(ida, run, h, roms, cj, ci)
        for m, q, name in zip(M, sels, a.names):
            y = np.where(truth > float(m["wet"]), truth, 0).astype(np.float64); p = predict(m, X[:, m["used"]], q).astype(np.float64); cvr = np.nanmin(np.where(np.isnan(m["cv_rmse"][q]), np.inf, m["cv_rmse"][q]), 1) if "cv_rmse" in m else np.full(len(q), np.inf)
            gy = np.array([np.median(y[:, owner == g], 1).max() for g in gid]); gp = np.array([np.median(p[:, owner == g], 1).max() for g in gid])
            for nm, w, v in (("all", np.ones(len(cj), bool), np.ones(len(gid), bool)), ("west of 90.8W", west, gw), ("east of 90.8W", ~west, ~gw)):
                d = p[:, w] - y[:, w]; yy = y[:, w]; pk, pt = p[:, w].max(0), yy.max(0); c = cvr[w]; c = c[np.isfinite(c)]
                rows.append({"run_rebuilt": run, "training": name, "cells": nm, "n_cells": int(w.sum()), "n_gauges": int(v.sum()), "hours": len(X),
                             "hour_by_hour_rmse_m": float(np.sqrt((d ** 2).mean())), "hour_by_hour_nse": float(1 - (d ** 2).sum() / ((yy - yy.mean()) ** 2).sum()),
                             "cell_largest_depth_run_mean_m": float(pt.mean()), "cell_largest_depth_mapping_mean_m": float(pk.mean()), "cell_largest_depth_rmse_m": float(np.sqrt(((pk - pt) ** 2).mean())), "cell_largest_depth_correlation": corr(pt, pk),
                             "gauge_largest_depth_run_median_m": float(np.median(gy[v])), "gauge_largest_depth_mapping_median_m": float(np.median(gp[v])), "gauge_largest_depth_mean_error_m": float((gp[v] - gy[v]).mean()),
                             "gauge_largest_depth_rmse_m": float(np.sqrt(((gp[v] - gy[v]) ** 2).mean())), "gauge_largest_depth_correlation": corr(gy[v], gp[v]),
                             "cross_validation_rmse_of_the_training_median_m": float(np.median(c)) if len(c) else np.nan})
    t = pd.DataFrame(rows); t.to_csv(a.out, index=False); pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(t[["run_rebuilt", "training", "cells", "n_cells", "hour_by_hour_rmse_m", "hour_by_hour_nse", "cell_largest_depth_rmse_m", "cell_largest_depth_correlation", "gauge_largest_depth_rmse_m", "gauge_largest_depth_correlation"]].round(3).to_string()); print("->", a.out)


if __name__ == "__main__":
    main()
