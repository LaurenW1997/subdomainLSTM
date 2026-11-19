"""Flood map: coarse fields of the paper's mapping model for drawing (which model every cell got, peak depths).

Input : --model model.npz of p2m_paper.py, --apply DIR with peak_<tag>.npz, --eval eval_<run>.npz of mapping_fit.py (land, water), --tags TAG ...
Output: --out NPZ: lat, lon (every --step-th cell block), land_frac, water_frac, class (most frequent in the block: 0 outside the prediction
        area, 1 Type 1, 2 Model-2, 3 hurdle, 4 Tobit, 5 low flood risk, 6 never flooded), peak | <tag> (largest in the block, land cells
        with a model), peak_truth | <tag> where the tag has one
Usage : python p2m_paper_coarse.py --model FILE --apply DIR --eval FILE --tags ida_hindcast_inputs francine_lead6 --out FILE
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--apply", required=True); ap.add_argument("--eval", required=True); ap.add_argument("--tags", nargs="+", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--step", type=int, default=4)
    a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    m = np.load(a.model); jj, ii = m["jj"], m["ii"]; ev = np.load(a.eval); lat, lon = ev["lat"], ev["lon"]; NY, NX = len(lat), len(lon); land = ev["dmax_no_storm"] <= 0.1; water = ev["dmin_all_runs"] > 0.1
    cls = np.zeros((NY, NX), np.int8); typ, mdl = m["type"], m["model"]; cls[jj, ii] = np.where(typ == 1, 1, np.where(typ == 2, mdl, np.where(typ == 3, 5, 6)))
    s = a.step; ny, nx = NY // s, NX // s; blk = lambda x: x[:ny * s, :nx * s].reshape(ny, s, nx, s)
    cnt = np.stack([(blk(cls) == k).sum((1, 3)) for k in range(7)]); o = {"lat": lat[:ny * s].reshape(ny, s).mean(1), "lon": lon[:nx * s].reshape(nx, s).mean(1), "land_frac": blk(land.astype(np.float32)).mean((1, 3)),
                                                                         "water_frac": blk(water.astype(np.float32)).mean((1, 3)), "class": cnt.argmax(0).astype(np.int8), "class_land": np.stack([(blk(np.where(land, cls, -1)) == k).sum((1, 3)) for k in range(7)]).argmax(0).astype(np.int8)}
    has = np.zeros((NY, NX), bool); has[jj, ii] = mdl > 0
    for tag in a.tags:
        z = np.load(Path(a.apply) / f"peak_{tag}.npz")
        for key, nm in (("peak", "peak"), ("peak_truth", "peak_truth")):
            if key in z.files:
                f = np.zeros((NY, NX), np.float32); f[jj, ii] = np.nan_to_num(z[key], nan=0.0); o[f"{nm} | {tag}"] = blk(np.where(land & has, f, 0)).max((1, 3))
    np.savez_compressed(a.out, **o); print("->", a.out)


if __name__ == "__main__":
    main()
