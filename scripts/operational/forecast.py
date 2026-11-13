"""Operational inference: pull the last 72 h of observations from the live USGS / NOAA
APIs (plus HRRR wind, HRRR rainfall and USGS discharge when the model uses them), run the trained
global LSTM, write 1-6 h water-level forecasts for every station.

Which inputs are built is read from the training switches stored in best.pt:
  --wind / --future-wind      HRRR 10 m wind (hrrr_wind.py)
  --discharge                 USGS discharge of the upstream gauge
  --rain / --future-rain      past hours: MRMS radar rainfall (mrms_rain.py), hours MRMS lacks from the 1 h lead of the
                              hourly HRRR cycles (hrrr_rain.py); the 6 target hours: one HRRR cycle issued `lag` h
                              before the origin (--rain-fc hrrr_lag<L>_p<km>)
  --fill ffill                a missing hour takes the last valid level (FILL_EXTRA_H more hours are fetched for this)
  --delta-norm / --delta-feat forecast change scaled by the station's typical 6 h change (scale saved in best.pt)
Switches this script does not build inputs for (--long-feat, --downstream, --upstream-stage, --stations) stop it.

Only sources with a real-time feed are forecast (USGS NWIS IV, NOAA CO-OPS). CRMS and
USACE stations in the model are listed in the output with status "no_realtime_source".

Model dir needs best.pt + stations.csv (training station order). A wind model also needs
wind_coverage.csv, a discharge model q_norm.csv (both written by build_extras.py).

Output: <out>/<cycle>/forecast.csv, manifest.json, raw/ (verbatim API payloads).
  forecast.csv columns: source, station_id, name, lat, lon, domains, datum, cycle_utc,
  last_obs_utc, last_obs_m, fcst_1h_m .. fcst_6h_m, input_valid_frac, wind_valid_frac,
  q_valid_frac, rain_valid_frac, rain_past72h_mm, rain_next6h_mm, status
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
FILL_EXTRA_H = 24        # extra hours fetched before the window so that a gap at its start can be filled from the last valid level
CFS = 0.028316846592
USGS_URL = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_PAUSE = 0.6
USGS_PAD_H = 2            # hours added on both sides of a USGS request (see fetch_usgs)


# ----------------------------------------------------------------------------- live data
def fetch_usgs(sites: list[str], begin: pd.Timestamp, end: pd.Timestamp, raw_dir: Path, param: str = "00065", tag: str = "usgs") -> dict[str, pd.Series]:
    """One USGS IV parameter (00065 gauge height ft, 00060 discharge cfs) for many sites per call.

    The service does not honour the requested UTC window exactly: while daylight-saving time is in force at a site it
    returns data from one hour before `begin` to one hour before `end` (seen 2024-07: endDT 12:59Z -> last reading
    11:45Z). The newest hour would then be averaged from the first half of its readings only. So the request is padded
    by USGS_PAD_H on both sides and the readings, whose own time stamps carry the correct offset, are cut to
    [begin, end] here."""
    out: dict[str, pd.Series] = {}
    pad = pd.Timedelta(hours=USGS_PAD_H)
    for i in range(0, len(sites), 80):
        chunk = sites[i:i + 80]
        r = get(USGS_URL, {"format": "json", "sites": ",".join(chunk), "parameterCd": param,
                           "startDT": (begin - pad).strftime("%Y-%m-%dT%H:%MZ"), "endDT": (end + pad).strftime("%Y-%m-%dT%H:%MZ"),
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
                s = s[(s.index >= begin) & (s.index <= end)]
                if not s.empty:
                    out[site] = pd.concat([out[site], s]) if site in out else s
    return out


def fetch_noaa(station: str, datum: str, begin: pd.Timestamp, end: pd.Timestamp, raw_dir: Path) -> pd.Series:
    """6-minute water level in metres on the requested datum (NAVD or MSL)."""
    params = {"product": "water_level", "application": "LSU_subdomainLSTM_operational", "station": station,
              "datum": datum, "units": "metric", "time_zone": "gmt", "format": "json",
              "begin_date": begin.strftime("%Y%m%d %H:%M"), "end_date": end.strftime("%Y%m%d %H:%M")}
    for attempt in range(4):     # CO-OPS answers {"message": "Forbidden"} while another client of the same host is downloading
        r = get(NOAA_URL, params)
        (raw_dir / f"noaa_{station}.json").write_text(r.text, encoding="utf-8")
        time.sleep(NOAA_PAUSE)
        try:
            j = r.json()
        except ValueError:
            log.error("NOAA %s: non-JSON reply", station); return pd.Series(dtype=float)
        if j.get("message") != "Forbidden":
            break
        time.sleep(5 * (attempt + 1))
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


def fetch_levels(st: pd.DataFrame, sources: list[str], begin: pd.Timestamp, end: pd.Timestamp, raw_dir: Path) -> dict[tuple[str, str], pd.Series]:
    """Water level in metres on each station's own datum, {(source, station_id): series at the native time step}."""
    series: dict[tuple[str, str], pd.Series] = {}
    # USGS: feet above gauge datum -> metres (+ NAVD88 offset where the census has it)
    if "USGS" in sources:
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
    if "NOAA_COOPS" in sources:
        noaa = st[st.source == "NOAA_COOPS"]
        for _, r in noaa.iterrows():
            datum = "MSL" if str(r.datum).upper().startswith("MSL") else "NAVD"
            s = fetch_noaa(r.station_id, datum, begin, end, raw_dir)
            if not s.empty:
                series[("NOAA_COOPS", r.station_id)] = s
        log.info("NOAA: %d/%d stations returned data", sum(1 for k in series if k[0] == "NOAA_COOPS"), len(noaa))
    return series


# ----------------------------------------------------------------------------- features
def time_features(index: pd.DatetimeIndex) -> np.ndarray:
    hours = index.hour.to_numpy() + index.minute.to_numpy() / 60
    doy = index.day_of_year.to_numpy() + hours / 24
    return np.stack([np.sin(2 * np.pi * hours / 24), np.cos(2 * np.pi * hours / 24),
                     np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)], 1).astype(np.float32)


# settings that decide the inputs: every member_*.pt must share them with best.pt
SAME_INPUTS = ("lookback", "wind", "future_wind", "discharge", "rain", "future_rain", "rain_var", "rain_fc", "future_rain_form", "fill",
               "delta_norm", "delta_power", "delta_feat", "long_feat", "downstream", "upstream_stage", "stations", "hidden", "layers")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="run dir with best.pt and stations.csv; member_*.pt next to best.pt are further models with the same inputs (other random seeds) and the forecast is then the mean of all of them")
    ap.add_argument("--cycle", help="forecast origin, UTC hour, e.g. 2026-11-08T12 (default: last full hour - 1)")
    ap.add_argument("--out", default="/data/ywan245/subdomainLSTM/operational")
    ap.add_argument("--sources", nargs="*", default=["USGS", "NOAA_COOPS"])
    ap.add_argument("--wind-cache", help="HRRR cache dir (default <out>/wind)")
    ap.add_argument("--rain-cache", help="rainfall cache dir (default <out>/rain)")
    ap.add_argument("--past-rain", choices=["mrms", "hrrr"], default="mrms", help="product for the look-back rainfall (hrrr = HRRR only)")
    a = ap.parse_args()

    cycle = pd.Timestamp(a.cycle) if a.cycle else pd.Timestamp.now("UTC").tz_localize(None).floor("h") - pd.Timedelta(hours=1)
    run_dir = Path(a.model)
    out = Path(a.out) / cycle.strftime("%Y%m%dT%H"); raw_dir = out / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)
    ck = torch.load(run_dir / "best.pt", map_location="cpu")
    args = ck["args"]
    lookback = int(args.get("lookback", 72))
    use_wind, use_future, use_q = bool(args.get("wind")), bool(args.get("wind") and args.get("future_wind")), bool(args.get("discharge"))
    use_rain = bool(args.get("rain")); use_future_rain = bool(use_rain and args.get("future_rain"))
    rain_form = args.get("future_rain_form", "hourly")
    ffill, delta_norm, delta_feat = args.get("fill", "zero") == "ffill", bool(args.get("delta_norm")), bool(args.get("delta_feat"))
    unsupported = [k for k in ("long_feat", "downstream", "upstream_stage", "stations") if args.get(k)]
    if unsupported:
        raise SystemExit(f"model trained with {unsupported}: forecast.py does not build these inputs")
    if use_future_rain and not args.get("rain_fc"):
        raise SystemExit("model trained with OBSERVED rainfall in the 6 target hours: not available in real time")
    n_feat_expected = 6 + 3 * use_wind + 2 * use_q + 2 * use_rain + delta_feat
    n_future_expected = 2 * HORIZON * use_future + (0 if not use_future_rain else (HORIZON if rain_form == "hourly" else 1))
    assert (ck.get("n_feat", 6), ck.get("n_future", 0)) == (n_feat_expected, n_future_expected), \
        f"checkpoint expects n_feat {ck.get('n_feat')} / n_future {ck.get('n_future')}, this script builds {n_feat_expected} / {n_future_expected}"
    model = GlobalLSTM(ck["n_stations"], n_feat=ck.get("n_feat", 6), hidden=args["hidden"], layers=args["layers"], n_future=ck.get("n_future", 0),
                       delta_scale=delta_norm, init_state=args.get("init_state", False))
    model.load_state_dict(ck["state_dict"]); model.eval()
    if delta_feat and not delta_norm:
        raise SystemExit("--delta-feat without --delta-norm: the scale is not stored in the checkpoint")
    rscale = model.rscale.numpy() if delta_norm else None
    # further models trained with the same settings and another random seed: the forecast is the mean of all members
    models, member_files = [model], sorted(run_dir.glob("member_*.pt"))
    for mf in member_files:
        mk = torch.load(mf, map_location="cpu")
        diff = [k for k in SAME_INPUTS if (mk["args"].get(k) or None) != (args.get(k) or None)]
        assert not diff and (mk["n_stations"], mk.get("n_feat", 6), mk.get("n_future", 0)) == (ck["n_stations"], ck.get("n_feat", 6), ck.get("n_future", 0)), \
            f"{mf.name} was not trained with the same inputs as best.pt: {diff}"
        m_ = GlobalLSTM(mk["n_stations"], n_feat=mk.get("n_feat", 6), hidden=mk["args"]["hidden"], layers=mk["args"]["layers"], n_future=mk.get("n_future", 0),
                        delta_scale=delta_norm, init_state=mk["args"].get("init_state", False))
        m_.load_state_dict(mk["state_dict"]); m_.eval()
        assert not delta_norm or np.allclose(m_.rscale.numpy(), rscale), f"{mf.name}: other 6 h-change scale than best.pt"
        models.append(m_)
    st = pd.read_csv(run_dir / "stations.csv", dtype={"station_id": str})
    assert len(st) == ck["n_stations"], "stations.csv does not match the checkpoint"
    log.info("cycle %s UTC, model %s (%d stations, lookback %d h, wind=%s future_wind=%s discharge=%s rain=%s future_rain=%s fill=%s scaled_change=%s)",
             cycle, run_dir.name, len(st), lookback, use_wind, use_future, use_q, use_rain, use_future_rain, args.get("fill", "zero"), delta_norm)
    if member_files:
        log.info("forecast = mean of %d models (best.pt and %s)", len(models), ", ".join(f.name for f in member_files))

    index = pd.date_range(cycle - pd.Timedelta(hours=lookback - 1), cycle, freq="1h")
    future_index = pd.date_range(cycle + pd.Timedelta(hours=1), periods=HORIZON, freq="1h")
    long_index = pd.date_range(index[0] - pd.Timedelta(hours=FILL_EXTRA_H if ffill else 0), cycle, freq="1h")
    begin, end = long_index[0] - pd.Timedelta(hours=1), cycle + pd.Timedelta(minutes=59)
    manifest_extra: dict = {}

    series = fetch_levels(st, a.sources, begin, end, raw_dir)

    # ---- wind (HRRR) and discharge (USGS 00060) for all stations at once
    u_p = v_p = u_f = v_f = q = None
    wind_cov = None
    if use_wind:
        from hrrr_wind import station_wind
        cov = pd.read_csv(run_dir / "wind_coverage.csv", dtype={"station_id": str})
        assert (cov.station_id.to_numpy() == st.station_id.to_numpy()).all(), "wind_coverage.csv does not match stations.csv"
        wind_cov = cov.wind_valid_frac.to_numpy()
        # stations trained with the wind input switched off (config/stations_wind_hurts.csv at training time):
        # feed zeros and no wind mask, exactly as in training, and do not require wind for them
        wind_off = np.zeros(len(st), bool)
        nw = args.get("no_wind_stations")
        if nw:
            nwf = run_dir / "no_wind_stations.csv"
            if not nwf.exists():
                nwf = REPO / "config" / Path(nw).name
            sub = pd.read_csv(nwf, dtype=str)
            keyset = set(zip(sub.source, sub.station_id))
            wind_off = np.array([(s_, str(i_)) in keyset for s_, i_ in zip(st.source, st.station_id)])
            manifest_extra["wind_off_stations"] = int(wind_off.sum())
            log.info("wind input switched off at %d stations (%s)", wind_off.sum(), nwf.name)
        t = time.time()
        # now=cycle: the wind of the next 6 h comes from the HRRR cycle of the forecast hour or an earlier one, also when a past
        # forecast time is run later (without it such a run took the cycle issued one hour after the forecast time)
        u_p, v_p, u_f, v_f, prov = station_wind(st, index, future_index, Path(a.wind_cache) if a.wind_cache else Path(a.out) / "wind", now=cycle)
        manifest_extra["wind"] = {"source": "HRRR conus wrfsfc, 10 m UGRD/VGRD, nearest cell", "seconds": round(time.time() - t),
                                  "past_valid_frac": float(np.isfinite(u_p).mean()), "future_valid_frac": float(np.isfinite(u_f).mean()),
                                  "past_fhr_counts": pd.Series(list(prov["past"].values())).value_counts().to_dict() if prov["past"] else {},
                                  "future_fhr": prov["future"], "cells": prov["cells"]}
        log.info("wind: past valid %.3f, future valid %.3f, %d s", np.isfinite(u_p).mean(), np.isfinite(u_f).mean(), time.time() - t)
    if use_q:
        q, qinfo = fetch_discharge(st, run_dir, index, raw_dir)
        manifest_extra["discharge"] = qinfo
    rain_p = rain_f = None
    if use_rain:
        from hrrr_rain import box_cells, lag_of, station_rain
        t = time.time()
        rain_cache = Path(a.rain_cache) if a.rain_cache else Path(a.out) / "rain"
        past_km = 3 * box_cells(args.get("rain_var", "p15"))
        rain_p = np.full((len(st), len(index)), np.nan, np.float32); mprov = None
        if a.past_rain == "mrms":
            from mrms_rain import station_mrms
            rain_p, mprov = station_mrms(st, index, rain_cache, cells=past_km if past_km % 2 else past_km + 1)
        gap = ~np.isfinite(rain_p).any(0)          # hours with no MRMS file (all hours when --past-rain hrrr): HRRR 1 h lead
        hp, rain_f, rprov = station_rain(st, index[gap], cycle, rain_cache,
                                         past_cells=box_cells(args.get("rain_var", "p15")), future_cells=box_cells(args.get("rain_fc")),
                                         lag=lag_of(args.get("rain_fc")), want_future=use_future_rain)
        rain_p[:, gap] = hp
        manifest_extra["rain"] = {"source": "past: MRMS MultiSensor QPE 01H (gaps: HRRR APCP 1 h lead); next 6 h: HRRR APCP; box mean around the station",
                                  "past_product": a.past_rain, "mrms": mprov, "past_hours_from_hrrr": int(gap.sum()), "seconds": round(time.time() - t),
                                  "past_valid_frac": float(np.isfinite(rain_p).mean()), "future_available": rain_f is not None,
                                  "trained_with": {"past": f"AORC {args.get('rain_var', 'p15')}", "future": args.get("rain_fc"), "form": rain_form}, **rprov}
        log.info("rain: past valid %.3f (%d of %d hours from HRRR), future %s, %d s", np.isfinite(rain_p).mean(), gap.sum(), len(index),
                 rprov["future"] or "NOT AVAILABLE", time.time() - t)

    # ---- windows -> model
    tf = time_features(index)
    feats, futs, rows_idx, recs = [], [], [], []
    for i, r in st.iterrows():
        key = (r.source, r.station_id)
        rec = {"source": r.source, "station_id": r.station_id, "name": r["name"], "lat": r.lat, "lon": r.lon,
               "domains": r.domains, "datum": r.datum, "cycle_utc": cycle, "last_obs_utc": None, "last_obs_m": np.nan,
               **{f"fcst_{h}h_m": np.nan for h in range(1, HORIZON + 1)}, "input_valid_frac": 0.0,
               "wind_valid_frac": np.nan, "q_valid_frac": np.nan, "rain_valid_frac": np.nan, "rain_past72h_mm": np.nan, "rain_next6h_mm": np.nan,
               "status": ""}
        if r.source not in a.sources:
            rec["status"] = "no_realtime_source"; recs.append(rec); continue
        if key not in series:
            rec["status"] = "no_data_returned"; recs.append(rec); continue
        h_long = to_hourly(series[key]).reindex(long_index)
        h = h_long.reindex(index)
        valid = h.notna()
        rec["input_valid_frac"] = float(valid.mean())
        if valid.any():
            last_t = h.dropna().index[-1]
            rec["last_obs_utc"], rec["last_obs_m"] = last_t, float(h.dropna().iloc[-1])
        if valid.mean() < MIN_INPUT_VALID:
            rec["status"] = "insufficient_input"; recs.append(rec); continue
        if (cycle - rec["last_obs_utc"]) > pd.Timedelta(hours=MAX_STALE_H):
            rec["status"] = "stale"; recs.append(rec); continue
        if ffill:      # as in training (--fill ffill): a missing hour takes the last valid level; the mask channel still marks it
            h = h_long.ffill().reindex(index).bfill()
        x = np.nan_to_num((h.to_numpy(np.float32) - r.mean_m) / r.std_m)
        m = valid.to_numpy(np.float32)
        parts = [x[:, None], m[:, None], tf]
        fut = np.zeros(0, np.float32)
        if use_wind and wind_off[i]:                  # wind switched off for this station at training time
            L = len(index)
            parts += [np.zeros((L, 1), np.float32), np.zeros((L, 1), np.float32), np.zeros((L, 1), np.float32)]
            rec["wind_valid_frac"] = 0.0
            if use_future:
                fut = np.zeros(2 * HORIZON, np.float32)
        elif use_wind:
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
        if use_rain:   # log1p(mm/h) and its mask, then (head input) the next 6 h as hourly values or as one total
            rm = np.isfinite(rain_p[i])
            rec["rain_valid_frac"] = float(rm.mean())
            if rm.mean() < MIN_INPUT_VALID or (use_future_rain and (rain_f is None or not np.isfinite(rain_f[i]).all())):
                rec["status"] = "insufficient_rain"; recs.append(rec); continue
            mm = np.nan_to_num(np.clip(rain_p[i], 0, None))
            rec["rain_past72h_mm"] = float(mm.sum())
            parts += [np.log1p(mm)[:, None], rm.astype(np.float32)[:, None]]
            if use_future_rain:
                fm = np.clip(rain_f[i], 0, None)
                rec["rain_next6h_mm"] = float(fm.sum())
                fut = np.concatenate([fut, np.log1p(fm) if rain_form == "hourly" else np.log1p(fm.sum(keepdims=True))]).astype(np.float32)
        if delta_feat:   # level relative to the newest hour, in units of the station's typical 6 h change (last channel, as in training)
            parts.append(np.clip((x - x[-1]) / rscale[i], -20, 20)[:, None].astype(np.float32))
        feats.append(np.concatenate(parts, 1)); futs.append(fut)
        rows_idx.append(i); rec["status"] = "ok"; recs.append(rec)
    df = pd.DataFrame(recs)
    if feats:
        with torch.no_grad():
            f = torch.from_numpy(np.stack(feats).astype(np.float32)); fu = torch.from_numpy(np.stack(futs)) if ck.get("n_future", 0) else None
            sidx = torch.tensor(rows_idx, dtype=torch.long)
            each = np.stack([m_(f, sidx, fu).numpy() for m_ in models])        # [members, stations, leads]
        mean = st.loc[rows_idx, "mean_m"].to_numpy(); std = st.loc[rows_idx, "std_m"].to_numpy()
        each = each * std[None, :, None] + mean[None, :, None]
        pred = each.mean(0)
        for h in range(HORIZON):
            df.loc[rows_idx, f"fcst_{h+1}h_m"] = pred[:, h]
        if len(models) > 1:      # lowest and highest member: how far the models disagree (not the full forecast error)
            for h in range(HORIZON):
                df.loc[rows_idx, f"member_min_{h+1}h_m"] = each[:, :, h].min(0)
                df.loc[rows_idx, f"member_max_{h+1}h_m"] = each[:, :, h].max(0)
    df["valid_time_6h_utc"] = cycle + pd.Timedelta(hours=HORIZON)
    df.to_csv(out / "forecast.csv", index=False)
    manifest = {"cycle_utc": str(cycle), "model": str(run_dir), "members": ["best.pt"] + [f.name for f in member_files], "checkpoint_args": args, "lookback_h": lookback,
                "horizon_h": HORIZON, "n_feat": ck.get("n_feat", 6), "n_future": ck.get("n_future", 0),
                "n_stations": int(len(df)), "status_counts": df.status.value_counts().to_dict(),
                "sources": a.sources, **manifest_extra, "generated_utc": str(pd.Timestamp.now("UTC").tz_localize(None).floor("s"))}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    log.info("wrote %s: %s", out / "forecast.csv", manifest["status_counts"])


if __name__ == "__main__":
    main()
