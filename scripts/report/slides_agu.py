"""Slides for AGU on the water-level model that is run (mean of five LSTMs; inputs water level, wind, rainfall, river discharge).

Slide 1: the data and the model (numbers, map of the gauges, block diagram).
Slide 2: validation in the hurricanes Beryl and Francine of 2024 (four gauges, all forecasts 6 h ahead against the observations, RMSE by kind of gauge).
Slide 3: validation in real time, 14 to 20 November 2026 (six gauges, RMSE by kind of gauge).
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
from pptx.util import Inches

from slides_figures import picture, text

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "37_agu"
C, L, R = PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.RIGHT


def rmse_table(sl, rows: list, x: float, y: float, w: float, size: float = 12.5, step: float = 0.255) -> None:
    """Kinds of gauge in columns; lines: number of gauges, RMSE of all forecasts at 1, 3, 6 h, RMSE of the median gauge at 6 h (cm)."""
    lab = 3.0; cw = (w - lab) / len(rows)
    lines = [("RMSE (cm)", [r["gauges_of"] for r in rows], True), ("Number of gauges", [f"{r['gauges']}" for r in rows], False)]
    lines += [(f"All forecasts, {h} h ahead", [f"{r[f'rmse_{h}h_cm']:.1f}" for r in rows], False) for h in (1, 3, 6)]
    lines += [("Median gauge, 6 h ahead", [f"{r['median_gauge_6h_cm']:.1f}" for r in rows], False)]
    for i, (name, cells, bold) in enumerate(lines):
        text(sl, x, y + i * step, lab, 0.3, name, size=size, bold=bold)
        for k, c in enumerate(cells):
            text(sl, x + lab + k * cw, y + i * step, cw - 0.05, 0.3, c, size=size, bold=bold or k == 0, align=R)


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

    # ---- slide 2: hurricanes
    a0 = hu["table"][0]
    sl = new(f"Validation in hurricanes: Beryl and Francine, 2024 (test years, not used in training)")
    text(sl, 0.5, 0.88, 12.3, 0.35, f"Beryl, 7 to 11 July (Texas and Galveston domains), and Francine, 10 to 14 September (Louisiana domain): {hu['gauges']} gauges, a forecast every hour, {hu['forecasts']:,} forecasts.", size=13.5)
    picture(sl, D / "agu_hurricane_gauges.png", 0.5, 1.4, 8.1, 4.25); picture(sl, D / "agu_hurricane_scatter.png", 8.75, 1.35, 4.1, 4.25)
    rmse_table(sl, hu["table"], 0.5, 5.78, 12.3)

    # ---- slide 3: the week in real time
    a1 = rw["table"][0]
    sl = new("Validation in real time: one week of forecasts, 14 to 20 November 2026")
    text(sl, 0.5, 0.88, 12.3, 0.35, f"Forecasts from the live data feeds (USGS, NOAA, HRRR, MRMS), every hour: {rw['gauges']} gauges, {rw['forecasts']:,} forecasts; one gauge with faulty readings left out.", size=13.5)
    picture(sl, D / "agu_recent_gauges.png", 0.5, 1.35, 12.3, 4.3)
    rmse_table(sl, rw["table"], 0.5, 5.78, 12.3)
    prs.save(a.out); print("->", a.out, "| 6 h, all forecasts:", a0["rmse_6h_cm"], a1["rmse_6h_cm"])


if __name__ == "__main__":
    main()
