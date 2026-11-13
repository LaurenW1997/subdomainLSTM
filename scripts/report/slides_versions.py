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
        "v6_wind_q": ("gauge on the same river; no wind at 15 inland rivers", "yes"),
        "v7_rain_p15_past": ("rainfall, 15 km around the station, past 72 h only", "yes (MRMS)"),
        "v9_fc1_t45": ("past rainfall + HRRR forecast total of the next 6 h", "yes (MRMS, HRRR)"),
        "v7_rain_p15": ("past rainfall + observed rainfall of the next 6 h", "NO  -  upper bound"),
        "v10_dnorm_x_p50": ("error scaled by 6 h change; gaps take the last value", "yes  -  no new data"),
        "v11_fc1_t45": ("past rainfall + HRRR forecast total of the next 6 h", "yes (MRMS, HRRR)"),
        "v14_stale25": ("newest 1-3 h of level removed in 25% of samples", "yes (MRMS, HRRR)"),
        "v15r_mean5": ("five such models, random seeds 0 to 4, forecasts averaged", "yes (MRMS, HRRR)"),
        "v11_rain_obs": ("past rainfall + observed rainfall of the next 6 h", "NO  -  upper bound")}
SHORT = {"v3_obs": "Water level only", "v3_wind_past": "+ wind, past 72 h", "v3_wind": "+ wind, next 6 h", "v3_wind_q": "+ upstream discharge",
         "v6_wind_q": "refined discharge and wind (no rainfall)", "v7_rain_p15_past": "+ rainfall, past 72 h", "v9_fc1_t45": "+ rainfall, HRRR forecast",
         "v7_rain_p15": "+ rainfall, observed future", "v10_dnorm_x_p50": "6 h-change scaling + gap filling", "v11_fc1_t45": "scaling + gap filling + HRRR rainfall", "v14_stale25": "scaling + gap filling + HRRR rainfall,\ntrained with missing hours",
         "v15r_mean5": "scaling + gap filling + HRRR rainfall,\ntrained with missing hours, mean of 5 models",
         "v11_rain_obs": "scaling + gap filling + observed rainfall"}
# additions tried on top of the current version: run, name, what it adds, real time
TRIED = [("v12_lb720", "look-back 720 h instead of 72 h", "30 days of history as input; training 9 times as long", "yes"),
         ("v12_long", "+ 7-day and 30-day summaries", "mean level and rainfall totals of the last 7 and 30 days", "yes"),
         ("v13_fc_ds_us", "+ gauges up- and downstream", "water level at the next gauges on the same river", "yes (USGS, NOAA)")]
HILITE = RGBColor(0xFB, 0xE3, 0xD3)
LIVE_TAG, LIVE_WHEN = "20261112T12_mean_of_5", "12 November 2026, 12:00 UTC"
LIVE_STATIONS = ["8771450", "8747437", "08116850", "08072050", "07387040", "08164503", "08117500", "08115000"]      # the eight drawn by live_cycle_figs.py
SEEDS = ["v14_stale25", "v15r_seed1", "v15r_seed2", "v15r_seed3", "v15r_seed4"]                                      # the five members of the mean


def hilite(sl, x, y, w, h):
    """Pale band behind the row / paragraph of the current version."""
    sh = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = HILITE; sh.line.fill.background(); sh.shadow.inherit = False
    return sh


def pooled_nc(run: str, ref: str = "v6_wind_q") -> tuple[float, float]:
    """6 h RMSE pooled over operational stations for a run and for the reference on the same stations."""
    d = load_runs([ref, run]); return pooled(d[run]), pooled(d[ref])


STORM_TITLE = "In the hurricanes: better overall, but too high at some stations"


def storm_slide(sl) -> None:
    """Body of the slide that compares the versions station by station in the hurricane periods (runs/<run>/storm_station.csv,
    eval_storm_station.py). Module level so that it can also be added to a deck that was edited by hand."""
    def rd(r):
        return pd.read_csv(REPO / "runs" / r / "storm_station.csv", dtype={"station_id": str}).set_index(["source", "station_id"])

    def pooled_(x):
        return float(np.sqrt((x.n * x.rmse_6h_cm ** 2).sum() / x.n.sum()))

    wl = rd("v3_obs")
    run, obs = rd(CURRENT).reindex(wl.index), rd("v11_rain_obs").reindex(wl.index)
    seeds = [rd(r).reindex(wl.index) for r in SEEDS]
    ps = [pooled_(x) for x in seeds]
    rows = [(["Water level only"], f"{pooled_(wl):.1f}", False), (["Water level + wind + discharge"], f"{pooled_(rd('v6_wind_q')):.1f}", False),
            (["6 h-change scaling + gap filling, no rainfall"], f"{pooled_(rd('v10_dnorm_x_p50')):.1f}", False),
            (["Scaling + gap filling + HRRR rainfall, trained with", "missing hours: one model (five random seeds)"], f"{min(ps):.1f} to {max(ps):.1f}", False),
            (["Scaling + gap filling + HRRR rainfall, trained with", "missing hours, mean of 5 models"], f"{pooled_(run):.1f}", True),
            (["Scaling + gap filling + observed rainfall  (upper bound)"], f"{pooled_(obs):.1f}", False)]

    def clearly(x):
        return (x.rmse_6h_cm > wl.rmse_6h_cm + 1) & (x.rmse_6h_cm > 1.1 * wl.rmse_6h_cm)

    worse, clear = run.rmse_6h_cm > wl.rmse_6h_cm, clearly(run)
    y = 1.0
    text(sl, 0.5, y, 5.6, 0.3, "6 h RMSE in the hurricane periods, all forecasts (cm)", size=11.5, bold=True); y += 0.38
    for lab, val, cur in rows:
        if cur:
            hilite(sl, 0.42, y - 0.01, 5.75, 0.47)
        text(sl, 0.5, y, 4.4, 0.3, lab if len(lab) > 1 else lab[0], size=11.5, bold=cur)
        text(sl, 4.8, y, 1.3, 0.3, val, size=11.5, bold=cur, align=PP_ALIGN.RIGHT)
        y += 0.32 + 0.17 * (len(lab) > 1)
    cx = [(6.5, 2.6, PP_ALIGN.LEFT), (9.0, 0.9, PP_ALIGN.RIGHT), (9.95, 1.2, PP_ALIGN.RIGHT), (11.2, 1.6, PP_ALIGN.RIGHT)]
    y = 1.0
    text(sl, 6.5, y, 6.3, 0.3, "Stations where the mean of 5 models is worse than water level only", size=11.5, bold=True); y += 0.38
    for (x, w, al), h in zip(cx, ["", "stations", "worse", "clearly worse"]):
        text(sl, x, y, w, 0.3, h, size=11, bold=True, align=al)
    y += 0.3
    types = [("river / canal", "Rivers / canals"), ("estuary / tidal channel", "Estuaries / tidal channels"), ("tide gauge", "Tide gauges"), ("lake", "Lakes"),
             ("marsh", "Marsh"), ("urban creek (Houston)", "Urban creeks (Houston)"), (None, "All stations")]
    for key, lab in types:
        m = np.ones(len(wl), bool) if key is None else (wl.type == key).to_numpy()
        tot = key is None
        vals = [lab, f"{int(m.sum())}", f"{int(worse[m].sum())}" + (f"  ({100 * worse.mean():.0f}%)" if tot else ""), f"{int(clear[m].sum())}" + (f"  ({100 * clear.mean():.0f}%)" if tot else "")]
        for (x, w, al), v in zip(cx, vals):
            text(sl, x, y, w, 0.3, v, size=11.5, bold=tot, align=al)
        y += 0.29
    c = clear.to_numpy()
    fixed = int((obs.rmse_6h_cm[c] < wl.rmse_6h_cm[c]).sum())
    uc = (wl.type == "urban creek (Houston)").to_numpy()
    k = pd.concat([clearly(x) for x in seeds], axis=1).sum(1).to_numpy()            # in how many of the five single models a station is clearly worse
    alw = k == len(seeds)
    tc = wl.type[alw].value_counts()
    ei = ("NOAA_COOPS", "8764314")
    eis = [float(x.rmse_6h_cm[ei]) for x in seeds]
    text(sl, 0.5, 4.2, 12.3, 3.2, [
        f"Hurricane periods as in the table by station type: Beryl in the Texas and Galveston domains, Francine in the Louisiana domain. {len(wl)} stations with real-time data, a forecast every hour, "
        f"{int(wl.n.sum()):,} forecasts. Clearly worse: by more than 1 cm and more than 10%.",
        "",
        f"Too high, not too late. At {100 * (run.bias_6h_cm[c] > 0).mean():.0f}% of the {int(c.sum())} clearly worse stations the forecast is too high on average. The versions with wind and rainfall see hurricane wind and a large "
        f"rainfall forecast and forecast a rise; the station rose less (median range at these stations {wl.obs_range_cm[c].median():.0f} cm, at all stations {wl.obs_range_cm.median():.0f} cm). "
        f"Part of it is the rainfall forecast: with observed instead of HRRR rainfall, {fixed} of the {int(c.sum())} are no longer worse.",
        "",
        f"How a single station comes out in a hurricane depends on the random seed: {int((k >= 1).sum())} stations are clearly worse in at least one of the five single models, {int(alw.sum())} in all five "
        f"({int(tc.get('river / canal', 0))} rivers, {int(tc.get('estuary / tidal channel', 0))} estuaries, {int(tc.get('tide gauge', 0))} tide gauges). At those {int(alw.sum())} every model is too high, "
        f"by {run.bias_6h_cm[alw].mean():.1f} cm on average, and averaging does not remove it. "
        f"Example of the seed effect, Eugene Island tide gauge: {wl.rmse_6h_cm[ei]:.1f} cm with water level only, {min(eis):.1f} to {max(eis):.1f} cm among the five models, {run.rmse_6h_cm[ei]:.1f} cm with their mean.",
        "",
        f"Water level only does not forecast too high, but it misses the large rises: urban creeks, median station, {wl.rmse_6h_cm[uc].median():.1f} cm against {run.rmse_6h_cm[uc].median():.1f} cm.",
    ], size=11.5)


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
    groups = []                                              # order of the deck: slides are sorted by group at the end, creation order within a group

    def new(title, group=0):
        nonlocal n
        n += 1; sl = prs.slides.add_slide(blank); groups.append(group)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=17, bold=True)       # no page numbers: slides are added and removed by hand
        return sl

    def count(a, b):
        dd = r6[a] - r6[b]; return int((dd <= -0.5).sum()), int((dd >= 0.5).sum())

    def med(key, tname):
        return float(np.median(r6[key][typ == tname]))

    # ---- where the stations are
    sl = new("The stations: all of them for training, those with a real-time feed for the forecast")
    yb = picture(sl, F / "stations_map.png", 0.3, 1.0, 12.7, 4.6)
    text(sl, 0.5, yb + 0.2, 12.3, 1.6, [
        "(a) One model is trained on all 1010 stations in the three 100 m domains. The 552 CRMS marsh stations are read out from loggers and published months later, "
        "so they add training data but cannot be forecast in real time.",
        "(b) A forecast is issued for the 457 USGS and NOAA stations, which report in real time: tide gauges, estuaries, lakes, rivers and the Houston creeks.",
        f"All error numbers on the following slides are for the {n_st} of these 457 stations that have enough observations in the test period (January 2024 to December 2025). CRMS stations are not in any of the numbers.",
    ], size=12)

    # ---- 1 the versions as a table
    sl = new("Every model version so far; the version that is run is highlighted")
    cols = [(0.5, 3.05, "Version", PP_ALIGN.LEFT), (3.6, 3.7, "What it adds or changes", PP_ALIGN.LEFT), (7.35, 1.95, "Available in real time", PP_ALIGN.LEFT),
            (9.3, 1.1, "All stations", PP_ALIGN.RIGHT), (10.45, 1.1, "Urban creeks", PP_ALIGN.RIGHT), (11.6, 1.2, "Tide gauges", PP_ALIGN.RIGHT)]
    y = 0.9
    text(sl, 9.3, y - 0.05, 3.5, 0.3, "6 h RMSE (cm)", size=10, bold=True, align=PP_ALIGN.CENTER); y += 0.25
    for x, w, h, al in cols:
        text(sl, x, y, w, 0.3, h, size=10, bold=True, align=al)
    y += 0.33
    lines = [(r.run, SHORT[r.run], WHAT[r.run][0], WHAT[r.run][1], r["all"], r["urban creek (Houston)"], r["tide gauge"]) for _, r in tab.iterrows()]
    for run, name, what, rt in TRIED:
        x_ = load_runs(["v11_fc1_t45", run])[run]
        lines.append((run, name, what, rt, pooled(x_), float(x_.rmse_6h_cm[x_.type == "urban creek (Houston)"].median()), float(x_.rmse_6h_cm[x_.type == "tide gauge"].median())))
    for k, (run, name, what, rt, a_, u_, tg_) in enumerate(lines):
        if k in (5, 8, 13):
            y += 0.08                                        # blocks: built step by step / rainfall / scaling and gap filling / tried on top of the current version
        cur = run == CURRENT
        two = "\n" in name                                  # a name on two lines: the row is taller
        if cur:
            hilite(sl, 0.42, y - 0.01, 12.45, 0.26 + 0.17 * two)
        for (x, w, _, al), v in zip(cols, [name.split("\n") if two else name, what, rt, f"{a_:.1f}", f"{u_:.1f}", f"{tg_:.1f}"]):
            text(sl, x, y, w, 0.3, v, size=10, bold=cur, align=al)
        y += 0.262 + 0.17 * two
    text(sl, 0.5, y + 0.03, 12.3, 1.1, [
        "Highlighted: the version that is run for the forecast - 6 h-change scaling, gap filling, HRRR rainfall, trained with missing hours, mean of 5 models. First block: each row keeps everything above it and adds one input, "
        "ending with water level + wind + discharge. Second block: rainfall added to that. Third block: water level + wind + discharge and the two rainfall versions again, with the error scaled by the 6 h change and gaps filled "
        "with the last observation; then the model trained to cope with a gauge that has stopped reporting, and five such models with different random seeds, averaged. "
        "Fourth block: three more additions tried on top of scaling + gap filling + HRRR rainfall; they changed nothing and were dropped.",
        "Every rainfall row has the rainfall of the past 72 h as input; the rows differ in where the rainfall of the next 6 h comes from. In real time the past 72 h come from MRMS radar rainfall.",
        f"Test period January 2024 to December 2025, {n_st} stations with real-time data (USGS and NOAA; CRMS marsh stations are used for training only and are left out). "
        "All stations: RMSE over all forecasts. Urban creeks, tide gauges: the median station of that type. Same network in every row unless stated: 2-layer LSTM, hidden size 128, 72 h look-back, one model for all stations.",
    ], size=9.5)

    # ---- 3 bars
    sl = new("What each version does, by station type")
    picture(sl, F / "versions_bars.png", 0.3, 0.95, 12.7, 4.45)
    text(sl, 0.5, 5.45, 12.3, 1.6, [
        f"Wind helps the tidal types: tide gauges {t.loc['v3_obs','tide gauge']:.1f} to {t.loc['v3_wind','tide gauge']:.1f} cm, estuaries {t.loc['v3_obs','estuary / tidal channel']:.1f} to {t.loc['v3_wind','estuary / tidal channel']:.1f} cm, lakes {t.loc['v3_obs','lake']:.1f} to {t.loc['v3_wind','lake']:.1f} cm. Upstream discharge changes the medians by 0.1 cm or less.",
        f"The 6 h-change scaling and gap filling help rivers ({t.loc['v6_wind_q','river / canal']:.1f} to {t.loc['v10_dnorm_x_p50','river / canal']:.1f} cm) and do not cost the tidal types anything.",
        f"Rainfall helps urban creeks, and how much depends on where the rainfall of the next 6 h comes from: {t.loc['v6_wind_q','urban creek (Houston)']:.1f} cm without rainfall, "
        f"{t.loc[CURRENT,'urban creek (Houston)']:.1f} cm with scaling, gap filling, the HRRR forecast and five models averaged (highlighted), {t.loc['v11_rain_obs','urban creek (Houston)']:.1f} cm if the rainfall were known exactly (grey bars, not available in real time).",
        "Without the scaling and gap filling, HRRR rainfall made rivers and tide gauges slightly worse; with them it does not. "
        f"Averaging five models lowers every type a little: all stations {t.loc['v14_stale25','all']:.1f} to {t.loc[CURRENT,'all']:.1f} cm, tide gauges {t.loc['v14_stale25','tide gauge']:.1f} to {t.loc[CURRENT,'tide gauge']:.1f} cm.",
    ], size=11.5)

    # ---- 4 lead time
    sl = new("Error against lead time for the six main versions")
    picture(sl, F / "versions_lead.png", 0.5, 1.0, 12.3, 4.4)
    text(sl, 0.5, 5.6, 12.3, 1.4, [
        f"Tide gauges: the versions with wind lie close together, {med('wl','tide gauge') - med('wind','tide gauge'):.1f} to {med('wl','tide gauge') - med('base_fc','tide gauge'):.1f} cm below water level only at 6 h. "
        "Neither the scaling and gap filling nor rainfall changes them; the thick line is slightly lower because it is the mean of 5 models.",
        "Rivers: the 6 h-change scaling and gap filling lower the error at every lead; rainfall lowers it further.",
        f"Urban creeks: the versions separate after 2 h. With scaling, gap filling, HRRR rainfall and five models averaged (thick line) the error is {med('q','urban creek (Houston)') - med('base_fc','urban creek (Houston)'):.1f} cm below water level + wind + discharge at 6 h; "
        f"with observed rainfall it would be {med('q','urban creek (Houston)') - med('base_obs','urban creek (Houston)'):.1f} cm below."], size=12)

    # ---- 5, 6 maps
    above = {k: int((v > 10).sum()) for k, v in r6.items()}
    sl = new("Station by station: 6 h RMSE of the six main versions")
    picture(sl, F / "versions_map_rmse.png", 0.3, 0.95, 12.7, 5.3)
    text(sl, 0.5, 6.3, 12.3, 0.8, [
        f"Stations above 10 cm: {above['wl']} with water level only, {above['q']} with wind and discharge added, {above['base']} with 6 h-change scaling and gap filling, {above['base_fc']} with HRRR rainfall added to that and five models averaged, {above['base_obs']} with observed rainfall. "
        "The dark stations sit in the same two places in every map: the Houston creeks and the small rivers north and east of Baton Rouge."], size=12)

    sl = new("Station by station: each version against water level only")
    picture(sl, F / "versions_map_change.png", 0.3, 1.0, 8.6, 5.9)
    c1, d1 = count("q", "wl"); c2, d2 = count("base", "wl"); c3, d3 = count("base_fc", "wl"); c4, d4 = count("base_obs", "wl")
    b2, w2 = count("base", "q"); b3, w3 = count("base_fc", "q")            # against the previous version: used on the closing slide
    text(sl, 9.1, 1.05, 3.9, 5.9, [
        "All four maps show the 6 h RMSE minus that of the water-level-only version, so they can be compared with each other.",
        "",
        f"(a) Water level + wind + discharge: {c1} stations better, {d1} worse. The gain follows the coast and the bays.",
        "",
        f"(b) 6 h-change scaling + gap filling, no rainfall: {c2} better, {d2} worse. Inland rivers are added to the gain; no station is worse than with water level only.",
        "",
        f"(c) Scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models: {c3} better, {d3} worse. Houston and the creeks around Baton Rouge turn blue. "
        "The two dark orange stations are Pearl River navigation locks, where gate operation sets the level and rainfall only misleads the model.",
        "",
        f"(d) Scaling + gap filling + observed rainfall of the next 6 h: {c4} better, {d4} worse. Same places as (c), several times stronger. The difference between (c) and (d) is the error of the rainfall forecast.",
        "",
        "Better / worse: by 0.5 cm or more. Colour scale limited to 5 cm in both directions.",
    ], size=12)

    # ---- the version that is run: RMSE by station type, hurricane periods and the rest
    ev = pd.read_csv(REPO / "deliverables" / "22_rmse_by_type_and_period.csv").set_index("type")
    sl = new("The version that is run: RMSE by station type, in the hurricanes and in the rest of the test period")
    cx = [(0.5, 3.3, PP_ALIGN.LEFT), (3.9, 1.0, PP_ALIGN.RIGHT), (5.4, 1.0, PP_ALIGN.RIGHT), (6.5, 1.0, PP_ALIGN.RIGHT), (7.6, 1.0, PP_ALIGN.RIGHT),
          (9.3, 1.0, PP_ALIGN.RIGHT), (10.4, 1.0, PP_ALIGN.RIGHT), (11.5, 1.0, PP_ALIGN.RIGHT)]
    y = 1.0
    text(sl, 5.4, y, 3.2, 0.3, "Hurricanes Beryl and Francine", size=12, bold=True, align=PP_ALIGN.RIGHT)
    text(sl, 9.3, y, 3.2, 0.3, "Rest of 2024 and 2025", size=12, bold=True, align=PP_ALIGN.RIGHT); y += 0.34
    for (x, w, al), h in zip(cx, ["RMSE (cm)", "stations", "1 h ahead", "3 h ahead", "6 h ahead", "1 h ahead", "3 h ahead", "6 h ahead"]):
        text(sl, x, y, w, 0.3, h, size=12, bold=True, align=al)
    y += 0.4
    for name, r in ev.iterrows():
        tot = name == "All stations"
        if tot:
            y += 0.08
        vals = [name, f"{int(r.stations)}"] + [f"{r[f'hurricane_{L}h_cm']:.1f}" for L in (1, 3, 6)] + [f"{r[f'other_{L}h_cm']:.1f}" for L in (1, 3, 6)]
        for (x, w, al), v in zip(cx, vals):
            text(sl, x, y, w, 0.3, v, size=12, bold=tot, align=al)
        y += 0.34
    al_ = ev.loc["All stations"]; uc_ = ev.loc["Urban creeks (Houston)"]; es_ = ev.loc["Estuaries / tidal channels"]
    text(sl, 0.5, y + 0.3, 12.3, 2.6, [
        "Scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models. RMSE over all forecasts of the stations of a type (not the median station); stations with real-time data, January 2024 to December 2025.",
        "Hurricane periods: Beryl, 7 to 11 July 2024, at the stations of the Texas and Galveston domains; Francine, 10 to 14 September 2024, at the stations of the Louisiana domain. "
        "Rest: every other forecast of the two years; it still contains other floods, such as May 2024.",
        "",
        f"Over all stations the 6 h error in the hurricanes is {al_.hurricane_6h_cm / al_.other_6h_cm:.1f} times that of the rest ({al_.hurricane_6h_cm:.1f} against {al_.other_6h_cm:.1f} cm). "
        f"The largest errors are at urban creeks ({uc_.hurricane_6h_cm:.1f} cm) and estuaries ({es_.hurricane_6h_cm:.1f} cm); lakes and rivers grow least. "
        f"At 1 h ahead no type exceeds {ev.hurricane_1h_cm.max():.1f} cm, also in the hurricanes.",
        f"Marsh: {int(ev.loc['Marsh', 'stations'])} stations and {int(ev.loc['Marsh', 'n_hurricane'])} forecasts in the hurricane periods, so those numbers are uncertain.",
    ], size=12)

    # ---- 7 tried and set aside
    sl = new("Also tried: changes that made no measurable difference", 2)
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
                          ("v13_ds", "Water level at the next gauge downstream (or the nearest tide gauge) as input", "v10_dnorm_x_p50"),
                          ("v15r_init_state", "The LSTM starts from a state of its own for every station instead of from zero", "v14_stale25")]:
        a, b = pooled_nc(run, ref)
        rows.append((lab, f"{a:.2f}", f"{b:.2f}", False))
    y = 1.0
    for lab, a, b, bold in rows:
        text(sl, 0.5, y, 8.3, 0.3, lab, size=11.5, bold=bold); text(sl, 8.8, y, 2.2, 0.3, a, size=11.5, bold=bold, align=PP_ALIGN.RIGHT); text(sl, 11.0, y, 1.8, 0.3, b, size=11.5, bold=bold, align=PP_ALIGN.RIGHT)
        y += 0.315
    text(sl, 0.5, y + 0.12, 12.3, 1.6, [
        "Reference: water level + wind + discharge for the first three rows and the eighth; the version of the same kind for the others (for the last four rows: one model with 6 h-change scaling and gap filling, with or without HRRR rainfall). Same stations in both columns.",
        "Separate models for tidal stations and for river stations were also trained and were not better than the single model on the same stations. "
        "For scale: five trainings of one model that differ only in the random seed range from 8.63 to 8.70 cm.",
        "Network size and the form of the inputs are not what limits the forecast. The limit is information the inputs do not contain: rainfall of the coming hours, and gate and reservoir operation.",
    ], size=11.5)

    # ---- 8 how to read
    sl = new("How to read the station slides", 9)
    text(sl, 0.5, 1.1, 12.3, 5.6, [
        "One station per slide. Six columns: six versions, left to right. Two rows: two 4-day periods from the test years.",
        "   Top row: the hurricane — Francine, 10 to 14 September 2024, in Louisiana; Beryl, 7 to 11 July 2024, in Texas.",
        "   Bottom row: the highest water level at that station outside the hurricane.",
        "",
        "Black: observed water level. Orange lines, pale to vivid: the forecast valid at each hour that was issued 1, 3 and 6 hours earlier. A forecast is issued every hour.",
        "A red-orange line that follows the black line a few hours late means the version only reacts once the rise is already in the observations. Grey band: 24 hours around the observed peak. Numbers inside each panel: RMSE in that period at 1, 3 and 6 hours lead.",
        "Above each column: the 6 h RMSE of that version at the station over the whole two test years.",
        "",
        "The fifth column, with its heading in bold, is the version that is run: 6 h-change scaling, gap filling and HRRR rainfall, trained with missing hours, mean of 5 models. Columns one to four have no rainfall.",
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
        sl = new(f"{TYPE_EN[r.type]}  —  {name}  ({r.source.replace('NOAA_COOPS', 'NOAA')} {sid}), {r.domain}", 9)
        yb = picture(sl, F / f"station_{sid}.png", 0.3, 0.95, 12.7, 5.35)
        vals = {k: float(per[run].loc[per[run].station_id == sid, "rmse_6h_cm"].iloc[0]) for k, run in key2run.items()}
        summary.append({"sid": sid, "type": r.type, **vals})
        text(sl, 0.5, yb + 0.12, 12.3, 0.6,
             f"Whole test period, step by step: wind {vals['wind'] - vals['wl']:+.1f} cm; discharge and wind refinements {vals['q'] - vals['wind']:+.1f} cm; "
             f"6 h-change scaling and gap filling {vals['base'] - vals['q']:+.1f} cm; HRRR rainfall, training with missing hours and the mean of 5 models on top of that {vals['base_fc'] - vals['base']:+.1f} cm "
             f"(observed rainfall would give {vals['base_obs'] - vals['base']:+.1f} cm).", size=11.5)

    # ---- hurricane periods, station by station
    storm_slide(new(STORM_TITLE, 1))

    # ---- forecast lag and a second gauge on the same river
    mp = pd.read_csv(REPO / "config" / "station_downstream_map.csv", dtype=str).fillna("")
    has_us = set(mp.station_id[mp.us_station_id != ""])
    ref = load_runs(["v10_dnorm_x_p50", "v13_ds", "v13_ds_us", "v11_fc1_t45", "v13_fc_ds_us"])
    us = ref["v10_dnorm_x_p50"].station_id.isin(has_us).to_numpy()

    def cnt(a, b, sel):
        dd = ref[b].rmse_6h_cm.to_numpy()[sel] - ref[a].rmse_6h_cm.to_numpy()[sel]; return int((dd <= -0.5).sum()), int((dd >= 0.5).sum())

    lag = pd.read_csv(REPO / "deliverables" / "19_reference_gauge" / "lag_table.csv", dtype={"station_id": str})
    lus = lag[lag.upstream_ref != ""]
    sl = new("The 6 h forecast runs late: a gauge upstream helps at 127 stations, the lag stays on average", 1)
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
    pr = load_runs(["v14_stale25_pastaorc", "v14_stale25_pastmrms", "v14_stale25_pasthrrr", "v14_stale25_pastnone"])
    sl = new("Rainfall in real time: where the two rainfall inputs come from", 3)
    rows = [("Rainfall of the past 72 h taken from", "Available in real time", "All stations", "Urban creeks", "Stations worse", True)]
    for run, lab, rt in [("v14_stale25_pastaorc", "AORC reanalysis (used for training)", "no"),
                         ("v14_stale25_pastmrms", "MRMS radar and gauge analysis, 1 km", "yes, 16 min after the hour"),
                         ("v14_stale25_pasthrrr", "HRRR short-range forecast, 1 to 6 h lead", "yes"),
                         ("v14_stale25_pastnone", "No rainfall of the past 72 h", "-")]:
        x = pr[run]; dd = x.rmse_6h_cm.to_numpy() - pr["v14_stale25_pastaorc"].rmse_6h_cm.to_numpy()
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
        "One of the five models (scaling + gap filling + HRRR rainfall, trained with missing hours, random seed 0) in every row; only the source of the past rainfall is changed, without retraining. "
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

    import json
    ver = json.loads((REPO / "deliverables" / "20_operational_rain" / f"{LIVE_TAG}_verification.json").read_text())["leads"]

    # ---- one forecast from the real-time services, checked afterwards: stations
    sl = new(f"A forecast from the real-time data services for {LIVE_WHEN}, checked afterwards", 3)
    yb = picture(sl, F / f"live_{LIVE_TAG}_stations.png", 0.3, 0.95, 12.7, 5.3)
    vf = pd.read_csv(REPO / "deliverables" / "20_operational_rain" / f"{LIVE_TAG}_verification.csv", dtype={"station_id": str}).set_index("station_id")
    fcs = pd.read_csv(REPO / "deliverables" / "20_operational_rain" / f"{LIVE_TAG}_forecast.csv", dtype={"station_id": str})
    gen = pd.Timestamp(json.loads((REPO / "deliverables" / "20_operational_rain" / f"{LIVE_TAG}_manifest.json").read_text())["generated_utc"])

    def nice(nm):
        return str(nm).title() if str(nm).isupper() else str(nm)

    e8 = vf.loc[LIVE_STATIONS, "err_6h_cm"].abs()
    text(sl, 0.5, yb + 0.12, 12.3, 0.9, [
        "Black: observed, 48 h before the forecast time and the 6 h after it. Red-orange: the forecast of the version that is run (scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models). "
        f"Numbers: error at 1, 3 and 6 h. The forecast script was run on {gen.day} {gen:%B} at {gen:%H:%M} UTC for the forecast time 12:00 UTC of 12 November, with inputs dated no later than that hour "
        "(gauges and MRMS up to 12:00, HRRR wind from the 12:00 cycle, HRRR rainfall from the 11:00 cycle). "
        "Eight stations with large changes in those 6 h, from all five types, all with a complete record: the tide going out, Texas rivers still rising or falling after the rain of 11 November. "
        f"Largest miss among the eight: {nice(vf.loc[e8.idxmax(), 'name'])}, {e8.max():.1f} cm at 6 h."], size=11.5)

    # ---- the same forecast at all stations
    sl = new(f"The same forecast at all {ver['6']['n']} stations: 1, 3 and 6 hours ahead", 3)
    yb = picture(sl, F / f"live_{LIVE_TAG}_scatter.png", 0.5, 0.95, 12.3, 4.5)
    bt = ver["6"]["by_type"]
    text(sl, 0.5, yb + 0.15, 12.3, 1.6, [
        "Each dot is a station: how much the water level changed after the forecast time (horizontal) against how much the forecast said it would change (vertical). On the line = exact.",
        f"RMSE over all stations: {ver['1']['rmse_cm']:.1f} cm at 1 h, {ver['2']['rmse_cm']:.1f} at 2 h, {ver['3']['rmse_cm']:.1f} at 3 h, {ver['4']['rmse_cm']:.1f} at 4 h, {ver['5']['rmse_cm']:.1f} at 5 h, {ver['6']['rmse_cm']:.1f} at 6 h; "
        f"half of the stations are within {ver['1']['median_abs_cm']:.1f}, {ver['3']['median_abs_cm']:.1f} and {ver['6']['median_abs_cm']:.1f} cm at 1, 3 and 6 h. "
        f"At 6 h by type: tide gauges {bt['tide gauge']['rmse_cm']:.1f}, estuaries {bt['estuary / tidal channel']['rmse_cm']:.1f}, lakes {bt['lake']['rmse_cm']:.1f}, rivers {bt['river / canal']['rmse_cm']:.1f}, urban creeks {bt['urban creek (Houston)']['rmse_cm']:.1f} cm.",
        f"{int((fcs.status == 'ok').sum())} of the 457 stations got a forecast (the others returned no or too little data); the whole run took under a minute. "
        f"Largest miss: {nice(vf.loc[vf.err_6h_cm.abs().idxmax(), 'name'])}, {vf.err_6h_cm.abs().max():.0f} cm at 6 h "
        f"(observed change {100 * (vf.obs_6h_m - vf.last_obs_m)[vf.err_6h_cm.abs().idxmax()]:+.0f} cm, forecast {100 * (vf.fcst_6h_m - vf.last_obs_m)[vf.err_6h_cm.abs().idxmax()]:+.0f} cm). "
        "One forecast time with no rain ahead: it shows that the chain works, it is not a statistic.",
    ], size=11.5)

    # ---- what 1, 3 and 6 h forecasts cost: computing and timing
    so_ = pd.read_csv(REPO / "runs" / CURRENT / "stale_origin.csv")
    so_ = so_[so_.group == "all"].pivot(index="lead_h", columns="hours_without_data", values="rmse_cm")
    age = pd.read_csv(REPO / "deliverables" / "20_operational_rain" / "data_age_20261112.csv", dtype={"station_id": str}, parse_dates=["snapshot_utc", "asked_utc", "newest_utc"])
    snaps = sorted(age.snapshot_utc.unique())
    a0 = age[age.snapshot_utc == snaps[0]]
    med_age = {src: float(g.age_min.median()) for src, g in a0.groupby("source")}
    hour0 = pd.Timestamp(snaps[0]).floor("h")
    arrive = []                                   # (minutes past the hour, share of answering USGS gauges with a reading of that hour)
    for t_ in snaps:
        g = age[(age.snapshot_utc == t_) & (age.source == "USGS") & age.newest_utc.notna()]
        arrive.append(((pd.Timestamp(g.asked_utc.iloc[0]) - hour0).total_seconds() / 60, float((g.newest_utc >= hour0).mean())))
    arrive = [x for x in arrive if x[0] < 75]

    def minute_at(share):
        m_ = [m for m, f in arrive if f >= share]
        return min(m_) if m_ else None

    sl = new("1, 3 and 6 h forecasts: the computing cost is the same, the timing is not", 3)
    y = 0.95
    text(sl, 0.5, y, 12.3, 0.3, "Computing", size=12, bold=True)
    text(sl, 0.5, y + 0.3, 12.3, 1.2, [
        "Each model gives all six lead times in one pass, so offering 1 h, 3 h or 6 h costs the same. Training: once, about 40 min on one A100 GPU for each of the five models. "
        "One forecast for the 457 stations: about 50 s, of which USGS water level 6 s, NOAA water level 37 s (54 gauges one after another, the service refuses parallel requests), "
        "HRRR wind 4 s, discharge 2 s, rainfall and the five networks together under 1 s each. "
        "The only input that grows with the lead time is the HRRR wind forecast: 1, 3 or 6 forecast hours, about 2 MB and under 1 s each."], size=11.5)
    y = 2.35
    text(sl, 0.5, y, 12.3, 0.3, "Accuracy", size=12, bold=True); y += 0.33
    cx = [(0.5, 3.6, PP_ALIGN.LEFT), (4.1, 2.7, PP_ALIGN.RIGHT), (6.9, 2.7, PP_ALIGN.RIGHT), (9.7, 2.7, PP_ALIGN.RIGHT)]
    for (x, w, al), h in zip(cx, ["RMSE (cm), stations with real-time data", "newest hour in hand", "newest 1 h not yet in", "newest 2 h not yet in"]):
        text(sl, x, y, w, 0.3, h, size=11, bold=True, align=al)
    y += 0.32
    for L in (1, 3, 6):
        for (x, w, al), v in zip(cx, [f"{L} h ahead", f"{so_.loc[L, 0]:.1f}", f"{so_.loc[L, 1]:.1f}", f"{so_.loc[L, 2]:.1f}"]):
            text(sl, x, y, w, 0.3, v, size=11.5, align=al)
        y += 0.3
    text(sl, 0.5, y + 0.02, 12.3, 0.3, "Scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models; all forecasts of 2024 and 2025. Lead time counted from the forecast hour.", size=10.5)
    y += 0.5
    text(sl, 0.5, y, 12.3, 0.3, "Timing", size=12, bold=True)
    n_sn = len(arrive)
    if n_sn >= 6 and minute_at(0.5) is not None:
        m50, m90 = minute_at(0.5), minute_at(0.9)
        arr = (f"Asked again every 5 min until {arrive[-1][0]:.0f} min after the hour: half of the USGS gauges had the {hour0:%H}:00 reading after {m50:.0f} min"
               + (f", nine in ten after {m90:.0f} min. " if m90 is not None else f", {100 * arrive[-1][1]:.0f}% after {arrive[-1][0]:.0f} min. "))
    else:
        arr = f"{arrive[0][0]:.0f} min after {hour0:%H}:00 no USGS gauge had the reading of that hour. "
    text(sl, 0.5, y + 0.3, 12.3, 2.7, [
        f"What a short lead time needs is speed, not computing. Measured on {hour0:%d %B %Y}, {pd.Timestamp(snaps[0]):%H:%M} UTC: the newest reading was "
        f"{med_age['NOAA_COOPS']:.0f} min old at the NOAA tide gauges and {med_age['USGS']:.0f} min old at the USGS gauges (median). " + arr +
        "Wind and rainfall do not hold the run back: the script takes the newest MRMS hour and HRRR cycle that are published.",
        "",
        "If the forecast waits until the USGS readings of the forecast hour are in, it leaves about an hour after it: the 1 h forecast is then already in the past, "
        "the 3 h forecast has about 2 h left, the 6 h forecast about 5 h.",
        "",
        "A 1 h forecast is therefore useful only if the run starts a few minutes after the hour, without the newest hour at the USGS gauges. "
        "The models are trained for that; the price is the middle column of the table. It also needs an hourly scheduled run; the forecast is started by hand so far.",
    ], size=11.5)

    # ---- a gauge that has stopped reporting
    so = {r_: pd.read_csv(REPO / "runs" / r_ / "stale_origin.csv") for r_ in ("v6_wind_q", "v11_fc1_t45", "v14_stale25", CURRENT)}

    def sv(run, group, lead, k):
        t_ = so[run]; return float(t_[(t_.group == group) & (t_.lead_h == lead) & (t_.hours_without_data == k)].rmse_cm.iloc[0])

    sl = new("When a gauge stops reporting: the model is now trained for it", 3)
    cx = [(0.5, 3.3, PP_ALIGN.LEFT), (3.6, 2.2, PP_ALIGN.RIGHT), (5.9, 2.2, PP_ALIGN.RIGHT), (8.15, 2.3, PP_ALIGN.RIGHT), (10.5, 2.4, PP_ALIGN.RIGHT)]
    y = 0.95
    hilite(sl, 10.6, y - 0.02, 2.35, 4.15)
    for (x, w, al), h in zip(cx, ["6 h RMSE (cm)", ["Water level + wind", "+ discharge"], ["Scaling + gap filling", "+ HRRR rainfall"],
                                  ["Scaling + gap filling", "+ HRRR rainfall, trained", "with missing hours"],
                                  ["Scaling + gap filling", "+ HRRR rainfall, trained with", "missing hours, mean of 5 models"]]):
        text(sl, x, y, w, 0.3, h, size=10.5, bold=True, align=al)
    y += 0.78
    for grp, glab in (("all", "All forecasts, 2024 to 2025"), ("hurricane periods", "Hurricanes Beryl and Francine")):
        text(sl, 0.5, y, 6, 0.3, glab, size=12, bold=True); y += 0.33
        for k, klab in ((0, "newest observation at forecast time"), (1, "gauge silent for 1 h"), (2, "gauge silent for 2 h"), (3, "gauge silent for 3 h")):
            for (x, w, al), v in zip(cx, ["      " + klab, f"{sv('v6_wind_q', grp, 6, k):.1f}", f"{sv('v11_fc1_t45', grp, 6, k):.1f}", f"{sv('v14_stale25', grp, 6, k):.1f}", f"{sv(CURRENT, grp, 6, k):.1f}"]):
                text(sl, x, y, w, 0.3, v, size=12, align=al)
            y += 0.31
        y += 0.1
    text(sl, 0.5, y + 0.12, 12.3, 2.3, [
        "A station is still forecast while its newest observation is at most 3 h old. The newest 1, 2 or 3 hours of water level were removed from every test forecast, the way the forecast script fills a gap; wind, rainfall and discharge were left as they are.",
        f"Without preparation one silent hour was enough to throw the model off: {sv('v11_fc1_t45', 'all', 6, 0):.1f} to {sv('v11_fc1_t45', 'all', 6, 1):.1f} cm with scaling, gap filling and HRRR rainfall "
        f"({sv('v6_wind_q', 'all', 6, 0):.1f} to {sv('v6_wind_q', 'all', 6, 1):.1f} cm with water level + wind + discharge, which fills gaps with the station mean). The model had hardly seen such input in training.",
        f"Trained with the newest 1 to 3 hours removed in a quarter of the samples, the model loses {sv('v14_stale25', 'all', 6, 1) - sv('v14_stale25', 'all', 6, 0):.1f} cm per silent hour instead: "
        f"{sv('v14_stale25', 'all', 6, 0):.1f}, {sv('v14_stale25', 'all', 6, 1):.1f}, {sv('v14_stale25', 'all', 6, 2):.1f}, {sv('v14_stale25', 'all', 6, 3):.1f} cm. "
        f"At 1 h lead: {sv('v14_stale25', 'all', 1, 0):.1f} cm with a fresh observation, {sv('v14_stale25', 'all', 1, 3):.1f} cm after 3 silent hours ({sv('v11_fc1_t45', 'all', 1, 3):.1f} cm before). "
        "With complete input nothing is lost (first row of each block).",
        f"Highlighted: five models trained this way with different random seeds, averaged; this is what is run. At 1 h lead: {sv(CURRENT, 'all', 1, 0):.1f} cm with a fresh observation, {sv(CURRENT, 'all', 1, 3):.1f} cm after 3 silent hours.",
    ], size=11.5)

    # ---- five models that differ only in the random seed, averaged
    ens = load_runs([r for _, r, _, _ in MAIN] + SEEDS + ["v15r_init_state"])
    idx = ens[CURRENT].index
    mk = {k_: pd.read_csv(REPO / "runs" / CURRENT / f"per_station_test_mean{k_}.csv", dtype={"station_id": str}).loc[idx] for k_ in (2, 3, 5)}
    sp = {h: [pooled(ens[r], h) for r in SEEDS] for h in (1, 3, 6)}
    sl = new("Five models that differ only in the random seed, averaged", 3)
    cx = [(0.5, 3.4, PP_ALIGN.LEFT), (3.9, 1.3, PP_ALIGN.RIGHT), (5.2, 1.3, PP_ALIGN.RIGHT), (6.5, 1.3, PP_ALIGN.RIGHT)]
    y = 1.0
    for (x, w, al), h in zip(cx, ["RMSE over all forecasts (cm)", "1 h ahead", "3 h ahead", "6 h ahead"]):
        text(sl, x, y, w, 0.3, h, size=11.5, bold=True, align=al)
    y += 0.36
    lines5 = [("One model (range of the five seeds)", [f"{min(sp[h]):.2f} to {max(sp[h]):.2f}" for h in (1, 3, 6)], False),
              ("Mean of 2 models", [f"{pooled(mk[2], h):.2f}" for h in (1, 3, 6)], False), ("Mean of 3 models", [f"{pooled(mk[3], h):.2f}" for h in (1, 3, 6)], False),
              ("Mean of 5 models", [f"{pooled(mk[5], h):.2f}" for h in (1, 3, 6)], True)]
    for lab, vals, cur in lines5:
        if cur:
            hilite(sl, 0.42, y - 0.01, 7.45, 0.3)
        for (x, w, al), v in zip(cx, [lab] + vals):
            text(sl, x, y, w, 0.3, v, size=11.5, bold=cur, align=al)
        y += 0.31
    cx2 = [(8.3, 2.2, PP_ALIGN.LEFT), (10.3, 1.5, PP_ALIGN.RIGHT), (11.7, 1.1, PP_ALIGN.RIGHT)]
    y2 = 1.0
    for (x, w, al), h in zip(cx2, ["Median station, 6 h (cm)", "one model", "mean of 5"]):
        text(sl, x, y2, w, 0.3, h, size=11.5, bold=True, align=al)
    y2 += 0.36
    for tk, tl in [("tide gauge", "Tide gauges"), ("estuary / tidal channel", "Estuaries"), ("lake", "Lakes"), ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks (Houston)")]:
        m_ = (ens[CURRENT].type == tk).to_numpy()
        one = [float(ens[r].rmse_6h_cm[m_].median()) for r in SEEDS]
        for (x, w, al), v in zip(cx2, [tl, f"{min(one):.2f} to {max(one):.2f}", f"{mk[5].rmse_6h_cm[m_].median():.2f}"]):
            text(sl, x, y2, w, 0.3, v, size=11.5, align=al)
        y2 += 0.29
    dd5 = mk[5].rmse_6h_cm.to_numpy() - ens["v14_stale25"].rmse_6h_cm.to_numpy()
    mv = [(int((ens[r].rmse_6h_cm.to_numpy() - ens["v14_stale25"].rmse_6h_cm.to_numpy() < -0.5).sum()), int((ens[r].rmse_6h_cm.to_numpy() - ens["v14_stale25"].rmse_6h_cm.to_numpy() > 0.5).sum())) for r in SEEDS[1:]]

    def storm_pool(r):
        x = pd.read_csv(REPO / "runs" / r / "storm_station.csv"); return float(np.sqrt((x.n * x.rmse_6h_cm ** 2).sum() / x.n.sum()))

    stp = [storm_pool(r) for r in SEEDS]
    text(sl, 0.5, 3.1, 12.3, 4.2, [
        "What was done. The model with scaling, gap filling and HRRR rainfall, trained with missing hours, was trained four more times with exactly the same data and settings; only the random seed differs "
        "(the random starting weights and the order of the training samples). The forecast is the mean of the five forecasts. No new data; a forecast takes about a second longer.",
        "",
        f"Test period, {len(idx)} stations with real-time data: {pooled(ens['v14_stale25']):.2f} to {pooled(mk[5]):.2f} cm at 6 h ({100 * (pooled(mk[5]) / pooled(ens['v14_stale25']) - 1):+.1f}%) and "
        f"{pooled(ens['v14_stale25'], 1):.2f} to {pooled(mk[5], 1):.2f} cm at 1 h, below every single model at every lead time and for every station type. "
        f"{int((dd5 < 0).sum())} of the {len(idx)} stations are better than with the single model of seed 0; by more than 0.5 cm, {int((dd5 < -0.5).sum())} better and {int((dd5 > 0.5).sum())} worse. "
        "Most of the gain comes with the first two or three models.",
        "",
        f"Hurricane periods, 6 h, all forecasts: {storm_pool(CURRENT):.1f} cm with the mean, {min(stp):.1f} to {max(stp):.1f} cm with the single models. "
        "The stations where all five models forecast too high stay too high (slide on the hurricanes).",
        "",
        f"A yardstick for every other comparison. Another seed alone moves the 6 h RMSE over all stations between {min(sp[6]):.2f} and {max(sp[6]):.2f} cm, and "
        f"{min(a_ for a_, _ in mv)} to {max(a_ for a_, _ in mv)} stations get better and {min(b_ for _, b_ in mv)} to {max(b_ for _, b_ in mv)} get worse by more than 0.5 cm. A difference of that size between two versions is not a difference.",
        "",
        f"Also tried after the group meeting: a starting state of its own for every station in the LSTM, instead of zero. No change: {pooled(ens['v15r_init_state']):.2f} cm.",
    ], size=11.5)

    # ---- closing: where things stand
    sl = new("Where things stand", 4)
    a0, a1, a2, a3 = t.loc["v6_wind_q", "all"], t.loc["v10_dnorm_x_p50", "all"], t.loc[CURRENT, "all"], t.loc["v11_rain_obs", "all"]
    u0, u1, u2, u3 = (t.loc[x, "urban creek (Houston)"] for x in ("v6_wind_q", "v10_dnorm_x_p50", CURRENT, "v11_rain_obs"))
    text(sl, 0.5, 1.0, 12.3, 2.9, [
        f"From water level only to water level + wind + discharge: {t.loc['v3_obs','all']:.1f} to {a0:.1f} cm over all stations, nearly all of it from wind and at tide gauges, estuaries and lakes.",
        "",
        "Three options were compared:",
        f"A.  Water level + wind + discharge, without rainfall. All stations {a0:.1f} cm, urban creeks {u0:.1f} cm.",
        f"B.  Same inputs, with 6 h-change scaling and gap filling. All stations {a1:.1f} cm ({100 * (a1 / a0 - 1):+.0f}%); large rivers much better (the {int(big.sum())} rivers whose level ranges over metres: median {np.median(r6['q'][big]):.1f} to {np.median(r6['base'][big]):.1f} cm); "
        f"{b2} stations better, {w2} worse; urban creeks {u1:.1f} cm. No new data.",
        f"C.  B with rainfall (MRMS for the past 72 h, HRRR forecast for the next 6 h), trained to cope with missing hours, five models with different random seeds averaged. All stations {a2:.1f} cm ({100 * (a2 / a0 - 1):+.0f}%), urban creeks {u2:.1f} cm ({100 * (u2 / u0 - 1):+.0f}%); {b3} stations better, {w3} worse.",
    ], size=12)
    hilite(sl, 0.42, 3.05, 12.45, 0.62)
    text(sl, 0.5, 3.09, 12.3, 0.6, [
        "The version that is run: C. The forecast script builds all of its inputs in real time; one forecast from the real-time services, for 12 November 2026, was checked against the observations. "
        "It is run from a separate directory and is not connected to the group's forecast website."], size=12, bold=True)
    text(sl, 0.5, 3.95, 12.3, 2.5, [
        f"With exact rainfall one model with scaling and gap filling reaches {a3:.1f} cm over all stations and {u3:.1f} cm at urban creeks. The distance between C and that number is rainfall-forecast error, not model error: "
        "a better short-range rainfall forecast (radar-based nowcast) can replace HRRR later without changing the model.",
        "",
                "Open points:",
        "1.  Rainfall should be switched off at gate-controlled stations such as the Pearl River locks, where it misleads the model.",
        "2.  HRRR will be replaced by RRFS at a date not yet announced; the next-6 h rainfall input then has to be retrained with RRFS forecasts.",
        "3.  The forecast is started by hand; it is not scheduled and not connected to the group's website.",
    ], size=12)

    ids = prs.slides._sldIdLst
    els = list(ids)
    for el in els:
        ids.remove(el)
    for _, _, el in sorted(zip(groups, range(len(els)), els), key=lambda z: z[:2]):
        ids.append(el)
    out = F / "version_comparison.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = F / f"version_comparison_{datetime.date.today():%Y%m%d}.pptx"; prs.save(out)
    pd.DataFrame(summary).round(2).to_csv(F / "stations_summary.csv", index=False)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
