"""Partner stations whose newest hours have not arrived: one table over the cases evaluated with eval_protocol.py --partner-late / --own-late.

Rows: the groups (mean of the members); columns: the cases. RMSE in cm over all forecasts of the stations with real-time
data, the largest 6 h changes, the hurricane periods, the lag on the rises, and the 6 h RMSE by station type.
Input : runs/protocol_<name>/protocol_station.csv of every case that exists
Output: printed tables; --csv FILE
Usage : python partner_late_table.py [--csv deliverables/28_partner_late.csv]
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
# group -> {case: name of runs/protocol_<name>}
CASES = ["on time", "partners 1 h late", "partners 2 h late", "partners 3 h late", "partners 6 h late", "station and partners 1 h late"]
GROUPS = {
    "no partner stations (the model that is run)": {"on time": "hrrr_total", "station and partners 1 h late": "hrrr_total_ownlate1"},
    "partner stations (rivers and creeks within 50 km), trained with their data complete": {"on time": "partners4_river50", "partners 1 h late": "partners4_river50_late1", "partners 2 h late": "partners4_river50_late2",
                                                           "partners 3 h late": "partners4_river50_late3", "partners 6 h late": "partners4_river50_late6",
                                                           "station and partners 1 h late": "partners4_river50_ownlate1_late1"},
    "partner stations (rivers and creeks within 50 km), trained with their newest hours missing": {"on time": "partners4_river50_lateaug", "partners 1 h late": "partners4_river50_lateaug_late1",
                                                                  "partners 2 h late": "partners4_river50_lateaug_late2", "partners 3 h late": "partners4_river50_lateaug_late3",
                                                                  "partners 6 h late": "partners4_river50_lateaug_late6",
                                                                  "station and partners 1 h late": "partners4_river50_lateaug_ownlate1_late1"},
    "partner stations by river network, trained with their newest hours missing": {"on time": "partners4_network_lateaug", "partners 1 h late": "partners4_network_lateaug_late1",
                                                                                   "partners 2 h late": "partners4_network_lateaug_late2", "partners 3 h late": "partners4_network_lateaug_late3",
                                                                                   "partners 6 h late": "partners4_network_lateaug_late6",
                                                                                   "station and partners 1 h late": "partners4_network_lateaug_ownlate1_late1"},
}
TYPES = ["tide gauge", "estuary / tidal channel", "lake", "marsh", "river / canal", "urban creek (Houston)"]


def pool(x: pd.DataFrame, col: str, n: str) -> float:
    w = x[n].to_numpy(float); v = np.nan_to_num(x[col].to_numpy(float))
    return float(np.sqrt((w * v ** 2).sum() / max(w.sum(), 1)))


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--csv"); ap.add_argument("--min-n", type=int, default=720)
    a = ap.parse_args()
    rows = []
    for g, cases in GROUPS.items():
        for c in CASES:
            f = REPO / "runs" / f"protocol_{cases.get(c, '-')}" / "protocol_station.csv"
            if not f.exists():
                continue
            X = pd.read_csv(f, dtype={"station_id": str}); X = X[X.n_6h >= a.min_n]
            x = X[X.model == "mean"]; mem = [m for m in X.model.unique() if m != "mean"]
            single = [pool(X[X.model == m], "rmse_6h_cm", "n_6h") for m in mem]
            r = {"group": g, "case": c, "stations": len(x), "rmse_1h_cm": pool(x, "rmse_1h_cm", "n_6h"), "rmse_3h_cm": pool(x, "rmse_3h_cm", "n_6h"),
                 "rmse_6h_cm": pool(x, "rmse_6h_cm", "n_6h"), "single_6h_min": min(single), "single_6h_max": max(single),
                 "event_6h_cm": pool(x, "rmse_event_6h_cm", "n_event"), "storm_6h_cm": pool(x, "rmse_storm_6h_cm", "n_storm"),
                 "lag_h": float(x.lag_h[x.n_timing >= 10].mean())}
            for t in TYPES:
                r[f"rmse_6h_{t.split(' ')[0]}_cm"] = pool(x[x.type == t], "rmse_6h_cm", "n_6h")
            rows.append(r)
    d = pd.DataFrame(rows)
    for col, lab in [("rmse_6h_cm", "6 h RMSE, all forecasts (cm)"), ("rmse_3h_cm", "3 h RMSE"), ("rmse_1h_cm", "1 h RMSE"), ("event_6h_cm", "largest 6 h changes, 6 h (cm)"),
                     ("storm_6h_cm", "hurricane periods, 6 h (cm)"), ("lag_h", "lag on the rises (h)")] + [(f"rmse_6h_{t.split(' ')[0]}_cm", f"6 h RMSE, {t}") for t in TYPES]:
        print(f"\n{lab}")
        print(d.pivot(index="group", columns="case", values=col).reindex(index=list(GROUPS), columns=CASES).round(2).to_string())
    if a.csv:
        d.round(3).to_csv(a.csv, index=False); print("\n->", a.csv)


if __name__ == "__main__":
    main()
