"""Event-scale forecast plots: a few-day window with every 1-6 h forecast trajectory drawn.

For each station three windows of `--days` days from the test period are chosen automatically:
  flood/storm : the window that contains the highest observed level
  worst       : the window with the largest 6 h-ahead RMSE
  typical     : the window whose 6 h RMSE is closest to the station's overall test RMSE
(or give windows explicitly with --start 2024-05-01 2024-07-07 ...). In every window the plot shows the
observation (black) and, for every origin at 00/06/12/18 UTC, the forecast trajectory issued at that time
(origin observation -> 1 h -> ... -> 6 h ahead). A second run can be drawn for comparison.

Usage (sv7):
  python event_plots.py --dataset DATA/dataset_v4 --run RUNS/v4_wind_q --label "v4: wind + discharge"
         [--run-b RUNS/v3_obs --label-b "water level only"] --out DIR --stations NOAA_COOPS:8747437 USGS:08114000
         [--days 4] [--start 2024-05-01 ...] [--every 6] [--test-end 2025-12-31T17]
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
from station_compare import load, series  # noqa: E402


def forecasts(model, sm, device, s: int, t0s: np.ndarray) -> np.ndarray:
    """All-horizon forecasts (m) [len(t0s), HORIZON] for the given origins; NaN rows where unusable."""
    ok = sm._ok(np.full(len(t0s), s), t0s)
    out = np.full((len(t0s), HORIZON), np.nan, np.float32)
    std, mean = float(sm.stations["std_m"].iloc[s]), float(sm.stations["mean_m"].iloc[s])
    if ok.any():
        idx = np.where(ok)[0]
        feats, fut, ss, y, ym = sm.window(np.full(len(idx), s), t0s[idx])
        f, fu, st, _, _ = to_torch((feats, fut, ss, y, ym), device)
        with torch.no_grad():
            out[idx] = model(f, st, fu).cpu().numpy() * std + mean
    return out


def pick_windows(time: pd.DatetimeIndex, obs: np.ndarray, f6: np.ndarray, hours: int) -> dict[str, int]:
    """Start index (into the test slice) of the flood/storm, worst and typical windows."""
    n = len(obs) - hours
    starts = np.arange(0, n, 24)
    mx = np.array([np.nanmax(obs[i:i + hours]) if np.isfinite(obs[i:i + hours]).any() else -np.inf for i in starts])
    err = np.array([np.sqrt(np.nanmean((f6[i:i + hours] - obs[i:i + hours]) ** 2)) if np.isfinite(f6[i:i + hours] - obs[i:i + hours]).sum() > hours / 2 else np.nan for i in starts])
    overall = np.sqrt(np.nanmean((f6 - obs) ** 2))
    w = {"flood / storm (highest level)": int(starts[np.nanargmax(mx)]),
         "worst 6 h RMSE": int(starts[np.nanargmax(err)]),
         "typical (RMSE = station average)": int(starts[np.nanargmin(np.abs(err - overall))])}
    # centre the flood window on the peak
    i = w["flood / storm (highest level)"]; k = int(np.nanargmax(obs[i:i + hours])); w["flood / storm (highest level)"] = max(0, min(n - 1, i + k - hours // 2))
    return w


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--run", required=True); ap.add_argument("--label", default="forecast")
    ap.add_argument("--run-b"); ap.add_argument("--label-b", default="water level only"); ap.add_argument("--dataset-b")
    ap.add_argument("--out", required=True); ap.add_argument("--stations", nargs="+", required=True)
    ap.add_argument("--days", type=float, default=4); ap.add_argument("--every", type=int, default=6, help="hours between drawn forecast origins")
    ap.add_argument("--start", nargs="*", help="explicit window starts (UTC) instead of automatic choice")
    ap.add_argument("--test-end", default="2025-12-31T17")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    sm, model = load(Path(a.run), Path(a.dataset), device)
    sm_b = model_b = None
    if a.run_b:
        sm_b, model_b = load(Path(a.run_b), Path(a.dataset_b or a.dataset), device)
    st = sm.stations.reset_index(); st["station_id"] = st.station_id.astype(str)
    lo, hi = sm.split_range("test")
    hi = min(hi, int(np.searchsorted(sm.time.values, np.datetime64(a.test_end)))) + HORIZON
    time = pd.DatetimeIndex(sm.time[lo:hi])
    hours = int(a.days * 24)
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    rows = []
    for key in a.stations:
        src, sid = key.split(":")
        m = st[(st.source == src) & (st.station_id == sid)]
        if m.empty:
            print("missing", key); continue
        s = int(m.row.iloc[0]); name = m.name.iloc[0]
        obs = np.asarray(sm.values[s, lo:hi], np.float32)
        f6 = series(model, sm, device, s, lo, hi)
        if a.start:
            wins = {f"from {x}": int(np.searchsorted(time.values, np.datetime64(x))) for x in a.start}
        else:
            wins = pick_windows(time, obs, f6, hours)
        fig, axes = plt.subplots(len(wins), 1, figsize=(15, 3.6 * len(wins)))
        axes = np.atleast_1d(axes)
        for ax, (wname, i0) in zip(axes, wins.items()):
            i1 = min(i0 + hours, len(time) - HORIZON - 1)
            t0s = np.arange(lo + i0, lo + i1)                              # every origin in the window
            fc = forecasts(model, sm, device, s, t0s)
            fcb = forecasts(model_b, sm_b, device, s, t0s) if model_b is not None else None
            tw = time[i0:i1 + HORIZON]; ow = obs[i0:i1 + HORIZON]
            ax.plot(tw, ow, color="k", lw=1.6, label="observed", zorder=5)
            drawn = [j for j in range(len(t0s)) if time[i0 + j].hour % a.every == 0]
            lab_done = lab_done_b = False
            for j in drawn:
                if not np.isfinite(fc[j]).all():
                    continue
                tt = time[i0 + j: i0 + j + HORIZON + 1]
                yy = np.concatenate([[ow[j]], fc[j]])
                ax.plot(tt, yy, color="tab:red", lw=1.1, alpha=.9, marker="o", ms=2.2, label=None if lab_done else f"{a.label}: 1-6 h trajectory issued every {a.every} h", zorder=4); lab_done = True
                if fcb is not None and np.isfinite(fcb[j]).all():
                    ax.plot(tt, np.concatenate([[ow[j]], fcb[j]]), color="tab:blue", lw=.9, alpha=.8, ls="--", label=None if lab_done_b else f"{a.label_b}", zorder=3); lab_done_b = True
            # window errors per horizon (all origins, not only the drawn ones)
            e = []
            for h in range(HORIZON):
                tgt = obs[i0 + 1 + h: i1 + 1 + h]
                e.append(100 * np.sqrt(np.nanmean((fc[:, h] - tgt) ** 2)))
            eb = ""
            if fcb is not None:
                e2 = [100 * np.sqrt(np.nanmean((fcb[:, h] - obs[i0 + 1 + h: i1 + 1 + h]) ** 2)) for h in range(HORIZON)]
                eb = f"   |   {a.label_b}: 1 h {e2[0]:.1f}, 3 h {e2[2]:.1f}, 6 h {e2[5]:.1f} cm"
            ax.set_title(f"{wname}  —  {a.label} RMSE in this window: 1 h {e[0]:.1f}, 3 h {e[2]:.1f}, 6 h {e[5]:.1f} cm{eb}", fontsize=9.5, loc="left")
            ax.set_ylabel("water level (m)"); ax.grid(alpha=.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %Hh")); ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
            ax.legend(loc="upper left", fontsize=8)
            rows.append({"source": src, "station_id": sid, "name": name, "window": wname, "start": str(time[i0]), "hours": i1 - i0,
                         **{f"rmse_{h + 1}h_cm": round(e[h], 2) for h in range(HORIZON)}})
        fig.suptitle(f"{src} {sid} - {name}: forecasts issued every {a.every} h, each line = the 1-6 h forecast from that origin", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fig.savefig(out / f"event_{sid}.png", dpi=140); plt.close(fig)
        print(key, name, {k: str(time[v])[:13] for k, v in wins.items()})
    pd.DataFrame(rows).to_csv(out / "event_windows.csv", index=False)


if __name__ == "__main__":
    main()
