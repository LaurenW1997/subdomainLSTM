"""RMSE of one model by station type, inside and outside the hurricane periods, at 1, 3 and 6 h lead.

Reads runs/<run>/stale_origin.csv (eval_stale_origin.py; rows with the newest observation in hand, k = 0), where the
groups 'type' and 'type | hurricane periods' hold the pooled RMSE and the number of forecasts. The RMSE outside the
hurricane periods follows from the two by subtraction of the squared errors.
Hurricane periods: Beryl, 7 to 11 July 2024, stations in the Texas and Galveston domains; Francine, 10 to 14 September
2024, stations in the Louisiana domain. Stations with real-time data only (USGS and NOAA, no CRMS).
Usage: python event_summary.py [--run v14_stale25]
Output: deliverables/22_rmse_by_type_and_period.csv and .md
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from versions_figs import load_runs

REPO = Path(__file__).resolve().parents[2]
TYPES = [("tide gauge", "Tide gauges", "潮位站"), ("estuary / tidal channel", "Estuaries / tidal channels", "河口 / 潮汐河道"), ("lake", "Lakes", "湖"),
         ("river / canal", "Rivers / canals", "河流 / 渠道"), ("urban creek (Houston)", "Urban creeks (Houston)", "城市溪流（Houston）"), ("marsh", "Marsh", "湿地"),
         ("all", "All stations", "全部站")]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--run", default="v14_stale25"); a = ap.parse_args()
    t = pd.read_csv(REPO / "runs" / a.run / "stale_origin.csv")
    t = t[t.hours_without_data == 0].set_index(["group", "lead_h"])
    per = load_runs([a.run])[a.run]            # stations with at least 720 test forecasts, as in the other tables
    nst = per.type.value_counts().to_dict(); nst["all"] = len(per)
    rows = []
    for key, en, zh in TYPES:
        hk = "hurricane periods" if key == "all" else f"{key} | hurricane periods"
        r = {"type": en, "type_zh": zh, "stations": int(nst.get(key, 0))}
        for L in (1, 3, 6):
            ra, na = t.loc[(key, L), "rmse_cm"], t.loc[(key, L), "n"]
            rh, nh = t.loc[(hk, L), "rmse_cm"], t.loc[(hk, L), "n"]
            r[f"hurricane_{L}h_cm"] = round(float(rh), 1)
            r[f"other_{L}h_cm"] = round(float(np.sqrt((na * ra ** 2 - nh * rh ** 2) / (na - nh))), 1)
            r[f"all_{L}h_cm"] = round(float(ra), 1)
        r["n_hurricane"] = int(t.loc[(hk, 6), "n"]); r["n_other"] = int(t.loc[(key, 6), "n"] - t.loc[(hk, 6), "n"])
        rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(REPO / "deliverables" / "22_rmse_by_type_and_period.csv", index=False)
    print(d.drop(columns=["type_zh"]).to_string(index=False))
    md = ["# 22 各类站点在飓风期间和其余时间的 RMSE", "",
          f"模型：scaling + gap filling + HRRR rainfall，按缺测训练（实际运行的模型，`runs/{a.run}`）。测试期 2024-01 到 2025-12，只含有实时数据的站（USGS 和 NOAA，不含 CRMS）。",
          "RMSE 是该类站点全部预报合在一起算的（不是站点中位数），单位 cm。数字来自 `runs/" + a.run + "/stale_origin.csv`（最新观测已到的那一组），脚本 `scripts/report/event_summary.py`。", "",
          "- **飓风期间**：Beryl，2024-07-07 到 07-11，Texas 和 Galveston 两个区域的站；Francine，2024-09-10 到 09-14，Louisiana 区域的站。",
          "- **其余时间**：测试期内除这两段以外的全部预报。里面仍然包含其他洪水（例如 2024 年 5 月），不等于平静期。", "",
          "| 站点类型 | 站数 | 飓风期间 1 h | 3 h | 6 h | 其余时间 1 h | 3 h | 6 h | 飓风期间预报数 | 其余时间预报数 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b = "**" if r["type"] == "All stations" else ""
        md.append(f"| {b}{r['type_zh']}{b} | {r['stations']} | {r['hurricane_1h_cm']:.1f} | {r['hurricane_3h_cm']:.1f} | {r['hurricane_6h_cm']:.1f} | "
                  f"{r['other_1h_cm']:.1f} | {r['other_3h_cm']:.1f} | {r['other_6h_cm']:.1f} | {r['n_hurricane']:,} | {r['n_other']:,} |")
    md += ["", "预报数是每 6 小时起报一次统计的。湿地类只有少数几个站、飓风期间只有约 140 个预报，数字不稳。"]
    (REPO / "deliverables" / "22_rmse_by_type_and_period.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("->", REPO / "deliverables" / "22_rmse_by_type_and_period.md")


if __name__ == "__main__":
    main()
