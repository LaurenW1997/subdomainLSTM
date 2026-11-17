"""RMSE of every station at every lead for several forecast folders of an hourly test (forecast.py output), on the forecasts
that every folder has and that have an observation.

Output (stdout or --out): source, station_id, name, lead, n, rmse_<label>_cm for every folder
Usage : python station_rmse_hourly.py --dirs run=DIR partners=DIR --levels FILE [--out FILE]
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
    ap.add_argument("--dirs", nargs="+", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--out")
    a = ap.parse_args()
    dirs = dict(x.split("=", 1) for x in a.dirs)
    cyc = sorted(set.intersection(*[{p.name for p in Path(d).iterdir() if (p / "forecast.csv").exists()} for d in dirs.values()]))
    parts = []
    for lab, d in dirs.items():
        x = pd.concat([pd.read_csv(Path(d) / c / "forecast.csv", dtype={"station_id": str}, parse_dates=["cycle_utc"]) for c in cyc], ignore_index=True)
        x = x[x.status == "ok"]
        x = x.melt(id_vars=K + ["name", "cycle_utc"], value_vars=[f"fcst_{h}h_m" for h in range(1, HORIZON + 1)], var_name="lead", value_name=lab)
        x["lead"] = x.lead.str.extract(r"(\d+)").astype(int)
        parts.append(x.set_index(K + ["cycle_utc", "lead"]))
    f = parts[0][["name"]].join([p[[c for c in p.columns if c != "name"]] for p in parts], how="inner").reset_index()
    f["valid"] = f.cycle_utc + pd.to_timedelta(f.lead, unit="h")
    obs = {k: to_hourly(s) for k, s in pd.read_pickle(a.levels).items()}
    o = pd.concat([s.rename("obs").to_frame().assign(source=k[0], station_id=k[1]) for k, s in obs.items()]).reset_index().rename(columns={"index": "valid"})
    f = f.merge(o, on=K + ["valid"], how="left").dropna(subset=["obs"] + list(dirs))
    g = f.groupby(K + ["name", "lead"])
    r = g.size().rename("n").to_frame()
    for lab in dirs:
        r[f"rmse_{lab}_cm"] = g.apply(lambda x, lab=lab: float(100 * np.sqrt(((x[lab] - x.obs) ** 2).mean()))).round(3)
    r = r.reset_index()
    r.to_csv(a.out if a.out else sys.stdout, index=False)
    sys.stderr.write(f"{len(cyc)} forecast times {cyc[0]} .. {cyc[-1]}, {r[K].drop_duplicates().shape[0]} stations\n")


if __name__ == "__main__":
    main()
