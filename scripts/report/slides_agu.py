"""Two slides for AGU on the water-level model that is run (mean of five LSTMs; inputs water level, wind, rainfall, river discharge).

Slide 1: the data and the model (numbers, map of the gauges, block diagram).
Slide 2: validation in two parts. The hurricanes Beryl and Francine of 2024 (three gauges with the time of landfall, every
         forecast 6 h ahead of all gauges against the observation) and one week of forecasts made from the real-time data
         feeds, 14 to 20 November 2026 (four gauges); one table with the RMSE of both parts.
White background, black Times New Roman, no title page, no page numbers.
Input : deliverables/37_agu/ (figures and agu_numbers.json of agu_figs.py)
Output: deliverables/37_agu_lstm.pptx
Usage : python slides_agu.py [--out FILE]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from slides_figures import BLACK, FONT, picture, text

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "37_agu"
C, L, R = PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.RIGHT
KINDS = ["Tide gauges", "Estuaries", "Lakes", "Rivers", "Urban creeks"]


def heading(sl, x, y, w, bold: str, rest: str, size: float = 13) -> None:
    """One line: a bold lead-in followed by plain text."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.3)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.03)
    for s, b in ((bold, True), (rest, False)):
        r = tf.paragraphs[0].add_run(); r.text = s; r.font.name = FONT; r.font.size = Pt(size); r.font.bold = b; r.font.color.rgb = BLACK


def rmse_table(sl, parts: list, x: float, y: float, size: float = 12, step: float = 0.25) -> None:
    """parts: (label, table of agu_numbers.json). Lines: the two parts. Columns: number of gauges; all gauges, RMSE of all
    forecasts at 1, 3, 6 h; the median gauge at 6 h; RMSE of all forecasts at 6 h for every kind of gauge. In cm."""
    lab = 3.4; wd = [0.8, 0.7, 0.7, 0.7, 1.05, 1.15, 1.0, 0.75, 0.8, 1.25]; cx = [x + lab + sum(wd[:k]) for k in range(len(wd))]
    text(sl, x, y, lab, 0.3, "RMSE (cm)", size=size, bold=True)
    text(sl, cx[1] - 0.6, y, sum(wd[1:4]) + 0.6, 0.3, "All gauges, all forecasts", size=size, bold=True, align=R)
    text(sl, cx[4], y, wd[4], 0.3, "Median", size=size, bold=True, align=R)
    text(sl, cx[5], y, sum(wd[5:]), 0.3, "All forecasts 6 h ahead, by kind of gauge", size=size, bold=True, align=R)
    for k, h in enumerate(["Gauges", "1 h", "3 h", "6 h", "gauge, 6 h"] + KINDS):
        text(sl, cx[k], y + step, wd[k], 0.3, h, size=size, bold=True, align=R)
    for i, (name, tab) in enumerate(parts):
        t = {r["gauges_of"]: r for r in tab}; a = t["All gauges"]
        cells = [f"{a['gauges']}", f"{a['rmse_1h_cm']:.1f}", f"{a['rmse_3h_cm']:.1f}", f"{a['rmse_6h_cm']:.1f}", f"{a['median_gauge_6h_cm']:.1f}"] + [f"{t[k]['rmse_6h_cm']:.1f}" for k in KINDS]
        text(sl, x, y + (i + 2) * step, lab, 0.3, name, size=size)
        for k, c in enumerate(cells):
            text(sl, cx[k], y + (i + 2) * step, wd[k], 0.3, c, size=size, align=R)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "deliverables" / "37_agu_lstm.pptx")); a = ap.parse_args()
    assert not (Path(a.out).parent / ("~$" + Path(a.out).name)).exists(), "the deck is open in PowerPoint"
    n = json.loads((D / "agu_numbers.json").read_text()); src = n["by_source"]; hu, rw = n["hurricanes"], n["recent_week"]
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]

    def new(title):
        sl = prs.slides.add_slide(blank); text(sl, 0.5, 0.3, 12.3, 0.5, title, size=22, bold=True); return sl

    # ---- slide 1: data and model
    sl = new(f"One LSTM for {n['gauges']:,} gauges: water level 1 to 6 hours ahead on the Louisiana and Texas coast")
    years = 2025 - 2010 + 1
    tiles = [(f"{n['gauges']:,}", f"gauges: USGS {src['USGS']}, NOAA {src['NOAA_COOPS']}, CRMS {src['CRMS']}, USACE {src['USACE_MVN']}"),
             (f"{years} years", "of hourly records, 2010 to 2025"),
             (f"{n['observations_all_2010_2025'] / 1e6:.0f} million", "hourly water-level observations"),
             ("4 inputs", "water level, wind, rainfall, river discharge"),
             ("1 to 6 h", "forecast lead time, at every gauge")]
    w = 12.3 / len(tiles)
    for k, (big, small) in enumerate(tiles):
        text(sl, 0.5 + k * w, 1.05, w - 0.15, 0.55, big, size=27, bold=True); text(sl, 0.5 + k * w, 1.62, w - 0.2, 0.6, small, size=12.5)
    text(sl, 0.5, 2.45, 5.4, 0.35, "Gauges", size=15, bold=True); picture(sl, D / "agu_gauges_map.png", 0.5, 2.85, 5.3, 3.3)
    text(sl, 6.05, 2.45, 6.6, 0.35, "Model", size=15, bold=True); picture(sl, D / "agu_architecture.png", 6.0, 2.75, 6.9, 4.1)
    text(sl, 0.5, 6.1, 5.6, 1.0, ["Training 2010 to 2022, validation 2023, test 2024 to 2025.",
                                  f"One set of weights for all gauges: {round(n['observations_train_2010_2022'] / 1e6):.0f} million training observations,",
                                  f"{n['training_minutes_per_model']} minutes of training per network on one NVIDIA A100 GPU."], size=12.5)

    # ---- slide 2: validation, hurricanes and one week in real time
    sl = new("Validation: the hurricanes of 2024 and one week of forecasts in real time")
    heading(sl, 0.5, 0.93, 12.3, "Hurricanes Beryl and Francine, 2024", f" (test years, not used in training): {hu['gauges']} gauges, a forecast every hour, {hu['forecasts']:,} forecasts. Times in UTC.")
    picture(sl, D / "agu_hurricane_gauges.png", 0.5, 1.28, 9.45, 2.65); picture(sl, D / "agu_hurricane_scatter.png", 10.15, 1.2, 2.6, 2.6)
    heading(sl, 0.5, 3.92, 12.3, "In real time, 14 to 20 November 2026", f": forecasts every hour from the live data feeds (USGS, NOAA, HRRR, MRMS), {rw['gauges']} gauges, {rw['forecasts']:,} forecasts.")
    picture(sl, D / "agu_recent_gauges.png", 0.5, 4.24, 12.3, 2.05)
    rmse_table(sl, [("Hurricanes Beryl and Francine, 2024", hu["table"]), ("In real time, 14 to 20 November 2026*", rw["table"])], 0.5, 6.28, step=0.245)
    text(sl, 0.5, 7.25, 12.3, 0.22, "* One gauge with faulty readings on 17 November is left out.", size=9.5)
    prs.save(a.out); print("->", a.out)


if __name__ == "__main__":
    main()
