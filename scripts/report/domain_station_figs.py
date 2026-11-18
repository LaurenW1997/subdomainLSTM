"""Station figures of the runs on a schedule: five fixed stations in each of the three 100 m domains, both models.

Drawn every time results of the runs on a schedule are reported. The stations are fixed so that the figures of different
days can be compared: they are the representative stations of deliverable 10 (chosen per domain and type), limited to
stations with real-time data inside the operational grid of the domain.
Style of partner_live_fig.py: observed level and continuous lines for 1, 3 and 6 h lead (a forecast from every hour, from
operational/hourly_fill.sh on sv7), the version that is run on the left, the version with partner stations on the right.
Input : deliverables/33_partner_live_test/hourly_fc_schedule.csv  (extract_hourly_test.py on sv7 with --stations of ALL below)
Output: deliverables/33_partner_live_test/domain_<domain>_1.png        five stations, one figure per domain
        deliverables/33_partner_live_test/domain_<domain>_slide_<n>.png  three and two stations, for slides
Usage : python domain_station_figs.py            (prints the station ids with --ids)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
T = HERE.parents[1] / "deliverables" / "33_partner_live_test"
DOMAINS = {
    "Louisiana100m": ["8761724", "8761927", "8747437", "07387050", "07381590"],    # Grand Isle, New Canal, Bay Waveland, Vermilion Bay, Wax Lake Outlet
    "Galveston100m": ["8771450", "8770613", "08072050", "08114000", "08068310"],   # Galveston Pier 21, Morgans Point, San Jacinto Rv nr Sheldon, Brazos Rv at Richmond, Spring Ck
    "Texas100m": ["8774770", "8773259", "08188810", "08211500", "08176500"],       # Rockport, Port Lavaca, Guadalupe Rv nr Tivoli, Nueces Rv at Calallen, Guadalupe Rv at Victoria
}
ALL = [s for v in DOMAINS.values() for s in v]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--ids", action="store_true", help="print the station ids and stop"); ap.add_argument("--src", default=str(T / "hourly_fc_schedule.csv"))
    a = ap.parse_args()
    if a.ids:
        print(" ".join(ALL)); return
    d = pd.read_csv(a.src, dtype={"station_id": str}); d["valid"] = pd.to_datetime(d.valid, format="mixed")
    d = d.dropna(subset=["obs"])
    b = d.valid.min()                                        # the hours that have a forecast and an observation;
    e = min(d.valid.max(), pd.to_datetime(d.origin, format="mixed").max())    # the hour after the newest forecast time has only part of its readings
    span = f"{b:%d %B %H} UTC to {e:%d %B %H} UTC {e:%Y}".replace(" 0", " ").lstrip("0")
    fmt = "%Y-%m-%dT%H"
    for dom, ids in DOMAINS.items():
        have = [s for s in ids if (d.station_id == s).any()]
        if len(have) < len(ids):
            print(f"{dom}: no forecast for {sorted(set(ids) - set(have))}")
        for extra in ([], ["--per-figure", "3"]):
            prefix = f"domain_{dom}" + ("_slide" if extra else "")
            cmd = [sys.executable, str(HERE / "partner_live_fig.py"), "--period", f"{dom}:  {span}", a.src, b.strftime(fmt), e.strftime(fmt), "--stations", *have,
                   "--per-figure", "5", "--prefix", prefix] if not extra else \
                  [sys.executable, str(HERE / "partner_live_fig.py"), "--period", f"{dom}:  {span}", a.src, b.strftime(fmt), e.strftime(fmt), "--stations", *have, *extra, "--prefix", prefix]
            subprocess.run(cmd, check=True, cwd=str(HERE))


if __name__ == "__main__":
    main()
