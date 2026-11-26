"""Flood map: two fits of the mapping model (p2m_paper.py) rebuilt on a run neither has seen, scored on the same cells.

The fits differ in their training runs and therefore give a model to different cells; the scores p2m_paper.py writes are over
each fit's own cells and cannot be compared directly. Here every hour of the run is rebuilt by both fits from the control-point
series of the run itself and scored, hour by hour, on
    common Type 2 cells   dry in normal conditions, flooded at times, with a model in both fits
    cells only the second fit has a model for (Type 2 there), scored for the second fit alone
Scores: NSE and RMSE of the depth over all hours and cells; mean of the largest depth; area flooded above a threshold in the
numerical model and in the rebuilt field, and their overlap (CSI).
Input : --ida DIR, --run RUN, --inputs NPZ:key (control-point series of the run), --fits FILE FILE (model.npz), --names NAME NAME
Output: --out CSV
Usage : python p2m_paper_common_cells.py --ida DIR --run RUN --inputs FILE:X --fits A/model.npz B/model.npz --names "..." "..." --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
try:
    from p2m_paper_v3 import load_depth, predict  # noqa: E402  (name of the file on the server)
except ImportError:
    from p2m_paper import load_depth, predict  # noqa: E402

THR = (0.1, 0.3, 0.5, 1.0)


def score(p, y, wet) -> dict:
    y = np.where(y > wet, y, 0); d = (p - y).astype(np.float64); n = d.size; var = (y.astype(np.float64) ** 2).sum() - y.sum(dtype=np.float64) ** 2 / n; pk, pt = np.nanmax(p, 0), y.max(0)
    r = {"cells": p.shape[1], "area_km2": p.shape[1] / 100, "hours": p.shape[0], "nse": 1 - (d ** 2).sum() / var, "rmse_m": float(np.sqrt((d ** 2).mean())), "mean_error_m": float(d.mean()),
         "largest_depth_mean_numerical_model_m": float(pt.mean()), "largest_depth_mean_mapping_m": float(pk.mean()), "rmse_of_largest_depth_m": float(np.sqrt(((pk - pt) ** 2).mean()))}
    for t in THR:
        A, B = pt > t, pk > t; r[f"flooded_above_{t}m_numerical_model_km2"] = A.sum() / 100; r[f"flooded_above_{t}m_mapping_km2"] = B.sum() / 100; r[f"csi_{t}m"] = (A & B).sum() / max((A | B).sum(), 1)
    return r


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--ida", required=True); ap.add_argument("--run", required=True); ap.add_argument("--inputs", required=True); ap.add_argument("--fits", nargs=2, required=True); ap.add_argument("--names", nargs=2, required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--chunk", type=int, default=200000); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    M = [dict(np.load(f, allow_pickle=True)) for f in a.fits]; assert np.array_equal(M[0]["jj"], M[1]["jj"]) and np.array_equal(M[0]["ii"], M[1]["ii"]) and np.array_equal(M[0]["used"], M[1]["used"]); wet = float(M[0]["wet"])
    f, _, key = a.inputs.partition(":"); X = np.asarray(np.load(f)[key], np.float64)[:, M[0]["used"]]; h, roms, _, _ = grid(Path(a.ida)); t2 = [(m["type"] == 2) & (m["model"] > 0) for m in M]
    groups = {"common Type 2 cells": np.where(t2[0] & t2[1])[0], f"Type 2 cells with a model only in: {a.names[1]}": np.where(t2[1] & ~(M[0]["model"] > 0))[0]}; rows = []
    for g, sel in groups.items():
        if len(sel) == 0:
            continue
        y = load_depth(Path(a.ida), a.run, h, roms, M[0]["jj"][sel], M[0]["ii"][sel]); which = (0, 1) if g.startswith("common") else (1,)
        for k in which:
            p = np.concatenate([predict(M[k], X, sel[s0:s0 + a.chunk]) for s0 in range(0, len(sel), a.chunk)], 1); rows.append({"run": a.run, "cells_scored": g, "trained_on": a.names[k], **score(p, y, wet)})
    d = pd.DataFrame(rows); d.to_csv(a.out, index=False); pd.set_option("display.width", 250); print(d.round(3).T.to_string())


if __name__ == "__main__":
    main()
