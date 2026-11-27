"""Flood map, the level zero: the water level of a run of the numerical model at the marsh gauges (CRMS), not only the depth.

Around every site (cells within --radius, as the flood map is scored): the depth on the land cells, the water surface elevation
(depth + ground of the cell) on the land cells that are flooded, and the water surface elevation on the cells that are not land
(channels, ponds, open water) - the last is what a gauge standing in a channel beside the marsh measures also when the marsh is dry.
It separates two things the depth alone mixes: is the water of the model lower than observed, or is the ground of the grid different?
Input : --ida DIR, --run RUN, --sites CSV station, lat, lon, --land eval_<run>.npz (dmax_no_storm)
Output: --out NPZ: station, depth_land [T, S], level_land_flooded [T, S], share_land_flooded [T, S], level_water_cells [T, S],
        ground_land [S], ground_water_cells [S], n_cells [S, 2] (land, not land)
Usage : python p2m_run_level_at_sites.py --ida DIR --run Francine_landfall_10_days --sites FILE --land FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
try:
    from p2m_paper_v3 import load_depth  # noqa: E402  (name of the file on the server)
except ImportError:
    from p2m_paper import load_depth  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("ida", "run", "sites", "land", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--radius", type=int, default=3); ap.add_argument("--wet", type=float, default=0.05); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; land = np.load(a.land)["dmax_no_storm"] <= 0.1; sites = pd.read_csv(a.sites); R = a.radius; cj, ci, owner = [], [], []
    for k, s in enumerate(sites.itertuples()):
        j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin()); js, is_ = np.meshgrid(np.arange(max(j - R, 0), min(j + R + 1, NY)), np.arange(max(i - R, 0), min(i + R + 1, NX)), indexing="ij")
        near = np.hypot(js - j, is_ - i) <= R + 0.5; cj += list(js[near]); ci += list(is_[near]); owner += [k] * int(near.sum())
    cj, ci, owner = np.array(cj), np.array(ci), np.array(owner); isl = land[cj, ci]; Y = load_depth(Path(a.ida), a.run, h, roms, cj, ci); T = Y.shape[0]
    ground = (-h[cj, ci]).astype(np.float32); lev = np.where(Y > a.wet, Y + ground[None, :], np.nan); S = len(sites); nan = lambda: np.full((T, S), np.nan, np.float32)
    dl, ll, sl, lw = nan(), nan(), nan(), nan(); gl, gw = np.full(S, np.nan, np.float32), np.full(S, np.nan, np.float32); n = np.zeros((S, 2), int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for k in range(S):
            L = (owner == k) & isl; W = (owner == k) & ~isl; n[k] = [int(L.sum()), int(W.sum())]
            if L.any():
                dl[:, k] = np.median(Y[:, L], 1); ll[:, k] = np.nanmedian(lev[:, L], 1); sl[:, k] = (Y[:, L] > a.wet).mean(1); gl[k] = np.median(ground[L])
            if W.any():
                lw[:, k] = np.nanmedian(lev[:, W], 1); gw[k] = np.median(ground[W])
    np.savez_compressed(a.out, station=sites.station.to_numpy(str), depth_land=dl, level_land_flooded=ll, share_land_flooded=sl, level_water_cells=lw, ground_land=gl, ground_water_cells=gw, n_cells=n)
    print(f"{S} sites, {int((n[:, 0] > 0).sum())} with land cells, {int((n[:, 1] > 0).sum())} with cells that are not land ->", a.out)


if __name__ == "__main__":
    main()
