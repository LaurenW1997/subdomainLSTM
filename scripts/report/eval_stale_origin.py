"""What happens to the forecast when the gauge has stopped reporting for the last 1, 2 or 3 hours?

Operationally a station is still forecast while its newest observation is at most 3 h old. Here the newest k hours of
water level (k = 0 .. 3) are removed from the input of test-set origins exactly as the forecast script would see them:
  model trained with --fill ffill : those hours take the last value before the gap, mask 0, the change-unit channel is
                                    rebuilt from the filled series (the forecast then starts from that older value)
  model trained without it        : those hours take the station mean (0 in z-score units), mask 0
Wind, rainfall and discharge are left untouched. Only origins whose newest k+1 hours were really observed are used,
the same origins for every k. Operational stations only (no CRMS).
Output: runs/<run>/stale_origin.csv (group, k, lead, rmse_cm, n), printed tables.
Usage (sv7, CPU): python eval_stale_origin.py --run v11_fc1_t45 --dataset DATA/dataset_v6 [--test-end 2025-12-31T17]
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
KMAX = 3
STORMS = [("Beryl", "2024-07-07", "2024-07-11", ("Texas100m", "Galveston100m")), ("Francine", "2024-09-10", "2024-09-14", ("Louisiana100m",))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True); ap.add_argument("--dataset", required=True)
    ap.add_argument("--test-end", default="2025-12-31T17"); ap.add_argument("--stride", type=int, default=6); ap.add_argument("--batch", type=int, default=4096)
    a = ap.parse_args()
    device = torch.device("cpu"); torch.set_num_threads(32)
    sm, model = load(REPO / "runs" / a.run, Path(a.dataset), device)
    ffill = sm.fill == "ffill"
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))
    lo = sm.split_range("test")[0]; t_lo = -(-lo // a.stride) * a.stride          # 00/06/12/18 UTC for every run, so that runs can be compared
    S, T0 = sm.eval_origins("test", a.stride, t_lo=t_lo, t_hi=t_hi)
    st = sm.stations.reset_index(drop=True)
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    typ = st[["source", "station_id"]].astype(str).merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left").type.fillna("other").to_numpy()
    oper = (st.source != "CRMS").to_numpy()
    recent = np.stack([sm.mask[S, T0 - i] for i in range(KMAX + 1)], 1).all(1)      # the newest KMAX+1 hours were really observed
    keep = oper[S] & recent
    S, T0 = S[keep], T0[keep]
    storm = np.zeros(len(S), bool)
    dom = st.domains.astype(str).to_numpy()
    for _, d0, d1, doms in STORMS:
        i0, i1 = np.searchsorted(sm.time.values, np.datetime64(d0)), np.searchsorted(sm.time.values, np.datetime64(d1))
        in_dom = np.array([any(x in dd for x in doms) for dd in dom])
        storm |= (T0 >= i0) & (T0 < i1) & in_dom[S]
    print(f"{a.run}: fill={'last value' if ffill else 'station mean'}, {len(S)} origins at {len(np.unique(S))} operational stations, {int(storm.sum())} of them in the hurricane periods", flush=True)
    std = st.std_m.to_numpy(np.float32)
    groups = {"all": np.ones(len(S), bool), "hurricane periods": storm}
    for t in sorted(set(typ[oper])):
        groups[t] = typ[S] == t
        groups[f"{t} | hurricane periods"] = (typ[S] == t) & storm
    rows = []
    for k in range(KMAX + 1):
        se = np.zeros((len(S), HORIZON), np.float32); ok = np.zeros((len(S), HORIZON), bool)
        with torch.no_grad():
            for i in range(0, len(S), a.batch):
                s, t0 = S[i:i + a.batch], T0[i:i + a.batch]
                feats, fut, s, y, ym = sm.window(s, t0)
                if k:
                    sm.drop_newest(feats, s, k)
                f, fu, sx, _, _ = to_torch((feats, fut, s, y, ym), device)
                err = (model(f, sx, fu).numpy() - y) * std[s][:, None]
                se[i:i + a.batch] = err ** 2; ok[i:i + a.batch] = ym
        for name, sel in groups.items():
            for h in (1, 3, 6):
                m = sel & ok[:, h - 1]
                if m.sum() >= 50:
                    rows.append({"group": name, "hours_without_data": k, "lead_h": h, "rmse_cm": round(100 * float(np.sqrt(se[m, h - 1].mean())), 2), "n": int(m.sum())})
        print(f"  newest {k} h missing: 6 h RMSE {[r['rmse_cm'] for r in rows if r['group'] == 'all' and r['hours_without_data'] == k and r['lead_h'] == 6][0]} cm", flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(REPO / "runs" / a.run / "stale_origin.csv", index=False)
    pd.set_option("display.width", 200)
    for h in (1, 3, 6):
        print(f"\nlead {h} h, RMSE (cm) by hours without data")
        print(t[t.lead_h == h].pivot(index="group", columns="hours_without_data", values="rmse_cm").to_string())


if __name__ == "__main__":
    main()
