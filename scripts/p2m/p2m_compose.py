"""Flood map: put two fits of p2m_paper.py together - some cells take their model from another fit.

Why: a run whose own grid differs from the Ida grid at some cells (ocean depth) gives a wrong depth there, so those cells
must not learn from that run. The fit with that run is made for all cells, and the cells in question take the model of a fit
made without that run. Both fits must use the same control points and the same nearest control points per cell; the other fit
may hold only the cells in question (a fit made for those cells alone).
The coefficients of the linear and Tobit models act on the control-point levels themselves and are copied as they are. The
logistic regression acts on levels standardised with the mean and standard deviation of the training hours, which differ
between the fits; its coefficients are converted exactly to the standardisation of the base fit.
Input : --base model.npz, --other model.npz, --cells NPZ[:key] boolean [lat, lon] (the cells that take the other model)
Output: --out DIR/model.npz and compose_summary.txt
Usage : python p2m_compose.py --base DIR/model.npz --other DIR/model.npz --cells differ_NAME.npz:differ --out DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

PER_CELL = ("type", "model", "cv_rmse", "valid_folds", "coef_linear", "coef_logit", "coef_tobit")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--base", required=True); ap.add_argument("--other", required=True); ap.add_argument("--cells", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "model.npz").exists(), f"{out} has a model already"
    B = dict(np.load(a.base, allow_pickle=True)); O = np.load(a.other, allow_pickle=True); f, _, key = a.cells.partition(":"); mask = np.load(f)[key or "differ"].astype(bool)
    assert (B["used"] == O["used"]).all() and float(B["wet"]) == float(O["wet"]), "the two fits do not use the same control points"
    sel = np.where(mask[B["jj"], B["ii"]])[0]; before = {k: B[k][sel].copy() for k in ("type", "model")}
    NX = int(max(B["ii"].max(), O["ii"].max())) + 1; lin_o = O["jj"].astype(np.int64) * NX + O["ii"]; order = np.argsort(lin_o); lin_b = B["jj"][sel].astype(np.int64) * NX + B["ii"][sel]       # the other fit may hold fewer cells (a fit made for these cells only)
    pos = np.searchsorted(lin_o[order], lin_b); assert (pos < len(order)).all() and (lin_o[order][pos] == lin_b).all(), "the other fit lacks some of the cells"; so_ = order[pos]
    assert (B["cols"][sel] == O["cols"][so_]).all(), "a cell does not have the same nearest control points in the two fits"
    for k in PER_CELL:
        B[k] = B[k].copy(); B[k][sel] = O[k][so_]
    c = B["cols"][sel].astype(int); g = O["coef_logit"][so_].astype(np.float64); mo, so, mb, sb = O["xmean"], O["xstd"], B["xmean"], B["xstd"]             # logit: g0 + sum g_p (x_p - m_p) / s_p, rewritten with the mean and std of the base fit
    g2 = g.copy(); g2[:, 1:] = g[:, 1:] * sb[c] / so[c]; g2[:, 0] = g[:, 0] + (g[:, 1:] * (mb[c] - mo[c]) / so[c]).sum(1); B["coef_logit"][sel] = g2.astype(B["coef_logit"].dtype)
    B["composed_from"] = np.array([str(a.base), str(a.other)]); B["cells_from_other"] = sel.astype(np.int32); np.savez_compressed(out / "model.npz", **B)
    names = {0: "no model", 1: "Type 1", 2: "Type 2 with a model", 3: "low flood risk", 4: "never flooded"}
    L = [f"base: {a.base}", f"other: {a.other}", f"cells that take the model of the other fit: {len(sel)} of {len(B['jj'])} ({mask.sum()} cells marked on the grid, {len(sel)} of them in the prediction area)",
         "their type before -> after: " + "; ".join(f"{names[int(t)]}: {int((before['type'] == t).sum())} -> {int((B['type'][sel] == t).sum())}" for t in (1, 2, 3, 4)),
         f"with a model before {int((before['model'] > 0).sum())}, after {int((B['model'][sel] > 0).sum())}"]
    (out / "compose_summary.txt").write_text(chr(10).join(L), encoding="utf-8"); print(chr(10).join(L)); print("->", out / "model.npz")


if __name__ == "__main__":
    main()
