"""deliverable 04: where is the error? Test-period RMSE split by period type and station type.

Period types (per hour):
  storm  - days when the domain's tide gauges show a large non-tidal deviation
           (|obs - NOAA tide prediction|, monthly-mean removed, averaged over the
           domain's NOAA stations) : top STORM_FRAC of test days per domain
  high   - the station's own level is above its test-period HIGH_Q quantile
           (river floods, sustained set-up) and the day is not a storm day
  calm   - everything else
Station types: from the census (site_type, county) and the source.

Writes 04_error_split.csv (station x period RMSE), 04_split_tables.md, 04_error_split.png.
Usage: python error_split.py --dataset DIR --run DIR --out DIR [--census config/stations_census.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from data import HORIZON, StationMatrix, to_torch  # noqa: E402
from model import GlobalLSTM  # noqa: E402
from common import HOURLY  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STORM_FRAC = 0.10
HIGH_Q = 0.95
PERIODS = ["calm", "high", "storm"]
HOUSTON_COUNTIES = {"201", "157", "339", "167", "071", "291"}   # Harris, Fort Bend, Montgomery, Galveston, Chambers, Liberty


def station_type(r: pd.Series) -> str:
    if r.source == "NOAA_COOPS":
        return "tide gauge"
    if r.source == "CRMS" or str(r.get("site_type", "")) == "WE":
        return "marsh"
    if r.source.startswith("USACE"):
        return "river / canal"
    st = str(r.get("site_type", ""))
    county = str(r.get("county", ""))
    if st in ("ES", "OC", "OC-CO", "ST-TS", "TS") or "TS" in st:
        return "estuary / tidal channel"
    if st.startswith("LK"):
        return "lake"
    if st.startswith("ST") and county in HOUSTON_COUNTIES and "Galveston100m" in str(r.domains):
        return "urban creek (Houston)"
    if st.startswith("ST"):
        return "river / canal"
    return "other"


def storm_days(sm: StationMatrix, st: pd.DataFrame, lo: int, hi: int) -> dict[str, set]:
    """Per domain: set of test-period dates whose mean |non-tidal residual| is in the top STORM_FRAC."""
    out = {}
    time = sm.time[lo:hi]
    for dom in ("Louisiana100m", "Galveston100m", "Texas100m"):
        res = []
        for _, r in st[(st.source == "NOAA_COOPS") & st.domains.astype(str).str.contains(dom)].iterrows():
            p = HOURLY / "NOAA_COOPS" / f"{r.station_id}.pred.parquet"
            if not p.exists():
                continue
            pred = pd.read_parquet(p)["pred_m"].reindex(time)
            obs = pd.Series(sm.values[int(r.row), lo:hi], index=time)
            d = obs - pred
            d = d - d.groupby(d.index.to_period("M")).transform("mean")   # remove datum / monthly offsets
            res.append(d.abs())
        if not res:
            out[dom] = set(); continue
        daily = pd.concat(res, axis=1).mean(axis=1).resample("1D").mean().dropna()
        thr = daily.quantile(1 - STORM_FRAC)
        out[dom] = set(daily[daily >= thr].index.date)
        print(f"{dom}: {len(res)} tide gauges, storm threshold {thr*100:.1f} cm, {len(out[dom])} storm days")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--run", required=True); ap.add_argument("--out", required=True); ap.add_argument("--test-end", help="last test origin, e.g. 2025-12-31T17")
    ap.add_argument("--census", default=str(REPO / "config" / "stations_census.csv"))
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
    st["station_id"] = st.station_id.astype(str)
    cen = pd.read_csv(a.census, dtype=str).drop_duplicates(["source", "station_id"])
    cen["county"] = cen.extra.str.extract(r"county=(\d+)")
    st = st.merge(cen[["source", "station_id", "site_type", "county", "coastal"]], on=["source", "station_id"], how="left")
    st["type"] = st.apply(station_type, axis=1)

    lo, hi = sm.split_range("test")
    if a.test_end:
        hi = min(hi, int(np.searchsorted(sm.time.values, np.datetime64(a.test_end))))
    hi = hi + HORIZON + 1
    sdays = storm_days(sm, st, lo, hi)
    dates = sm.time.date
    is_storm = {dom: np.array([d in days for d in dates]) for dom, days in sdays.items()}

    # evaluate every 6 h origin, keep per-sample squared errors with their period label
    S, T0 = sm.eval_origins("test", 6, t_hi=hi - HORIZON - 1)
    std = st["std_m"].to_numpy(np.float32)
    se = {p: np.zeros((sm.S, HORIZON)) for p in PERIODS}; n = {p: np.zeros((sm.S, HORIZON)) for p in PERIODS}
    # per-station high-water threshold over the test period
    test_vals = np.asarray(sm.values[:, lo:hi])
    q_high = np.nanquantile(test_vals, HIGH_Q, axis=1)
    dom_first = st.domains.astype(str).str.split(";").str[0].to_numpy()
    with torch.no_grad():
        for i in range(0, len(S), 8192):
            s, t0 = S[i:i + 8192], T0[i:i + 8192]
            feats, fut, _, y, ym = sm.window(s, t0)
            f, fu, stt, _, _ = to_torch((feats, fut, s, y, ym), device)
            pred = model(f, stt, fu).cpu().numpy()
            err2 = ((pred - y) * std[s][:, None]) ** 2
            tv = t0 + HORIZON                                                   # label by the 6 h target time
            storm = np.array([is_storm.get(dom_first[ss], np.zeros(sm.T, bool))[t] for ss, t in zip(s, tv)])
            level = np.asarray(sm.values)[s, tv]
            high = (~storm) & np.isfinite(level) & (level > q_high[s])
            calm = ~storm & ~high
            for p, m in (("storm", storm), ("high", high), ("calm", calm)):
                if not m.any():
                    continue
                for h in range(HORIZON):
                    w = ym[m, h]
                    np.add.at(se[p][:, h], s[m], np.where(w, err2[m, h], 0))
                    np.add.at(n[p][:, h], s[m], w)
    rows = st[["row", "source", "station_id", "name", "lat", "lon", "domains", "type"]].copy()
    for p in PERIODS:
        rows[f"rmse_6h_{p}_cm"] = 100 * np.sqrt(se[p][:, -1] / np.maximum(n[p][:, -1], 1))
        rows[f"n_6h_{p}"] = n[p][:, -1]
        rows[f"sse_6h_{p}"] = se[p][:, -1]
    tot_n = sum(n[p][:, -1] for p in PERIODS); tot_se = sum(se[p][:, -1] for p in PERIODS)
    rows["rmse_6h_all_cm"] = 100 * np.sqrt(tot_se / np.maximum(tot_n, 1)); rows["n_6h_all"] = tot_n
    rows = rows[rows.n_6h_all >= 24 * 30]
    rows.to_csv(out / "04_error_split.csv", index=False)

    # tables
    md = ["## 误差按时段拆分（测试集，提前 6 小时，RMSE cm）", "",
          f"时段定义：**storm** = 本域 NOAA 潮位站非潮汐偏差（观测 − 潮汐预报）日均绝对值排前 {STORM_FRAC*100:.0f}% 的日子（冷锋、风暴）；"
          f"**high** = 该站自身水位高于其测试期 {HIGH_Q*100:.0f}% 分位（河流涨水、持续壅水），且不是 storm 日；**calm** = 其余时间。", "",
          "| 站点类型 | 站数 | calm | high | storm | 全部 | 样本占比 calm/high/storm | 误差（平方和）占比 calm/high/storm |", "|---|---|---|---|---|---|---|---|"]

    def line(label, g):
        med = {p: g[f"rmse_6h_{p}_cm"][g[f"n_6h_{p}"] > 0].median() for p in PERIODS}
        nn = {p: g[f"n_6h_{p}"].sum() for p in PERIODS}; ss = {p: g[f"sse_6h_{p}"].sum() for p in PERIODS}
        N = sum(nn.values()); SS = sum(ss.values())
        return (f"| {label} | {len(g)} | {med['calm']:.1f} | {med['high']:.1f} | {med['storm']:.1f} | {g.rmse_6h_all_cm.median():.1f} | "
                f"{nn['calm']/N*100:.0f}/{nn['high']/N*100:.0f}/{nn['storm']/N*100:.0f}% | {ss['calm']/SS*100:.0f}/{ss['high']/SS*100:.0f}/{ss['storm']/SS*100:.0f}% |")

    order = ["tide gauge", "marsh", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)", "other"]
    for t in order:
        g = rows[rows.type == t]
        if len(g):
            md.append(line(t, g))
    md.append(line("**全部**", rows))
    md += ["", "RMSE 列是该类站各站 RMSE 的中位数。最后两列说明：各时段占了多少预报样本，以及占了多少误差（平方和）——误差占比远大于样本占比的时段，就是模型最吃力、需要外部输入的时段。", "",
           "## 按 domain", "", "| domain | 站数 | calm | high | storm | 全部 | 样本占比 | 误差占比 |", "|---|---|---|---|---|---|---|---|"]
    for dom in ("Louisiana100m", "Galveston100m", "Texas100m"):
        g = rows[rows.domains.astype(str).str.contains(dom)]
        md.append(line(dom, g))
    (out / "04_split_tables.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    types = [t for t in order if (rows.type == t).sum() >= 5]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(types)); w = 0.26
    for k, (p, c) in enumerate(zip(PERIODS, ["C2", "C0", "C3"])):
        vals = [rows[(rows.type == t) & (rows[f"n_6h_{p}"] > 0)][f"rmse_6h_{p}_cm"].median() for t in types]
        ax.bar(x + (k - 1) * w, vals, w, label=p, color=c)
    ax.set_xticks(x); ax.set_xticklabels([f"{t}\n({(rows.type == t).sum()})" for t in types], fontsize=8)
    ax.set_ylabel("median 6 h RMSE (cm)"); ax.legend(title="period"); ax.grid(axis="y", alpha=.3)
    ax.set_title("6 h RMSE by station type and period, test period")
    fig.tight_layout(); fig.savefig(out / "04_error_split.png", dpi=150)


if __name__ == "__main__":
    main()
