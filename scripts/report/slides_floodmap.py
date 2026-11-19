"""A deck of its own that explains the flood map work step by step (deliverables/35_floodmap.md).

For reading slowly: the problem, the approach of Bao et al. (2025), what a mapping model is (with one cell as an example),
the training data, the control points, the three tests in order (the hindcast left out; observed water levels as input;
independent storm-tide sensors), what can and cannot be said, what is missing, and the words used.
Same style as the other decks: white background, black Times New Roman, no title page, no page numbers.
Input : deliverables/35_floodmap/ (metrics, station tables, figures; explain_*.png of floodmap_explain_figs.py)
Output: deliverables/36_floodmap_explained.pptx
Usage : python slides_floodmap.py [--out FILE]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.util import Inches

from slides_figures import picture, text
from slides_partners import L, R, table

REPO = Path(__file__).resolve().parents[2]
D = REPO / "deliverables" / "35_floodmap"
BODY = 13.5
THR = (0.1, 0.3, 0.5, 1.0, 2.0)


def extent(m: pd.DataFrame, inp: str) -> list[dict]:
    m = m[m.input == inp]
    return [m[m.cells == f"land with peak depth above {t} m"].iloc[0].to_dict() for t in THR]


def flooded(m: pd.DataFrame, inp: str) -> dict:
    return m[(m.input == inp) & m.cells.str.startswith("land, flooded")].iloc[0].to_dict()


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "deliverables" / "36_floodmap_explained.pptx"))
    a = ap.parse_args()
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]

    def new(title):
        sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=19, bold=True)
        return sl

    m1 = pd.read_csv(D / "metrics_Exp1_fully_coupled_39_points.csv"); m2 = pd.read_csv(D / "metrics_Exp1_fully_coupled_observed_inputs.csv")
    e1, e2 = extent(m1, "exact"), extent(m2, "observed"); f1, f2 = flooded(m1, "exact"), flooded(m2, "observed")
    st = pd.read_csv(D / "observed_inputs_stations.csv", dtype={"station_id": str})
    lo, ck = st[st.group.str.startswith("control")], st[st.group.str.startswith("check")]
    cu = pd.read_csv(D / "controls_used_39_points.csv"); n_cp = int(cu.used.sum())
    tide = pd.read_csv(D / "ida_storm_tide_compare.csv"); sh, be = tide[~tide.grand_isle], tide[tide.grand_isle]
    err = lambda x, c: (float((x[c] - x.sensor_peak_m).mean()), float(np.sqrt(((x[c] - x.sensor_peak_m) ** 2).mean())))
    cell = json.loads((D / "cell_example_manchac.json").read_text(encoding="utf-8"))
    km = lambda v: f"{v:,.0f}"

    # ---- 1 the problem
    sl = new("The problem: the LSTM forecasts single points, a flood map needs every place")
    yb = picture(sl, D / "explain_pipeline.png", 0.5, 0.95, 12.3, 3.4)
    text(sl, 0.5, yb + 0.15, 12.3, 3.0, [
        "-  The LSTM gives one number per gauge: the water level at 458 gauges, 1 to 6 h ahead.",
        "-  A flood map needs the water depth everywhere. The Louisiana grid has 14.8 million cells of 100 m.",
        "-  The numerical model computes every cell, but it is far too slow to be run again every hour.",
        "-  The idea (Bao et al. 2025, npj Natural Hazards): let the numerical model teach a fast formula once. Afterwards the map follows from the gauges in seconds.",
        "",
        "The LSTM box exists. This deck is about the orange box: can such formulas be built for Louisiana, and how good is the map they give?",
    ], size=BODY)

    # ---- 2 the mapping model, one cell
    sl = new("The mapping model: every grid cell has its own formula")
    text(sl, 0.5, 0.95, 12.3, 0.4, f"depth in this cell   =   constant   +   w1 x level at gauge 1   +   w2 x level at gauge 2   +   ...   +   w{n_cp} x level at gauge {n_cp}", size=15, bold=True)
    text(sl, 0.5, 1.4, 12.3, 0.9, [
        "A negative result is set to 0: the cell is dry. The weights w are different for every cell. Nobody sets them: they are computed from the output of the numerical model, "
        "where every hour has both the level at the gauge cells and the depth in every cell.",
    ], size=BODY)
    yb = picture(sl, D / "explain_cell_example.png", 0.4, 2.2, 12.5, 3.9)
    text(sl, 0.5, yb + 0.05, 12.3, 1.3, [
        f"Example: a marsh cell at Pass Manchac, ground {cell['ground_m']:.2f} m. Fed with the levels at the {n_cp} gauges, its formula follows the numerical model "
        f"(peak {max(cell['mapping_model_inputs_m']):.2f} m against {max(cell['hindcast_depth_m']):.2f} m; fed with the observed levels, {max(cell['mapping_observed_inputs_m']):.2f} m).",
        "The weights are not tidy: gauges that rise and fall together share the weight, and some weights are negative. A single weight means little; the sum is what counts.",
    ], size=BODY)

    # ---- 3 the training data
    sl = new("What the formulas are learned from: 12 runs of Hurricane Ida, 3,180 hours")
    cols = [(0.5, 3.4, L), (4.0, 8.6, L)]
    y = table(sl, 1.05, cols, ["Run of the numerical model", "Role here"],
              [["Exp1  fully coupled", "The hindcast of Ida: wind, rain and rivers as they were. Hidden in test 1, never used for learning in any test."],
               ["Exp2  no wind", "Learning"], ["Exp3  no precipitation", "Learning"], ["Exp4  river only", "Learning"], ["Exp5  Ida base", "Learning"],
               ["Exp6  absolute base", "Learning. Without the hurricane: a cell that stays dry in this run is counted as 'land'."],
               ["Exp7  wind base", "Learning"], ["Exp8  precipitation base", "Learning"],
               ["Drought river, with and without the storm", "Learning (2 runs)"], ["Flood river, with and without the storm", "Learning (2 runs)"]], size=12.5, hl=0, step=0.31)
    text(sl, 0.5, y + 0.3, 12.3, 2.6, [
        "-  Every run: 265 hourly fields, 25 August to 5 September 2021, on the Louisiana 100 m grid (quality-controlled archive on sv6).",
        "-  Why several runs help: the formulas see the same coast flooded for different reasons (surge without rain, rain without surge, a high or a low river), "
        "so they are not tied to one single course of events.",
        "-  The paper used one run of Hurricane Harvey (60 days) and 8 control points for Galveston Bay.",
        "-  Cost: one pass over the 12 runs takes 3 minutes, computing the formulas for all 14.8 million cells less than 1 minute.",
    ], size=BODY)

    # ---- 4 control points
    sl = new(f"Which gauges may be inputs (control points): {n_cp} pass three conditions")
    cols = [(0.5, 9.6, L), (10.3, 1.0, R)]
    y = table(sl, 1.05, cols, ["", "gauges"],
              [["Gauges inside the Louisiana grid", "242"], ["with at least 200 hours of observations during Ida", "195"],
               ["Condition 1: the hindcast follows the gauge in time (correlation of at least 0.8, best cell within 2 km)", "71"],
               ["Condition 2: the gauge has data in real time now, so the LSTM forecasts it", "60"],
               ["Condition 3: the hindcast also rises and falls by the right amount (0.5 to 2 times the observed)", str(n_cp)]], size=13, hl=4, step=0.36)
    text(sl, 0.5, y + 0.35, 12.3, 3.4, [
        "Why conditions at all: the formulas are learned inside the numerical model but will be fed with real water levels. At a gauge where the model does not behave like "
        "reality, the formula would be fed something it has never seen.",
        "",
        "-  Condition 3 was added in the second round. At 21 gauges, mostly small creeks around Baton Rouge, the model rises at the right time but by less than half: "
        "on a 100 m grid these creeks hardly exist.",
        "-  Dropping the 21 changed nothing in test 1. They carried no weight.",
        "-  In calm weather the model is 0.3 to 0.4 m lower than the gauges. Before real water levels are fed in, every gauge is shifted by its own offset "
        "(the difference in the three days before the storm).",
    ], size=BODY)

    # ---- 5 test 1, the map
    sl = new(f"Test 1, the exam: hide the hindcast, then rebuild it from its own {n_cp} points")
    yb = picture(sl, D / "ida_peak_flood_depth_39_points.png", 0.3, 0.85, 12.7, 5.75)
    text(sl, 0.5, yb + 0.05, 12.3, 0.8, [
        f"The formulas are learned from the 11 other runs. Then only the hindcast's water level at the {n_cp} points goes in, and (b) comes out. (a) is the answer. "
        "(c) = (b) minus (a): blue means the mapping is too shallow. Flood depth on land, east of 92.5 W (the west was not tuned: no good bathymetry there)."], size=11.5)

    # ---- 6 the score
    sl = new("Test 1: how to read the score")
    picture(sl, D / "explain_csi.png", 0.3, 1.0, 5.6, 3.2)
    cols = [(6.4, 2.6, L), (9.0, 1.4, R), (10.4, 1.3, R), (11.7, 0.9, R)]
    table(sl, 1.05, cols, [["Land with a peak", "depth above"], ["numerical", "model (km2)"], ["mapping", "(km2)"], "CSI"],
          [[f"{t} m", km(r["area_km2"]), km(r["area_mapping_km2"]), f"{r['csi']:.2f}"] for t, r in zip(THR, e1)], size=13, step=0.38)
    text(sl, 0.5, 4.45, 12.3, 2.8, [
        f"-  Where it floods: at 0.3 m, four fifths of the area agree (CSI {e1[1]['csi']:.2f}). Above 2 m the mapping finds only half of the area ({km(e1[4]['area_mapping_km2'])} of {km(e1[4]['area_km2'])} km2).",
        f"-  How deep: on the land that floods, the peak depth is {f1['peak_model_mean_m']:.2f} m in the numerical model and {f1['peak_mapping_mean_m']:.2f} m in the mapping, "
        f"{-f1['peak_bias_m']:.2f} m too shallow on average.",
        f"-  RMSE on that land: {f1['rmse_all_hours_m']:.2f} m over all 265 hours, {f1['peak_rmse_m']:.2f} m for the peak. The paper reports 0.26 to 0.29 m for Galveston Bay.",
        "",
        "Peak depth = the largest depth of a cell during the 265 hours. 'Land' = cells that stay dry in the run without the hurricane.",
    ], size=BODY)

    # ---- 7 right and wrong, and why the exam is easy
    sl = new("Test 1: what comes out right, what does not, and why this exam is an easy one")
    text(sl, 0.5, 1.0, 6.3, 6.2, [
        "Right:  flooding by the storm surge (Barataria, Breton Sound, around Lakes Pontchartrain and Maurepas). That water is the sea coming in, and the coastal gauges measure exactly that.",
        "",
        "Too shallow at the deepest places.  A straight-line formula pulls extremes towards the usual. The paper uses other formulas for cells that are normally dry; not done here yet.",
        "",
        "Rain flooding in the northern river valleys is missing (the blue in panel c).  No control point lies there, and a water level gauge elsewhere does not know how much rain fell in a valley.",
        "",
        "Short pulses are lost (figure).  At many land cells the peak of the numerical model lasts one or two hours (probably local rain; not checked). No gauge knows about it.",
    ], size=BODY)
    yb = picture(sl, D / "explain_cell_miss.png", 7.0, 1.0, 6.0, 3.3)
    text(sl, 7.1, yb + 0.2, 5.8, 2.6, [
        "Why the exam is easy:",
        "1.  The same storm. Among the 11 runs used for learning are runs with the same wind and rain as the hindcast; only the river flow differs.",
        "2.  Perfect inputs. The formulas were fed the model's own water level at the gauges, not a measurement and not a forecast.",
        "",
        "Test 1 shows that the formulas can express this numerical model. It does not show how they do in real use.",
    ], size=BODY)

    # ---- 8 test 2, the method and the numbers at the gauges
    sl = new("Test 2: feed the formulas with what the gauges really measured during Ida")
    text(sl, 0.5, 1.0, 12.3, 3.0, [
        "Question: the formulas were learned inside the numerical model. Fed with real water levels, is the result still right?",
        "",
        f"-  Offset: for every gauge, the median of (model minus observed) in the three days before the storm is added to its observations. Median of the {n_cp} gauges: "
        f"{lo.offset_m.median():+.2f} m.",
        f"-  Left out in turn: each of the {n_cp} control points is hidden once. Its water level is computed from the observations of the other {n_cp - 1} and compared with what it measured.",
        f"-  Never an input: {len(ck)} more gauges pass conditions 1 and 3 but have no real-time data now. The full formulas are evaluated at their cells.",
        "-  Yardstick: the hindcast at the same gauge and the same hours.",
    ], size=BODY)
    cols = [(0.5, 4.6, L), (5.2, 1.0, R), (6.4, 2.0, R), (8.5, 2.0, R), (10.6, 2.2, R)]
    y = table(sl, 3.45, cols, ["RMSE against the observations, median over the gauges (m)", "gauges", "mapping", "hindcast", ["gauges where the", "mapping is closer"]],
              [["Control points, left out in turn", str(len(lo)), f"{lo.rmse_mapping_m.median():.2f}", f"{lo.rmse_hindcast_m.median():.2f}", str(int((lo.rmse_mapping_m < lo.rmse_hindcast_m).sum()))],
               ["Gauges that are never an input", str(len(ck)), f"{ck.rmse_mapping_m.median():.2f}", f"{ck.rmse_hindcast_m.median():.2f}", str(int((ck.rmse_mapping_m < ck.rmse_hindcast_m).sum()))]], size=13, step=0.38)
    text(sl, 0.5, y + 0.35, 12.3, 1.6, [
        "Driven by the observations of other gauges, the mapping is as close to a gauge it has not seen as the numerical model itself is.",
        "Both are too low at the peak by about the same amount (0.15 m on average at the left-out gauges).",
    ], size=BODY)

    # ---- 9 test 2, station figure
    sl = new("Test 2 at eight gauges the mapping was not given")
    picture(sl, D / "ida_observed_inputs_stations.png", 0.3, 0.9, 8.6, 6.4)
    text(sl, 9.1, 1.0, 3.9, 6.0, [
        "Black: observed.",
        "Blue: numerical model (hindcast).",
        "Orange: mapping, driven by the observations of the other gauges.",
        "",
        "Coast and lakes (Grand Isle, Shell Beach, Bay Waveland, Carrollton, Belle Chasse): time and height of the peak follow from the other gauges.",
        "",
        "Baton Rouge: left out, the mapping gives it a tidal curve. The flow from upstream is known to this gauge alone.",
        "",
        "In use Baton Rouge is an input, so this does not happen. But it shows that every large river needs a control point of its own.",
    ], size=13)

    # ---- 10 test 2, the whole map
    sl = new("Test 2, the whole map: driven by observed water levels it stays close to the hindcast")
    yb = picture(sl, D / "ida_peak_flood_depth_observed_inputs.png", 0.3, 0.85, 12.7, 5.45)
    text(sl, 0.5, yb + 0.05, 12.3, 1.2, [
        "CSI against the hindcast: " + ",  ".join(f"{r['csi']:.2f} at {t} m" for t, r in zip(THR, e2)) + f".   Peak depth on the flooded land: {f2['peak_mapping_mean_m']:.2f} m "
        f"(hindcast {f2['peak_model_mean_m']:.2f} m; mapping from the model's own series {f1['peak_mapping_mean_m']:.2f} m).",
        f"Deeper than in test 1, because the gauges rose more than the model did at their cells: above 2 m, {km(e2[4]['area_mapping_km2'])} km2 instead of {km(e1[4]['area_mapping_km2'])} km2 "
        f"(hindcast {km(e2[4]['area_km2'])} km2).  There is no truth for the depth on land here: where (b) and (a) differ, either may be right.",
    ], size=11.5)

    # ---- 11 test 3
    sl = new("Test 3: 14 storm-tide sensors that are in none of the inputs")
    picture(sl, D / "ida_storm_tide_peaks.png", 0.3, 0.95, 8.3, 5.0)
    (hm, hr), (om, orr) = err(sh, "hindcast_peak_m"), err(sh, "mapping_observed_inputs_peak_m"); (bm, _), (bo, _) = err(be, "hindcast_peak_m"), err(be, "mapping_observed_inputs_peak_m")
    text(sl, 8.8, 1.0, 4.2, 6.2, [
        "USGS set up temporary sensors along the coast before landfall and recorded the peak (NAVD88). They are not in our gauge data, so nothing in the mapping has seen them.",
        "",
        f"Away from Grand Isle ({len(sh)}; bays, lakes, passes): the mapping driven by observations has a mean error of {om:+.2f} m and an RMS of {orr:.2f} m. The hindcast: {hm:+.2f} / {hr:.2f} m. "
        f"Measured peaks: {sh.sensor_peak_m.min():.1f} to {sh.sensor_peak_m.max():.1f} m.",
        "",
        f"Grand Isle ({len(be)}; State Park pier on the Gulf side, pier at Caminada Pass): the hindcast is {-bm:.2f} m lower than the sensors, and the mapping follows it "
        f"({-bo:.2f} m lower). The regular gauges agree: at the peak the hindcast is 0.45 m low at NOAA Grand Isle (bay side) and 0.9 m low at USGS Caminada Pass, after the offset. "
        "A limit of the hindcast, not of the mapping.",
    ], size=13)
    text(sl, 0.5, 6.15, 8.0, 1.1, [
        f"Model and mapping are moved to NAVD88 with one offset, {-float(tide.offset_m.iloc[0]):.2f} m: what the model is lower than 9 NOAA tide gauges before the storm.",
        "USGS high-water marks were looked for first: of 655 for Ida, only 6 are in Louisiana and Mississippi.",
    ], size=11.5)

    # ---- 12 what can be said
    sl = new("What can be said now, and what cannot")
    text(sl, 0.5, 1.0, 6.0, 0.4, "Can be said", size=15, bold=True); text(sl, 0.5, 4.2, 6.0, 0.4, "Known errors", size=15, bold=True); text(sl, 7.0, 1.0, 5.9, 0.4, "Cannot be said yet", size=15, bold=True)
    text(sl, 0.5, 1.5, 6.0, 2.6, [
        f"1.  The formulas can express the numerical model: four fifths of the flood extent at 0.3 m, from {n_cp} points (test 1).",
        "",
        "2.  They work with real water levels: the map keeps its shape, and at gauges they have not seen they are as close as the hindcast (test 2).",
        "",
        "3.  At independent sensors away from Grand Isle the peak has the right size and no bias (test 3).",
    ], size=BODY)
    text(sl, 0.5, 4.7, 6.0, 2.4, [
        "-  Too shallow at the deepest places.",
        "-  Rain flooding in the northern valleys is missing.",
        "-  Grand Isle: the peak 0.5 to 2 m too low (from the hindcast).",
        "-  West of 92.5 W is left out (bathymetry).",
    ], size=BODY)
    text(sl, 7.0, 1.5, 5.9, 5.7, [
        "-  Another storm.  Everything is Hurricane Ida. A run of the numerical model for another storm does not exist yet, so the formulas have never met a storm they were not built from.",
        "",
        "-  Forecasts as input.  So far the inputs were observed water levels. The LSTM forecasts 1 to 6 h ahead have not been fed in.",
        "",
        "-  Depth on land.  The gauges stand in channels and open water. For the flooded land itself there are only the 14 sensor peaks of test 3, several of them at the shore.",
        "",
        "-  The offsets in real use.  They were taken from the three days before this storm. In operation they must come from normal days.",
    ], size=BODY)

    # ---- 13 what is missing
    sl = new("What is still missing before a map can go online")
    text(sl, 0.5, 1.0, 12.3, 6.0, [
        "1.  Connect the LSTM: feed the forecasts for 1 to 6 h ahead into the formulas, one map per lead time, and compare with the map from observations.",
        "",
        "2.  Decide the product: depth or flood extent, which area, which file format, how often.",
        "",
        "3.  Formulas for normally dry cells as in the paper (a formula for 'wet or dry' and one for the depth). This is aimed at the shallow bias.",
        "",
        "4.  More independent measurements: the CRMS marsh gauges (several hundred along the coast, hourly) would turn the 14 points of test 3 into hundreds, with full time series.",
        "",
        "5.  Offsets for operation: compare the operational model with the gauges on normal days.",
        "",
        "6.  Rain flooding inland: needs an input that knows about rain. To be decided.",
        "",
        "7.  A second storm, as soon as a run of the numerical model for it exists.",
        "",
        "Nothing is connected to the operational system. All computations are in new folders under my own account on sv7; notes in deliverables/35_floodmap.md.",
    ], size=BODY)

    # ---- 14 words
    sl = new("Words used in this deck")
    cols = [(0.5, 2.6, L), (3.2, 9.6, L)]
    table(sl, 1.05, cols, ["Word", "Meaning here"],
          [["Numerical model", "The coupled land and ocean model (WRF-Hydro and ROMS) on the Louisiana 100 m grid. Slow, computes every cell."],
           ["Hindcast", "The run of the numerical model that reproduces Ida as it happened (Exp1)."],
           ["Prediction model", "The LSTM: water level at the gauges, 1 to 6 h ahead, from observations."],
           ["Mapping model", "One formula per grid cell that turns the water levels at the control points into the depth in that cell."],
           ["Control point", f"A gauge whose water level is an input of the mapping model ({n_cp} of them)."],
           ["Left out / hidden", "Not used for learning or as input, only for comparing afterwards."],
           ["Offset", "A constant added to the observations of a gauge so that they sit on the level of the numerical model."],
           ["Peak depth", "The largest depth of a cell during the 265 hours."],
           ["Land", "Cells that stay dry in the run without the hurricane."],
           ["RMSE", "Root mean square error: the typical size of the difference, in metres."],
           ["CSI", "Critical success index: the area flooded in both maps divided by the area flooded in either. 1 = identical."],
           ["NAVD88", "The vertical datum of the gauges and sensors; the numerical model sits about 0.4 m lower in calm weather."]], size=13, step=0.42)

    prs.save(a.out); print(f"-> {a.out}: {len(prs.slides)} slides")


if __name__ == "__main__":
    main()
