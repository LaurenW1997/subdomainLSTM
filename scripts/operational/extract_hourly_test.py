"""Forecasts from every hour of a test period, of several forecast folders, as one table per lead time and valid hour.

For figures with continuous lead-time lines (the forecast valid at each hour that was issued 1, 3, 6 h earlier) and for
the RMSE over all hourly forecast times. The observations come from the pickle of fetch_levels_span.py.
Output: <out>/hourly_fc.csv    source, station_id, origin, lead, valid, <label of every folder> (m), obs (m)   [--stations only]
        <out>/hourly_rmse.csv  RMSE per folder and lead over all stations and forecast times with a forecast in every folder
Usage : python extract_hourly_test.py --dirs run=DIR partners=DIR --levels FILE --out OUT [--stations 07374000 ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forecast import HORIZON, to_hourly  # noqa: E402

K = ["source", "station_id"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--out", required=True); ap.add_argument("--stations", nargs="*")
    a = ap.parse_args()
    dirs = dict(x.split("=", 1) for x in a.dirs); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cyc = sorted(set.intersection(*[{p.name for p in Path(d).iterdir() if (p / "forecast.csv").exists()} for d in dirs.values()]))
    obs = {k: to_hourly(s) for k, s in pd.read_pickle(a.levels).items()}
    parts = []
    for lab, d in dirs.items():
        x = pd.concat([pd.read_csv(Path(d) / c / "forecast.csv", dtype={"station_id": str}, parse_dates=["cycle_utc"]) for c in cyc], ignore_index=True)
        x = x[x.status == "ok"]
        x = x.melt(id_vars=K + ["name", "cycle_utc"], value_vars=[f"fcst_{h}h_m" for h in range(1, HORIZON + 1)], var_name="lead", value_name=lab)
        x["lead"] = x.lead.str.extract(r"(\d+)").astype(int)
        parts.append(x.set_index(K + ["cycle_utc", "lead"]))
    f = parts[0][["name"]].join([p[[c for c in p.columns if c != "name"]] for p in parts], how="inner").reset_index().rename(columns={"cycle_utc": "origin"})
    f["valid"] = f.origin + pd.to_timedelta(f.lead, unit="h")
    o = pd.concat([s.rename("obs").to_frame().assign(source=k[0], station_id=k[1]) for k, s in obs.items()]).reset_index().rename(columns={"index": "valid"})
    f = f.merge(o, on=K + ["valid"], how="left")
    labs = list(dirs)
    s = f.dropna(subset=["obs"] + labs)
    rows = [{"model": lab, "lead": h, "n": int((s.lead == h).sum()), "stations": s[K].drop_duplicates().shape[0], "origins": s.origin.nunique(),
             "rmse_cm": round(float(100 * np.sqrt(((s[lab] - s.obs)[s.lead == h] ** 2).mean())), 3)} for lab in labs for h in range(1, HORIZON + 1)]
    r = pd.DataFrame(rows); r.to_csv(out / "hourly_rmse.csv", index=False)
    print(f"{len(cyc)} forecast times {cyc[0]} .. {cyc[-1]}"); print(r.pivot(index="lead", columns="model", values="rmse_cm").to_string()); print("forecasts per lead:", int(r.n.iloc[0]))
    if a.stations:
        f = f[f.station_id.isin(a.stations)]
    f.round(4).to_csv(out / "hourly_fc.csv", index=False)
    print("->", out / "hourly_fc.csv", len(f))


if __name__ == "__main__":
    main()
