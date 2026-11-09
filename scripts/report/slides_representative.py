"""deliverable 10: slide deck of the representative stations (white background, black Times New Roman, no title page).

Reads deliverables/10_representative/{summary.csv, map.png, range_<domain>.png, <prefix>_<station>.png}
and writes deliverables/10_representative/representative_stations.pptx.
Usage: python slides_representative.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "10_representative"
FONT = "Times New Roman"
BLACK = RGBColor(0, 0, 0)
PREFIX = {"Louisiana100m": "la", "Galveston100m": "gal", "Texas100m": "tx"}
HURR = {"Louisiana100m": "Francine (Sep 2024)", "Galveston100m": "Beryl (Jul 2024)", "Texas100m": "Beryl (Jul 2024)"}
TYPE_EN = {"tide gauge": "tide gauge", "marsh": "marsh (CRMS)", "estuary / tidal channel": "estuary / tidal channel", "river / canal": "river", "urban creek (Houston)": "urban creek (Houston)"}
NOTE = {  # one line per station, written from the event plots
    "8761724": "Open coast. Tide dominates; both models within 4 cm except the Francine surge hours.",
    "8761927": "Lake Pontchartrain. Wind set-up is the main signal; wind input halves the error on windy days.",
    "8747437": "Mississippi Sound. Francine surge of 1.75 m followed by the wind model; the water-level-only model overshoots to 2.4 m.",
    "CRMS0367-H01": "Terrebonne marsh, slow water. Errors under 1 cm in quiet weeks; Francine window 5 cm.",
    "CRMS0517-H01": "Teche/Vermilion marsh. One of the largest wind gains among marsh stations (12.9 to 9.7 cm over the year).",
    "07387050": "Vermilion Bay. Shallow bay pushed by wind; hurricane window 18.6 cm, normal 6.4 cm.",
    "301429089145600": "Mississippi Sound light. Storm set-up resolved by the wind model.",
    "07381590": "Wax Lake Outlet, Atchafalaya distributary. River plus tide; Francine window 16 cm, otherwise 2 to 5 cm.",
    "07374000": "Lower Mississippi. Water-level-only model is better here (3.7 vs 4.6 cm): wind is noise for a far-inland river station.",
    "07379050": "Baton Rouge urban creek. Flash rises of 3 m in two hours are not forecastable from level, wind or discharge; rain is missing.",
    "8771450": "Galveston Pier 21. Beryl window 12 cm (water-level-only 15 cm); normal weeks 5 cm.",
    "8770613": "Upper Galveston Bay. Beryl surge of 2.1 m followed by the wind model (14.7 cm vs 27.6 cm water-level-only).",
    "08072050": "San Jacinto River above the bay. Tide plus Lake Houston releases; Beryl window 26 cm.",
    "08074000": "Buffalo Bayou downtown. Beryl rise of 7 m: the 6 h forecast reaches 8.3 m of 9.9 m; recession well captured.",
    "08114000": "Brazos River at Richmond. Same-river upstream discharge helps every month; a false 5 m spike during Beryl remains (wind).",
    "08066250": "Trinity River below Lake Livingston dam. Releases are scheduled; no input anticipates them.",
    "08068310": "Spring Creek, The Woodlands. Typical Houston creek: quiet weeks 12 cm, Beryl 46 cm.",
    "08074500": "Whiteoak Bayou, Houston. Largest errors in the set: 33 cm over the year, 130 cm in the Beryl window.",
    "8774770": "Rockport, Aransas Bay. Best station class: 2 cm over the year, 3 cm during Beryl.",
    "8773259": "Port Lavaca, Matagorda Bay. Beryl window 16 cm, otherwise 5 cm.",
    "08188810": "Lower Guadalupe, tidal. Hurricane window 10.5 cm; river rises 2 cm.",
    "08211500": "Nueces River at Calallen, below the saltwater dam. Nearly flat; 2.4 cm over the year.",
    "08176500": "Guadalupe River at Victoria. Inland river; errors concentrate in the first hours of each rise (June 2025 flood).",
}


def text(slide, x, y, w, h, s, size=14, bold=False, align=PP_ALIGN.LEFT, color=BLACK):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.03)
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = line
        r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color
    return tb


def slide_number(slide, n):
    text(slide, 12.5, 7.05, 0.6, 0.3, str(n), size=10, align=PP_ALIGN.RIGHT)


def fmt(v):
    return "–" if pd.isna(v) else f"{v:.1f}"


def main() -> None:
    s = pd.read_csv(D / "summary.csv", dtype={"station_id": str})
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    n = 0

    # 1. overview: map
    n += 1; sl = prs.slides.add_slide(blank)
    text(sl, 0.5, 0.35, 12.3, 0.5, "Representative stations: 1–6 h water-level forecasts of the LSTM (inputs: water level, wind, upstream discharge)", size=18, bold=True)
    sl.shapes.add_picture(str(D / "map.png"), Inches(0.85), Inches(0.95), width=Inches(11.6))
    cnt = s.groupby(["domain", "type"]).size()
    lines = ["Test period 2024-01 to 2025-12. Forecasts issued every hour; the plots show the 1–6 h trajectory issued every 6 h.",
             "Louisiana100m: " + ", ".join(f"{cnt[('Louisiana100m', t)]} {TYPE_EN[t]}" for t in TYPE_EN if ("Louisiana100m", t) in cnt) + ".",
             "Galveston100m: " + ", ".join(f"{cnt[('Galveston100m', t)]} {TYPE_EN[t]}" for t in TYPE_EN if ("Galveston100m", t) in cnt) + ".",
             "Texas100m: " + ", ".join(f"{cnt[('Texas100m', t)]} {TYPE_EN[t]}" for t in TYPE_EN if ("Texas100m", t) in cnt) + "."]
    text(sl, 0.5, 6.05, 12.3, 1.0, lines, size=11)
    slide_number(sl, n)

    # 2. how to read
    n += 1; sl = prs.slides.add_slide(blank)
    text(sl, 0.5, 0.35, 12.3, 0.5, "How to read the station slides", size=18, bold=True)
    text(sl, 0.5, 1.1, 12.3, 5.5, [
        "Each station slide has three 4-day windows from the test period:",
        "   hurricane — Francine (10–14 Sep 2024) for Louisiana100m, Beryl (7–11 Jul 2024) for Galveston100m and Texas100m;",
        "   high water — the 4 days around the highest observed level outside the hurricane;",
        "   normal — 4 days whose 6 h error equals the station's whole-year error.",
        "",
        "Black: observation. Red: the LSTM with water level + wind + upstream discharge, 1–6 h forecast issued every 6 h, drawn from the observation at the issue time.",
        "Blue dashed: the same LSTM trained on water level alone (no wind, no discharge), same issue times.",
        "The RMSE in each window title uses every hourly issue time in the window, not only the drawn ones.",
        "",
        "Whole-year RMSE is the test-period RMSE of all hourly forecasts (2024-01 to 2025-12). All errors in cm.",
        "Where no red line is drawn, the past 72 h of observations or wind were too incomplete to issue a forecast.",
    ], size=13)
    slide_number(sl, n)

    # 3. per domain: range chart + station slides
    for dom in ["Louisiana100m", "Galveston100m", "Texas100m"]:
        g = s[s.domain == dom]
        n += 1; sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.35, 12.3, 0.5, f"{dom}: 6 h RMSE of the representative stations", size=18, bold=True)
        from PIL import Image
        iw, ih = Image.open(D / f"range_{dom}.png").size
        wpic = 8.6; hpic = wpic * ih / iw
        if hpic > 5.8:
            hpic = 5.8; wpic = hpic * iw / ih
        sl.shapes.add_picture(str(D / f"range_{dom}.png"), Inches(0.5), Inches(1.0), width=Inches(wpic))
        med = g.r6_new.median(); best = g.loc[g.r6_new.idxmin()]; worst = g.loc[g.r6_new.idxmax()]
        text(sl, 9.4, 1.1, 3.5, 5.5, [
            f"Hurricane window: {HURR[dom]}.",
            "",
            f"Whole-year 6 h RMSE from {best.r6_new:.1f} cm ({best['short']}) to {worst.r6_new:.1f} cm ({worst['short']}).",
            "",
            "Tide gauges, marsh and estuaries: hurricane windows 2 to 3 times the whole-year error; the wind input reduces them most.",
            "",
            "Rivers and creeks: the high-water or hurricane window is 5 to 10 times the whole-year error; errors sit in the first hours of each rise.",
            "",
            "Log scale.",
        ], size=12)
        slide_number(sl, n)
        for _, r in g.iterrows():
            n += 1; sl = prs.slides.add_slide(blank)
            text(sl, 0.5, 0.3, 12.3, 0.5, f"{r['short']}  —  {r['name']}  ({r.source} {r.station_id})", size=16, bold=True)
            text(sl, 0.5, 0.75, 8.6, 0.3, f"{dom} · {TYPE_EN[r.type]} · {r.lat:.3f}°N {abs(r.lon):.3f}°W", size=11)
            img = D / f"{PREFIX[dom]}_{r.station_id}.png"
            sl.shapes.add_picture(str(img), Inches(0.4), Inches(1.1), height=Inches(6.1))
            x = 9.1
            text(sl, x, 1.15, 3.8, 0.3, "6 h RMSE, cm", size=12, bold=True)
            rows = [("whole year, with wind + discharge", fmt(r.r6_new)), ("whole year, water level only", fmt(r.r6_obs)),
                    (f"hurricane window ({r.hurricane_start})", fmt(r["hurricane_6h"])),
                    (f"high-water window ({r.high_water_start})", fmt(r["high water_6h"])),
                    (f"normal window ({r.normal_start})", fmt(r["normal_6h"]))]
            y = 1.5
            for lab, val in rows:
                text(sl, x, y, 3.0, 0.3, lab, size=11); text(sl, x + 3.0, y, 0.8, 0.3, val, size=11, align=PP_ALIGN.RIGHT); y += 0.32
            text(sl, x, y + 0.1, 3.8, 0.3, "1 / 3 / 6 h, whole year, with wind + discharge", size=12, bold=True)
            text(sl, x, y + 0.42, 3.8, 0.3, f"{r.r1_new:.1f} / {r.r3_new:.1f} / {r.r6_new:.1f} cm", size=11)
            text(sl, x, y + 1.0, 3.8, 2.6, NOTE.get(r.station_id, ""), size=11)
            slide_number(sl, n)

    # 4. summary table (one slide per domain)
    for dom in ["Louisiana100m", "Galveston100m", "Texas100m"]:
        g = s[s.domain == dom]
        n += 1; sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.35, 12.3, 0.5, f"{dom}: summary (6 h RMSE, cm)", size=18, bold=True)
        cols = ["station", "type", "year, wind + discharge", "year, level only", "hurricane", "high water", "normal", "1 h", "3 h"]
        tbl = sl.shapes.add_table(len(g) + 1, len(cols), Inches(0.5), Inches(1.1), Inches(12.3), Inches(0.4 * (len(g) + 1))).table
        widths = [2.7, 2.1, 1.7, 1.2, 1.1, 1.2, 1.0, 0.6, 0.7]
        for j, wdt in enumerate(widths):
            tbl.columns[j].width = Inches(wdt)
        def cell(i, j, v, bold=False, align=PP_ALIGN.LEFT):
            c = tbl.cell(i, j); c.text = ""; c.fill.background()
            c.margin_left = c.margin_right = Inches(0.05); c.margin_top = c.margin_bottom = Inches(0.02)
            p = c.text_frame.paragraphs[0]; p.alignment = align
            rr = p.add_run(); rr.text = str(v); rr.font.name = FONT; rr.font.size = Pt(11); rr.font.bold = bold; rr.font.color.rgb = BLACK
        for j, c0 in enumerate(cols):
            cell(0, j, c0, bold=True, align=PP_ALIGN.LEFT if j < 2 else PP_ALIGN.RIGHT)
        for i, (_, r) in enumerate(g.iterrows(), start=1):
            vals = [r["short"], TYPE_EN[r.type], fmt(r.r6_new), fmt(r.r6_obs), fmt(r["hurricane_6h"]), fmt(r["high water_6h"]), fmt(r["normal_6h"]), fmt(r.r1_new), fmt(r.r3_new)]
            for j, v in enumerate(vals):
                cell(i, j, v, align=PP_ALIGN.LEFT if j < 2 else PP_ALIGN.RIGHT)
        # plain table style: remove banding by setting all fills to none already; borders stay default
        text(sl, 0.5, 1.2 + 0.4 * (len(g) + 1) + 0.2, 12.3, 0.6, f"Hurricane window: {HURR[dom]}. year = whole test period 2024-01 to 2025-12; windows = 4 days; all values are 6 h RMSE of the LSTM with wind + discharge except the level-only column.", size=11)
        slide_number(sl, n)

    # 5. what the set shows
    n += 1; sl = prs.slides.add_slide(blank)
    text(sl, 0.5, 0.35, 12.3, 0.5, "What the 23 stations show", size=18, bold=True)
    tide = s[s.type.isin(["tide gauge", "marsh", "estuary / tidal channel"])]; riv = s[s.type.isin(["river / canal", "urban creek (Houston)"])]
    text(sl, 0.5, 1.1, 12.3, 5.8, [
        f"Tide gauges, marsh, estuaries ({len(tide)} stations): whole-year 6 h RMSE {tide.r6_new.min():.1f}–{tide.r6_new.max():.1f} cm; "
        f"hurricane windows {tide['hurricane_6h'].min():.1f}–{tide['hurricane_6h'].max():.1f} cm. The wind input gives most of the improvement over the water-level-only model, and it shows in the surge hours (Bay Waveland, Morgans Point).",
        "",
        f"Rivers ({len(riv[riv.type == 'river / canal'])} stations): whole-year 2–11 cm. Large rivers are quiet most of the year; the first hours of a rise carry the error. Upstream discharge helps mid-river stations (Brazos Richmond); it cannot anticipate dam releases (Trinity Goodrich). For the far-inland Mississippi the wind input only adds noise.",
        "",
        f"Urban creeks and small creeks ({len(riv[riv.type == 'urban creek (Houston)']) + 1} stations incl. Ward Creek): whole-year 13–33 cm, hurricane windows 30–130 cm. Flash rises from local rainfall are not visible in any current input.",
        "",
        "Normal 4-day windows equal the whole-year RMSE at every station: the whole-year number describes ordinary days; event skill has to be read from the event windows.",
    ], size=13)
    slide_number(sl, n)

    out = D / "representative_stations.pptx"
    try:
        prs.save(out)
    except PermissionError:                       # the deck is open in PowerPoint: write a dated copy instead
        import datetime
        out = D / f"representative_stations_{datetime.date.today():%Y%m%d}.pptx"
        prs.save(out)
    print("->", out, n, "slides")


if __name__ == "__main__":
    main()
