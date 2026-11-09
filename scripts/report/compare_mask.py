"""deliverable 09 (section 10): global model with the wind input switched off at the listed stations (v6_wind_q)
vs the same global model with wind everywhere (v4_wind_q) and the water-level-only model (v3_obs).
Writes deliverables/09_mask_tables.md and 09_mask_per_station.csv. Runs locally.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "deliverables"


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in df.iterrows()])


def main(min_n: int = 720) -> None:
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    off = pd.read_csv(REPO / "config" / "stations_wind_hurts.csv", dtype=str)
    runs = {"obs": "v3_obs", "all": "v4_wind_q", "mask": "v6_wind_q"}
    d = {k: pd.read_csv(REPO / "runs" / r / "per_station_test.csv", dtype={"station_id": str}) for k, r in runs.items()}
    b = d["all"][["source", "station_id", "domains"]].merge(g[["source", "station_id", "name", "type"]], on=["source", "station_id"], how="left")
    for k in runs:
        for h in (1, 3, 6):
            b[f"r{h}_{k}"] = d[k][f"rmse_{h}h_cm"].to_numpy()
        b[f"n_{k}"] = d[k].n_6h.to_numpy()
    b = b[(b.n_obs >= min_n) & (b.n_all >= min_n) & (b.n_mask >= min_n)].copy()
    b["wind_off"] = [(s, i) in set(zip(off.source, off.station_id)) for s, i in zip(b.source, b.station_id)]
    b["d_mask_all"] = b.r6_mask - b.r6_all
    b.to_csv(OUT / "09_mask_per_station.csv", index=False)

    def row(label, s):
        return {"分组": label, "站数": len(s), "只用水位": round(s.r6_obs.median(), 2), "全局模型，所有站给风": round(s.r6_all.median(), 2),
                "全局模型，15 站不给风": round(s.r6_mask.median(), 2), "差 (6 h)": f"{(s.r6_mask - s.r6_all).median():+.2f}",
                "变好 ≥0.5": int((s.d_mask_all <= -0.5).sum()), "变差 ≥0.5": int((s.d_mask_all >= 0.5).sum())}
    L = ["# 09 附表：全局模型，15 个站的风输入置零（表格）", "",
         f"测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），{len(b)} 个站。6 h RMSE 各站中位数，cm。", ""]
    L += ["## 全部 / 置零的站 / 其余站", "", md(pd.DataFrame([row("全部", b), row("风置零的 15 站", b[b.wind_off]), row("其余站", b[~b.wind_off])])), ""]
    L += ["## 按站点类型", "", md(pd.DataFrame([row(t, b[b.type == t]) for t in ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]])), ""]
    tab = b[b.wind_off].sort_values("r6_all", ascending=False)[["station_id", "name", "r6_obs", "r6_all", "r6_mask", "d_mask_all"]].round(2)
    tab.columns = ["站号", "站名", "只用水位", "所有站给风", "15 站不给风", "差"]
    L += ["## 风置零的 15 个站逐站", "", md(tab), ""]
    L += ["## 1 / 3 / 6 h（全部站中位数）", "", md(pd.DataFrame([{"提前": f"{h} h", "只用水位": round(b[f"r{h}_obs"].median(), 2), "所有站给风": round(b[f"r{h}_all"].median(), 2), "15 站不给风": round(b[f"r{h}_mask"].median(), 2)} for h in (1, 3, 6)])), ""]
    u = b[~b.wind_off]
    L += [f"其余 {len(u)} 站两次训练之间的差异：中位 {u.d_mask_all.abs().median():.2f} cm，90% 分位 {u.d_mask_all.abs().quantile(.9):.2f} cm，最大 {u.d_mask_all.abs().max():.2f} cm（训练随机性的量级）。"]
    (OUT / "09_mask_tables.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
