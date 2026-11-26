"""Flood map in Hurricane Francine from the forecasts of the water-level model, with three trainings of the mapping model,
against the observations at the marsh gauges (CRMS).

Columns: the mapping model trained on the eleven runs of Hurricane Ida; on those and the operational forecasts; on those, the
operational forecasts and the hindcast of Hurricane Francine. Top: the largest depth of the storm days on land from the
forecast issued --lead hours before; dots: the largest depth observed at the marsh gauges, same colours (squares: gauges where
that training gives no map). Bottom: the same per gauge, map against observation, gauges west and east of 90.8 W apart.
The table holds every version, every lead and both sets of gauges (the gauges a training has a map for; the gauges all three have).
Input : deliverables/35_floodmap/ <stem>_coarse_francine_leads.npz (p2m_paper_coarse.py), <stem>_crms.csv (p2m_paper_crms.py),
        <stem>_sites.csv (p2m_paper.py apply) for the three trainings, marsh_map_sites.csv (observed depths at all gauges)
Output: deliverables/35_floodmap/p2m_more_data_francine_forecast_map.png, p2m_more_data_francine_marsh_gauges.csv
Usage : python p2m_more_data_francine_fig.py [--version with_input_error] [--lead 6]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

from mapping_fig import DEPTH, DEPTH_B, DRY, INK, WATER

D = Path(__file__).resolve().parents[2] / "deliverables" / "35_floodmap"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
EXT = [-92.5, -88.4, 28.85, 30.6]; SPLIT = -90.8; WEST, EAST = "#c2410c", "#2f6fb5"
TRAININGS = {"eleven runs of Hurricane Ida": "p2m_paper_11runs_{v}", "eleven runs of Hurricane Ida\nand the operational forecasts": "p2m_more_data_ida11_operational_{v}",
             "eleven runs of Hurricane Ida, the operational\nforecasts and the hindcast of Hurricane Francine": "p2m_more_data_ida11_operational_francine_{v}"}
FIELDS = {0: "Francine, inputs observed", 1: "Francine, inputs forecast 1 h before", 3: "Francine, inputs forecast 3 h before", 6: "Francine, inputs forecast 6 h before"}


def stats(x: pd.DataFrame) -> dict:
    o, p = x.storm_observed_largest_depth_m.to_numpy(), x.storm_map_largest_depth_m.to_numpy(); w = x.lon.to_numpy() < SPLIT; r = lambda m: float(np.sqrt(((p - o)[m] ** 2).mean())) if m.any() else np.nan
    return {"marsh_gauges": len(x), "west_of_90.8W": int(w.sum()), "east_of_90.8W": int((~w).sum()), "depth_hour_by_hour_rmse_median_per_gauge_m": x.rmse_depth_m.median(), "largest_depth_mean_error_m": float((p - o).mean()),
            "largest_depth_rmse_m": r(np.ones(len(x), bool)), "largest_depth_rmse_west_m": r(w), "largest_depth_rmse_east_m": r(~w), "largest_depth_correlation": float(np.corrcoef(o, p)[0, 1]),
            "largest_depth_observed_median_west_m": float(np.median(o[w])), "largest_depth_map_median_west_m": float(np.median(p[w])), "largest_depth_observed_median_east_m": float(np.median(o[~w])), "largest_depth_map_median_east_m": float(np.median(p[~w]))}


def table() -> pd.DataFrame:
    rows = []
    for v in ("as_in_the_paper", "with_input_error"):
        C = {n: pd.read_csv(D / (s.format(v=v) + "_crms.csv")).dropna(subset=["storm_observed_largest_depth_m", "storm_map_largest_depth_m"]) for n, s in TRAININGS.items()}
        for L, f in FIELDS.items():
            X = {n: c[c.field == f] for n, c in C.items()}; common = set.intersection(*[set(x.station) for x in X.values()])
            for n, x in X.items():
                for g, y in (("the gauges this training has a map for", x), ("the gauges all three trainings have a map for", x[x.station.isin(common)])):
                    rows.append({"version": v.replace("_", " "), "inputs": f.replace("Francine, inputs ", ""), "trained_on": n.replace("\n", " "), "gauges_scored": g, **stats(y)})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--version", default="with_input_error"); ap.add_argument("--lead", type=int, default=6); a_ = ap.parse_args(); v, L = a_.version, a_.lead
    t = table(); t.to_csv(D / "p2m_more_data_francine_marsh_gauges.csv", index=False)
    a = pd.read_csv(D / "marsh_map_sites.csv"); a = a[a.field.str.startswith("the site's own fit") & a.field.str.endswith("6 h before")].dropna(subset=["storm_observed_largest_depth_m"])
    dcm = ListedColormap(DEPTH); dn = BoundaryNorm(DEPTH_B, dcm.N); bcm = ListedColormap([DRY, WATER])
    C = {n: pd.read_csv(D / (s.format(v=v) + "_crms.csv")) for n, s in TRAININGS.items()}; C = {n: c[c.field == FIELDS[L]].dropna(subset=["storm_observed_largest_depth_m", "storm_map_largest_depth_m"]) for n, c in C.items()}
    common = set.intersection(*[set(c.station) for c in C.values()]); top = max(max(float(c.storm_observed_largest_depth_m.max()), float(c.storm_map_largest_depth_m.max())) for c in C.values()) * 1.06
    fig = plt.figure(figsize=(17.2, 9.3)); gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.45], left=0.04, right=0.99, top=0.90, bottom=0.14, wspace=0.12, hspace=0.06)
    for k, (n, s) in enumerate(TRAININGS.items()):
        z = np.load(D / (s.format(v=v) + "_coarse_francine_leads.npz")); lat, lon = z["lat"], z["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; water = z["water_frac"] >= 0.5; f = z[f"peak | francine_lead{L}"]
        info = pd.read_csv(D / (s.format(v=v) + "_sites.csv")).set_index("station").with_a_model; m_ = a.assign(model=[bool(info.get(s_, 0) > 0) for s_ in a.station])
        ax = fig.add_subplot(gs[0, k]); ax.imshow(np.where(water, 1.0, 0.0), extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        im = ax.imshow(np.where(~water & (f > DEPTH_B[0]), f, np.nan), extent=ext, origin="lower", cmap=dcm, norm=dn, aspect="auto", interpolation="nearest")
        for m, mk, sz in ((m_[m_.model], "o", 15), (m_[~m_.model], "s", 19)):
            o = m.storm_observed_largest_depth_m; ax.scatter(m.lon, m.lat, c=np.where(o > DEPTH_B[0], o, np.nan), cmap=dcm, norm=dn, s=sz, marker=mk, edgecolor=INK, linewidth=0.4 if mk == "o" else 0.85, zorder=5, plotnonfinite=False)
            dry = m[o <= DEPTH_B[0]]; ax.scatter(dry.lon, dry.lat, c=DRY, s=sz, marker=mk, edgecolor=INK, linewidth=0.4 if mk == "o" else 0.85, zorder=5)
        ax.axvline(SPLIT, color=INK, lw=0.5, ls=(0, (4, 3)), zorder=4); ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.7)))
        ax.set_title("Mapping model trained on " + n, loc="left", fontsize=10.5, pad=4, linespacing=1.15); ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda x, p: f"{-x:.0f}°W"); ax.yaxis.set_major_formatter(lambda y, p: f"{y:.1f}°N"); ax.text(SPLIT - 0.03, 28.88, "90.8°W", ha="right", va="bottom", fontsize=8, color=INK)
        ax.text(0.015, 0.975, f"no map at {int((~m_.model).sum())} of {len(m_)} gauges", transform=ax.transAxes, va="top", ha="left", fontsize=8.8, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.9), zorder=6)
        x = C[n]; o, p = x.storm_observed_largest_depth_m.to_numpy(), x.storm_map_largest_depth_m.to_numpy(); w = x.lon.to_numpy() < SPLIT; q = stats(x); qc = stats(x[x.station.isin(common)])
        bx = fig.add_subplot(gs[1, k]); bx.plot([0, top], [0, top], color="#8a8a86", lw=0.8, zorder=1)
        bx.scatter(o[~w], p[~w], s=24, color=EAST, edgecolor="white", linewidth=0.5, zorder=3); bx.scatter(o[w], p[w], s=24, color=WEST, edgecolor="white", linewidth=0.5, zorder=4)
        bx.set_xlim(0, top); bx.set_ylim(0, top); bx.set_aspect("equal"); bx.grid(color="#e3e3df", lw=0.5); bx.set_axisbelow(True); bx.tick_params(labelsize=8.5, length=2.5); bx.set_xlabel("observed: largest depth on the marsh (m)", fontsize=9.5)
        if k == 0:
            bx.set_ylabel("flood map: largest depth (m)", fontsize=9.5)
        bx.text(0.03, 0.975, f"RMSE of the largest depth (m), {len(x)} gauges with a map" + "\n" + f"all {q['largest_depth_rmse_m']:.2f}, west {q['largest_depth_rmse_west_m']:.2f}, east {q['largest_depth_rmse_east_m']:.2f}; correlation {q['largest_depth_correlation']:.2f}" + "\n"
                + f"on the {len(common)} gauges all three have: {qc['largest_depth_rmse_m']:.2f}; correlation {qc['largest_depth_correlation']:.2f}" + "\n" + f"depth hour by hour, median per gauge: {q['depth_hour_by_hour_rmse_median_per_gauge_m']:.2f}",
                transform=bx.transAxes, va="top", ha="left", fontsize=8.6, color=INK, linespacing=1.3, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.88), zorder=6)
    cax = fig.add_axes([0.34, 0.04, 0.32, 0.012]); cb = fig.colorbar(im, cax=cax, ticks=DEPTH_B[:-1], spacing="uniform", orientation="horizontal"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5); cb.set_label("largest depth (m)", fontsize=9, labelpad=2)
    fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc=DEPTH[3], mec=INK, mew=0.45, ms=5, label="observed at a marsh gauge"), Line2D([], [], marker="s", ls="", mfc=DEPTH[3], mec=INK, mew=0.9, ms=5, label="observed, where the training gives no map")],
               loc="lower left", bbox_to_anchor=(0.04, 0.005), frameon=False, fontsize=8.8, ncol=1, handletextpad=0.3, title="maps", title_fontsize=8.8, alignment="left")
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=WEST, ms=5, label="marsh gauge west of 90.8°W"), Line2D([], [], marker="o", ls="", color=EAST, ms=5, label="marsh gauge east of 90.8°W")],
               loc="lower right", bbox_to_anchor=(0.97, 0.005), frameon=False, fontsize=8.8, ncol=1, handletextpad=0.3, title="gauge by gauge", title_fontsize=8.8, alignment="left")
    src = "forecast issued %d h before" % L if L else "observed water levels"
    fig.suptitle(f"Hurricane Francine, 10 to 13 September 2024: largest depth on land from the {src} at the control points, through three trainings of the mapping model"
                 + (" (with an assumed error of the inputs)" if v == "with_input_error" else "") + ", against the marsh gauges", x=0.012, ha="left", fontsize=11.5, y=0.975)
    out = D / ("p2m_more_data_francine_forecast_map.png" if (v, L) == ("with_input_error", 6) else f"p2m_more_data_francine_forecast_map_{v}_lead{L}.png"); fig.savefig(out, dpi=200); plt.close(fig)
    pd.set_option("display.width", 250); s = t[(t.version == v.replace("_", " ")) & (t.inputs == FIELDS[L].replace("Francine, inputs ", ""))]; print(s.drop(columns=["version", "inputs"]).round(3).T.to_string()); print("->", out)


if __name__ == "__main__":
    main()
