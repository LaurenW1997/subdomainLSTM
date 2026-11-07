"""Collect per-station meta.json files into one table and print a data-length summary."""
from __future__ import annotations

import json

import pandas as pd

from common import DATA_ROOT, HOURLY


def main() -> None:
    rows = [json.loads(p.read_text()) for p in HOURLY.glob("*/*.meta.json")]
    df = pd.DataFrame(rows)
    out = DATA_ROOT / "data_inventory.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 200)
    print(f"{len(df)} stations with hourly files -> {out}\n")
    g = df.groupby("source")["years_valid"]
    print(g.describe()[["count", "min", "25%", "50%", "75%", "max"]].round(1).to_string())
    print("\nstations by valid years:")
    bins = [0, 1, 3, 5, 10, 15, 100]
    print(pd.crosstab(df["source"], pd.cut(df["years_valid"], bins)).to_string())
    dom = df["domains"].fillna("").str.get_dummies(";")
    print("\nper domain, stations with >= 3 valid years:")
    for c in dom.columns:
        m = (dom[c] == 1) & (df["years_valid"] >= 3)
        print(f"  {c:14s} {int(m.sum()):4d}  (total hours {int(df.loc[m, 'n_valid'].sum()):,})")


if __name__ == "__main__":
    main()
