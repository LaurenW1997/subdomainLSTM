"""Flood map: a small prediction area for test fits - only the land cells around the marsh gauges (CRMS).

The land cells within --radius cells of every site (the cells the flood map is scored on at a gauge, taken as `p2m_paper.py apply`
takes them) that lie inside a prediction area. A fit on this area takes minutes instead of hours.
Input : --ida DIR (grid), --sites CSV station, lat, lon, --land eval_<run>.npz (dmax_no_storm), --within NPZ (area) of the full prediction area
Output: --out NPZ: area [lat, lon] (boolean)
Usage : python p2m_area_around_sites.py --ida DIR --sites FILE --land FILE --within FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402


def cells_around(sites: pd.DataFrame, lat, lon, land, R: int):
    """Row, column and index of the site of every land cell within R cells of a site (a cell near two sites appears twice)."""
    NY, NX = land.shape; cj, ci, owner = [], [], []
    for k, s in enumerate(sites.itertuples()):
        j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin()); js, is_ = np.meshgrid(np.arange(max(j - R, 0), min(j + R + 1, NY)), np.arange(max(i - R, 0), min(i + R + 1, NX)), indexing="ij")
        near = (np.hypot(js - j, is_ - i) <= R + 0.5) & land[js, is_]; cj += list(js[near]); ci += list(is_[near]); owner += [k] * int(near.sum())
    return np.array(cj, int), np.array(ci, int), np.array(owner, int)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("ida", "sites", "land", "within", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--radius", type=int, default=3); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    h, roms, lat, lon = grid(Path(a.ida)); land = np.load(a.land)["dmax_no_storm"] <= 0.1; cj, ci, _ = cells_around(pd.read_csv(a.sites), lat, lon, land, a.radius)
    area = np.zeros(h.shape, bool); area[cj, ci] = True; area &= np.load(a.within)["area"]; np.savez_compressed(a.out, area=area); print(f"{int(area.sum())} cells ->", a.out)


if __name__ == "__main__":
    main()
