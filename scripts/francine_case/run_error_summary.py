"""Francine case: how the error of the run is distributed - over the stations, over the kinds of water, in time, and with the height of the water.

Stations and window as in run_fig_batch.py: the gauges whose model cell followed the gauge in the Ida hindcast, five days
before to five days after the landfall, the model moved by its mean difference from the observations in these ten days.
Error = model minus observed, hour by hour.
Input : --series, --stations (_series.npz of run_score.py, _stations.csv of run_fig_batch.py), --fields NPZ of run_fields.py (only for the outline of the water on the maps)
Output: --out PREFIX: .png (six panels), _by_group.csv, _by_time.csv, _by_level.csv, _overall.csv, _stations.csv (group, peak and its timing per station)
Usage : python run_error_summary.py --series FILE --stations FILE --fields FILE --out deliverables/35_floodmap/francine_run_error_summary
"""
from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5, "axes.linewidth": 0.6})
INK, MUTED = "#0b0b0b", "#52514e"
LANDFALL = pd.Timestamp("2024-09-11 22:00")
GROUPS = {"open coast and passes": ["8770822", "8768094", "8766072", "8764314", "8764227", "07380249", "8761724", "8760922"],
          "bays, sounds and lakes": ["8770475", "08017118", "07387050", "07387040", "073816525", "8761305", "07380260", "8747437", "301429089145600", "301849088350000", "8741533", "02481299", "301200090072400", "8761927", "07375230", "301141089320300"],
          "Mississippi River": ["07374000", "8761955", "07374525", "8760721"],
          "inland channels and swamps": ["295744093303800", "07381600", "07378746", "07378745", "07378748", "07381355", "07381350", "07381150", "8762482", "295501090190400"]}
GCOL = {"open coast and passes": "#2a78d6", "bays, sounds and lakes": "#eb6834", "Mississippi River": "#1baf7a", "inland channels and swamps": "#eda100"}; GMARK = {"open coast and passes": "o", "bays, sounds and lakes": "s", "Mississippi River": "^", "inland channels and swamps": "D"}
SEQ = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]); DIV = LinearSegmentedColormap.from_list("blue_red", ["#104281", "#3987e5", "#f0efec", "#e34948", "#8a1f1f"])
LEVELS = [(-9, -0.3, "below -0.3"), (-0.3, -0.1, "-0.3 to -0.1"), (-0.1, 0.1, "-0.1 to 0.1"), (0.1, 0.3, "0.1 to 0.3"), (0.3, 0.6, "0.3 to 0.6"), (0.6, 9, "above 0.6")]


def region(lon: float) -> str:
    return "west of 92 W" if lon < -92 else ("92 W to 90.5 W (landfall)" if lon < -90.5 else "east of 90.5 W")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("series", "stations", "fields", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    z = np.load(a.series, allow_pickle=True); t = pd.DatetimeIndex(z["time"]); k = {(s, i): n for n, (s, i) in enumerate(zip(z["source"], z["station_id"]))}
    w = np.asarray((t >= LANDFALL - pd.Timedelta(days=5)) & (t <= LANDFALL + pd.Timedelta(days=5))); tv = t[w]; days = np.asarray((tv - LANDFALL) / pd.Timedelta(days=1))
    d = pd.read_csv(a.stations, dtype={"station_id": str}); gof = {i: g for g, ids in GROUPS.items() for i in ids}; d["group"] = d.station_id.map(gof); assert d.group.notna().all(), d[d.group.isna()].name.tolist(); d["region"] = d.lon.map(region)
    E = np.full((len(tv), len(d)), np.nan); A = np.full_like(E, np.nan); rows = []
    for n, r in enumerate(d.itertuples()):
        o = z["observed"][w, k[(r.source, r.station_id)]].astype("f8"); m = z["model"][w, k[(r.source, r.station_id)]].astype("f8"); ok = np.isfinite(o) & np.isfinite(m); ms = m - (m - o)[ok].mean(); E[:, n] = np.where(ok, ms - o, np.nan); A[:, n] = np.where(ok, o - o[ok].mean(), np.nan)
        ko = int(np.nanargmax(np.where(ok, o, np.nan))); km = int(np.nanargmax(np.where(ok, ms, np.nan)))
        rows.append({"source": r.source, "station_id": r.station_id, "name": r.name, "lat": r.lat, "lon": r.lon, "group": r.group, "region": r.region, "rmse_m": float(np.sqrt(np.nanmean(E[:, n] ** 2))), "mean_absolute_error_m": float(np.nanmean(np.abs(E[:, n]))),
                     "highest_observed_m": float(o[ko]), "highest_model_m": float(ms[km]), "highest_model_minus_observed_m": float(ms[km] - o[ko]), "hours_model_peak_after_observed_peak": float((tv[km] - tv[ko]) / pd.Timedelta(hours=1)),
                     "observed_rise_to_the_peak_m": float(o[ko] - o[ok].mean()), "error_at_the_observed_peak_m": float(ms[ko] - o[ko])})
    s = pd.DataFrame(rows); s.to_csv(a.out + "_stations.csv", index=False); e = E[np.isfinite(E)]
    ov = {"stations": len(s), "station_hours": int(e.size), "rmse_all_hours_m": float(np.sqrt((e ** 2).mean())), "mean_absolute_error_m": float(np.abs(e).mean()), **{f"error_percentile_{p}_m": float(np.percentile(e, p)) for p in (5, 25, 50, 75, 95)},
          **{f"share_of_hours_within_{x:.2f}_m": float((np.abs(e) <= x).mean()) for x in (0.05, 0.10, 0.20)}, "station_rmse_median_m": float(s.rmse_m.median()), "highest_model_minus_observed_median_m": float(s.highest_model_minus_observed_m.median()),
          "highest_model_minus_observed_rms_m": float(np.sqrt((s.highest_model_minus_observed_m ** 2).mean())), "stations_model_peak_within_3_hours": int((s.hours_model_peak_after_observed_peak.abs() <= 3).sum()), "peak_timing_median_hours": float(s.hours_model_peak_after_observed_peak.median())}
    pd.Series(ov).to_csv(a.out + "_overall.csv", header=["value"]); print(pd.Series(ov).round(3).to_string())
    grp = []
    for kind, col in (("kind of water", "group"), ("region", "region")):
        for g, x in s.groupby(col, sort=False):
            ee = E[:, x.index.to_numpy()]; ee = ee[np.isfinite(ee)]
            grp.append({"grouped_by": kind, "group": g, "stations": len(x), "rmse_station_median_m": x.rmse_m.median(), "rmse_all_hours_m": float(np.sqrt((ee ** 2).mean())), "share_of_hours_within_0.10_m": float((np.abs(ee) <= 0.1).mean()),
                        "highest_observed_median_m": x.highest_observed_m.median(), "highest_model_minus_observed_median_m": x.highest_model_minus_observed_m.median(), "highest_model_minus_observed_rms_m": float(np.sqrt((x.highest_model_minus_observed_m ** 2).mean())),
                        "stations_model_peak_too_low_by_more_than_0.1_m": int((x.highest_model_minus_observed_m < -0.1).sum()), "stations_model_peak_too_high_by_more_than_0.1_m": int((x.highest_model_minus_observed_m > 0.1).sum())})
    G = pd.DataFrame(grp); G.to_csv(a.out + "_by_group.csv", index=False); pd.set_option("display.width", 250); print(G.round(3).to_string(index=False))
    bt = pd.DataFrame({"time": tv.strftime("%Y-%m-%d %H:%M"), "days_from_landfall": days, "rms_over_stations_m": np.sqrt(np.nanmean(E ** 2, 1)), "mean_over_stations_m": np.nanmean(E, 1), "stations": np.isfinite(E).sum(1)}); bt.to_csv(a.out + "_by_time.csv", index=False)
    for name, lo, hi in (("five days to one day before the landfall", -5, -1), ("one day before to one day after", -1, 1), ("one to five days after", 1, 5.01)):
        ee = E[(days >= lo) & (days < hi)]; ee = ee[np.isfinite(ee)]; print(f"{name}: rmse {np.sqrt((ee ** 2).mean()):.3f} m, mean error {ee.mean():+.3f} m, within 0.10 m {100 * (np.abs(ee) <= 0.1).mean():.0f}%")
    lv = []
    for lo, hi, lab in LEVELS:
        sel = np.isfinite(E) & (A >= lo) & (A < hi); ee = E[sel]; lv.append({"observed_level_relative_to_the_station_mean": lab.replace("\n", " "), "share_of_hours": float(sel.sum() / np.isfinite(E).sum()), "mean_error_m": float(ee.mean()), "rmse_m": float(np.sqrt((ee ** 2).mean())), "error_quartile_25_m": float(np.percentile(ee, 25)), "error_quartile_75_m": float(np.percentile(ee, 75))})
    L = pd.DataFrame(lv); L.to_csv(a.out + "_by_level.csv", index=False); print(L.round(3).to_string(index=False))

    F = np.load(a.fields, allow_pickle=True); bg = ListedColormap(["#ffffff", "#e3e9ee"]); ext = [F["lon"][0], F["lon"][-1], F["lat"][0], F["lat"][-1]]
    fig, ax = plt.subplots(2, 3, figsize=(14, 8.2))
    for p, (col, cmap, vmin, vmax, title, lab) in enumerate((("rmse_m", SEQ, 0.0, 0.2, "RMSE at each station", "RMSE (m)"), ("highest_model_minus_observed_m", DIV, -0.3, 0.3, "Highest water level, model minus observed", "difference (m)"))):
        x = ax[0, p]; x.imshow(F["open_water"] >= 0.5, origin="lower", extent=ext, cmap=bg, aspect="auto", interpolation="nearest", zorder=1)
        for g in GROUPS:
            q = s[s.group == g]; sc = x.scatter(q.lon, q.lat, c=q[col], cmap=cmap, vmin=vmin, vmax=vmax, marker=GMARK[g], s=46, edgecolors=INK, linewidths=0.6, zorder=5)
        cb = fig.colorbar(sc, ax=x, orientation="horizontal", pad=0.09, fraction=0.05, aspect=40, extend="max" if p == 0 else "both"); cb.set_label(lab); cb.outline.set_linewidth(0.4)
        x.set_title(title); x.set_ylabel("latitude"); x.set_xlim(ext[0], ext[1]); x.set_ylim(28.75, 30.75); x.tick_params(length=2.5, width=0.5)
        if p == 0:
            x.legend([plt.Line2D([], [], marker=GMARK[g], ls="", mfc="#ffffff", mec=INK, ms=6) for g in GROUPS], list(GROUPS), loc="upper left", fontsize=8, frameon=True, framealpha=0.9, edgecolor="#cccccc", handletextpad=0.2)
    x = ax[0, 2]; x.hist(e, bins=np.arange(-0.5, 0.5001, 0.02), color="#3987e5", edgecolor="#ffffff", linewidth=0.4); x.axvline(0, color=INK, lw=0.6)
    x.set_title("All stations and hours: error of the model"); x.set_xlabel("model minus observed (m)"); x.set_ylabel("station-hours"); x.set_xlim(-0.5, 0.5)
    x.text(0.03, 0.96, f"{e.size} station-hours\nRMSE {ov['rmse_all_hours_m']:.2f} m\nwithin 0.05 m: {100 * ov['share_of_hours_within_0.05_m']:.0f}%\nwithin 0.10 m: {100 * ov['share_of_hours_within_0.10_m']:.0f}%\nwithin 0.20 m: {100 * ov['share_of_hours_within_0.20_m']:.0f}%\n"
           f"5th to 95th percentile:\n{ov['error_percentile_5_m']:+.2f} to {ov['error_percentile_95_m']:+.2f} m", transform=x.transAxes, va="top", ha="left", fontsize=9, color=INK)
    x = ax[1, 0]; x.axhline(0, color=INK, lw=0.5); x.axvline(0, color=MUTED, lw=0.6, ls=(0, (3, 3))); x.plot(days, bt.rms_over_stations_m, color="#2a78d6", lw=1.6, label="root mean square over the stations"); x.plot(days, bt.mean_over_stations_m, color="#eb6834", lw=1.6, label="mean over the stations")
    x.set_title("Error against time"); x.set_xlabel("days from the landfall"); x.set_ylabel("error (m)"); x.set_xlim(-5, 5); x.set_ylim(-0.12, 0.30); x.legend(loc="upper right", fontsize=8.5, frameon=False); x.text(0.08, x.get_ylim()[0] + 0.02 * np.ptp(x.get_ylim()), "landfall", fontsize=8.5, color=MUTED, va="bottom")
    x = ax[1, 1]; hi = float(max(s.highest_observed_m.max(), s.highest_model_m.max())) + 0.15; x.plot([0, hi], [0, hi], color=MUTED, lw=0.8)
    for g in GROUPS:
        q = s[s.group == g]; x.scatter(q.highest_observed_m, q.highest_model_m, color=GCOL[g], marker=GMARK[g], s=42, edgecolors="#ffffff", linewidths=0.6, zorder=5, label=f"{g} ({len(q)})")
    x.set_title("Highest water level at each station"); x.set_xlabel("observed (m, datum of the gauge)"); x.set_ylabel("model, datum difference taken out (m)"); x.set_xlim(0.2, hi); x.set_ylim(0.2, hi); x.set_aspect("equal"); x.legend(loc="upper left", fontsize=8.5, frameon=False, handletextpad=0.2)
    x.text(0.97, 0.05, f"model minus observed:\nmedian {ov['highest_model_minus_observed_median_m']:+.2f} m, rms {ov['highest_model_minus_observed_rms_m']:.2f} m", transform=x.transAxes, ha="right", va="bottom", fontsize=9)
    x = ax[1, 2]; xs = np.arange(len(L)); x.axhline(0, color=INK, lw=0.5); x.bar(xs, L.mean_error_m, width=0.62, color="#3987e5", zorder=3); x.vlines(xs, L.error_quartile_25_m, L.error_quartile_75_m, color=INK, lw=1.0, zorder=4)
    for i, r in L.iterrows():
        x.text(i, 0.235, f"{100 * r.share_of_hours:.0f}%", ha="center", va="bottom", fontsize=8.5); x.text(i, 0.195, f"{r.rmse_m:.2f} m", ha="center", va="bottom", fontsize=8.5)
    x.text(-0.62, 0.235, "share of hours", ha="right", va="bottom", fontsize=8.5, color=MUTED); x.text(-0.62, 0.195, "RMSE", ha="right", va="bottom", fontsize=8.5, color=MUTED)
    x.set_xticks(xs); x.set_xticklabels([lab for _, _, lab in LEVELS], fontsize=8.5); x.set_title("Error against the height of the water"); x.set_xlabel("observed level relative to the mean of the station in the ten days (m)"); x.set_ylabel("mean error (bar) and quartiles (line), m"); x.set_ylim(-0.25, 0.28); x.set_xlim(-1.75, len(L) - 0.5)
    for x in ax.ravel()[2:]:
        x.grid(True, lw=0.3, color="#d9d9d9", zorder=0); x.tick_params(length=2.5, width=0.5); x.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Hurricane Francine run against 38 gauges, five days before to five days after the landfall (model moved by its mean difference from each gauge)", fontsize=11.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.975), w_pad=1.6, h_pad=1.4); fig.savefig(a.out + ".png", dpi=200); print("->", a.out + ".png")


if __name__ == "__main__":
    main()
