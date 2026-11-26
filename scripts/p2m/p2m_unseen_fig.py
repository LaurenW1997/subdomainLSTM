"""Flood map: an unseen storm rebuilt by two trainings of the mapping model, as maps.

Top row: the largest depth of water on land in the ten days around the landfall of Hurricane Francine - in the numerical
model, and rebuilt by the mapping model from the control-point series of that run, once trained on the eleven runs of
Hurricane Ida and once on those plus the operational forecasts. Neither training has seen the Francine run.
Bottom row: rebuilt minus numerical model, and where the second training has a model and the first has none.
Fields are the largest value in blocks of 8 x 8 cells (the coarse file of the server). Grey: land without a model.
Input : --coarse NPZ (francine_unseen_coarse.npz), --version as_in_the_paper | with_input_error
Output: --out PNG
Usage : python p2m_unseen_fig.py --coarse FILE --version as_in_the_paper --out deliverables/35_floodmap/p2m_more_data_francine_unseen.png
"""
from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9.5, "axes.titlesize": 10.5, "axes.linewidth": 0.6})
SEQ = LinearSegmentedColormap.from_list("blue", ["#eef4fc", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]); DIV = LinearSegmentedColormap.from_list("blue_red", ["#0d366b", "#3987e5", "#f0efec", "#e34948", "#6e1414"])
NAMES = {"ida11": "eleven runs of Hurricane Ida", "ida11_operational": "eleven runs of Hurricane Ida\nand the operational forecasts"}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--coarse", required=True); ap.add_argument("--version", default="as_in_the_paper"); ap.add_argument("--out", required=True); a = ap.parse_args()
    z = np.load(a.coarse); v = a.version; lon, lat = z["lon"], z["lat"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; land = (z["land_share"] > 0.5) & (z["area_share"] > 0.5); truth = z[f"numerical_model | {v}"]
    M = {k: z[f"mapping | {k} | {v}"] for k in NAMES}; H = {k: z[f"share_with_model | {k} | {v}"] for k in NAMES}
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.4)); bg = np.where(land, 1.0, np.nan); asp = 1 / np.cos(np.deg2rad(29.8))

    def base(x, title):
        x.imshow(bg, origin="lower", extent=ext, cmap=ListedColormap(["#d9d9d6"]), aspect=asp, interpolation="nearest", zorder=1); x.set_title(title); x.set_xlim(-93.2, -88.7); x.set_ylim(28.95, 30.75); x.tick_params(length=2.5, width=0.5)
    base(ax[0, 0], "Numerical model (Francine hindcast)"); im = ax[0, 0].imshow(np.where(land, truth, np.nan), origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=2, aspect=asp, interpolation="nearest", zorder=2)
    for c, k in enumerate(NAMES, 1):
        ok = land & np.isfinite(M[k]); base(ax[0, c], "Mapping model trained on " + NAMES[k]); ax[0, c].imshow(np.where(ok, M[k], np.nan), origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=2, aspect=asp, interpolation="nearest", zorder=2)
        base(ax[1, c], "Mapping model minus numerical model"); dm = ax[1, c].imshow(np.where(ok, M[k] - truth, np.nan), origin="lower", extent=ext, cmap=DIV, vmin=-1, vmax=1, aspect=asp, interpolation="nearest", zorder=2)
    new = land & (H["ida11_operational"] > 0.5) & ~(H["ida11"] > 0.5); base(ax[1, 0], "Land that has a model only with the operational forecasts")
    ax[1, 0].imshow(np.where(new, 1.0, np.nan), origin="lower", extent=ext, cmap=ListedColormap(["#eb6834"]), aspect=asp, interpolation="nearest", zorder=2)
    cb = fig.colorbar(im, ax=ax[0, :], orientation="vertical", fraction=0.012, pad=0.01, extend="max"); cb.set_label("largest depth of water (m)"); cb.outline.set_linewidth(0.4)
    cb = fig.colorbar(dm, ax=ax[1, :], orientation="vertical", fraction=0.012, pad=0.01, extend="both"); cb.set_label("difference (m)"); cb.outline.set_linewidth(0.4)
    fig.suptitle("Hurricane Francine, five days before to five days after the landfall: largest depth of water on land, rebuilt from the control points of the run itself"
                 + ("" if v == "as_in_the_paper" else " (mapping with an assumed error of the inputs)") + ". Grey: land without a model", fontsize=11, y=0.985)
    fig.savefig(a.out, dpi=200, bbox_inches="tight"); print("->", a.out)


if __name__ == "__main__":
    main()
