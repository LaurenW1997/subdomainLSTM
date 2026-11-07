"""Assemble the per-station hourly parquet files into one training matrix.

Output (DATA_ROOT/dataset/):
  values.npy    float32 [n_stations, n_hours], NaN = missing, UTC hourly from START to END
  time.npy      int64 ns timestamps of the hour axis
  stations.csv  one row per matrix row: source, station_id, lat, lon, domains, datum,
                mean/std used for normalisation (train period only), valid counts per split
  meta.json     split boundaries, thresholds

Selection: >= MIN_YEARS valid hours overall, >= MIN_TRAIN_YEARS inside the training
period, and a non-degenerate train-period standard deviation.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data/ywan245/subdomainLSTM/data"))
HOURLY = DATA_ROOT / "hourly"
OUT = DATA_ROOT / "dataset"

START = pd.Timestamp("2010-01-01 00:00")
END = pd.Timestamp("2026-11-07 00:00")
TRAIN_END = pd.Timestamp("2022-12-31 23:00")   # train: 2010-2022
VAL_END = pd.Timestamp("2023-12-31 23:00")     # val: 2023, test: 2024-
MIN_YEARS = 3.0
MIN_TRAIN_YEARS = 1.0
MIN_STD_M = 0.02


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(DATA_ROOT / "data_inventory.csv")
    inv = inv[inv["years_valid"] >= MIN_YEARS].reset_index(drop=True)
    time_index = pd.date_range(START, END, freq="1h")
    n_t = len(time_index)
    rows, mats = [], []
    for _, r in inv.iterrows():
        p = HOURLY / r["source"] / f"{r['station_id']}.parquet"
        if not p.exists():
            continue
        s = pd.read_parquet(p)["value_m"]
        s = s.reindex(time_index)
        v = s.to_numpy(dtype=np.float32)
        tr = s[:TRAIN_END]
        n_train = int(tr.notna().sum())
        if n_train < MIN_TRAIN_YEARS * 8766:
            continue
        mean, std = float(tr.mean()), float(tr.std())
        if not np.isfinite(std) or std < MIN_STD_M:
            print(f"skip {r['source']} {r['station_id']}: std={std:.3f}", file=sys.stderr)
            continue
        # crude despike: beyond 8 sigma of the train distribution -> NaN
        bad = np.abs(v - mean) > 8 * std
        v[bad] = np.nan
        rows.append({
            "source": r["source"], "station_id": str(r["station_id"]), "name": r.get("name", ""),
            "lat": r["lat"], "lon": r["lon"], "domains": r.get("domains", ""), "datum": r.get("datum", ""),
            "mean_m": mean, "std_m": std,
            "n_train": n_train, "n_val": int(s[TRAIN_END:VAL_END].notna().sum()),
            "n_test": int(s[VAL_END:].notna().sum()), "n_despiked": int(bad.sum()),
        })
        mats.append(v)
    values = np.stack(mats)
    np.save(OUT / "values.npy", values)
    np.save(OUT / "time.npy", time_index.values.astype("datetime64[ns]").astype(np.int64))
    st = pd.DataFrame(rows)
    st.index.name = "row"
    st.to_csv(OUT / "stations.csv")
    meta = {"start": str(START), "end": str(END), "train_end": str(TRAIN_END), "val_end": str(VAL_END),
            "n_stations": int(len(st)), "n_hours": int(n_t), "min_years": MIN_YEARS,
            "min_train_years": MIN_TRAIN_YEARS, "min_std_m": MIN_STD_M,
            "valid_fraction": float(np.isfinite(values).mean())}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))
    print(st.groupby("source").agg(n=("station_id", "size"), train_h=("n_train", "sum"),
                                   val_h=("n_val", "sum"), test_h=("n_test", "sum")).to_string())
    print(f"values.npy: {values.nbytes / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
