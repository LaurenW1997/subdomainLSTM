"""Slide deck comparing every model version side by side (deliverable 17): white background, black Times New Roman,
no title page.

Reads deliverables/17_versions/{versions_table.csv, versions_bars.png, versions_lead.png, station_<id>.png, data/*.csv}
(from versions_figs.py) and runs/*/per_station_test.csv. Writes deliverables/17_versions/version_comparison.pptx.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from slides_figures import picture, text
from versions_figs import MAIN, load_runs, pooled

REPO = Path(__file__).resolve().parents[2]
F = REPO / "deliverables" / "17_versions"
TYPE_ORDER = ["tide gauge", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]
TYPE_EN = {"tide gauge": "Tide gauge", "estuary / tidal channel": "Estuary / tidal channel", "lake": "Lake", "river / canal": "River", "urban creek (Houston)": "Urban creek"}
WHAT = {"v3_obs": ("72 h of water level at the station", "yes"),
        "v3_wind_past": ("wind at the station, past 72 h", "yes (HRRR analysis)"),
        "v3_wind": ("wind for the 6 forecast hours", "yes (HRRR forecast)"),
        "v3_wind_q": ("discharge at the nearest upstream USGS gauge", "yes (USGS)"),
        "v6_wind_q": ("gauge on the same river; no wind at 15 inland rivers", "yes  —  operational"),
        "v7_rain_p15_past": ("rainfall, 15 km around the station, past 72 h", "yes (radar / analysis)"),
        "v9_fc1_t45": ("HRRR rainfall forecast, total of the next 6 h", "yes (HRRR forecast)"),
        "v7_rain_p15": ("observed rainfall of the next 6 h", "NO  —  upper bound")}
SHORT = {"v3_obs": "Water level only", "v3_wind_past": "+ wind, past 72 h", "v3_wind": "+ wind, next 6 h", "v3_wind_q": "+ upstream discharge",
         "v6_wind_q": "refined discharge and wind", "v7_rain_p15_past": "+ rainfall, past 72 h", "v9_fc1_t45": "+ rainfall, HRRR forecast",
         "v7_rain_p15": "+ rainfall, observed future"}


def pooled_nc(run: str, ref: str = "v6_wind_q") -> tuple[float, float]:
    """6 h RMSE pooled over operational stations for a run and for the reference on the same stations."""
    d = load_runs([ref, run]); return pooled(d[run]), pooled(d[ref])


def main() -> None:
    tab = pd.read_csv(F / "versions_table.csv")
    scr = pd.read_csv(F / "data" / "station_screen.csv", dtype={"station_id": str}).set_index("station_id")
    per = load_runs([r for _, r, _, _ in MAIN])
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]
    n = 0

    def new(title):
        nonlocal n
        n += 1; sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=17, bold=True)
        text(sl, 12.5, 7.05, 0.6, 0.3, str(n), size=10, align=PP_ALIGN.RIGHT)
        return sl

    # ---- 1 the ladder as a table
    sl = new("Every model version so far, in the order it was built")
    cols = [(0.5, 2.55, "Version", PP_ALIGN.LEFT), (3.1, 4.0, "What was added", PP_ALIGN.LEFT), (7.15, 2.1, "Available in real time", PP_ALIGN.LEFT),
            (9.3, 1.1, "All stations", PP_ALIGN.RIGHT), (10.45, 1.1, "Urban creeks", PP_ALIGN.RIGHT), (11.6, 1.2, "Tide gauges", PP_ALIGN.RIGHT)]
    y = 1.05
    text(sl, 9.3, y - 0.05, 3.5, 0.3, "6 h RMSE (cm)", size=11, bold=True, align=PP_ALIGN.CENTER); y += 0.28
    for x, w, h, al in cols:
        text(sl, x, y, w, 0.3, h, size=11, bold=True, align=al)
    y += 0.38
    for _, r in tab.iterrows():
        op = r.run == "v6_wind_q"
        vals = [SHORT[r.run], WHAT[r.run][0], WHAT[r.run][1], f"{r['all']:.1f}", f"{r['urban creek (Houston)']:.1f}", f"{r['tide gauge']:.1f}"]
        for (x, w, _, al), v in zip(cols, vals):
            text(sl, x, y, w, 0.3, v, size=11, bold=op, align=al)
        y += 0.44
    text(sl, 0.5, y + 0.15, 12.3, 1.3, [
        f"Each row keeps everything above it and adds one thing. Test period January 2024 to December 2025, {int(tab.n_stations.iloc[0])} operational stations (USGS and NOAA; CRMS marsh stations are used for training only and are left out here).",
        "All stations: RMSE over all forecasts. Urban creeks and tide gauges: the median station of that type. Same network in every row: 2-layer LSTM, hidden size 128, 72 h look-back, one model for all stations.",
        "The HRRR-rainfall row is scored on forecasts issued at 00/06/12/18 UTC, the other rows at 23/05/11/17 UTC; the operational version differs by 0.01 cm between the two sets."], size=11)

    # ---- 2 bars
    sl = new("What each added input bought, by station type")
    picture(sl, F / "versions_bars.png", 0.3, 1.0, 12.7, 3.6)
    t = tab.set_index("run")
    text(sl, 0.5, 4.75, 12.3, 2.3, [
        f"Wind is the step that helps the tidal station types: tide gauges {t.loc['v3_obs','tide gauge']:.1f} to {t.loc['v3_wind','tide gauge']:.1f} cm, estuaries {t.loc['v3_obs','estuary / tidal channel']:.1f} to {t.loc['v3_wind','estuary / tidal channel']:.1f} cm, lakes {t.loc['v3_obs','lake']:.1f} to {t.loc['v3_wind','lake']:.1f} cm. It does little for rivers and urban creeks.",
        "Upstream discharge changes the medians by 0.1 cm or less. Its effect is at individual mid-river stations and in high-water periods, not in the typical station.",
        f"Rainfall is the step that helps urban creeks, and how much depends on where the rainfall of the next 6 h comes from: {t.loc['v6_wind_q','urban creek (Houston)']:.1f} cm without rainfall, {t.loc['v9_fc1_t45','urban creek (Houston)']:.1f} cm with the HRRR forecast, {t.loc['v7_rain_p15','urban creek (Houston)']:.1f} cm if the rainfall were known exactly (grey bar, not available in real time).",
        "With HRRR rainfall the tidal types are 0.1 cm worse than the operational version: that model could only be trained on 2014 onwards and on four forecast times a day."], size=12)

    # ---- 3 lead time
    sl = new("Error against lead time for the five main versions")
    picture(sl, F / "versions_lead.png", 0.5, 1.0, 12.3, 4.4)
    text(sl, 0.5, 5.6, 12.3, 1.4, [
        "Tide gauges: all versions with wind lie on one line, 0.7 cm below water level only at 6 h. Rainfall adds nothing.",
        "Rivers: the versions are within 0.3 cm of each other at every lead, except observed future rainfall.",
        "Urban creeks: the versions separate after 2 h. The HRRR-rainfall version is 1.4 cm below the operational one at 6 h; observed rainfall is 5 cm below."], size=12)

    # ---- maps: 6 h RMSE at every station, version by version, and the change of each step
    r6 = {k: per[run].rmse_6h_cm.to_numpy() for k, run, _, _ in MAIN}
    above = {k: int((v > 10).sum()) for k, v in r6.items()}
    sl = new("Station by station: 6 h RMSE of the five main versions")
    picture(sl, F / "versions_map_rmse.png", 0.3, 0.95, 12.7, 5.1)
    text(sl, 0.5, 6.15, 12.3, 1.0, [
        f"Stations above 10 cm: {above['wl']} with water level only, {above['q']} in the operational version, {above['rain_fc']} with HRRR rainfall, {above['rain_obs']} with observed rainfall.",
        "The dark stations sit in the same two places in every map: the Houston creeks and the small rivers north and east of Baton Rouge. "
        "The coast is light from the second map on."], size=12)

    def count(a, b):
        dd = r6[a] - r6[b]; return int((dd <= -0.5).sum()), int((dd >= 0.5).sum())

    sl = new("Station by station: what each step changed")
    picture(sl, F / "versions_map_change.png", 0.3, 1.0, 12.7, 3.4)
    b1, w1 = count("q", "wl"); b2, w2 = count("rain_fc", "q"); b3, w3 = count("rain_obs", "q")
    text(sl, 0.5, 4.5, 12.3, 2.5, [
        f"Left, wind and discharge: {b1} stations better and {w1} worse by 0.5 cm or more. The gain follows the coast and the bays; inland stations do not change.",
        f"Middle, HRRR rainfall on top of the operational version: {b2} better, {w2} worse. The gain is in Houston and around Baton Rouge, where the rain-fed creeks are. "
        "Most of the stations that get worse are rivers; the two largest losses are at the Pearl River navigation locks (2 to 7 cm and 13 to 19 cm), where the level is set by gate operation.",
        f"Right, the same step with observed rainfall: {b3} better, {w3} worse. Same places as the middle map, several times stronger. "
        "The difference between the middle and the right map is the error of the rainfall forecast.",
        "Colour scale limited to 5 cm in both directions; larger changes take the end colour."], size=12)

    # ---- 4 tried and set aside
    sl = new("Also tried: changes that made no measurable difference")
    rows = [("Change", "6 h RMSE, all stations (cm)", "Reference (cm)", True)]
    for run, lab, ref in [("v6_lb168", "Look-back 168 h instead of 72 h", "v6_wind_q"), ("v6_lb336", "Look-back 336 h instead of 72 h", "v6_wind_q"),
                          ("v6_l3", "3 LSTM layers instead of 2", "v6_wind_q"),
                          ("v7_rain_p", "Observed rainfall at the station point instead of the 15 km mean", "v7_rain_p15"),
                          ("v9_fc1_h15", "HRRR rainfall as 6 hourly values, 15 km, instead of a 6 h total, 45 km", "v9_fc1_t45"),
                          ("v9_fc1_h45", "HRRR rainfall as 6 hourly values, 45 km", "v9_fc1_t45"),
                          ("v9_fc0_h15", "HRRR cycle issued at forecast time instead of 1 h earlier", "v9_fc1_t45"),
                          ("v7_rain_p15_hrrr1", "Model trained on observed rainfall, run with HRRR rainfall", "v6_wind_q_sameorig")]:
        a, b = pooled_nc(run, ref)
        rows.append((lab, f"{a:.2f}", f"{b:.2f}", False))
    y = 1.1
    for lab, a, b, bold in rows:
        text(sl, 0.5, y, 7.6, 0.3, lab, size=12, bold=bold); text(sl, 8.2, y, 2.4, 0.3, a, size=12, bold=bold, align=PP_ALIGN.RIGHT); text(sl, 10.7, y, 1.9, 0.3, b, size=12, bold=bold, align=PP_ALIGN.RIGHT)
        y += 0.42
    text(sl, 0.5, y + 0.2, 12.3, 1.6, [
        "Reference: the operational version for the first three rows and the last one; the rainfall version of the same kind for the others. Same stations in both columns.",
        "Separate models for tidal stations and for river stations were also trained and were not better than the single model on the same stations.",
        "Network size and the form of the inputs are not what limits the forecast. The limit is information the inputs do not contain: rainfall of the coming hours, and reservoir releases."], size=12)

    # ---- 5 how to read
    sl = new("How to read the station slides")
    text(sl, 0.5, 1.1, 12.3, 5.6, [
        "One station per slide. Five columns: five versions, left to right in the order they were built. Two rows: two 4-day periods from the test years.",
        "   Top row: the hurricane — Francine, 10 to 14 September 2024, in Louisiana; Beryl, 7 to 11 July 2024, in Texas.",
        "   Bottom row: the highest water level at that station outside the hurricane.",
        "",
        "Black: observed water level. Blue: every 6 hours each version issues a forecast for the next 1 to 6 hours; the line is that forecast and the dot is its last point, 6 hours ahead.",
        "A blue line that leaves the black line and ends far from it is a forecast that missed. The number in each panel is the RMSE of the dots in that period.",
        "Under the figure: the 6 h RMSE of each version at that station over the whole two test years.",
        "",
        "The fifth column uses the observed rainfall of the next 6 hours. It cannot be run in real time and shows how far a perfect rainfall forecast would go.",
        "",
        "Stations: 18, picked by type, with a complete record. A station is shown only if the observation and the inputs of all five versions have no missing hour in both periods.",
        "No USGS marsh station met that condition, so the marsh type is not shown.",
    ], size=13)

    # ---- station slides
    key2run = {k: r for k, r, _, _ in MAIN}
    xcol = [0.132, 0.306, 0.480, 0.654, 0.828]           # left edge of the five panel columns, fraction of the picture width
    sids = [f.stem[:-3] for f in sorted((F / "data").glob("*_fc.csv"))]
    sids.sort(key=lambda s: (TYPE_ORDER.index(scr.loc[s].type), scr.loc[s].domain, s))
    summary = []
    for sid in sids:
        r = scr.loc[sid]
        name = str(r["name"]).title() if str(r["name"]).isupper() else r["name"]
        sl = new(f"{TYPE_EN[r.type]}  —  {name}  ({r.source.replace('NOAA_COOPS', 'NOAA')} {sid}), {r.domain}")
        yb = picture(sl, F / f"station_{sid}.png", 0.3, 0.95, 12.7, 5.0)
        pic = sl.shapes[-1]; px, pw = pic.left / 914400, pic.width / 914400      # the picture is centred when its height is the limit
        vals = {k: float(per[run].loc[per[run].station_id == sid, "rmse_6h_cm"].iloc[0]) for k, run in key2run.items()}
        summary.append({"sid": sid, "type": r.type, **vals})
        text(sl, px - 0.15, yb + 0.12, 1.6, 0.5, ["Whole test period,", "6 h RMSE (cm)"], size=10.5, bold=True)
        for (k, _, _, _), xf in zip(MAIN, xcol):
            text(sl, px + pw * xf, yb + 0.17, 1.6, 0.35, f"{vals[k]:.1f}", size=14, bold=(k == "q"))
        d_wind = vals["wind"] - vals["wl"]; d_q = vals["q"] - vals["wind"]; d_fc = vals["rain_fc"] - vals["q"]; d_ob = vals["rain_obs"] - vals["q"]
        text(sl, 0.5, yb + 0.68, 12.3, 0.55,
             f"Step by step over the whole test period: wind {d_wind:+.1f} cm, discharge and wind refinements {d_q:+.1f} cm, HRRR rainfall {d_fc:+.1f} cm on top of the operational version; "
             f"observed rainfall would give {d_ob:+.1f} cm.", size=11.5)

    # ---- closing: by type and options
    sm = pd.DataFrame(summary)
    t = tab.set_index("run")
    sl = new("Where this leaves the choice")
    a0, a1, a2 = t.loc["v6_wind_q", "all"], t.loc["v9_fc1_t45", "all"], t.loc["v7_rain_p15", "all"]
    u0, u1, u2 = t.loc["v6_wind_q", "urban creek (Houston)"], t.loc["v9_fc1_t45", "urban creek (Houston)"], t.loc["v7_rain_p15", "urban creek (Houston)"]
    text(sl, 0.5, 1.05, 12.3, 6.0, [
        f"From water level only to the operational version: {t.loc['v3_obs','all']:.1f} to {a0:.1f} cm over all stations. Nearly all of it is wind, and it is at tide gauges, estuaries and lakes.",
        f"Rivers and urban creeks have barely moved: the typical urban creek is at {u0:.1f} cm, against {t.loc['v3_obs','urban creek (Houston)']:.1f} cm with water level only.",
        "",
        "Three ways forward:",
        "",
        f"A.  Keep the operational inputs (water level, wind, upstream discharge). Nothing new to maintain. All stations {a0:.1f} cm, urban creeks {u0:.1f} cm.",
        "",
        f"B.  Add rainfall with the HRRR forecast. All stations {a1:.1f} cm ({100 * (a1 / a0 - 1):+.0f}%), urban creeks {u1:.1f} cm ({100 * (u1 / u0 - 1):+.0f}%). "
        "Needs two more real-time feeds (a rainfall analysis for the past 72 h and the HRRR precipitation forecast) and one more training run "
        "so that tide gauges, estuaries and lakes keep the operational inputs and do not lose 0.1 cm.",
        "",
        f"C.  Look for a better rainfall forecast for the next 6 h (radar-based nowcast) before adding rainfall. With exact rainfall the same model reaches {a2:.1f} cm over all stations and {u2:.1f} cm at urban creeks; "
        "the distance between B and that number is rainfall-forecast error, not model error.",
        "",
        "B and C do not exclude each other: B can be put in place now and its rainfall source replaced later without changing the model.",
    ], size=13)

    out = F / "version_comparison.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = F / f"version_comparison_{datetime.date.today():%Y%m%d}.pptx"; prs.save(out)
    sm.round(2).to_csv(F / "stations_summary.csv", index=False)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
