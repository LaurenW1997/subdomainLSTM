"""Which stations are better and which are worse with partner stations: test years and the two hourly tests on live data.

One row per station with real-time data: 6 h RMSE without and with partner stations in the test years 2024-2025 (five-model
means; clearly worse / better = all five single models on one side of all five of the other version) and in the hourly
tests of 10-12 and 14-17 November 2026, the tide class and the number of partners.
Input : runs/protocol_hrrr_total, runs/protocol_partners4_behaviour_lateaug (protocol_station.csv), config/station_behaviour.csv,
        config/station_partners_behaviour.csv, deliverables/33_partner_live_test/station_rmse_hourly_*.csv
Output: deliverables/33_partner_live_test/station_better_worse.csv, and the counts on stdout
Usage : python partner_better_worse.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
T = REPO / "deliverables" / "33_partner_live_test"
K = ["source", "station_id"]


def test_years() -> pd.DataFrame:
    A = pd.read_csv(REPO / "runs" / "protocol_hrrr_total" / "protocol_station.csv", dtype={"station_id": str})
    B = pd.read_csv(REPO / "runs" / "protocol_partners4_behaviour_lateaug" / "protocol_station.csv", dtype={"station_id": str})
    A, B = A[A.n_6h >= 720], B[B.n_6h >= 720]
    a = A[A.model == "mean"].set_index(K); b = B[B.model == "mean"].set_index(K).reindex(a.index)
    mem = lambda Z: Z[Z.model != "mean"].set_index(K + ["model"]).rmse_6h_cm.unstack("model").reindex(a.index)
    ma, mb = mem(A), mem(B)
    return pd.DataFrame({"name": a.name if "name" in a else "", "type": a.type, "test_n": a.n_6h, "test_run": a.rmse_6h_cm, "test_partners": b.rmse_6h_cm,
                         "test_clearly_worse": mb.min(1) > ma.max(1), "test_clearly_better": mb.max(1) < ma.min(1)})


def live(f: str, tag: str) -> pd.DataFrame:
    d = pd.read_csv(T / f, dtype={"station_id": str}); d = d[d.lead == 6].set_index(K)
    return pd.DataFrame({f"{tag}_n": d.n, f"{tag}_run": d.rmse_run_cm, f"{tag}_partners": d.rmse_partners_cm})


def counts(x: pd.DataFrame, a: str, b: str, label: str) -> None:
    y = x.dropna(subset=[a, b]); d = y[b] - y[a]; pct = 100 * d / y[a].clip(lower=0.1)
    print(f"{label:58s} n {len(y):3d} | better {int((d < 0).sum()):3d}  worse {int((d > 0).sum()):3d} | by more than 0.5 cm: {int((d < -0.5).sum()):3d} / {int((d > 0.5).sum()):3d}"
          f" | by more than 1 cm: {int((d < -1).sum()):3d} / {int((d > 1).sum()):3d} | median station {y[a].median():.2f} -> {y[b].median():.2f}")


def main() -> None:
    beh = pd.read_csv(REPO / "config" / "station_behaviour.csv", dtype={"station_id": str}).set_index(K)[["name", "behaviour"]]
    pm = pd.read_csv(REPO / "config" / "station_partners_behaviour.csv", dtype=str).fillna("").set_index(K)
    npar = pd.to_numeric(pm.n_partners, errors="coerce").fillna(0).astype(int)
    x = test_years().drop(columns="name").join(beh, how="left").join(npar.rename("n_partners"), how="left").join(live("station_rmse_hourly_10to12nov.csv", "nov10to12"), how="outer") \
        .join(live("station_rmse_hourly_14to17nov.csv", "nov14to17"), how="outer")
    x["name"] = x.name.fillna(beh.name.reindex(x.index)); x["behaviour"] = x.behaviour.fillna(beh.behaviour.reindex(x.index)); x["n_partners"] = x.n_partners.fillna(npar.reindex(x.index)).fillna(0).astype(int)
    for t in ("test", "nov10to12", "nov14to17"):
        x[f"{t}_diff"] = (x[f"{t}_partners"] - x[f"{t}_run"]).round(3)
    x.reset_index().to_csv(T / "station_better_worse.csv", index=False)

    print("6 h RMSE, with partner stations against the version that is run\n")
    for t, lab in (("test", "Test years 2024-2025"), ("nov10to12", "10-12 November, hourly (49 forecast times)"), ("nov14to17", "14-17 November, hourly (61 forecast times)")):
        counts(x, f"{t}_run", f"{t}_partners", lab + ": all stations")
        counts(x[x.n_partners > 0], f"{t}_run", f"{t}_partners", "    stations with partners")
        counts(x[x.n_partners == 0], f"{t}_run", f"{t}_partners", "    stations without partner (nothing changed for them)")
        for b in ("tidal", "weakly tidal", "no tide"):
            counts(x[(x.behaviour == b) & (x.n_partners > 0)], f"{t}_run", f"{t}_partners", f"    with partners, {b}")
    ty = x.dropna(subset=["test_run"])
    print(f"\ntest years: clearly worse {int(ty.test_clearly_worse.sum())} (with partners {int((ty.test_clearly_worse & (ty.n_partners > 0)).sum())}), clearly better {int(ty.test_clearly_better.sum())}")
    cols = ["name", "behaviour", "n_partners", "test_run", "test_partners", "nov10to12_run", "nov10to12_partners", "nov14to17_run", "nov14to17_partners"]
    pd.set_option("display.width", 260); pd.set_option("display.max_colwidth", 44)
    print("\nclearly worse in the test years:"); print(ty[ty.test_clearly_worse][cols].round(2).to_string())
    print("\nworse by more than 0.5 cm in the test years:"); print(ty[ty.test_diff > 0.5][cols].round(2).to_string())
    # do the few days of live data tell which stations are worse?
    z = x.dropna(subset=["test_diff", "nov10to12_diff", "nov14to17_diff"]); z = z[z.n_partners > 0]
    wa, wb, wt = z.nov10to12_diff > 0.5, z.nov14to17_diff > 0.5, z.test_diff > 0
    print(f"\nstations with partners and all three numbers: {len(z)}")
    print(f"worse by more than 0.5 cm in 10-12 Nov: {int(wa.sum())}; in 14-17 Nov: {int(wb.sum())}; in both: {int((wa & wb).sum())} (expected by chance {wa.mean() * wb.mean() * len(z):.1f})")
    print(f"of the {int((wa | wb).sum())} worse in at least one live period, worse in the test years (any amount): {int(((wa | wb) & wt).sum())}; of all {len(z)}: {int(wt.sum())}")
    print(f"correlation of the change per station: 10-12 Nov with 14-17 Nov {np.corrcoef(z.nov10to12_diff, z.nov14to17_diff)[0, 1]:.2f}; test years with 10-12 Nov {np.corrcoef(z.test_diff, z.nov10to12_diff)[0, 1]:.2f}; "
          f"test years with 14-17 Nov {np.corrcoef(z.test_diff, z.nov14to17_diff)[0, 1]:.2f}")
    print("\nworse by more than 0.5 cm in both live periods:"); print(z[wa & wb][cols].round(2).to_string())
    print("\nthe two stations asked about:"); print(x[x.index.get_level_values(1).isin(["08116850", "08164503"])][cols].round(2).to_string())


if __name__ == "__main__":
    main()
