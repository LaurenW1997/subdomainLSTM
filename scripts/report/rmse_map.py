"""deliverable 02: map of per-station 6 h RMSE (runs locally, needs cartopy).

Usage: python rmse_map.py --per-station deliverables/02_per_station_test.csv --out deliverables/02_rmse_map.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cf

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-station", default=str(REPO / "deliverables" / "02_per_station_test.csv"))
    ap.add_argument("--out", default=str(REPO / "deliverables" / "02_rmse_map.png"))
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
    bounds = [0, 2, 4, 6, 8, 10, 15, 20, 30, 50]
    norm = BoundaryNorm(bounds, 256)
    sc = ax.scatter(d.lon, d.lat, c=d.rmse_6h_cm.clip(0, 50), s=9, cmap="viridis_r", norm=norm,
                    edgecolor="none", transform=ccrs.PlateCarree(), zorder=5)
    cb = plt.colorbar(sc, ax=ax, shrink=.75, pad=.02, ticks=bounds)
    cb.set_label("6 h RMSE, test 2024–26 (cm)")
    gl = ax.gridlines(draw_labels=True, lw=.3, alpha=.5); gl.top_labels = gl.right_labels = False
    ax.set_title(f"{len(d)} stations; median 6 h RMSE {d.rmse_6h_cm.median():.1f} cm; "
                 f"{(d.rmse_6h_cm < 5).mean()*100:.0f}% below 5 cm, {(d.rmse_6h_cm < 10).mean()*100:.0f}% below 10 cm")
    fig.tight_layout(); fig.savefig(a.out, dpi=150)
    print("saved", a.out)


if __name__ == "__main__":
    main()
