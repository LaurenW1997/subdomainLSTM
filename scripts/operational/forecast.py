"""Operational skeleton: pull the last 72 h of observations from the live USGS / NOAA
APIs, run the trained global LSTM, write 1-6 h water-level forecasts for every station.

Only sources with a real-time feed are forecast (USGS NWIS IV, NOAA CO-OPS). CRMS and
USACE stations in the model are listed in the output with status "no_realtime_source".

Output: <out>/<cycle>/forecast.csv, manifest.json, raw/ (verbatim API payloads).
  forecast.csv columns: source, station_id, name, lat, lon, domains, datum, cycle_utc,
  last_obs_utc, last_obs_m, fcst_1h_m .. fcst_6h_m, input_valid_frac, status
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

HORIZON = 6
MIN_INPUT_VALID = 0.7
MAX_STALE_H = 3
USGS_URL = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_PAUSE = 0.6


# ----------------------------------------------------------------------------- live data
def fetch_usgs(sites: list[str], begin: pd.Timestamp, end: pd.Timestamp, raw_dir: Path) -> dict[str, pd.Series]:
    """Gauge height (00065) in feet for many sites per call."""
    out: dict[str, pd.Series] = {}
    for i in range(0, len(sites), 80):
        chunk = sites[i:i + 80]
        r = get(USGS_URL, {"format": "json", "sites": ",".join(chunk), "parameterCd": "00065",
                           "startDT": begin.strftime("%Y-%m-%dT%H:%MZ"), "endDT": end.strftime("%Y-%m-%dT%H:%MZ"),
                           "siteStatus": "all"})
        (raw_dir / f"usgs_{i // 80:02d}.json").write_text(r.text, encoding="utf-8")
        if r.status_code != 200:
            log.error("USGS chunk %d: HTTP %s", i // 80, r.status_code); continue
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
    a = ap.parse_args()

    cycle = pd.Timestamp(a.cycle) if a.cycle else pd.Timestamp.now("UTC").tz_localize(None).floor("h") - pd.Timedelta(hours=1)
    run_dir = Path(a.model)
    out = Path(a.out) / cycle.strftime("%Y%m%dT%H"); raw_dir = out / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)
    ck = torch.load(run_dir / "best.pt", map_location="cpu")
    lookback = int(ck["args"].get("lookback", 72))
    model = GlobalLSTM(ck["n_stations"], hidden=ck["args"]["hidden"], layers=ck["args"]["layers"])
    model.load_state_dict(ck["state_dict"]); model.eval()
    st = pd.read_csv(run_dir / "stations.csv", dtype={"station_id": str})
    assert len(st) == ck["n_stations"], "stations.csv does not match the checkpoint"
    log.info("cycle %s UTC, model %s (%d stations, lookback %d h)", cycle, run_dir.name, len(st), lookback)

    index = pd.date_range(cycle - pd.Timedelta(hours=lookback - 1), cycle, freq="1h")
    begin, end = index[0] - pd.Timedelta(hours=1), cycle + pd.Timedelta(minutes=59)
    series: dict[tuple[str, str], pd.Series] = {}

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

    # ---- windows -> model
    tf = time_features(index)
    feats, rows_idx, recs = [], [], []
    for i, r in st.iterrows():
        key = (r.source, r.station_id)
        rec = {"source": r.source, "station_id": r.station_id, "name": r["name"], "lat": r.lat, "lon": r.lon,
               "domains": r.domains, "datum": r.datum, "cycle_utc": cycle, "last_obs_utc": None, "last_obs_m": np.nan,
               **{f"fcst_{h}h_m": np.nan for h in range(1, HORIZON + 1)}, "input_valid_frac": 0.0, "status": ""}
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
        feats.append(np.concatenate([np.nan_to_num(x)[:, None], m[:, None], tf], 1))
        rows_idx.append(i); rec["status"] = "ok"; recs.append(rec)
    df = pd.DataFrame(recs)
    if feats:
        with torch.no_grad():
            pred = model(torch.from_numpy(np.stack(feats)), torch.tensor(rows_idx, dtype=torch.long)).numpy()
        mean = st.loc[rows_idx, "mean_m"].to_numpy(); std = st.loc[rows_idx, "std_m"].to_numpy()
        pred = pred * std[:, None] + mean[:, None]
        for h in range(HORIZON):
            df.loc[rows_idx, f"fcst_{h+1}h_m"] = pred[:, h]
    df["valid_time_6h_utc"] = cycle + pd.Timedelta(hours=HORIZON)
    df.to_csv(out / "forecast.csv", index=False)
    manifest = {"cycle_utc": str(cycle), "model": str(run_dir), "checkpoint_args": ck["args"], "lookback_h": lookback,
                "horizon_h": HORIZON, "n_stations": int(len(df)), "status_counts": df.status.value_counts().to_dict(),
                "sources": a.sources, "generated_utc": str(pd.Timestamp.now("UTC").tz_localize(None).floor("s"))}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    log.info("wrote %s: %s", out / "forecast.csv", manifest["status_counts"])


if __name__ == "__main__":
    main()
