"""deliverable 08: effect of the same-river upstream discharge mapping (v4_wind_q vs v3_wind_q).

Reads runs/{v3_wind,v3_wind_q,v4_wind_q}/per_station_test.csv (same test window), keeps stations
with >= 720 6 h samples in all three, and writes
  08_compare_per_station.csv   all stations: 1/3/6 h RMSE of the three runs, old/new gauge, change
  08_compare_tables.md         overall / re-mapped stations / by chain / by domain / by type tables
  08_compare_bars.png          6 h RMSE of the three runs for the re-mapped stations, grouped by river
Runs locally (no torch needed).
"""
from __future__ import annotations

import argparse
import sys
import types
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for n, attrs in (("torch", ()), ("data", ("HORIZON", "StationMatrix", "to_torch")), ("model", ("GlobalLSTM",)), ("common", ("HOURLY",))):
    if n not in sys.modules:
        mod = types.ModuleType(n)
        for a in attrs:
            setattr(mod, a, None)
        sys.modules[n] = mod
sys.path.insert(0, str(REPO / "scripts" / "report"))
from error_split import station_type  # noqa: E402

RUNS = [("wind", "v3_wind", "+风（无流量）"), ("old", "v3_wind_q", "+风+流量（HUC8 配站）"), ("new", "v4_wind_q", "+风+流量（同河上游配站）")]
DOMS = ["Louisiana100m", "Galveston100m", "Texas100m"]
TYPES = ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]
CHAIN_OF = {  # station -> river chain label (same lists as scripts/data/remap_same_river.py)
    **{s: "Sabine" for s in ["08026000", "08028500", "08030500"]},
    **{s: "Neches" for s in ["08033500", "08040600", "08041000", "08041780"]},
    **{s: "Trinity" for s in ["08066000", "08066250", "08066500", "08067000", "08067100", "08067250"]},
    **{s: "W Fk San Jacinto" for s in ["08067650", "08068000", "08068090"]},
    **{s: "Buffalo Bayou" for s in ["08073100", "08073500", "08073600", "08073700", "08074000"]},
    **{s: "Brazos" for s in ["08098450", "08108700", "08110200", "08111500", "08111850", "08114000", "08114100", "08116650", "08116850", "08079120"]},
    **{s: "Colorado" for s in ["08161000", "08162000", "08162500", "08162501"]},
    **{s: "Guadalupe" for s in ["08175800", "08176500"]},
    **{s: "Mississippi" for s in ["07374000", "07374525"]},
    **{s: "Atchafalaya" for s in ["07381490", "07381515", "07381600"]},
    **{s: "Amite / Comite" for s in ["07377000", "07378500", "07380120", "07377750", "07377870", "07378000", "07378050"]},
    **{s: "Pearl" for s in ["02489500", "02490193", "02490200", "02492100", "02492519", "02492600", "02492511", "02492700"]},
}


def med_table(df: pd.DataFrame, by: str, order=None) -> pd.DataFrame:
    rows = []
    groups = order if order is not None else sorted(df[by].dropna().unique())
    for g in groups:
        s = df[df[by].astype(str).str.contains(g, regex=False)] if by == "domains" else df[df[by] == g]
        if len(s) == 0:
            continue
        rows.append({by: g, "站数": len(s), **{lab: round(s[f"r6_{k}"].median(), 2) for k, _, lab in RUNS},
                     "变好 ≥0.5 cm": int((s.d_new_old <= -0.5).sum()), "变差 ≥0.5 cm": int((s.d_new_old >= 0.5).sum())})
    return pd.DataFrame(rows)


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "deliverables"))
    ap.add_argument("--min-n", type=int, default=720)
    a = ap.parse_args()
    out = Path(a.out)
    d = {k: pd.read_csv(REPO / "runs" / r / "per_station_test.csv", dtype={"station_id": str}) for k, r, _ in RUNS}
    b = d["old"][["source", "station_id", "domains", "lat", "lon"]].copy()
    ok = np.ones(len(b), bool)
    for k, df in d.items():
        assert (df.station_id.to_numpy() == b.station_id.to_numpy()).all()
        for h in (1, 3, 6):
            b[f"r{h}_{k}"] = df[f"rmse_{h}h_cm"]
        b[f"n_{k}"] = df.n_6h
        ok &= df.n_6h.to_numpy() >= a.min_n
    b = b[ok].copy()
    cen = pd.read_csv(REPO / "config" / "stations_census.csv", dtype=str).drop_duplicates(["source", "station_id"])
    cen["county"] = cen.extra.str.extract(r"county=(\d+)")
    b = b.merge(cen[["source", "station_id", "name", "site_type", "county"]], on=["source", "station_id"], how="left")
    b["type"] = b.apply(station_type, axis=1)
    m_new = pd.read_csv(REPO / "config" / "station_discharge_map.csv", dtype=str)
    b = b.merge(m_new[["source", "station_id", "assignment", "gauge_id", "gauge_name"]], on=["source", "station_id"], how="left")
    b["chain"] = b.station_id.map(CHAIN_OF)
    b["remapped"] = b.assignment.eq("same_river_upstream")
    b["d_new_old"] = b.r6_new - b.r6_old
    b["d_new_wind"] = b.r6_new - b.r6_wind
    b["d_old_wind"] = b.r6_old - b.r6_wind
    b.to_csv(out / "08_compare_per_station.csv", index=False)

    lines = ["# 08 流量改配同河上游站之后的对比（表格）", "",
             f"测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），{len(b)} 个站在三组里都有 ≥ {a.min_n} 个样本。RMSE 单位 cm，各站中位数。", ""]
    lines += ["## 全部站", "", md(pd.DataFrame([{"提前": f"{h} h", **{lab: round(b[f"r{h}_{k}"].median(), 2) for k, _, lab in RUNS}} for h in (1, 3, 6)])), ""]
    r = b[b.remapped]
    lines += [f"## 改配的 {len(r)} 个站（same_river_upstream）", "",
              md(pd.DataFrame([{"提前": f"{h} h", **{lab: round(r[f"r{h}_{k}"].median(), 2) for k, _, lab in RUNS}} for h in (1, 3, 6)])), "",
              f"6 h：比 HUC8 配站 变好 ≥ 0.5 cm 的站 {int((r.d_new_old <= -0.5).sum())}，变差 ≥ 0.5 cm 的站 {int((r.d_new_old >= 0.5).sum())}；"
              f"比不加流量 变好 {int((r.d_new_wind <= -0.5).sum())}，变差 {int((r.d_new_wind >= 0.5).sum())}。", ""]
    lines += ["## 改配的站按河流", "", md(med_table(r, "chain")), ""]
    lines += ["## 没改配的站（应当基本不变）", "",
              md(pd.DataFrame([{"提前": f"{h} h", **{lab: round(b[~b.remapped][f"r{h}_{k}"].median(), 2) for k, _, lab in RUNS}} for h in (1, 3, 6)])), ""]
    lines += ["## 按 domain（全部站）", "", md(med_table(b, "domains", DOMS)), ""]
    lines += ["## 按站点类型（全部站）", "", md(med_table(b, "type", TYPES)), ""]
    rr = r.sort_values("d_new_old")
    cols = ["station_id", "name", "chain", "gauge_name", "r6_wind", "r6_old", "r6_new", "d_new_old"]
    tab = rr[cols].copy(); tab.columns = ["站号", "站名", "河流", "新配的上游站", "+风", "HUC8 配站", "同河上游", "新 − 旧"]
    for c in ["+风", "HUC8 配站", "同河上游", "新 − 旧"]:
        tab[c] = tab[c].round(2)
    lines += ["## 改配的站逐站（按 6 h 变化排序，负 = 变好）", "", md(tab), ""]
    big = b[~b.remapped].reindex(b[~b.remapped].d_new_old.abs().sort_values(ascending=False).index).head(10)
    tab2 = big[["station_id", "name", "type", "r6_old", "r6_new", "d_new_old"]].copy(); tab2.columns = ["站号", "站名", "类型", "HUC8 配站", "同河上游", "新 − 旧"]
    for c in ["HUC8 配站", "同河上游", "新 − 旧"]:
        tab2[c] = tab2[c].round(2)
    lines += ["## 没改配却变化最大的 10 个站（训练随机性的量级）", "", md(tab2), ""]
    (out / "08_compare_tables.md").write_text("\n".join(lines), encoding="utf-8")

    # bars: re-mapped stations grouped by chain
    plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    chains = [c for c in r.chain.value_counts().index]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    x = np.arange(len(chains)); w = 0.27
    for i, (k, _, lab) in enumerate(RUNS):
        ax.bar(x + (i - 1) * w, [r[r.chain == c][f"r6_{k}"].median() for c in chains], w, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([f"{c}\n({int((r.chain == c).sum())})" for c in chains], fontsize=9)
    ax.set_ylabel("6 h RMSE 中位数 (cm)"); ax.set_title("改配同河上游流量站的站，按河流"); ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "08_compare_bars.png", dpi=150); plt.close(fig)
    print("\n".join(lines[:40]))
    print("->", out)


if __name__ == "__main__":
    main()
