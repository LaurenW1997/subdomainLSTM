"""Flood map against the water-level gauges that are not control points: scores and figures (p2m_paper_gauges_longrun.py).

Water level of the map at the cell of a gauge against the observed level, hour by hour, 2024-01-02 .. 2025-12-19, by kind of
day (as p2m_paper_longrun_score.py). The constant difference of every gauge (datum, the offset of the numerical model, ground of
the cell) is taken out: the median of map minus observed over the ordinary days. Hours in which the cell of the map is dry
(less than --wet m) cannot be compared and are counted. For reference: the direct forecast of the water-level model at the
same gauge, 6 h before, and how far the observed water rises above its ordinary median.
Groups: in the bays and lakes (cell of the ocean model, always under water) / inland water (always under water) /
        cell dry at times, with water in the map at least --share of the hours / cell dry at times, almost never with water in the map
Input : data/p2m_gauges_v1/gauges.csv, series.npz, forecasts_hourly.npz (from sv7 p2m/gauges_v1, fc_v3), deliverables/35_floodmap/p2m_paper_ordinary_days_high_water_days.csv
Output: deliverables/35_floodmap/p2m_paper_other_gauges_stations.csv, _summary.csv, _fig_data.npz, p2m_paper_other_gauges.png, p2m_paper_other_gauges_stations.png
Usage : python p2m_paper_gauges_score.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

from mapping_fig import DRY, INK, WATER

ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "deliverables" / "35_floodmap"; L = ROOT / "data" / "p2m_gauges_v1"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
FR = ("2024-09-10 00:00", "2024-09-14 00:00"); WET, SHARE = 0.05, 0.2; LEAD_COL = {1: "#f6cdb8", 3: "#ee9468", 6: "#d6450c"}
KINDS = ["ordinary days", "high water outside Francine", "Francine"]
GROUPS = ["in the bays and lakes, always under water", "inland water, always under water", "cell dry at times, with water in the map part of the time", "cell dry at times, almost never with water in the map"]
SEQ = ["#fde8c8", "#f9c27a", "#ee8f3a", "#cf5a14", "#8f3206"]; SEQ_B = [0, 0.05, 0.10, 0.20, 0.40, 2.0]
WIN = {"ordinary days": ("2024-03-23 00:00", "2024-03-26 23:00"), "high water outside Francine": ("2024-04-08 00:00", "2024-04-11 23:00"), "Francine": ("2024-09-10 00:00", "2024-09-13 23:00")}
SHOW = ["073802516", "301001089442600", "073802332", "07380200", "07381590"]
LABEL = {"073802516": ("Barataria Pass", "at Grand Isle"), "301001089442600": ("Rigolets", "near Slidell"), "073802332": ("Inner Harbor Navigation", "Canal, New Orleans"), "07380200": ("Amite River near", "French Settlement"),
         "07381590": ("Wax Lake Outlet", "at Calumet")}


def main() -> None:
    warnings.simplefilter("ignore")
    z = np.load(L / "series.npz"); G = pd.read_csv(L / "gauges.csv", dtype={"station_id": str}); M = G[G.has_a_map].reset_index(drop=True); t = pd.DatetimeIndex(z["times"]); assert list(M.station_id) == list(z["station_id"])
    hw = pd.read_csv(D / "p2m_paper_ordinary_days_high_water_days.csv"); fr = np.asarray((t >= FR[0]) & (t < FR[1])); hwm = np.asarray(t.normalize().isin(pd.DatetimeIndex(hw.day))) & ~fr
    kind = {"ordinary days": ~fr & ~hwm, "high water outside Francine": hwm, "Francine": fr}; od = kind["ordinary days"]; obs = z["level_observed"].astype(np.float64)
    f = np.load(L / "forecasts_hourly.npz"); assert list(f["station_id"]) == list(M.station_id); i0 = pd.DatetimeIndex(f["valid"]).get_indexer(t); F = f["forecast"]; direct = {h: F[i0 - h, h - 1, :].astype(np.float64) for h in (1, 3, 6)}
    rows = []; offs = np.full(len(M), np.nan); grp = []
    for k, r in M.iterrows():
        o = obs[:, k]; dp = z["depth_map_lead6"][:, k].astype(np.float64); wet = dp > WET; share = float(wet[np.isfinite(dp)].mean())
        g = (GROUPS[0] if r.cell_in_ocean_model else GROUPS[1]) if r.cell.startswith("always") else (GROUPS[2] if share >= SHARE else GROUPS[3]); grp.append(g)
        use = wet & np.isfinite(o); offs[k] = np.median((z["level_map_lead6"][:, k] - o)[use & od]) if (use & od).sum() >= 240 else np.nan
        rec = {"source": r.source, "station_id": r.station_id, "name": r["name"], "lat": r.lat, "lon": r.lon, "group": g, "cell_distance_m": r.cell_distance_m, "share_of_hours_with_water_in_the_map": share, "map_minus_observed_ordinary_days_m": offs[k]}
        for kn, m in kind.items():
            key = kn.split()[0]; rec[f"observed_rise_above_ordinary_median_m | {key}"] = float(np.nanmean(o[m]) - np.nanmedian(o[od])); rec[f"rmse_direct_forecast_6h_m | {key}"] = float(np.sqrt(np.nanmean((direct[6][m, k] - o[m]) ** 2)))
            for h in (0, 1, 3, 6):
                lv = z[f"level_map_lead{h}"][:, k].astype(np.float64); w_ = (z[f"depth_map_lead{h}"][:, k] > WET) & np.isfinite(o) & m; e = (lv - o - offs[k])[w_]
                rec[f"rmse_map_{'observed_inputs' if h == 0 else f'{h}h'}_m | {key}"] = float(np.sqrt(np.mean(e ** 2))) if len(e) >= 24 and np.isfinite(offs[k]) else np.nan
        rows.append(rec)
    S = pd.DataFrame(rows); S.to_csv(D / "p2m_paper_other_gauges_stations.csv", index=False); M["group"] = grp
    sm = []
    for g in GROUPS:
        x = S[S.group == g]
        for kn in KINDS:
            key = kn.split()[0]; v = x[f"rmse_map_6h_m | {key}"]
            sm.append({"group": g, "gauges": len(x), "kind_of_day": kn, "gauges_scored": int(v.notna().sum()), "share_of_hours_with_water_in_the_map_median": x.share_of_hours_with_water_in_the_map.median(), "rmse_map_1h_median_m": x[f"rmse_map_1h_m | {key}"].median(),
                       "rmse_map_3h_median_m": x[f"rmse_map_3h_m | {key}"].median(), "rmse_map_6h_median_m": v.median(), "gauges_rmse_above_0.3m": int((v > 0.3).sum()), "rmse_direct_forecast_6h_median_m": x[f"rmse_direct_forecast_6h_m | {key}"].median(),
                       "observed_rise_above_ordinary_median_m": x[f"observed_rise_above_ordinary_median_m | {key}"].median()})
    SM = pd.DataFrame(sm); SM.to_csv(D / "p2m_paper_other_gauges_summary.csv", index=False); pd.set_option("display.width", 250); print(G.groupby(["in_prediction_area", "cell"]).size().to_string()); print(SM.round(3).to_string(index=False))

    # figure 1: where the map can be checked, and how far it is off at high water
    c = np.load(D / "p2m_paper_11runs_with_input_error_coarse.npz"); lat, lon = c["lat"], c["lon"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]; base = np.where(c["water_frac"] >= 0.5, 1.0, 0.0); bcm = ListedColormap([DRY, WATER]); area = c["class"] > 0
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.5)); fig.subplots_adjust(left=0.045, right=0.985, top=0.885, bottom=0.27, wspace=0.10); E = [-92.6, -88.4, 28.85, 30.95]
    for ax in axes:
        ax.imshow(base, extent=ext, origin="lower", cmap=bcm, vmin=0, vmax=1, aspect="auto", interpolation="nearest"); ax.contour(lon, lat, area.astype(float), levels=[0.5], colors=[INK], linewidths=0.6, linestyles=[(0, (4, 3))])
        ax.set_xlim(E[0], E[1]); ax.set_ylim(E[2], E[3]); ax.set_aspect(1 / np.cos(np.deg2rad(29.9))); ax.set_xticks(np.arange(-92, -88, 1)); ax.set_yticks(np.arange(29, 31, 0.5)); ax.tick_params(labelsize=8.5, length=2.5)
        ax.xaxis.set_major_formatter(lambda v, p: f"{-v:.0f}°W"); ax.yaxis.set_major_formatter(lambda v, p: f"{v:.1f}°N")
    ax = axes[0]; out_ = G[~G.in_prediction_area]; nom = G[G.in_prediction_area & ~G.has_a_map]; dry = S[S.group == GROUPS[3]]; part = S[S.group == GROUPS[2]]; wetc = S[S.group.isin(GROUPS[:2])]
    ax.scatter(out_.lon, out_.lat, s=16, marker="x", color="#7a7a76", linewidth=0.9, zorder=4); ax.scatter(nom.lon, nom.lat, s=20, marker="s", facecolor="white", edgecolor=INK, linewidth=0.8, zorder=5)
    ax.scatter(dry.lon, dry.lat, s=24, marker="o", facecolor="white", edgecolor="#c2410c", linewidth=1.1, zorder=6); ax.scatter(part.lon, part.lat, s=26, marker="o", color="#c2410c", edgecolor="white", linewidth=0.5, zorder=7); ax.scatter(wetc.lon, wetc.lat, s=28, marker="o", color="#2f6fb5", edgecolor="white", linewidth=0.5, zorder=8)
    ax.set_title(f"(a) The {len(G)} water-level gauges that are not control points: where the map can be checked", loc="left", fontsize=10.5, pad=4)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color="#2f6fb5", ms=5.5, label=f"cell always under water: {len(wetc)}"), Line2D([], [], marker="o", ls="", color="#c2410c", ms=5.5, label=f"cell dry at times, water in the map part of the time: {len(part)}"),
                       Line2D([], [], marker="o", ls="", mfc="white", mec="#c2410c", mew=1.1, ms=5.5, label=f"almost never water in the map at the gauge: {len(dry)}"), Line2D([], [], marker="s", ls="", mfc="white", mec=INK, ms=5, label=f"no cell with a model nearby: {len(nom)}"),
                       Line2D([], [], marker="x", ls="", color="#7a7a76", ms=5, label=f"outside the prediction area (dashed): {len(out_)}")], loc="upper left", bbox_to_anchor=(0.0, -0.10), ncol=2, frameon=False, fontsize=8.8, handletextpad=0.2, columnspacing=1.2)
    ax = axes[1]; cm = ListedColormap(SEQ); nm = BoundaryNorm(SEQ_B, cm.N); x = S[S.group != GROUPS[3]].dropna(subset=["rmse_map_6h_m | high"])
    sc = ax.scatter(x.lon, x.lat, c=x["rmse_map_6h_m | high"], cmap=cm, norm=nm, s=34, edgecolor=INK, linewidth=0.45, zorder=6); ax.set_title("(b) High water outside Francine: RMSE of the water level of the map (m)", loc="left", fontsize=10.5, pad=4)
    cax = fig.add_axes([0.62, 0.15, 0.26, 0.02]); cb = fig.colorbar(sc, cax=cax, orientation="horizontal", ticks=SEQ_B[:-1], spacing="uniform"); cb.ax.tick_params(labelsize=8.5, length=2); cb.outline.set_linewidth(0.5)
    fig.suptitle("Flood map against the water-level gauges that are not control points, 2024 to 2025 (the constant difference of every gauge taken out)", x=0.012, ha="left", fontsize=11, y=0.975)
    o1 = D / "p2m_paper_other_gauges.png"; fig.savefig(o1, dpi=220); plt.close(fig)

    # figure 2: five gauges, three windows; observed moved by the constant difference of the gauge
    idx = [list(M.station_id).index(s) for s in SHOW]; fd = {"station_id": np.array(SHOW), "name": M.name.to_numpy(str)[idx], "group": np.array(grp)[idx]}
    fig, axes = plt.subplots(len(idx), 3, figsize=(13.0, 2.05 * len(idx) + 1.1), sharey="row", gridspec_kw={"wspace": 0.08, "hspace": 0.20, "top": 0.925, "bottom": 0.075, "left": 0.075, "right": 0.99})
    for j, kn in enumerate(KINDS):
        w = np.asarray((t >= WIN[kn][0]) & (t <= WIN[kn][1])); tw = t[w]; fd[f"times | {kn}"] = np.array(tw.strftime("%Y-%m-%d %H:%M"), dtype=str)
        for i, k in enumerate(idx):
            ax = axes[i, j]; o = obs[w, k] + offs[k]; fd[f"observed | {kn} | {SHOW[i]}"] = o.astype(np.float32); P = {}
            for h in (1, 3, 6):
                p = z[f"level_map_lead{h}"][w, k].astype(np.float64); p[z[f"depth_map_lead{h}"][w, k] <= WET] = np.nan; P[h] = p; ax.plot(tw, p, color=LEAD_COL[h], lw=0.9, zorder=4); fd[f"lead{h} | {kn} | {SHOW[i]}"] = p.astype(np.float32)
            ax.plot(tw, o, color=INK, lw=1.1, zorder=5)
            if np.isfinite(o).any():
                pk = tw[int(np.nanargmax(o))]; ax.axvspan(pk - pd.Timedelta(hours=12), pk + pd.Timedelta(hours=12), color="#000000", alpha=0.05, lw=0)
            if j == 2:
                lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.34 * (hi - lo))
            rm = lambda p: float(np.sqrt(np.nanmean((p - o) ** 2)) * 100) if np.isfinite(p - o).sum() >= 12 else np.nan; dryh = float(np.mean(~np.isfinite(P[6])))
            lab = "RMSE (cm)   " + "   ".join(f"{h} h {rm(P[h]):.1f}" for h in (1, 3, 6)) + (f"      no water in the map: {100 * dryh:.0f}% of the hours" if dryh > 0.02 else "")
            ax.text(0.03, 0.95, lab, transform=ax.transAxes, va="top", ha="left", fontsize=7.8, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85), zorder=6)
            ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{mdates.num2date(v).day} {mdates.num2date(v):%b}")); ax.set_xlim(tw[0], tw[-1])
            ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(labelsize=8, length=2.5)
            if i < len(idx) - 1:
                ax.set_xticklabels([])
            if i == 0:
                ax.set_title({"ordinary days": "Ordinary days, 2024", "high water outside Francine": "High water outside Francine, 2024", "Francine": "Hurricane Francine, 2024"}[kn], loc="left", fontsize=9.5)
            if j == 0:
                ax.set_ylabel("\n".join(LABEL[SHOW[i]] + ("water level (m)",)), fontsize=8.3, linespacing=1.2)
    h_ = [Line2D([], [], color=INK, lw=1.1)] + [Line2D([], [], color=LEAD_COL[h], lw=1.2) for h in (1, 3, 6)]
    fig.legend(h_, ["observed"] + [f"flood map, from forecasts issued {h} h earlier" for h in (1, 3, 6)], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.012))
    fig.suptitle("Water level at five gauges that are not control points: observed (moved by the constant difference of the gauge) and the flood map; a gap in the map = no water in the map there", x=0.012, ha="left", fontsize=10.4, y=0.975)
    o2 = D / "p2m_paper_other_gauges_stations.png"; fig.savefig(o2, dpi=230); plt.close(fig); np.savez_compressed(D / "p2m_paper_other_gauges_fig_data.npz", **fd); print("->", o1); print("->", o2)


if __name__ == "__main__":
    main()
