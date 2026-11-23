"""Flood map, why the map is too dry: is the numerical model itself too dry on the marsh?

The depth of a run of the numerical model at the land cells around every marsh gauge (CRMS), hour by hour - the same cells,
taken the same way (median), as the mapping model is scored on - to set beside the observed depth on the marsh.
Input : --ida DIR, --run RUN, --model model.npz of p2m_paper.py (which cells have a model), --sites CSV station, lat, lon, --land eval_<run>.npz
Output: --out NPZ: station, depth_cells_with_a_model [T, S], depth_all_land_cells [T, S], n_cells
Usage : python p2m_paper_hindcast_at_sites.py --ida DIR --run Exp1_fully_coupled --model FILE --sites FILE --land FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
from p2m_paper import load_depth  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("ida", "run", "model", "sites", "land", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--radius", type=int, default=3); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    m = np.load(a.model); jj, ii = m["jj"], m["ii"]; has = m["model"] > 0; h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; land = np.load(a.land)["dmax_no_storm"] <= 0.1
    idx = np.full((NY, NX), -1, np.int64); idx[jj, ii] = np.arange(len(jj)); sites = pd.read_csv(a.sites); R = a.radius; cj, ci, owner, withm = [], [], [], []
    for k, s in enumerate(sites.itertuples()):
        j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin()); js, is_ = np.meshgrid(np.arange(max(j - R, 0), min(j + R + 1, NY)), np.arange(max(i - R, 0), min(i + R + 1, NX)), indexing="ij")
        near = (np.hypot(js - j, is_ - i) <= R + 0.5) & land[js, is_]; q = idx[js[near], is_[near]]
        cj += list(js[near]); ci += list(is_[near]); owner += [k] * int(near.sum()); withm += list((q >= 0) & has[np.maximum(q, 0)])
    cj, ci, owner, withm = np.array(cj), np.array(ci), np.array(owner), np.array(withm, bool); Y = load_depth(Path(a.ida), a.run, h, roms, cj, ci); T = Y.shape[0]
    A = np.full((T, len(sites)), np.nan, np.float32); B = np.full((T, len(sites)), np.nan, np.float32); n = np.zeros((len(sites), 2), int)
    for k in range(len(sites)):
        w = owner == k; v = w & withm; n[k] = [int(w.sum()), int(v.sum())]
        if w.any():
            B[:, k] = np.median(Y[:, w], 1)
        if v.any():
            A[:, k] = np.median(Y[:, v], 1)
    np.savez_compressed(a.out, station=sites.station.to_numpy(str), depth_cells_with_a_model=A, depth_all_land_cells=B, n_cells=n); print("->", a.out)


if __name__ == "__main__":
    main()
