"""Compare groups of models (each group: the same settings trained with several random seeds) from eval_protocol.py output.

For every group: the mean of its members and the range of the single members, for the RMSE over all forecasts, the RMSE
of the forecasts with the largest observed 6 h changes, the hurricane periods, and the timing of the rises.
For every group against the reference group (mean against mean, the same stations): the difference with a 95% interval
from resampling the stations, the station-by-station picture (median change, stations better / worse, Wilcoxon signed-rank
test, effect size), and the range of the difference over all pairs of single members (the seed noise of the comparison).
Input : runs/protocol_<name>/protocol_station.csv
Output: printed tables; --csv FILE (one row per group and quantity)
Usage : python protocol_summary.py --groups "label=name" ... --ref label [--csv deliverables/25_....csv]
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
REPO = Path(__file__).resolve().parents[2]
TYPES = [("tide gauge", "Tide gauges"), ("estuary / tidal channel", "Estuaries"), ("lake", "Lakes"), ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks")]
MAXLAG = 8
# quantity -> (label, RMSE column, column with the number of forecasts)
POOLED = {"all_1h": ("all forecasts, 1 h", "rmse_1h_cm", "n_6h"), "all_3h": ("all forecasts, 3 h", "rmse_3h_cm", "n_6h"), "all_6h": ("all forecasts, 6 h", "rmse_6h_cm", "n_6h"),
          "event_6h": ("largest 6 h changes, 6 h", "rmse_event_6h_cm", "n_event"), "rise_6h": ("  of these: rises", "rmse_rise_6h_cm", "n_rise"),
          "fall_6h": ("  of these: falls", "rmse_fall_6h_cm", "n_fall"), "storm_6h": ("hurricane periods, 6 h", "rmse_storm_6h_cm", "n_storm")}


def pooled(x: pd.DataFrame, col: str, ncol: str) -> float:
    w = x[ncol].to_numpy(float); v = np.nan_to_num(x[col].to_numpy(float))
    return float(np.sqrt((w * v ** 2).sum() / w.sum()))


def lag_mean(x: pd.DataFrame) -> float:
    return float(x.lag_h[x.n_timing >= 10].mean())


def rise_share(x: pd.DataFrame) -> float:
    w = x.n_timing.to_numpy(float)
    return float(np.nansum(w * x.rise_fc_cm) / np.nansum(w * x.rise_obs_cm))


def quantities(x: pd.DataFrame) -> dict[str, float]:
    q = {k: pooled(x, c, n) for k, (_, c, n) in POOLED.items()}
    q["lag_h"] = lag_mean(x); q["rise_share"] = rise_share(x)
    return q


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="+", required=True, help="label=name of runs/protocol_<name>"); ap.add_argument("--ref", required=True)
    ap.add_argument("--csv"); ap.add_argument("--boot", type=int, default=2000); ap.add_argument("--min-n", type=int, default=720)
    a = ap.parse_args()
    G = {}
    for spec in a.groups:
        lab, name = spec.split("=")
        G[lab] = pd.read_csv(REPO / "runs" / f"protocol_{name}" / "protocol_station.csv", dtype={"station_id": str})
    # the same stations in every group: enough forecasts in the mean of every group
    key = lambda d: d.source + ":" + d.station_id
    ok = None
    for d in G.values():
        m = d[d.model == "mean"]; k = set(key(m)[m.n_6h >= a.min_n])
        ok = k if ok is None else ok & k
    M = {}
    for lab, d in G.items():
        d = d[key(d).isin(ok)]
        M[lab] = {m: x.sort_values(["source", "station_id"]).reset_index(drop=True) for m, x in d.groupby("model", sort=False)}
    ref = M[a.ref]["mean"]; n_st = len(ref)
    print(f"{n_st} stations with real-time data; forecasts: all {int(ref.n_6h.sum()):,}, largest 6 h changes {int(ref.n_event.sum()):,} "
          f"(rises {int(ref.n_rise.sum()):,}, falls {int(ref.n_fall.sum()):,}), hurricane periods {int(ref.n_storm.sum()):,} at {int((ref.n_storm > 0).sum())} stations, "
          f"rises used for the timing {int(ref.n_timing.sum()):,} at {int((ref.n_timing >= 10).sum())} stations")

    rows = []
    print("\n=== every group: mean of its members [range of the single members]   (RMSE cm; lag h; share of the observed rise that is forecast)")
    for lab, mm in M.items():
        qm = quantities(mm["mean"]); qs = [quantities(x) for m, x in mm.items() if m != "mean"]
        print(f"\n{lab}   ({len(qs)} members)")
        for k in list(POOLED) + ["lag_h", "rise_share"]:
            name = POOLED[k][0] if k in POOLED else {"lag_h": "lag of the 6 h forecast on the rises (h)", "rise_share": "share of the observed 6 h rise that is forecast"}[k]
            lo, hi = min(q[k] for q in qs), max(q[k] for q in qs)
            print(f"  {name:48s} {qm[k]:7.2f}   [{lo:6.2f} - {hi:6.2f}]")
            rows.append({"group": lab, "quantity": k, "mean_of_members": round(qm[k], 3), "member_min": round(lo, 3), "member_max": round(hi, 3)})
        print("  by station type:  n   median station 6 h | largest changes 6 h | hurricanes 6 h | lag h")
        for t, tl in TYPES:
            x = mm["mean"][mm["mean"].type == t]
            print(f"    {tl:14s} {len(x):4d}   {x.rmse_6h_cm.median():6.2f}            | {pooled(x, 'rmse_event_6h_cm', 'n_event'):6.2f}              | {pooled(x, 'rmse_storm_6h_cm', 'n_storm'):6.2f}         | {lag_mean(x):.2f}")
            rows.append({"group": lab, "quantity": f"type:{t}", "median_station_6h_cm": round(float(x.rmse_6h_cm.median()), 3),
                         "event_6h_cm": round(pooled(x, "rmse_event_6h_cm", "n_event"), 3), "storm_6h_cm": round(pooled(x, "rmse_storm_6h_cm", "n_storm"), 3), "lag_h": round(lag_mean(x), 3)})

    rng = np.random.default_rng(0)
    print(f"\n=== every group against: {a.ref}   (difference = group - reference; negative = better)")
    for lab, mm in M.items():
        if lab == a.ref:
            continue
        A, B = M[a.ref]["mean"], mm["mean"]
        assert (A.station_id.to_numpy() == B.station_id.to_numpy()).all()
        print(f"\n{lab}")
        idx = rng.integers(0, n_st, (a.boot, n_st))
        for k in list(POOLED) + ["lag_h"]:
            f = (lambda x: pooled(x, POOLED[k][1], POOLED[k][2])) if k in POOLED else lag_mean
            d0 = f(B) - f(A)
            bs = np.array([f(B.iloc[i]) - f(A.iloc[i]) for i in idx[:a.boot if k in ("all_6h", "event_6h", "storm_6h", "lag_h") else 0]])
            pairs = [f(y) - f(x) for mx, x in M[a.ref].items() if mx != "mean" for my, y in mm.items() if my != "mean"]
            name = POOLED[k][0] if k in POOLED else "lag on the rises (h)"
            ci = f"   95% interval [{np.percentile(bs, 2.5):+.2f}, {np.percentile(bs, 97.5):+.2f}]" if len(bs) else ""
            print(f"  {name:28s} {f(A):6.2f} -> {f(B):6.2f}   {d0:+.2f} ({100 * d0 / f(A):+.1f}%){ci}   single members, all pairs [{min(pairs):+.2f}, {max(pairs):+.2f}]")
            rows.append({"group": lab, "quantity": f"diff:{k}", "reference": round(f(A), 3), "mean_of_members": round(f(B), 3), "diff": round(d0, 3),
                         "ci_lo": round(float(np.percentile(bs, 2.5)), 3) if len(bs) else np.nan, "ci_hi": round(float(np.percentile(bs, 97.5)), 3) if len(bs) else np.nan,
                         "pairs_min": round(min(pairs), 3), "pairs_max": round(max(pairs), 3)})
        dd = B.rmse_6h_cm.to_numpy() - A.rmse_6h_cm.to_numpy()
        p = wilcoxon(dd).pvalue
        print(f"  station by station, 6 h: median change {np.median(dd):+.2f} cm; better at {int((dd < 0).sum())}, worse at {int((dd > 0).sum())} of {n_st}; "
              f"by more than 0.5 cm: {int((dd < -0.5).sum())} better, {int((dd > 0.5).sum())} worse; Wilcoxon p = {p:.1e}; effect size (mean / sd of the change) {dd.mean() / dd.std(ddof=1):+.2f}")
        for t, tl in TYPES:
            m = (A.type == t).to_numpy()
            print(f"    {tl:14s} median station {np.median(A.rmse_6h_cm[m]):6.2f} -> {np.median(B.rmse_6h_cm[m]):6.2f}   worse at {int((dd[m] > 0).sum())} of {int(m.sum())}")
        rows.append({"group": lab, "quantity": "stations_6h", "median_change_cm": round(float(np.median(dd)), 3), "better": int((dd < 0).sum()), "worse": int((dd > 0).sum()),
                     "better_05": int((dd < -0.5).sum()), "worse_05": int((dd > 0.5).sum()), "wilcoxon_p": p, "effect_size": round(float(dd.mean() / dd.std(ddof=1)), 3)})
    if a.csv:
        pd.DataFrame(rows).to_csv(REPO / a.csv, index=False); print("\n->", a.csv)


if __name__ == "__main__":
    main()
