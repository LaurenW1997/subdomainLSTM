"""Forecasts made from the real-time data feeds, every hour of a period, with the observations that came in afterwards.

Reads the forecast folders of forecast.py (one sub-folder per forecast time, several parent folders may follow one another
in time) and the pickle of fetch_levels_span.py; one row per station, forecast time and lead.
Output: --out CSV (gzip if the name ends in .gz): source, station_id, name, origin, lead, valid, forecast (m), obs (m);
        the RMSE per lead over all rows with an observation is printed
Usage : python realtime_pairs.py --dirs DIR [DIR ...] --levels FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
K = ["source", "station_id"]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dirs", nargs="+", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--code", default=str(HERE), help="folder with forecast.py"); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    sys.path.insert(0, a.code)
    from forecast import HORIZON, despike_readings, to_hourly
    files = sorted(p for d in a.dirs for p in Path(d).glob("*/forecast.csv"))
    x = pd.concat([pd.read_csv(p, dtype={"station_id": str}, parse_dates=["cycle_utc"]) for p in files], ignore_index=True); x = x[x.status == "ok"]
    assert not x.duplicated(K + ["cycle_utc"]).any(), "a forecast time is in two folders"
    f = x.melt(id_vars=K + ["name", "cycle_utc"], value_vars=[f"fcst_{h}h_m" for h in range(1, HORIZON + 1)], var_name="lead", value_name="forecast").rename(columns={"cycle_utc": "origin"})
    f["lead"] = f.lead.str.extract(r"(\d+)").astype(int); f["valid"] = f.origin + pd.to_timedelta(f.lead, unit="h")
    obs = {k: to_hourly(despike_readings(s)[0]) for k, s in pd.read_pickle(a.levels).items()}
    o = pd.concat([s.rename("obs").to_frame().assign(source=k[0], station_id=k[1]) for k, s in obs.items()]).reset_index().rename(columns={"index": "valid"})
    f = f.merge(o, on=K + ["valid"], how="left").sort_values(K + ["origin", "lead"])
    s = f.dropna(subset=["obs", "forecast"])
    print(f"{len(files)} forecast times {f.origin.min()} .. {f.origin.max()}; {s[K].drop_duplicates().shape[0]} stations; {len(s)} forecasts with an observation")
    print("RMSE (cm) by lead:", {h: round(float(100 * np.sqrt(((s.forecast - s.obs)[s.lead == h] ** 2).mean())), 2) for h in range(1, HORIZON + 1)})
    f.round(4).to_csv(a.out, index=False); print("->", a.out, len(f))


if __name__ == "__main__":
    main()
