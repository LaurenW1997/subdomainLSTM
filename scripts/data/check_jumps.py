"""Scan hourly series for persistent level shifts (datum jumps).

For every <source>/<station>.parquet: daily medians -> largest absolute change
between the median of the 30 days before and the 30 days after each day
(step size), plus overall range and std. Writes data/datum_jumps.csv sorted by
step size and plots the top-N daily series to data/datum_jumps.png.

Usage: python check_jumps.py [--top 24] [--min-step 1.0]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import DATA_ROOT, HOURLY

WIN = 30  # days each side


def scan_one(p: Path) -> dict | None:
    s = pd.read_parquet(p)["value_m"].dropna()
    if len(s) < 24 * 60:
        return None
    d = s.resample("1D").median().dropna()
    if len(d) < 3 * WIN:
        return None
    # medians of the 30 days before / after each day
    before = d.rolling(WIN, min_periods=WIN // 2).median()
    after = d[::-1].rolling(WIN, min_periods=WIN // 2).median()[::-1].shift(-1)
    step = (after - before).dropna()
    i = step.abs().idxmax()
    meta = json.loads(p.with_suffix(".meta.json").read_text()) if p.with_suffix(".meta.json").exists() else {}
    return {"source": p.parent.name, "station_id": p.stem, "n_days": len(d), "std_m": float(d.std()),
            "min_m": float(d.min()), "max_m": float(d.max()), "max_step_m": float(step.loc[i]),
            "step_date": i.date().isoformat(), "level_before": float(before.loc[i]), "level_after": float(after.loc[i]),
            "datum": meta.get("datum", ""), "name": meta.get("name", "")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--min-step", type=float, default=1.0)
    a = ap.parse_args()
    rows = []
    for p in sorted(HOURLY.glob("*/*.parquet")):
        if p.name.endswith(".pred.parquet"):
            continue
        try:
            r = scan_one(p)
        except Exception as e:  # noqa: BLE001
            print("skip", p, e); continue
        if r:
            rows.append(r)
    df = pd.DataFrame(rows)
    df["abs_step"] = df.max_step_m.abs()
    df = df.sort_values("abs_step", ascending=False).drop(columns="abs_step")
    out = Path(DATA_ROOT) / "datum_jumps.csv"
    df.to_csv(out, index=False)
    flagged = df[df.max_step_m.abs() >= a.min_step]
    print(f"{len(df)} stations scanned, {len(flagged)} with |step| >= {a.min_step} m -> {out}")
    print(flagged.groupby("source").size().to_string())
    print(flagged.head(40).round(2).to_string(index=False))

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    top = df.head(a.top)
    n = len(top); cols = 4; rws = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rws, cols, figsize=(5 * cols, 2.6 * rws), squeeze=False)
    for ax, (_, r) in zip(axes.ravel(), top.iterrows()):
        s = pd.read_parquet(HOURLY / r.source / f"{r.station_id}.parquet")["value_m"].resample("1D").median()
        ax.plot(s.index, s.values, lw=.6)
        ax.axvline(pd.Timestamp(r.step_date), color="r", lw=.8, ls="--")
        ax.set_title(f"{r.source} {r.station_id} step {r.max_step_m:+.1f} m @ {r.step_date}", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.tight_layout(); fig.savefig(Path(DATA_ROOT) / "datum_jumps.png", dpi=110)
    print("plot ->", Path(DATA_ROOT) / "datum_jumps.png")


if __name__ == "__main__":
    main()
