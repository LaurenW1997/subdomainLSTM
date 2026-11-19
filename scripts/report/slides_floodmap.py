"""A deck of its own that tells the flood map work from the problem to the present result (deliverables/35_floodmap.md).

Order: the problem and the chain; the models; the first mapping, learned from the model runs of Ida; the whole chain against
observations (Francine); the two problems found (rainfall in the north; every storm looks like Ida); the mapping learned from
observations instead; its results; the highest surge; the gridded map; forecasts 6 h ahead; the two mappings on one grid;
what can and cannot be said; the words used.
Same style as the other decks: white background, black Times New Roman, no title page, no page numbers.
Input : deliverables/35_floodmap/ (tables and figures of the scripts in scripts/p2m and of floodmap_story_figs.py)
Output: deliverables/36_floodmap_explained.pptx
Usage : python slides_floodmap.py [--out FILE]
"""
from __future__ import annotations

import argparse
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
OLD6, NEW6 = "Francine, mapping from forecasts issued 6 h before", "Francine, inputs forecast 6 h before"
FIRST, BEST, NOSTEEP = "gauges", "near gauges favoured + steeper at high water + wind", "near gauges favoured + wind"
BANDS = [-92.5, -91.5, -90.8, -90.2, -89.6, -88.0]


def stats(x: pd.DataFrame) -> dict:
    y = x.dropna(subset=["storm_map_largest_depth_m"]); e = y.storm_map_largest_depth_m - y.storm_observed_largest_depth_m; hi = y.storm_observed_largest_depth_m > 1.2; c = x.dropna(subset=["calm_map_flooded_share"])
    return {"n": len(x), "rmse": x.rmse_depth_m.median(), "calm_obs": np.average(c.calm_observed_flooded_share, weights=c.calm_hours), "calm_map": np.average(c.calm_map_flooded_share, weights=c.calm_hours),
            "mean": e.mean(), "rms": np.sqrt((e ** 2).mean()), "corr": np.corrcoef(y.storm_observed_largest_depth_m, y.storm_map_largest_depth_m)[0, 1], "n_hi": int(hi.sum()), "hi": e[hi].mean(),
            "rest_mean": e[~hi].mean(), "rest_rms": np.sqrt((e[~hi] ** 2).mean())}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "deliverables" / "36_floodmap_explained.pptx"))
    a = ap.parse_args()
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]

    def new(title):
        sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=19, bold=True)
        return sl

    km = lambda v: f"{v:,.0f}"; f2 = lambda v: f"{v:.2f}"; sg = lambda v: f"{v:+.2f}"
    fs = pd.read_csv(D / "francine_forecast_map_summary.csv"); lo = fs[fs.group == "control point, left out"].set_index("lead_h")
    vr = pd.read_csv(D / "valley_check_runs.csv").set_index("run"); vm = pd.read_csv(D / "valley_check_mapping.csv").set_index("field"); vg = pd.read_csv(D / "valley_check_gauges.csv"); NC = "north of 30.5 N, above 0.1 m (km2)"
    oc = pd.read_csv(D / "crms_marsh_check_sites_all_leads.csv"); nf = pd.read_csv(D / "marsh_obs_sites.csv")
    o6, n6 = oc[oc.field == OLD6], nf[nf.field == NEW6]; common = sorted(set(o6.station) & set(n6.station)); o6, n6 = o6[o6.station.isin(common)], n6[n6.station.isin(common)]; so, sn = stats(o6), stats(n6)
    j = o6.set_index("station")[["lon", "storm_observed_largest_depth_m", "storm_map_largest_depth_m"]].join(n6.set_index("station").storm_map_largest_depth_m.rename("new")).dropna()
    bd = j.assign(band=pd.cut(j.lon, BANDS)).groupby("band", observed=True).agg(n=("lon", "size"), obs=("storm_observed_largest_depth_m", "median"), old=("storm_map_largest_depth_m", "median"), new=("new", "median"))
    oc0 = stats(oc[oc.field == "Francine, mapping from observed water levels"])
    vs = pd.read_csv(D / "marsh_obs_variants_sites.csv"); vv = pd.read_csv(D / "marsh_obs_variants_validation.csv").set_index("variant")
    T6, T0, TI = "Francine, inputs forecast 6 h before", "Francine, inputs observed", "Ida, inputs observed (the fit leaves this storm out)"
    sv = {(t, v): stats(vs[(vs.test == t) & (vs.variant == v)]) for t in (T6, T0, TI) for v in (FIRST, BEST, NOSTEEP)}
    ms = pd.read_csv(D / "marsh_map_sites.csv"); mst = {f: stats(x) for f, x in ms.groupby("field")}; ma = pd.read_csv(D / "marsh_map_areas.csv").set_index("field")
    hw = pd.read_csv(D / "forecast_high_water_by_lead.csv").set_index("lead_h"); ca = pd.read_csv(D / "combined_map_areas.csv").set_index("class")

    # ---- 1 the problem
    sl = new("The problem: the forecast is for single gauges, a flood map needs every place")
    yb = picture(sl, D / "explain_pipeline_two_sources.png", 0.5, 0.95, 12.3, 3.9)
    text(sl, 0.5, yb + 0.2, 12.3, 2.4, [
        "-  The water-level model (LSTM) gives the level at each gauge 1 to 6 h ahead. A flood map needs the depth of water on land, everywhere.",
        "-  The missing piece is the mapping: a fast rule that turns the levels at the gauges into a map.",
        "-  The mapping has to be learned from something. Two sources were tried, in this order: the output of a numerical model, and observations.",
        "-  The yardstick throughout: a map made from forecasts, compared with what was observed, for a storm the models have not seen.",
    ], size=BODY)

    # ---- 2 the models
    sl = new("Three models, none of them complicated")
    cols = [(0.5, 2.6, L), (3.2, 3.5, L), (6.8, 3.4, L), (10.3, 2.6, L)]
    y = table(sl, 1.05, cols, ["Step", "Model", "Learned from", "Gives"],
              [["1  Forecast at the gauges", ["LSTM, one model for all gauges,", "mean of 5 random seeds"], ["observed levels 2010 to 2022,", "wind, discharge, rainfall forecast"], ["level at every gauge,", "1 to 6 h ahead"]],
               ["2a  Mapping, first attempt", ["one linear formula per grid cell", "(ridge regression), 30 gauges in"], ["11 runs of a numerical model", "of Hurricane Ida"], ["depth in all 14.8", "million cells"]],
               ["2b  Mapping, used now", ["one linear formula per marsh gauge", "(ridge regression), 146 gauges in"], ["observations 2016 to 2023", "(many storms)"], ["level at 330 marsh gauges,", "then spread over the grid"]]], size=13, hl=2, step=0.36)
    text(sl, 0.5, y + 0.4, 12.3, 3.0, [
        "-  Step 1 exists and is accurate: in Hurricane Francine the RMSE at the gauges was 2 / 5 / 9 cm at 1 / 3 / 6 h.",
        "-  2a and 2b are the same kind of model. They differ in what they are learned from, and in how many gauges go in.",
        "-  2a follows Bao et al. (2025, npj Natural Hazards), who learned the mapping for Galveston Bay from a model run of Hurricane Harvey.",
        "-  The two are separate fits. They are not trained together; a later slide (both mappings on one grid) shows why that would add little.",
    ], size=BODY)

    # ---- 3 the first mapping
    sl = new("First attempt: every grid cell gets a formula, learned from the model runs of Ida")
    text(sl, 0.5, 0.95, 12.3, 0.4, "depth in this cell   =   constant   +   w1 x level at gauge 1   +   w2 x level at gauge 2   +   ...   (one weight per input gauge)", size=15, bold=True)
    yb = picture(sl, D / "explain_cell_example.png", 0.4, 1.5, 12.5, 3.7)
    text(sl, 0.5, yb + 0.1, 12.3, 2.2, [
        "-  The weights are computed from the numerical model, where every hour has both the level at the gauge cells and the depth in every cell. 12 runs of Hurricane Ida, 265 hours each; the hindcast is held back. (The example above is a marsh cell at Pass Manchac, from the fit that still had 39 input gauges.)",
        "-  Only gauges the model reproduces may be inputs: 242 gauges lie in the grid, 30 remain (the model follows them in time and in size, their cell is always water, away from the model boundaries, and they report in real time).",
        "-  Rebuilding the held-back hindcast from its own 30 points works at shallow depth (overlap 0.77 at 0.3 m) and poorly at depth (0.36 at 2 m). This compares the mapping with the model, not with reality.",
    ], size=BODY)

    # ---- 4 the whole chain against observations
    sl = new("The whole chain against observations: Hurricane Francine, which neither model had seen")
    cols = [(0.5, 3.5, L), (4.0, 0.75, R), (4.75, 0.6, R), (5.35, 0.6, R), (5.95, 0.6, R)]
    y = table(sl, 1.0, cols, ["RMSE, median over 30 gauges (m)", ["observed", "levels in"], "1 h", "3 h", "6 h"],
              [[["Map at a gauge that was left out", "(the other 29 go in)"]] + [f2(lo.rmse_mapping_median_m[k]) for k in (0, 1, 3, 6)],
               [["LSTM at the gauge itself", "(what one has where a gauge exists)"], ""] + [f2(lo.rmse_direct_forecast_median_m[k]) for k in (1, 3, 6)]], size=12.5, step=0.34)
    text(sl, 0.5, y + 0.3, 6.1, 4.2, [
        "-  Francine (September 2024) lies in the test years of the LSTM. The mapping had only seen Ida.",
        "-  No model run of Francine is needed: the formulas exist, the forecasts go in, the map comes out.",
        f"-  The chain works: at a place without a gauge the level is within about {lo.rmse_mapping_median_m[6]:.2f} m, 1 to 6 h ahead (the levels varied by about 1 m).",
        f"-  The error is in the mapping, not in the forecast: {lo.rmse_mapping_median_m[0]:.2f} m with observed levels as input, {lo.rmse_mapping_median_m[6]:.2f} m with 6 h forecasts.",
        "-  Where a gauge exists, its own forecast is much better than the map.",
        "",
        "But gauges stand in open water. This says nothing yet about water on land.",
    ], size=BODY)
    picture(sl, D / "francine_forecast_map_stations.png", 6.9, 0.9, 6.2, 6.45)

    # ---- 5 first problem: rainfall
    sl = new("Problem 1: in the north the map repeats the rainfall of Ida")
    cols = [(0.5, 7.4, L), (8.0, 2.2, R)]
    y = table(sl, 1.05, cols, ["Land north of 30.5 N flooded above 0.1 m", "km2"],
              [["Numerical model, the six runs with rainfall", f"{km(vr[NC].loc[['Exp2_no_wind', 'Exp5_Ida_base', 'Exp8_precipitation_base', 'drought_river_storm']].min())} to {km(vr[NC].max())}"],
               ["Numerical model, runs without rainfall (no precipitation; river only; wind only)", " / ".join(km(vr[NC][r]) for r in ("Exp3_no_precipitation", "Exp4_river_only", "Exp7_wind_base"))],
               ["Map for Francine, at the peak", km(vm[NC]["Francine: mapping from observed levels, peak of 10 to 13 September"])],
               ["Map for Francine, in the calm hours before the storm", km(vm[NC][[k for k in vm.index if "calm hours" in k][0]])],
               ["Map with every input at its mean (the constant term alone)", km(vm[NC]["every input at its training mean (the constant term alone)"])]], size=13, step=0.36)
    text(sl, 0.5, y + 0.4, 12.3, 3.2, [
        "-  In the numerical model the valleys of the north flood when it rains, and only then. The gauges on the coast and the lakes do not see the rain.",
        "-  What the formulas learned is that surge and rain came together in Ida. So the map floods the valleys in every storm, and even before the storm.",
        f"-  Observations: 47 gauges in the north rose by {vg.rise_ida_m.median():.2f} m in Ida (median) and by {vg.rise_francine_m.median():.2f} m in Francine. The map gives nearly the same flooded area for both.",
        "",
        "Consequence: no map is given where flooding comes from rainfall.",
    ], size=BODY)

    # ---- 6 observations of flooding on land
    sl = new("Observations of flooding on land: the marsh gauges (CRMS)")
    text(sl, 0.5, 1.0, 6.0, 5.8, [
        "-  Checking a flood map needs observations of water on land. High-water marks are few (6 for Ida in the region, none for Francine).",
        "-  The CRMS network has several hundred gauges in the coastal marsh. Its records give, every hour, the water level relative to the surveyed marsh surface: positive means the marsh is flooded, and by how much.",
        "-  216 sites lie on land cells of the grid and have data. They report late, not in real time, so they are never an input of any model here.",
        "",
        f"First use: is the shallow water the map shows before the storm real? Yes. In the two calm days before Francine the marsh was flooded {100 * oc0['calm_obs']:.0f}% of the time; the map said {100 * oc0['calm_map']:.0f}%.",
        "",
        "The ground level of the grid agrees with the surveyed marsh surface: median difference +0.05 m.",
    ], size=BODY)
    picture(sl, D / "crms_marsh_check_francine.png", 6.7, 1.0, 6.4, 5.8)

    # ---- 7 second problem: every storm looks like Ida
    sl = new("Problem 2: whatever storm comes, the map looks like Ida")
    cols = [(0.5, 3.3, L), (3.9, 0.8, R), (4.8, 1.0, R), (5.9, 1.4, R)]
    y = table(sl, 1.05, cols, [["Largest depth on the marsh,", "Francine, median (m)"], "sites", "observed", ["map learned", "from Ida runs"]],
              [[f"{-b.left:.1f} to {-b.right:.1f} W" + ("  (landfall)" if b.left == -91.5 else ""), str(int(r.n)), f2(r.obs), f2(r.old)] for b, r in bd.iterrows()], size=13, step=0.36)
    text(sl, 0.5, y + 0.35, 12.3, 3.4, [
        "-  The table and the figure of the previous slide, panels (a) to (c): observed, map, difference.",
        "-  Francine came ashore in the west. There the marsh stood 0.4 to 0.6 m under water (up to 2 m on the Terrebonne coast); the map shows almost none.",
        "-  Over the sites, the depths the map gives for Francine and for Ida correlate at 0.94. The observed depths of the two storms correlate at 0.35.",
        "-  Reason: Ida struck the east. In all 12 runs the western marsh hardly floods (largest depth 0.15 m), so the formulas learned that it stays dry.",
        "",
        "A mapping learned from one storm carries the pattern of that storm.",
    ], size=BODY)

    # ---- 8 the change
    sl = new("The change: learn the mapping from observations of many years instead")
    text(sl, 0.5, 0.95, 12.3, 0.4, "level at a marsh gauge   =   constant   +   w1 x level at gauge 1   +   ...   +   w146 x level at gauge 146   (+ wind at the site)", size=15, bold=True)
    cols = [(0.5, 2.7, L), (3.3, 4.6, L), (8.0, 4.9, L)]
    y = table(sl, 1.6, cols, ["", "Learned from the model runs of Ida", "Learned from observations"],
              [["Target", "depth in every grid cell", "level at each of 330 marsh gauges (CRMS)"],
               ["Inputs", "30 gauges the model reproduces", "146 gauges with data in real time"],
               ["Training", "one storm, 11 model runs, 2,915 hours", ["8 years, 2016 to 2023: Harvey, Barry, Laura,", "Delta, Zeta, Ida and many cold fronts"]],
               ["Tests", "the hindcast of the same storm", ["Francine (after the training years);", "Ida with a fit that leaves Ida out"]],
               ["Depth on land", "direct", "level minus surveyed marsh surface"],
               ["New model run needed", "for every further storm", "no"]], size=13, step=0.36)
    text(sl, 0.5, y + 0.35, 12.3, 2.0, [
        "-  The observations already contain storms on many tracks. Nothing has to be simulated.",
        "-  The marsh gauges are the target, never an input: they do not report in real time. The inputs are the gauges the LSTM forecasts.",
        "-  Choices of the fit (which terms, how much smoothing) are made on eight storms inside the training years, each left out in turn. Francine and Ida take no part in that.",
    ], size=BODY)

    # ---- result at the sites, map view
    sl = new("Result: where Francine flooded the marsh, the new mapping shows water")
    yb = picture(sl, D / "marsh_obs_francine_sites.png", 0.3, 0.85, 12.7, 5.85)
    text(sl, 0.5, yb + 0.05, 12.3, 0.7, "Largest depth on the marsh, 10 to 13 September 2024, at the sites both mappings cover; both from forecasts issued 6 h before. (a) observed, (b) learned from the Ida runs, "
         "(c) learned from observations, (d) medians by longitude.", size=11.5)

    # ---- 9 result in time
    sl = new("Result at the marsh gauges, Francine, from forecasts issued 6 h before")
    cols = [(0.5, 3.4, L), (4.0, 1.25, R), (5.3, 1.25, R)]
    y = table(sl, 1.0, cols, [f"{so['n']} sites both mappings cover", ["learned from", "Ida runs"], ["learned from", "observations"]],
              [["Depth on the marsh, RMSE (median, m)", f2(so["rmse"]), f2(sn["rmse"])],
               [f"Marsh flooded before the storm (observed {100 * so['calm_obs']:.0f}%)", f"{100 * so['calm_map']:.0f}%", f"{100 * sn['calm_map']:.0f}%"],
               ["Largest depth: RMS error (m)", f2(so["rms"]), f2(sn["rms"])],
               ["Largest depth: correlation with observed", f2(so["corr"]), f2(sn["corr"])],
               [f"West of the landfall (observed {bd.obs.iloc[0]:.2f} m)", f2(bd.old.iloc[0]), f2(bd.new.iloc[0])],
               [f"At the landfall (observed {bd.obs.iloc[1]:.2f} m)", f2(bd.old.iloc[1]), f2(bd.new.iloc[1])]], size=12.5, step=0.34)
    text(sl, 0.5, y + 0.3, 6.1, 3.0, [
        "-  The figure: five marsh gauges, the two mappings in columns. Black is observed; one line per lead time.",
        "-  West of the landfall (first row) the earlier map is flat; the new one follows the observation.",
        "-  1, 3 and 6 h ahead are almost the same: the lead time costs little.",
        "-  Third row: the highest surge is missed by both. Next slide.",
    ], size=BODY)
    picture(sl, D / "marsh_obs_francine_series.png", 6.9, 0.9, 6.2, 6.45)

    # ---- 10 the highest surge
    a6, b6, ai, bi = sv[(T6, FIRST)], sv[(T6, BEST)], sv[(TI, FIRST)], sv[(TI, BEST)]
    sl = new("Where the surge was highest the fit was 1 m low; about half of that could be removed")
    cols = [(0.5, 3.9, L), (4.5, 0.95, R), (5.5, 0.95, R)]
    y = table(sl, 1.0, cols, ["Eight storms of the training years, each left out", ["peak, RMS", "error (m)"], ["rise > 1 m:", "mean error"]],
              [[lab, f2(vv.peak_rms_error_m[v]), sg(vv.high_peak_mean_error_m[v])] for lab, v in (("All gauges alike (first fit)", FIRST), ("+ wind at the site", "gauges + wind"), ("Near gauges favoured", "near gauges favoured"),
                                                                                                  ("Near gauges favoured + steeper at high water", "near gauges favoured + steeper at high water"),
                                                                                                  ("Near gauges favoured + steeper + wind", BEST))], size=12.5, hl=4, step=0.33)
    text(sl, 0.5, y + 0.3, 6.1, 3.6, [
        "-  Cause: the Terrebonne coast has almost no gauge in real time. One gauge read the surge (1.7 m), and the first fit gave it a weight of 0.16.",
        "-  Three changes, chosen on the left-out storms: weights move to the gauges near the site; the slope may be steeper when those gauges are far above normal; wind stress at the site.",
        f"-  Sites above 1.2 m, mean error: Francine {sg(a6['hi'])} to {sg(b6['hi'])} m, Ida {sg(ai['hi'])} to {sg(bi['hi'])} m. Largest depth, RMS error: {f2(a6['rms'])} to {f2(b6['rms'])} m and {f2(ai['rms'])} to {f2(bi['rms'])} m.",
        "-  What is left is where no gauge reads the surge. A formula cannot make up for that.",
    ], size=BODY)
    picture(sl, D / "marsh_obs_variants_largest_depth.png", 6.9, 0.9, 6.2, 6.45)

    # ---- 11 the gridded map
    g6 = mst["level from the nearest other sites, ground of the grid | inputs forecast 6 h before"]; s6 = mst["the site's own fit, surveyed marsh surface | inputs forecast 6 h before"]; n6s = mst["level from the nearest other sites, surveyed marsh surface | inputs forecast 6 h before"]
    sl = new("From the marsh gauges to a map on the 100 m grid")
    yb = picture(sl, D / "marsh_map_francine.png", 0.3, 0.85, 8.3, 5.1)
    text(sl, 0.4, yb + 0.05, 8.2, 1.4, [
        "(a) the map from observations, (b) the mapping learned from the Ida runs on the same cells; dots: observed at the marsh gauges, same colours. (c) a minus b. (d) where the map is given. "
        "Largest depth of 10 to 13 September 2024, from forecasts issued 6 h before."], size=11.5)
    text(sl, 8.8, 0.95, 4.3, 3.1, [
        "-  A land cell takes the level of the four nearest marsh gauges (weighted by distance) minus the ground level of the grid.",
        "-  The map is given on land within 10 km of a marsh gauge and outside the leveed areas (National Levee Database, as used when the grid was built): 11,910 km2.",
        "-  A storm of four days takes 15 seconds.",
    ], size=12.5)
    cols = [(8.8, 2.9, L), (11.7, 1.4, R)]
    table(sl, 4.05, cols, ["Depth on the marsh", ["RMSE", "(median, m)"]],
          [["at the marsh gauge itself", f2(s6["rmse"])], ["level taken from the other gauges", f2(n6s["rmse"])], [["... and the ground of the grid", "(a cell without a gauge)"], f2(g6["rmse"])], ["mapping learned from Ida runs", f2(so["rmse"])]], size=12, hl=2, step=0.32)
    text(sl, 8.8, 6.2, 4.3, 1.0, "Spreading the level between sites costs little; the ground level of the grid costs most.", size=12.5)

    # ---- 12 forecasts 6 h ahead
    A1 = "above 1.0 m (km2)"; n0, n6m = ma[A1]["from observations, inputs observed"], ma[A1]["from observations, inputs forecast 6 h before"]; c6, d6 = sv[(T6, BEST)], sv[(T6, NOSTEEP)]
    sl = new("Forecasts 6 h ahead: the deep water was overdone, and why")
    cols = [(0.5, 6.4, L), (7.0, 1.9, R), (9.0, 1.9, R), (11.0, 1.9, R)]
    y = table(sl, 1.05, cols, ["Francine", ["6 h forecasts,", "steeper terms"], ["6 h forecasts,", "without them"], ["observed", "levels in"]],
              [["Map: land above 1 m (km2)", "2,794", km(n6m), km(n0)],
               ["Sites: depth on the marsh, RMSE (median, m)", f2(c6["rmse"]), f2(d6["rmse"]), f2(sv[(T0, BEST)]["rmse"])],
               ["Sites above 1.2 m: mean error of the largest depth (m)", sg(c6["hi"]), sg(d6["hi"]), sg(sv[(T0, BEST)]["hi"])],
               ["The other sites: RMS error of the largest depth (m)", f2(c6["rest_rms"]), f2(d6["rest_rms"]), f2(sv[(T0, BEST)]["rest_rms"])]], size=13, hl=1 - 1, step=0.36)
    text(sl, 0.5, y + 0.4, 12.3, 3.6, [
        f"-  Is the LSTM too high at high water in general? No. Over 2024 and 2025 without Francine, {100 * hw.factor[6]:.0f}% of what a 6 h forecast shows above the 95th percentile of a gauge is observed.",
        "-  The overshoot belongs to the hurricane: in Francine 29 of 146 gauges were more than 0.3 m too high at the peak 6 h ahead, none too low. Worst are small rain-fed streams (up to 1.3 m).",
        "-  The terms that are steeper at high water multiply that error. For forecast inputs they are left out; for observed inputs they stay.",
        f"-  Land above 1 m: from 96% too much to {100 * (n6m / n0 - 1):.0f}% too much. The price: the highest sites fall back from {sg(c6['hi'])} to {sg(d6['hi'])} m.",
        "-  This choice was made after seeing Francine; it needs another storm to confirm. What remains is the overshoot of the forecast itself.",
    ], size=BODY)

    # ---- 13 the two mappings on one grid
    sl = new("Both mappings on one grid: the model runs of Ida add little")
    yb = picture(sl, D / "combined_map_francine.png", 0.3, 0.9, 12.7, 3.75)
    cols = [(0.5, 7.9, L), (8.5, 1.6, R), (10.2, 2.6, R)]
    y = table(sl, yb + 0.1, cols, ["Land east of 92.5 W: 58,161 km2", "km2", "of it in leveed areas"],
              [["From observations: marsh within 10 km of a marsh gauge, outside leveed areas", km(ca["land (km2)"]["from observations"]), km(ca["of it in a leveed area (km2)"]["from observations"])],
               ["From the Ida runs: elsewhere, where the model floods without rainfall", km(ca["land (km2)"]["from the Ida runs"]), km(ca["of it in a leveed area (km2)"]["from the Ida runs"])],
               ["No map: in the Ida runs flooded only when it rains", km(ca["land (km2)"].iloc[2]), km(ca["of it in a leveed area (km2)"].iloc[2])],
               ["No map: dry in all twelve Ida runs", km(ca["land (km2)"].iloc[3]), km(ca["of it in a leveed area (km2)"].iloc[3])]], size=12.5, step=0.31)
    text(sl, 0.5, y + 0.15, 12.3, 1.2, [
        "-  Outside the marsh, the gauges can only say something where the water comes from the coast. That is 623 km2. Training the two together would add no more than this.",
        "-  What is missing is flooding by rainfall, inside the leveed areas and in the north: about 19,000 km2. It needs rainfall as an input and more than one rain event to learn from.",
    ], size=12.5)

    # ---- 14 what can and cannot be said
    sl = new("What can be said, what cannot, and what is missing")
    text(sl, 0.5, 1.0, 6.0, 6.0, [
        "Can be said",
        f"-  On the coastal marsh (about 12,000 km2) a map of water depth can be made from the gauge forecasts, 1 to 6 h ahead, without a numerical model run.",
        f"-  Checked on a storm the models had not seen: depth on the marsh within {f2(sn['rmse'])} m at the marsh gauges and about {f2(g6['rmse'])} m at cells without a gauge (median RMSE).",
        "-  The pattern of the flooding follows the storm, not the storm the mapping was learned from.",
        "",
        "Cannot be said",
        f"-  The depth where the surge is highest: still about {-sv[(T6, NOSTEEP)]['hi']:.1f} m low in Francine. No gauge in real time reads it.",
        "-  Anything inside the leveed areas, in the valleys of the north, or far from a marsh gauge.",
        "-  That it holds for the next storm: two storms were tested (Francine, and Ida left out).",
    ], size=BODY)
    text(sl, 6.9, 1.0, 6.0, 6.0, [
        "Missing",
        "-  Flooding by rainfall (leveed areas, valleys): needs rainfall as an input.",
        "-  The overshoot of the 6 h forecast at a hurricane peak: a matter of the water-level model.",
        "-  The ground level between sites: the main error of the gridded map.",
        "-  Wind: the fit used a reanalysis; in a forecast it is the forecast wind. Not tested.",
        "-  Bad readings at an input gauge pass straight into the map: they must be screened first.",
        "-  Lead times 1 to 5 h for the gridded map; the Texas and Galveston grids.",
        "",
        "Not needed for the marsh",
        "-  A further run of the numerical model. It would matter for the rainfall part, with several rain events.",
    ], size=BODY)

    # ---- 15 words
    sl = new("Words used")
    cols = [(0.5, 3.0, L), (3.6, 9.2, L)]
    table(sl, 1.05, cols, ["", ""],
          [["Mapping", "the rule that turns the water levels at the gauges into water levels or depths elsewhere"],
           ["Ridge regression", "a linear formula whose weights are kept small, so that gauges that rise and fall together do not get large weights of opposite sign"],
           ["Marsh gauge (CRMS)", "a gauge of the Coastwide Reference Monitoring System; its record includes the level relative to the surveyed marsh surface"],
           ["Depth on the marsh", "water level minus marsh surface; zero when the water is below the surface"],
           ["Left out", "a gauge or a storm that the fit did not see, used to check it"],
           ["Lead time", "how long before the valid time a forecast was issued (1, 3, 6 h)"],
           ["Leveed area", "land behind a levee, from the National Levee Database; no map is given there"],
           ["Steeper at high water", "extra terms that let the formula rise faster once the nearest gauges are far above their normal range"],
           ["RMSE", "root-mean-square error; here against observations unless said otherwise"]], size=13, step=0.5)

    prs.save(a.out); print("->", a.out, len(prs.slides), "slides")


if __name__ == "__main__":
    main()
