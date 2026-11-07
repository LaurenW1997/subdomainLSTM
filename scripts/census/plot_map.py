"""Map of the station census over the three domain boxes."""
from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import pandas as pd

from common import CONFIG, ROOT, load_domains

COLORS = {"USGS": "#1f77b4", "NOAA_COOPS": "#d62728", "USACE_MVN": "#2ca02c", "USACE_SWG": "#2ca02c",
          "USACE_MVK": "#2ca02c", "USACE_SWF": "#2ca02c", "TCOON": "#ff7f0e", "CRMS": "#9467bd"}


def main() -> None:
    df = pd.read_csv(CONFIG / "stations_census.csv")
    domains = load_domains()
    fig, axes = plt.subplots(2, 1, figsize=(14, 12), subplot_kw={"projection": ccrs.PlateCarree()})
    for ax, subset, title in [
        (axes[0], df, f"all sources in bbox (n={len(df)})"),
        (axes[1], df[df["training_eligible"]], f"active and >= 3 yr record (n={int(df['training_eligible'].sum())})"),
    ]:
        ax.set_extent([-99.3, -88.0, 25.5, 31.5])
        ax.add_feature(cfeature.LAND.with_scale("10m"), facecolor="#f0f0f0")
        ax.add_feature(cfeature.OCEAN.with_scale("10m"), facecolor="#dbe9f6")
        ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=0.5)
        ax.add_feature(cfeature.STATES.with_scale("10m"), linewidth=0.4, edgecolor="gray")
        ax.add_feature(cfeature.RIVERS.with_scale("10m"), linewidth=0.3, edgecolor="#9ecae1")
        for name, b in domains.items():
            ax.plot([b["lon_min"], b["lon_max"], b["lon_max"], b["lon_min"], b["lon_min"]],
                    [b["lat_min"], b["lat_min"], b["lat_max"], b["lat_max"], b["lat_min"]],
                    color="k", lw=1.2, ls="--", transform=ccrs.PlateCarree())
            ax.text(b["lon_min"] + 0.05, b["lat_max"] - 0.15, name, fontsize=9, weight="bold")
        for src, g in subset.groupby("source"):
            key = src.split("_")[0] if src.startswith("USACE") else src
            c = COLORS.get(src, COLORS.get(key, "k"))
            lab = "USACE" if src.startswith("USACE") else src
            ax.scatter(g["lon"], g["lat"], s=14, c=c, label=f"{lab} ({len(g)})", alpha=0.8,
                       edgecolor="k", linewidth=0.2, transform=ccrs.PlateCarree())
        # de-duplicate legend labels (USACE offices)
        h, l = ax.get_legend_handles_labels()
        seen, hh, ll = set(), [], []
        for hi, li in zip(h, l):
            k = li.split(" (")[0]
            if k in seen:
                continue
            seen.add(k)
            n = int(subset["source"].str.startswith(k).sum())
            hh.append(hi); ll.append(f"{k} ({n})")
        ax.legend(hh, ll, loc="lower left", fontsize=9)
        ax.set_title(title)
        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5)
        gl.top_labels = gl.right_labels = False
    fig.tight_layout()
    out = ROOT / "figures" / "stations_census.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    print(out)


if __name__ == "__main__":
    main()
