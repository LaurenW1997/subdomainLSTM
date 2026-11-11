"""Forecasts of several model versions at the same stations and windows, issued EVERY HOUR (deliverable 17 figures:
continuous lines of the forecast valid at each hour for 1, 3 and 6 h lead).

Same output format as extract_versions.py:
  <out>/<station>_obs.csv   window, time, obs
  <out>/<station>_fc.csv    window, origin, lead, valid, <version keys>
The version trained with HRRR forecast rainfall (--hrrr-key) was trained on 00/06/12/18 UTC origins with the HRRR cycle
issued `lag` h before the origin. For hourly origins the same construction is used: for origin t0 the 6 h rainfall total
comes from the cycle issued at t0 - lag, leads lag+1 .. lag+6, fetched here from the AWS archive for the hours needed
(mean of the 15 x 15 HRRR cells around the station = 45 km, as in training).
Usage (sv7): python extract_versions_hourly.py --windows windows.csv --out DIR --version key:run:dataset ...
             --hrrr-key base_fc --obs-key base_obs --hrrr-cells DATA/precip/hrrr_cells.csv
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from event_plots import forecasts  # noqa: E402
from station_compare import load  # noqa: E402
from data import HORIZON, to_torch  # noqa: E402
from hrrr_precip import fetch_apcp, values  # noqa: E402

DAYS = 4
BOX = 15


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", required=True, help="CSV: source, station_id, window, start (00 UTC)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", action="append", required=True, help="key:run_dir:dataset_dir")
    ap.add_argument("--hrrr-key", help="version whose future rainfall is the HRRR forecast")
    ap.add_argument("--obs-key", help="version with the same inputs but observed rainfall (used for input availability)")
    ap.add_argument("--hrrr-cells"); ap.add_argument("--lag", type=int, default=1); ap.add_argument("--threads", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    win = pd.read_csv(a.windows, dtype={"station_id": str})
    models = {}
    for spec in a.version:
        key, run, ds = spec.split(":")
        models[key] = load(Path(run), Path(ds), device)
        print("loaded", key, flush=True)
    sm0 = next(iter(models.values()))[0]
    time = pd.DatetimeIndex(sm0.time)
    st = sm0.stations.reset_index(); st["station_id"] = st.station_id.astype(str)
    hours = DAYS * 24
    rowof = {(r.source, r.station_id): int(r.row) for r in st.itertuples()}

    # ---- HRRR rainfall for hourly origins: (cycle, lead) -> box mean at each station that needs it
    rain = {}
    if a.hrrr_key:
        smh = models[a.hrrr_key][0]
        assert smh.future_rain_form == "total", "written for the 6 h total form"
        cells = pd.read_csv(a.hrrr_cells, dtype={"station_id": str})
        need = {}                                                    # (cycle, lead) -> set of station rows
        for w in win.itertuples():
            s = rowof[(w.source, w.station_id)]; i0 = int(time.searchsorted(pd.Timestamp(w.start)))
            for t0 in range(i0 - HORIZON, i0 + hours):
                cyc = time[t0] - pd.Timedelta(hours=a.lag)
                for h in range(1, HORIZON + 1):
                    need.setdefault((cyc, h + a.lag), set()).add(s)
        off = np.arange(-(BOX // 2), BOX // 2 + 1)
        print(f"HRRR: {len(need)} messages to fetch", flush=True)

        def work(job):
            with requests.Session() as s2:
                return job, fetch_apcp(job[0], job[1], s2)

        done = 0
        with ThreadPoolExecutor(a.threads) as ex:
            futs = [ex.submit(work, j) for j in need]
            for f in as_completed(futs):
                job, b = f.result(); done += 1
                if b is None:
                    continue
                try:
                    v = values(b)
                except Exception:  # noqa: BLE001
                    continue
                ny, nx = v.shape
                for s in need[job]:
                    iy, ix = int(cells.iy.iloc[s]), int(cells.ix.iloc[s])
                    jb = np.clip(iy + off, 0, ny - 1)[:, None]; ib = np.clip(ix + off, 0, nx - 1)[None, :]
                    rain[(s, job[0], job[1])] = float(v[jb, ib].mean())
                if done % 2000 == 0:
                    print(f"  {done}/{len(need)}", flush=True)
        print(f"HRRR: {len(rain)} station values", flush=True)

    for (src, sid), g in win.groupby(["source", "station_id"], sort=False):
        s = rowof[(src, sid)]
        obs_rows, fc_rows = [], []
        for w in g.itertuples():
            i0 = int(time.searchsorted(pd.Timestamp(w.start))); assert time[i0].hour == 0
            ob = np.asarray(sm0.values[s, i0:i0 + hours + 1], np.float32)
            obs_rows += [{"window": w.window, "time": time[i0 + j], "obs": float(ob[j])} for j in range(hours + 1)]
            t0s = np.arange(i0 - HORIZON, i0 + hours)                       # every hour
            fc = {}
            for k, (sm, mod) in models.items():
                if k != a.hrrr_key:
                    fc[k] = forecasts(mod, sm, device, s, t0s); continue
                tot = np.array([sum(rain.get((s, time[t0] - pd.Timedelta(hours=a.lag), h + a.lag), np.nan) for h in range(1, HORIZON + 1)) for t0 in t0s])
                ok = np.isfinite(tot)
                if a.obs_key:                                               # the other inputs: same availability as the observed-rain twin
                    ok &= models[a.obs_key][0]._ok(np.full(len(t0s), s), t0s)
                res = np.full((len(t0s), HORIZON), np.nan, np.float32)
                if ok.any():
                    idx = np.where(ok)[0]
                    feats, fut, ss, y, ym = sm.window(np.full(len(idx), s), t0s[idx])
                    fut = fut.copy(); fut[:, -1] = np.log1p(np.clip(tot[idx], 0, None))
                    f, fu, stt, _, _ = to_torch((feats, fut, ss, y, ym), device)
                    with torch.no_grad():
                        res[idx] = mod(f, stt, fu).cpu().numpy() * float(sm.stations["std_m"].iloc[s]) + float(sm.stations["mean_m"].iloc[s])
                fc[k] = res
            for n, t0 in enumerate(t0s):
                for h in range(1, HORIZON + 1):
                    fc_rows.append({"window": w.window, "origin": time[t0], "lead": h, "valid": time[t0 + h], **{k: float(v[n, h - 1]) for k, v in fc.items()}})
        pd.DataFrame(obs_rows).to_csv(out / f"{sid}_obs.csv", index=False)
        f = pd.DataFrame(fc_rows); f.to_csv(out / f"{sid}_fc.csv", index=False)
        print(src, sid, "missing forecasts per version:", {k: int(f[k].isna().sum()) for k in models}, "missing obs:", int(pd.DataFrame(obs_rows).obs.isna().sum()), flush=True)
    print("HOURLY_DONE", flush=True)


if __name__ == "__main__":
    main()
