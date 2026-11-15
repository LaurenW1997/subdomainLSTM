"""Where partner-station input helps and where it hurts: two groups of models from eval_protocol.py, station by station.

Both groups: mean of the members, stations with real-time data (n_6h >= --min-n). The stations are grouped by
  type of the station; type and distance of its first partner; number of its partners that are rivers / creeks farther
  than --far-km; whether the station has an upstream gauge in config/station_downstream_map.csv; whether the linear
  diagnostic (station_sharing.py) found it more than 5% better.
"clearly better / worse": every single member of the new group is better / worse than every single member of the reference.
Input : runs/protocol_<ref>/protocol_station.csv, runs/protocol_<new>/protocol_station.csv, config/station_partners.csv
Output: printed tables; runs/protocol_<new>/partner_station_compare.csv (one row per station)
Usage : python partner_compare.py --ref hrrr_total --new partners4 [--map config/station_partners.csv --far-km 50]
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
REPO = Path(__file__).resolve().parents[2]
K = ["source", "station_id"]
TIDAL = {"tide gauge", "estuary / tidal channel", "lake", "marsh"}


def pool(x: pd.DataFrame, col: str, n: str) -> float:
    w = x[n].to_numpy(float); v = np.nan_to_num(x[col].to_numpy(float))
    return float(np.sqrt((w * v ** 2).sum() / max(w.sum(), 1)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True); ap.add_argument("--new", required=True)
    ap.add_argument("--map", default=str(REPO / "config" / "station_partners.csv")); ap.add_argument("--far-km", type=float, default=50.0)
    ap.add_argument("--min-n", type=int, default=720)
    a_ = ap.parse_args()
    A = pd.read_csv(REPO / "runs" / f"protocol_{a_.ref}" / "protocol_station.csv", dtype={"station_id": str})
    B = pd.read_csv(REPO / "runs" / f"protocol_{a_.new}" / "protocol_station.csv", dtype={"station_id": str})
    a = A[A.model == "mean"].set_index(K); a = a[a.n_6h >= a_.min_n]
    b = B[B.model == "mean"].set_index(K).loc[a.index]
    assert (a.n_6h == b.n_6h).all(), "the two groups were not evaluated on the same forecasts"
    pm = pd.read_csv(a_.map, dtype=str).fillna("").set_index(K).loc[a.index]
    k = sum(c.endswith("_km") for c in pm.columns)
    km = pd.DataFrame({j: pd.to_numeric(pm[f"p{j}_km"], errors="coerce") for j in range(1, k + 1)})
    typ = pd.DataFrame({j: pm[f"p{j}_type"] for j in range(1, k + 1)})
    n_p = pm.n_partners.astype(int)
    far = ((~typ.isin(TIDAL)) & (typ != "") & (km > a_.far_km)).sum(1)          # partners that are rivers / creeks far away

    def row(lab: str, m: pd.Series) -> None:
        xa, xb = a[m], b[m]
        if not len(xa):
            return
        q = lambda c, n: (pool(xa, c, n), pool(xb, c, n))
        r6, ev, hu = q("rmse_6h_cm", "n_6h"), q("rmse_event_6h_cm", "n_event"), q("rmse_storm_6h_cm", "n_storm")
        lag = (xa.lag_h[xa.n_timing >= 10].mean(), xb.lag_h[xb.n_timing >= 10].mean())
        print(f"  {lab:46s} {len(xa):4d}   {r6[0]:6.2f} -> {r6[1]:6.2f} ({100 * (r6[1] / r6[0] - 1):+5.1f}%)   {ev[0]:6.1f} -> {ev[1]:6.1f}   {hu[0]:5.1f} -> {hu[1]:5.1f}   "
              f"{lag[0]:.2f} -> {lag[1]:.2f}   {int((xb.rmse_6h_cm < 0.95 * xa.rmse_6h_cm).sum()):4d} / {int((xb.rmse_6h_cm > 1.05 * xa.rmse_6h_cm).sum()):3d}")

    def head(t: str) -> None:
        print(f"\n{t}\n  {'':46s}    n   6 h RMSE, all forecasts (cm)   largest changes     hurricanes      lag (h)      stations better / worse by more than 5%")

    T = pd.Series(True, index=a.index); has = n_p > 0; p1_tidal = typ[1].isin(TIDAL); st_tidal = a.type.isin(TIDAL)
    head("by type of the station"); row("all", T)
    for t in ["tide gauge", "estuary / tidal channel", "lake", "marsh", "river / canal", "urban creek (Houston)"]:
        row(t, a.type == t)
    head("by the station and its first partner")
    row("tide gauge / estuary / lake / marsh", st_tidal)
    row("river or creek, first partner tidal or lake", ~st_tidal & has & p1_tidal)
    for lo, hi in [(0, 25), (25, 50), (50, 1e9)]:
        row(f"river or creek, first partner river/creek {lo}-{hi if hi < 1e8 else ''} km", ~st_tidal & has & ~p1_tidal & (km[1] >= lo) & (km[1] < hi))
    row("no partner", ~has)
    head(f"by the number of partners that are rivers / creeks farther than {a_.far_km:.0f} km")
    for i in range(k + 1):
        row(f"{i}", far == i)
    dn = pd.read_csv(REPO / "config" / "station_downstream_map.csv", dtype=str).set_index(K).reindex(a.index)
    up = dn.us_station_id.fillna("") != ""
    head("upstream gauge in config/station_downstream_map.csv"); row("with", up); row("without", ~up)
    f = REPO / "runs" / "station_sharing" / "sharing_station.csv"
    if f.exists():
        sh = pd.read_csv(f, dtype={"station_id": str}).set_index(K).reindex(a.index)
        fl = (sh.rmse_partners_cm < 0.95 * sh.rmse_model_cm).fillna(False)
        head("linear diagnostic (station_sharing.py)"); row("more than 5% better in the diagnostic", fl); row("the other stations", ~fl)

    mem = lambda X: X[X.model != "mean"].set_index(K + ["model"]).rmse_6h_cm.unstack("model").loc[a.index]
    ma, mb = mem(A), mem(B)
    d = pd.DataFrame({"name": pm.name, "type": a.type, "n_6h": a.n_6h, "rmse_6h_ref_cm": a.rmse_6h_cm, "rmse_6h_new_cm": b.rmse_6h_cm,
                      "change_pct": 100 * (b.rmse_6h_cm / a.rmse_6h_cm - 1), "ref_member_min": ma.min(1), "ref_member_max": ma.max(1),
                      "new_member_min": mb.min(1), "new_member_max": mb.max(1), "rmse_event_ref_cm": a.rmse_event_6h_cm, "rmse_event_new_cm": b.rmse_event_6h_cm,
                      "rmse_storm_ref_cm": a.rmse_storm_6h_cm, "rmse_storm_new_cm": b.rmse_storm_6h_cm, "lag_ref_h": a.lag_h, "lag_new_h": b.lag_h,
                      "n_partners": n_p, "n_far_river_partners": far})
    d["clearly_better"] = d.new_member_max < d.ref_member_min; d["clearly_worse"] = d.new_member_min > d.ref_member_max
    for j in range(1, k + 1):
        d[f"p{j}_name"], d[f"p{j}_type"], d[f"p{j}_km"] = pm[f"p{j}_name"], typ[j], km[j]
    head("every single member better / worse than every single member of the reference")
    row("clearly better", d.clearly_better); row("clearly worse", d.clearly_worse)
    print("\n  clearly better / worse by type:", {t: (int(x.clearly_better.sum()), int(x.clearly_worse.sum())) for t, x in d.groupby("type")})
    show = ["name", "type", "rmse_6h_ref_cm", "rmse_6h_new_cm", "change_pct", "p1_name", "p1_km"]
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 46)
    print("\nlargest improvements (%)\n", d.sort_values("change_pct").head(15)[show].round(2).to_string(index=False))
    print("\nlargest deteriorations (%)\n", d.sort_values("change_pct").tail(15)[show].round(2).to_string(index=False))
    out = REPO / "runs" / f"protocol_{a_.new}" / "partner_station_compare.csv"
    d.round(4).to_csv(out); print("\n->", out)


if __name__ == "__main__":
    main()
