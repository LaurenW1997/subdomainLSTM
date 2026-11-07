"""Shared helpers for the station census."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "census" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# Common output schema for every source
COLUMNS = [
    "source", "station_id", "name", "lat", "lon", "state",
    "site_type", "parameter", "datum", "units", "interval_min",
    "record_start", "record_end", "active", "domains", "extra",
]


def load_domains() -> dict[str, dict]:
    d = json.loads((CONFIG / "domains.json").read_text())
    return {k: v for k, v in d.items() if not k.startswith("_")}


def union_bbox(domains: dict[str, dict]) -> tuple[float, float, float, float]:
    return (
        min(v["lon_min"] for v in domains.values()),
        min(v["lat_min"] for v in domains.values()),
        max(v["lon_max"] for v in domains.values()),
        max(v["lat_max"] for v in domains.values()),
    )


def tag_domains(lat: float, lon: float, domains: dict[str, dict]) -> str:
    hits = [
        k for k, b in domains.items()
        if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]
    ]
    return ";".join(hits)


def finalize(df: pd.DataFrame, domains: dict[str, dict]) -> pd.DataFrame:
    df = df.copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    df["domains"] = [tag_domains(a, o, domains) for a, o in zip(df["lat"], df["lon"])]
    df = df[df["domains"] != ""]
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS].reset_index(drop=True)
