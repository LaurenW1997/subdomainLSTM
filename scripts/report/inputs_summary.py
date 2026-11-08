"""deliverable 05: what the wind and discharge inputs are - coverage, statistics, maps.

Runs locally (needs cartopy) on data/dataset_v3 (wind_u/v.npy, stations.csv, time.npy),
data/wind/cells.csv, data/hourly/USGS_Q/*.parquet, config/discharge_gauges.csv,
config/station_discharge_map.csv. Writes deliverables/05_*.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cf

REPO = Path(__file__).resolve().parents[2]
D = REPO / "data"; OUT = REPO / "deliverables"
DOMS = ["Louisiana100m", "Galveston100m", "Texas100m"]
EXTENT = [-99.3, -88.2, 25.6, 31.4]


def basemap(ax):
    ax.set_extent(EXTENT)
    ax.add_feature(cf.LAND, facecolor="0.93"); ax.add_feature(cf.OCEAN, facecolor="0.98")
    ax.add_feature(cf.COASTLINE, lw=.6); ax.add_feature(cf.STATES, lw=.4); ax.add_feature(cf.RIVERS, lw=.4, alpha=.6)
    doms = json.loads((REPO / "config" / "domains.json").read_text())
    for name, b in doms.items():
        if isinstance(b, dict):
            ax.plot([b["lon_min"], b["lon_max"], b["lon_max"], b["lon_min"], b["lon_min"]],
                    [b["lat_min"], b["lat_min"], b["lat_max"], b["lat_max"], b["lat_min"]], "k--", lw=.7, transform=ccrs.PlateCarree())


def main() -> None:
    st = pd.read_csv(D / "dataset_v3" / "stations.csv", dtype={"station_id": str})
    time = pd.to_datetime(np.load(D / "dataset_v3" / "time.npy"))
    md = []

    # ------------------------------------------------------------------ wind
    u = np.load(D / "dataset_v3" / "wind_u.npy", mmap_mode="r"); v = np.load(D / "dataset_v3" / "wind_v.npy", mmap_mode="r")
    wmeta = json.loads((D / "wind" / "meta.json").read_text())
    cells = pd.read_csv(D / "wind" / "cells.csv", dtype={"station_id": str})
    cells["dist_km"] = np.hypot((cells.cell_lat - cells.lat) * 111, (cells.cell_lon - cells.lon) * 111 * np.cos(np.radians(cells.lat)))
    years = time.year.to_numpy()
    yr_valid = {int(y): float(np.isfinite(u[:, years == y]).mean()) for y in range(2010, 2026)}
    spd = np.sqrt(np.asarray(u, dtype=np.float32) ** 2 + np.asarray(v, dtype=np.float32) ** 2)
    cov = np.isfinite(spd[:, years <= 2025]).mean(1)
    ws = pd.DataFrame({"source": st.source, "station_id": st.station_id, "name": st["name"], "lat": st.lat, "lon": st.lon, "domains": st.domains,
                       "wind_coverage": cov, "cell_dist_km": cells.dist_km,
                       "speed_mean_ms": np.nanmean(spd, 1), "speed_p99_ms": np.nanpercentile(spd, 99, axis=1), "speed_max_ms": np.nanmax(spd, 1)})
    ws.to_csv(OUT / "05_wind_per_station.csv", index=False)
    nocov = ws[ws.wind_coverage < 0.5]
    # domain-wide: speed stats, strongest hours
    flat = spd[:, years <= 2025]
    md += ["# 05 风场和流量输入的基本情况", "",
           "## 一、风场", "",
           "| 项目 | 内容 |", "|---|---|",
           "| 数据 | NOAA AORC v1.1（Analysis of Record for Calibration），NOAA 为水文模型校准做的再分析驱动场 |",
           "| 变量 | 10 m 高度风 u、v 分量（m/s） |",
           "| 分辨率 | 1 km，逐小时，UTC |",
           "| 时段 | 用了 2010-01-01 至 2025-12-31；AORC 本身 1979 年起，到 2025 年底 |",
           "| 获取 | AWS 公开桶 `s3://noaa-nws-aorc-v1-1-1km`，不用账号；按每个站的经纬度取最近的格点，全部 16 年 13 分钟提完 |",
           f"| 格点到站点距离 | 中位 {cells.dist_km.median():.2f} km，最大 {cells.dist_km.max():.2f} km（1 km 格点，基本就是站点所在格） |",
           f"| 覆盖 | 每年有效率 {min(yr_valid.values())*100:.1f}%–{max(yr_valid.values())*100:.1f}%；{len(nocov)} 个站落在海上无格点：" + "、".join(f"{r.source} {r.station_id} {r['name']}" for _, r in nocov.iterrows()) + " |",
           f"| 风速统计（全部站 2010–2025） | 中位 {np.nanmedian(flat):.1f} m/s，平均 {np.nanmean(flat):.1f} m/s，99% 分位 {np.nanpercentile(flat, 99):.1f} m/s，最大 {np.nanmax(flat):.1f} m/s |",
           "| 进模型的方式 | 过去 72 小时每小时的 u、v（除以 10 做尺度归一）+ 有无数据标记；可选再给未来 6 小时的 u、v（训练用 AORC 代替预报，业务上换成 RRFS/NAM 预报风） |",
           "| 2026 年 | AORC 没有 2026，所以加风的实验统一在 2024–2025 上评估 |", "",
           "按 domain 的风速（各站 2010–2025，m/s）：", "", "| domain | 站数 | 平均风速（站中位） | 99% 分位（站中位） | 最大（所有站） |", "|---|---|---|---|---|"]
    for dom in DOMS:
        g = ws[ws.domains.astype(str).str.contains(dom) & (ws.wind_coverage > 0.5)]
        md.append(f"| {dom} | {len(g)} | {g.speed_mean_ms.median():.1f} | {g.speed_p99_ms.median():.1f} | {g.speed_max_ms.max():.1f} |")
    md += ["", "![](05_wind_map.png)", "", "![](05_wind_example.png)", ""]

    # wind map
    fig = plt.figure(figsize=(14, 5.6)); ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree()); basemap(ax)
    g = ws[ws.wind_coverage > 0.5]
    sc = ax.scatter(g.lon, g.lat, c=g.speed_p99_ms, s=9, cmap="viridis", transform=ccrs.PlateCarree(), zorder=5)
    ax.scatter(nocov.lon, nocov.lat, marker="x", c="r", s=40, transform=ccrs.PlateCarree(), zorder=6, label="no AORC cell (offshore)")
    plt.colorbar(sc, ax=ax, shrink=.75, pad=.02, label="99th percentile 10 m wind speed 2010-25 (m/s)")
    ax.legend(loc="lower left", fontsize=8); ax.set_title("AORC 10 m wind at the stations: 99th-percentile speed")
    fig.tight_layout(); fig.savefig(OUT / "05_wind_map.png", dpi=150); plt.close(fig)
    # example: Grand Isle, Francine week + a 2024 cold-front week
    i = st.index[(st.source == "NOAA_COOPS") & (st.station_id == "8761724")][0]
    fig, axes = plt.subplots(1, 2, figsize=(15, 3.8))
    for ax, (w0, w1, title) in zip(axes, [("2024-09-08", "2024-09-15", "Grand Isle - Hurricane Francine 2024-09"),
                                          ("2025-01-18", "2025-01-25", "Grand Isle - cold front / winter storm 2025-01")]):
        lo, hi = time.searchsorted(np.datetime64(w0)), time.searchsorted(np.datetime64(w1))
        ax.plot(time[lo:hi], spd[i, lo:hi], "C0", lw=1.2, label="wind speed (m/s)")
        ax.plot(time[lo:hi], u[i, lo:hi], "C2", lw=.8, label="u (east+)"); ax.plot(time[lo:hi], v[i, lo:hi], "C3", lw=.8, label="v (north+)")
        ax.axhline(0, color="k", lw=.5); ax.set_title(title, fontsize=10); ax.tick_params(labelsize=7); ax.grid(alpha=.3)
    axes[0].legend(fontsize=8); axes[0].set_ylabel("m/s")
    fig.tight_layout(); fig.savefig(OUT / "05_wind_example.png", dpi=130); plt.close(fig)

    # ------------------------------------------------------------------ discharge
    gauges = pd.read_csv(REPO / "config" / "discharge_gauges.csv", dtype=str)
    m = pd.read_csv(REPO / "config" / "station_discharge_map.csv", dtype=str)
    rows = []
    for _, g in gauges.iterrows():
        p = D / "hourly" / "USGS_Q" / f"{g.gauge_id}.parquet"
        n_st = int((m.gauge_id == g.gauge_id).sum())
        if not p.exists():
            rows.append({"gauge_id": g.gauge_id, "name": g.gauge_name, "huc8": g.huc8, "drain_area_km2": float(g.drain_area_mi2) * 2.58999,
                         "lat": float(g.lat), "lon": float(g.lon), "n_stations": n_st, "status": "no data from API"}); continue
        s = pd.read_parquet(p)["value_m"]
        s = s[s > -1000]
        rows.append({"gauge_id": g.gauge_id, "name": g.gauge_name, "huc8": g.huc8, "drain_area_km2": float(g.drain_area_mi2) * 2.58999,
                     "lat": float(g.lat), "lon": float(g.lon), "n_stations": n_st, "status": "ok",
                     "first": s.index.min().date(), "last": s.index.max().date(), "valid_frac_2010_26": len(s) / len(time),
                     "q_median_m3s": s.median(), "q_p90_m3s": s.quantile(.9), "q_max_m3s": s.max(), "q_max_date": s.idxmax().date()})
    gq = pd.DataFrame(rows).sort_values("drain_area_km2", ascending=False)
    gq.to_csv(OUT / "05_discharge_gauges.csv", index=False)
    ok = gq[gq.status == "ok"]
    no_series = m[m.gauge_id.isna() | m.gauge_id.isin(gq[gq.status != "ok"].gauge_id)]
    md += ["## 二、流量", "",
           "| 项目 | 内容 |", "|---|---|",
           "| 数据 | USGS NWIS 瞬时流量（要素 00060），15 分钟原始值平均到小时，单位 m³/s；历史和实时是同一个接口 |",
           "| 时段 | 2010-01-01 至今（实时） |",
           f"| 选站规则 | 三个 domain 范围内 277 个有实时流量的 USGS 站里，每个 HUC8 流域取汇水面积最大、2012 年前就有记录的一个 → **{len(gauges)} 个上游控制站**，{len(ok)} 个有数据（{len(gauges) - len(ok)} 个接口不返回：" + "、".join(gq[gq.status != 'ok'].gauge_id) + "） |",
           f"| 汇水面积 | 最大密西西比 Belle Chasse {ok.drain_area_km2.max()/1e6:.2f} 百万 km²，最小 {ok.drain_area_km2.min():.0f} km²；中位 {ok.drain_area_km2.median():.0f} km² |",
           f"| 数据完整度 | {len(ok)} 个站 2010–2026 小时有效率中位 {ok.valid_frac_2010_26.median()*100:.0f}%，最低 {ok.valid_frac_2010_26.min()*100:.0f}% |",
           f"| 配给水位站 | 每个水位站配一个上游站：USGS 站用自己的 HUC8（{(m.assignment=='same_huc8').sum()} 站）；CRMS/NOAA 站按经纬度查 HUC8；Barataria、Terrebonne、下 Atchafalaya、Breton Sound、Maurepas、Mermentau 这些没有上游站的海岸流域手动指给喂它们的河（{(m.assignment=='manual_coastal_basin').sum()} 站）。最终 **{len(m) - len(no_series)}/{len(m)} 站有流量输入**，{len(no_series)} 站没有（流域内没有控制站，或控制站接口无数据） |",
           "| 进模型的方式 | 过去 72 小时每小时的流量，取 log(1+Q) 后按各控制站 2010–2022 的均值/标准差标准化 + 有无数据标记；没有流量的站输入为 0、标记为 0 |", "",
           "![](05_discharge_map.png)", "",
           "控制站一览（按汇水面积，流量 m³/s，2010–2026）：", "",
           "| 站 | 河流 / 站名 | 汇水面积 km² | 配给的水位站数 | 有效率 | 中位流量 | 90% 分位 | 最大 | 最大出现 |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in gq.iterrows():
        if r.status != "ok":
            md.append(f"| {r.gauge_id} | {r['name']} | {r.drain_area_km2:,.0f} | {r.n_stations} | — | 接口无数据 | | | |"); continue
        md.append(f"| {r.gauge_id} | {r['name']} | {r.drain_area_km2:,.0f} | {r.n_stations} | {r.valid_frac_2010_26*100:.0f}% | {r.q_median_m3s:,.0f} | {r.q_p90_m3s:,.0f} | {r.q_max_m3s:,.0f} | {r.q_max_date} |")
    md += ["", "![](05_discharge_example.png)", "", "## 文件", "",
           "- `05_wind_per_station.csv`：每站风场覆盖率、格点距离、平均/99%/最大风速",
           "- `05_discharge_gauges.csv`：上表的原始数字", "- `config/discharge_gauges.csv`、`config/station_discharge_map.csv`：控制站清单和站点配对（仓库里）"]
    (OUT / "05_inputs_summary.md").write_text("\n".join(md), encoding="utf-8")

    # discharge map: gauges sized by drainage area, stations coloured by assigned gauge
    fig = plt.figure(figsize=(14, 5.6)); ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree()); basemap(ax)
    mm = m.merge(st[["source", "station_id", "lat", "lon"]], on=["source", "station_id"])
    gids = ok.gauge_id.tolist(); cmap = plt.get_cmap("tab20", len(gids))
    col = {g: cmap(i % 20) for i, g in enumerate(gids)}
    has = mm[mm.gauge_id.isin(gids)]
    ax.scatter(has.lon, has.lat, c=[col[g] for g in has.gauge_id], s=7, transform=ccrs.PlateCarree(), zorder=4)
    none = mm[~mm.gauge_id.isin(gids)]
    ax.scatter(none.lon, none.lat, c="0.5", s=7, marker="x", transform=ccrs.PlateCarree(), zorder=4, label=f"no discharge input ({len(none)})")
    ax.scatter(ok.lon, ok.lat, s=20 + 120 * np.log10(ok.drain_area_km2) / 6, c=[col[g] for g in ok.gauge_id], edgecolor="k", lw=.8, marker="^",
               transform=ccrs.PlateCarree(), zorder=6, label="discharge gauge (size ~ log drainage area)")
    ax.legend(loc="lower left", fontsize=8); ax.set_title(f"{len(ok)} upstream discharge gauges (triangles) and the stations assigned to each (same colour)")
    fig.tight_layout(); fig.savefig(OUT / "05_discharge_map.png", dpi=150); plt.close(fig)
    # example series: Mississippi Belle Chasse, Atchafalaya Simmesport, Trinity Romayor, Buffalo Bayou Piney Point 2024-2025
    fig, axes = plt.subplots(2, 2, figsize=(15, 6.5))
    for ax, gid in zip(axes.ravel(), ["07374525", "07381490", "08066500", "08073700"]):
        p = D / "hourly" / "USGS_Q" / f"{gid}.parquet"
        s = pd.read_parquet(p)["value_m"]; s = s[s > -1000]["2024":"2025"]
        ax.plot(s.index, s.values, lw=.7); ax.set_title(f"{gid} {gauges.set_index('gauge_id').loc[gid, 'gauge_name']}", fontsize=9)
        ax.set_ylabel("m³/s"); ax.tick_params(labelsize=7); ax.grid(alpha=.3)
    fig.suptitle("Hourly discharge 2024-2025 at four control gauges", fontsize=11); fig.tight_layout()
    fig.savefig(OUT / "05_discharge_example.png", dpi=130); plt.close(fig)
    print("\n".join(md[:40]))


if __name__ == "__main__":
    main()
