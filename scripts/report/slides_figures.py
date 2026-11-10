"""Slide deck of the publication-style figures (deliverable 11): white background, black Times New Roman,
no title page, one figure per slide with one or two sentences.

Version of 2026-11-10: main model = water level + wind + upstream discharge + rainfall (AORC observed, past 72 h and next 6 h),
compared with the operational model (no rainfall). The observed future rainfall is an upper bound; the slides say so.

Reads deliverables/11_figures/{rmse_map, rmse_vs_lead, rmse_box_by_type, station_<id>}.png,
deliverables/11_figures/data/<prefix>_<id>.csv (window series) and deliverables/10_representative/stations.csv.
Writes deliverables/11_figures/forecast_figures.pptx.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[2]
F = REPO / "deliverables" / "11_figures"
R = REPO / "deliverables" / "10_representative"
FONT = "Times New Roman"; BLACK = RGBColor(0, 0, 0)
PREFIX = {"Louisiana100m": "la", "Galveston100m": "gal", "Texas100m": "tx"}
HURR = {"Louisiana100m": "Francine, September 2024", "Galveston100m": "Beryl, July 2024", "Texas100m": "Beryl, July 2024"}
TYPE_EN = {"tide gauge": "tide gauge", "marsh": "marsh (USGS)", "estuary / tidal channel": "estuary / tidal channel", "river / canal": "river", "urban creek (Houston)": "urban creek (Houston)"}
NOTE = {
    "8761724": "Open coast. Tide dominates; rainfall adds nothing here (3.7 cm with and without). Francine window 6.6 cm.",
    "8761927": "Lake Pontchartrain. Wind set-up is the main signal; 3.8 cm over the year, 5.4 cm in the Francine window.",
    "8747437": "Mississippi Sound. The 1.8 m Francine surge is followed at all leads (12 cm). Rainfall makes no difference at open-water gauges.",
    "07387050": "Vermilion Bay. Shallow bay pushed by wind; Francine window 18.5 cm, two to three times the normal error.",
    "301429089145600": "Mississippi Sound light. Storm set-up is carried by the wind input; rainfall changes nothing (5.8 vs 5.9 cm).",
    "07381590": "Wax Lake Outlet, Atchafalaya distributary. River plus tide; Francine window 19 cm, otherwise 3 to 5 cm.",
    "07374000": "Lower Mississippi, far inland; wind input switched off. 4.5 cm over the year: a slow river that needs little beyond its own level.",
    "07379050": "Baton Rouge urban creek. With observed rainfall the 6 h error falls from 24.8 to 10.2 cm over the year and from 84 to 23 cm in the high-water window: the rise is forecast before it starts.",
    "8771450": "Galveston Pier 21. Beryl window 9 cm; normal weeks 5 cm. No effect of rainfall.",
    "8770613": "Upper Galveston Bay. The 2.1 m Beryl surge is followed at all leads (17 cm); 5.9 cm over the year.",
    "08072050": "San Jacinto River above the bay. Tide plus Lake Houston releases; the releases are in no input and rainfall does not help (8.7 vs 8.3 cm).",
    "08074000": "Buffalo Bayou downtown. Beryl rise of 9 m: 6 h error 43 cm with observed rainfall, 103 cm without. Whole year 18.2 vs 27.9 cm.",
    "08114000": "Brazos River at Richmond. Large river, wind switched off. 4.8 cm over the year, rainfall makes no difference; Beryl window 19 cm.",
    "08066250": "Trinity River below Lake Livingston dam. Releases are scheduled by the operator; rainfall does not anticipate them (9.7 vs 10.5 cm).",
    "08068310": "Spring Creek, The Woodlands. Typical Houston creek: 7.5 cm with observed rainfall, 12.9 cm without; Beryl window 19 vs 42 cm.",
    "08074500": "Whiteoak Bayou, Houston. Largest errors in the set: 20 cm over the year with rainfall (33 without), Beryl window 60 cm (144 without).",
    "8774770": "Rockport, Aransas Bay. Best station class: 2 cm over the year, 3 cm during Beryl.",
    "8773259": "Port Lavaca, Matagorda Bay. Beryl window 18 cm, otherwise 5 cm.",
    "08188810": "Lower Guadalupe, tidal. Hurricane window 10 cm; river rises 2 cm.",
    "08211500": "Nueces River at Calallen, below the saltwater dam. Nearly flat; 2.4 cm over the year.",
    "08176500": "Guadalupe River at Victoria. Inland river; rainfall lowers the whole-year error from 9.3 to 7.9 cm.",
}


def text(slide, x, y, w, h, s, size=13, bold=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, line in enumerate(s if isinstance(s, list) else [s]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
        r = p.add_run(); r.text = line; r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = BLACK
    return tb


def picture(slide, path, x, y, max_w, max_h):
    iw, ih = Image.open(path).size
    w = max_w; h = w * ih / iw
    if h > max_h:
        h = max_h; w = h * iw / ih
    slide.shapes.add_picture(str(path), Inches(x + (max_w - w) / 2), Inches(y), width=Inches(w))
    return y + h


def rmse(a, b):
    d = (a - b).dropna(); return float(np.sqrt((d ** 2).mean())) * 100 if len(d) else np.nan


def main() -> None:
    st = pd.read_csv(R / "stations.csv", dtype={"station_id": str})
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]
    n = 0

    def new(title):
        nonlocal n
        n += 1; sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=17, bold=True)
        text(sl, 12.5, 7.05, 0.6, 0.3, str(n), size=10, align=PP_ALIGN.RIGHT)
        return sl

    per = pd.read_csv(REPO / "runs" / "v7_rain_p15" / "per_station_test.csv", dtype={"station_id": str})
    n_all = int(((per.n_6h >= 720) & (per.source != "CRMS")).sum())
    sl = new(f"6 h forecast error with rainfall as an input: {n_all} stations, January 2024 to December 2025")
    picture(sl, F / "rmse_map.png", 0.5, 0.95, 12.3, 5.0)
    text(sl, 0.5, 6.05, 12.3, 1.2, ["LSTM inputs: water level, wind, upstream discharge and rainfall (15 km mean around the station), each for the past 72 h; wind and rainfall also for the next 6 h. "
                                    f"Colour: RMSE of the 6 h forecast over the test period. Squares: the {len(st)} stations on the following slides.",
                                    "The rainfall is observed (AORC analysis), including the next 6 h. A real-time system only has a rainfall forecast for those hours, "
                                    "so every number in this deck is the best case with a perfect rainfall forecast. The last slide gives the result with HRRR forecast rainfall."], size=12)

    sl = new("Rainfall removes much of the urban-creek and river error; tidal station types do not change")
    picture(sl, F / "rmse_vs_lead.png", 0.5, 0.95, 8.3, 5.8)
    text(sl, 9.1, 1.1, 3.8, 5.5, ["Median RMSE over the stations of each type, 1 to 6 h lead. Solid: with rainfall (observed, incl. next 6 h). Dashed: without rainfall. Shading: interquartile range.",
                                   "", "Urban creeks (Houston): 6 h median 12.9 to 7.9 cm. The gain grows with lead time because the rain of the next hours decides the rise.",
                                   "", "Rivers: 5.7 to 5.1 cm; small creeks gain most, large rivers little.",
                                   "", "Tide gauges, lakes, marsh, estuaries: within 0.1 cm. No station type gets worse."], size=12)

    sl = new("Spread across stations within each type")
    picture(sl, F / "rmse_box_by_type.png", 0.5, 0.95, 12.3, 5.2)
    text(sl, 0.5, 6.25, 12.3, 0.9, ["Per-station 6 h RMSE, whole test period, CRMS marsh stations excluded. White: without rainfall. Grey: with rainfall (observed, incl. next 6 h).",
                                    "For urban creeks the whole distribution moves down; for rivers the upper half moves down; the tidal types overlap."], size=12)

    sl = new("How to read the station slides")
    text(sl, 0.5, 1.1, 12.3, 5.7, [
        "Each station: three 4-day windows from the test period, side by side.",
        "   (a) hurricane — Francine, 10 to 13 September 2024, for Louisiana100m; Beryl, 7 to 10 July 2024, for Galveston100m and Texas100m;",
        "   (b) high water — the 4 days around the highest observed level outside the hurricane;",
        "   (c) normal — 4 days whose 6 h error equals the station's whole-year error.",
        "",
        "Black: observation. Blue lines, light to dark: the forecast valid at each hour that was issued 1, 3 and 6 hours earlier (model with rainfall).",
        "Grey band: 24 hours around the window peak. RMSE in each panel title: all hourly forecasts in that window.",
        "",
        "Below each figure: whole-year 6 h RMSE with and without the rainfall input, and the three window values.",
        "All errors in cm. Water levels in metres above each station's own datum.",
        "",
        "Rainfall of the next 6 h is taken from observations in all of these figures: best case, not what a real-time forecast would give.",
    ], size=13)

    for dom in ["Louisiana100m", "Galveston100m", "Texas100m"]:
        g = st[st.domain == dom]
        for _, r in g.iterrows():
            sl = new(f"{r['name']}  ({r.source} {r.station_id})  —  {dom}, {TYPE_EN[r.type]}")
            y = picture(sl, F / f"station_{r.station_id}.png", 0.4, 0.9, 12.5, 3.8)
            d = pd.read_csv(F / "data" / f"{PREFIX[dom]}_{r.station_id}.csv", parse_dates=["time"])
            wins = list(dict.fromkeys(d.window))
            vals = {}
            for w in wins:
                dd = d[d.window == w]; key = "hurricane" if w.startswith("hurricane") else ("high water" if w.startswith("high") else "normal")
                vals[key] = (rmse(dd.f6, dd.obs), rmse(dd.b6, dd.obs) if "b6" in dd else np.nan)
            y0 = y + 0.25
            text(sl, 0.5, y0, 6.0, 0.3, "6 h RMSE, cm", size=12, bold=True)
            rows = [("", "with rainfall", "without rainfall"),
                    ("whole year 2024–2025", f"{r.r6_new:.1f}", f"{r.r6_base:.1f}"),
                    (f"hurricane window", f"{vals['hurricane'][0]:.1f}", f"{vals['hurricane'][1]:.1f}"),
                    ("high-water window", f"{vals['high water'][0]:.1f}", f"{vals['high water'][1]:.1f}"),
                    ("normal window", f"{vals['normal'][0]:.1f}", f"{vals['normal'][1]:.1f}")]
            yy = y0 + 0.35
            for i, (a, b, c) in enumerate(rows):
                text(sl, 0.5, yy, 2.6, 0.28, a, size=11, bold=(i == 0)); text(sl, 3.1, yy, 1.9, 0.28, b, size=11, bold=(i == 0), align=PP_ALIGN.RIGHT); text(sl, 5.0, yy, 1.6, 0.28, c, size=11, bold=(i == 0), align=PP_ALIGN.RIGHT)
                yy += 0.3
            text(sl, 7.2, y0, 5.7, 2.0, NOTE.get(r.station_id, ""), size=12)

    sl = new(f"What the {len(st)} stations show")
    tide = st[st.type.isin(["tide gauge", "estuary / tidal channel"])]; riv = st[st.type == "river / canal"]; urb = st[st.type == "urban creek (Houston)"]
    text(sl, 0.5, 1.1, 12.3, 5.8, [
        f"Tide gauges and estuaries ({len(tide)} stations): rainfall changes nothing, 2 to 9 cm over the year with and without. The exception is Buffalo Bayou downtown, a tidal urban bayou: 27.9 to 18.2 cm.",
        "",
        f"Rivers ({len(riv)} stations): large rivers do not change (Mississippi, Brazos, Trinity below the dam). Small rain-fed rivers and creeks gain: Ward Creek 24.8 to 10.2 cm, Guadalupe at Victoria 9.3 to 7.9 cm.",
        "",
        f"Urban creeks ({len(urb)} stations in this set, 71 in the test set): Spring Creek 12.9 to 7.5 cm, Whiteoak Bayou 33 to 20 cm. In the Beryl window the 6 h error is cut by more than half. "
        "With the rainfall of the next hours known, the forecast rises with the observation instead of six hours after it.",
        "",
        "What rainfall does not fix: releases from reservoirs (San Jacinto below Lake Houston, Trinity below Lake Livingston) and the largest flash rises, where 20 to 60 cm of error remain.",
    ], size=13)

    sl = new("With a real rainfall forecast the gain is not there yet")
    text(sl, 0.5, 1.1, 12.3, 5.8, [
        "All previous slides use observed rainfall for the next 6 h. The same model was re-tested with HRRR forecast rainfall in that slot (test period 2024 to 2025, all 847 stations, 6 h RMSE over all samples):",
        "",
        "      without rainfall (current operational inputs)                                 7.65 cm",
        "      with rainfall, next 6 h observed (perfect forecast)                         5.95 cm",
        "      with rainfall, next 6 h from the HRRR cycle issued at forecast time      7.39 cm",
        "      with rainfall, next 6 h from the HRRR cycle issued 1 h earlier              7.66 cm",
        "",
        "HRRR has the right amount of rain over 6 h (correlation 0.67 with observations in a 15 km box) but not the right hour and place (0.3 to 0.4 hour by hour). "
        "A model trained on observed rainfall trusts the forecast too much and follows its errors.",
        "",
        "Next step, in progress: train the model with HRRR forecast rainfall for the next 6 h, hourly or as a 6 h total, over a 15 km or 45 km box, so that it learns how far to trust the forecast.",
        "",
        "Operational model for now: water level + wind + upstream discharge, without rainfall.",
    ], size=13)

    out = F / "forecast_figures.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = F / f"forecast_figures_{datetime.date.today():%Y%m%d}.pptx"; prs.save(out)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
