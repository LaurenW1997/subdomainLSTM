"""End-to-end check of the operational pipeline on past cycles.

forecast.py is run for past cycles (--cycle), i.e. with the inputs the real-time system would have had: water level and
discharge from the public APIs, HRRR wind, MRMS / HRRR rainfall. This script scores those forecasts against the
observations in the training dataset and, on exactly the same (station, cycle) pairs, scores the forecasts the same
models make from the dataset inputs (AORC wind and rainfall) - the numbers reported in the test tables. The difference
between the two is what the switch from the training inputs to the real-time inputs costs.

Usage (sv7): python hindcast_check.py --dataset DATA/dataset_v6 --out DIR/hindcast_check \
               --model new:OUT_DIR_NEW:RUN_DIR_NEW:DATASET_NEW --model old:OUT_DIR_OLD:RUN_DIR_OLD:DATASET_OLD
Output: <out>_pairs.csv (one row per station, cycle), <out>_summary.csv, printed table.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "train"))
sys.path.insert(0, str(HERE.parents[0] / "report"))
from data import to_torch  # noqa: E402
from station_compare import load  # noqa: E402

LEADS = (1, 3, 6)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="dataset dir with values.npy, time.npy, stations.csv (observations)")
    ap.add_argument("--model", action="append", required=True, help="key:operational_out_dir:run_dir:dataset_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = Path(a.dataset)
    values = np.load(d / "values.npy", mmap_mode="r")
    time = pd.DatetimeIndex(np.load(d / "time.npy"))
    st = pd.read_csv(d / "stations.csv", dtype={"station_id": str})
    row_of = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}
    frames = []; keys = []
    for spec in a.model:
        key, out_dir, run_dir, ds = spec.split(":"); keys.append(key)
        sm, model = load(Path(run_dir), Path(ds), torch.device("cpu"))
        recs = []
        for f in sorted(Path(out_dir).glob("*/forecast.csv")):
            df = pd.read_csv(f, dtype={"station_id": str}, parse_dates=["cycle_utc"])
            df = df[df.status == "ok"]
            if df.empty:
                continue
            cyc = df.cycle_utc.iloc[0]
            t0 = int(time.get_indexer([cyc])[0])
            if t0 < 0 or t0 + 6 >= len(time):
                continue
            rows = np.array([row_of[(s, i)] for s, i in zip(df.source, df.station_id)])
            # the same model from the dataset inputs (AORC wind / rainfall), same stations and origin
            feats, fut, s, _, _ = sm.window(rows, np.full(len(rows), t0))
            with torch.no_grad():
                f_, fu_, s_, _, _ = to_torch((feats, fut, s, np.zeros((len(s), 6), np.float32), np.zeros((len(s), 6), bool)), torch.device("cpu"))
                z = model(f_, s_, fu_).numpy()
            off = z * st.std_m.to_numpy()[rows][:, None] + st.mean_m.to_numpy()[rows][:, None]
            okin = sm._ok(rows, np.full(len(rows), t0)) if (t0 % 6 == 0) else np.ones(len(rows), bool)
            r = pd.DataFrame({"source": df.source.to_numpy(), "station_id": df.station_id.to_numpy(), "cycle": cyc,
                              "obs_origin": np.asarray(values[rows, t0]), "api_origin": df.last_obs_m.to_numpy(), "offline_inputs_ok": okin})
            for h in LEADS:
                r[f"obs_{h}"] = np.asarray(values[rows, t0 + h])
                r[f"{key}_live_{h}"] = df[f"fcst_{h}h_m"].to_numpy()
                r[f"{key}_data_{h}"] = off[:, h - 1]
            recs.append(r)
        frames.append(pd.concat(recs).rename(columns={"offline_inputs_ok": f"{key}_data_ok", "api_origin": f"{key}_api_origin"}))
        print(key, "cycles", frames[-1].cycle.nunique(), "pairs", len(frames[-1]), flush=True)
    j = frames[0]
    for f in frames[1:]:
        j = j.merge(f.drop(columns=["obs_origin"] + [f"obs_{h}" for h in LEADS]), on=["source", "station_id", "cycle"], how="inner")
    ok = np.ones(len(j), bool)
    for k in keys:
        ok &= j[f"{k}_data_ok"].to_numpy()
    for h in LEADS:
        ok &= np.isfinite(j[f"obs_{h}"].to_numpy())
    j = j[ok & (j.source != "CRMS")].copy()
    j["event"] = j.cycle.dt.strftime("%Y-%m")
    j.to_csv(f"{a.out}_pairs.csv", index=False)
    d0 = (j[f"{keys[0]}_api_origin"] - j.obs_origin).abs()
    print(f"level at the origin, live API vs dataset: median |difference| {100 * d0.median():.2f} cm, 95th percentile {100 * d0.quantile(0.95):.2f} cm, "
          f"{(d0 > 0.05).mean():.1%} of pairs differ by more than 5 cm")
    rows = []
    for name, x in [("all cycles", j)] + [(e, g) for e, g in j.groupby("event")]:
        r = {"cycles": name, "n_cycles": x.cycle.nunique(), "pairs": len(x)}
        for k in keys:
            for src in ("data", "live"):
                for h in LEADS:
                    r[f"{k} {src} {h}h"] = round(100 * float(np.sqrt(np.mean((x[f"{k}_{src}_{h}"] - x[f"obs_{h}"]) ** 2))), 2)
        rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(f"{a.out}_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print("RMSE in cm; 'data' = dataset inputs (AORC), 'live' = operational pipeline (APIs, HRRR, MRMS)")
    print(t[["cycles", "n_cycles", "pairs"] + [c for c in t.columns if c.endswith(" 6h")]].to_string(index=False))


if __name__ == "__main__":
    main()
