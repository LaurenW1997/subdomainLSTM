"""deliverable 10: representative stations per domain and type - map, error-range comparison, summary table.

Inputs (deliverables/10_representative/):
  stations.csv                      the chosen stations (domain, type, source, station_id, name, lat, lon, r6_obs, r6_v4, hurricane)
  {la,gal,tx}_windows.csv           per-window 1-6 h RMSE from event_plots.py --hurricane (copied from sv7)
Outputs (same folder):
  map.png                           all chosen stations, colour = type, label = short name, domain boxes
  range_<domain>.png                per station: 6 h RMSE full year (with and without wind + discharge) and in the hurricane / high-water / normal windows
  summary.csv / summary.md          one row per station
Usage: python representative.py [--map-only]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "10_representative"
plt.rcParams["font.family"] = "Times New Roman"
TYPES = ["tide gauge", "marsh", "estuary / tidal channel", "river / canal", "urban creek (Houston)"]
TCOL = {"tide gauge": "#1f4e79", "marsh": "#2e7d32", "estuary / tidal channel": "#8e24aa", "river / canal": "#b26a00", "urban creek (Houston)": "#c62828"}
DOMS = {"Louisiana100m": (-94.11, -88.39, 28.74, 31.14), "Texas100m": (-99.03, -95.24, 25.85, 29.13), "Galveston100m": (-96.71, -94.04, 28.74, 31.16)}
SHORT = {"8761724": "Grand Isle", "8761927": "New Canal", "8747437": "Bay Waveland", "CRMS0367-H01": "CRMS0367", "CRMS0517-H01": "CRMS0517",
         "07387050": "Vermilion Bay", "301429089145600": "Merrill Shell Bank", "07381590": "Wax Lake Outlet", "07374000": "Mississippi R. Baton Rouge",
         "07379050": "Ward Creek", "8771450": "Galveston Pier 21", "8770613": "Morgans Point", "08072050": "San Jacinto R. Sheldon",
         "08074000": "Buffalo Bayou Houston", "08114000": "Brazos R. Richmond", "08066250": "Trinity R. Goodrich", "08068310": "Spring Creek",
         "08074500": "Whiteoak Bayou", "8774770": "Rockport", "8773259": "Port Lavaca", "08188810": "Guadalupe R. Tivoli", "08211500": "Nueces R. Calallen",
         "08176500": "Guadalupe R. Victoria"}
WIN = {"hurricane": "hurricane", "high water": "high water", "normal": "normal"}


def short(sid: str, name: str) -> str:
    return SHORT.get(sid, name[:22])


def make_map(st: pd.DataFrame) -> None:
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    fig = plt.figure(figsize=(13, 5.6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([-99.3, -88.0, 25.6, 31.4])
    ax.add_feature(cf.LAND, facecolor="#f4f4f4"); ax.add_feature(cf.OCEAN, facecolor="#ffffff")
    ax.add_feature(cf.COASTLINE, lw=.6); ax.add_feature(cf.STATES, lw=.4, edgecolor="#777777")
    ax.add_feature(cf.RIVERS, lw=.4, edgecolor="#9ecae1")
    for dom, (x0, x1, y0, y1) in DOMS.items():
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="k", lw=.8, ls="--", transform=ccrs.PlateCarree())
        ax.text(x0 + .08, y1 - .12, dom, fontsize=10, va="top", transform=ccrs.PlateCarree())
    for t in TYPES:
        s = st[st.type == t]
        ax.scatter(s.lon, s.lat, s=46, c=TCOL[t], edgecolor="k", lw=.5, label=f"{t} ({len(s)})", transform=ccrs.PlateCarree(), zorder=5)
    # labels with small manual nudges to avoid overlap
    nudge = {"8761927": (0.1, 0.1), "8747437": (0.1, -0.22), "07374000": (0.12, 0.16), "07379050": (0.12, -0.22), "CRMS0517-H01": (-0.12, 0.16),
             "07387050": (0.1, -0.26), "07381590": (0.08, 0.1), "8771450": (0.12, -0.24), "8770613": (0.12, -0.22), "08072050": (0.12, 0.12),
             "08074000": (-0.12, -0.26), "08074500": (-0.12, 0.16), "08068310": (0.1, 0.08), "08114000": (-0.12, -0.26), "08066250": (0.1, 0.08),
             "8774770": (0.12, -0.22), "8773259": (0.12, -0.2), "08188810": (-0.1, -0.24), "08211500": (-0.12, 0.14), "08176500": (0.12, 0.14),
             "8761724": (0.1, -0.2), "CRMS0367-H01": (0.1, 0.1), "301429089145600": (-0.1, 0.16)}
    for _, r in st.iterrows():
        dx, dy = nudge.get(r.station_id, (0.1, 0.08))
        ax.text(r.lon + dx, r.lat + dy, short(r.station_id, r["name"]), fontsize=7.5, ha="left" if dx > 0 else "right", transform=ccrs.PlateCarree(), zorder=6)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False)
    ax.set_title(f"{len(st)} representative stations", fontsize=11)
    fig.tight_layout(); fig.savefig(D / "map.png", dpi=170); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--map-only", action="store_true"); a = ap.parse_args()
    st = pd.read_csv(D / "stations.csv", dtype={"station_id": str})
    make_map(st)
    print("map ->", D / "map.png")
    if a.map_only:
        return
    w = pd.concat([pd.read_csv(f, dtype={"station_id": str}) for f in sorted(D.glob("*_windows.csv"))], ignore_index=True)
    w["win"] = w.window.str.extract(r"^(hurricane|high water|normal)")[0]
    piv = w.pivot_table(index="station_id", columns="win", values=["rmse_1h_cm", "rmse_3h_cm", "rmse_6h_cm"])
    piv.columns = [f"{c[1]}_{c[0].split('_')[1]}" for c in piv.columns]
    dates = w[w.win == "hurricane"].set_index("station_id").start.str[:10].rename("hurricane_start")
    hw = w[w.win == "high water"].set_index("station_id").start.str[:10].rename("high_water_start")
    nm = w[w.win == "normal"].set_index("station_id").start.str[:10].rename("normal_start")
    s = st.merge(piv, left_on="station_id", right_index=True, how="left").merge(dates, left_on="station_id", right_index=True, how="left") \
          .merge(hw, left_on="station_id", right_index=True, how="left").merge(nm, left_on="station_id", right_index=True, how="left")
    s["short"] = [short(i, n) for i, n in zip(s.station_id, s["name"])]
    s.to_csv(D / "summary.csv", index=False)
    cols = ["domain", "type", "short", "r1_new", "r3_new", "r6_new", "r6_obs", "hurricane_6h", "high water_6h", "normal_6h", "hurricane_start", "high_water_start", "normal_start"]
    md = s[cols].copy(); md.columns = ["domain", "type", "station", "year 1 h", "year 3 h", "year 6 h", "water-level-only 6 h", "hurricane 6 h", "high water 6 h", "normal 6 h", "hurricane window", "high-water window", "normal window"]
    lines = ["# Representative stations: 6 h RMSE (cm) of the LSTM with water level + wind + upstream discharge", "",
             "year = whole test period 2024-01 to 2025-12; hurricane / high water / normal = 4-day windows (all forecast origins in the window). water-level-only = the same LSTM trained on water level alone (no wind, no discharge), whole test period.", "",
             "| " + " | ".join(md.columns) + " |", "|" + "---|" * len(md.columns)]
    for _, r in md.iterrows():
        lines.append("| " + " | ".join(f"{v:.1f}" if isinstance(v, float) else str(v) for v in r.values) + " |")
    (D / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    # error-range comparison per domain
    for dom, g in s.groupby("domain", sort=False):
        g = g.sort_values(["type", "r6_new"])
        fig, ax = plt.subplots(figsize=(11, 0.55 * len(g) + 2.3))
        y = np.arange(len(g))
        ax.barh(y + 0.3, g.r6_obs, 0.18, color="#bbbbbb", label="whole year — water level only")
        ax.barh(y + 0.1, g.r6_new, 0.18, color="#222222", label="whole year — water level + wind + upstream discharge")
        ax.barh(y - 0.1, g["high water_6h"], 0.18, color="#7a7a7a", label="high-water window — with wind + discharge")
        ax.barh(y - 0.3, g["hurricane_6h"], 0.18, color="#ffffff", edgecolor="#222222", hatch="///", label="hurricane window — with wind + discharge")
        ax.scatter(g["normal_6h"], y, marker="|", s=120, color="k", zorder=5, label="normal window — with wind + discharge")
        ax.set_yticks(y); ax.set_yticklabels([f"{r.short}  ({r.type})" for _, r in g.iterrows()], fontsize=9)
        ax.invert_yaxis(); ax.set_xlabel("6 h RMSE (cm), log scale"); ax.set_xscale("log")
        ax.set_xticks([1, 2, 5, 10, 20, 50, 100]); ax.set_xticklabels(["1", "2", "5", "10", "20", "50", "100"])
        ax.grid(axis="x", alpha=.3, which="both"); ax.set_title(dom, fontsize=11, loc="left")
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.legend(fontsize=9, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
        fig.tight_layout(); fig.savefig(D / f"range_{dom}.png", dpi=170); plt.close(fig)
    print(s[["domain", "short", "r6_new", "hurricane_6h", "high water_6h", "normal_6h"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
