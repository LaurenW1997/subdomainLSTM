"""Checks of common.despike_readings on constructed series.  Usage: python test_despike.py"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import despike_readings, to_hourly


def ser(values, step="15min", start="2026-11-17 10:00"):
    return pd.Series(np.asarray(values, float), index=pd.date_range(start, periods=len(values), freq=step))


def check(name, s, n_expected, kept=None):
    out, n = despike_readings(s)
    ok = n == n_expected and (kept is None or np.allclose(out.to_numpy(), kept))
    print(("ok   " if ok else "FAIL ") + f"{name}: removed {n}, expected {n_expected}")
    assert ok, name
    return out


def main() -> None:
    # the reading of USGS 02481510 on 17 November 2026
    wolf = ser([1.305, 1.308, 1.305, 8.281, 1.308, 1.305, 1.308], start="2026-11-17 10:30")
    out = check("one reading 7 m above its neighbours", wolf, 1, [1.305, 1.308, 1.305, 1.308, 1.305, 1.308])
    h_raw, h_new = to_hourly(wolf), to_hourly(out)
    print(f"     hourly value at 11:00: {h_raw['2026-11-17 11:00']:.3f} m with the reading, {h_new['2026-11-17 11:00']:.3f} m without")
    assert abs(h_new["2026-11-17 11:00"] - 1.3065) < 0.002

    check("one reading dropping to zero", ser([2.4, 2.41, 0.0, 2.42, 2.43]), 1)
    check("a rise that stays (step of 0.7 m)", ser([1.3, 1.3, 2.0, 2.0, 2.1, 2.1]), 0)
    check("a flood: 0.6 m per reading up, then slowly down", ser([1.0, 1.6, 2.2, 2.8, 2.7, 2.5, 2.2]), 0)
    check("a peak two readings wide", ser([1.0, 1.9, 1.9, 1.0, 1.0]), 0)
    check("spike in the newest reading (no reading after it)", ser([1.3, 1.3, 1.3, 8.3]), 0)
    check("spike in the first reading", ser([8.3, 1.3, 1.3, 1.3]), 0)
    check("a jump of 0.4 m and back (below the minimum)", ser([1.3, 1.7, 1.3, 1.3]), 0)
    check("up 1.0 m, back only 0.6 m: the level stays 0.4 m higher, so the neighbours do not agree", ser([1.0, 2.0, 1.4, 1.4]), 0)
    check("up 0.8 m, back 0.75 m: the neighbours agree within 5 cm", ser([1.0, 1.8, 1.05, 1.05]), 1)
    gap = pd.Series([1.3, 8.3, 1.3], index=pd.to_datetime(["2026-11-17 08:00", "2026-11-17 10:00", "2026-11-17 12:00"]))
    check("neighbours four hours apart", gap, 0)
    t = pd.date_range("2026-11-10", periods=24 * 10 * 5, freq="6min")
    tide = pd.Series(1.0 * np.sin(2 * np.pi * np.arange(len(t)) * 0.1 / 12.42) + 0.02 * np.random.default_rng(0).standard_normal(len(t)), index=t)
    check("five days of tide with a 2 m range and 2 cm noise", tide, 0)
    two = ser([1.3, 1.3, 8.3, 1.3, 1.3, 0.2, 1.3, 1.3])
    check("two separate spikes", two, 2)
    nan = ser([1.3, np.nan, 1.3, 8.3, 1.3, 1.3])
    check("a missing reading next to the spike", nan, 1)
    print("all checks passed")


if __name__ == "__main__":
    main()
