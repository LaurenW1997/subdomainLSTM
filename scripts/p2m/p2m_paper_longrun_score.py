"""Flood map on ordinary days: the two-year series of p2m_paper_longrun.py scored at the marsh gauges, by kind of day.

Kinds of day (hours of 2024-01-02 .. 2025-12-19, the test period of the water-level model):
    Francine                     10 to 13 September 2024
    high water outside Francine  days whose highest water is among the highest --top share of the days outside Francine. The water
                                 of a day: the median over the marsh gauges of (observed level minus the median level of the gauge),
                                 its highest value of the day
    ordinary days                all other days
Observed depth on the marsh = max(observed level - surveyed marsh surface, 0); 'flooded' = deeper than --wet m.
Input : --series series.npz, --sites sites.csv of p2m_paper_longrun.py (default data/p2m_long_v1, fetched from sv7 p2m/long_v1)
Output: deliverables/35_floodmap/p2m_paper_ordinary_days_summary.csv (kind of day x lead x all / west / east of 90.8 W),
        p2m_paper_ordinary_days_sites.csv (per gauge and kind of day, inputs observed and forecast 6 h before),
        p2m_paper_ordinary_days_high_water_days.csv, p2m_paper_ordinary_days_fig_data.npz (what the figures draw)
Usage : python p2m_paper_longrun_score.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "deliverables" / "35_floodmap"
FR = ("2024-09-10 00:00", "2024-09-14 00:00"); SPLIT = -90.8; LEADS = (0, 1, 3, 6)
KINDS = ["ordinary days", "high water outside Francine", "Francine"]
FIG_SITES = [(-91.9, 29.6), (-91.1, 29.45), (-90.45, 29.45), (-90.1, 29.85), (-89.75, 29.7)]          # places to take an example gauge near: west, Atchafalaya, Terrebonne, Barataria, east
FIG_WINDOWS = {"Francine": ("2024-09-10 00:00", "2024-09-14 00:00")}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--series", default=str(ROOT / "data" / "p2m_long_v1" / "series.npz")); ap.add_argument("--sites", default=str(ROOT / "data" / "p2m_long_v1" / "sites.csv"))
    ap.add_argument("--top", type=float, default=0.05); ap.add_argument("--wet", type=float, default=0.1); ap.add_argument("--min-days", type=int, default=60); a = ap.parse_args()
    z = np.load(a.series); t = pd.DatetimeIndex(z["times"]); s = pd.read_csv(a.sites); lvl = z["level_observed"].astype(np.float64)
    ok = (s.with_a_model > 0).to_numpy() & (np.isfinite(lvl).sum(0) >= 24 * a.min_days) & np.isfinite(s.marsh_surface_m).to_numpy(); s = s[ok].reset_index(drop=True); lvl = lvl[:, ok]
    obs = np.maximum(lvl - s.marsh_surface_m.to_numpy()[None, :], 0); obs[~np.isfinite(lvl)] = np.nan; P = {L: z[f"depth_map_lead{L}"][:, ok].astype(np.float64) for L in LEADS}
    idx = pd.Series(np.nanmedian(lvl - np.nanmedian(lvl, 0)[None, :], 1), index=t); day = idx.resample("D").max(); fr_day = (day.index >= pd.Timestamp(FR[0]).normalize()) & (day.index < FR[1])
    thr = float(day[~fr_day].quantile(1 - a.top)); hw_days = day.index[(day > thr) & ~fr_day]; dn = t.normalize()
    fr = np.asarray((t >= FR[0]) & (t < FR[1])); hw = np.asarray(dn.isin(hw_days)) & ~fr; kind = {"ordinary days": ~fr & ~hw, "high water outside Francine": hw, "Francine": fr}
    ev = pd.DataFrame({"day": hw_days.strftime("%Y-%m-%d"), "highest_water_of_the_day_above_normal_m": day[hw_days].round(3).to_numpy()}); ev["event"] = (hw_days.to_series().diff().dt.days.fillna(9).to_numpy() > 1).cumsum()
    ev.to_csv(D / "p2m_paper_ordinary_days_high_water_days.csv", index=False)
    print(f"{len(s)} gauges; days: {int((~fr_day).sum())} outside Francine, {len(hw_days)} of high water (above {thr:.2f} m over normal) in {ev.event.nunique()} events; hours: " + ", ".join(f"{k} {int(m.sum())}" for k, m in kind.items()))
    west = s.lon.to_numpy() < SPLIT; rows = []; per = []
    for k, m in kind.items():
        o = obs[m]
        for L in LEADS:
            p = P[L][m]; e = p - o; n = np.isfinite(e).sum(0); good = n >= 24
            with np.errstate(all="ignore"):
                rm = np.sqrt(np.nanmean(e ** 2, 0)); bi = np.nanmean(e, 0); om = np.nanmean(np.where(np.isfinite(e), o, np.nan), 0); pm = np.nanmean(np.where(np.isfinite(e), p, np.nan), 0)
                of = np.nanmean(np.where(np.isfinite(e), o > a.wet, np.nan), 0); pf = np.nanmean(np.where(np.isfinite(e), p > a.wet, np.nan), 0)
                both = np.isfinite(e) & (o > a.wet) & (p > a.wet); bw = np.array([np.mean(e[:, j][both[:, j]]) if both[:, j].sum() >= 12 else np.nan for j in range(e.shape[1])])
                omx = np.nanmax(np.where(np.isfinite(e), o, np.nan), 0); pmx = np.nanmax(np.where(np.isfinite(e), p, np.nan), 0)
            for name, g in (("all", good), ("west of 90.8 W", good & west), ("east of 90.8 W", good & ~west)):
                rows.append({"kind_of_day": k, "inputs": "observed" if L == 0 else f"forecast {L} h before", "gauges": name, "n_gauges": int(g.sum()), "hours": int(m.sum()), "rmse_depth_median_m": np.median(rm[g]), "bias_median_m": np.median(bi[g]),
                             "mean_depth_observed_m": np.median(om[g]), "mean_depth_map_m": np.median(pm[g]), "flooded_share_observed": np.mean(of[g]), "flooded_share_map": np.mean(pf[g]),
                             "bias_when_both_flooded_median_m": np.nanmedian(bw[g]), "gauges_rmse_above_0.3m": int((rm[g] > 0.3).sum()), "largest_depth_observed_median_m": np.median(omx[g]), "largest_depth_map_median_m": np.median(pmx[g])})
            if L in (0, 6):
                per.append(pd.DataFrame({"station": s.station, "lat": s.lat, "lon": s.lon, "kind_of_day": k, "inputs": "observed" if L == 0 else f"forecast {L} h before", "hours": n, "rmse_depth_m": rm, "bias_m": bi, "mean_depth_observed_m": om,
                                         "mean_depth_map_m": pm, "flooded_share_observed": of, "flooded_share_map": pf, "largest_depth_observed_m": omx, "largest_depth_map_m": pmx})[good])
    sm = pd.DataFrame(rows); sm.to_csv(D / "p2m_paper_ordinary_days_summary.csv", index=False); pd.concat(per).to_csv(D / "p2m_paper_ordinary_days_sites.csv", index=False)
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 100); print(sm[sm.gauges == "all"].drop(columns=["gauges", "hours"]).round(3).to_string(index=False)); print(sm[(sm.gauges != "all") & sm.inputs.isin(["forecast 6 h before"])].drop(columns=["hours", "inputs"]).round(3).to_string(index=False))
    print(ev.groupby("event").agg(first=("day", "first"), last=("day", "last"), days=("day", "size"), top=("highest_water_of_the_day_above_normal_m", "max")).to_string())
    # what the figure of example gauges draws: the gauge nearest to each place with nearly complete observations, three windows
    best = ev.loc[ev.groupby("event").highest_water_of_the_day_above_normal_m.idxmax()].sort_values("highest_water_of_the_day_above_normal_m", ascending=False)
    pick = next(d for d in best.day if not ("2024-06-15" <= d <= "2024-06-25") and not ("2024-11-01" <= d <= "2024-11-12") and not ("2024-07-05" <= d <= "2024-07-10"))    # an event without a tropical storm in the Gulf
    # ordinary days to show: the four days without high water in which most gauges are flooded part of the time (neither dry throughout nor under water throughout)
    od = pd.Series(kind["ordinary days"], index=t).resample("D").min().astype(bool); cand = [d for d in od.index[:-4] if od[d:d + pd.Timedelta(days=3)].all()]; wet = pd.DataFrame(obs > a.wet, index=t).where(np.isfinite(obs))
    share = [(wet[d:d + pd.Timedelta(days=4) - pd.Timedelta(hours=1)].mean().between(0.2, 0.8)).mean() for d in cand]; o0 = cand[int(np.argmax(share))]
    c0 = pd.Timestamp(pick) - pd.Timedelta(days=2); win = {"ordinary days": (str(o0), str(o0 + pd.Timedelta(days=4))), "high water outside Francine": (str(c0), str(c0 + pd.Timedelta(days=4))), "Francine": FIG_WINDOWS["Francine"]}
    wm = {k: np.asarray((t >= w[0]) & (t < w[1])) for k, w in win.items()}; cover = np.min([np.isfinite(obs[m]).mean(0) for m in wm.values()], 0); chosen = []
    for x, y in FIG_SITES:
        d = np.hypot((s.lon.to_numpy() - x) * 97, (s.lat.to_numpy() - y) * 111); d[(cover < 0.95) | np.isin(np.arange(len(s)), chosen)] = 1e9; chosen.append(int(d.argmin()))
    o_ = {"station": s.station.to_numpy(str)[chosen], "lat": s.lat.to_numpy()[chosen], "lon": s.lon.to_numpy()[chosen], "kinds": np.array(list(win))}
    for k in win:
        key = k.replace(" ", "_"); o_[f"times | {key}"] = np.array(t[wm[k]].strftime("%Y-%m-%d %H:%M"), dtype=str); o_[f"observed | {key}"] = obs[wm[k]][:, chosen].astype(np.float32)
        for L in (1, 3, 6):
            o_[f"lead{L} | {key}"] = P[L][wm[k]][:, chosen].astype(np.float32)
    np.savez_compressed(D / "p2m_paper_ordinary_days_fig_data.npz", **o_); print("example gauges:", list(o_["station"]), "windows:", win)


if __name__ == "__main__":
    main()
