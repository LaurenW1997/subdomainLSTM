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
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from slides_figures import picture, text
from versions_figs import CURRENT, MAIN, load_runs, pooled

REPO = Path(__file__).resolve().parents[2]
F = REPO / "deliverables" / "17_versions"
TYPE_ORDER = ["tide gauge", "estuary / tidal channel", "lake", "river / canal", "urban creek (Houston)"]
TYPE_EN = {"tide gauge": "Tide gauge", "estuary / tidal channel": "Estuary / tidal channel", "lake": "Lake", "river / canal": "River", "urban creek (Houston)": "Urban creek"}
WHAT = {"v3_obs": ("72 h of water level at the station", "yes"),
        "v3_wind_past": ("wind at the station, past 72 h", "yes (HRRR analysis)"),
        "v3_wind": ("wind for the 6 forecast hours", "yes (HRRR forecast)"),
        "v3_wind_q": ("discharge at the nearest upstream USGS gauge", "yes (USGS)"),
        "v6_wind_q": ("gauge on the same river; no wind at 15 inland rivers", "yes  -  previous version"),
        "v7_rain_p15_past": ("rainfall, 15 km around the station, past 72 h only", "yes (MRMS)"),
        "v9_fc1_t45": ("past rainfall + HRRR forecast total of the next 6 h", "yes (MRMS, HRRR)"),
        "v7_rain_p15": ("past rainfall + observed rainfall of the next 6 h", "NO  -  upper bound"),
        "v10_dnorm_x_p50": ("error scaled by 6 h change; gaps take the last value", "yes  -  no new data"),
        "v11_fc1_t45": ("the row above + past rainfall + HRRR forecast, next 6 h", "yes  -  CURRENT VERSION"),
        "v11_rain_obs": ("the row above + past and observed future rainfall", "NO  -  upper bound")}
SHORT = {"v3_obs": "Water level only", "v3_wind_past": "+ wind, past 72 h", "v3_wind": "+ wind, next 6 h", "v3_wind_q": "+ upstream discharge",
         "v6_wind_q": "refined discharge and wind (no rainfall)", "v7_rain_p15_past": "+ rainfall, past 72 h", "v9_fc1_t45": "+ rainfall, HRRR forecast",
         "v7_rain_p15": "+ rainfall, observed future", "v10_dnorm_x_p50": "6 h-change scaling + gap filling", "v11_fc1_t45": "scaling + gap filling + HRRR rainfall",
         "v11_rain_obs": "scaling + gap filling + observed rainfall"}
# additions tried on top of the current version: run, name, what it adds, real time
TRIED = [("v12_lb720", "look-back 720 h instead of 72 h", "30 days of history as input; training 9 times as long", "yes"),
         ("v12_long", "+ 7-day and 30-day summaries", "mean level and rainfall totals of the last 7 and 30 days", "yes"),
         ("v13_fc_ds_us", "+ gauges up- and downstream", "water level at the next gauges on the same river", "yes (USGS, NOAA)")]
HILITE = RGBColor(0xFB, 0xE3, 0xD3)


def hilite(sl, x, y, w, h):
    """Pale band behind the row / paragraph of the current version."""
    sh = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = HILITE; sh.line.fill.background(); sh.shadow.inherit = False
    return sh


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
    sl = new("Every model version so far; the current version is highlighted")
    cols = [(0.5, 3.05, "Version", PP_ALIGN.LEFT), (3.6, 3.7, "What it adds or changes", PP_ALIGN.LEFT), (7.35, 1.95, "Available in real time", PP_ALIGN.LEFT),
            (9.3, 1.1, "All stations", PP_ALIGN.RIGHT), (10.45, 1.1, "Urban creeks", PP_ALIGN.RIGHT), (11.6, 1.2, "Tide gauges", PP_ALIGN.RIGHT)]
    y = 0.95
    text(sl, 9.3, y - 0.05, 3.5, 0.3, "6 h RMSE (cm)", size=10, bold=True, align=PP_ALIGN.CENTER); y += 0.26
    for x, w, h, al in cols:
        text(sl, x, y, w, 0.3, h, size=10, bold=True, align=al)
    y += 0.33
    lines = [(r.run, SHORT[r.run], WHAT[r.run][0], WHAT[r.run][1], r["all"], r["urban creek (Houston)"], r["tide gauge"]) for _, r in tab.iterrows()]
    for run, name, what, rt in TRIED:
        x_ = load_runs(["v11_fc1_t45", run])[run]
        lines.append((run, name, what, rt, pooled(x_), float(x_.rmse_6h_cm[x_.type == "urban creek (Houston)"].median()), float(x_.rmse_6h_cm[x_.type == "tide gauge"].median())))
    for k, (run, name, what, rt, a_, u_, tg_) in enumerate(lines):
        if k in (5, 8, 11):
            y += 0.08                                        # blocks: built step by step / rainfall / scaling and gap filling / tried on top of the current version
        cur = run == CURRENT
        if cur:
            hilite(sl, 0.42, y - 0.01, 12.45, 0.29)
        for (x, w, _, al), v in zip(cols, [name, what, rt, f"{a_:.1f}", f"{u_:.1f}", f"{tg_:.1f}"]):
            text(sl, x, y, w, 0.3, v, size=10, bold=cur, align=al)
        y += 0.3
    text(sl, 0.5, y + 0.08, 12.3, 1.2, [
        "Highlighted: the current version. First block: each row keeps everything above it and adds one input; its last row is the previous version, which has no rainfall. Second block: rainfall added to the previous version. "
        "Third block: the previous version and the two rainfall versions again, with the error scaled by the 6 h change and gaps filled with the last observation (next slide). "
        "Fourth block: additions tried on top of the current version; none of them replaced it.",
        "Every rainfall row has the rainfall of the past 72 h as input; the rows differ in where the rainfall of the next 6 h comes from. In real time the past 72 h come from MRMS radar rainfall.",
        f"Test period January 2024 to December 2025, {n_st} stations with real-time data (USGS and NOAA; CRMS marsh stations are used for training only and are left out). "
        "All stations: RMSE over all forecasts. Urban creeks, tide gauges: the median station of that type. Same network in every row unless stated: 2-layer LSTM, hidden size 128, 72 h look-back, one model for all stations.",
    ], size=10)

    # ---- 2 the 6 h-change scaling and gap filling, explained
    sl = new("Same inputs as the previous version, trained differently: 6 h-change scaling and gap filling")
    b_b, b_w = count("base", "q")
    text(sl, 0.5, 1.0, 6.9, 6.1, [
        "Inputs: water level, wind, upstream discharge, as in the previous version (no rainfall yet). No new data source. Three things change:",
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
        "Example. Left: previous version. Right: same inputs with the three changes. At high river (bottom) the observed level is smooth; "
        "the 6 h forecast of the previous version (red-orange line) wanders several cm around it, the other one follows it. Whole test period: 4.8 to 2.5 cm.",
        "The current version is this one with rainfall added."], size=11)

    # ---- 3 bars
    sl = new("What each version does, by station type")
    picture(sl, F / "versions_bars.png", 0.3, 0.95, 12.7, 4.45)
    text(sl, 0.5, 5.45, 12.3, 1.6, [
        f"Wind helps the tidal types: tide gauges {t.loc['v3_obs','tide gauge']:.1f} to {t.loc['v3_wind','tide gauge']:.1f} cm, estuaries {t.loc['v3_obs','estuary / tidal channel']:.1f} to {t.loc['v3_wind','estuary / tidal channel']:.1f} cm, lakes {t.loc['v3_obs','lake']:.1f} to {t.loc['v3_wind','lake']:.1f} cm. Upstream discharge changes the medians by 0.1 cm or less.",
        f"The 6 h-change scaling and gap filling help rivers ({t.loc['v6_wind_q','river / canal']:.1f} to {t.loc['v10_dnorm_x_p50','river / canal']:.1f} cm) and do not cost the tidal types anything.",
        f"Rainfall helps urban creeks, and how much depends on where the rainfall of the next 6 h comes from: {t.loc['v6_wind_q','urban creek (Houston)']:.1f} cm without rainfall, "
        f"{t.loc['v11_fc1_t45','urban creek (Houston)']:.1f} cm in the current version (HRRR forecast, with scaling and gap filling; highlighted), {t.loc['v11_rain_obs','urban creek (Houston)']:.1f} cm if the rainfall were known exactly (grey bars, not available in real time).",
        "Without the scaling and gap filling, HRRR rainfall made rivers and tide gauges slightly worse; with them it does not.",
    ], size=11.5)

    # ---- 4 lead time
    sl = new("Error against lead time for the six main versions")
    picture(sl, F / "versions_lead.png", 0.5, 1.0, 12.3, 4.4)
    text(sl, 0.5, 5.6, 12.3, 1.4, [
        "Tide gauges: all versions with wind lie on one line, 0.7 cm below water level only at 6 h. Neither the scaling and gap filling nor rainfall changes them.",
        "Rivers: the 6 h-change scaling and gap filling lower the error at every lead; rainfall lowers it further.",
        f"Urban creeks: the versions separate after 2 h. In the current version (thick line) the error is {med('q','urban creek (Houston)') - med('base_fc','urban creek (Houston)'):.1f} cm below the previous version at 6 h; "
        f"with observed rainfall it would be {med('q','urban creek (Houston)') - med('base_obs','urban creek (Houston)'):.1f} cm below."], size=12)

    # ---- 5, 6 maps
    above = {k: int((v > 10).sum()) for k, v in r6.items()}
    sl = new("Station by station: 6 h RMSE of the six main versions")
    picture(sl, F / "versions_map_rmse.png", 0.3, 0.95, 12.7, 5.3)
    text(sl, 0.5, 6.3, 12.3, 0.8, [
        f"Stations above 10 cm: {above['wl']} with water level only, {above['q']} in the previous version, {above['base']} with 6 h-change scaling and gap filling, {above['base_fc']} in the current version (HRRR rainfall added), {above['base_obs']} with observed rainfall. "
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
                          ("v10_dnorm_x", "Error scaled all the way to the 6 h change instead of half-way (tide gauges 0.4 cm worse)", "v10_dnorm_x_p50"),
                          ("v12_lb720_e12", "Look-back 720 h (30 days) instead of 72 h; 12 training epochs each, training takes 9 times as long", "v12_lb72_e12"),
                          ("v12_long", "Mean level and rainfall total of the last 7 and 30 days as extra inputs", "v11_fc1_t45"),
                          ("v13_ds", "Water level at the next gauge downstream (or the nearest tide gauge) as input", "v10_dnorm_x_p50")]:
        a, b = pooled_nc(run, ref)
        rows.append((lab, f"{a:.2f}", f"{b:.2f}", False))
    y = 1.05
    for lab, a, b, bold in rows:
        text(sl, 0.5, y, 8.3, 0.3, lab, size=11.5, bold=bold); text(sl, 8.8, y, 2.2, 0.3, a, size=11.5, bold=bold, align=PP_ALIGN.RIGHT); text(sl, 11.0, y, 1.8, 0.3, b, size=11.5, bold=bold, align=PP_ALIGN.RIGHT)
        y += 0.33
    text(sl, 0.5, y + 0.12, 12.3, 1.6, [
        "Reference: the previous version for the first three rows and the eighth; the version of the same kind for the others (for the last three rows: the version with 6 h-change scaling and gap filling, with or without HRRR rainfall). Same stations in both columns.",
        "Separate models for tidal stations and for river stations were also trained and were not better than the single model on the same stations.",
        "Network size and the form of the inputs are not what limits the forecast. The limit is information the inputs do not contain: rainfall of the coming hours, and gate and reservoir operation.",
    ], size=11.5)

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
        "The fifth column, with its heading in bold, is the current version. The third is the previous version, without rainfall.",
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

    # ---- forecast lag and a second gauge on the same river
    mp = pd.read_csv(REPO / "config" / "station_downstream_map.csv", dtype=str).fillna("")
    has_us = set(mp.station_id[mp.us_station_id != ""])
    ref = load_runs(["v10_dnorm_x_p50", "v13_ds", "v13_ds_us", "v11_fc1_t45", "v13_fc_ds_us"])
    us = ref["v10_dnorm_x_p50"].station_id.isin(has_us).to_numpy()

    def cnt(a, b, sel):
        dd = ref[b].rmse_6h_cm.to_numpy()[sel] - ref[a].rmse_6h_cm.to_numpy()[sel]; return int((dd <= -0.5).sum()), int((dd >= 0.5).sum())

    lag = pd.read_csv(REPO / "deliverables" / "19_reference_gauge" / "lag_table.csv", dtype={"station_id": str})
    lus = lag[lag.upstream_ref != ""]
    sl = new("The 6 h forecast runs late: a gauge upstream helps at 127 stations, the lag stays on average")
    yb = picture(sl, F / "refgauge_08076700.png", 0.3, 1.0, 7.5, 4.95)
    text(sl, 0.3, yb + 0.1, 7.5, 1.3, [
        "The station with the largest gain: Greens Bayou at Ley Rd, with a gauge 11.5 km upstream on the same bayou. Here the 6 h forecast (red-orange) also rises earlier: "
        "its lag goes from 2 to 1 h during Beryl and from 4 to 2 h in May 2024. This station is the exception; over all stations with an upstream gauge the lag does not change."], size=11)
    bu, wu = cnt("v10_dnorm_x_p50", "v13_ds_us", us); br, wr = cnt("v11_fc1_t45", "v13_fc_ds_us", us)
    text(sl, 8.0, 1.0, 5.0, 6.1, [
        "On the station slides the 6 h forecast often follows the observation a few hours late. Tested: give the model the water level at the next gauge "
        "downstream (sees tide and surge first) and at the next gauge upstream (sees a flood wave first) on the same river.",
        "",
        f"6 h RMSE, all stations: {pooled(ref['v10_dnorm_x_p50']):.2f} cm without, {pooled(ref['v13_ds']):.2f} cm with the downstream gauge, "
        f"{pooled(ref['v13_ds_us']):.2f} cm with both. With HRRR rainfall: {pooled(ref['v11_fc1_t45']):.2f} to {pooled(ref['v13_fc_ds_us']):.2f} cm.",
        "",
        f"The gain is at the {int(us.sum())} stations that have a gauge upstream: {pooled(ref['v10_dnorm_x_p50'][us]):.1f} to {pooled(ref['v13_ds_us'][us]):.1f} cm, "
        f"{bu} better and {wu} worse by 0.5 cm or more (with HRRR rainfall {pooled(ref['v11_fc1_t45'][us]):.1f} to {pooled(ref['v13_fc_ds_us'][us]):.1f} cm, {br} better, {wr} worse). "
        "The downstream gauge alone changes nothing.",
        "",
        f"Lag of the 6 h forecast behind the observation, mean over {len(lag)} event periods at {lag.station_id.nunique()} stations: "
        f"{lag.lag_base.mean():.1f} h without, {lag.lag_ds.mean():.1f} h with the downstream gauge, {lag.lag_ds_us.mean():.1f} h with both. "
        f"At the stations with an upstream gauge: {lus.lag_base.mean():.1f} h and {lus.lag_ds_us.mean():.1f} h. Mississippi at Baton Rouge during Francine: 3 h in all three.",
        "",
        "On average the upstream gauge improves the height of the forecast, not its timing. The lag comes from what has not happened yet at forecast time: "
        "with the observed rainfall of the next 6 h as input, the lag at the urban creeks drops from 4-5 h to nearly zero.",
        "",
        "Lag: the shift, 0 to 8 h, at which the forecast fits the observation best.",
    ], size=11.5)

    # ---- rainfall inputs in real time
    pr = load_runs(["v11_fc1_t45_pastaorc", "v11_fc1_t45_pastmrms", "v11_fc1_t45_pasthrrr", "v11_fc1_t45_pastnone"])
    sl = new("Rainfall in real time: where the two rainfall inputs come from")
    rows = [("Rainfall of the past 72 h taken from", "Available in real time", "All stations", "Urban creeks", "Stations worse", True)]
    for run, lab, rt in [("v11_fc1_t45_pastaorc", "AORC reanalysis (used for training)", "no"),
                         ("v11_fc1_t45_pastmrms", "MRMS radar and gauge analysis, 1 km", "yes, 16 min after the hour"),
                         ("v11_fc1_t45_pasthrrr", "HRRR short-range forecast, 1 to 6 h lead", "yes"),
                         ("v11_fc1_t45_pastnone", "No rainfall of the past 72 h", "-")]:
        x = pr[run]; dd = x.rmse_6h_cm.to_numpy() - pr["v11_fc1_t45_pastaorc"].rmse_6h_cm.to_numpy()
        rows.append((lab, rt, f"{pooled(x):.2f}", f"{x.rmse_6h_cm[x.type == 'urban creek (Houston)'].median():.1f}",
                     "-" if run.endswith("aorc") else f"{int((dd >= 0.5).sum())} of {len(x)}", False))
    y = 1.05
    text(sl, 7.6, y - 0.05, 3.2, 0.3, "6 h RMSE (cm)", size=12, bold=True, align=PP_ALIGN.CENTER); y += 0.3
    for lab, rt, a_, u_, w_, bold in rows:
        text(sl, 0.5, y, 4.4, 0.3, lab, size=12, bold=bold); text(sl, 4.9, y, 2.8, 0.3, rt, size=12, bold=bold)
        text(sl, 7.6, y, 1.5, 0.3, a_, size=12, bold=bold, align=PP_ALIGN.RIGHT); text(sl, 9.2, y, 1.6, 0.3, u_, size=12, bold=bold, align=PP_ALIGN.RIGHT)
        text(sl, 10.9, y, 1.9, 0.3, w_, size=12, bold=bold, align=PP_ALIGN.RIGHT)
        y += 0.4
    text(sl, 0.5, y + 0.2, 12.3, 3.6, [
        "The same trained model (the current version) in every row; only the source of the past rainfall is changed, without retraining. "
        "Stations worse: by 0.5 cm or more than with the training product.",
        "",
        "Past 72 h. The model was trained with AORC, which is not produced in real time. MRMS replaces it at almost no cost: hourly correlation with AORC 0.93 over the two test years, "
        "3 hours missing in two years. A short-range HRRR forecast does not: hourly correlation 0.33, and half of the gain from rainfall is lost. "
        "The forecast script therefore uses MRMS and falls back to HRRR only for hours MRMS does not have.",
        "",
        "Next 6 h. HRRR precipitation forecast, the cycle issued 1 h before forecast time, total of the 45 km around the station - exactly as in training.",
        "",
        "HRRR is still produced. NWS replaced NAM by RRFS on 3 November 2026 and intends RRFS to replace HRRR later; when that is announced, the next-6 h rainfall "
        "input has to be retrained with RRFS forecasts, and an archive of them has to be collected first.",
    ], size=12)

    # ---- the current version run as a real-time forecast
    import json
    hc = pd.read_csv(REPO / "deliverables" / "20_operational_rain" / "hindcast_check_summary.csv").set_index("cycles")
    ver = json.loads((REPO / "deliverables" / "20_operational_rain" / "20261111T20_verification.json").read_text())["leads"]
    sl = new("The current version run as a real-time forecast")
    ev = [("all cycles", "All 32 cycles"), ("2024-05", "Flood, 2 to 3 May 2024"), ("2024-07", "Hurricane Beryl, 8 to 9 July 2024"),
          ("2024-09", "Hurricane Francine, 11 to 12 September 2024"), ("2025-10", "Calm period, 10 to 11 October 2025")]
    cx = [(0.5, 4.6, PP_ALIGN.LEFT), (5.2, 1.8, PP_ALIGN.RIGHT), (7.1, 1.8, PP_ALIGN.RIGHT), (9.1, 1.8, PP_ALIGN.RIGHT), (11.0, 1.8, PP_ALIGN.RIGHT)]
    y = 1.0
    text(sl, 5.2, y, 3.7, 0.3, "Previous version (no rainfall)", size=12, bold=True, align=PP_ALIGN.CENTER)
    hilite(sl, 9.05, y - 0.02, 3.8, 2.75)
    text(sl, 9.1, y, 3.7, 0.3, "Current version", size=12, bold=True, align=PP_ALIGN.CENTER); y += 0.33
    for (x, w, al), h in zip(cx, ["6 h RMSE (cm)", "training inputs", "real-time inputs", "training inputs", "real-time inputs"]):
        text(sl, x, y, w, 0.3, h, size=12, bold=True, align=al)
    y += 0.4
    for key, lab in ev:
        r = hc.loc[key]
        for (x, w, al), v in zip(cx, [lab, f"{r['old data 6h']:.1f}", f"{r['old live 6h']:.1f}", f"{r['new data 6h']:.1f}", f"{r['new live 6h']:.1f}"]):
            text(sl, x, y, w, 0.3, v, size=12, bold=(key == "all cycles"), align=al)
        y += 0.38
    ra = hc.loc["all cycles"]
    text(sl, 0.5, y + 0.25, 12.3, 3.4, [
        f"The forecast script was run for 32 past forecast times with the inputs the real-time system would have had: water level and discharge from the USGS and NOAA services, HRRR wind, "
        f"MRMS rainfall for the past 72 h, HRRR rainfall forecast for the next 6 h. {int(ra['pairs']):,} forecasts at 447 stations, scored against the observations. "
        "Training inputs: the same model fed from the training dataset (AORC wind and rainfall), same stations and times.",
        "",
        f"Real-time inputs cost the current version {100 * (ra['new live 6h'] / ra['new data 6h'] - 1):.1f}% (lead 1 h: {ra['new data 1h']:.1f} and {ra['new live 1h']:.1f} cm; 3 h: {ra['new data 3h']:.1f} and {ra['new live 3h']:.1f} cm). "
        f"With real-time inputs the current version is {100 * (1 - ra['new live 6h'] / ra['old live 6h']):.0f}% below the previous version. "
        "The forecast times are floods and hurricanes by choice, so the numbers are much larger than the whole-period RMSE on the other slides.",
        "",
        f"One live forecast, 11 November 2026, 20:00 UTC: 418 stations, under a minute. Scored afterwards: RMSE {ver['1']['rmse_cm']:.1f} cm at 1 h, {ver['3']['rmse_cm']:.1f} cm at 3 h, {ver['6']['rmse_cm']:.1f} cm at 6 h "
        "(one forecast during a recession after rain, not a statistic).",
        "",
        "A fault found by this check and fixed: during daylight-saving time the USGS service returned data ending one hour before the requested time, so the newest hour was averaged from half of its readings "
        "(too low by tens of cm on a fast rise). The numbers above are after the fix. Training data were not affected.",
    ], size=12)

    # ---- closing: where things stand
    sl = new("Where things stand")
    a0, a1, a2, a3 = t.loc["v6_wind_q", "all"], t.loc["v10_dnorm_x_p50", "all"], t.loc["v11_fc1_t45", "all"], t.loc["v11_rain_obs", "all"]
    u0, u1, u2, u3 = (t.loc[x, "urban creek (Houston)"] for x in ("v6_wind_q", "v10_dnorm_x_p50", "v11_fc1_t45", "v11_rain_obs"))
    text(sl, 0.5, 1.0, 12.3, 2.9, [
        f"From water level only to the previous version (water level, wind, discharge): {t.loc['v3_obs','all']:.1f} to {a0:.1f} cm over all stations, nearly all of it from wind and at tide gauges, estuaries and lakes.",
        "",
        "Three options were compared:",
        f"A.  Keep the previous version, without rainfall. All stations {a0:.1f} cm, urban creeks {u0:.1f} cm.",
        f"B.  Same inputs, with 6 h-change scaling and gap filling. All stations {a1:.1f} cm ({100 * (a1 / a0 - 1):+.0f}%); large rivers much better (Mississippi at Baton Rouge 4.8 to 2.5 cm); "
        f"{b2} stations better, {w2} worse; urban creeks {u1:.1f} cm. No new data.",
        f"C.  B with rainfall: MRMS for the past 72 h, HRRR forecast for the next 6 h. All stations {a2:.1f} cm ({100 * (a2 / a0 - 1):+.0f}%), urban creeks {u2:.1f} cm ({100 * (u2 / u0 - 1):+.0f}%); {b3} stations better, {w3} worse.",
    ], size=12)
    hilite(sl, 0.42, 3.05, 12.45, 0.62)
    text(sl, 0.5, 3.09, 12.3, 0.6, [
        "Current version: C. The forecast script builds all of its inputs in real time and has been checked on 32 past forecast times and one live forecast (previous slide). "
        "It is run from a separate directory and is not connected to the group's forecast website."], size=12, bold=True)
    st_ = pd.read_csv(REPO / "runs" / "v11_fc1_t45" / "stale_origin.csv")
    so = st_[(st_.group == "all") & (st_.lead_h == 6)].set_index("hours_without_data").rmse_cm
    text(sl, 0.5, 3.95, 12.3, 2.5, [
        f"With exact rainfall the same model reaches {a3:.1f} cm over all stations and {u3:.1f} cm at urban creeks. The distance between the current version and that number is rainfall-forecast error, not model error: "
        "a better short-range rainfall forecast (radar-based nowcast) can replace HRRR later without changing the model.",
        "",
        "Open points:",
        f"1.  When a gauge has not reported for the newest hour the forecast gets much worse: 6 h RMSE {so[0]:.1f} cm with complete input, {so[1]:.1f} cm with 1 h missing, {so[3]:.1f} cm with 3 h missing. "
        "The model has hardly seen this case in training; it can be trained with such gaps.",
        "2.  Rainfall should be switched off at gate-controlled stations such as the Pearl River locks, where it misleads the model.",
        "3.  HRRR will be replaced by RRFS at a date not yet announced; the next-6 h rainfall input then has to be retrained with RRFS forecasts.",
    ], size=12)

    out = F / "version_comparison.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = F / f"version_comparison_{datetime.date.today():%Y%m%d}.pptx"; prs.save(out)
    pd.DataFrame(summary).round(2).to_csv(F / "stations_summary.csv", index=False)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
