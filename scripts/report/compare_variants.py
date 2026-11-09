"""Compare any set of runs against a reference run, per station (deliverable 13: rain and architecture variants).

Usage: python compare_variants.py --ref v6_wind_q --runs v7_rain_p15 v7_rain_p v7_rain_p15_past --labels "rain 15 km + future" "rain point + future" "rain 15 km, past only" --out deliverables/13_rain
Writes <out>_tables.md and <out>_per_station.csv. Runs locally.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
TYPES = ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]
DOMS = ["Louisiana100m", "Galveston100m", "Texas100m"]


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in df.iterrows()])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="v6_wind_q"); ap.add_argument("--ref-label", default="当前模型（v6）")
    ap.add_argument("--runs", nargs="+", required=True); ap.add_argument("--labels", nargs="+", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--min-n", type=int, default=720)
    ap.add_argument("--title", default="变体对比")
    a = ap.parse_args()
    assert len(a.runs) == len(a.labels)
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    ref = pd.read_csv(REPO / "runs" / a.ref / "per_station_test.csv", dtype={"station_id": str})
    b = ref[["source", "station_id", "domains"]].merge(g[["source", "station_id", "name", "type"]], on=["source", "station_id"], how="left")
    for h in (1, 3, 6):
        b[f"r{h}_ref"] = ref[f"rmse_{h}h_cm"].to_numpy()
    ok = ref.n_6h.to_numpy() >= a.min_n
    keys = []
    for run, lab in zip(a.runs, a.labels):
        d = pd.read_csv(REPO / "runs" / run / "per_station_test.csv", dtype={"station_id": str})
        assert (d.station_id.to_numpy() == ref.station_id.to_numpy()).all(), run
        k = run
        for h in (1, 3, 6):
            b[f"r{h}_{k}"] = d[f"rmse_{h}h_cm"].to_numpy()
        ok &= d.n_6h.to_numpy() >= a.min_n
        keys.append((k, lab))
    b = b[ok].copy()
    for k, _ in keys:
        b[f"d6_{k}"] = b[f"r6_{k}"] - b.r6_ref
    b.to_csv(Path(a.out + "_per_station.csv"), index=False)

    def row(label, s):
        r = {"分组": label, "站数": len(s), a.ref_label: round(s.r6_ref.median(), 2)}
        for k, lab in keys:
            r[lab] = f"{s[f'r6_{k}'].median():.2f} ({(s[f'r6_{k}'] - s.r6_ref).median():+.2f})"
        return r

    def counts(label, s):
        r = {"分组": label, "站数": len(s)}
        for k, lab in keys:
            r[lab] = f"{int((s[f'd6_{k}'] <= -0.5).sum())} 好 / {int((s[f'd6_{k}'] >= 0.5).sum())} 差"
        return r

    L = [f"# {a.title}", "", f"测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），{len(b)} 个站所有 run 都有 ≥ {a.min_n} 个样本。",
         f"6 h RMSE 各站中位数，cm；括号里是和 {a.ref_label} 的中位差（负 = 变好）。", ""]
    L += ["## 全部站 / 按站点类型", "", md(pd.DataFrame([row("全部", b)] + [row(t, b[b.type == t]) for t in TYPES if (b.type == t).sum() >= 5])), ""]
    L += ["## 变好 / 变差 0.5 cm 以上的站数", "", md(pd.DataFrame([counts("全部", b)] + [counts(t, b[b.type == t]) for t in TYPES if (b.type == t).sum() >= 5])), ""]
    L += ["## 按 domain", "", md(pd.DataFrame([row(dm, b[b.domains.astype(str).str.contains(dm)]) for dm in DOMS])), ""]
    L += ["## 1 / 3 / 6 h（全部站中位数）", "", md(pd.DataFrame([{"提前": f"{h} h", a.ref_label: round(b[f"r{h}_ref"].median(), 2), **{lab: round(b[f"r{h}_{k}"].median(), 2) for k, lab in keys}} for h in (1, 3, 6)])), ""]
    for k, lab in keys:
        t = b.reindex(b[f"d6_{k}"].sort_values().index).head(12)[["station_id", "name", "type", "r6_ref", f"r6_{k}", f"d6_{k}"]].round(2)
        t.columns = ["站号", "站名", "类型", a.ref_label, lab, "差"]
        L += [f"## {lab}：变好最多的 12 个站", "", md(t), ""]
    Path(a.out + "_tables.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
