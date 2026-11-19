"""Flood map without the numerical model: the water level at the marsh gauges (CRMS) learned from observations of many years.

The mapping model of mapping_fit.py is fitted on the runs of one storm and gives every storm the pattern of that storm.
Here, for every CRMS site, a linear model is fitted on observations:
    water level at the site (NAVD88) = a + sum_p b_p * water level at gauge p        (ridge, inputs with an error of --noise m)
The gauges p are stations with data in real time (they have a forecast), the training hours are --train (several years with
many storms and cold fronts), the storms that are tested are left out. With --unusual-power the hours in which the gauges
are far from their normal levels get more weight, so that the fit is not ruled by the calm hours. The depth on the marsh is the level minus the
surveyed marsh surface of the site (from the CIMS export: water elevation to datum minus water elevation to marsh).
Hours without an observation at an input gauge are filled with its expectation given the other gauges.
Tests (CRMS sites are never an input):
    Francine (September 2024, after the training period): inputs observed, and forecasts issued 1, 3 and 6 h before
    Ida (August 2021): a second fit that leaves out 15 August to 15 September 2021; inputs observed
    between sites: the level of a site taken from the --neighbours nearest other sites (weights 1 / distance^2), as a
                   grid cell without a gauge would get it; with the surveyed marsh surface and with the ground level of the grid
Input : --dataset DIR, --live FILE, --fc NPZ of forecast_inputs.py, --crms-raw CSV (rows of the CIMS export for the two periods),
        --controls CSV (optional: only the control points of mapping_fit.py marked used are inputs), --grid-sites CSV (sites.csv of crms_marsh_check.py)
Output: --out DIR: sites.csv (one row per site and field), coef.npz, series.npz, summary.txt
Usage : python marsh_obs_fit.py --dataset DIR --live FILE --fc FILE --crms-raw FILE --grid-sites FILE --out DIR
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

FT = 0.3048
IDA = ("2021-08-25 00:00", "2021-09-05 00:00"); IDA_OUT = ("2021-08-15", "2021-09-15"); IDA_STORM = ("2021-08-28 12:00", "2021-08-31 12:00")
FR_CALM, FR_STORM = "2024-09-09 00:00", ("2024-09-10 00:00", "2024-09-14 00:00")
BANDS = [-94.2, -92.5, -91.5, -90.8, -90.2, -89.6, -88.0]


def fill(X, mu, cov, lam):
    """Missing inputs replaced by their expectation given the inputs present in the same hour."""
    out = X.copy(); fin = np.isfinite(X); pat, inv = np.unique(fin, axis=0, return_inverse=True); inv = np.asarray(inv).ravel()
    for k, A in enumerate(pat):
        if A.all():
            continue
        rows = np.where(inv == k)[0]; M = np.where(~A)[0]; a = np.where(A)[0]
        if len(a) < 3:
            out[np.ix_(rows, M)] = mu[M]; continue
        w = np.linalg.solve(cov[np.ix_(a, a)] + lam * np.eye(len(a)), cov[np.ix_(a, M)])
        out[np.ix_(rows, M)] = mu[M] + (X[np.ix_(rows, a)] - mu[a]) @ w
    return out


def sums(X, y, w):
    m = np.isfinite(y); x = X[m]; yy = y[m]; ww = w[m]; xw = x * ww[:, None]
    return np.array([ww.sum()], float), xw.sum(0), xw.T @ x, np.array([(ww * yy).sum()]), xw.T @ yy


def solve(S, noise):
    n, Sx, Sxx, Sy, Sxy = S; n = float(n[0]); xm = Sx / n; ym = float(Sy[0]) / n
    b = np.linalg.solve(Sxx - n * np.outer(xm, xm) + n * noise ** 2 * np.eye(len(xm)), Sxy - n * xm * ym)
    return b, ym - xm @ b


def metrics(field, r, o, dep, lev_obs, lev, calm, storm, wet):
    fin = np.isfinite(o) & np.isfinite(dep)
    if fin.sum() < 48:
        return None
    od = np.maximum(o, 0); dp = np.maximum(dep, 0); e = dp - od; fl = fin & np.isfinite(lev_obs)
    rec = {"field": field, "station": r.station_id, "lat": r.lat, "lon": r.lon, "hours": int(fin.sum()), "rmse_depth_m": float(np.sqrt(np.mean(e[fin] ** 2))), "bias_depth_m": float(e[fin].mean()),
           "rmse_level_m": float(np.sqrt(np.mean((lev - lev_obs)[fl] ** 2))) if fl.sum() >= 48 else np.nan}
    for nm, msk in (("calm", calm), ("storm", storm)):
        q = fin & msk
        if q.sum() >= 12:
            rec.update({f"{nm}_hours": int(q.sum()), f"{nm}_observed_flooded_share": float((o[q] > wet).mean()), f"{nm}_map_flooded_share": float((dp[q] > wet).mean()),
                        f"{nm}_observed_largest_depth_m": float(od[q].max()), f"{nm}_map_largest_depth_m": float(dp[q].max()), f"{nm}_observed_mean_depth_m": float(od[q].mean()), f"{nm}_map_mean_depth_m": float(dp[q].mean()),
                        f"{nm}_rmse_depth_m": float(np.sqrt(np.mean(e[q] ** 2)))})
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--live", required=True); ap.add_argument("--fc", required=True); ap.add_argument("--crms-raw", required=True); ap.add_argument("--controls"); ap.add_argument("--grid-sites")
    ap.add_argument("--out", required=True); ap.add_argument("--train", nargs=2, default=["2016-01-01", "2024-01-01"]); ap.add_argument("--val-from", default="2023-01-01")
    ap.add_argument("--noise", type=float, nargs="+", default=[0.03, 0.08, 0.15], help="assumed error of the inputs (m); the value with the smallest error in the validation year is used")
    ap.add_argument("--unusual-power", type=float, default=0.0, help="weight of a training hour = (mean squared standardised anomaly of the inputs) ** this; 0 = all hours alike")
    ap.add_argument("--min-coverage", type=float, default=0.8); ap.add_argument("--neighbours", type=int, default=4); ap.add_argument("--wet", type=float, default=0.1)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "summary.txt").exists(), f"{out} has results already"
    t00 = time.time(); ds = Path(a.dataset)
    st = pd.read_csv(ds / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(ds / "time.npy")); vals = np.load(ds / "values.npy", mmap_mode="r")
    row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    i0, iv, i1 = (int(tm.get_indexer([pd.Timestamp(x)])[0]) for x in (a.train[0], a.val_from, a.train[1]))
    z = np.load(a.fc); F, OF = z["forecast"].astype(np.float64), z["observed"].astype(np.float64); fvalid = pd.DatetimeIndex(z["valid"]); TF, H = F.shape[0], F.shape[1]; V = np.arange(H, TF); tF = fvalid[V]
    fcol = {(s, i): k for k, (s, i) in enumerate(zip(z["source"], z["station_id"]))}

    live = set(Path(a.live).read_text().split()); keys = [k for k in fcol if k[1] in live and k in row]                 # inputs: gauges with a forecast
    if a.controls:
        c = pd.read_csv(a.controls, dtype={"station_id": str}); c = c[c.used] if "used" in c.columns else c; keep = set(zip(c.source, c.station_id)); keys = [k for k in keys if k in keep]
    cov_tr = np.array([np.isfinite(vals[row[k], i0:i1]).mean() for k in keys]); cov_fr = np.array([np.isfinite(OF[:, fcol[k]]).mean() for k in keys])
    keys = [k for k, c1, c2 in zip(keys, cov_tr, cov_fr) if c1 >= a.min_coverage and c2 >= 0.9]; P = len(keys); rin = [row[k] for k in keys]
    lines = [f"inputs: {P} gauges with data in real time (observed in at least {100 * a.min_coverage:.0f}% of the training hours and in the Francine period); training {a.train[0]} .. {a.train[1]}"]

    d = pd.read_csv(a.crms_raw, usecols=["Station ID", "Date (mm/dd/yyyy)", "Time (hh:mm:ss)", "Time Zone", "Adjusted Water Elevation to Marsh (ft)", "Adjusted Water Elevation to Datum (ft)"], dtype=str, encoding="latin-1", on_bad_lines="skip")
    d.columns = ["station", "date", "time", "tz", "to_marsh", "to_datum"]; d = d[d.station.str.startswith("CRMS")]
    d["t"] = pd.to_datetime(d.date + " " + d.time, format="%m/%d/%Y %H:%M:%S", errors="coerce") + pd.to_timedelta(d.tz.map({"CST": 6, "CDT": 5, "UTC": 0, "GMT": 0}).fillna(6).astype(int), unit="h")
    d["to_marsh"] = pd.to_numeric(d.to_marsh, errors="coerce") * FT; d["to_datum"] = pd.to_numeric(d.to_datum, errors="coerce") * FT
    d = d.dropna(subset=["t", "to_marsh", "to_datum"]); d = d[d.t.dt.minute == 0].drop_duplicates(["station", "t"])
    cr = st[(st.source == "CRMS") & st.station_id.isin(set(d.station))].copy()
    cr["cov"] = [np.isfinite(vals[r, i0:i1]).mean() for r in cr.index]; cr = cr[cr["cov"] >= 0.5].reset_index(drop=True); S = len(cr); rs = [row[("CRMS", i)] for i in cr.station_id]
    lines.append(f"targets: {S} CRMS sites with a water level relative to the marsh in the export and observations in at least half of the training hours")

    X = np.asarray(vals[rin, i0:i1], np.float64).T; Y = np.asarray(vals[rs, i0:i1], np.float64).T; ttr = tm[i0:i1]
    fin = np.isfinite(X); mu = np.nanmean(X, 0); Xc = np.where(fin, X - mu[None, :], 0.0); Mf = fin.astype(np.float64)
    cov = (Xc.T @ Xc) / np.maximum(Mf.T @ Mf, 1.0); lam = 0.05 ** 2
    Xf = fill(X, mu, cov, lam); lines.append(f"input hours without an observation, filled from the other gauges: {100 * (~fin).mean():.1f}% in the training period")
    blocks = {"early": np.arange(len(ttr)) < (iv - i0), "val": np.arange(len(ttr)) >= (iv - i0), "ida": np.asarray((ttr >= IDA_OUT[0]) & (ttr < IDA_OUT[1]))}
    u = (((Xf - mu[None, :]) / np.nanstd(X, 0)[None, :]) ** 2).mean(1); w = u ** a.unusual_power; w = w / w.mean()          # hours in which the gauges are far from normal count more
    if a.unusual_power:
        lines.append(f"training hours weighted by how unusual the inputs are (power {a.unusual_power}): the 1% most unusual hours carry {100 * np.sort(w)[-len(w) // 100:].sum() / w.sum():.0f}% of the weight")
    SM = {b: [sums(Xf[m], Y[m, s], w[m]) for s in range(S)] for b, m in blocks.items()}
    add = lambda A, B, sg=1.0: tuple(x + sg * y for x, y in zip(A, B))
    val = {}                                                                # the error of the inputs that suits the validation year
    for nz in a.noise:
        e = []
        for s in range(S):
            if np.isfinite(Y[blocks["early"], s]).sum() < 2000:
                continue
            b, c0 = solve(SM["early"][s], nz); yy = Y[blocks["val"], s]; m = np.isfinite(yy)
            if m.sum() > 500:
                e.append(float(np.sqrt(np.mean((c0 + Xf[blocks["val"]][m] @ b - yy[m]) ** 2))))
        val[nz] = float(np.median(e))
    noise = min(val, key=val.get); lines.append("validation year (fit on the years before): median RMSE of the level per site, by assumed error of the inputs: " + ", ".join(f"{k} m: {v:.3f} m" for k, v in val.items()) + f"; used: {noise} m")
    ok = np.isfinite(Y).sum(0) >= 5000
    BF = np.zeros((P, S)); AF = np.zeros(S); BI = np.zeros((P, S)); AI = np.zeros(S)
    for s in np.where(ok)[0]:
        full = add(SM["early"][s], SM["val"][s]); BF[:, s], AF[s] = solve(full, noise); BI[:, s], AI[s] = solve(add(full, SM["ida"][s], -1.0), noise)
    np.savez(out / "coef.npz", coef_francine=BF, const_francine=AF, coef_ida=BI, const_ida=AI, input_source=np.array([k[0] for k in keys]), input_station=np.array([k[1] for k in keys]),
             site=cr.station_id.to_numpy(str), fitted=ok, noise=noise)
    print(f"fitted {int(ok.sum())} sites, {time.time() - t00:.0f} s", flush=True)

    # the test periods: inputs, predictions of the level at the sites
    def obs_marsh(times):
        g = d[(d.t >= times[0]) & (d.t <= times[-1])]
        om = g.pivot(index="t", columns="station", values="to_marsh").reindex(index=times, columns=cr.station_id).to_numpy(float)
        od = g.pivot(index="t", columns="station", values="to_datum").reindex(index=times, columns=cr.station_id).to_numpy(float)
        return om, od, np.nanmedian(od - om, 0)                              # depth on the marsh, level, surveyed marsh surface (NAVD88)

    fc_cols = [fcol[k] for k in keys]
    xin = {"Francine, inputs observed": OF[V][:, fc_cols], **{f"Francine, inputs forecast {L} h before": np.stack([F[V - L, L - 1, cc] for cc in fc_cols], 1) for L in (1, 3, 6)}}
    tI = pd.date_range(IDA[0], IDA[1], freq="h"); jI = tm.get_indexer(tI); xI = np.asarray(vals[rin][:, jI], np.float64).T
    with np.errstate(all="ignore"):
        omF, odF, gF = obs_marsh(tF); omI, odI, gI = obs_marsh(tI)
    calmF = np.asarray(tF < FR_CALM); stormF = np.asarray((tF >= FR_STORM[0]) & (tF < FR_STORM[1])); calmI = np.arange(len(tI)) < 72; stormI = np.asarray((tI >= IDA_STORM[0]) & (tI <= IDA_STORM[1]))
    lev = {k: AF[None, :] + fill(x, mu, cov, lam) @ BF for k, x in xin.items()}; levI = AI[None, :] + fill(xI, mu, cov, lam) @ BI

    lat, lon = cr.lat.to_numpy(float), cr.lon.to_numpy(float)              # between sites: the level from the nearest other sites
    dx = (lon[:, None] - lon[None, :]) * np.cos(np.deg2rad(29.7)) * 111.2; dy = (lat[:, None] - lat[None, :]) * 111.2; dist = np.hypot(dx, dy); dist[~ok, :] = np.inf; dist[:, ~ok] = np.inf; np.fill_diagonal(dist, np.inf)
    nb = np.argsort(dist, 1)[:, :a.neighbours]; wn = 1.0 / np.maximum(np.take_along_axis(dist, nb, 1), 0.1) ** 2; wn /= wn.sum(1, keepdims=True)
    near = lambda L: np.einsum("tsk,sk->ts", L[:, nb], wn)
    gs = pd.read_csv(a.grid_sites).drop_duplicates("station").set_index("station") if a.grid_sites else None
    ground = np.array([float(gs.ground_model_m.get(i, np.nan)) if gs is not None else np.nan for i in cr.station_id]); common = np.array([gs is not None and i in gs.index for i in cr.station_id])

    recs = []; ser = {"times_francine": np.array(tF.strftime("%Y-%m-%d %H:%M"), dtype=str), "times_ida": np.array(tI.strftime("%Y-%m-%d %H:%M"), dtype=str)}
    jobs = [(k, L, omF, odF, gF, calmF, stormF) for k, L in lev.items()] + [("Ida, inputs observed (the fit leaves this storm out)", levI, omI, odI, gI, calmI, stormI)]
    jobs += [("Francine, inputs observed, level from the nearest other sites", near(lev["Francine, inputs observed"]), omF, odF, gF, calmF, stormF),
             ("Francine, inputs forecast 6 h before, level from the nearest other sites", near(lev["Francine, inputs forecast 6 h before"]), omF, odF, gF, calmF, stormF),
             ("Francine, inputs observed, level from the nearest other sites, ground level of the grid", near(lev["Francine, inputs observed"]), omF, odF, ground, calmF, stormF)]
    for k, L, om, od, g, calm, storm in jobs:
        for s in np.where(ok)[0]:
            if not np.isfinite(g[s]):
                continue
            r = metrics(k, cr.iloc[s], om[:, s], L[:, s] - g[s], od[:, s], L[:, s], calm, storm, a.wet)
            if r:
                r.update({"in_grid_comparison": bool(common[s]), "marsh_surface_m": float(g[s]), "nearest_other_site_km": float(dist[s, nb[s, 0]])}); recs.append(r)
                if "Francine" in k and ("nearest" not in k or "grid" not in k):
                    ser[f"{k}|{cr.station_id[s]}"] = np.stack([om[:, s], L[:, s] - g[s]]).astype(np.float32)
    t = pd.DataFrame(recs); t.to_csv(out / "sites.csv", index=False); np.savez_compressed(out / "series.npz", **ser)
    pd.set_option("display.width", 250)
    for k, x in t.groupby("field", sort=False):
        lines.append(""); lines.append(f"{k}: {len(x)} sites; level: RMSE median per site {x.rmse_level_m.median():.2f} m; depth on the marsh, all hours: RMSE median per site {x.rmse_depth_m.median():.2f} m, mean error median {x.bias_depth_m.median():+.2f} m")
        for nm in ("calm", "storm"):
            y = x.dropna(subset=[f"{nm}_map_largest_depth_m"])
            if y.empty:
                continue
            of, mf = y[f"{nm}_observed_largest_depth_m"] > a.wet, y[f"{nm}_map_largest_depth_m"] > a.wet; pe = y[f"{nm}_map_largest_depth_m"] - y[f"{nm}_observed_largest_depth_m"]
            lines.append(f"  {nm} hours, {len(y)} sites: share of site hours flooded, observed {np.average(y[f'{nm}_observed_flooded_share'], weights=y[f'{nm}_hours']):.2f}, predicted {np.average(y[f'{nm}_map_flooded_share'], weights=y[f'{nm}_hours']):.2f}; "
                         f"sites flooded at some hour: observed {int(of.sum())}, predicted {int(mf.sum())}, both {int((of & mf).sum())}, predicted only {int((mf & ~of).sum())}, observed only {int((of & ~mf).sum())}; "
                         f"largest depth, predicted minus observed: mean {pe.mean():+.2f} m, RMS {np.sqrt((pe ** 2).mean()):.2f} m, median observed {y[f'{nm}_observed_largest_depth_m'].median():.2f} m, predicted {y[f'{nm}_map_largest_depth_m'].median():.2f} m, "
                         f"correlation {np.corrcoef(y[f'{nm}_observed_largest_depth_m'], y[f'{nm}_map_largest_depth_m'])[0, 1]:.2f}; RMSE of the depth in these hours, median per site {y[f'{nm}_rmse_depth_m'].median():.2f} m")
        if "storm_map_largest_depth_m" in x:
            y = x.dropna(subset=["storm_map_largest_depth_m"]); y = y.assign(band=pd.cut(y.lon, BANDS))
            g_ = y.groupby("band", observed=True).agg(sites=("station", "size"), observed=("storm_observed_largest_depth_m", "median"), predicted=("storm_map_largest_depth_m", "median"))
            lines.append("  largest depth in the storm hours by longitude (median): " + "; ".join(f"{b}: {int(r_.sites)} sites, observed {r_.observed:.2f}, predicted {r_.predicted:.2f}" for b, r_ in g_.iterrows()))
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print(f"-> {out}, {time.time() - t00:.0f} s")


if __name__ == "__main__":
    main()
