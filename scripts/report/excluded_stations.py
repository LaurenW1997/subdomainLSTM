"""deliverable 01: every censused station that is NOT in the training set, with the reason.

Stages: census -> download (data_inventory) -> dataset (excluded.csv). Output
deliverables/01_excluded_stations.csv and a markdown summary.
Usage: python excluded_stations.py --dataset data/dataset_v1
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
REASON_TXT = {
    "inactive": "普查时站已停测（目录里 record_end 早于 2026 年，或近 30 天没有数据）",
    "catalog_record_too_short": "目录记录长度不足 3 年（站仍在测）",
    "no_data_downloaded": "目录上有、但下载不到 2010 年以来的小时水位（USACE 只有日均序列、CRMS 周报里没有该站、USGS 没有 00065 要素等）",
    "too_short": "下载到的有效小时数据不足 3 年",
    "too_short_in_train": "训练期 2010–2022 内有效数据不足 1 年（多为 2022 年后新建站）",
    "flat": "训练期标准差小于 2 cm，水位基本不动",
    "source_excluded": "USACE SWG 整个来源不用：47 站中 37 站含填充值，10 个是水库库水位，23 个与 USGS 站是同一仪器",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(REPO / "data" / "dataset_v1"))
    ap.add_argument("--out", default=str(REPO / "deliverables"))
    a = ap.parse_args()
    ds = Path(a.dataset)
    cen = pd.read_csv(REPO / "config" / "stations_census.csv", dtype=str)
    inv = pd.read_csv(REPO / "config" / "data_inventory_20261107.csv", dtype=str)
    ex = pd.read_csv(ds / "excluded.csv", dtype=str)
    kept = pd.read_csv(ds / "stations.csv", dtype=str)
    jumps = pd.read_csv(REPO / "data" / "qc" / "datum_jumps.csv", dtype=str) if (REPO / "data/qc/datum_jumps.csv").exists() else None

    def key(df):
        return df.source.str.replace(r"USACE_.*", "USACE", regex=True) + "|" + df.station_id

    cen["key"], inv["key"], ex["key"], kept["key"] = key(cen), key(inv), key(ex), key(kept)
    cen = cen.drop_duplicates("key")  # same USACE gauge listed by two offices
    rows = []
    # stage A: census stations that never reached the download inventory
    for _, r in cen[~cen.key.isin(inv.key)].iterrows():
        if r.active != "True":
            reason, detail = "inactive", (f"record_end={r.record_end}" if isinstance(r.record_end, str) else "catalog marks station inactive")
        elif r.years_known == "True" and float(r.years) < 3:
            reason, detail = "catalog_record_too_short", f"catalog years={float(r.years):.1f}"
        else:
            reason, detail = "no_data_downloaded", f"interval_min={r.interval_min}; parameter={r.parameter}"
        rows.append(dict(source=r.source, station_id=r.station_id, name=r["name"], lat=r.lat, lon=r.lon,
                         domains=r.domains, stage="census->download", reason=reason, detail=detail))
    # stage B: downloaded but excluded when building the dataset
    for _, r in ex.iterrows():
        detail = r.detail if isinstance(r.detail, str) else ""
        if r.reason == "source_excluded" and jumps is not None:
            j = jumps[(jumps.source == r.source) & (jumps.station_id == r.station_id)]
            if len(j):
                detail = f"{int(j.iloc[0].n_sentinel)} fill values; min={float(j.iloc[0].min_m):.1f} m max={float(j.iloc[0].max_m):.1f} m"
        m = inv[inv.key == r.key].iloc[0]
        rows.append(dict(source=r.source, station_id=r.station_id, name=m["name"], lat=m.lat, lon=m.lon,
                         domains=m.domains, stage="download->dataset", reason=r.reason, detail=detail))
    out = pd.DataFrame(rows).sort_values(["stage", "source", "reason", "station_id"])
    Path(a.out).mkdir(exist_ok=True)
    out.to_csv(Path(a.out) / "01_excluded_stations.csv", index=False, encoding="utf-8-sig")

    n_cen = len(set(cen.key) | set(inv.key))
    tab = out.pivot_table(index="reason", columns="source", values="station_id", aggfunc="count", fill_value=0)
    tab["total"] = tab.sum(1)
    tab = tab.loc[[k for k in REASON_TXT if k in tab.index]]
    kept_tab = kept.groupby("source").size()
    md = ["# 01 被筛掉的站点", "",
          f"普查到 **{n_cen}** 个水位站（普查表 2057 条记录，去掉同一 USACE 测站被两个办公室重复列出的条目，加上 7 个只在 CRMS 周报里出现、CIMS 站表里没有的站），进入训练集 **{len(kept)}** 个，"
          f"筛掉 **{len(out)}** 个。完整清单见 `01_excluded_stations.csv`（每站一行：来源、编号、名称、经纬度、所在 domain、在哪一步被筛掉、原因、补充说明）。", "",
          "## 进入训练集的站", "", "| 来源 | 站数 |", "|---|---|"]
    md += [f"| {s} | {n} |" for s, n in kept_tab.items()]
    md += ["", "## 筛掉的站：原因 × 来源", "", "| 原因 | " + " | ".join(tab.columns) + " |", "|---|" + "---|" * len(tab.columns)]
    md += [f"| {k} | " + " | ".join(str(v) for v in tab.loc[k]) + " |" for k in tab.index]
    md += ["", "## 原因说明", ""]
    md += [f"- **{k}**：{v}" for k, v in REASON_TXT.items()]
    md += ["", "## 补充", "",
           "- `inactive` 里的 TCOON 105 站：TCOON 项目 2014 年起停止资助，其中还在运行的仪器已并入 NOAA CO-OPS，所以这 105 个编号本身不算丢站。",
           "- USACE MVN/MVK/SWF 的站绝大多数只有日均或已停测，所以几乎全部在 `inactive` / `no_data_downloaded`。",
           "- CRMS 的 `too_short` / `too_short_in_train`：CRMS 站表有 937 站，周报里能取到小时数据的 690 站，其中不少是近几年新建或已改为间歇观测。",
           "- 筛掉的站只是**不参与训练**，下载的数据都还在 sv7 上，后面随时可以放回来。"]
    (Path(a.out) / "01_excluded_stations.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
