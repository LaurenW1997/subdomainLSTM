"""Francine case, open boundary: the constant to add to the HYCOM free surface so that the boundary keeps the level convention of the Ida run.

The boundary of the Ida run (from a 1 km model of the Gulf) has its own zero: at the gauges the model stands about 0.4 m below the
observed level (NAVD88). The runs of Francine must keep that, or the two sets of runs cannot be used together. Rule:
    mean boundary level of Francine, calm weeks before the storm
        = mean boundary level of Ida, calm weeks before the storm
        + how much higher the sea observed at the coastal gauges stood in the calm weeks of 2024 than in those of 2021
so the boundary sits as far below the real sea in the Francine run as it did in the Ida run. One constant for all three edges.
Input : --hycom DIR (ssh_*.nc), --edges NPZ (edge coordinates and the calm mean of the Ida boundary), --gauges CSV (station, difference_m, valid_2021, valid_2024)
Output: printed, and --out TXT
Usage : python level_shift.py --hycom DIR --edges FILE --gauges FILE --out FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_boundary_hycom import EDGES, apply, bilinear, load, nearest_fill_index  # noqa: E402

CALM = ("2024-08-14 00:00", "2024-09-07 00:00")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--hycom", required=True); ap.add_argument("--edges", required=True); ap.add_argument("--gauges", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
    E = np.load(a.edges); g = pd.read_csv(a.gauges); g = g[(g.valid_2021 > 0.9) & (g.valid_2024 > 0.9)]; rise = float(g.difference_m.median())
    ssh, ts, lat, lon, _ = load(a.hycom, "ssh", "surf_el"); fi = nearest_fill_index(np.isfinite(ssh).mean(0) > 0.5, lat, lon); ssh = ssh.reshape(len(ssh), -1)[:, fi.ravel()].reshape(ssh.shape)
    calm = np.asarray((ts >= CALM[0]) & (ts < CALM[1])); L = [f"calm weeks of Francine: {CALM[0]} .. {CALM[1]} ({int(calm.sum())} hours of HYCOM); of Ida: 2021-08-01 .. 2021-08-25",
                                                             f"observed sea level, 2024 minus 2021, at {len(g)} coastal gauges: median {rise:+.3f} m (quartiles {g.difference_m.quantile(0.25):+.3f} .. {g.difference_m.quantile(0.75):+.3f})"]
    n = 0; s_ida = 0.0; s_hy = 0.0
    for e in EDGES:
        m = E[f"mask_rho_{e}"] > 0.5; w = bilinear(lat, lon, E[f"lat_rho_{e}"], E[f"lon_rho_{e}"]); z = apply(ssh[calm], w).mean(0); ida = E[f"ida_zeta_mean_calm_{e}"]
        L.append(f"  {e}: {int(m.sum())} ocean points; Ida boundary {ida[m].mean():+.3f} m, HYCOM {z[m].mean():+.3f} m (along the edge {z[m].min():+.3f} .. {z[m].max():+.3f})"); n += int(m.sum()); s_ida += float(ida[m].sum()); s_hy += float(z[m].sum())
    ida_mean, hy_mean = s_ida / n, s_hy / n; target = ida_mean + rise; shift = target - hy_mean
    L += [f"all edges: Ida boundary {ida_mean:+.3f} m; target for Francine {ida_mean:+.3f} {rise:+.3f} = {target:+.3f} m; HYCOM as it is {hy_mean:+.3f} m", f"shift to add to the HYCOM free surface: {shift:+.3f} m"]
    Path(a.out).write_text(chr(10).join(L), encoding="utf-8"); print(chr(10).join(L))


if __name__ == "__main__":
    main()
