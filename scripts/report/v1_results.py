"""deliverable 02: test-set (2024-2026) results of a trained run, by domain + representative stations.

Runs where torch + the dataset live (sv7). Writes into --out:
  02_per_station_test.csv          per station, per horizon RMSE (model, persistence), n
  02_domain_summary.csv            pooled / median RMSE by domain and by domain x source
  02_domains_boxplot.png           per-station 6 h RMSE distributions by domain
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
from data import HORIZON, LOOKBACK, StationMatrix, to_torch  # noqa: E402
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


def per_station_eval(model, sm, device, stride=6, batch=8192):
    S, T0 = sm.eval_origins("test", stride)
    std = sm.stations["std_m"].to_numpy(np.float32)
    se_m = np.zeros((sm.S, HORIZON)); se_p = np.zeros((sm.S, HORIZON)); n = np.zeros((sm.S, HORIZON))
    with torch.no_grad():
        for i in range(0, len(S), batch):
            feats, s, y, ym = sm.window(S[i:i + batch], T0[i:i + batch])
            f, st, _, _ = to_torch((feats, s, y, ym), device)
            pred = model(f, st).cpu().numpy()
            last = feats[:, -1, 0:1]
            em = (pred - y) * std[s][:, None]; ep = (last - y) * std[s][:, None]
            for h in range(HORIZON):
                np.add.at(se_m[:, h], s, np.where(ym[:, h], em[:, h] ** 2, 0))
                np.add.at(se_p[:, h], s, np.where(ym[:, h], ep[:, h] ** 2, 0))
                np.add.at(n[:, h], s, ym[:, h])
    return se_m, se_p, n


def forecast_series(model, sm, device, s: int, t_lo: int, t_hi: int):
    """Hourly forecasts for one station for every origin in [t_lo, t_hi)."""
    t0 = np.arange(max(t_lo, LOOKBACK), min(t_hi, sm.T - HORIZON - 1))
    feats, ss, y, ym = sm.window(np.full(len(t0), s), t0)
    ok = feats[:, :, 1].mean(1) >= 0.7
    pred = np.full((len(t0), HORIZON), np.nan, np.float32)
    with torch.no_grad():
        if ok.any():
            f, st, _, _ = to_torch((feats[ok], ss[ok], y[ok], ym[ok]), device)
            pred[ok] = model(f, st).cpu().numpy()
    mean, std = sm.stations.loc[s, "mean_m"], sm.stations.loc[s, "std_m"]
    return t0, pred * std + mean, feats[:, -1, 0] * std + mean


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--run", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    sm = StationMatrix(Path(a.dataset))
    ck = torch.load(Path(a.run) / "best.pt", map_location=device)
    model = GlobalLSTM(ck["n_stations"], hidden=ck["args"]["hidden"], layers=ck["args"]["layers"]).to(device)
    model.load_state_dict(ck["state_dict"]); model.eval()
    st = sm.stations.reset_index()

    # ---- per station, per horizon
    se_m, se_p, n = per_station_eval(model, sm, device)
    rows = st[["row", "source", "station_id", "name", "lat", "lon", "domains", "std_m"]].copy()
    for h in range(HORIZON):
        rows[f"rmse_model_{h+1}h"] = np.sqrt(se_m[:, h] / np.maximum(n[:, h], 1))
        rows[f"rmse_persist_{h+1}h"] = np.sqrt(se_p[:, h] / np.maximum(n[:, h], 1))
    rows["n_6h"] = n[:, -1]
    rows["skill_6h"] = 1 - rows.rmse_model_6h / rows.rmse_persist_6h
    rows = rows[rows.n_6h >= 24 * 30]          # at least a month of test targets
    rows.to_csv(out / "02_per_station_test.csv", index=False)
    for h in range(HORIZON):
        rows[f"sse_m_{h+1}"] = se_m[rows.row, h]; rows[f"sse_p_{h+1}"] = se_p[rows.row, h]; rows[f"n_{h+1}"] = n[rows.row, h]

    # ---- domain tables (a station in two domains counts in both)
    rows["domain_list"] = rows.domains.astype(str).str.split(";")
    ex = rows.explode("domain_list").rename(columns={"domain_list": "domain"})

    def summarise(g):
        d = {"n_stations": len(g)}
        for h in (1, 3, 6):
            d[f"pooled_model_{h}h"] = np.sqrt(g[f"sse_m_{h}"].sum() / g[f"n_{h}"].sum())
            d[f"pooled_persist_{h}h"] = np.sqrt(g[f"sse_p_{h}"].sum() / g[f"n_{h}"].sum())
            d[f"median_model_{h}h"] = g[f"rmse_model_{h}h"].median()
            d[f"median_persist_{h}h"] = g[f"rmse_persist_{h}h"].median()
        d["median_skill_6h"] = g.skill_6h.median(); d["frac_better_6h"] = (g.skill_6h > 0).mean()
        return pd.Series(d)

    dom = ex.groupby("domain").apply(summarise)
    dom_src = ex.groupby(["domain", "source"]).apply(summarise)
    allrow = summarise(rows).to_frame("ALL").T
    pd.concat([dom, allrow]).to_csv(out / "02_domain_summary.csv")
    dom_src.to_csv(out / "02_domain_source_summary.csv")

    md = ["### 三个 domain 整体（测试集 2024-01 至 2026-11，所有站）", "",
          "| domain | 站数 | 6 h RMSE 中位数 LSTM | 6 h RMSE 中位数 persistence | 1 h 中位数 LSTM / pers. | 3 h 中位数 LSTM / pers. | 优于 persistence 的站 | 6 h pooled LSTM / pers. |",
          "|---|---|---|---|---|---|---|---|"]
    for k, r in pd.concat([dom, allrow]).iterrows():
        md.append(f"| {k} | {int(r.n_stations)} | **{r.median_model_6h*100:.1f} cm** | {r.median_persist_6h*100:.1f} cm | "
                  f"{r.median_model_1h*100:.1f} / {r.median_persist_1h*100:.1f} cm | {r.median_model_3h*100:.1f} / {r.median_persist_3h*100:.1f} cm | "
                  f"{r.frac_better_6h*100:.0f}% | {r.pooled_model_6h*100:.1f} / {r.pooled_persist_6h*100:.1f} cm |")
    md += ["", "### domain × 数据源（6 h，中位数）", "", "| domain | 来源 | 站数 | LSTM | persistence | 中位 skill | 优于 persistence |", "|---|---|---|---|---|---|---|"]
    for (d, s), r in dom_src.iterrows():
        md.append(f"| {d} | {s} | {int(r.n_stations)} | {r.median_model_6h*100:.1f} cm | {r.median_persist_6h*100:.1f} cm | {r.median_skill_6h:.2f} | {r.frac_better_6h*100:.0f}% |")

    # ---- boxplot by domain
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    doms = ["Louisiana100m", "Galveston100m", "Texas100m"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    rng = np.random.default_rng(0)
    for ax, d in zip(axes, doms):
        g = ex[ex.domain == d]
        data = [g.rmse_persist_6h * 100, g.rmse_model_6h * 100]
        ax.boxplot(data, showfliers=False)
        ax.set_xticks([1, 2]); ax.set_xticklabels(["persistence", "LSTM"])
        for i, dd in enumerate(data, 1):
            ax.scatter(rng.normal(i, 0.05, len(dd)), dd, s=4, alpha=.3)
        ax.set_title(f"{d}: {len(g)} stations"); ax.set_ylim(0, 60); ax.grid(axis="y", alpha=.3)
    axes[0].set_ylabel("6 h RMSE per station, test 2024-26 (cm)")
    fig.tight_layout(); fig.savefig(out / "02_domains_boxplot.png", dpi=150); plt.close(fig)

    # ---- representative stations
    md += ["", "### 代表性站点（6 h RMSE，测试集全段）", "", "| 站 | 说明 | LSTM 1 h | LSTM 3 h | LSTM 6 h | persistence 6 h | skill 6 h |", "|---|---|---|---|---|---|---|"]
    series = []
    for src, sid, label in REPRESENTATIVE:
        m = st[(st.source == src) & (st.station_id.astype(str) == sid)]
        if m.empty:
            print("missing", src, sid); continue
        s = int(m.row.iloc[0]); r = rows[rows.row == s]
        if r.empty:
            print("no test data", src, sid); continue
        r = r.iloc[0]
        md.append(f"| {src} {sid} | {label} | {r.rmse_model_1h*100:.1f} cm | {r.rmse_model_3h*100:.1f} cm | **{r.rmse_model_6h*100:.1f} cm** | {r.rmse_persist_6h*100:.1f} cm | {r.skill_6h:.2f} |")
        fig, axes = plt.subplots(1, 4, figsize=(20, 3.8), gridspec_kw={"width_ratios": [3, 3, 3, 1.3]})
        for ax, (wl, (w0, w1)) in zip(axes, WINDOWS.items()):
            lo = int(np.searchsorted(sm.time.values, np.datetime64(w0))); hi = int(np.searchsorted(sm.time.values, np.datetime64(w1)))
            t0, pred, last = forecast_series(model, sm, device, s, lo - HORIZON, hi)
            obs = sm.values[s, lo:hi]
            tt = sm.time[lo:hi]
            tv = t0 + HORIZON                      # 6 h forecast valid at t0+6
            keep = (tv >= lo) & (tv < hi)
            ax.plot(tt, obs, "k", lw=1.2, label="observed")
            ax.plot(sm.time[tv[keep]], pred[keep, -1], "C3", lw=1, label="LSTM 6 h ahead")
            ax.plot(sm.time[tv[keep]], last[keep], "C0", lw=.8, ls="--", label="persistence 6 h")
            ax.set_title(wl, fontsize=9); ax.tick_params(labelsize=7); ax.grid(alpha=.3)
            for k in np.where(keep)[0]:
                series.append({"source": src, "station_id": sid, "window": wl, "valid_time": sm.time[tv[k]],
                               "obs_m": float(sm.values[s, tv[k]]), "lstm_6h_m": float(pred[k, -1]), "persist_6h_m": float(last[k])})
        axes[0].set_ylabel("water level (m)"); axes[0].legend(fontsize=7, loc="upper left")
        ax = axes[3]
        hs = np.arange(1, HORIZON + 1)
        ax.bar(hs - 0.2, [r[f"rmse_model_{h}h"] * 100 for h in hs], 0.4, label="LSTM", color="C3")
        ax.bar(hs + 0.2, [r[f"rmse_persist_{h}h"] * 100 for h in hs], 0.4, label="persistence", color="C0")
        ax.set_xlabel("lead (h)"); ax.set_ylabel("RMSE test (cm)"); ax.legend(fontsize=7); ax.grid(axis="y", alpha=.3)
        fig.suptitle(f"{src} {sid} - {label}", fontsize=11); fig.tight_layout()
        fig.savefig(out / f"02_station_{sid}.png", dpi=130); plt.close(fig)
    pd.DataFrame(series).to_csv(out / "02_station_forecasts.csv", index=False)
    (out / "02_tables.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
