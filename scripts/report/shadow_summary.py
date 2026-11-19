"""Summary of the runs in real time: the run of 17 November 18 UTC started by hand and the runs on a schedule since then.

Input (deliverables/33_partner_live_test/, copied from sv7):
  live_20261117T18_verification_summary.csv   partner_live_20261117/verification/verification_summary.csv
  shadow_verification_summary.csv             shadow_20261117/verification/<latest forecast time>/verification_summary.csv
  shadow_status.csv                           shadow_20261117/status.csv
  shadow_wrong_readings.csv                   optional: the station forecasts hit by a wrong reading (rows of verification_long.csv, one per model),
                                              for the totals without them (live_summary_without_wrong_readings.csv) and the note
Output (same folder): live_summary.csv (one row per model and run time, all forecast times together), live_by_time.csv
                      (one row per forecast time), live_meta.json and live_note.txt for the slide
Usage : python shadow_summary.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

T = Path(__file__).resolve().parents[2] / "deliverables" / "33_partner_live_test"
ORDER = [("no partners, run 31 min after the hour", "Run 31 min after the hour: the version that is run"), ("partners, run 31 min after the hour", "     with partner stations"),
         ("no partners, run 65 min after the hour", "Run 65 min after the hour: the version that is run"), ("partners, run 65 min after the hour", "     with partner stations"),
         ("no partners, data complete", "Data complete (run 7 h later): the version that is run"), ("partners, data complete", "     with partner stations")]
REN = {"no partners, run at 18:31": ORDER[0][0], "partners, run at 18:31": ORDER[1][0], "no partners, run at 19:05": ORDER[2][0], "partners, run at 19:05": ORDER[3][0]}


def main() -> None:
    a = pd.read_csv(T / "live_20261117T18_verification_summary.csv"); a["model"] = a.model.replace(REN)
    b = pd.read_csv(T / "shadow_verification_summary.csv")
    cyc = pd.concat([a[a.group_by == "cycle_utc"], b[b.group_by == "cycle_utc"]]).rename(columns={"group": "forecast_time"})
    cyc = cyc[["forecast_time", "model", "n", "rmse_1h_cm", "rmse_3h_cm", "rmse_6h_cm"]]
    cyc.to_csv(T / "live_by_time.csv", index=False)
    g = cyc.groupby("model", sort=False)
    tot = pd.DataFrame({"n": g.n.sum(), **{f"rmse_{h}h_cm": g.apply(lambda z, h=h: float(np.sqrt((z.n * z[f"rmse_{h}h_cm"] ** 2).sum() / z.n.sum()))) for h in (1, 3, 6)}})
    out = pd.DataFrame([{"label": lab, "model": m, **tot.loc[m].round(3).to_dict()} for m, lab in ORDER])
    out.to_csv(T / "live_summary.csv", index=False)
    times = sorted(cyc.forecast_time.unique())
    st = pd.read_csv(T / "shadow_status.csv")
    failed = int(((st.exit_no_partners != 0) | (st.exit_partners != 0) | (st.stations_no_partners == 0) | (st.stations_partners == 0)).sum())
    p6 = cyc.pivot(index="forecast_time", columns="model", values="rmse_6h_cm")
    better = sum(int((p6[ORDER[k + 1][0]] < p6[ORDER[k][0]]).sum()) for k in (0, 2, 4)); pairs = 3 * len(p6)
    f = lambda m, h: round(float(tot.loc[m, f"rmse_{h}h_cm"]), 3) + 1e-9      # as the table of the slide rounds it
    fmt = lambda t: pd.Timestamp(t).strftime("%d November %H UTC").lstrip("0")
    wr = T / "shadow_wrong_readings.csv"                     # station forecasts hit by a wrong reading: the totals without them
    wo = None
    if wr.exists():
        w = pd.read_csv(wr, dtype={"station_id": str}); k = w.groupby("model").size(); nw = w.drop_duplicates(["forecast_time", "station_id"]).shape[0]
        wo = pd.DataFrame({f"rmse_{h}h_cm": np.sqrt((tot.n * tot[f"rmse_{h}h_cm"] ** 2 - w.groupby("model")[f"err_{h}h_cm"].apply(lambda e: (e ** 2).sum())) / (tot.n - k)) for h in (1, 3, 6)})
        wo.insert(0, "n", tot.n - k)
        pd.DataFrame([{"label": lab, "model": m, **wo.loc[m].round(3).to_dict()} for m, lab in ORDER]).to_csv(T / "live_summary_without_wrong_readings.csv", index=False)
    g_ = (lambda m, h: float(wo.loc[m, f"rmse_{h}h_cm"])) if wo is not None else None
    meta = {"n_times": len(times), "first": fmt(times[0]), "last": fmt(times[-1]), "steps": int(len(st)), "failed": failed, "forecasts": int(tot.n.iloc[0])}
    (T / "live_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    note = [
        f"{meta['n_times']} forecast times, {meta['first']} to {meta['last']}, run when the data were arriving and scored 7 h later. The first was started by hand, the others by cron on sv7, under my own account. "
        "Both models read the same readings.",
        "",
        f"-  {'No failed step' if failed == 0 else str(failed) + ' failed steps'} on the schedule so far: {meta['steps']} steps, each with a forecast for {int(st.stations_no_partners.min())} to {int(st.stations_no_partners.max())} stations. "
        "The USGS service dropped connections several times; the retries got through.",
        f"-  With partner stations: lower 6 h RMSE in {better} of {pairs} comparisons (forecast time x run time). Run 31 min after the hour: {f(ORDER[0][0], 6):.2f} to {f(ORDER[1][0], 6):.2f} cm at 6 h, "
        f"{f(ORDER[0][0], 3):.2f} to {f(ORDER[1][0], 3):.2f} cm at 3 h.",
    ]
    if wo is None:
        note.append(f"-  When to run: at 1 h the RMSE is {f(ORDER[0][0], 1):.2f} cm when run 31 min after the hour and {f(ORDER[2][0], 1):.2f} cm at 65 min (part of the newest readings have not arrived at 31 min); at 6 h it makes no difference.")
    else:
        note += [
            f"-  {nw} more wrong readings, each a single reading: Cypress Ck nr Cypress (42.56 m among 39.53 m) gave a forecast 1 m too high in the run 31 min after the hour; Caernarvon Outfall Channel "
            "(-0.84 m among 0.83 m) is in the observations of the scoring. The rule that drops such readings removes both; it is not yet in the code on the schedule.",
            f"-  When to run: without these {nw} station forecasts the 1 h RMSE is {g_(ORDER[0][0], 1):.2f} cm when run 31 min after the hour and {g_(ORDER[2][0], 1):.2f} cm at 65 min (part of the newest readings "
            f"have not arrived at 31 min); at 6 h it makes no difference ({g_(ORDER[0][0], 6):.2f} and {g_(ORDER[2][0], 6):.2f} cm).",
        ]
    note += [
        f"-  Few forecast times on calm days (6 h RMSE near {f(ORDER[0][0], 6):.1f} cm, against 8.4 cm in the test years): this shows the chain running unattended, not the accuracy. The schedule runs until 21 November.",
    ]
    (T / "live_note.txt").write_text("\n".join(note), encoding="utf-8")
    print(out.drop(columns="model").round(2).to_string(index=False)); print(json.dumps(meta)); print("\n".join(note))


if __name__ == "__main__":
    main()
