"""Flood map on ordinary days, why the map is too dry: a test with a common shift of the inputs.

At the gauges whose datum is known the water level of the numerical model lies about 0.4 m below the observed one (NAVD88).
The chain moves the observations down to the level of the model before the mapping model sees them, so the mapping model
works in the world of the numerical model, where the water stands lower against the ground than it does in reality. Test:
the inputs of the mapping model (already on the level of the model) are raised by one common amount, the same at every
control point and hour, and the depth at the marsh gauges is computed again. Nothing is fitted here.
Input : --series series.npz of p2m_paper_longrun.py (inputs_lead<L>), --model model.npz of p2m_paper.py, --sites CSV, --land eval_<run>.npz, --ida DIR
Output: --out NPZ: times, station, shifts, depth_map [shift, T, S] (float16; NaN where the site has no model)
Usage : python p2m_paper_longrun_shift.py --series FILE --model FILE --sites FILE --land FILE --ida DIR --out FILE [--lead 6] [--shifts 0 0.1 ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid  # noqa: E402
from p2m_paper import predict  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("series", "model", "sites", "land", "ida", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--lead", type=int, default=6); ap.add_argument("--shifts", type=float, nargs="+", default=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]); ap.add_argument("--radius", type=int, default=3)
    a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    z = np.load(a.series); X = z[f"inputs_lead{a.lead}"].astype(np.float64); T = len(X); m = np.load(a.model); model = {k: m[k] for k in m.files}; jj, ii = model["jj"], model["ii"]; has = model["model"] > 0; mused = model["used"]
    h, roms, lat, lon = grid(Path(a.ida)); NY, NX = h.shape; land = np.load(a.land)["dmax_no_storm"] <= 0.1; idx = np.full((NY, NX), -1, np.int64); idx[jj, ii] = np.arange(len(jj))
    sites = pd.read_csv(a.sites); assert list(sites.station) == list(z["station"]); R = a.radius; out = np.full((len(a.shifts), T, len(sites)), np.nan, np.float16); ok = np.isfinite(X).all(1)
    for k, s in enumerate(sites.itertuples()):
        j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin()); js, is_ = np.meshgrid(np.arange(max(j - R, 0), min(j + R + 1, NY)), np.arange(max(i - R, 0), min(i + R + 1, NX)), indexing="ij")
        near = (np.hypot(js - j, is_ - i) <= R + 0.5) & land[js, is_]; ids = idx[js[near], is_[near]]; ids = ids[ids >= 0]; w = ids[has[ids]]
        if len(w) == 0:
            continue
        for q, d in enumerate(a.shifts):
            out[q, ok, k] = np.nanmedian(predict(model, (X[ok] + d)[:, mused], w), 1)
    np.savez_compressed(a.out, times=z["times"], station=z["station"], shifts=np.array(a.shifts), lead=a.lead, depth_map=out); print("->", a.out)


if __name__ == "__main__":
    main()
