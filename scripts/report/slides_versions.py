"""Slide deck comparing every model version side by side (deliverable 17): white background, black Times New Roman,
no title page.

Reads deliverables/17_versions/{versions_table.csv, versions_bars.png, versions_lead.png, versions_map_*.png,
station_<id>.png, data/*.csv} (from versions_figs.py) and runs/*/per_station_test.csv.
Writes deliverables/17_versions/version_comparison.pptx.
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
        "v7_rain_p15": ("observed rainfall of the next 6 h", "NO  —  upper bound"),
        "v10_dnorm_x_p50": ("error scaled by 6 h change; gaps take last observation", "yes  —  no new data"),
        "v11_fc1_t45": ("the row above with the HRRR rainfall forecast", "yes (HRRR forecast)"),
        "v11_rain_obs": ("the row above with observed rainfall instead", "NO  —  upper bound")}
SHORT = {"v3_obs": "Water level only", "v3_wind_past": "+ wind, past 72 h", "v3_wind": "+ wind, next 6 h", "v3_wind_q": "+ upstream discharge",
         "v6_wind_q": "refined discharge and wind", "v7_rain_p15_past": "+ rainfall, past 72 h", "v9_fc1_t45": "+ rainfall, HRRR forecast",
         "v7_rain_p15": "+ rainfall, observed future", "v10_dnorm_x_p50": "6 h-change scaling + gap filling", "v11_fc1_t45": "scaling + gap filling + HRRR rainfall",
         "v11_rain_obs": "scaling + gap filling + observed rainfall"}


def pooled_nc(run: str, ref: str = "v6_wind_q") -> tuple[float, float]:
    """6 h RMSE pooled over operational stations for a run and for the reference on the same stations."""
    d = load_runs([ref, run]); return pooled(d[run]), pooled(d[ref])


def main() -> None:
    tab = pd.read_csv(F / "versions_table.csv")
    t = tab.set_index("run")
    scr = pd.read_csv(F / "data" / "station_screen.csv", dtype={"station_id": str}).set_index("station_id")
    per = load_runs([r for _, r, _, _ in MAIN])
    key2run = {k: r for k, r, _, _ in MAIN}
    r6 = {k: per[run].rmse_6h_cm.to_numpy() for k, run in key2run.items()}
    typ = per["v3_obs"].type.to_numpy()
    std = pd.read_csv(REPO / "runs" / "v6_wind_q" / "stations.csv", dtype={"station_id": str}).set_index("station_id").std_m
    big = per["v3_obs"].station_id.map(std).to_numpy() > 1.5            # rivers whose level ranges over metres
    n_st = int(tab.n_stations.iloc[0])
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]
    n = 0

    def new(title):
        nonlocal n
        n += 1; sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=17, bold=True)
        text(sl, 12.5, 7.05, 0.6, 0.3, str(n), size=10, align=PP_ALIGN.RIGHT)
        return sl

    def count(a, b):
        dd = r6[a] - r6[b]; return int((dd <= -0.5).sum()), int((dd >= 0.5).sum())

    def med(key, tname):
        return float(np.median(r6[key][typ == tname]))

    # ---- 1 the versions as a table
    sl = new("Every model version so far")
    cols = [(0.5, 3.05, "Version", PP_ALIGN.LEFT), (3.6, 3.7, "What it adds or changes", PP_ALIGN.LEFT), (7.35, 1.95, "Available in real time", PP_ALIGN.LEFT),
            (9.3, 1.1, "All stations", PP_ALIGN.RIGHT), (10.45, 1.1, "Urban creeks", PP_ALIGN.RIGHT), (11.6, 1.2, "Tide gauges", PP_ALIGN.RIGHT)]
    y = 1.0
    text(sl, 9.3, y - 0.05, 3.5, 0.3, "6 h RMSE (cm)", size=10.5, bold=True, align=PP_ALIGN.CENTER); y += 0.27
    for x, w, h, al in cols:
        text(sl, x, y, w, 0.3, h, size=10.5, bold=True, align=al)
    y += 0.36
    for k, (_, r) in enumerate(tab.iterrows()):
        if k in (5, 8):
            y += 0.1                                         # blocks: built step by step / rainfall / scaling and gap filling
        op = r.run == "v6_wind_q"
        vals = [SHORT[r.run], WHAT[r.run][0], WHAT[r.run][1], f"{r['all']:.1f}", f"{r['urban creek (Houston)']:.1f}", f"{r['tide gauge']:.1f}"]
        for (x, w, _, al), v in zip(cols, vals):
            text(sl, x, y, w, 0.3, v, size=10.5, bold=op, align=al)
        y += 0.35
    text(sl, 0.5, y + 0.12, 12.3, 1.2, [
        "First block: each row keeps everything above it and adds one input; the last row of the block is the operational version. Second block: rainfall added to the operational version. "
        "Third block: the operational version and the two rainfall versions again, with the error scaled by the 6 h change and gaps filled with the last observation (next slide).",
        f"Test period January 2024 to December 2025, {n_st} operational stations (USGS and NOAA; CRMS marsh stations are used for training only and are left out). "
        "All stations: RMSE over all forecasts. Urban creeks, tide gauges: the median station of that type. Same network in every row: 2-layer LSTM, hidden size 128, 72 h look-back, one model for all stations.",
    ], size=10.5)

    # ---- 2 the 6 h-change scaling and gap filling, explained
    sl = new("Same inputs as the operational version, trained differently: 6 h-change scaling and gap filling")
    b_b, b_w = count("base", "q")
    text(sl, 0.5, 1.0, 6.9, 6.1, [
        "Inputs: water level, wind, upstream discharge, as in the operational version. No new data source. Three things change:",
        "",
        "1.  Gap filling. A missing hour in the input used to be replaced by the station's long-term mean level; it now takes the last valid observation. "
        "When the newest hour was missing, the forecast could be off by 0.5 to 1 m: at Baton Rouge the mean is 6.8 m and the river stood at 2.8 m.",
        "",
        "2.  6 h-change scaling. The error at each station used to be measured against the spread of its water level over the years. "
        "At Baton Rouge that spread is 3.3 m, so a 5 cm error counted as next to nothing and the model did not learn the small movements. "
        "The error is now measured half-way towards the spread of the 6 h change: 4.9 cm at Baton Rouge, 18 cm at a typical tide gauge (level spread 21 cm, so little changes there).",
        "",
        "3.  A second view of the water level as input: the last 72 h relative to the newest hour, in the same unit, so that small movements at large rivers are visible to the network.",
        "",
        f"6 h RMSE: all stations {t.loc['v6_wind_q','all']:.1f} to {t.loc['v10_dnorm_x_p50','all']:.1f} cm; the {int(big.sum())} rivers whose level ranges over metres, median "
        f"{np.median(r6['q'][big]):.1f} to {np.median(r6['base'][big]):.1f} cm. {b_b} stations better, {b_w} worse by 0.5 cm or more; "
        f"tide gauges {med('q','tide gauge'):.1f} to {med('base','tide gauge'):.1f} cm.",
        "",
        "Scaling all the way to the 6 h change gives the same overall number but makes tide gauges 0.4 cm worse; half-way keeps the gain at the rivers without that cost.",
    ], size=11.5)
    yb = picture(sl, F / "explain_scaling.png", 7.6, 1.0, 5.4, 4.6)
    text(sl, 7.6, yb + 0.1, 5.4, 1.4, [
        "Example. Left: operational version. Right: same inputs with the three changes. At high river (bottom) the observed level is smooth; "
        "the operational 6 h forecast (red-orange line) wanders several cm around it, the other one follows it. Whole test period: 4.8 to 2.5 cm.",
        "On the following slides this version is labelled \"6 h-change scaling + gap filling\"."], size=11)

    # ---- 3 bars
    sl = new("What each version does, by station type")
    picture(sl, F / "versions_bars.png", 0.3, 0.95, 12.7, 4.45)
    text(sl, 0.5, 5.45, 12.3, 1.6, [
        f"Wind helps the tidal types: tide gauges {t.loc['v3_obs','tide gauge']:.1f} to {t.loc['v3_wind','tide gauge']:.1f} cm, estuaries {t.loc['v3_obs','estuary / tidal channel']:.1f} to {t.loc['v3_wind','estuary / tidal channel']:.1f} cm, lakes {t.loc['v3_obs','lake']:.1f} to {t.loc['v3_wind','lake']:.1f} cm. Upstream discharge changes the medians by 0.1 cm or less.",
        f"The 6 h-change scaling and gap filling help rivers ({t.loc['v6_wind_q','river / canal']:.1f} to {t.loc['v10_dnorm_x_p50','river / canal']:.1f} cm) and do not cost the tidal types anything.",
        f"Rainfall helps urban creeks, and how much depends on where the rainfall of the next 6 h comes from: {t.loc['v6_wind_q','urban creek (Houston)']:.1f} cm without rainfall, "
        f"{t.loc['v11_fc1_t45','urban creek (Houston)']:.1f} cm with the HRRR forecast (with scaling and gap filling), {t.loc['v11_rain_obs','urban creek (Houston)']:.1f} cm if the rainfall were known exactly (grey bars, not available in real time).",
        "Without the scaling and gap filling, HRRR rainfall made rivers and tide gauges slightly worse; with them it does not.",
    ], size=11.5)

    # ---- 4 lead time
    sl = new("Error against lead time for the six main versions")
    picture(sl, F / "versions_lead.png", 0.5, 1.0, 12.3, 4.4)
    text(sl, 0.5, 5.6, 12.3, 1.4, [
        "Tide gauges: all versions with wind lie on one line, 0.7 cm below water level only at 6 h. Neither the scaling and gap filling nor rainfall changes them.",
        "Rivers: the 6 h-change scaling and gap filling lower the error at every lead; rainfall lowers it further.",
        f"Urban creeks: the versions separate after 2 h. With scaling, gap filling and HRRR rainfall the error is {med('q','urban creek (Houston)') - med('base_fc','urban creek (Houston)'):.1f} cm below the operational version at 6 h; "
        f"with observed rainfall it would be {med('q','urban creek (Houston)') - med('base_obs','urban creek (Houston)'):.1f} cm below."], size=12)

    # ---- 5, 6 maps
    above = {k: int((v > 10).sum()) for k, v in r6.items()}
    sl = new("Station by station: 6 h RMSE of the six main versions")
    picture(sl, F / "versions_map_rmse.png", 0.3, 0.95, 12.7, 5.3)
    text(sl, 0.5, 6.3, 12.3, 0.8, [
        f"Stations above 10 cm: {above['wl']} with water level only, {above['q']} in the operational version, {above['base']} with 6 h-change scaling and gap filling, {above['base_fc']} with HRRR rainfall added, {above['base_obs']} with observed rainfall. "
        "The dark stations sit in the same two places in every map: the Houston creeks and the small rivers north and east of Baton Rouge."], size=12)

    sl = new("Station by station: what each step changed")
    picture(sl, F / "versions_map_change.png", 0.3, 1.0, 8.6, 5.9)
    b1, w1 = count("q", "wl"); b2, w2 = count("base", "q"); b3, w3 = count("base_fc", "q"); b4, w4 = count("base_obs", "q")
    text(sl, 9.1, 1.05, 3.9, 5.9, [
        f"(a) Wind and discharge: {b1} stations better, {w1} worse. The gain follows the coast and the bays.",
        "",
        f"(b) 6 h-change scaling and gap filling: {b2} better, {w2} worse. The gain is at inland rivers; the coast does not change.",
        "",
        f"(c) The same with HRRR rainfall: {b3} better, {w3} worse. The gain is in Houston and around Baton Rouge, where the rain-fed creeks are. "
        "The two dark orange stations are Pearl River navigation locks, where gate operation sets the level and rainfall only misleads the model.",
        "",
        f"(d) The same with observed rainfall: {b4} better, {w4} worse. Same places as (c), several times stronger. The difference between (c) and (d) is the error of the rainfall forecast.",
        "",
        "Colour scale limited to 5 cm in both directions.",
    ], size=12)

    # ---- 7 tried and set aside
    sl = new("Also tried: changes that made no measurable difference")
    rows = [("Change", "6 h RMSE, all stations (cm)", "Reference (cm)", True)]
    for run, lab, ref in [("v6_lb168", "Look-back 168 h instead of 72 h", "v6_wind_q"), ("v6_lb336", "Look-back 336 h instead of 72 h", "v6_wind_q"),
                          ("v6_l3", "3 LSTM layers instead of 2", "v6_wind_q"),
                          ("v7_rain_p", "Observed rainfall at the station point instead of the 15 km mean", "v7_rain_p15"),
                          ("v9_fc1_h15", "HRRR rainfall as 6 hourly values, 15 km, instead of a 6 h total, 45 km", "v9_fc1_t45"),
                          ("v9_fc1_h45", "HRRR rainfall as 6 hourly values, 45 km", "v9_fc1_t45"),
                          ("v9_fc0_h15", "HRRR cycle issued at forecast time instead of 1 h earlier", "v9_fc1_t45"),
                          ("v7_rain_p15_hrrr1", "Model trained on observed rainfall, run with HRRR rainfall", "v6_wind_q_sameorig"),
                          ("v10_dnorm_x", "Error scaled all the way to the 6 h change instead of half-way (tide gauges 0.4 cm worse)", "v10_dnorm_x_p50")]:
        a, b = pooled_nc(run, ref)
        rows.append((lab, f"{a:.2f}", f"{b:.2f}", False))
    y = 1.05
    for lab, a, b, bold in rows:
        text(sl, 0.5, y, 7.9, 0.3, lab, size=12, bold=bold); text(sl, 8.4, y, 2.4, 0.3, a, size=12, bold=bold, align=PP_ALIGN.RIGHT); text(sl, 10.9, y, 1.9, 0.3, b, size=12, bold=bold, align=PP_ALIGN.RIGHT)
        y += 0.4
    text(sl, 0.5, y + 0.15, 12.3, 1.6, [
        "Reference: the operational version for the first three rows and the eighth; the version of the same kind for the others. Same stations in both columns.",
        "Separate models for tidal stations and for river stations were also trained and were not better than the single model on the same stations.",
        "Network size and the form of the inputs are not what limits the forecast. The limit is information the inputs do not contain: rainfall of the coming hours, and gate and reservoir operation.",
    ], size=12)

    # ---- 8 how to read
    sl = new("How to read the station slides")
    text(sl, 0.5, 1.1, 12.3, 5.6, [
        "One station per slide. Six columns: six versions, left to right. Two rows: two 4-day periods from the test years.",
        "   Top row: the hurricane — Francine, 10 to 14 September 2024, in Louisiana; Beryl, 7 to 11 July 2024, in Texas.",
        "   Bottom row: the highest water level at that station outside the hurricane.",
        "",
        "Black: observed water level. Orange lines, pale to vivid: the forecast valid at each hour that was issued 1, 3 and 6 hours earlier. A forecast is issued every hour.",
        "A red-orange line that follows the black line a few hours late means the version only reacts once the rise is already in the observations. Grey band: 24 hours around the observed peak. Numbers inside each panel: RMSE in that period at 1, 3 and 6 hours lead.",
        "Above each column: the 6 h RMSE of that version at the station over the whole two test years.",
        "",
        "The sixth column uses the observed rainfall of the next 6 hours. It cannot be run in real time and shows how far a perfect rainfall forecast would go.",
        "",
        "Stations: 18, picked by type, with a complete record. A station is shown only if the observation and the inputs of all six versions have no missing hour in both periods.",
        "No USGS marsh station met that condition, so the marsh type is not shown.",
    ], size=13)

    # ---- station slides
    sids = [f.stem[:-3] for f in sorted((F / "data").glob("*_fc.csv"))]
    sids.sort(key=lambda s: (TYPE_ORDER.index(scr.loc[s].type), scr.loc[s].domain, s))
    summary = []
    for sid in sids:
        r = scr.loc[sid]
        name = str(r["name"]).title() if str(r["name"]).isupper() else r["name"]
        sl = new(f"{TYPE_EN[r.type]}  —  {name}  ({r.source.replace('NOAA_COOPS', 'NOAA')} {sid}), {r.domain}")
        yb = picture(sl, F / f"station_{sid}.png", 0.3, 0.95, 12.7, 5.35)
        vals = {k: float(per[run].loc[per[run].station_id == sid, "rmse_6h_cm"].iloc[0]) for k, run in key2run.items()}
        summary.append({"sid": sid, "type": r.type, **vals})
        text(sl, 0.5, yb + 0.12, 12.3, 0.6,
             f"Whole test period, step by step: wind {vals['wind'] - vals['wl']:+.1f} cm; discharge and wind refinements {vals['q'] - vals['wind']:+.1f} cm; "
             f"6 h-change scaling and gap filling {vals['base'] - vals['q']:+.1f} cm; HRRR rainfall on top of that {vals['base_fc'] - vals['base']:+.1f} cm "
             f"(observed rainfall would give {vals['base_obs'] - vals['base']:+.1f} cm).", size=11.5)

    # ---- closing: options
    sl = new("Where this leaves the choice")
    a0, a1, a2, a3 = t.loc["v6_wind_q", "all"], t.loc["v10_dnorm_x_p50", "all"], t.loc["v11_fc1_t45", "all"], t.loc["v11_rain_obs", "all"]
    u0, u1, u2, u3 = (t.loc[x, "urban creek (Houston)"] for x in ("v6_wind_q", "v10_dnorm_x_p50", "v11_fc1_t45", "v11_rain_obs"))
    text(sl, 0.5, 1.05, 12.3, 6.0, [
        f"From water level only to the operational version: {t.loc['v3_obs','all']:.1f} to {a0:.1f} cm over all stations, nearly all of it from wind and at tide gauges, estuaries and lakes.",
        "",
        "Three ways forward:",
        "",
        f"A.  Keep the operational version. Nothing to change. All stations {a0:.1f} cm, urban creeks {u0:.1f} cm.",
        "",
        f"B.  Same inputs, with 6 h-change scaling and gap filling. All stations {a1:.1f} cm ({100 * (a1 / a0 - 1):+.0f}%); large rivers much better (Mississippi at Baton Rouge 4.8 to 2.5 cm); "
        f"{b2} stations better, {w2} worse; urban creeks {u1:.1f} cm. No new data. The model file is replaced and the forecast script has to fill gaps and build the extra input the same way.",
        "",
        f"C.  B with HRRR rainfall added. All stations {a2:.1f} cm ({100 * (a2 / a0 - 1):+.0f}%), urban creeks {u2:.1f} cm ({100 * (u2 / u0 - 1):+.0f}%); {b3} stations better, {w3} worse. "
        "Needs two more real-time feeds: a rainfall analysis for the past 72 h and the HRRR precipitation forecast. Rainfall should be switched off at gate-controlled stations such as the Pearl River locks.",
        "",
        f"With exact rainfall the same model reaches {a3:.1f} cm over all stations and {u3:.1f} cm at urban creeks. The distance between C and that number is rainfall-forecast error, not model error: "
        "a better short-range rainfall forecast (radar-based nowcast) can replace HRRR later without changing the model.",
        "",
        "B is contained in C, so B can be put in place first and rainfall added afterwards.",
    ], size=13)

    out = F / "version_comparison.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = F / f"version_comparison_{datetime.date.today():%Y%m%d}.pptx"; prs.save(out)
    pd.DataFrame(summary).round(2).to_csv(F / "stations_summary.csv", index=False)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
