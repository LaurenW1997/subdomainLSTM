"""deliverable 02: map of per-station 6 h skill vs persistence (runs locally, needs cartopy).

Usage: python skill_map.py --per-station deliverables/02_per_station_test.csv --out deliverables/02_skill_map.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cf

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-station", default=str(REPO / "deliverables" / "02_per_station_test.csv"))
    ap.add_argument("--out", default=str(REPO / "deliverables" / "02_skill_map.png"))
    a = ap.parse_args()
    d = pd.read_csv(a.per_station)
    doms = json.loads((REPO / "config" / "domains.json").read_text())
    fig = plt.figure(figsize=(14, 6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([-99.3, -88.2, 25.6, 31.4])
    ax.add_feature(cf.LAND, facecolor="0.93"); ax.add_feature(cf.OCEAN, facecolor="0.98")
    ax.add_feature(cf.COASTLINE, lw=.6); ax.add_feature(cf.STATES, lw=.4); ax.add_feature(cf.RIVERS, lw=.3, alpha=.5)
    for name, b in doms.items():
        if not isinstance(b, dict):
            continue
        lon0, lon1, lat0, lat1 = b["lon_min"], b["lon_max"], b["lat_min"], b["lat_max"]
        ax.plot([lon0, lon1, lon1, lon0, lon0], [lat0, lat0, lat1, lat1, lat0], "k", lw=.8, ls="--", transform=ccrs.PlateCarree())
        ax.text(lon0 + 0.05, lat1 - 0.15, name, fontsize=8, transform=ccrs.PlateCarree())
    sc = ax.scatter(d.lon, d.lat, c=d.skill_6h.clip(-0.5, 1), s=9, cmap="RdYlGn", vmin=-0.5, vmax=1,
                    edgecolor="none", transform=ccrs.PlateCarree(), zorder=5)
    cb = plt.colorbar(sc, ax=ax, shrink=.75, pad=.02)
    cb.set_label("6 h skill = 1 − RMSE(LSTM) / RMSE(persistence), test 2024–26")
    gl = ax.gridlines(draw_labels=True, lw=.3, alpha=.5); gl.top_labels = gl.right_labels = False
    ax.set_title(f"{len(d)} stations; {(d.skill_6h > 0).mean()*100:.0f}% better than persistence; median skill {d.skill_6h.median():.2f}")
    fig.tight_layout(); fig.savefig(a.out, dpi=150)
    print("saved", a.out)


if __name__ == "__main__":
    main()
