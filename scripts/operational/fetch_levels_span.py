"""Water levels of every real-time station for a whole period in one fetch, for tests on many past forecast times.

forecast.py --levels-all FILE then takes, for each forecast time, only the readings up to that time (cycle + 59 min);
the same file gives the observations the forecasts are compared with afterwards.
Output: --out (pickle: {(source, station_id): readings in metres on the station's datum})
Usage : python fetch_levels_span.py --model RUN_DIR --begin 2026-11-10T18 --end 2026-11-17T13 --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forecast import fetch_levels  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--begin", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    st = pd.read_csv(Path(a.model) / "stations.csv", dtype={"station_id": str})
    out = Path(a.out); raw = out.parent / (out.stem + "_raw"); raw.mkdir(parents=True, exist_ok=True)
    series = fetch_levels(st, ["USGS", "NOAA_COOPS"], pd.Timestamp(a.begin), pd.Timestamp(a.end), raw)
    pd.to_pickle(series, out)
    print(f"{len(series)} stations, readings from {min(s.index.min() for s in series.values())} to {max(s.index.max() for s in series.values())} -> {out}")


if __name__ == "__main__":
    main()
