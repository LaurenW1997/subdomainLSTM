"""Two slides for AGU on the water-level model that is run (mean of five LSTMs; inputs water level, wind, rainfall, river discharge).

Slide 1: the data and the model (numbers, map of the gauges, block diagram). Slide 2: validation on the test years 2024-2025
(six gauges, RMSE by lead time). White background, black Times New Roman, no title page, no page numbers.
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


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "deliverables" / "37_agu_lstm.pptx")); a = ap.parse_args()
    assert not (Path(a.out).parent / ("~$" + Path(a.out).name)).exists(), "the deck is open in PowerPoint"
    n = json.loads((D / "agu_numbers.json").read_text()); src = n["by_source"]; ra, rm = n["rmse_all_forecasts_cm"], n["rmse_median_gauge_cm"]
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

    # ---- slide 2: validation
    sl = new(f"Test on 2024 and 2025, not used in training: RMSE of {ra['6']:.1f} cm six hours ahead at {n['test_gauges']} gauges")
    picture(sl, D / "agu_validation.png", 0.5, 1.0, 12.3, 4.85)
    y = 6.1
    text(sl, 0.5, y, 5.6, 1.1, [f"Test period: January 2024 to December 2025.", f"{n['test_gauges']} gauges with data in real time, {n['test_forecasts'] / 1e6:.2f} million forecasts.",
                                "Rainfall of the next 6 hours from the HRRR forecast, as in real time."], size=13.5)
    cols = [(6.6, 3.0, L), (9.7, 1.0, R), (10.8, 1.0, R), (11.9, 1.0, R)]
    rows = [(["RMSE by lead time", "1 h", "3 h", "6 h"], True), (["All forecasts"] + [f"{ra[h]:.1f} cm" for h in "136"], False), (["Median gauge"] + [f"{rm[h]:.1f} cm" for h in "136"], False)]
    for i, (cells, bold) in enumerate(rows):
        for (x, w_, al), c in zip(cols, cells):
            text(sl, x, y + i * 0.36, w_, 0.34, c, size=15, bold=bold, align=al)
    prs.save(a.out); print("->", a.out)


if __name__ == "__main__":
    main()
