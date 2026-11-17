"""Score several finished forecast cycles of several forecast folders against what was observed afterwards.

For a test of two (or more) models on past forecast times: every folder is an --out of forecast.py with one sub-folder
per cycle. The observations are pulled once from the live services for the whole period (same unit and datum handling
as forecast.py). A (cycle, station) is scored only if EVERY folder has a forecast with status "ok" for it and the
observation of the lead exists, so that all folders are scored on the same forecasts.
Output: <out>/verification_long.csv   one row per folder, cycle, station: observed level, forecast and error per lead
        <out>/verification_summary.csv  RMSE per folder and lead over all scored forecasts, by station type and by
                                        measured behaviour (config/station_behaviour.csv), and per cycle
        printed tables
Usage : python verify_cycles.py --dirs A=DIR_A B=DIR_B --out OUT [--cycles 2026-11-15T00 ...]   (default: every cycle all folders have)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forecast import HORIZON, REPO, fetch_levels, to_hourly  # noqa: E402

K = ["source", "station_id"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True, help="label=folder (an --out of forecast.py)"); ap.add_argument("--out", required=True); ap.add_argument("--cycles", nargs="*")
    a = ap.parse_args()
    dirs = dict(x.split("=", 1) for x in a.dirs); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cyc = sorted(set.intersection(*[{p.name for p in Path(d).iterdir() if (p / "forecast.csv").exists()} for d in dirs.values()]))
    if a.cycles:
        want = {pd.Timestamp(c).strftime("%Y%m%dT%H") for c in a.cycles}; cyc = [c for c in cyc if c in want]
    F = {}
    for lab, d in dirs.items():
        x = pd.concat([pd.read_csv(Path(d) / c / "forecast.csv", dtype={"station_id": str}, parse_dates=["cycle_utc"]) for c in cyc], ignore_index=True)
        F[lab] = x[x.status == "ok"].set_index(K + ["cycle_utc"])
    common = sorted(set.intersection(*[set(x.index) for x in F.values()]))
    idx = pd.MultiIndex.from_tuples(common, names=K + ["cycle_utc"])
    first = next(iter(F.values())).loc[idx]
    st = first.reset_index()[K + ["name", "lat", "lon", "domains", "datum"]].drop_duplicates(K).reset_index(drop=True)
    t0, t1 = idx.get_level_values("cycle_utc").min(), idx.get_level_values("cycle_utc").max() + pd.Timedelta(hours=HORIZON)
    now = pd.Timestamp.now("UTC").tz_localize(None)
    raw = out / "raw_verify"; raw.mkdir(exist_ok=True)
    series = fetch_levels(st, ["USGS", "NOAA_COOPS"], t0 - pd.Timedelta(hours=1), t1 + pd.Timedelta(minutes=59), raw)
    hourly = {k: to_hourly(s) for k, s in series.items()}
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str}).set_index(K).type
    b = pd.read_csv(REPO / "config" / "station_behaviour.csv", dtype={"station_id": str}).set_index(K).behaviour
    keys = list(zip(idx.get_level_values(0), idx.get_level_values(1))); cy = idx.get_level_values("cycle_utc")
    obs = np.full((len(idx), HORIZON), np.nan)
    for n, (k, c) in enumerate(zip(keys, cy)):
        h = hourly.get(k)
        if h is not None:
            hours = pd.date_range(c + pd.Timedelta(hours=1), periods=HORIZON, freq="1h")
            v = h.reindex(hours).to_numpy(float).copy()
            v[np.array([now < x + pd.Timedelta(minutes=75) for x in hours])] = np.nan       # the hour (mean over -30 .. +30 min) must have passed, plus the reporting delay
            obs[n] = v
    rows = []
    for lab, x in F.items():
        x = x.loc[idx]
        r = pd.DataFrame({"model": lab, "source": idx.get_level_values(0), "station_id": idx.get_level_values(1), "cycle_utc": cy, "name": x["name"].to_numpy(),
                          "type": g.reindex(keys).to_numpy(), "behaviour": b.reindex(keys).to_numpy(), "last_obs_m": x.last_obs_m.to_numpy(), "last_obs_utc": x.last_obs_utc.to_numpy(),
                          "n_partners": x.n_partners.to_numpy() if "n_partners" in x else np.nan,
                          "n_partners_reporting": x.n_partners_reporting.to_numpy() if "n_partners_reporting" in x else np.nan})
        for h in range(1, HORIZON + 1):
            r[f"obs_{h}h_m"] = obs[:, h - 1]; r[f"fcst_{h}h_m"] = x[f"fcst_{h}h_m"].to_numpy(); r[f"err_{h}h_cm"] = 100 * (r[f"fcst_{h}h_m"] - r[f"obs_{h}h_m"])
        rows.append(r)
    d = pd.concat(rows, ignore_index=True)
    ok = np.isfinite(obs).all(1)                       # every lead observed: the same forecasts at every lead
    d["scored"] = np.tile(ok, len(F))
    d.round(4).to_csv(out / "verification_long.csv", index=False)
    s = d[d.scored]
    rm = lambda x, h: float(np.sqrt((x[f"err_{h}h_cm"] ** 2).mean()))
    print(f"{len(cyc)} cycles {cyc[0]} .. {cyc[-1]}; forecasts with status ok in every folder {len(idx)}, with all six hours observed {int(ok.sum())} at {s[K].drop_duplicates().shape[0]} stations")
    summ = []

    def table(title, col):
        print(f"\n{title}: RMSE (cm) at 1 / 3 / 6 h" + "".join(f"   {lab}" for lab in F))
        groups = [("all", s)] if col is None else [(str(k), x) for k, x in s.groupby(col)]
        for k, x in groups:
            line = f"  {k:28s} n={len(x) // len(F):5d}"
            for lab in F:
                y = x[x.model == lab]
                line += "   " + " / ".join(f"{rm(y, h):5.2f}" for h in (1, 3, 6))
                summ.append({"group_by": col or "all", "group": k, "model": lab, "n": len(y), **{f"rmse_{h}h_cm": round(rm(y, h), 3) for h in range(1, HORIZON + 1)}})
            print(line)

    table("all scored forecasts", None); table("by station type", "type"); table("by measured behaviour", "behaviour"); table("by cycle", "cycle_utc")
    pd.DataFrame(summ).to_csv(out / "verification_summary.csv", index=False)
    print("\n->", out / "verification_long.csv", out / "verification_summary.csv")


if __name__ == "__main__":
    main()
