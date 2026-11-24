"""Francine case, atmospheric forcing, step 1: the HRRR fields the model needs, hour by hour.

The runs of Hurricane Ida were forced with the hourly HRRR analysis (file wrfsfcf00 of every hourly cycle): 2 m temperature and
specific humidity, surface pressure, 10 m wind, downward short- and long-wave radiation at the surface and precipitation rate.
The same fields are taken here for another period, from the public archive on AWS, each message by its byte range
(the .idx file), and cut to the box of the Louisiana grid. Nothing is interpolated or converted in this step.
Checked against the files the Ida run read (2021-08-29 17:00): seven fields are the analysis of the hour; the precipitation rate of
hour t is the one of the 1-hour forecast of the cycle that starts at t (--fields rain --fhour 1 --stamp-cycle), the analysis holds none.
Output: --out DIR/YYYYMMDDHH.npz (Tair K, Qair kg/kg, Pair Pa, Uwind and Vwind m/s along the HRRR grid, swrad and lwrad W/m2, rain kg/m2/s;
        float32 [rows, columns] of the box) and DIR/box.npz (lon, lat of the box, its first row and column on the HRRR grid, grid spacing)
Usage : python hrrr_fetch.py --start "2024-08-14 00:00" --end "2024-09-19 00:00" --out DIR [--workers 12]
        python hrrr_fetch.py --start ... --end ... --out DIR_RAIN --fields rain --fhour 1 --stamp-cycle
        An hour already there is skipped.
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pygrib
import pyproj
import requests

BASE = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"
ALL_FIELDS = {"Tair": ":TMP:2 m above ground:", "Qair": ":SPFH:2 m above ground:", "Pair": ":PRES:surface:", "Uwind": ":UGRD:10 m above ground:", "Vwind": ":VGRD:10 m above ground:",
          "swrad": ":DSWRF:surface:", "lwrad": ":DLWRF:surface:", "rain": ":PRATE:surface:"}
LCC = pyproj.Proj(proj="lcc", lat_1=38.5, lat_2=38.5, lat_0=38.5, lon_0=-97.5, a=6371229, b=6371229)
FIRST = (237.280472 - 360.0, 21.138123); DX = 3000.0; NYH, NXH = 1059, 1799
AREA = (-94.35, -88.15, 28.50, 31.40)                                       # lon west, east, lat south, north: the model grid and a margin


def box():
    x0, y0 = LCC(*FIRST); lo = np.linspace(AREA[0], AREA[1], 200); la = np.linspace(AREA[2], AREA[3], 200); LO, LA = np.meshgrid(lo, la); x, y = LCC(LO, LA)
    i = (x - x0) / DX; j = (y - y0) / DX
    return max(int(np.floor(j.min())) - 3, 0), min(int(np.ceil(j.max())) + 4, NYH), max(int(np.floor(i.min())) - 3, 0), min(int(np.ceil(i.max())) + 4, NXH)


def fetch(when: pd.Timestamp, fhour: int, out: Path, bx, sess: requests.Session, names=None, stamp_cycle: bool = False) -> str:
    cyc = when if stamp_cycle else when - pd.Timedelta(hours=fhour); target = out / f"{when:%Y%m%d%H}.npz"; FIELDS = {k: v for k, v in ALL_FIELDS.items() if not names or k in names}
    if target.exists():
        return "there"
    url = f"{BASE}/hrrr.{cyc:%Y%m%d}/conus/hrrr.t{cyc:%H}z.wrfsfcf{fhour:02d}.grib2"
    for attempt in range(4):
        try:
            idx = sess.get(url + ".idx", timeout=40)
            if idx.status_code != 200:
                raise IOError(f"idx {idx.status_code}")
            lines = idx.text.splitlines(); starts = [int(l.split(":")[1]) for l in lines]; o = {}
            for name, key in FIELDS.items():
                k = [n for n, l in enumerate(lines) if key in l]
                if len(k) != 1:
                    raise IOError(f"{name}: {len(k)} messages match")
                rng = f"bytes={starts[k[0]]}-{starts[k[0] + 1] - 1}" if k[0] + 1 < len(lines) else f"bytes={starts[k[0]]}-"
                r = sess.get(url, headers={"Range": rng}, timeout=120); r.raise_for_status(); v = pygrib.fromstring(r.content).values
                assert v.shape == (NYH, NXH), v.shape; o[name] = np.asarray(np.ma.filled(v, np.nan)[bx[0]:bx[1], bx[2]:bx[3]], np.float32)
            tmp = out / f"{when:%Y%m%d%H}.tmp.npz"; np.savez_compressed(tmp, **o); tmp.rename(target)
            return "ok"
        except Exception as e:                                             # noqa: BLE001
            err = str(e)[:120]; time.sleep(3 * (attempt + 1))
    return f"FAILED {err}"


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--fhour", type=int, default=0); ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--fields", nargs="*", help="only these of Tair Qair Pair Uwind Vwind swrad lwrad rain"); ap.add_argument("--stamp-cycle", action="store_true", help="the hour of a file is the start of its cycle, not its valid time"); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); bx = box(); hours = pd.date_range(a.start, a.end, freq="h")
    if not (out / "box.npz").exists():
        r = requests.get(f"{BASE}/hrrr.{hours[0]:%Y%m%d}/conus/hrrr.t{hours[0]:%H}z.wrfsfcf00.grib2.idx", timeout=40); lines = r.text.splitlines(); k = [n for n, l in enumerate(lines) if ALL_FIELDS["Tair"] in l][0]
        st = [int(l.split(":")[1]) for l in lines]; m = pygrib.fromstring(requests.get(f"{BASE}/hrrr.{hours[0]:%Y%m%d}/conus/hrrr.t{hours[0]:%H}z.wrfsfcf00.grib2", headers={"Range": f"bytes={st[k]}-{st[k + 1] - 1}"}, timeout=120).content)
        la, lo = m.latlons(); lo = np.where(lo > 180, lo - 360, lo)
        assert abs(la[0, 0] - FIRST[1]) < 1e-3 and abs(lo[0, 0] - FIRST[0]) < 1e-3, "the first grid point is not the south-west corner"
        np.savez(out / "box.npz", lon=lo[bx[0]:bx[1], bx[2]:bx[3]], lat=la[bx[0]:bx[1], bx[2]:bx[3]], first_row=bx[0], first_col=bx[2], dx=DX, first_point_lon=FIRST[0], first_point_lat=FIRST[1])
    print(f"{len(hours)} hours {hours[0]} .. {hours[-1]}; box rows {bx[0]}-{bx[1]} columns {bx[2]}-{bx[3]} of the HRRR grid", flush=True)
    sess = requests.Session(); t0 = time.time(); bad = []
    with ThreadPoolExecutor(a.workers) as pool:
        for n, (when, res) in enumerate(zip(hours, pool.map(lambda w: fetch(w, a.fhour, out, bx, sess, a.fields, a.stamp_cycle), hours))):
            if res.startswith("FAILED"):
                bad.append(when); print(when, res, flush=True)
            if n % 48 == 0:
                print(f"  {when}  {res}  ({time.time() - t0:.0f} s)", flush=True)
    print(f"done: {len(hours) - len(bad)} of {len(hours)} hours in {out}; failed: {[str(b) for b in bad][:20]}", flush=True)


if __name__ == "__main__":
    main()
