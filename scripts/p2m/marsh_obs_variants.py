"""Flood map without the numerical model, second step: why the sites with the highest surge come out too low, and what helps.

marsh_obs_fit.py fits, per CRMS site, a linear model of the water level on the gauges with data in real time. At the sites
with the highest surge it is about 1 m low. Variants of the fit, all linear in their terms and fitted on the same years:
  gauges                       as marsh_obs_fit.py (all gauges with the same assumed error)
  near gauges favoured         the assumed error of a gauge grows with its distance from the site (--d0 km), so the weights
                               move to the gauges near the site
  steeper at high water        extra terms max(level - 95th percentile, 0) and max(level - 99th percentile, 0) of the --hinge nearest
                               gauges: the slope may change once those gauges are far above normal
  wind                         wind stress at the site (u|U|, v|U|), mean of the last 3 h and of the last 12 h (AORC reanalysis,
                               as the water-level model uses it; in a forecast this is the forecast wind)
  stretched at high water      the best variant, plus one correction for all sites above a threshold over the normal level of the
                               site, calibrated on the left-out storms (the fit is low at high water in every one of them)
The variant is chosen on storms inside the training years, each left out in turn (the fit never sees the storm it is scored
on, nor the week before and after). Then Francine (after the training years) and Ida (left out) are scored as before.
A gauge is an input if it has data in real time and observations in --min-coverage of the training hours; a gauge that fails
during a storm stays an input, its missing hours are filled from the other gauges.
Input : --dataset DIR (values, wind_u, wind_v), --live FILE, --fc NPZ of forecast_inputs.py, --crms-raw CSV
Output: --out DIR: validation.csv (per variant), storms.csv (per variant, storm and site), sites.csv (Francine and Ida, per variant and site), series.npz, summary.txt,
        levels.npz (the level at every site and hour from the chosen variant, with the observations, for marsh_map.py)
Usage : python marsh_obs_variants.py --dataset DIR --live FILE --fc FILE --crms-raw FILE --out DIR
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marsh_obs_fit import FR_CALM, FR_STORM, FT, IDA, IDA_STORM, fill, metrics  # noqa: E402

VAL = {"Harvey 2017": ("2017-08-26", "2017-09-01"), "Nate 2017": ("2017-10-06", "2017-10-10"), "Gordon 2018": ("2018-09-03", "2018-09-07"), "Barry 2019": ("2019-07-10", "2019-07-17"),
       "Cristobal 2020": ("2020-06-05", "2020-06-10"), "Laura 2020": ("2020-08-25", "2020-08-30"), "Delta 2020": ("2020-10-07", "2020-10-12"), "Zeta 2020": ("2020-10-27", "2020-10-31")}
PAD = pd.Timedelta(days=7)
BEST = "near gauges favoured + steeper at high water + wind"; STRETCHED = BEST + ", stretched at high water"
VARIANTS = {"gauges": (False, False, False), "gauges + wind": (False, False, True), "near gauges favoured": (True, False, False), "near gauges favoured + steeper at high water": (True, True, False),
            "near gauges favoured + wind": (True, False, True), "near gauges favoured + steeper at high water + wind": (True, True, True)}


def trail(a, k):
    """Mean of the last k hours (the hour itself included) along axis 0."""
    c = np.cumsum(np.vstack([np.zeros((1,) + a.shape[1:]), a]), 0); out = np.empty_like(a); n = np.minimum(np.arange(1, len(a) + 1), k)
    out[:] = (c[1:] - c[np.maximum(np.arange(1, len(a) + 1) - k, 0)]) / n.reshape((-1,) + (1,) * (a.ndim - 1))
    return out


def sums(F, y):
    return np.array([float(len(y))]), F.sum(0), F.T @ F, np.array([y.sum()]), F.T @ y


def solve(S, cols, sig2):
    n = float(S[0][0]); xm = S[1][cols] / n; ym = float(S[3][0]) / n
    b = np.linalg.solve(S[2][np.ix_(cols, cols)] - n * np.outer(xm, xm) + n * np.diag(sig2), S[4][cols] - n * xm * ym)
    return b, ym - xm @ b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--live", required=True); ap.add_argument("--fc", required=True); ap.add_argument("--crms-raw", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--train", nargs=2, default=["2016-01-01", "2024-01-01"]); ap.add_argument("--until", default="2024-12-31"); ap.add_argument("--noise", type=float, default=0.08); ap.add_argument("--d0", type=float, default=30.0)
    ap.add_argument("--hinge", type=int, default=5); ap.add_argument("--min-coverage", type=float, default=0.8); ap.add_argument("--wet", type=float, default=0.1); ap.add_argument("--high", type=float, default=1.0, help="rise of the observed level that counts as high (m)")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "summary.txt").exists(), f"{out} has results already"
    t00 = time.time(); ds = Path(a.dataset)
    st = pd.read_csv(ds / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(ds / "time.npy")); vals = np.load(ds / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    i0, i1, i2 = (int(tm.get_indexer([pd.Timestamp(x)])[0]) for x in (a.train[0], a.train[1], a.until)); tt = tm[i0:i2]; T = len(tt); train = np.arange(T) < (i1 - i0)
    z = np.load(a.fc); FC = z["forecast"].astype(np.float64); fvalid = pd.DatetimeIndex(z["valid"]); TF, H = FC.shape[0], FC.shape[1]; V = np.arange(H, TF); tF = fvalid[V]
    fcol = {(s, i): k for k, (s, i) in enumerate(zip(z["source"], z["station_id"]))}
    live = set(Path(a.live).read_text().split()); keys = [k for k in fcol if k[1] in live and k in row]
    keys = [k for k in keys if np.isfinite(vals[row[k], i0:i1]).mean() >= a.min_coverage]; P = len(keys); rin = [row[k] for k in keys]
    lines = [f"inputs: {P} gauges with data in real time and observations in at least {100 * a.min_coverage:.0f}% of the training hours ({a.train[0]} .. {a.train[1]}); a gauge that fails during a storm stays an input"]

    d = pd.read_csv(a.crms_raw, usecols=["Station ID", "Date (mm/dd/yyyy)", "Time (hh:mm:ss)", "Time Zone", "Adjusted Water Elevation to Marsh (ft)", "Adjusted Water Elevation to Datum (ft)"], dtype=str, encoding="latin-1", on_bad_lines="skip")
    d.columns = ["station", "date", "time", "tz", "to_marsh", "to_datum"]; d = d[d.station.str.startswith("CRMS")]
    d["t"] = pd.to_datetime(d.date + " " + d.time, format="%m/%d/%Y %H:%M:%S", errors="coerce") + pd.to_timedelta(d.tz.map({"CST": 6, "CDT": 5, "UTC": 0, "GMT": 0}).fillna(6).astype(int), unit="h")
    d["to_marsh"] = pd.to_numeric(d.to_marsh, errors="coerce") * FT; d["to_datum"] = pd.to_numeric(d.to_datum, errors="coerce") * FT
    d = d.dropna(subset=["t", "to_marsh", "to_datum"]); d = d[d.t.dt.minute == 0].drop_duplicates(["station", "t"])
    cr = st[(st.source == "CRMS") & st.station_id.isin(set(d.station))].copy(); cr["cov"] = [np.isfinite(vals[r, i0:i1]).mean() for r in cr.index]; cr = cr[cr["cov"] >= 0.5].reset_index(drop=True)
    S = len(cr); rs = [row[("CRMS", i)] for i in cr.station_id]

    X = np.asarray(vals[rin, i0:i2], np.float64).T; Y = np.asarray(vals[rs, i0:i2], np.float64).T
    fin = np.isfinite(X[train]); mu = np.nanmean(X[train], 0); Xc = np.where(fin, X[train] - mu[None, :], 0.0); Mf = fin.astype(np.float64); cov = (Xc.T @ Xc) / np.maximum(Mf.T @ Mf, 1.0); lam = 0.05 ** 2
    Xf = fill(X, mu, cov, lam); qs = np.nanpercentile(X[train], [95, 99], 0); hinge_of = lambda Z: np.concatenate([np.maximum(Z - q[None, :], 0) for q in qs], 1)
    HG = hinge_of(Xf); hsd = HG[train].std(0); HG = HG / hsd[None, :]          # scaled to unit spread: these terms are zero in most hours, a penalty in metres would switch them off
    jF = tt.get_indexer(tF); assert (jF >= 0).all()
    X6 = fill(np.stack([FC[V - 6, 5, fcol[k]] for k in keys], 1), mu, cov, lam); HG6 = hinge_of(X6) / hsd[None, :]                     # Francine: forecasts issued 6 h before
    wu = np.asarray(np.load(ds / "wind_u.npy", mmap_mode="r")[rs, i0:i2], np.float64).T; wv = np.asarray(np.load(ds / "wind_v.npy", mmap_mode="r")[rs, i0:i2], np.float64).T
    sp = np.hypot(wu, wv); tx, ty = np.nan_to_num(wu * sp), np.nan_to_num(wv * sp)
    W = np.stack([trail(tx, 3), trail(ty, 3), trail(tx, 12), trail(ty, 12)], 2); W = W / W[train].std(0, keepdims=True)                   # [T, S, 4]
    lat, lon = cr.lat.to_numpy(float), cr.lon.to_numpy(float); ilat = np.array([st.lat[r] for r in rin]); ilon = np.array([st.lon[r] for r in rin])
    dist = np.hypot((lon[:, None] - ilon[None, :]) * np.cos(np.deg2rad(29.7)) * 111.2, (lat[:, None] - ilat[None, :]) * 111.2)             # [S, P]
    print(f"{P} inputs, {S} sites, {T} hours; prepared in {time.time() - t00:.0f} s", flush=True)

    win = {k: (np.asarray((tt >= pd.Timestamp(v[0]) - PAD) & (tt < pd.Timestamp(v[1]) + PAD)), np.where((tt >= v[0]) & (tt < v[1]))[0]) for k, v in VAL.items()}
    win["Ida"] = (np.asarray((tt >= "2021-08-15") & (tt < "2021-09-15")), tt.get_indexer(pd.date_range(IDA[0], IDA[1], freq="h")))
    K = a.hinge; G = np.arange(P); HC = P + np.arange(2 * K); WC = P + 2 * K + np.arange(4)
    hourly = []; recs = []; LF = {v: np.full((len(tF), S), np.nan) for v in VARIANTS}; LF6 = {v: np.full((len(tF), S), np.nan) for v in VARIANTS}; LI = {v: np.full((len(win["Ida"][1]), S), np.nan) for v in VARIANTS}
    ok = np.isfinite(Y[train]).sum(0) >= 5000
    for s in np.where(ok)[0]:
        nn = np.argsort(dist[s])[:K]; nh = np.concatenate([nn, P + nn]); F = np.concatenate([Xf, HG[:, nh], W[:, s]], 1); y = Y[:, s]; m = train & np.isfinite(y)
        tot = sums(F[m], y[m]); ws = {k: sums(F[m & w[0]], y[m & w[0]]) for k, w in win.items()}
        F6 = np.concatenate([X6, HG6[:, nh], W[jF, s]], 1)
        for v, (near, hinge, wind) in VARIANTS.items():
            cols = np.concatenate([G] + ([HC] if hinge else []) + ([WC] if wind else []))
            sig2 = np.concatenate([a.noise ** 2 * (1 + (dist[s] / a.d0) ** 2 if near else np.ones(P))] + ([np.full(2 * K, 0.05 ** 2)] if hinge else []) + ([np.full(4, 0.05 ** 2)] if wind else []))
            for k, (wm, ev) in win.items():
                b, c0 = solve(tuple(x - y_ for x, y_ in zip(tot, ws[k])), cols, sig2); p = c0 + F[ev][:, cols] @ b
                if k == "Ida":
                    LI[v][:, s] = p; continue
                o = y[ev]; f_ = np.isfinite(o)
                if f_.mean() < 0.6:
                    continue
                base = np.nanmedian(y[max(ev[0] - 48, 0):ev[0]]) if np.isfinite(y[max(ev[0] - 48, 0):ev[0]]).sum() >= 12 else np.nan
                if v == BEST:
                    hourly.append((k, s, o[f_], p[f_]))
                recs.append({"variant": v, "storm": k, "station": cr.station_id[s], "lon": lon[s], "observed_peak_m": float(o[f_].max()), "predicted_peak_m": float(p[f_].max()), "observed_rise_m": float(o[f_].max() - base),
                             "rmse_m": float(np.sqrt(np.mean((p - o)[f_] ** 2)))})
            b, c0 = solve(tot, cols, sig2); LF[v][:, s] = c0 + F[jF][:, cols] @ b; LF6[v][:, s] = c0 + F6[:, cols] @ b
    print(f"fits done, {time.time() - t00:.0f} s", flush=True)

    # The fit is low at high water in every left-out storm (a least-squares fit with imperfect inputs has less spread than the
    # observations). A stretch above a threshold, the same for all sites, is calibrated on the left-out storms:
    #     level' = level + beta * max(level - normal level of the site - r0, 0)
    ymed = np.nanmedian(Y[train], 0)

    def calibrate(items):
        an = np.concatenate([p - ymed[s] for _, s, o, p in items]); er = np.concatenate([o - p for _, s, o, p in items]); best = None
        for r0 in np.arange(0.1, 1.01, 0.1):
            h = np.maximum(an - r0, 0); beta = float((h * er).sum() / max((h * h).sum(), 1e-9)); sse = float(((er - beta * h) ** 2).sum())
            best = (sse, r0, beta) if best is None or sse < best[0] else best
        return best[1], best[2]

    stretch = lambda L, r0, beta: L + beta * np.maximum(L - ymed[None, :] - r0, 0)
    for k in VAL:                                                         # the stretch scored on a storm it was not calibrated on
        r0, beta = calibrate([x for x in hourly if x[0] != k])
        for kk, s, o, p in hourly:
            if kk == k:
                p2 = p + beta * np.maximum(p - ymed[s] - r0, 0); base = [r_ for r_ in recs if r_["variant"] == BEST and r_["storm"] == k and r_["station"] == cr.station_id[s]][0]
                recs.append({**base, "variant": STRETCHED, "predicted_peak_m": float(p2.max()), "rmse_m": float(np.sqrt(np.mean((p2 - o) ** 2)))})
    R0, BETA = calibrate(hourly); LF[STRETCHED] = stretch(LF[BEST], R0, BETA); LF6[STRETCHED] = stretch(LF6[BEST], R0, BETA); LI[STRETCHED] = stretch(LI[BEST], R0, BETA)
    lines.append(f"stretch at high water, calibrated on the left-out storms: above {R0:.1f} m over the normal level of the site, every further metre counts as {1 + BETA:.2f} m")
    sv = pd.DataFrame(recs); sv.to_csv(out / "storms.csv", index=False); sv["e"] = sv.predicted_peak_m - sv.observed_peak_m; hi = sv.observed_rise_m > a.high
    val = sv.groupby("variant", sort=False).apply(lambda x: pd.Series({"site_storms": len(x), "rmse_hourly_median_m": x.rmse_m.median(), "peak_mean_error_m": x.e.mean(), "peak_rms_error_m": np.sqrt((x.e ** 2).mean()),
                                                                       "high_site_storms": int((x.observed_rise_m > a.high).sum()), "high_peak_mean_error_m": x.e[x.observed_rise_m > a.high].mean(),
                                                                       "high_peak_rms_error_m": np.sqrt((x.e[x.observed_rise_m > a.high] ** 2).mean()), "other_peak_rms_error_m": np.sqrt((x.e[~(x.observed_rise_m > a.high)] ** 2).mean())}), include_groups=False).reset_index()
    val.to_csv(out / "validation.csv", index=False); pd.set_option("display.width", 250)
    lines += ["", f"storms inside the training years, each left out in turn ({', '.join(VAL)}); peak = highest level of the storm days; high = the observed level rose by more than {a.high} m:", val.round(3).to_string(index=False)]
    lines += ["", "by storm, sites that rose by more than %.1f m: number, mean error of the peak per variant" % a.high,
              sv[hi].pivot_table(index="storm", columns="variant", values="e", aggfunc="mean", sort=False).round(2).assign(n=sv[hi & (sv.variant == "gauges")].groupby("storm").size()).to_string()]

    def obs_marsh(times):
        g = d[(d.t >= times[0]) & (d.t <= times[-1])]
        om = g.pivot(index="t", columns="station", values="to_marsh").reindex(index=times, columns=cr.station_id).to_numpy(float); od = g.pivot(index="t", columns="station", values="to_datum").reindex(index=times, columns=cr.station_id).to_numpy(float)
        return om, od, np.nanmedian(od - om, 0)
    tI = pd.date_range(IDA[0], IDA[1], freq="h")
    with np.errstate(all="ignore"):
        omF, odF, gF = obs_marsh(tF); omI, odI, gI = obs_marsh(tI)
    calmF = np.asarray(tF < FR_CALM); stormF = np.asarray((tF >= FR_STORM[0]) & (tF < FR_STORM[1])); calmI = np.arange(len(tI)) < 72; stormI = np.asarray((tI >= IDA_STORM[0]) & (tI <= IDA_STORM[1]))
    np.savez_compressed(out / "levels.npz", variant=BEST, site=cr.station_id.to_numpy(str), lat=lat, lon=lon, fitted=ok, times_francine=np.array(tF.strftime("%Y-%m-%d %H:%M"), dtype=str),
                        times_ida=np.array(tI.strftime("%Y-%m-%d %H:%M"), dtype=str), level_francine_inputs_observed=LF[BEST], level_francine_inputs_forecast_6h=LF6[BEST], level_ida_left_out=LI[BEST],
                        observed_to_marsh_francine=omF, observed_level_francine=odF, marsh_surface_francine=gF, observed_to_marsh_ida=omI, observed_level_ida=odI, marsh_surface_ida=gI)      # for marsh_map.py
    rr = []; ser = {"times_francine": np.array(tF.strftime("%Y-%m-%d %H:%M"), dtype=str)}
    for v in list(VARIANTS) + [STRETCHED]:
        for field, L, om, od, g, calm, storm in ((f"Francine, inputs observed | {v}", LF[v], omF, odF, gF, calmF, stormF), (f"Francine, inputs forecast 6 h before | {v}", LF6[v], omF, odF, gF, calmF, stormF),
                                                 (f"Ida, inputs observed (the fit leaves this storm out) | {v}", LI[v], omI, odI, gI, calmI, stormI)):
            for s in np.where(ok)[0]:
                if np.isfinite(g[s]):
                    r = metrics(field, cr.iloc[s], om[:, s], L[:, s] - g[s], od[:, s], L[:, s], calm, storm, a.wet)
                    if r:
                        r["variant"] = v; r["test"] = field.split(" | ")[0]; rr.append(r)
                        if "6 h" in field:
                            ser[f"{v}|{cr.station_id[s]}"] = np.stack([om[:, s], L[:, s] - g[s]]).astype(np.float32)
    t = pd.DataFrame(rr); t.to_csv(out / "sites.csv", index=False); np.savez_compressed(out / "series.npz", **ser)
    t["pe"] = t.storm_map_largest_depth_m - t.storm_observed_largest_depth_m; core = t.storm_observed_largest_depth_m > 1.2
    for test, x in t.groupby("test", sort=False):
        g_ = x.groupby("variant", sort=False).apply(lambda y: pd.Series({"sites": len(y), "rmse_depth_median_m": y.rmse_depth_m.median(), "storm_rmse_depth_median_m": y.storm_rmse_depth_m.median(),
                                                                         "calm_flooded_observed": np.average(y.calm_observed_flooded_share.dropna(), weights=y.calm_hours.dropna()), "calm_flooded_predicted": np.average(y.calm_map_flooded_share.dropna(), weights=y.calm_hours.dropna()),
                                                                         "largest_mean_error_m": y.pe.mean(), "largest_rms_error_m": np.sqrt((y.pe ** 2).mean()), "largest_corr": y[["storm_observed_largest_depth_m", "storm_map_largest_depth_m"]].dropna().corr().iloc[0, 1],
                                                                         "sites_above_1.2m": int((y.storm_observed_largest_depth_m > 1.2).sum()), "above_1.2m_mean_error_m": y.pe[y.storm_observed_largest_depth_m > 1.2].mean(),
                                                                         "others_mean_error_m": y.pe[~(y.storm_observed_largest_depth_m > 1.2)].mean(), "others_rms_error_m": np.sqrt((y.pe[~(y.storm_observed_largest_depth_m > 1.2)] ** 2).mean())}), include_groups=False)
        lines += ["", test + ": depth on the marsh; largest = largest depth of the storm days", g_.round(3).to_string()]
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print(f"-> {out}, {time.time() - t00:.0f} s")


if __name__ == "__main__":
    main()
