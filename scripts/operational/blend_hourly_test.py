"""Does combining the forecasts of neighbouring forecast times lower the RMSE?  (test on past forecast times, a forecast from every hour)

The line of a lead time in the station figures is jagged because every point is a separate forecast. This script combines,
at forecast time t and for lead L (valid hour v = t + L), only what exists at time t:

  new          the forecast issued at t                                              f_t(L)
  mean2/mean3  mean with the forecasts for the same hour issued 1 (and 2) h earlier  f_t-1(L+1), f_t-2(L+2)        L <= 5 / 4
  anchor2/3    the same, the older forecasts first moved to the newest observation   obs(t) + f_t-j(L+j) - f_t-j(j)  L <= 5 / 4
  change2/3    newest observation + mean of the changes forecast at t, t-1 (, t-2)   obs(t) + mean_j [f_t-j(L) - obs(t-j)]

obs(t) is the last observation the forecast run itself had (forecast.csv), so nothing later than the forecast time is used.
Every method of a lead is scored on the same forecasts: forecast times t, t-1, t-2 all present, observation at the valid hour.
Output: <out>/blend_rmse.csv     model, subset, method, lead, n, rmse_cm
        <out>/blend_station.csv  model, source, station_id, behaviour, lead, n, rmse_cm of every method (stations with >= 24 forecasts)
Usage : python blend_hourly_test.py --dirs run=DIR partners=DIR --levels FILE --behaviour config/station_behaviour.csv --out OUT
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forecast import HORIZON, despike_readings, to_hourly  # noqa: E402

K = ["source", "station_id"]
METHODS = ["new", "mean2", "mean3", "anchor2", "anchor3", "change2", "change3"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--behaviour"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dirs = dict(x.split("=", 1) for x in a.dirs); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cyc = sorted(set.intersection(*[{p.name for p in Path(d).iterdir() if (p / "forecast.csv").exists()} for d in dirs.values()]))
    T = pd.DatetimeIndex([pd.Timestamp(c) for c in cyc])
    assert (np.diff(T.values) == np.timedelta64(1, "h")).all(), "forecast times must be consecutive hours"
    raw = {}
    for lab, d in dirs.items():
        x = pd.concat([pd.read_csv(Path(d) / c / "forecast.csv", dtype={"station_id": str}, parse_dates=["cycle_utc", "last_obs_utc"]) for c in cyc], ignore_index=True)
        raw[lab] = x[x.status == "ok"]
    st = sorted(set.intersection(*[set(map(tuple, x[K].drop_duplicates().values)) for x in raw.values()]))
    si = {k: i for i, k in enumerate(st)}; ti = {t: i for i, t in enumerate(T)}
    nS, nT = len(st), len(T)
    F, O0 = {}, {}
    for lab, x in raw.items():
        f = np.full((nS, nT, HORIZON + 1), np.nan); o = np.full((nS, nT), np.nan)       # f[..., 0] is not used
        s = np.array([si[k] for k in map(tuple, x[K].values)]); t = np.array([ti[v] for v in x.cycle_utc])
        for h in range(1, HORIZON + 1):
            f[s, t, h] = x[f"fcst_{h}h_m"].values
        o[s, t] = np.where((x.last_obs_utc == x.cycle_utc).values, x.last_obs_m.values, np.nan)      # only when the newest hour was there
        F[lab], O0[lab] = f, o
    hours = pd.date_range(T[0], T[-1] + pd.Timedelta(hours=HORIZON), freq="h")
    lv = pd.read_pickle(a.levels)
    OBS = np.stack([to_hourly(despike_readings(lv[k])[0]).reindex(hours).values if k in lv else np.full(len(hours), np.nan) for k in st])
    beh = None
    if a.behaviour:
        b = pd.read_csv(a.behaviour, dtype={"station_id": str}).set_index(K).behaviour
        beh = np.array([b.get(k, "") for k in st])

    def lag(x, j):          # x[s, t] -> value at forecast time t - j
        y = np.full_like(x, np.nan); y[:, j:] = x[:, :-j] if j else x
        return y

    rows, srows = [], []
    for lab in dirs:
        f, o = F[lab], O0[lab]
        base = np.isfinite(o) & np.isfinite(lag(o, 1)) & np.isfinite(lag(o, 2))
        for j in (0, 1, 2):
            base &= np.isfinite(lag(f[:, :, 1:].sum(2), j))
        for L in range(1, HORIZON + 1):
            truth = np.full((nS, nT), np.nan); truth[:, :] = OBS[:, L:L + nT]
            P = {"new": f[:, :, L]}
            if L + 1 <= HORIZON:
                P["mean2"] = (f[:, :, L] + lag(f[:, :, L + 1], 1)) / 2
                P["anchor2"] = (f[:, :, L] + o + lag(f[:, :, L + 1] - f[:, :, 1], 1)) / 2
            if L + 2 <= HORIZON:
                P["mean3"] = (f[:, :, L] + lag(f[:, :, L + 1], 1) + lag(f[:, :, L + 2], 2)) / 3
                P["anchor3"] = (f[:, :, L] + o + lag(f[:, :, L + 1] - f[:, :, 1], 1) + o + lag(f[:, :, L + 2] - f[:, :, 2], 2)) / 3
            ch = f[:, :, L] - o
            P["change2"] = o + (ch + lag(ch, 1)) / 2
            P["change3"] = o + (ch + lag(ch, 1) + lag(ch, 2)) / 3
            ok = base & np.isfinite(truth)
            trained = np.broadcast_to((T.hour % 6 == 0)[None, :], ok.shape)
            subsets = {"all forecast times": ok, "forecast times 00 06 12 18 UTC": ok & trained}
            if beh is not None:
                for c in ("tidal", "weakly tidal", "no tide"):
                    subsets[c] = ok & (beh == c)[:, None]
            for sub, m in subsets.items():
                for name, p in P.items():
                    rows.append({"model": lab, "subset": sub, "method": name, "lead": L, "n": int(m.sum()), "rmse_cm": round(float(100 * np.sqrt(((p - truth)[m] ** 2).mean())), 3)})
            n = ok.sum(1)
            e = {name: 100 * np.sqrt(np.where(ok, (p - truth) ** 2, 0.0).sum(1) / np.maximum(n, 1)) for name, p in P.items()}
            for i in np.where(n >= 24)[0]:
                srows.append({"model": lab, "source": st[i][0], "station_id": st[i][1], "behaviour": beh[i] if beh is not None else "", "lead": L, "n": int(n[i]),
                              **{name: round(float(v[i]), 3) for name, v in e.items()}})
    r = pd.DataFrame(rows); r.to_csv(out / "blend_rmse.csv", index=False)
    sr = pd.DataFrame(srows); sr.to_csv(out / "blend_station.csv", index=False)
    print(f"{nT} forecast times {cyc[0]} .. {cyc[-1]}, {nS} stations")
    for (lab, sub), g in r.groupby(["model", "subset"], sort=False):
        print(f"\n== {lab} | {sub} | forecasts per lead: {int(g.n.max())}")
        print(g.pivot(index="method", columns="lead", values="rmse_cm").reindex(METHODS).to_string(na_rep="  -"))
    print()
    print("stations where a method has a lower RMSE than the newest forecast (in brackets: lower by more than 0.5 cm), of", sr[K].drop_duplicates().shape[0])
    for lab in dirs:
        for L in (1, 3, 6):
            g = sr[(sr.model == lab) & (sr.lead == L)]
            print(f"  {lab}, {L} h: " + ", ".join(f"{m} {int((g[m] < g.new).sum())} ({int((g[m] < g.new - 0.5).sum())})" for m in METHODS[1:] if m in g and g[m].notna().any()))
    print("->", out / "blend_rmse.csv", out / "blend_station.csv")


if __name__ == "__main__":
    main()
