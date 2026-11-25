"""Francine case: animations of the run - how the water level changes during the storm, with the wind of the forcing.

Colour: change of the water level from the mean of the three days before the storm (run_fields.py). On a cell that is dry
before the storm the change is the depth of water that comes to stand on it; under water it is the rise (red) or fall (blue)
of the level, tide included. Grey line: the shore before the storm. Arrows: 10 m wind of the forcing (HRRR), thin lines:
air pressure every 5 hPa up to 1005 hPa.
Input : --fields NPZ of run_fields.py
Output: --out GIF, and beside it _frame.png (the frame nearest to --still)
Usage : python run_animation.py --fields FILE --view whole|zoom --start "2024-09-10 00:00" --end "2024-09-13 12:00" --out FILE.gif [--fps 6] [--still "2024-09-12 02:00"]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.linewidth": 0.6})
INK, MUTED = "#0b0b0b", "#52514e"; LANDFALL = pd.Timestamp("2024-09-11 22:00")
DIV = LinearSegmentedColormap.from_list("blue_red", ["#0d366b", "#1c5cab", "#3987e5", "#9ec5f4", "#f0efec", "#f1a7a0", "#e34948", "#b02a2a", "#6e1414"])


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--fields", required=True); ap.add_argument("--view", choices=["whole", "zoom"], required=True); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=6); ap.add_argument("--vmax", type=float, default=1.5); ap.add_argument("--still", default="2024-09-12 02:00"); ap.add_argument("--dpi", type=int, default=100); a = ap.parse_args()
    F = np.load(a.fields, allow_pickle=True); t = pd.DatetimeIndex(F["time"]); sel = np.where((t >= a.start) & (t <= a.end))[0]; z = a.view == "zoom"
    C = F["zoom_change" if z else "change"]; lon = F["zoom_lon" if z else "lon"]; lat = F["zoom_lat" if z else "lat"]; water = F["zoom_open_water" if z else "open_water"]; ext = [lon[0], lon[-1], lat[0], lat[-1]]
    wl, wa = F["wind_lon"], F["wind_lat"]; ang = np.deg2rad(0.6225 * (wl + 97.5)); step = 5 if z else 10; q = (slice(step // 2, None, step), slice(step // 2, None, step))        # winds of HRRR run along its own grid: turned to east and north
    box = (wl >= ext[0]) & (wl <= ext[1]) & (wa >= ext[2]) & (wa <= ext[3])

    def wind(k):
        u = F["wind_u"][k].astype("f4"); v = F["wind_v"][k].astype("f4"); return np.cos(ang) * u + np.sin(ang) * v, -np.sin(ang) * u + np.cos(ang) * v
    fig = plt.figure(figsize=(7.6, 6.9) if z else (10.4, 5.9)); ax = fig.add_axes([0.07, 0.17, 0.90, 0.72] if z else [0.055, 0.19, 0.925, 0.70])
    im = ax.imshow(C[sel[0]].astype("f4"), origin="lower", extent=ext, cmap=DIV, vmin=-a.vmax, vmax=a.vmax, aspect=1 / np.cos(np.deg2rad(lat.mean())), interpolation="nearest", zorder=1)
    ax.contour(lon, lat, water, levels=[0.5], colors=["#6b6b68"], linewidths=0.45, zorder=3)
    u, v = wind(sel[0]); m = box[q]; Q = ax.quiver(wl[q][m], wa[q][m], u[q][m], v[q][m], color=INK, scale=520 if z else 700, width=0.0022, headwidth=3.6, headlength=4.2, zorder=6, alpha=0.85)
    ax.quiverkey(Q, 0.90, -0.085, 20, "wind 20 m/s", labelpos="E", coordinates="axes", fontproperties={"size": 9.5})
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.tick_params(length=2.5, width=0.5)
    cax = fig.add_axes([0.10, 0.075, 0.52, 0.022] if z else [0.08, 0.075, 0.50, 0.024]); cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend="both"); cb.set_label("change of water level from before the storm (m); on land that is dry before: depth of water", fontsize=9); cb.outline.set_linewidth(0.4)
    fig.text(0.5, 0.955, "Hurricane Francine run" + (", south-east Louisiana" if z else ", Louisiana 100 m grid"), ha="center", va="center", fontsize=12.5); stamp = fig.text(0.5, 0.915, "", ha="center", va="center", fontsize=11.5, color=INK)
    state = {"cs": None}

    def draw(n):
        k = sel[n]; im.set_data(C[k].astype("f4")); u, v = wind(k); Q.set_UVC(u[q][m], v[q][m])
        if state["cs"] is not None:
            state["cs"].remove()
        state["cs"] = ax.contour(wl, wa, F["pair"][k], levels=np.arange(960, 1006, 5), colors=[INK], linewidths=0.5, alpha=0.6, zorder=5)
        h = (t[k] - LANDFALL) / pd.Timedelta(hours=1); stamp.set_text(f"{t[k]:%d %B %Y  %H:%M} UTC     " + (f"{abs(h):.0f} h before the landfall" if h < 0 else ("landfall" if h == 0 else f"{h:.0f} h after the landfall")))
        return [im]
    still = int(np.argmin(np.abs(t[sel] - pd.Timestamp(a.still)))); draw(still); fig.savefig(str(Path(a.out).with_suffix("")) + "_frame.png", dpi=160)
    FuncAnimation(fig, draw, frames=len(sel), blit=False).save(a.out, writer=PillowWriter(fps=a.fps), dpi=a.dpi); print("->", a.out, f"{len(sel)} frames, {Path(a.out).stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
