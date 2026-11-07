"""Scan hourly series for persistent level shifts (datum jumps) and sentinels.

For every <source>/<station>.parquet (daily medians):
  * step30   : largest change between the 30-day medians before/after a day
               (catches datum jumps but also floods);
  * shift365 : change of the 10th percentile over 365 days before vs after that
               same day (a datum jump moves the low-water baseline, a flood
               does not);
  * wy_boundary : step date falls on the USGS water-year boundary (Sep 25-Oct 5),
               where NWIS records typically switch gauge datum;
  * n_sentinel : values outside [-60, 200] m (e.g. -999999 ft, 1000 ft fills).
Classification: sentinel | datum_jump | flood | ok.
Writes data/datum_jumps.csv and plots the datum_jump/sentinel stations to
data/datum_jumps.png.

Usage: python check_jumps.py [--min-step 1.0] [--plot-n 32]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import DATA_ROOT, HOURLY

WIN = 30
LO, HI = -60.0, 200.0


def scan_one(p: Path) -> dict | None:
    s = pd.read_parquet(p)["value_m"].dropna()
    n_sent = int(((s < LO) | (s > HI)).sum())
    s = s[(s >= LO) & (s <= HI)]
    if len(s) < 24 * 60:
        return None
    d = s.resample("1D").median().dropna()
    if len(d) < 3 * WIN:
        return None
    before = d.rolling(WIN, min_periods=WIN // 2).median()
    after = d[::-1].rolling(WIN, min_periods=WIN // 2).median()[::-1].shift(-1)
    step = (after - before).dropna()
    if step.empty:
        return None
    i = step.abs().idxmax()
    yb = d.loc[i - pd.Timedelta(days=365): i - pd.Timedelta(days=1)]
    ya = d.loc[i + pd.Timedelta(days=1): i + pd.Timedelta(days=365)]
    shift365 = float(ya.quantile(0.1) - yb.quantile(0.1)) if len(yb) > 60 and len(ya) > 60 else np.nan
    meta_p = p.with_suffix(".meta.json")
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    wy = (i.month == 9 and i.day >= 25) or (i.month == 10 and i.day <= 5)
    return {"source": p.parent.name, "station_id": p.stem, "name": meta.get("name", ""), "datum": meta.get("datum", ""),
            "n_days": len(d), "std_m": float(d.std()), "min_m": float(d.min()), "max_m": float(d.max()),
            "step30_m": float(step.loc[i]), "step_date": i.date().isoformat(), "shift365_m": shift365,
            "level_before": float(before.loc[i]), "level_after": float(after.loc[i]),
            "wy_boundary": bool(wy), "n_sentinel": n_sent}


def classify(r: pd.Series, min_step: float) -> str:
    if r.n_sentinel > 0:
        return "sentinel"
    if abs(r.step30_m) < min_step:
        return "ok"
    consistent = np.isfinite(r.shift365_m) and np.sign(r.shift365_m) == np.sign(r.step30_m) \
        and abs(r.shift365_m) >= 0.6 * abs(r.step30_m)
    if consistent and (r.wy_boundary or abs(r.step30_m) >= 3):
        return "datum_jump"
    if consistent:
        return "shift_unclear"
    return "flood"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-step", type=float, default=1.0)
    ap.add_argument("--plot-n", type=int, default=32)
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
    df["flag"] = df.apply(classify, axis=1, min_step=a.min_step)
    df["abs_step"] = df.step30_m.abs()
    df = df.sort_values(["flag", "abs_step"], ascending=[True, False]).drop(columns="abs_step")
    out = Path(DATA_ROOT) / "datum_jumps.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} stations scanned -> {out}")
    print(df.groupby(["flag", "source"]).size().unstack(fill_value=0).to_string())
    cols = ["source", "station_id", "name", "n_days", "step30_m", "shift365_m", "step_date", "wy_boundary", "n_sentinel", "min_m", "max_m"]
    for f in ("sentinel", "datum_jump", "shift_unclear"):
        sub = df[df.flag == f]
        print(f"\n--- {f}: {len(sub)}")
        print(sub[cols].head(45).round(2).to_string(index=False))

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    top = df[df.flag.isin(["datum_jump", "sentinel", "shift_unclear"])].head(a.plot_n)
    n = len(top); ncol = 4; nrow = max(1, int(np.ceil(n / ncol)))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5 * ncol, 2.6 * nrow), squeeze=False)
    for ax, (_, r) in zip(axes.ravel(), top.iterrows()):
        s = pd.read_parquet(HOURLY / r.source / f"{r.station_id}.parquet")["value_m"]
        s = s[(s >= LO) & (s <= HI)].resample("1D").median()
        ax.plot(s.index, s.values, lw=.6)
        ax.axvline(pd.Timestamp(r.step_date), color="r", lw=.8, ls="--")
        ax.set_title(f"[{r.flag}] {r.source} {r.station_id} step {r.step30_m:+.1f} m @ {r.step_date}", fontsize=7)
        ax.tick_params(labelsize=7)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.tight_layout(); fig.savefig(Path(DATA_ROOT) / "datum_jumps.png", dpi=110)
    print("plot ->", Path(DATA_ROOT) / "datum_jumps.png")


if __name__ == "__main__":
    main()
