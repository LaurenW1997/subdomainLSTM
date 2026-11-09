"""deliverable 09: one global model (v4_wind_q) vs two group models (v5_tidal + v5_river).

Runs compared (same test window, origins <= 2025-12-31T17):
  obs       v3_obs         global, water level only
  v4        v4_wind_q      global, wind + future wind + discharge (same-river upstream)
  tidal     v5_tidal       tidal group only (tide gauges, marsh, lakes, estuaries): wind + future wind, no discharge
  river     v5_river       river group only (rivers, urban creeks): discharge, no wind
  river_wq  v5_river_wq    river group only: wind + future wind + discharge (isolates grouping from input change)
"split" = v5_tidal for tidal stations + v5_river for river stations.
Writes 09_groups_per_station.csv, 09_groups_tables.md, 09_groups_bars.png. Runs locally.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RUNS = {"obs": "v3_obs", "v4": "v4_wind_q", "tidal": "v5_tidal", "river": "v5_river", "river_wq": "v5_river_wq"}
LAB = {"obs": "只用水位（全局）", "v4": "v4 全局（风+流量）", "split": "分组模型（潮汐组：风；河流组：流量）", "river_wq": "河流组（风+流量）"}
TYPES = ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]
DOMS = ["Louisiana100m", "Galveston100m", "Texas100m"]
BIG = "Mississippi|Atchafalaya|Brazos Rv|Sabine Rv|Neches Rv|Trinity Rv|Colorado Rv|Pearl River"


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in df.iterrows()])


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "deliverables")); ap.add_argument("--min-n", type=int, default=720)
    a = ap.parse_args(); out = Path(a.out)
    d = {k: pd.read_csv(REPO / "runs" / r / "per_station_test.csv", dtype={"station_id": str}) for k, r in RUNS.items()}
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    b = d["v4"][["source", "station_id", "domains", "lat", "lon"]].merge(g[["source", "station_id", "name", "type", "group"]], on=["source", "station_id"], how="left")
    for k in ("obs", "v4"):
        for h in (1, 3, 6):
            b[f"r{h}_{k}"] = d[k][f"rmse_{h}h_cm"].to_numpy()
        b[f"n_{k}"] = d[k].n_6h.to_numpy()
    # group runs: merge by station key
    for k in ("tidal", "river", "river_wq"):
        s = d[k][["source", "station_id"] + [f"rmse_{h}h_cm" for h in (1, 3, 6)] + ["n_6h"]].rename(columns={**{f"rmse_{h}h_cm": f"r{h}_{k}" for h in (1, 3, 6)}, "n_6h": f"n_{k}"})
        b = b.merge(s, on=["source", "station_id"], how="left")
    for h in (1, 3, 6):
        b[f"r{h}_split"] = np.where(b.group == "tidal", b[f"r{h}_tidal"], b[f"r{h}_river"])
    b["n_split"] = np.where(b.group == "tidal", b.n_tidal, b.n_river)
    ok = (b.n_obs >= a.min_n) & (b.n_v4 >= a.min_n) & (b.n_split >= a.min_n)
    b = b[ok].copy()
    b["d_split_v4"] = b.r6_split - b.r6_v4
    b["d_split_obs"] = b.r6_split - b.r6_obs
    b["big_river"] = b.name.str.contains(BIG, regex=True, na=False) & (b.group == "river")
    b.to_csv(out / "09_groups_per_station.csv", index=False)

    def row(label, s, keys=("obs", "v4", "split")):
        r = {"分组": label, "站数": len(s)}
        for k in keys:
            r[LAB[k] if k in LAB else k] = round(s[f"r6_{k}"].median(), 2)
        r["分组 − v4 (6 h)"] = f"{(s.r6_split - s.r6_v4).median():+.2f}"
        r["变好 ≥0.5"] = int((s.d_split_v4 <= -0.5).sum()); r["变差 ≥0.5"] = int((s.d_split_v4 >= 0.5).sum())
        r["< 5 cm 的站 (v4 → 分组)"] = f"{(s.r6_v4 < 5).mean()*100:.0f}% → {(s.r6_split < 5).mean()*100:.0f}%"
        return r

    L = ["# 09 一个全局模型 对 两个分组模型（表格）", "",
         f"测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），{len(b)} 个站三组都有 ≥ {a.min_n} 个样本。6 h RMSE 各站中位数，cm。", "",
         "分组模型：潮汐组（潮位站、湿地、湖、河口，674 站）只用水位 + 过去和未来的风；河流组（河流、城市溪流，336 站）只用水位 + 同河上游流量，不用风。", ""]
    L += ["## 全部站", "", md(pd.DataFrame([row("全部", b), row("潮汐组", b[b.group == "tidal"]), row("河流组", b[b.group == "river"]), row("其中大河站", b[b.big_river])])), ""]
    L += ["## 按站点类型", "", md(pd.DataFrame([row(t, b[b.type == t]) for t in TYPES if (b.type == t).sum() >= 5])), ""]
    L += ["## 按 domain", "", md(pd.DataFrame([row(dm, b[b.domains.astype(str).str.contains(dm)]) for dm in DOMS])), ""]
    L += ["## 1 / 3 / 6 h（全部站中位数）", "", md(pd.DataFrame([{"提前": f"{h} h", **{LAB[k]: round(b[f"r{h}_{k}"].median(), 2) for k in ("obs", "v4", "split")}} for h in (1, 3, 6)])), ""]
    # river group: is it the grouping or the removal of wind?
    rg = b[b.group == "river"].copy()
    rows = []
    for label, s in (("河流组全部", rg), ("大河站", rg[rg.big_river]), ("河流 / 运河（非大河）", rg[(rg.type == "river / canal") & ~rg.big_river]), ("Houston 城市溪流", rg[rg.type == "urban creek (Houston)"])):
        rows.append({"分组": label, "站数": len(s), "只用水位（全局）": round(s.r6_obs.median(), 2), "v4 全局（风+流量）": round(s.r6_v4.median(), 2),
                     "河流组（风+流量）": round(s.r6_river_wq.median(), 2), "河流组（只流量，无风）": round(s.r6_river.median(), 2)})
    L += ["## 河流组：分组的作用 和 去掉风的作用 分开看", "", md(pd.DataFrame(rows)), "",
          "“河流组（风+流量）”和 v4 的差别只在于单独训练；“河流组（只流量）”再去掉风。", ""]
    big = b[b.big_river].sort_values("r6_v4", ascending=False)[["station_id", "name", "r6_obs", "r6_v4", "r6_river_wq", "r6_split", "d_split_v4"]].round(2)
    big.columns = ["站号", "站名", "只用水位", "v4 全局", "河流组（风+流量）", "河流组（只流量）", "分组 − v4"]
    L += ["## 大河站逐站（6 h RMSE，cm）", "", md(big), ""]
    ch = b.reindex(b.d_split_v4.abs().sort_values(ascending=False).index).head(15)[["station_id", "name", "type", "r6_v4", "r6_split", "d_split_v4"]].round(2)
    ch.columns = ["站号", "站名", "类型", "v4 全局", "分组", "分组 − v4"]
    L += ["## 变化最大的 15 个站", "", md(ch), ""]
    (out / "09_groups_tables.md").write_text("\n".join(L), encoding="utf-8")

    plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ts = [t for t in TYPES if (b.type == t).sum() >= 5]; x = np.arange(len(ts)); w = 0.27
    for i, k in enumerate(("obs", "v4", "split")):
        ax.bar(x + (i - 1) * w, [b[b.type == t][f"r6_{k}"].median() for t in ts], w, label=LAB[k])
    ax.set_xticks(x); ax.set_xticklabels([f"{t}\n({int((b.type == t).sum())})" for t in ts], fontsize=9)
    ax.set_ylabel("6 h RMSE 中位数 (cm)"); ax.set_title("一个全局模型 对 两个分组模型，按站点类型"); ax.legend(fontsize=9); ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(out / "09_groups_bars.png", dpi=150); plt.close(fig)
    print("\n".join(L[:30])); print("->", out)


if __name__ == "__main__":
    main()
