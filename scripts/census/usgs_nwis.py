"""USGS NWIS instantaneous-value sites with gage height (00065) in the domain bboxes.

Uses the legacy site service with seriesCatalogOutput so each row carries the
period of record and sample count for the 00065 'iv' series.
"""
from __future__ import annotations

import io
import sys

import pandas as pd
import requests

from common import RAW, finalize, load_domains

URL = "https://waterservices.usgs.gov/nwis/site/"
PARAM = "00065"


def fetch_bbox(bbox: tuple[float, float, float, float], status: str) -> pd.DataFrame:
    params = {
        "format": "rdb",
        "bBox": ",".join(f"{v:.4f}" for v in bbox),
        "parameterCd": PARAM,
        "siteStatus": status,
        "outputDataTypeCd": "iv",
        "seriesCatalogOutput": "true",  # cannot be combined with siteOutput=expanded
    }
    r = requests.get(URL, params=params, timeout=120)
    if r.status_code == 404:  # no sites
        return pd.DataFrame()
    r.raise_for_status()
    lines = [l for l in r.text.splitlines() if not l.startswith("#")]
    # second line is the rdb type row
    text = "\n".join([lines[0]] + lines[2:])
    return pd.read_csv(io.StringIO(text), sep="\t", dtype=str)


def fetch_expanded(bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """Site metadata (state, county, site type, altitude) for all 00065 sites in bbox."""
    params = {
        "format": "rdb",
        "bBox": ",".join(f"{v:.4f}" for v in bbox),
        "parameterCd": PARAM,
        "siteStatus": "all",
        "hasDataTypeCd": "iv",
        "siteOutput": "expanded",
    }
    r = requests.get(URL, params=params, timeout=120)
    if r.status_code == 404:
        return pd.DataFrame()
    r.raise_for_status()
    lines = [l for l in r.text.splitlines() if not l.startswith("#")]
    return pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[2:])), sep="\t", dtype=str)


def main() -> None:
    domains = load_domains()
    frames = []
    meta = pd.concat(
        [fetch_expanded((b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"])) for b in domains.values()],
        ignore_index=True,
    ).drop_duplicates("site_no").set_index("site_no")
    meta.to_csv(RAW / "usgs_nwis_sites_expanded.csv")
    for name, b in domains.items():
        bbox = (b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"])
        for status in ("active", "inactive"):
            df = fetch_bbox(bbox, status)
            if df.empty:
                continue
            df["query_domain"] = name
            df["query_status"] = status
            frames.append(df)
            print(f"{name:14s} {status:8s} rows={len(df)}", file=sys.stderr)
    raw = pd.concat(frames, ignore_index=True)
    raw.to_csv(RAW / "usgs_nwis_series_catalog.csv", index=False)

    # keep only the 00065 instantaneous series
    sel = raw[(raw["parm_cd"] == PARAM) & (raw["data_type_cd"].isin(["iv", "uv"]))].copy()
    sel = sel.drop_duplicates(subset=["site_no", "data_type_cd", "parm_cd", "begin_date", "end_date"])
    # one row per site: earliest begin, latest end, summed count
    g = sel.groupby("site_no")
    out = pd.DataFrame({
        "source": "USGS",
        "station_id": g["site_no"].first(),
        "name": g["station_nm"].first(),
        "lat": g["dec_lat_va"].first(),
        "lon": g["dec_long_va"].first(),
        "state": g["site_no"].first().map(meta["state_cd"]).fillna(""),
        "site_type": g["site_tp_cd"].first(),
        "parameter": "gage_height",
        "datum": g["alt_datum_cd"].first().fillna(""),
        "units": "ft",
        "interval_min": "",
        "record_start": g["begin_date"].min(),
        "record_end": g["end_date"].max(),
        "active": g["query_status"].agg(lambda s: "active" in set(s)),
        "extra": g["agency_cd"].first() + "|huc=" + g["huc_cd"].first().fillna("")
                 + "|county=" + g["site_no"].first().map(meta["county_cd"]).fillna("")
                 + "|alt_ft=" + g["site_no"].first().map(meta["alt_va"]).fillna("")
                 + "|n=" + g["count_nu"].apply(lambda s: int(pd.to_numeric(s, errors="coerce").fillna(0).sum())).astype(str),
    }).reset_index(drop=True)
    out = finalize(out, domains)
    out.to_csv(RAW / "usgs_nwis.csv", index=False)
    print(f"USGS: {len(out)} sites with 00065 iv in domains ({out['active'].sum()} active)", file=sys.stderr)


if __name__ == "__main__":
    main()
