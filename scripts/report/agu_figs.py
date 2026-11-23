"""Figures of the AGU slides on the water-level model that is run: the mean of five LSTMs with the inputs water level,
wind, upstream discharge and rainfall (run folder v15r_mean5).

  agu_gauges_map.png         the gauges: with data in real time (forecast) and marsh gauges used for training only; the three 100 m domains
  agu_architecture.png       inputs, network and output as a block diagram
  agu_hurricane_gauges.png   hurricanes Beryl and Francine (2024, test period): observed level and the forecasts issued 1, 3, 6 h earlier at four gauges
  agu_hurricane_scatter.png  the same two hurricanes, every forecast 6 h ahead of all gauges against the observation
  agu_recent_gauges.png      14 to 20 November 2026, forecasts made from the real-time data feeds: the same kind of panels at six gauges
  agu_numbers.json           the numbers the slides quote
Input : runs/v14_stale25/stations.csv, runs/v15r_mean5/per_station_test.csv, runs/v14_stale25/history.json, config/station_groups.csv,
        deliverables/17_versions/data and deliverables/37_agu/data (<station>_obs.csv, <station>_fc.csv of extract_versions_hourly.py; column base_fc),
        deliverables/37_agu/storm_pairs.npz (agu_storm_pairs.py), deliverables/37_agu/realtime_pairs.csv.gz (scripts/operational/realtime_pairs.py)
Output: deliverables/37_agu/
Usage : python agu_figs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from versions_figs import DOMAINS, INK, LEAD_COL, REPO, SEQ, load_runs, pooled

OUT = REPO / "deliverables" / "37_agu"
DATA = [REPO / "deliverables" / "17_versions" / "data", OUT / "data"]
KEY = "base_fc"                                             # column of the mean of five models in the forecast files
GREY, LIGHT, RULE = "#8a8a84", "#efefec", "#b9b9b3"
LEADS = (1, 3, 6)
plt.rcParams.update({"font.family": "Times New Roman", "mathtext.fontset": "stix", "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False})

# gauges drawn, chosen for good results. Hurricanes: station, window in the data files, name, what it is
HURRICANE = [("02481660", "hurricane Francine", "Jourdan River near Bay St. Louis, Mississippi", "tidal river, Hurricane Francine, Sep 2024"),
             ("07380260", "hurricane Francine", "Empire Waterway, Louisiana", "tidal channel, Hurricane Francine, Sep 2024"),
             ("08162500", "hurricane Beryl", "Colorado River near Bay City, Texas", "river, Hurricane Beryl, Jul 2024"),
             ("08067000", "hurricane Beryl", "Trinity River at Liberty, Texas", "river, Hurricane Beryl, Jul 2024")]
# the week of real-time forecasts: station, name, what it is
RECENT = [("8760922", "Southwest Pass, Louisiana", "tide gauge at the mouth of the Mississippi"),
          ("07374000", "Mississippi River at Baton Rouge", "river"),
          ("08068900", "Cypress Creek, Houston, Texas", "urban creek, after rain"),
          ("8779770", "Port Isabel, Texas", "tide gauge"),
          ("08162000", "Colorado River at Wharton, Texas", "river"),
          ("08210000", "Nueces River near Three Rivers, Texas", "river")]
FAULTY = ["02481510"]                                       # Wolf River near Landon: wrong readings on 17 Nov 2026 in the input (deliverable 33), left out of the week's scores
TYPES = [("tide gauge", "Tide gauges"), ("estuary / tidal channel", "Estuaries"), ("lake", "Lakes"), ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks")]


def rmse(e) -> float:
    e = np.asarray(e, float); e = e[np.isfinite(e)]; return float(np.sqrt((e ** 2).mean())) if len(e) else np.nan


def by_type(d: pd.DataFrame) -> list:
    """d: one row per forecast with station_id, type, e1, e3, e6 (cm). Rows of the slide table: all gauges, then every type."""
    ps = d.groupby(["station_id", "type"])[["e1", "e3", "e6"]].agg(rmse).reset_index()
    def row(lab, x, y):
        return {"gauges_of": lab, "gauges": int(y.station_id.nunique()), **{f"rmse_{h}h_cm": round(rmse(x[f"e{h}"]), 2) for h in LEADS}, **{f"median_gauge_{h}h_cm": round(float(y[f"e{h}"].median()), 2) for h in LEADS}}
    return [row("All gauges", d, ps)] + [row(lab, d[d.type == t], ps[ps.type == t]) for t, lab in TYPES]


def storm_pairs() -> pd.DataFrame:
    z = np.load(OUT / "storm_pairs.npz", allow_pickle=True); e = (z["forecast"] - z["observed"]) * 100; ok = z["valid"]
    d = pd.DataFrame({"station_id": z["station_id"].astype(str), "type": z["type"].astype(str), "storm": z["storm"].astype(str), "row": z["station"]})
    for h in LEADS:
        d[f"e{h}"] = np.where(ok[:, h - 1], e[:, h - 1], np.nan); d[f"fc{h}"] = np.where(ok[:, h - 1], z["forecast"][:, h - 1], np.nan); d[f"ob{h}"] = np.where(ok[:, h - 1], z["observed"][:, h - 1], np.nan)
    return d


def realtime() -> pd.DataFrame:
    f = pd.read_csv(OUT / "realtime_pairs.csv.gz", dtype={"station_id": str}, parse_dates=["origin", "valid"])
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})[["source", "station_id", "type"]]
    return f.merge(g, on=["source", "station_id"], how="left")


def numbers() -> dict:
    st = pd.read_csv(REPO / "runs" / "v14_stale25" / "stations.csv", dtype={"station_id": str})
    per = load_runs(["v15r_mean5"])["v15r_mean5"]; hist = json.loads((REPO / "runs" / "v14_stale25" / "history.json").read_text())
    n = {"gauges": len(st), "by_source": {k: int(v) for k, v in st.source.value_counts().items()}, "gauges_real_time": int(st.source.isin(["USGS", "NOAA_COOPS"]).sum()),
         "observations_train_2010_2022": int(st.n_train.sum()), "observations_all_2010_2025": int(st[["n_train", "n_val", "n_test"]].sum().sum()),
         "epochs": len(hist), "training_minutes_per_model": round(sum(e["sec"] for e in hist) / 60), "samples_per_model": len(hist) * 2000 * 1024,
         "test_2024_2025": {"gauges": len(per), "forecasts": int(per.n_6h.sum()), "rmse_all_forecasts_cm": {h: round(pooled(per, h), 3) for h in LEADS},
                            "rmse_median_gauge_cm": {h: round(float(per[f"rmse_{h}h_cm"].median()), 3) for h in LEADS}}}
    d = storm_pairs()
    n["hurricanes"] = {"gauges": int(d.station_id.nunique()), "forecasts": len(d), "forecasts_by_storm": {k: int(v) for k, v in d.storm.value_counts().items()}, "table": by_type(d)}
    f = realtime().dropna(subset=["obs", "forecast"]); f = f[~f.station_id.isin(FAULTY)]; f["e"] = (f.forecast - f.obs) * 100
    w = f[f.lead.isin(LEADS)].pivot_table(index=["station_id", "type", "origin"], columns="lead", values="e").rename(columns={h: f"e{h}" for h in LEADS}).reset_index()
    n["recent_week"] = {"gauges": int(w.station_id.nunique()), "forecast_times": int(w.origin.nunique()), "forecasts": len(w), "first": str(w.origin.min()), "last": str(w.origin.max()), "left_out": FAULTY, "table": by_type(w)}
    (OUT / "agu_numbers.json").write_text(json.dumps(n, indent=1)); return n


def gauges_map() -> Path:
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    st = pd.read_csv(REPO / "runs" / "v14_stale25" / "stations.csv", dtype={"station_id": str}); rt = st.source.isin(["USGS", "NOAA_COOPS"]); pc = ccrs.PlateCarree()
    fig = plt.figure(figsize=(5.6, 3.25)); ax = fig.add_axes([0.005, 0.13, 0.99, 0.865], projection=pc); ax.set_extent([-99.3, -88.1, 25.6, 31.4], crs=pc)
    ax.add_feature(cf.LAND, facecolor="#f4f4f1"); ax.add_feature(cf.COASTLINE, lw=0.4, edgecolor=GREY); ax.add_feature(cf.STATES, lw=0.3, edgecolor=RULE)
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_linewidth(0.5); sp.set_edgecolor(GREY)
    for (name, x0, x1, y0, y1), (tx, ty, ha, va) in zip(DOMAINS, [(-88.5, 28.82, "right", "bottom"), (-98.93, 25.93, "left", "bottom"), (-96.6, 31.06, "left", "top")]):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=INK, lw=0.8, ls=(0, (4, 2)), transform=pc, zorder=3))
        ax.text(tx, ty, name.replace("100m", ""), transform=pc, fontsize=9.5, color=INK, ha=ha, va=va, zorder=6, bbox=dict(facecolor="white", edgecolor="none", pad=1.0, alpha=0.85))
    ax.scatter(st.lon[~rt], st.lat[~rt], s=5, color="#a9a9a3", linewidth=0, transform=pc, zorder=4)
    ax.scatter(st.lon[rt], st.lat[rt], s=7, color=INK, linewidth=0, transform=pc, zorder=5)
    h = [Line2D([], [], marker="o", ls="", color=INK, markersize=4), Line2D([], [], marker="o", ls="", color="#a9a9a3", markersize=4), Line2D([], [], color=INK, lw=0.8, ls=(0, (4, 2)))]
    fig.legend(h, [f"{int(rt.sum())} gauges with data in real time (USGS, NOAA)", f"{int((~rt).sum())} more gauges, training only (CRMS marsh gauges, USACE)", "100 m model domains"], loc="lower center", ncol=2, frameon=False,
               fontsize=9.5, handletextpad=0.4, columnspacing=1.2, bbox_to_anchor=(0.5, -0.025), labelspacing=0.25)
    out = OUT / "agu_gauges_map.png"; fig.savefig(out, dpi=300); plt.close(fig); return out


def architecture() -> Path:
    """Block diagram: inputs of the past 72 h -> two LSTM layers (unrolled) -> last state joined with the gauge embedding and the
    forecast forcing of the next 6 h -> fully connected head -> water level 1 to 6 h ahead; five such networks, averaged."""
    fig = plt.figure(figsize=(7.4, 4.3)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 7.4); ax.set_ylim(0, 4.3); ax.axis("off")

    def box(x, y, w, h, label, fc="white", fs=10.5, lw=0.9, bold=False, ls="-", va="center", color=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", facecolor=fc, edgecolor=INK, linewidth=lw, linestyle=ls, zorder=2))
        if label:
            ax.text(x + w / 2, y + h / 2 if va == "center" else y + h - 0.09, label, ha="center", va=va if va != "top" else "top", fontsize=fs, color=color, fontweight="bold" if bold else "normal", linespacing=1.15, zorder=3)

    def arrow(x0, y0, x1, y1, lw=0.9):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9, linewidth=lw, color=INK, shrinkA=0, shrinkB=0, zorder=4))

    # ---- inputs of the past 72 h
    ax.text(0.95, 4.12, "Past 72 hours, hourly", ha="center", va="center", fontsize=11, fontweight="bold")
    rows = [("Water level", "at the gauge"), ("Wind", "10 m, at the gauge"), ("Rainfall", "around the gauge"), ("River discharge", "upstream gauge")]
    for k, (a, b) in enumerate(rows):
        y = 3.42 - k * 0.56; box(0.12, y, 1.66, 0.46, "", fc=LIGHT)
        ax.text(0.95, y + 0.30, a, ha="center", va="center", fontsize=10.5); ax.text(0.95, y + 0.12, b, ha="center", va="center", fontsize=9.5, color="#55554f")
    box(0.12, 0.62, 1.66, 0.62, "", fc="white"); ax.text(0.95, 1.03, "Gauge embedding", ha="center", va="center", fontsize=10.5)
    ax.text(0.95, 0.80, "16 numbers learned\nfor each of 1,010 gauges", ha="center", va="center", fontsize=9.5, color="#55554f", linespacing=1.1)

    # ---- the recurrent part, unrolled in time
    x0, cw, gap = 2.36, 0.48, 0.15; xs = [x0, x0 + cw + gap, x0 + 2 * (cw + gap) + 0.40, x0 + 3 * (cw + gap) + 0.40]; labs = ["t − 71", "t − 70", "t − 1", "t"]
    ax.add_patch(FancyBboxPatch((2.22, 1.62), 3.05, 2.30, boxstyle="round,pad=0,rounding_size=0.08", facecolor="white", edgecolor=RULE, linewidth=0.8, zorder=1))
    ax.text(3.73, 4.12, "LSTM: 2 layers × 128 units", ha="center", va="center", fontsize=11, fontweight="bold")
    BUS = 1.80                                                                 # the inputs of one hour run along this line into the lower layer
    for x, lab in zip(xs, labs):
        for y in (2.02, 2.92):
            box(x, y, cw, 0.50, "LSTM", fc=LIGHT, fs=9.5)
        arrow(x + cw / 2, 2.52, x + cw / 2, 2.92); arrow(x + cw / 2, BUS, x + cw / 2, 2.02)
        ax.text(x + cw / 2, 1.44, lab, ha="center", va="center", fontsize=9.5, style="italic")
    for y in (2.27, 3.17):
        arrow(xs[0] + cw, y, xs[1], y); arrow(xs[2] + cw, y, xs[3], y)
        ax.plot([xs[1] + cw, xs[1] + cw + 0.10], [y, y], color=INK, lw=0.9); arrow(xs[2] - 0.12, y, xs[2], y)
        ax.text((xs[1] + cw + xs[2]) / 2, y, "· · ·", ha="center", va="center", fontsize=11)
    ax.text((xs[1] + cw + xs[2]) / 2, 1.44, "· · ·", ha="center", va="center", fontsize=11)
    for k in range(4):                                                         # the four inputs and the embedding gathered on one line
        ax.plot([1.78, 2.00], [3.65 - k * 0.56] * 2, color=INK, lw=0.9)
    ax.plot([1.78, 2.00], [0.93, 0.93], color=INK, lw=0.9); ax.plot([2.00, 2.00], [0.93, 3.65], color=INK, lw=0.9)
    ax.plot([2.00, xs[3] + cw / 2], [BUS, BUS], color=INK, lw=0.9)

    # ---- the head
    box(5.62, 2.70, 1.62, 0.92, "", fc="white"); ax.text(6.43, 3.42, "Next 6 hours", ha="center", va="center", fontsize=10.5, fontweight="bold")
    ax.text(6.43, 3.03, "forecast wind\nforecast rainfall (HRRR)", ha="center", va="center", fontsize=9.5, color="#55554f", linespacing=1.15)
    box(5.62, 1.72, 1.62, 0.60, "Fully connected\nlayers", fc=LIGHT, fs=10.5)
    arrow(xs[3] + cw, 3.17, 5.44, 3.17); ax.plot([5.44, 5.44], [3.17, 2.02], color=INK, lw=0.9); arrow(5.44, 2.02, 5.62, 2.02)
    arrow(6.43, 2.70, 6.43, 2.32)
    ax.plot([0.95, 0.95], [0.62, 0.40], color=INK, lw=0.9); ax.plot([0.95, 5.30], [0.40, 0.40], color=INK, lw=0.9); ax.plot([5.30, 5.30], [0.40, 1.90], color=INK, lw=0.9); arrow(5.30, 1.90, 5.62, 1.90)
    arrow(6.43, 1.72, 6.43, 1.30)
    box(5.62, 0.66, 1.62, 0.64, "", fc="white", lw=1.3); ax.text(6.43, 1.08, "Water level", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(6.43, 0.85, "t + 1, t + 2, … , t + 6 h", ha="center", va="center", fontsize=9.5, style="italic")
    ax.text(3.15, 0.52, "gauge embedding", ha="center", va="center", fontsize=9.5, color="#55554f")
    ax.text(3.70, 0.14, "Five networks of this form, trained from different random starts; the forecast is their mean.", ha="center", va="center", fontsize=10.5)
    out = OUT / "agu_architecture.png"; fig.savefig(out, dpi=300); plt.close(fig); return out


def read(sid: str, window: str) -> tuple[pd.Series, pd.DataFrame]:
    """Observed series and forecasts (lead, valid, value) of a gauge in a window of the test period."""
    d = next(p for p in DATA if (p / f"{sid}_fc.csv").exists())
    obs = pd.read_csv(d / f"{sid}_obs.csv", parse_dates=["time"]); fc = pd.read_csv(d / f"{sid}_fc.csv", parse_dates=["origin", "valid"])
    o = obs[obs.window == window].set_index("time").obs; f = fc[(fc.window == window) & fc.valid.isin(o.index)]
    return o, f[["lead", "valid", KEY]].rename(columns={KEY: "value"})


def panels(items: list, out: Path, ncol: int, figsize, day_step: int = 1) -> Path:
    """items: (name, what, observed series, forecasts with lead, valid, value). Black: observed; warm lines, pale to vivid: the
    forecast valid at each hour that was issued 1, 3 and 6 h earlier. The RMSE of the window is written in every panel."""
    nrow = int(np.ceil(len(items) / ncol)); fig, axes = plt.subplots(nrow, ncol, figsize=figsize, squeeze=False, gridspec_kw={"wspace": 0.17, "hspace": 0.52})
    for ax, (name, what, o, f) in zip(axes.ravel(), items):
        for h in LEADS:
            g = f[f.lead == h].sort_values("valid"); ax.plot(g.valid, g.value, color=LEAD_COL[h], lw=1.2, zorder=4)
        ax.plot(o.index, o.values, color=INK, lw=1.4, zorder=5)
        lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi + 0.22 * (hi - lo))
        r = {h: 100 * rmse(f[f.lead == h].set_index("valid").value - o.reindex(f[f.lead == h].valid.values).values) for h in LEADS}
        ax.text(0.025, 0.965, "RMSE   " + "    ".join(f"{h} h: {r[h]:.1f} cm" for h in LEADS), transform=ax.transAxes, va="top", ha="left", fontsize=10, color=INK, zorder=6)
        ax.set_title(name, loc="left", fontsize=11.5, fontweight="bold", pad=17); ax.text(0, 1.035, what, transform=ax.transAxes, ha="left", va="bottom", fontsize=10, color="#55554f")
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=day_step)); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{mdates.num2date(x).day} {mdates.num2date(x):%b}"))
        ax.tick_params(labelsize=9.5, length=3, width=0.6); ax.grid(axis="y", color="#e6e6e2", lw=0.5); ax.set_axisbelow(True); ax.margins(x=0.01)
    for ax in axes[:, 0]:
        ax.set_ylabel("Water level (m)", fontsize=10.5)
    for ax in axes.ravel()[len(items):]:
        ax.axis("off")
    h = [Line2D([], [], color=INK, lw=1.6)] + [Line2D([], [], color=LEAD_COL[k], lw=1.8) for k in LEADS]
    fig.legend(h, ["Observed"] + [f"Forecast issued {k} h earlier" for k in LEADS], loc="lower center", ncol=4, frameon=False, fontsize=11 if ncol > 2 else 10,
               bbox_to_anchor=(0.5, -0.035), columnspacing=2.2 if ncol > 2 else 1.4)
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.04); plt.close(fig); return out


def hurricane_gauges() -> Path:
    return panels([(name, what, *read(sid, w)) for sid, w, name, what in HURRICANE], OUT / "agu_hurricane_gauges.png", ncol=2, figsize=(8.6, 4.4))


def hurricane_scatter(lead: int = 6) -> Path:
    """Every forecast of the two hurricanes at the given lead against the observation, all gauges; the level is taken relative to
    the mean level of the gauge (mean of the training years), so that gauges at different elevations fall on one diagram."""
    d = storm_pairs(); mean = pd.read_csv(REPO / "runs" / "v14_stale25" / "stations.csv").mean_m.to_numpy()[d.row.to_numpy()]
    x = (d[f"ob{lead}"] - mean).to_numpy(); y = (d[f"fc{lead}"] - mean).to_numpy(); m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    lo, hi = np.floor(min(x.min(), y.min())), np.ceil(max(x.max(), y.max()))
    fig = plt.figure(figsize=(4.3, 4.45)); ax = fig.add_axes([0.16, 0.115, 0.80, 0.773])
    hb = ax.hexbin(x, y, gridsize=70, extent=(lo, hi, lo, hi), mincnt=1, norm=LogNorm(vmin=1, vmax=3000), cmap=LinearSegmentedColormap.from_list("seq", SEQ), linewidths=0)
    ax.plot([lo, hi], [lo, hi], color=INK, lw=0.8, zorder=5); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("Observed water level (m)", fontsize=10.5); ax.set_ylabel(f"Forecast {lead} h earlier (m)", fontsize=10.5); ax.tick_params(labelsize=9.5, length=3, width=0.6)
    ax.text(0, 1.095, f"All {d.station_id.nunique()} gauges, {lead} h ahead", transform=ax.transAxes, ha="left", va="bottom", fontsize=11.5, fontweight="bold")
    ax.text(0, 1.035, "level relative to the mean level of each gauge", transform=ax.transAxes, ha="left", va="bottom", fontsize=10, color="#55554f")
    ax.text(0.04, 0.96, f"{len(x):,} forecasts" + chr(10) + f"r = {np.corrcoef(x, y)[0, 1]:.2f}", transform=ax.transAxes, ha="left", va="top", fontsize=10, linespacing=1.3)
    cax = ax.inset_axes([0.62, 0.10, 0.33, 0.035]); cb = fig.colorbar(hb, cax=cax, orientation="horizontal", ticks=[1, 10, 100, 1000]); cb.outline.set_linewidth(0.4)
    cax.tick_params(labelsize=8, length=2, width=0.4); cax.set_title("forecasts per cell", fontsize=8.5, pad=3)
    out = OUT / "agu_hurricane_scatter.png"; fig.savefig(out, dpi=300); plt.close(fig); return out


def recent_gauges() -> Path:
    f = realtime(); items = []
    for sid, name, what in RECENT:
        x = f[f.station_id == sid]; o = x.dropna(subset=["obs"]).drop_duplicates("valid").set_index("valid").obs.sort_index()
        items.append((name, what, o, x[x.valid.isin(o.index)][["lead", "valid", "forecast"]].rename(columns={"forecast": "value"})))
    return panels(items, OUT / "agu_recent_gauges.png", ncol=3, figsize=(12.6, 4.3), day_step=2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(json.dumps(numbers(), indent=1)[:6000])
    for fn in (gauges_map, architecture, hurricane_gauges, hurricane_scatter, recent_gauges):
        print("->", fn())


if __name__ == "__main__":
    main()
