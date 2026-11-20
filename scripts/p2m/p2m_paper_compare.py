"""Flood map: two fits of the paper's mapping model (p2m_paper.py) compared on the cells where both have a Type 2 model.

The fits differ in the training runs, so they give a model to different cells; the scores p2m_paper.py writes are over each
fit's own cells. Here the peak depth of the storm is compared on the common Type 2 cells only, for every tag both were applied to.
Input : --fits DIR DIR (model.npz), --applies DIR DIR (peak_<tag>.npz with peak and, where there is one, peak_truth), --names NAME NAME
Output: --out CSV: one row per tag and fit (cells, RMSE of the peak, mean peak, flooded areas and overlap above 0.3 / 1 / 2 m, cells above 5 m)
Usage : python p2m_paper_compare.py --fits A B --applies A B --names "hindcast only" "eleven other runs" --tags ida_hindcast_inputs ida_observed_inputs --out FILE
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--fits", nargs=2, required=True); ap.add_argument("--applies", nargs=2, required=True); ap.add_argument("--names", nargs=2, required=True)
    ap.add_argument("--tags", nargs="+", required=True); ap.add_argument("--out", required=True); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    m = [np.load(Path(f) / "model.npz") for f in a.fits]; assert np.array_equal(m[0]["jj"], m[1]["jj"]) and np.array_equal(m[0]["ii"], m[1]["ii"])
    t2 = [(x["type"] == 2) & (x["model"] > 0) for x in m]; both = t2[0] & t2[1]; rows = []
    print(f"Type 2 cells with a model: {a.names[0]} {t2[0].sum() / 100:.0f} km2, {a.names[1]} {t2[1].sum() / 100:.0f} km2, both {both.sum() / 100:.0f} km2")
    for tag in a.tags:
        for name, ad in zip(a.names, a.applies):
            z = np.load(Path(ad) / f"peak_{tag}.npz"); p = np.nan_to_num(z["peak"][both].astype(np.float64), nan=0.0); r = {"inputs": tag, "training": name, "cells": int(both.sum()), "cells_above_5m": int((p > 5).sum()), "peak_mean_p2m_m": p.mean()}
            if "peak_truth" in z.files:
                t = np.nan_to_num(z["peak_truth"][both].astype(np.float64), nan=0.0); r.update({"peak_mean_numerical_model_m": t.mean(), "peak_rmse_m": float(np.sqrt(((p - t) ** 2).mean())), "peak_within_0.3m_share": float((np.abs(p - t) <= 0.3).mean())})
                for th in (0.3, 1.0, 2.0):
                    r[f"flooded_above_{th}m_numerical_model_km2"] = (t > th).sum() / 100; r[f"flooded_above_{th}m_p2m_km2"] = (p > th).sum() / 100; r[f"csi_{th}m"] = ((p > th) & (t > th)).sum() / max(((p > th) | (t > th)).sum(), 1)
            else:
                for th in (0.3, 1.0, 2.0):
                    r[f"flooded_above_{th}m_p2m_km2"] = (p > th).sum() / 100
            rows.append(r)
    d = pd.DataFrame(rows); d.to_csv(a.out, index=False); print(d.round(3).to_string()); print("->", a.out)


if __name__ == "__main__":
    main()
