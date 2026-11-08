"""Operational inference: pull the last 72 h of observations from the live USGS / NOAA
APIs (plus HRRR wind and USGS discharge when the model uses them), run the trained
global LSTM, write 1-6 h water-level forecasts for every station.

Only sources with a real-time feed are forecast (USGS NWIS IV, NOAA CO-OPS). CRMS and
USACE stations in the model are listed in the output with status "no_realtime_source".

Model dir needs best.pt + stations.csv (training station order). A wind model also needs
wind_coverage.csv, a discharge model q_norm.csv (both written by build_extras.py).

Output: <out>/<cycle>/forecast.csv, manifest.json, raw/ (verbatim API payloads).
  forecast.csv columns: source, station_id, name, lat, lon, domains, datum, cycle_utc,
  last_obs_utc, last_obs_m, fcst_1h_m .. fcst_6h_m, input_valid_frac, wind_valid_frac,
  q_valid_frac, status
Usage: python forecast.py --model RUN_DIR [--cycle 2026-11-08T12] [--out DIR] [--sources USGS NOAA_COOPS]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "train"))
sys.path.insert(0, str(HERE.parents[0] / "data"))
from model import GlobalLSTM  # noqa: E402
from common import FT, census, extra, get, log, to_hourly  # noqa: E402
from data import WIND_SCALE  # noqa: E402

REPO = HERE.parents[1]
HORIZON = 6
MIN_INPUT_VALID = 0.7
MAX_STALE_H = 3
CFS = 0.028316846592
USGS_URL = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_PAUSE = 0.6


# ----------------------------------------------------------------------------- live data
def fetch_usgs(sites: list[str], begin: pd.Timestamp, end: pd.Timestamp, raw_dir: Path, param: str = "00065", tag: str = "usgs") -> dict[str, pd.Series]:
    """One USGS IV parameter (00065 gauge height ft, 00060 discharge cfs) for many sites per call."""
    out: dict[str, pd.Series] = {}
    for i in range(0, len(sites), 80):
        chunk = sites[i:i + 80]
        r = get(USGS_URL, {"format": "json", "sites": ",".join(chunk), "parameterCd": param,
                           "startDT": begin.strftime("%Y-%m-%dT%H:%MZ"), "endDT": end.strftime("%Y-%m-%dT%H:%MZ"),
                           "siteStatus": "all"})
        (raw_dir / f"{tag}_{i // 80:02d}.json").write_text(r.text, encoding="utf-8")
        if r.status_code != 200:
            log.error("USGS %s chunk %d: HTTP %s", param, i // 80, r.status_code); continue
        for ts in (r.json().get("value") or {}).get("timeSeries") or []:
            site = ts["sourceInfo"]["siteCode"][0]["value"]
            nodata = ts.get("variable", {}).get("noDataValue")
            parts = []
            for block in ts.get("values", []):
                vals = block.get("value", [])
                if not vals:
                    continue
                df = pd.DataFrame(vals)
                t = pd.to_datetime(df["dateTime"], utc=True).dt.tz_convert(None)
                v = pd.to_numeric(df["value"], errors="coerce")
                if nodata is not None:
                    v = v.mask(v == float(nodata))
                parts.append(pd.Series(v.values, index=t))
            if parts:
                s = pd.concat(parts)
                out[site] = pd.concat([out[site], s]) if site in out else s
    return out


def fetch_noaa(station: str, datum: str, begin: pd.Timestamp, end: pd.Timestamp, raw_dir: Path) -> pd.Series:
    """6-minute water level in metres on the requested datum (NAVD or MSL)."""
    params = {"product": "water_level", "application": "LSU_subdomainLSTM_operational", "station": station,
              "datum": datum, "units": "metric", "time_zone": "gmt", "format": "json",
              "begin_date": begin.strftime("%Y%m%d %H:%M"), "end_date": end.strftime("%Y%m%d %H:%M")}
    r = get(NOAA_URL, params)
    (raw_dir / f"noaa_{station}.json").write_text(r.text, encoding="utf-8")
    time.sleep(NOAA_PAUSE)
    try:
        j = r.json()
    except ValueError:
        log.error("NOAA %s: non-JSON reply", station); return pd.Series(dtype=float)
    if "data" not in j:
        log.warning("NOAA %s: %s", station, (j.get("error") or {}).get("message") or j.get("message") or j); return pd.Series(dtype=float)
    df = pd.DataFrame(j["data"])
    t = pd.to_datetime(df["t"], format="%Y-%m-%d %H:%M")
    v = pd.to_numeric(df["v"], errors="coerce")
    return pd.Series(v.values, index=t)


def fetch_discharge(st: pd.DataFrame, run_dir: Path, index: pd.DatetimeIndex, raw_dir: Path) -> tuple[np.ndarray, dict]:
    """Normalised upstream discharge [S, L] for every station (NaN where no gauge / no data),
    exactly as build_extras.py: m3/s, clip >= 0, log1p, z-score with the gauge's train-period mean/std."""
    m = pd.read_csv(REPO / "config" / "station_discharge_map.csv", dtype=str)
    m = st[["source", "station_id"]].merge(m[["source", "station_id", "gauge_id"]], on=["source", "station_id"], how="left")
    norm = pd.read_csv(run_dir / "q_norm.csv", dtype={"gauge_id": str}).set_index("gauge_id")
    gauges = sorted(g for g in m.gauge_id.dropna().unique() if g in norm.index)
    raw = fetch_usgs(gauges, index[0] - pd.Timedelta(hours=1), index[-1] + pd.Timedelta(minutes=59), raw_dir, param="00060", tag="usgs_q")
    series = {}
    for g in gauges:
        s = raw.get(g)
        if s is None or s.empty:
            continue
        h = to_hourly(s * CFS).reindex(index)
        x = np.log1p(h.clip(lower=0))
        series[g] = ((x - norm.loc[g, "mu_log1p"]) / norm.loc[g, "sd_log1p"]).to_numpy(np.float32)
    q = np.full((len(st), len(index)), np.nan, np.float32)
    for i, g in enumerate(m.gauge_id):
        if isinstance(g, str) and g in series:
            q[i] = series[g]
    info = {"n_gauges": len(gauges), "n_gauges_with_data": len(series), "gauges_without_data": sorted(set(gauges) - set(series))}
    log.info("discharge: %d/%d gauges returned data", len(series), len(gauges))
    return q, info


# ----------------------------------------------------------------------------- features
def time_features(index: pd.DatetimeIndex) -> np.ndarray:
    hours = index.hour.to_numpy() + index.minute.to_numpy() / 60
    doy = index.day_of_year.to_numpy() + hours / 24
    return np.stack([np.sin(2 * np.pi * hours / 24), np.cos(2 * np.pi * hours / 24),
                     np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)], 1).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="run dir with best.pt and stations.csv")
    ap.add_argument("--cycle", help="forecast origin, UTC hour, e.g. 2026-11-08T12 (default: last full hour - 1)")
    ap.add_argument("--out", default="/data/ywan245/subdomainLSTM/operational")
    ap.add_argument("--sources", nargs="*", default=["USGS", "NOAA_COOPS"])
    ap.add_argument("--wind-cache", help="HRRR cache dir (default <out>/wind)")
    a = ap.parse_args()

    cycle = pd.Timestamp(a.cycle) if a.cycle else pd.Timestamp.now("UTC").tz_localize(None).floor("h") - pd.Timedelta(hours=1)
    run_dir = Path(a.model)
    out = Path(a.out) / cycle.strftime("%Y%m%dT%H"); raw_dir = out / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)
    ck = torch.load(run_dir / "best.pt", map_location="cpu")
    args = ck["args"]
    lookback = int(args.get("lookback", 72))
    use_wind, use_future, use_q = bool(args.get("wind")), bool(args.get("wind") and args.get("future_wind")), bool(args.get("discharge"))
    model = GlobalLSTM(ck["n_stations"], n_feat=ck.get("n_feat", 6), hidden=args["hidden"], layers=args["layers"], n_future=ck.get("n_future", 0))
    model.load_state_dict(ck["state_dict"]); model.eval()
    st = pd.read_csv(run_dir / "stations.csv", dtype={"station_id": str})
    assert len(st) == ck["n_stations"], "stations.csv does not match the checkpoint"
    log.info("cycle %s UTC, model %s (%d stations, lookback %d h, wind=%s future_wind=%s discharge=%s)",
             cycle, run_dir.name, len(st), lookback, use_wind, use_future, use_q)

    index = pd.date_range(cycle - pd.Timedelta(hours=lookback - 1), cycle, freq="1h")
    future_index = pd.date_range(cycle + pd.Timedelta(hours=1), periods=HORIZON, freq="1h")
    begin, end = index[0] - pd.Timedelta(hours=1), cycle + pd.Timedelta(minutes=59)
    series: dict[tuple[str, str], pd.Series] = {}
    manifest_extra: dict = {}

    # USGS: feet above gauge datum -> metres (+ NAVD88 offset where the census has it)
    if "USGS" in a.sources:
        usgs = st[st.source == "USGS"]
        cen = census("USGS", only_active=False).set_index("station_id")
        raw = fetch_usgs(usgs.station_id.tolist(), begin, end, raw_dir)
        for sid in usgs.station_id:
            s = raw.get(sid)
            if s is None or s.empty:
                continue
            s = s * FT
            row = cen.loc[sid] if sid in cen.index else None
            if row is not None and extra(row, "alt_ft") and str(row.get("datum", "")) == "NAVD88":
                s = s + float(extra(row, "alt_ft")) * FT
            series[("USGS", sid)] = s
        log.info("USGS: %d/%d stations returned data", sum(1 for k in series if k[0] == "USGS"), len(usgs))

    if "NOAA_COOPS" in a.sources:
        noaa = st[st.source == "NOAA_COOPS"]
        for _, r in noaa.iterrows():
            datum = "MSL" if str(r.datum).upper().startswith("MSL") else "NAVD"
            s = fetch_noaa(r.station_id, datum, begin, end, raw_dir)
            if not s.empty:
                series[("NOAA_COOPS", r.station_id)] = s
        log.info("NOAA: %d/%d stations returned data", sum(1 for k in series if k[0] == "NOAA_COOPS"), len(noaa))

    # ---- wind (HRRR) and discharge (USGS 00060) for all stations at once
    u_p = v_p = u_f = v_f = q = None
    wind_cov = None
    if use_wind:
        from hrrr_wind import station_wind
        cov = pd.read_csv(run_dir / "wind_coverage.csv", dtype={"station_id": str})
        assert (cov.station_id.to_numpy() == st.station_id.to_numpy()).all(), "wind_coverage.csv does not match stations.csv"
        wind_cov = cov.wind_valid_frac.to_numpy()
        t = time.time()
        u_p, v_p, u_f, v_f, prov = station_wind(st, index, future_index, Path(a.wind_cache) if a.wind_cache else Path(a.out) / "wind")
        manifest_extra["wind"] = {"source": "HRRR conus wrfsfc, 10 m UGRD/VGRD, nearest cell", "seconds": round(time.time() - t),
                                  "past_valid_frac": float(np.isfinite(u_p).mean()), "future_valid_frac": float(np.isfinite(u_f).mean()),
                                  "past_fhr_counts": pd.Series(list(prov["past"].values())).value_counts().to_dict() if prov["past"] else {},
                                  "future_fhr": prov["future"], "cells": prov["cells"]}
        log.info("wind: past valid %.3f, future valid %.3f, %d s", np.isfinite(u_p).mean(), np.isfinite(u_f).mean(), time.time() - t)
    if use_q:
        q, qinfo = fetch_discharge(st, run_dir, index, raw_dir)
        manifest_extra["discharge"] = qinfo

    # ---- windows -> model
    tf = time_features(index)
    feats, futs, rows_idx, recs = [], [], [], []
    for i, r in st.iterrows():
        key = (r.source, r.station_id)
        rec = {"source": r.source, "station_id": r.station_id, "name": r["name"], "lat": r.lat, "lon": r.lon,
               "domains": r.domains, "datum": r.datum, "cycle_utc": cycle, "last_obs_utc": None, "last_obs_m": np.nan,
               **{f"fcst_{h}h_m": np.nan for h in range(1, HORIZON + 1)}, "input_valid_frac": 0.0,
               "wind_valid_frac": np.nan, "q_valid_frac": np.nan, "status": ""}
        if r.source not in a.sources:
            rec["status"] = "no_realtime_source"; recs.append(rec); continue
        if key not in series:
            rec["status"] = "no_data_returned"; recs.append(rec); continue
        h = to_hourly(series[key]).reindex(index)
        valid = h.notna()
        rec["input_valid_frac"] = float(valid.mean())
        if valid.any():
            last_t = h.dropna().index[-1]
            rec["last_obs_utc"], rec["last_obs_m"] = last_t, float(h.dropna().iloc[-1])
        if valid.mean() < MIN_INPUT_VALID:
            rec["status"] = "insufficient_input"; recs.append(rec); continue
        if (cycle - rec["last_obs_utc"]) > pd.Timedelta(hours=MAX_STALE_H):
            rec["status"] = "stale"; recs.append(rec); continue
        x = ((h.to_numpy(np.float32) - r.mean_m) / r.std_m)
        m = valid.to_numpy(np.float32)
        parts = [np.nan_to_num(x)[:, None], m[:, None], tf]
        fut = np.zeros(0, np.float32)
        if use_wind:
            if wind_cov[i] == 0:                      # station never had wind in training (offshore, no AORC cell)
                rec["status"] = "no_wind_in_training"; recs.append(rec); continue
            wm = np.isfinite(u_p[i]) & np.isfinite(v_p[i])
            rec["wind_valid_frac"] = float(wm.mean())
            if wm.mean() < MIN_INPUT_VALID or (use_future and not (np.isfinite(u_f[i]).all() and np.isfinite(v_f[i]).all())):
                rec["status"] = "insufficient_wind"; recs.append(rec); continue
            parts += [np.nan_to_num(u_p[i] / WIND_SCALE)[:, None], np.nan_to_num(v_p[i] / WIND_SCALE)[:, None], wm.astype(np.float32)[:, None]]
            if use_future:
                fut = np.concatenate([u_f[i] / WIND_SCALE, v_f[i] / WIND_SCALE]).astype(np.float32)
        if use_q:
            qm = np.isfinite(q[i])
            rec["q_valid_frac"] = float(qm.mean())
            parts += [np.nan_to_num(q[i])[:, None], qm.astype(np.float32)[:, None]]
        feats.append(np.concatenate(parts, 1)); futs.append(fut)
        rows_idx.append(i); rec["status"] = "ok"; recs.append(rec)
    df = pd.DataFrame(recs)
    if feats:
        with torch.no_grad():
            f = torch.from_numpy(np.stack(feats)); fu = torch.from_numpy(np.stack(futs)) if use_future else None
            pred = model(f, torch.tensor(rows_idx, dtype=torch.long), fu).numpy()
        mean = st.loc[rows_idx, "mean_m"].to_numpy(); std = st.loc[rows_idx, "std_m"].to_numpy()
        pred = pred * std[:, None] + mean[:, None]
        for h in range(HORIZON):
            df.loc[rows_idx, f"fcst_{h+1}h_m"] = pred[:, h]
    df["valid_time_6h_utc"] = cycle + pd.Timedelta(hours=HORIZON)
    df.to_csv(out / "forecast.csv", index=False)
    manifest = {"cycle_utc": str(cycle), "model": str(run_dir), "checkpoint_args": args, "lookback_h": lookback,
                "horizon_h": HORIZON, "n_feat": ck.get("n_feat", 6), "n_future": ck.get("n_future", 0),
                "n_stations": int(len(df)), "status_counts": df.status.value_counts().to_dict(),
                "sources": a.sources, **manifest_extra, "generated_utc": str(pd.Timestamp.now("UTC").tz_localize(None).floor("s"))}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    log.info("wrote %s: %s", out / "forecast.csv", manifest["status_counts"])


if __name__ == "__main__":
    main()
