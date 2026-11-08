"""deliverable 06: compare the four phase-2 runs (obs / +past wind / +past+future wind / +wind+discharge).

Reads runs/<run>/per_station_test.csv (same stations, same test window: origins <= 2025-12-31T17),
keeps stations with >= 720 6 h samples in all runs, writes
  06_compare_per_station.csv, 06_compare_tables.md, 06_compare_bars.png, 06_change_map.png (cartopy)
Runs locally (no torch needed).
"""
from __future__ import annotations

import argparse
import sys
import types
from pathlib import Path

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

RUNS = [("obs", "v3_obs", "只用水位"), ("wind_past", "v3_wind_past", "+过去风"), ("wind", "v3_wind", "+过去风+未来风"), ("wind_q", "v3_wind_q", "+风+流量")]
LABELS_EN = ["water level only", "+ past wind", "+ past & future wind", "+ wind + discharge"]
DOMS = ["Louisiana100m", "Galveston100m", "Texas100m"]
TYPES = ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "deliverables"))
    ap.add_argument("--min-n", type=int, default=720)
    a = ap.parse_args()
    out = Path(a.out)
    d = {k: pd.read_csv(REPO / "runs" / r / "per_station_test.csv", dtype={"station_id": str}) for k, r, _ in RUNS}
    b = d["obs"][["source", "station_id", "domains", "lat", "lon"]].copy()
    ok = np.ones(len(b), bool)
    for k, df in d.items():
        for h in (1, 3, 6):
            b[f"r{h}_{k}"] = df[f"rmse_{h}h_cm"]
        b[f"n_{k}"] = df.n_6h
        ok &= df.n_6h.to_numpy() >= a.min_n
    b = b[ok].copy()
    cen = pd.read_csv(REPO / "config" / "stations_census.csv", dtype=str).drop_duplicates(["source", "station_id"])
    cen["county"] = cen.extra.str.extract(r"county=(\d+)")
    b = b.merge(cen[["source", "station_id", "name", "site_type", "county"]], on=["source", "station_id"], how="left")
    b["type"] = b.apply(station_type, axis=1)
    m = pd.read_csv(REPO / "config" / "station_discharge_map.csv", dtype=str)
    b = b.merge(m[["source", "station_id", "assignment", "gauge_name"]], on=["source", "station_id"], how="left")
    b["change_wind_cm"] = b.r6_wind - b.r6_obs
    b["change_wind_q_cm"] = b.r6_wind_q - b.r6_obs
    b["change_q_cm"] = b.r6_wind_q - b.r6_wind
    b.to_csv(out / "06_compare_per_station.csv", index=False)
    ks = [k for k, _, _ in RUNS]

    def line(label, g):
        med = " | ".join(f"{g[f'r6_{k}'].median():.2f}" for k in ks)
        return (f"| {label} | {len(g)} | {med} | {(g.r6_obs < 5).mean()*100:.0f}% → {(g.r6_wind_q < 5).mean()*100:.0f}% | "
                f"{(g.r6_obs < 10).mean()*100:.0f}% → {(g.r6_wind_q < 10).mean()*100:.0f}% |")

    hdr = ["| 分组 | 站数 | " + " | ".join(lbl for _, _, lbl in RUNS) + " | 6 h RMSE < 5 cm 的站 (只用水位 → +风+流量) | < 10 cm 的站 |",
           "|---|---|" + "---|" * len(RUNS) + "---|---|"]
    md = ["## 四组模型对比（测试集 2024-01 → 2025-12，提前 6 小时，各站 RMSE 的中位数，cm）", "",
          f"只统计四组里都有 ≥ {a.min_n} 个 6 h 样本的 {len(b)} 个站；四组用同一测试窗口、同一网络、同样训练 40 轮，只有输入不同。", ""] + hdr
    md.append(line("**全部**", b))
    md += ["", "### 按 domain", ""] + hdr + [line(dm, b[b.domains.astype(str).str.contains(dm)]) for dm in DOMS]
    md += ["", "### 按站点类型", ""] + hdr + [line(t, b[b.type == t]) for t in TYPES if (b.type == t).sum() >= 5]
    md += ["", "### 按数据源", ""] + hdr + [line(s, g) for s, g in b.groupby("source")]
    md += ["", "### 按流量配站方式（same_huc8 = 同一 HUC8 的上游控制站；manual_coastal_basin = 手工配的大河；none = 没配）", ""] + hdr
    md += [line(s, g) for s, g in b.groupby("assignment")]
    md += ["", "### 1 / 3 / 6 h 中位数（全部站）", "", "| 模型 | 1 h | 3 h | 6 h |", "|---|---|---|---|"]
    md += [f"| {lbl} | {b[f'r1_{k}'].median():.2f} | {b[f'r3_{k}'].median():.2f} | {b[f'r6_{k}'].median():.2f} |" for k, _, lbl in RUNS]
    md += ["", "### 逐站变化（6 h RMSE，cm）", "", "| 对比 | 中位变化 | 变好 > 0.5 cm 的站 | 变差 > 0.5 cm 的站 | 变好的站占比 |", "|---|---|---|---|---|"]
    for c, lbl in (("change_wind_cm", "只用水位 → +风"), ("change_wind_q_cm", "只用水位 → +风+流量"), ("change_q_cm", "+风 → +风+流量（流量单独的贡献）")):
        md.append(f"| {lbl} | {b[c].median():+.2f} | {(b[c] < -0.5).sum()} | {(b[c] > 0.5).sum()} | {(b[c] < 0).mean()*100:.0f}% |")
    cols = ["source", "station_id", "name", "type", "r6_obs", "r6_wind", "r6_wind_q"]
    th = ["| 站 | 名称 | 类型 | 只用水位 | +风 | +风+流量 |", "|---|---|---|---|---|---|"]

    def rows(df):
        return [f"| {r.source} {r.station_id} | {r['name']} | {r.type} | {r.r6_obs:.1f} | {r.r6_wind:.1f} | {r.r6_wind_q:.1f} |" for _, r in df.iterrows()]

    md += ["", "### 加风后改善最大的站", ""] + th + rows(b.sort_values("change_wind_q_cm")[cols].head(12))
    md += ["", "### 加风后变差最大的站", ""] + th + rows(b.sort_values("change_wind_q_cm")[cols].tail(8).iloc[::-1])
    md += ["", "### 流量贡献最大的站（+风 → +风+流量）", ""] + th + rows(b.sort_values("change_q_cm")[cols].head(10))
    (out / "06_compare_tables.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = [("all", b)] + [(dm.replace("100m", ""), b[b.domains.astype(str).str.contains(dm)]) for dm in DOMS] + \
             [(t, b[b.type == t]) for t in TYPES if (b.type == t).sum() >= 5]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    x = np.arange(len(groups))
    w = 0.2
    for i, (k, _, _) in enumerate(RUNS):
        vals = [g[f"r6_{k}"].median() for _, g in groups]
        bars = ax.bar(x + (i - 1.5) * w, vals, w, label=LABELS_EN[i])
        if i in (0, 3):
            for bb, v in zip(bars, vals):
                ax.text(bb.get_x() + bb.get_width() / 2, v + 0.1, f"{v:.1f}", ha="center", fontsize=6.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\n({len(g)})" for n, g in groups], fontsize=8)
    ax.set_ylabel("median 6 h RMSE (cm)")
    ax.grid(axis="y", alpha=.3)
    ax.legend(fontsize=8)
    ax.set_title("Test 2024-25, 6 h ahead: same network, different inputs")
    fig.tight_layout()
    fig.savefig(out / "06_compare_bars.png", dpi=150)
    plt.close(fig)

    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cf
    except ImportError:
        print("no cartopy; skip map")
        return
    fig = plt.figure(figsize=(13, 5.2))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([-99.2, -88.0, 25.6, 31.2])
    ax.add_feature(cf.LAND, facecolor="#f2f2f2")
    ax.add_feature(cf.COASTLINE, lw=.5)
    ax.add_feature(cf.STATES, lw=.4)
    ch = b.change_wind_q_cm.clip(-3, 3)
    sc = ax.scatter(b.lon, b.lat, c=ch, cmap="RdBu_r", vmin=-3, vmax=3, s=14, edgecolor="k", lw=.15, transform=ccrs.PlateCarree(), zorder=5)
    cb = fig.colorbar(sc, ax=ax, shrink=.75, pad=.02)
    cb.set_label("change in 6 h RMSE, cm  (blue = better with wind + discharge)")
    ax.set_title(f"{len(b)} stations: 6 h RMSE change, water-level-only → wind + discharge (median {b.change_wind_q_cm.median():+.2f} cm; "
                 f"{(b.change_wind_q_cm < 0).mean()*100:.0f}% of stations improve)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "06_change_map.png", dpi=150)


if __name__ == "__main__":
    main()
