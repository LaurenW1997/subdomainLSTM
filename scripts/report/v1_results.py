"""deliverable 02: test-set (2024-2026) RMSE of a trained run, by domain + representative stations.

Runs where torch + the dataset live (sv7). Writes into --out:
  02_per_station_test.csv          per station, per horizon RMSE and n
  02_domain_summary.csv            median / pooled RMSE by domain, 02_domain_source_summary.csv by domain x source
  02_domains_boxplot.png           per-station 6 h RMSE distributions by domain
  02_rmse_by_horizon.png           median RMSE vs lead time per domain
  02_station_<id>.png              representative stations: event week + calm week + RMSE by horizon
  02_station_forecasts.csv         the plotted series
  02_tables.md                     markdown tables to paste into the summary
Usage: python v1_results.py --dataset DIR --run DIR --out DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
from data import HORIZON, StationMatrix, to_torch  # noqa: E402
from model import GlobalLSTM  # noqa: E402

REPRESENTATIVE = [  # (source, station_id, short label)
    ("NOAA_COOPS", "8761724", "Grand Isle (open coast, LA)"),
    ("NOAA_COOPS", "8761927", "New Canal, Lake Pontchartrain (LA)"),
    ("USGS", "07381600", "Lower Atchafalaya at Morgan City (river+tide, LA)"),
    ("CRMS", "CRMS0311-H01", "CRMS0311 Barataria marsh (LA)"),
    ("NOAA_COOPS", "8771450", "Galveston Pier 21 (TX)"),
    ("NOAA_COOPS", "8770613", "Morgans Point, upper Galveston Bay (TX)"),
    ("USGS", "08074000", "Buffalo Bayou at Houston (urban bayou, TX)"),
    ("NOAA_COOPS", "8774770", "Rockport (TX)"),
    ("NOAA_COOPS", "8779770", "Port Isabel (TX)"),
    ("USGS", "08211500", "Nueces River at Calallen (tidal river, TX)"),
    ("USGS", "08188500", "San Antonio River at Goliad (inland river, TX)"),
]
WINDOWS = {  # label -> (start, end) UTC
    "Hurricane Francine 2024-09": ("2024-09-08", "2024-09-15"),
    "Hurricane Beryl 2024-07": ("2024-07-05", "2024-07-12"),
    "calm week 2025-03": ("2025-03-10", "2025-03-17"),
}
DOMS = ["Louisiana100m", "Galveston100m", "Texas100m"]


def per_station_eval(model, sm, device, stride=6, batch=8192, t_hi=None):
    S, T0 = sm.eval_origins("test", stride, t_hi=t_hi)
    std = sm.stations["std_m"].to_numpy(np.float32)
    se = np.zeros((sm.S, HORIZON)); n = np.zeros((sm.S, HORIZON))
    with torch.no_grad():
        for i in range(0, len(S), batch):
            feats, fut, s, y, ym = sm.window(S[i:i + batch], T0[i:i + batch])
            f, fu, st, _, _ = to_torch((feats, fut, s, y, ym), device)
            pred = model(f, st, fu).cpu().numpy()
            err = (pred - y) * std[s][:, None]
            for h in range(HORIZON):
                np.add.at(se[:, h], s, np.where(ym[:, h], err[:, h] ** 2, 0))
                np.add.at(n[:, h], s, ym[:, h])
    return se, n


def forecast_series(model, sm, device, s: int, t_lo: int, t_hi: int):
    """Hourly forecasts for one station for every origin in [t_lo, t_hi)."""
    t0 = np.arange(max(t_lo, sm.lookback), min(t_hi, sm.T - HORIZON - 1))
    feats, fut, ss, y, ym = sm.window(np.full(len(t0), s), t0)
    ok = feats[:, :, 1].mean(1) >= 0.7
    if sm.use_wind:
        ok &= feats[:, :, 8].mean(1) >= 0.7
    pred = np.full((len(t0), HORIZON), np.nan, np.float32)
    with torch.no_grad():
        if ok.any():
            f, fu, st, _, _ = to_torch((feats[ok], fut[ok], ss[ok], y[ok], ym[ok]), device)
            pred[ok] = model(f, st, fu).cpu().numpy()
    mean, std = sm.stations.loc[s, "mean_m"], sm.stations.loc[s, "std_m"]
    return t0, pred * std + mean


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--run", required=True); ap.add_argument("--out", required=True); ap.add_argument("--test-end", help="last test origin, e.g. 2025-12-31T17")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    ck = torch.load(Path(a.run) / "best.pt", map_location=device)
    sm = StationMatrix(Path(a.dataset), lookback=ck["args"].get("lookback", 72), use_wind=ck["args"].get("wind", False),
                       use_future_wind=ck["args"].get("future_wind", False), use_q=ck["args"].get("discharge", False))
    model = GlobalLSTM(ck["n_stations"], n_feat=ck.get("n_feat", 6), hidden=ck["args"]["hidden"], layers=ck["args"]["layers"],
                       n_future=ck.get("n_future", 0)).to(device)
    model.load_state_dict(ck["state_dict"]); model.eval()
    st = sm.stations.reset_index()

    # ---- per station, per horizon
    t_hi = int(np.searchsorted(sm.time.values, np.datetime64(a.test_end))) if a.test_end else None
    se, n = per_station_eval(model, sm, device, t_hi=t_hi)
    rows = st[["row", "source", "station_id", "name", "lat", "lon", "domains", "std_m"]].copy()
    for h in range(HORIZON):
        rows[f"rmse_{h+1}h_cm"] = 100 * np.sqrt(se[:, h] / np.maximum(n[:, h], 1))
    rows["n_6h"] = n[:, -1]
    rows = rows[rows.n_6h >= 24 * 30]          # at least a month of test targets
    rows.to_csv(out / "02_per_station_test.csv", index=False)
    for h in range(HORIZON):
        rows[f"sse_{h+1}"] = se[rows.row, h]; rows[f"n_{h+1}"] = n[rows.row, h]

    # ---- domain tables (a station in two domains counts in both)
    rows["domain_list"] = rows.domains.astype(str).str.split(";")
    ex = rows.explode("domain_list").rename(columns={"domain_list": "domain"})

    def summarise(g):
        d = {"n_stations": len(g)}
        for h in range(1, HORIZON + 1):
            d[f"median_{h}h_cm"] = g[f"rmse_{h}h_cm"].median()
            d[f"pooled_{h}h_cm"] = 100 * np.sqrt(g[f"sse_{h}"].sum() / g[f"n_{h}"].sum())
        d["q25_6h_cm"] = g.rmse_6h_cm.quantile(.25); d["q75_6h_cm"] = g.rmse_6h_cm.quantile(.75)
        d["frac_6h_below_5cm"] = (g.rmse_6h_cm < 5).mean(); d["frac_6h_below_10cm"] = (g.rmse_6h_cm < 10).mean()
        return pd.Series(d)

    dom = ex.groupby("domain").apply(summarise).reindex(DOMS)
    dom_src = ex.groupby(["domain", "source"]).apply(summarise)
    allrow = summarise(rows).to_frame("ALL").T
    dom_all = pd.concat([dom, allrow])
    dom_all.to_csv(out / "02_domain_summary.csv")
    dom_src.to_csv(out / "02_domain_source_summary.csv")

    md = ["## 三个 domain 整体（测试集 2024-01 至 2026-11，所有站，单位 cm）", "",
          "| domain | 站数 | 1 h | 2 h | 3 h | 4 h | 5 h | **6 h** | 6 h 四分位 (25%–75%) | 6 h < 5 cm 的站 | 6 h < 10 cm 的站 | 6 h pooled |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in dom_all.iterrows():
        md.append(f"| {k} | {int(r.n_stations)} | " + " | ".join(f"{r[f'median_{h}h_cm']:.1f}" for h in range(1, 6)) +
                  f" | **{r.median_6h_cm:.1f}** | {r.q25_6h_cm:.1f}–{r.q75_6h_cm:.1f} | {r.frac_6h_below_5cm*100:.0f}% | {r.frac_6h_below_10cm*100:.0f}% | {r.pooled_6h_cm:.1f} |")
    md += ["", "每格是该 domain 内各站 RMSE 的中位数；pooled 是把所有站的误差堆在一起算的 RMSE（受误差大的站影响大）。", "",
           "## domain × 数据源（6 h RMSE 中位数，cm）", "", "| domain | 来源 | 站数 | 1 h | 3 h | **6 h** | 6 h 四分位 |", "|---|---|---|---|---|---|---|"]
    for (d, s), r in dom_src.iterrows():
        md.append(f"| {d} | {s} | {int(r.n_stations)} | {r.median_1h_cm:.1f} | {r.median_3h_cm:.1f} | **{r.median_6h_cm:.1f}** | {r.q25_6h_cm:.1f}–{r.q75_6h_cm:.1f} |")

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # ---- boxplot by domain
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rng = np.random.default_rng(0)
    data = [ex[ex.domain == d].rmse_6h_cm for d in DOMS]
    ax.boxplot(data, showfliers=False, widths=.5)
    for i, dd in enumerate(data, 1):
        ax.scatter(rng.normal(i, 0.06, len(dd)), dd, s=5, alpha=.35, color="C3")
    ax.set_xticks(range(1, 4)); ax.set_xticklabels([f"{d}\n{len(dd)} stations" for d, dd in zip(DOMS, data)])
    ax.set_ylim(0, 40); ax.set_ylabel("6 h RMSE per station, test 2024-26 (cm)"); ax.grid(axis="y", alpha=.3)
    ax.set_title("Per-station 6 h RMSE by domain (box = 25-75%, line = median)")
    fig.tight_layout(); fig.savefig(out / "02_domains_boxplot.png", dpi=150); plt.close(fig)
    # ---- RMSE vs lead time
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    hs = np.arange(1, HORIZON + 1)
    for d, c in zip(DOMS, ["C0", "C1", "C2"]):
        ax.plot(hs, [dom.loc[d, f"median_{h}h_cm"] for h in hs], "o-", color=c, label=f"{d} (median)")
        ax.plot(hs, [dom.loc[d, f"pooled_{h}h_cm"] for h in hs], "s--", color=c, alpha=.5, label=f"{d} (pooled)")
    ax.set_xlabel("lead time (h)"); ax.set_ylabel("RMSE (cm)"); ax.set_xticks(hs); ax.grid(alpha=.3); ax.legend(fontsize=7)
    ax.set_title("Test RMSE vs lead time"); fig.tight_layout(); fig.savefig(out / "02_rmse_by_horizon.png", dpi=150); plt.close(fig)

    # ---- representative stations
    md += ["", "## 代表性站点（测试集全段 RMSE，cm）", "", "| 站 | 说明 | 1 h | 2 h | 3 h | 4 h | 5 h | **6 h** |", "|---|---|---|---|---|---|---|---|"]
    series = []
    for src, sid, label in REPRESENTATIVE:
        m = st[(st.source == src) & (st.station_id.astype(str) == sid)]
        if m.empty:
            print("missing", src, sid); continue
        s = int(m.row.iloc[0]); r = rows[rows.row == s]
        if r.empty:
            print("no test data", src, sid); continue
        r = r.iloc[0]
        md.append(f"| {src} {sid} | {label} | " + " | ".join(f"{r[f'rmse_{h}h_cm']:.1f}" for h in range(1, 6)) + f" | **{r.rmse_6h_cm:.1f}** |")
        fig, axes = plt.subplots(1, 4, figsize=(20, 3.8), gridspec_kw={"width_ratios": [3, 3, 3, 1.3]})
        for ax, (wl, (w0, w1)) in zip(axes, WINDOWS.items()):
            lo = int(np.searchsorted(sm.time.values, np.datetime64(w0))); hi = int(np.searchsorted(sm.time.values, np.datetime64(w1)))
            t0, pred = forecast_series(model, sm, device, s, lo - HORIZON, hi)
            tv = t0 + HORIZON                      # 6 h forecast valid at t0+6
            keep = (tv >= lo) & (tv < hi)
            ax.plot(sm.time[lo:hi], sm.values[s, lo:hi], "k", lw=1.3, label="observed")
            ax.plot(sm.time[tv[keep]], pred[keep, -1], "C3", lw=1, label="LSTM, issued 6 h earlier")
            ax.set_title(wl, fontsize=9); ax.tick_params(labelsize=7); ax.grid(alpha=.3)
            for k in np.where(keep)[0]:
                series.append({"source": src, "station_id": sid, "window": wl, "valid_time": sm.time[tv[k]],
                               "obs_m": float(sm.values[s, tv[k]]), "lstm_6h_m": float(pred[k, -1])})
        axes[0].set_ylabel("water level (m)"); axes[0].legend(fontsize=7, loc="upper left")
        ax = axes[3]
        ax.bar(hs, [r[f"rmse_{h}h_cm"] for h in hs], 0.6, color="C3")
        ax.set_xlabel("lead time (h)"); ax.set_ylabel("RMSE, test 2024-26 (cm)"); ax.set_xticks(hs); ax.grid(axis="y", alpha=.3)
        fig.suptitle(f"{src} {sid} - {label}", fontsize=11); fig.tight_layout()
        fig.savefig(out / f"02_station_{sid}.png", dpi=130); plt.close(fig)
    pd.DataFrame(series).to_csv(out / "02_station_forecasts.csv", index=False)
    (out / "02_tables.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
