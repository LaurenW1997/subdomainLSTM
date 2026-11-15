"""Would the water level of OTHER stations help the 6 h forecast of a station? A test without new training.

1. similarity   the model already has a 16-number description of every station (the station embedding). For every station:
                the types of its nearest stations in that description, against chance. Per model, averaged over the models.
2. lead         from the observations of the training period, for every pair of stations within --max-km: the correlation
                between the change of station B over the last 3 h and the change of station A over the next 6 h.
3. value        the error that is left in the 6 h forecast of the model (mean of the members of --run) is fitted with a
                linear model on the recent changes (last 1, 3, 6 h) of
                  own       the station itself                    (control: the model has these already)
                  partners  own + up to --k partner stations      (nearest and highest lead correlation, real-time stations)
                per station, fitted on two of the years 2023 / 2024 / 2025 and applied to the third (validation year 2023 is
                only used for fitting). The RMSE of the test years with and without the fitted part says how much of the
                error other stations can explain linearly. partners minus own = what sharing adds.
Test origins at 00/06/12/18 UTC, stations with real-time data (no CRMS). RMSE in cm.
Output: <out>/sharing_station.csv (per station), <out>/sharing_pairs.csv (partners), printed tables
Usage : python station_sharing.py --run RUNS/v15r_mean5 --dataset DATA/dataset_v6 --out OUT
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HORIZON, to_torch  # noqa: E402
from station_compare import load  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TYPES = [("tide gauge", "Tide gauges"), ("estuary / tidal channel", "Estuaries"), ("lake", "Lakes"), ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks")]
MAXLAG = 8
LAGS = (1, 3, 6)


def km(lat, lon, la, lo):
    p = np.pi / 180
    a = np.sin((la - lat) * p / 2) ** 2 + np.cos(lat * p) * np.cos(la * p) * np.sin((lo - lon) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


def ridge_fit(X, y, alpha):
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + alpha * len(y) * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return mu, sd, w, y.mean()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--test-end", default="2025-12-31T17"); ap.add_argument("--stride", type=int, default=6); ap.add_argument("--batch", type=int, default=4096)
    ap.add_argument("--max-km", type=float, default=100.0); ap.add_argument("--k", type=int, default=6); ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--event-q", type=float, default=0.99); ap.add_argument("--rise-q", type=float, default=0.95)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(32)
    run = Path(a.run)
    sm, model = load(run, Path(a.dataset), device)
    st = sm.stations.reset_index(drop=True)
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    typ = st[["source", "station_id"]].astype(str).merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left").type.fillna("other").to_numpy()
    oper = (st.source != "CRMS").to_numpy(); rows = np.where(oper)[0]
    lat, lon = st.lat.to_numpy(float), st.lon.to_numpy(float)
    std = 100 * st.std_m.to_numpy(np.float64)

    # ---- 1. similarity in the station embedding
    cks = [run / "best.pt"] + sorted(run.glob("member_*.pt"))
    same, near_km = np.zeros(sm.S), np.zeros(sm.S)
    for p in cks:
        E = torch.load(p, map_location="cpu")["state_dict"]["emb.weight"].numpy()[rows]
        E = (E - E.mean(0)) / np.linalg.norm(E - E.mean(0), axis=1, keepdims=True)
        C = E @ E.T; np.fill_diagonal(C, -9)
        nn5 = np.argsort(-C, 1)[:, :5]
        same[rows] += (typ[rows][nn5] == typ[rows][:, None]).mean(1) / len(cks)
        near_km[rows] += np.array([np.median(km(lat[rows[i]], lon[rows[i]], lat[rows[nn5[i]]], lon[rows[nn5[i]]])) for i in range(len(rows))]) / len(cks)
    share = pd.Series(typ[rows]).value_counts(normalize=True)
    print(f"=== 1. station embedding ({len(cks)} models): of the 5 most similar stations, the share of the same type   (chance = share of that type among the {len(rows)} stations)")
    for t, tl in TYPES:
        m = typ[rows] == t
        print(f"  {tl:14s} {int(m.sum()):4d}   same type {same[rows][m].mean():.2f}   chance {share.get(t, 0):.2f}   median distance to them {np.median(near_km[rows][m]):.0f} km", flush=True)

    # ---- 2. lead correlation from the observations of the training period
    x = sm.norm[:, :sm.t_train_end]
    d3 = np.full_like(x, np.nan); d3[:, 3:] = x[:, 3:] - x[:, :-3]                       # change over the last 3 h
    f6 = np.full_like(x, np.nan); f6[:, :-HORIZON] = x[:, HORIZON:] - x[:, :-HORIZON]     # change over the next 6 h
    pairs = []
    partners = {}
    for s in rows:
        d = km(lat[s], lon[s], lat[rows], lon[rows])
        cand = rows[(d <= a.max_km) & (rows != s)]; dc = d[(d <= a.max_km) & (rows != s)]
        y = f6[s]
        def corr(u):
            ok = np.isfinite(u) & np.isfinite(y)[None, :]
            n = ok.sum(1)
            uu = np.where(ok, u, 0); yy = np.where(ok, y[None, :], 0)
            mu, my = uu.sum(1) / np.maximum(n, 1), yy.sum(1) / np.maximum(n, 1)
            cov = (uu * yy).sum(1) / np.maximum(n, 1) - mu * my
            vu = (uu ** 2).sum(1) / np.maximum(n, 1) - mu ** 2; vy = (yy ** 2).sum(1) / np.maximum(n, 1) - my ** 2
            return np.where(n >= 5000, cov / np.sqrt(np.maximum(vu * vy, 1e-12)), np.nan)
        own = float(corr(d3[s][None, :])[0])
        c = corr(d3[cand]) if len(cand) else np.array([])
        for j, cc, dd in zip(cand, c, dc):
            pairs.append((s, j, dd, cc, own))
        # partners for the value test: the nearest and the highest |lead correlation|, alternating, up to k
        byd = list(cand[np.argsort(dc)]); byc = list(cand[np.argsort(-np.abs(np.nan_to_num(c)))])
        pick = []
        while (byd or byc) and len(pick) < a.k:
            for lst in (byc, byd):
                while lst and lst[0] in pick:
                    lst.pop(0)
                if lst and len(pick) < a.k:
                    pick.append(lst.pop(0))
        partners[s] = pick
    P = pd.DataFrame(pairs, columns=["row", "partner_row", "km", "lead_corr", "own_corr"])
    for c in ("row", "partner_row"):
        P[c.replace("row", "id")] = (st.source + ":" + st.station_id.astype(str)).to_numpy()[P[c]]; P[c.replace("row", "type")] = typ[P[c]]
    P.round(4).to_csv(out / "sharing_pairs.csv", index=False)
    best = P.loc[P.groupby("row").lead_corr.apply(lambda v: v.abs().idxmax() if v.notna().any() else v.index[0])]
    print(f"\n=== 2. training period: correlation of the change over the next 6 h with the change over the last 3 h   (pairs within {a.max_km:.0f} km)")
    print("  type            n   own station | best other station | stations where another station beats the own | that station is of another type | its median distance")
    for t, tl in TYPES:
        b = best[best.type == t]
        if len(b):
            win = b.lead_corr.abs() > b.own_corr.abs()
            print(f"  {tl:14s} {len(b):4d}   {b.own_corr.median():+.2f}       | {b.lead_corr.median():+.2f}              | {int(win.sum()):4d}"
                  f"                                        | {float((b.partner_type != b.type).mean()):.2f}                            | {b.km.median():.0f} km", flush=True)
    del d3, f6

    # ---- 3. value: fit the remaining 6 h error on recent changes of other stations
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))
    S, T0 = [], []
    for split in ("val", "test"):
        lo = sm.split_range(split)[0]
        s_, t_ = sm.eval_origins(split, a.stride, t_lo=-(-lo // a.stride) * a.stride, t_hi=t_hi)
        S.append(s_); T0.append(t_)
    S, T0 = np.concatenate(S), np.concatenate(T0)
    k = oper[S]; S, T0 = S[k], T0[k]
    n = len(S)
    p6 = np.zeros(n, np.float32)
    with torch.no_grad():
        for i in range(0, n, a.batch):
            feats, fut, s, yy, mm = sm.window(S[i:i + a.batch], T0[i:i + a.batch])
            f, fu, sx, _, _ = to_torch((feats, fut, s, yy, mm), device)
            p6[i:i + a.batch] = model(f, sx, fu)[:, -1].cpu().numpy()
    y6 = sm.norm[S, T0 + HORIZON]; last = sm.norm[S, T0]
    err = (p6 - y6) * std[S]                                                            # cm, NaN where the 6 h value is missing
    year = sm.time.year.to_numpy()[T0]
    is_test = T0 >= sm.t_val_end
    print(f"\n{n} forecasts at {len(np.unique(S))} stations (validation year {int((~is_test).sum())}, test years {int(is_test.sum())})", flush=True)

    # recent changes in units of the typical 6 h change of that station (training period); missing -> 0
    d6s = np.full(sm.S, np.nan)
    with np.errstate(all="ignore"):
        d6s[rows] = np.nanstd(x[rows][:, HORIZON:] - x[rows][:, :-HORIZON], axis=1)
    def recent(j, t0):            # [len, 3] changes of station j over the last 1, 3, 6 h before t0, and whether its newest hour exists
        v = np.stack([sm.norm[j, t0] - sm.norm[j, t0 - L] for L in LAGS], 1) / d6s[j]
        return np.nan_to_num(np.clip(v, -20, 20)), np.isfinite(sm.norm[j, t0]).astype(float)[:, None]

    thr_ev, thr_rise = np.full(sm.S, np.inf), np.full(sm.S, np.inf)
    for s in rows:
        d = np.abs(x[s, HORIZON:] - x[s, :-HORIZON]); d = d[np.isfinite(d)]
        if len(d) >= 1000:
            thr_ev[s], thr_rise[s] = np.quantile(d, a.event_q), np.quantile(d, a.rise_q)
    d6 = y6 - last
    event = np.abs(d6) >= thr_ev[S]
    obs_lag = np.stack([sm.norm[S, T0 + HORIZON - kk] for kk in range(MAXLAG + 1)], 1)
    timing = (d6 >= thr_rise[S]) & np.isfinite(obs_lag).all(1)

    fit = {"own": np.zeros(n), "partners": np.zeros(n)}                                 # fitted part of the error, cm
    order = np.argsort(S, kind="stable"); bounds = np.searchsorted(S[order], np.arange(sm.S + 1))
    for s in rows:
        i = order[bounds[s]:bounds[s + 1]]
        if len(i) < 500:
            continue
        own, _ = recent(s, T0[i])
        parts = [own]
        for j in partners[s]:
            v, m = recent(j, T0[i]); parts += [v, m]
        X = {"own": own, "partners": np.concatenate(parts, 1)}
        ok = np.isfinite(err[i])
        for yr in (2024, 2025):                                                         # fit on the other two years, apply to this one
            tr, te = ok & (year[i] != yr), year[i] == yr
            if tr.sum() < 300 or not te.any():
                continue
            for name, XX in X.items():
                mu, sd, w, b = ridge_fit(XX[tr], err[i][tr], a.alpha)
                fit[name][i[te]] = ((XX[te] - mu) / sd) @ w + b

    res = []
    for s in rows:
        i = order[bounds[s]:bounds[s + 1]]; i = i[is_test[i] & np.isfinite(err[i])]
        if len(i) < 720:
            continue
        r = {"source": st.source[s], "station_id": st.station_id[s], "name": st.name[s], "type": typ[s], "n": len(i), "n_event": int(event[i].sum()),
             "n_partners": len(partners[s]), "partners": " | ".join((st.source + ":" + st.station_id.astype(str)).to_numpy()[partners[s]])}
        for name, e in (("model", err[i]), ("own", err[i] - fit["own"][i]), ("partners", err[i] - fit["partners"][i])):
            r[f"sse_{name}"] = float((e ** 2).sum()); r[f"sse_event_{name}"] = float((e[event[i]] ** 2).sum())
            r[f"rmse_{name}_cm"] = float(np.sqrt((e ** 2).mean()))
        # timing of the rises with and without the fitted part
        it = order[bounds[s]:bounds[s + 1]]; it = it[is_test[it] & timing[it]]
        r["n_timing"] = len(it)
        for name, c in (("model", 0), ("partners", fit["partners"][it])):
            pp = p6[it].astype(np.float64) - np.asarray(c) / std[s]
            r[f"lag_{name}_h"] = float(np.argmin(((pp[:, None] - obs_lag[it]) ** 2).sum(0))) if len(it) >= 10 else np.nan
        res.append(r)
    R = pd.DataFrame(res)
    R.round(4).to_csv(out / "sharing_station.csv", index=False)

    def line(lab, d):
        pool = lambda c, nn: float(np.sqrt(d[c].sum() / d[nn].sum()))
        m, o, p = pool("sse_model", "n"), pool("sse_own", "n"), pool("sse_partners", "n")
        em, eo, ep = pool("sse_event_model", "n_event"), pool("sse_event_own", "n_event"), pool("sse_event_partners", "n_event")
        ch = d.rmse_partners_cm / d.rmse_own_cm - 1
        print(f"  {lab:28s} {len(d):4d}   all {m:6.2f} -> own {o:6.2f} -> partners {p:6.2f} ({100 * (p / o - 1):+.1f}%)   largest changes {em:6.2f} -> {eo:6.2f} -> {ep:6.2f} ({100 * (ep / eo - 1):+.1f}%)"
              f"   stations better by > 5%: {int((ch < -0.05).sum())}, worse by > 5%: {int((ch > 0.05).sum())}   lag {d.lag_model_h.mean():.2f} -> {d.lag_partners_h.mean():.2f} h", flush=True)
    print(f"\n=== 3. 6 h RMSE (cm) of the test years: model -> minus a linear fit on the station's own recent changes -> minus a fit on own + partner stations   (% = partners against own)")
    line("all stations", R)
    for t, tl in TYPES:
        line(tl, R[R.type == t])
    nm = pd.read_csv(REPO / "config" / "station_downstream_map.csv", dtype=str).fillna("")
    has_us = set(zip(nm.source[nm.us_station_id != ""], nm.station_id[nm.us_station_id != ""]))
    up = np.array([(a_, str(b_)) in has_us for a_, b_ in zip(R.source, R.station_id)])
    line("with a gauge upstream", R[up]); line("without", R[~up])
    R["change"] = R.rmse_partners_cm / R.rmse_own_cm - 1
    print("\n  stations where the partners explain most:")
    for _, r in R.sort_values("change").head(15).iterrows():
        print(f"    {r.source}:{r.station_id:14s} {str(r['name'])[:44]:44s} {r.type[:12]:12s} {r.rmse_own_cm:6.2f} -> {r.rmse_partners_cm:6.2f} ({100 * r.change:+.0f}%)")


if __name__ == "__main__":
    main()
