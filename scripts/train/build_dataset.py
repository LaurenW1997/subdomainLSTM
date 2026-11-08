"""Assemble the per-station hourly parquet files into one training matrix.

Output (DATA_ROOT/<out>/):
  values.npy    float32 [n_stations, n_hours], NaN = missing, UTC hourly from START to END
  time.npy      int64 ns timestamps of the hour axis
  stations.csv  one row per matrix row: source, station_id, lat, lon, domains, datum,
                mean/std used for normalisation (train period only), valid counts per split
  excluded.csv  every inventory station that did NOT make it, with the reason
  meta.json     split boundaries, thresholds

Cleaning (v2): values outside [RANGE_LO, RANGE_HI] m are fill values -> NaN;
datum corrections from config/datum_corrections.csv (shift or drop the segment
before a break date); optional whole-source exclusion; isolated-spike filter
(a single hour that departs from the 5-hour running median by more than
max(SPIKE_MIN_M, SPIKE_K x typical hourly change) AND is a local extreme).
Sustained highs (real floods) are kept.
Selection: >= MIN_YEARS valid hours overall, >= MIN_TRAIN_YEARS inside the
training period, and a non-degenerate train-period standard deviation.

Usage: python build_dataset.py [--out dataset_v2] [--exclude-source USACE_SWG ...]
                               [--corrections ../../config/datum_corrections.csv]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data/ywan245/subdomainLSTM/data"))
HOURLY = DATA_ROOT / "hourly"
REPO = Path(__file__).resolve().parents[2]

START = pd.Timestamp("2010-01-01 00:00")
END = pd.Timestamp("2026-11-07 00:00")
TRAIN_END = pd.Timestamp("2022-12-31 23:00")   # train: 2010-2022
VAL_END = pd.Timestamp("2023-12-31 23:00")     # val: 2023, test: 2024-
MIN_YEARS = 3.0
MIN_TRAIN_YEARS = 1.0
MIN_STD_M = 0.02
RANGE_LO, RANGE_HI = -60.0, 200.0             # metres; anything outside is a fill value
SPIKE_MIN_M = 0.5        # metres; never flag departures smaller than this
SPIKE_K = 10.0           # x the station's typical (median) absolute hourly change


def despike(s: pd.Series) -> pd.Series:
    """Remove isolated one-hour spikes only; keep sustained extremes."""
    v = s.to_numpy(dtype=np.float64)
    rm = s.rolling(5, center=True, min_periods=3).median().to_numpy()
    dev = v - rm
    step = np.nanmedian(np.abs(np.diff(v[np.isfinite(v)]))) if np.isfinite(v).sum() > 10 else 0.0
    thr = max(SPIKE_MIN_M, SPIKE_K * step)
    prev = np.roll(v, 1); nxt = np.roll(v, -1)
    local_ext = ((v > prev) & (v > nxt)) | ((v < prev) & (v < nxt))
    bad = np.isfinite(dev) & (np.abs(dev) > thr) & local_ext
    out = s.copy(); out[bad] = np.nan
    return out


def apply_corrections(s: pd.Series, corr: pd.DataFrame) -> tuple[pd.Series, str]:
    notes = []
    for _, c in corr.iterrows():
        brk = pd.Timestamp(c["break_date"])
        if c["action"] == "shift_before":
            s = s.copy(); s[s.index < brk] = s[s.index < brk] + float(c["offset_m"])
            notes.append(f"shift_before {brk.date()} {float(c['offset_m']):+.3f}")
        elif c["action"] == "drop_before":
            s = s.copy(); s[s.index < brk] = np.nan
            notes.append(f"drop_before {brk.date()}")
    return s, "; ".join(notes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dataset_v2")
    ap.add_argument("--exclude-source", action="append", default=[])
    ap.add_argument("--corrections", default=str(REPO / "config" / "datum_corrections.csv"))
    a = ap.parse_args()
    out = DATA_ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    corr_all = pd.read_csv(a.corrections, dtype={"station_id": str})
    inv = pd.read_csv(DATA_ROOT / "data_inventory.csv", dtype={"station_id": str})
    time_index = pd.date_range(START, END, freq="1h")
    rows, mats, excluded = [], [], []

    def exclude(r, reason, detail=""):
        excluded.append({"source": r["source"], "station_id": r["station_id"], "name": r.get("name", ""),
                         "domains": r.get("domains", ""), "reason": reason, "detail": detail})

    for _, r in inv.iterrows():
        if r["source"] in a.exclude_source:
            exclude(r, "source_excluded", r["source"]); continue
        if r["years_valid"] < MIN_YEARS:
            exclude(r, "too_short", f"{r['years_valid']:.1f} valid years < {MIN_YEARS}"); continue
        p = HOURLY / r["source"] / f"{r['station_id']}.parquet"
        if not p.exists():
            exclude(r, "no_file"); continue
        s = pd.read_parquet(p)["value_m"]
        n_range = int(((s < RANGE_LO) | (s > RANGE_HI)).sum())
        s = s.where((s >= RANGE_LO) & (s <= RANGE_HI))
        corr = corr_all[(corr_all.source == r["source"]) & (corr_all.station_id == str(r["station_id"]))]
        corr_note = ""
        if len(corr):
            s, corr_note = apply_corrections(s, corr)
        s = s.reindex(time_index)
        n_before = int(s.notna().sum())
        s = despike(s)
        n_spk = n_before - int(s.notna().sum())
        v = s.to_numpy(dtype=np.float32)
        tr = s[:TRAIN_END]
        n_train = int(tr.notna().sum())
        if n_train < MIN_TRAIN_YEARS * 8766:
            exclude(r, "too_short_in_train", f"{n_train / 8766:.1f} valid years in 2010-2022 < {MIN_TRAIN_YEARS}"); continue
        mean, std = float(tr.mean()), float(tr.std())
        if not np.isfinite(std) or std < MIN_STD_M:
            exclude(r, "flat", f"train std {std:.3f} m < {MIN_STD_M}"); continue
        rows.append({
            "source": r["source"], "station_id": str(r["station_id"]), "name": r.get("name", ""),
            "lat": r["lat"], "lon": r["lon"], "domains": r.get("domains", ""), "datum": r.get("datum", ""),
            "mean_m": mean, "std_m": std,
            "n_train": n_train, "n_val": int(s[TRAIN_END:VAL_END].notna().sum()),
            "n_test": int(s[VAL_END:].notna().sum()), "n_despiked": n_spk,
            "n_range_filtered": n_range, "correction": corr_note,
        })
        mats.append(v)
    values = np.stack(mats)
    np.save(out / "values.npy", values)
    np.save(out / "time.npy", time_index.values.astype("datetime64[ns]").astype(np.int64))
    st = pd.DataFrame(rows); st.index.name = "row"
    st.to_csv(out / "stations.csv")
    ex = pd.DataFrame(excluded); ex.to_csv(out / "excluded.csv", index=False)
    meta = {"start": str(START), "end": str(END), "train_end": str(TRAIN_END), "val_end": str(VAL_END),
            "n_stations": int(len(st)), "n_excluded": int(len(ex)), "n_hours": int(len(time_index)),
            "min_years": MIN_YEARS, "min_train_years": MIN_TRAIN_YEARS, "min_std_m": MIN_STD_M,
            "range_m": [RANGE_LO, RANGE_HI], "spike_min_m": SPIKE_MIN_M, "spike_k": SPIKE_K,
            "excluded_sources": a.exclude_source, "corrections": a.corrections,
            "n_corrected_stations": int((st.correction != "").sum()),
            "valid_fraction": float(np.isfinite(values).mean())}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))
    print(st.groupby("source").agg(n=("station_id", "size"), train_h=("n_train", "sum"),
                                   val_h=("n_val", "sum"), test_h=("n_test", "sum"),
                                   range_filtered=("n_range_filtered", "sum"), despiked=("n_despiked", "sum")).to_string())
    print("excluded by reason:"); print(ex.groupby(["reason", "source"]).size().unstack(fill_value=0).to_string())
    print("max std by source (m):"); print(st.groupby("source").std_m.max().round(2).to_string())
    print(f"values.npy: {values.nbytes / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
