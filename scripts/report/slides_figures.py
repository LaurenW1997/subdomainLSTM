"""Slide deck of the publication-style figures (deliverable 11): white background, black Times New Roman,
no title page, one figure per slide with one or two sentences.

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
    "8761724": "Open coast. Tide dominates; 3.7 cm over the year, 8 cm in the Francine surge hours.",
    "8761927": "Lake Pontchartrain. Wind set-up is the main signal; the wind input cuts the error by a third (6.8 vs 9.6 cm in the Francine window).",
    "8747437": "Mississippi Sound. The 1.8 m Francine surge is followed at all leads: 10 cm with wind, 33 cm without.",
    "07387050": "Vermilion Bay. Shallow bay pushed by wind; the hurricane window is three times the normal error.",
    "301429089145600": "Mississippi Sound light. Storm set-up resolved by the wind input (11 vs 26 cm in the Francine window).",
    "07381590": "Wax Lake Outlet, Atchafalaya distributary. River plus tide; Francine window 14 cm, otherwise 2 to 5 cm.",
    "07374000": "Lower Mississippi, far inland. Wind input switched off here; the water-level-only model is still better (3.7 vs 4.8 cm): the slow river needs no extra input.",
    "07379050": "Baton Rouge urban creek. Rises of 3 m in two hours from local rainfall; the 6 h forecast cannot see them coming (84 cm in the high-water window).",
    "8771450": "Galveston Pier 21. Beryl window 12 cm (15 without wind); normal weeks 5 cm.",
    "8770613": "Upper Galveston Bay. The 2.1 m Beryl surge is followed at all leads (15 cm vs 28 cm without wind).",
    "08072050": "San Jacinto River above the bay. Tide plus Lake Houston releases; Beryl window 20 cm (38 without wind).",
    "08074000": "Buffalo Bayou downtown. Beryl rise of 9 m: 1 h forecast on time, 3 h two hours late, 6 h five hours late; recession well captured.",
    "08114000": "Brazos River at Richmond. Wind switched off, upstream discharge kept: 4.6 cm over the year; Beryl window 31 cm from the river flood.",
    "08066250": "Trinity River below Lake Livingston dam. Releases are scheduled by the operator; no input anticipates them.",
    "08068310": "Spring Creek, The Woodlands. Typical Houston creek: quiet weeks 12 cm, Beryl window 42 cm.",
    "08074500": "Whiteoak Bayou, Houston. Largest errors in the set: 33 cm over the year, 144 cm in the Beryl window.",
    "8774770": "Rockport, Aransas Bay. Best station class: 2 cm over the year, 3.5 cm during Beryl.",
    "8773259": "Port Lavaca, Matagorda Bay. Beryl window 16 cm, otherwise 5 cm.",
    "08188810": "Lower Guadalupe, tidal. Hurricane window 10 cm; river rises 2 cm.",
    "08211500": "Nueces River at Calallen, below the saltwater dam. Nearly flat; 2.4 cm over the year.",
    "08176500": "Guadalupe River at Victoria. Inland river; errors sit in the first hours of each rise.",
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

    per = pd.read_csv(REPO / "runs" / "v6_wind_q" / "per_station_test.csv", dtype={"station_id": str})
    n_all = int(((per.n_6h >= 720) & (per.source != "CRMS")).sum())
    sl = new(f"Where the 6 h forecast error is: {n_all} stations, test period January 2024 to December 2025")
    picture(sl, F / "rmse_map.png", 0.5, 0.95, 12.3, 5.1)
    text(sl, 0.5, 6.2, 12.3, 1.0, ["LSTM with water level, wind (past 72 h and next 6 h) and upstream discharge as inputs; wind switched off at 15 inland river stations where it only added noise. Colour: RMSE of the 6 h forecast over the whole test period. "
                                    f"Squares: the {len(st)} stations shown on the following slides. CRMS marsh stations are not shown (training only, not operational).",
                                    "Open-coast and bay gauges are mostly below 5 cm; the Houston creeks and the small creeks around Baton Rouge are above 10 cm."], size=12)

    sl = new("Error grows with lead time; wind and discharge help the tidal station types, not the creeks")
    picture(sl, F / "rmse_vs_lead.png", 0.5, 0.95, 8.3, 5.8)
    text(sl, 9.1, 1.1, 3.8, 5.5, ["Median RMSE over the stations of each type, 1 to 6 h lead. Solid: with wind and upstream discharge. Dashed: water level only. Shading: interquartile range.",
                                   "", "Tide gauges, lakes and estuaries: the inputs lower the error at every lead, most at 4 to 6 h.",
                                   "", "Rivers: small gain in the median; mid-river stations gain, the far-inland ones run without wind.",
                                   "", "Urban creeks: no change. Flash rises from local rainfall are not visible in any current input."], size=12)

    sl = new("Spread across stations within each type")
    picture(sl, F / "rmse_box_by_type.png", 0.5, 0.95, 12.3, 5.2)
    text(sl, 0.5, 6.25, 12.3, 0.9, ["Per-station 6 h RMSE, whole test period, CRMS marsh stations excluded. White: water level only. Grey: with wind and upstream discharge.",
                                    "For tide gauges, lakes and estuaries the whole distribution shifts down; for rivers and urban creeks the two distributions overlap."], size=12)

    sl = new("How to read the station slides")
    text(sl, 0.5, 1.1, 12.3, 5.5, [
        "Each station: three 4-day windows from the test period, side by side.",
        "   (a) hurricane — Francine, 10 to 13 September 2024, for Louisiana100m; Beryl, 7 to 10 July 2024, for Galveston100m and Texas100m;",
        "   (b) high water — the 4 days around the highest observed level outside the hurricane;",
        "   (c) normal — 4 days whose 6 h error equals the station's whole-year error.",
        "",
        "Black: observation. Blue lines, light to dark: the forecast valid at each hour that was issued 1, 3 and 6 hours earlier.",
        "A 6 h line that lags the observation by several hours means the model only reacts once the rise is already visible in the past data.",
        "Grey band: 24 hours around the window peak. RMSE in each panel title: all hourly forecasts in that window.",
        "",
        "Below each figure: whole-year 6 h RMSE with and without the wind and discharge inputs, and the three window values.",
        "All errors in cm. Water levels in metres above each station's own datum.",
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
            rows = [("", "with wind + discharge", "water level only"),
                    ("whole year 2024–2025", f"{r.r6_new:.1f}", f"{r.r6_obs:.1f}"),
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
        f"Tide gauges and estuaries ({len(tide)} stations): whole-year 6 h RMSE {tide.r6_new.min():.1f} to {tide[tide.station_id != '08074000'].r6_new.max():.1f} cm (Buffalo Bayou downtown, a tidal urban bayou, 28 cm). Hurricane windows are two to three times the whole-year value. The wind input gives most of the improvement over the water-level-only model and it shows in the surge hours (Bay Waveland, Morgans Point).",
        "",
        f"Rivers ({len(riv)} stations): whole-year 2 to 11 cm. Large rivers are quiet most of the year; the first hours of a rise carry the error. Upstream discharge helps mid-river stations (Brazos at Richmond) and cannot anticipate dam releases (Trinity below Lake Livingston). At the far-inland rivers (Mississippi at Baton Rouge, Brazos) the wind input is switched off.",
        "",
        f"Urban and small creeks ({len(urb) + 1} stations including Ward Creek): whole-year 13 to 33 cm, hurricane windows 30 to 130 cm. The forecast lags the rise by about its own lead time: a 6 h forecast reacts six hours late. Local rainfall, the cause of these rises, is not among the inputs.",
        "",
        "The normal 4-day window equals the whole-year RMSE at every station: the whole-year number describes ordinary days, and event skill has to be read from the event windows.",
    ], size=13)

    out = F / "forecast_figures.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = F / f"forecast_figures_{datetime.date.today():%Y%m%d}.pptx"; prs.save(out)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
