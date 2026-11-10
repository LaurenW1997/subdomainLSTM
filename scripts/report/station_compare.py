"""deliverable 06: for chosen stations, 6 h forecasts of two runs over the test window.

Top panel: observed vs 6 h-ahead forecast of run A and run B over the whole test period.
Bottom: monthly 6 h RMSE of both runs, so one can see in which months the inputs help or hurt.
Usage: python station_compare.py --dataset DIR --run-a runs/v3_obs --run-b runs/v3_wind_q --out DIR
                                 --stations USGS:08114000 NOAA_COOPS:8747437 ... [--test-end 2025-12-31T17]
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


def load(run: Path, dataset: Path, device):
    ck = torch.load(run / "best.pt", map_location=device)
    def local(p):   # trained on another machine: same file under this repo's config/
        return None if not p else (p if Path(p).exists() else str(Path(__file__).resolve().parents[2] / "config" / Path(p).name))
    sm = StationMatrix(dataset, lookback=ck["args"].get("lookback", 72), use_wind=ck["args"].get("wind", False),
                       use_future_wind=ck["args"].get("future_wind", False), use_q=ck["args"].get("discharge", False),
                       stations=local(ck["args"].get("stations")), no_wind_stations=local(ck["args"].get("no_wind_stations")),
                       use_rain=ck["args"].get("rain", False), use_future_rain=ck["args"].get("future_rain", False), rain_var=ck["args"].get("rain_var", "p15"),
                       rain_fc=ck["args"].get("rain_fc"), future_rain_form=ck["args"].get("future_rain_form", "hourly"),
                       fill=ck["args"].get("fill", "zero"), delta_norm=ck["args"].get("delta_norm", False), delta_feat=ck["args"].get("delta_feat", False))
    model = GlobalLSTM(ck["n_stations"], n_feat=ck.get("n_feat", 6), hidden=ck["args"]["hidden"], layers=ck["args"]["layers"],
                       n_future=ck.get("n_future", 0), delta_scale=ck["args"].get("delta_norm", False)).to(device)
    model.load_state_dict(ck["state_dict"]); model.eval()
    return sm, model


def series(model, sm, device, s: int, lo: int, hi: int):
    """6 h-ahead forecast (m) valid at every hour in [lo, hi); NaN where the window is not usable."""
    t0 = np.arange(lo - HORIZON, hi - HORIZON)
    ok = sm._ok(np.full(len(t0), s), t0)
    out = np.full(len(t0), np.nan, np.float32)
    std, mean = float(sm.stations["std_m"].iloc[s]), float(sm.stations["mean_m"].iloc[s])
    with torch.no_grad():
        for i in range(0, ok.sum(), 4096):
            idx = np.where(ok)[0][i:i + 4096]
            feats, fut, ss, y, ym = sm.window(np.full(len(idx), s), t0[idx])
            f, fu, st, _, _ = to_torch((feats, fut, ss, y, ym), device)
            out[idx] = model(f, st, fu)[:, -1].cpu().numpy() * std + mean
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--run-a", required=True); ap.add_argument("--run-b", required=True)
    ap.add_argument("--dataset-b", help="dataset for run B when its inputs differ (e.g. another discharge mapping); default = --dataset")
    ap.add_argument("--label-a", default="water level only"); ap.add_argument("--label-b", default="wind + discharge")
    ap.add_argument("--out", required=True); ap.add_argument("--stations", nargs="+", required=True); ap.add_argument("--test-end", default="2025-12-31T17")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    sm_a, model_a = load(Path(a.run_a), Path(a.dataset), device)
    sm_b, model_b = load(Path(a.run_b), Path(a.dataset_b or a.dataset), device)
    st = sm_a.stations.reset_index(); st["station_id"] = st.station_id.astype(str)
    lo, hi = sm_a.split_range("test")
    hi = min(hi, int(np.searchsorted(sm_a.time.values, np.datetime64(a.test_end)))) + HORIZON
    time = sm_a.time[lo:hi]
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = []
    for key in a.stations:
        src, sid = key.split(":")
        m = st[(st.source == src) & (st.station_id == sid)]
        if m.empty:
            print("missing", key); continue
        s = int(m.row.iloc[0]); name = m.name.iloc[0]
        obs = np.asarray(sm_a.values[s, lo:hi], np.float32)
        pa, pb = series(model_a, sm_a, device, s, lo, hi), series(model_b, sm_b, device, s, lo, hi)
        df = pd.DataFrame({"obs": obs, "a": pa, "b": pb}, index=time)
        df["ea"] = (df.a - df.obs) ** 2; df["eb"] = (df.b - df.obs) ** 2
        mon = df[["ea", "eb"]].resample("MS").mean().pipe(np.sqrt) * 100
        both = df.dropna()
        ra, rb = 100 * np.sqrt(((both.a - both.obs) ** 2).mean()), 100 * np.sqrt(((both.b - both.obs) ** 2).mean())
        rows.append({"source": src, "station_id": sid, "name": name, "rmse_6h_a_cm": ra, "rmse_6h_b_cm": rb, "n": len(both)})
        fig, axes = plt.subplots(2, 1, figsize=(16, 6.5), gridspec_kw={"height_ratios": [2.2, 1]})
        ax = axes[0]
        ax.plot(df.index, df.obs, "k", lw=.8, label="observed")
        ax.plot(df.index, df.a, "C0", lw=.6, alpha=.8, label=f"{a.label_a} (6 h RMSE {ra:.1f} cm)")
        ax.plot(df.index, df.b, "C3", lw=.6, alpha=.8, label=f"{a.label_b} (6 h RMSE {rb:.1f} cm)")
        ax.set_ylabel("water level (m)"); ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=.3)
        ax.set_title(f"{src} {sid} - {name}: 6 h-ahead forecasts over the test period", fontsize=10)
        ax = axes[1]
        w = 12
        ax.bar(mon.index - pd.Timedelta(days=w / 2), mon.ea, w, color="C0", label=a.label_a)
        ax.bar(mon.index + pd.Timedelta(days=w / 2), mon.eb, w, color="C3", label=a.label_b)
        ax.set_ylabel("monthly 6 h RMSE (cm)"); ax.grid(axis="y", alpha=.3); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(out / f"06_station_{sid}.png", dpi=130); plt.close(fig)
        print(key, name, f"A {ra:.1f}  B {rb:.1f} cm")
    pd.DataFrame(rows).to_csv(out / "06_station_compare.csv", index=False)


if __name__ == "__main__":
    main()
