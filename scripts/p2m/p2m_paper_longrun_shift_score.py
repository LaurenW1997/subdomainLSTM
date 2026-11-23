"""Flood map on ordinary days, why the map is too dry: scores and figure of the test with a common shift of the inputs.

Input : data/p2m_long_v1/series.npz, sites.csv (p2m_paper_longrun.py), shift_lead6.npz (p2m_paper_longrun_shift.py), obs_v3_stations.csv
        (stations.csv of observed_inputs.py: offset of every control point), controls_used.csv - all fetched from sv7
Output: deliverables/35_floodmap/p2m_paper_too_dry_shift_test.csv (kind of day x shift x all / west / east of 90.8 W),
        p2m_paper_too_dry_best_shift_per_gauge.csv, p2m_paper_too_dry_level_offsets.csv, p2m_paper_too_dry.png
Usage : python p2m_paper_longrun_shift_score.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "deliverables" / "35_floodmap"; L = ROOT / "data" / "p2m_long_v1"
FR = ("2024-09-10 00:00", "2024-09-14 00:00"); SPLIT = -90.8; WEST, EAST, INK = "#c2410c", "#2f6fb5", "#1a1a19"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})


def main() -> None:
    warnings.simplefilter("ignore")
    z = np.load(L / "series.npz"); q = np.load(L / "shift_lead6.npz"); t = pd.DatetimeIndex(z["times"]); s = pd.read_csv(L / "sites.csv"); lvl = z["level_observed"].astype(np.float64); sh = q["shifts"]
    ok = (s.with_a_model > 0).to_numpy() & (np.isfinite(lvl).sum(0) >= 24 * 60) & np.isfinite(s.marsh_surface_m).to_numpy(); s = s[ok].reset_index(drop=True); lvl = lvl[:, ok]
    obs = np.maximum(lvl - s.marsh_surface_m.to_numpy()[None, :], 0); obs[~np.isfinite(lvl)] = np.nan; P = q["depth_map"][:, :, ok].astype(np.float64); west = s.lon.to_numpy() < SPLIT
    idx = pd.Series(np.nanmedian(lvl - np.nanmedian(lvl, 0)[None, :], 1), index=t); day = idx.resample("D").max(); frd = (day.index >= "2024-09-10") & (day.index < FR[1]); hwd = day.index[(day > day[~frd].quantile(0.95)) & ~frd]
    fr = np.asarray((t >= FR[0]) & (t < FR[1])); hw = np.asarray(t.normalize().isin(hwd)) & ~fr; kinds = {"ordinary days": ~fr & ~hw, "high water outside Francine": hw, "Francine": fr}; rows = []
    for k, m in kinds.items():
        o = obs[m]
        for i, d in enumerate(sh):
            p = P[i][m]; e = p - o; fin = np.isfinite(e); g = fin.sum(0) >= 24; rm = np.sqrt(np.nanmean(e ** 2, 0)); om = np.nanmean(np.where(fin, o, np.nan), 0); pm = np.nanmean(np.where(fin, p, np.nan), 0)
            of = np.nanmean(np.where(fin, o > 0.1, np.nan), 0); pf = np.nanmean(np.where(fin, p > 0.1, np.nan), 0)
            for name, gg in (("all", g), ("west of 90.8 W", g & west), ("east of 90.8 W", g & ~west)):
                rows.append({"kind_of_day": k, "inputs_raised_by_m": float(d), "gauges": name, "n_gauges": int(gg.sum()), "rmse_depth_median_m": np.median(rm[gg]), "mean_depth_observed_m": np.median(om[gg]), "mean_depth_map_m": np.median(pm[gg]),
                             "flooded_share_observed": np.mean(of[gg]), "flooded_share_map": np.mean(pf[gg]), "gauges_rmse_above_0.3m": int((rm[gg] > 0.3).sum())})
    T = pd.DataFrame(rows); T.to_csv(D / "p2m_paper_too_dry_shift_test.csv", index=False)
    y24, y25 = np.asarray(t.year == 2024), np.asarray(t.year == 2025); r24 = np.array([np.sqrt(np.nanmean((P[i][y24] - obs[y24]) ** 2, 0)) for i in range(len(sh))]); r25 = np.array([np.sqrt(np.nanmean((P[i][y25] - obs[y25]) ** 2, 0)) for i in range(len(sh))])
    g = np.isfinite(r24).all(0) & np.isfinite(r25).all(0); b = np.argmin(r24, 0); ar = np.arange(len(b))
    B = pd.DataFrame({"station": s.station, "lat": s.lat, "lon": s.lon, "ground_grid_minus_surveyed_marsh_m": s.ground_grid_m - s.marsh_surface_m, "shift_with_lowest_rmse_in_2024_m": sh[b], "rmse_2025_no_shift_m": r25[0], "rmse_2025_inputs_raised_0.2m_m": r25[list(sh).index(0.2)],
                      "rmse_2025_own_shift_m": r25[b, ar]})[g]; B.to_csv(D / "p2m_paper_too_dry_best_shift_per_gauge.csv", index=False)
    c = pd.read_csv(L / "controls_used.csv", dtype={"station_id": str}); o_ = pd.read_csv(L / "obs_v3_stations.csv", dtype={"station_id": str}); o_ = o_[o_.group == "control point, left out"]
    O = o_[["source", "station_id", "name", "lat", "lon", "offset_m"]].merge(c[["station_id", "station_datum", "datum_known", "best_model"]], on="station_id").rename(columns={"offset_m": "numerical_model_minus_observed_calm_hours_before_ida_m", "best_model": "cell_model"}).sort_values("lon")
    O.to_csv(D / "p2m_paper_too_dry_level_offsets.csv", index=False); kn = O[O.datum_known & (O.numerical_model_minus_observed_calm_hours_before_ida_m < 0.5)]; med = float(kn.numerical_model_minus_observed_calm_hours_before_ida_m.median())

    fig = plt.figure(figsize=(13.4, 8.0)); gs = fig.add_gridspec(2, 3, left=0.06, right=0.985, top=0.90, bottom=0.115, wspace=0.24, hspace=0.42)
    ax = fig.add_subplot(gs[0, :2]); y = O.numerical_model_minus_observed_calm_hours_before_ida_m; k = O.datum_known.to_numpy()
    ax.axhline(0, color="#8a8a86", lw=0.8); ax.axhline(med, color=INK, lw=0.8, ls=(0, (4, 3))); ax.scatter(O.lon[k], y[k], s=30, color=INK, zorder=3); ax.scatter(O.lon[~k], y[~k], s=30, facecolor="white", edgecolor=INK, linewidth=0.9, zorder=3)
    ax.text(-93.95, -1.27, f"dashed: median of the gauges with a known datum, the three swamp gauges at 91.0°W left aside: {med:.2f} m", fontsize=9, color=INK, va="bottom"); ax.set_ylim(-1.38, 1.45)
    ax.set_title("(a) Water level of the numerical model minus the observed one (NAVD88) at the 30 control points, calm hours before Ida", loc="left", fontsize=10.5, pad=4)
    ax.set_ylabel("model minus observed (m)", fontsize=9.5); ax.xaxis.set_major_formatter(lambda v, p: f"{-v:.0f}°W"); ax.grid(axis="y", color="#e3e3df", lw=0.5); ax.set_axisbelow(True); ax.tick_params(labelsize=8.5, length=2.5)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=INK, ms=5.5, label="datum of the gauge known (NAVD88)"), Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=5.5, label="datum not known")], loc="upper left", frameon=False, fontsize=8.8, handletextpad=0.2)
    bx = fig.add_subplot(gs[0, 2]); w = (B.lon < SPLIT).to_numpy(); cw = [int(((B.shift_with_lowest_rmse_in_2024_m == v) & w).sum()) for v in sh]; ce = [int(((B.shift_with_lowest_rmse_in_2024_m == v) & ~w).sum()) for v in sh]
    bx.bar(sh - 0.021, ce, width=0.038, color=EAST); bx.bar(sh + 0.021, cw, width=0.038, color=WEST); bx.set_xticks(sh); bx.set_xlabel("inputs raised by (m)", fontsize=9.5); bx.set_ylabel("marsh gauges", fontsize=9.5)
    bx.set_title("(b) The shift that suits each marsh gauge best (2024)", loc="left", fontsize=10.5, pad=4); bx.grid(axis="y", color="#e3e3df", lw=0.5); bx.set_axisbelow(True); bx.tick_params(labelsize=8.5, length=2.5)
    bx.legend(handles=[Line2D([], [], marker="s", ls="", color=EAST, ms=6, label="east of 90.8°W"), Line2D([], [], marker="s", ls="", color=WEST, ms=6, label="west of 90.8°W")], loc="upper center", frameon=False, fontsize=8.8, handletextpad=0.2)
    for j, (kind, lab) in enumerate((("ordinary days", "(c) Ordinary days"), ("high water outside Francine", "(d) High water outside Francine"), ("Francine", "(e) Hurricane Francine"))):
        cx = fig.add_subplot(gs[1, j]); x = T[T.kind_of_day == kind]
        for name, col in (("east of 90.8 W", EAST), ("west of 90.8 W", WEST)):
            v = x[x.gauges == name]; cx.plot(v.inputs_raised_by_m, v.mean_depth_map_m, color=col, lw=1.6, marker="o", ms=4); cx.axhline(float(v.mean_depth_observed_m.iloc[0]), color=col, lw=1.0, ls=(0, (4, 3)))
        e0 = x[(x.gauges == "east of 90.8 W")].set_index("inputs_raised_by_m").rmse_depth_median_m; w0 = x[(x.gauges == "west of 90.8 W")].set_index("inputs_raised_by_m").rmse_depth_median_m
        cx.set_title(lab, loc="left", fontsize=10.5, pad=4); cx.set_xticks(sh); cx.set_xlabel("inputs of the mapping model raised by (m)", fontsize=9.5); cx.grid(axis="y", color="#e3e3df", lw=0.5); cx.set_axisbelow(True); cx.tick_params(labelsize=8.5, length=2.5); cx.set_ylim(0, None)
        cx.text(0.03, 0.97, "RMSE of the depth (m), no shift → raised by 0.2 m" + "\n" + f"east {e0[0.0]:.2f} → {e0[0.2]:.2f},  west {w0[0.0]:.2f} → {w0[0.2]:.2f}", transform=cx.transAxes, va="top", ha="left", fontsize=8.8, color=INK, linespacing=1.35,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.88), zorder=6)
        if j == 0:
            cx.set_ylabel("mean depth on the marsh (m)", fontsize=9.5)
    fig.legend(handles=[Line2D([], [], color=EAST, lw=1.6, marker="o", ms=4), Line2D([], [], color=EAST, lw=1.0, ls=(0, (4, 3))), Line2D([], [], color=WEST, lw=1.6, marker="o", ms=4), Line2D([], [], color=WEST, lw=1.0, ls=(0, (4, 3)))],
               labels=["flood map, gauges east of 90.8°W", "observed, east", "flood map, gauges west of 90.8°W", "observed, west"], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.012), fontsize=9.2)
    fig.suptitle("Why the flood map is too dry: the level of the numerical model against the gauges, and a test with the inputs of the mapping model raised by one common amount (2024 to 2025, forecasts issued 6 h before)", x=0.012, ha="left", fontsize=10.6, y=0.975)
    out = D / "p2m_paper_too_dry.png"; fig.savefig(out, dpi=220); plt.close(fig)
    pd.set_option("display.width", 250); print(T[T.inputs_raised_by_m.isin([0.0, 0.2])].round(3).to_string(index=False)); print(f"offset median, datum known: {med:.3f} m ({len(kn)} gauges)")
    for nm, m in (("east", ~w), ("west", w)):
        x = B[m]; print(nm, len(x), "RMSE 2025 median: no shift", round(x.rmse_2025_no_shift_m.median(), 3), "raised 0.2", round(x["rmse_2025_inputs_raised_0.2m_m"].median(), 3), "own shift", round(x.rmse_2025_own_shift_m.median(), 3))
    print("->", out)


if __name__ == "__main__":
    main()
