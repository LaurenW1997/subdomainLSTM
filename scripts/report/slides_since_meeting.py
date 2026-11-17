"""A deck of its own on the work since the group meeting of 13 November 2026.

Starts from the version at the end of that meeting and goes through the steps in order: how versions are compared, where
the remaining error is, partner stations (idea, rules, results in the test years, late data, station types), the forecast
script on live data (test on past forecast times, station figures, the jagged lead-time lines, the run in real time), and
where things stand. One message per slide, a table or a figure, a few lines of text.
The deck that is arranged by hand (deliverables/17_versions/version_comparison.pptx) is not touched.
Same style: white background, black Times New Roman, no title page, no page numbers.
Input : runs/protocol_<group>/protocol_station.csv, config/station_behaviour.csv, config/station_groups.csv,
        config/station_partners_network.csv, deliverables/17_versions/partner_map_wide.png, deliverables/33_partner_live_test/
Output: deliverables/34_since_meeting.pptx
Usage : python slides_since_meeting.py [--out FILE]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.util import Inches

from slides_figures import picture, text
from slides_partners import K, L, R, RUN, TYPES, against, load, pool, q, table

REPO = Path(__file__).resolve().parents[2]
F = REPO / "deliverables" / "17_versions"
T = REPO / "deliverables" / "33_partner_live_test"
BODY = 13.5
r2 = lambda x: f"{round(float(x) + 1e-9, 2):.2f}"      # 7.505 is written 7.51, as in the deliverable texts
MEETING = (2.24, 5.43, 8.66)          # the single model that was run at the meeting (deliverables/24_seed_mean.md)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "deliverables" / "34_since_meeting.pptx"))
    a = ap.parse_args()
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5); blank = prs.slide_layouts[6]

    def new(title):
        sl = prs.slides.add_slide(blank)
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=19, bold=True)
        return sl

    G = {k: load(k) for k in ["hrrr_total", "split_none", "split_early", "split_late", "split_both", "partners4", "partners4_river50", "partners4_river50_lateaug",
                              "partners4_network_lateaug", "partners4_behaviour_lateaug"]}
    Q = {k: q(v) for k, v in G.items() if v is not None}
    run, par = Q["hrrr_total"], Q["partners4_behaviour_lateaug"]; ref = G["hrrr_total"]
    n_st = int((ref.model == "mean").sum())
    sp = [Q[k] for k in ("split_none", "split_early", "split_late", "split_both")]
    pag = against(G["partners4_behaviour_lateaug"], ref)
    uc = "urban creek (Houston)"

    # ---- 1 starting point and the steps since
    sl = new("Starting point: the version at the end of the group meeting of 13 November, and the steps since")
    cols = [(0.5, 8.3, L), (9.0, 0.9, R), (10.0, 0.9, R), (11.0, 0.9, R)]
    y = table(sl, 1.05, cols, [f"RMSE (cm), test years 2024-2025, {n_st} stations with real-time data", "1 h", "3 h", "6 h"],
              [["At the meeting: scaling + gap filling + HRRR rainfall, trained with missing hours, one model", f"{MEETING[0]:.2f}", f"{MEETING[1]:.2f}", f"{MEETING[2]:.2f}"],
               ["Step 1: the same, trained five times, mean of 5 models  (the version that is run)", f"{run['h1']:.2f}", f"{run['h3']:.2f}", f"{run['h6']:.2f}"],
               ["Step 2: + water level of partner stations as input  (tested, not switched on)", f"{par['h1']:.2f}", f"{par['h3']:.2f}", f"{par['h6']:.2f}"],
               ["For reference only, not available in real time: the same model with observed instead of forecast rainfall for the next 6 h", f"{sp[3]['h1']:.2f}", f"{sp[3]['h3']:.2f}", f"{sp[3]['h6']:.2f}"]],
              size=13, hl=1, step=0.36)
    text(sl, 0.5, y + 0.35, 12.3, 3.6, [
        "The model itself did not change: one LSTM for all stations. Both steps add information, not a different network.",
        "",
        "Three questions since the meeting, in the order of the slides:",
        "1.  How to compare two versions when another random seed alone moves the numbers?   Five seeds for every setting.",
        "2.  Where is the remaining error?   In the rainfall forecast of the next 6 h (last row: not available in real time).",
        "3.  Can the water level at other stations help?   Yes, at stations with tide and at rivers with a gauge upstream.",
        "",
        "Then: partner stations in the forecast script, tested on live data of 15 to 17 November.",
    ], size=BODY)

    # ---- 2 how versions are compared
    sl = new("Comparing versions: every setting is trained five times, and four numbers are reported besides the average")
    cols = [(0.5, 4.3, L), (4.8, 1.5, R), (6.3, 1.7, R)]
    rng = lambda v, f="{:.2f}": f"{f.format(min(v))} to {f.format(max(v))}"
    y = table(sl, 1.05, cols, ["The version that is run", "mean of 5", "single models"],
              [["All forecasts, 1 / 3 / 6 h ahead (cm)", f"{run['h1']:.2f} / {run['h3']:.2f} / {run['h6']:.2f}", "6 h: " + rng(run["h6_single"])],
               ["Largest 1% of the 6 h changes, 6 h (cm)", f"{run['event']:.1f}", ""], ["    rises / falls", f"{run['rise']:.1f} / {run['fall']:.1f}", ""],
               ["Hurricane periods, 6 h (cm)", f"{run['storm']:.1f}", rng(run["storm_single"], "{:.1f}")], ["Lag of the forecast on the rises (h)", f"{run['lag']:.2f}", rng(run["lag_single"])],
               ["Share of the observed rise that is forecast", f"{run['share']:.2f}", ""]], size=12.5, step=0.33)
    cols2 = [(8.6, 1.5, L), (10.0, 0.8, R), (10.8, 1.0, R), (11.8, 1.0, R)]
    table(sl, 1.05, cols2, ["By station type", "stations", ["hurricanes,", "6 h (cm)"], ["lag on the", "rises (h)"]],
          [[lab, f"{run[t + '|n']}", f"{run[t + '|storm']:.1f}", f"{run[t + '|lag']:.1f}"] for t, lab in TYPES], size=12.5, step=0.33)
    text(sl, 0.5, y + 0.35, 12.3, 3.2, [
        "Another random seed alone moves the 6 h RMSE by about 0.04 cm, and single stations in a hurricane by a factor of two.",
        "So every setting is trained with five seeds and the mean of five is compared with the mean of five on the same forecasts.",
        "A station counts as clearly better or worse only if all five single models are on the same side of all five of the other version.",
        "",
        f"What the extra numbers show: the error sits in the rises ({run['rise']:.0f} cm against {run['fall']:.0f} cm on the falls); the model forecasts {100 * run['share']:.0f}% of an "
        f"observed rise and is {run['lag']:.1f} h late on average, {run[uc + '|lag']:.1f} h at urban creeks.",
    ], size=BODY)

    # ---- 3 rainfall in two parts
    sl = new("Where the remaining error is: the rainfall forecast of the next 6 hours")
    cols = [(0.5, 4.2, L), (4.8, 0.9, R), (5.7, 0.9, R), (6.6, 0.9, R), (7.8, 1.3, R), (9.2, 1.3, R), (10.6, 1.2, R)]
    labs = ["HRRR forecast / HRRR forecast", "Observed / HRRR forecast", "HRRR forecast / observed", "Observed / observed"]
    y = table(sl, 1.05, cols, [["Rainfall of hours 1-2 / of hours 3-6", "(the model is the same in every row)"], ["1 h", "(cm)"], ["3 h", "(cm)"], ["6 h", "(cm)"], ["largest 1%,", "6 h (cm)"], ["hurricanes,", "6 h (cm)"],
                               ["lag on the", "rises (h)"]],
              [[lab, f"{s['h1']:.2f}", f"{s['h3']:.2f}", f"{s['h6']:.2f}", f"{s['event']:.1f}", f"{s['storm']:.1f}", f"{s['lag']:.2f}"] for lab, s in zip(labs, sp)], size=12.5, hl=0, step=0.34)
    gap = lambda k: sp[0][k] - sp[3][k]
    fr = lambda k, i: 100 * (sp[0][k] - sp[i][k]) / gap(k)
    text(sl, 0.5, y + 0.35, 12.3, 3.6, [
        "Observed rainfall of the future does not exist in real time. The rows measure what a perfect rainfall forecast for that part would be worth.",
        "",
        f"-  With perfect rainfall the same model reaches {sp[3]['h6']:.2f} instead of {sp[0]['h6']:.2f} cm at 6 h. No change to the model so far has given this much.",
        f"-  Hours 1-2 account for {fr('h6', 1):.0f}% of the distance, hours 3-6 for {fr('h6', 2):.0f}%. In the hurricanes the later hours matter most ({sp[0]['storm']:.1f} to {sp[2]['storm']:.1f} cm).",
        f"-  The lag on the rises is largely a rainfall problem: {sp[0]['lag']:.2f} to {sp[3]['lag']:.2f} h, at urban creeks {sp[0][uc + '|lag']:.1f} to {sp[3][uc + '|lag']:.1f} h.",
        f"-  Tide gauges and lakes do not depend on rainfall ({sp[0]['tide gauge']:.2f} to {sp[3]['tide gauge']:.2f} cm at tide gauges).",
        "",
        "Conclusion: what is missing is information, not a more advanced model.",
    ], size=BODY)

    # ---- 4 partner stations: the idea
    beh = pd.read_csv(REPO / "config" / "station_behaviour.csv", dtype={"station_id": str}); rt = beh[beh.source != "CRMS"]
    nb = rt.behaviour.value_counts()
    sl = new("Partner stations: the water level of other stations as input")
    text(sl, 0.5, 1.05, 12.3, 6.0, [
        "At some stations the next change shows first somewhere else:",
        "-  the tide and a surge reach the coast before the inner bay,",
        "-  a flood wave reaches the gauge upstream before the one downstream.",
        "",
        "Each station gets the water level of the past 72 h at up to four such partner stations as extra input.",
        "",
        "What stays the same: one LSTM for all stations, the same training, no new data source. The partners are stations of the same real-time feed.",
        "",
        "Example: Lake Charles lies 52 km inland of the tide gauge at Calcasieu Pass. With Calcasieu Pass as partner its 6 h RMSE in the test years falls from 5.4 to 3.6 cm.",
        "",
        "Difference to a ConvLSTM: a ConvLSTM needs the stations on a regular grid and lets every grid cell see its neighbours. Gauges are not a grid, and a neighbour in distance is often not "
        "connected by water. Here the connections are chosen station by station.",
    ], size=14)

    # ---- 5 the rules
    sl = new("How the partners of a station are chosen")
    text(sl, 0.5, 1.05, 12.3, 6.0, [
        "Everything from the training period only.",
        "",
        f"1.  Class of the station, measured from its own water level: tidal if the tide explains at least 20% of its 6 h change ({int(nb.get('tidal', 0))} stations with real-time data), "
        f"weakly tidal from 5% ({int(nb.get('weakly tidal', 0))}), no tide below that ({int(nb.get('no tide', 0))}).",
        "",
        "2.  A station without tide may take partners only from upstream on its own river network (USGS river network data: real flow connections, not distance and not names).",
        "",
        "3.  A station with tide may take the stations on its river network, upstream and downstream, and any tidal station within 150 km.",
        "",
        "4.  Among the allowed stations: the one that explains most of the next 6 h change beyond the station's own history, then the next, up to four. Each must explain at least 1%.",
        "",
        "5.  Late data: in training the newest 1-3 h of each partner are removed in a quarter of the cases, so the model can cope when a partner has not reported yet.",
        "",
        "Rules 1 to 3 are the fourth attempt. Before: any station within 150 km; rivers and creeks only within 50 km; only on the same river network. Each step removed stations that had become worse.",
    ], size=BODY)

    sl = new("Partner stations on the map: inland the gauge upstream, on the coast the other tidal stations")
    talk_map = F / "partner_map_talk.png"
    yb = picture(sl, talk_map if talk_map.exists() else F / "partner_map_wide.png", 0.3, 0.9, 12.7, 6.0)
    text(sl, 0.5, yb + 0.02, 12.3, 0.5, [
        f"The {len(rt)} stations with real-time data. Colour: what the station's own water level does. All links, including those between tidal stations, are on the last slide."], size=11.5)

    # ---- 6 results in the test years
    rounds = [("hrrr_total", "No partner stations  (the version that is run)"), ("partners4", "Partners: any station within 150 km"),
              ("partners4_river50", "Partners: rivers and creeks only within 50 km"),
              ("partners4_network_lateaug", ["Partners: rivers and creeks only on the same river network,", "trained with the newest hours of the partners missing"]),
              ("partners4_behaviour_lateaug", ["Partners by measured tide and upstream direction,", "trained with the newest hours of the partners missing"])]
    rounds = [(k, lab) for k, lab in rounds if k in Q]
    sl = new(f"Partner stations in the test years: {run['h6']:.2f} to {par['h6']:.2f} cm at 6 h")
    cols = [(0.5, 4.9, L), (5.4, 0.8, R), (6.2, 0.8, R), (7.0, 0.8, R), (7.8, 0.7, R), (8.6, 0.75, R), (9.35, 0.75, R), (10.1, 0.75, R), (10.85, 0.75, R), (11.6, 1.3, R)]
    rows = []
    for k, lab in rounds:
        s = Q[k]; ag = against(G[k], ref) if k != "hrrr_total" else None
        rows.append([lab, f"{s['h6']:.2f}", f"{s['event']:.1f}", f"{s['storm']:.1f}", f"{s['lag']:.2f}", f"{s['tide gauge']:.2f}", f"{s['estuary / tidal channel']:.2f}", f"{s['river / canal']:.2f}",
                     f"{s[uc]:.2f}", f"{ag['clear_worse']}" if ag else ""])
    y = table(sl, 1.05, cols, ["6 h RMSE (cm), all five-model means", ["all", "forecasts"], ["largest", "1%"], ["hurri-", "canes"], ["lag", "(h)"], ["tide", "gauges"], ["estu-", "aries"], "rivers",
                               ["urban", "creeks"], ["stations", "clearly worse"]], rows, size=12, hl=0, step=0.33)
    text(sl, 0.5, y + 0.3, 12.3, 3.2, [
        f"{n_st} stations, about 1.25 million forecasts, the same forecasts in every row. Last column: stations where all five single models are worse than all five of the version that is run.",
        "",
        f"-  Last row against the version that is run: {100 * (par['h6'] / run['h6'] - 1):+.1f}% at 6 h, hurricanes {run['storm']:.1f} to {par['storm']:.1f} cm; {pag['better']} stations better and {pag['worse']} worse by more than 0.5 cm.",
        f"-  Who gains: stations that feel the tide, about 10% (tide gauges {run['tide gauge']:.2f} to {par['tide gauge']:.2f} cm), and river stations with a gauge upstream.",
        f"-  Urban creeks gain little ({run[uc]:.2f} to {par[uc]:.2f} cm): neighbouring creeks rise together, none earlier. They lack the rainfall of the next hours.",
        "-  Choosing partners by distance alone made 24 stations clearly worse: creeks far apart are related only through the weather passing over both.",
    ], size=BODY)

    # ---- 7 late data
    late = [("No partner stations  (the version that is run)", "hrrr_total", None, "hrrr_total_ownlate1"),
            (["Partners (rivers and creeks within 50 km),", "trained with complete partner data"], "partners4_river50", "partners4_river50_late{}", "partners4_river50_ownlate1_late1"),
            (["Partners by measured tide and upstream direction,", "trained with the newest hours of the partners missing"], "partners4_behaviour_lateaug", "partners4_behaviour_lateaug_late{}",
             "partners4_behaviour_lateaug_ownlate1_late1")]
    h6 = lambda name: (lambda X: pool(X[X.model == "mean"], "rmse_6h_cm") if X is not None else None)(load(name))
    sl = new("Partner data that arrive late: trained for it, the gain survives a delay of one to two hours")
    cols = [(0.5, 4.8, L), (5.4, 1.0, R), (6.5, 1.1, R), (7.7, 1.1, R), (8.9, 1.1, R), (10.1, 1.1, R), (11.3, 1.6, R)]
    rows, vals = [], {}
    for lab, on, pat, both in late:
        if h6(on) is None:
            continue
        v = [h6(on)] + [h6(on) if pat is None else h6(pat.format(k)) for k in (1, 2, 3, 6)] + [h6(both)]
        vals[on] = v; rows.append([lab] + [f"{x:.2f}" if x is not None else "" for x in v])
    y = table(sl, 1.05, cols, ["6 h RMSE over all forecasts (cm), test years", "on time", ["partners", "1 h late"], ["partners", "2 h late"], ["partners", "3 h late"], ["partners", "6 h late"],
                               ["station and partners", "both 1 h late"]], rows, size=12.5, hl=0, step=0.34)
    a_, c_, n_ = vals["hrrr_total"], vals["partners4_river50"], vals["partners4_behaviour_lateaug"]
    text(sl, 0.5, y + 0.35, 12.3, 3.2, [
        "In real time the newest hours of a partner may be missing. Here the newest 1, 2, 3 or 6 h of every partner are removed from the input, as the forecast script would see them.",
        "",
        f"-  Trained with complete partner data, the model relies on the partners: with the partners 1 h late it is already worse than without partners ({c_[1]:.2f} against {a_[0]:.2f} cm).",
        f"-  Trained with missing hours: nothing lost on time, better than without partners up to 2 h late, level at 3 h, worse at 6 h ({n_[4]:.2f} cm).",
        f"-  Closest to real time, station and partners both 1 h late: {a_[5]:.2f} to {n_[5]:.2f} cm.",
        "",
        "Open: a partner without data for more than 3 h.",
    ], size=BODY)

    # ---- 8 station types checked
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    x = rt.merge(g[K + ["type"]], on=K, suffixes=("", "_g"))
    ct = pd.crosstab(x.type, x.behaviour).reindex(columns=["tidal", "weakly tidal", "no tide"]).fillna(0).astype(int)
    sl = new("Station types checked against the water level itself: some registered types are wrong, and direction matters")
    cols = [(0.5, 2.6, L), (3.1, 0.8, R), (3.9, 1.0, R), (4.9, 0.9, R)]
    order = [("tide gauge", "Tide gauge"), ("estuary / tidal channel", "Estuary / tidal channel"), ("lake", "Lake"), ("marsh", "Marsh"), ("river / canal", "River"), (uc, "Urban creek")]
    y1 = table(sl, 1.05, cols, [["Type as registered", "(stations with real-time data)"], [" ", "tidal"], ["weakly", "tidal"], [" ", "no tide"]],
               [[lab] + [f"{int(ct.loc[t, c])}" for c in ct.columns] for t, lab in order if t in ct.index], size=12.5, step=0.33)
    cols = [(6.6, 3.9, L), (10.5, 1.1, R), (11.6, 1.2, R)]
    y2 = table(sl, 1.05, cols, [["River stations without tide, by their partners", "(change against the version that is run)"], ["validation", "year 2023"], ["test years", "2024-2025"]],
               [["No partner upstream  (150 stations)", "-1.0%", "0.0%"], ["One partner upstream  (54)", "-4.8%", "-3.4%"], ["Two partners upstream  (25)", "-8.2%", "-7.1%"],
                ["Partners downstream only  (39)", "-0.6%", "-0.1%"]], size=12.5, step=0.33)
    n_wrong = int(((x.type.isin(["tide gauge", "estuary / tidal channel", "lake", "marsh"])) & (x.behaviour != "tidal")).sum())
    n_tidal_river = int(((x.type.isin(["river / canal", uc])) & (x.behaviour == "tidal")).sum())
    text(sl, 0.5, max(y1, y2) + 0.35, 12.3, 3.0, [
        "The types used before are the site types registered by USGS. The check: the share of the 6 h change that a tide fit explains, from the training period of every station.",
        "",
        f"-  {n_wrong} stations registered as a tidal type have no or only weak tide (a canal behind a levee, an urban flood channel). As 'tidal' partners they made other stations worse.",
        f"-  {n_tidal_river} stations registered as rivers are tidal (Barataria Pass at Grand Isle: tide share 0.90).",
        "-  Direction matters more than the class: a river station without tide gains only from partners upstream (table on the right).",
        "-  Reservoirs between two stations: partners behind a reservoir still help at most stations. No rule was made.",
    ], size=BODY)

    # ---- 9 the forecast script on live data
    v = pd.read_csv(T / "verification_summary.csv")
    g_ = lambda by, grp, model: v[(v.group_by == by) & (v.group.astype(str) == grp) & (v.model == model)].iloc[0]
    f3 = lambda r: [f"{r.rmse_1h_cm:.2f}", f"{r.rmse_3h_cm:.2f}", f"{r.rmse_6h_cm:.2f}"]
    A, B, AL, BL = (g_("all", "all", m) for m in ("no partners", "partners", "no partners, USGS 1 h late", "partners, USGS 1 h late"))
    hr = pd.read_csv(T / "hourly_rmse.csv").pivot(index="lead", columns="model", values="rmse_cm")
    sl = new("Partner stations in the forecast script: tested on live data of 15 to 17 November")
    cols = [(0.5, 6.4, L), (7.0, 0.8, R), (7.9, 0.8, R), (8.8, 0.8, R)]
    y = table(sl, 1.05, cols, ["RMSE (cm), 418 stations, the same forecasts in both rows of a pair", "1 h", "3 h", "6 h"],
              [[f"A forecast every 6 h (10 forecast times): the version that is run"] + f3(A), ["     with partner stations"] + f3(B),
               ["The same, newest hour of every USGS gauge removed: the version that is run"] + f3(AL), ["     with partner stations"] + f3(BL),
               ["A forecast every hour (61 forecast times): the version that is run"] + [r2(hr.loc[h, 'run']) for h in (1, 3, 6)], ["     with partner stations"] + [r2(hr.loc[h, 'partners']) for h in (1, 3, 6)]],
              size=12.5, step=0.33)
    cols2 = [(10.0, 1.3, L), (11.2, 0.9, R), (12.1, 0.9, R)]
    table(sl, 1.05, cols2, [["6 h RMSE (cm),", "every 6 h"], ["version", "that is run"], ["with", "partners"]],
          [[lab, f"{g_('behaviour', k, 'no partners').rmse_6h_cm:.2f}", f"{g_('behaviour', k, 'partners').rmse_6h_cm:.2f}"] for k, lab in (("tidal", "Tidal"), ("weakly tidal", "Weakly tidal"), ("no tide", "No tide"))], size=12.5, step=0.33)
    text(sl, 0.5, y + 0.3, 12.3, 3.4, [
        "The forecast script builds the partner inputs from the same live readings. Both models were run for past forecast times and scored once the observations were in.",
        "",
        "Data hygiene:  the period is outside training, validation and test years;  both models read the same saved readings (no difference in 10,100 station rows);  no input later than the forecast time;  "
        "wind and rainfall forecasts only from HRRR cycles issued at or before the forecast time.",
        "",
        f"-  Same direction and size as in the test years ({run['h6']:.2f} to {par['h6']:.2f} cm there). The gain is again at the stations with tide.",
        "-  One rain event at Houston on 15 November (creeks rose by more than 1 m in 6 h). Neither model forecast it: rainfall, not partner stations.",
        "-  Two and a half days are not evidence of accuracy on their own. They show that the whole chain works on live data.",
    ], size=BODY)

    # ---- 10 station figures: the stations of the forecast check shown at the meeting
    two = sorted(T.glob("two_periods_slide_*.png")); one = sorted(T.glob("same_stations_wide_*.png"))
    figs = two or one
    for n_, f_ in enumerate(figs, 1):
        sl = new(("The eight stations of the forecast check of 12 November, both models, in two periods" if two else "The eight stations of the forecast check of 12 November, both models, 15 to 17 November") + f"  ({n_} of {len(figs)})")
        yb = picture(sl, f_, 0.2, 0.85, 12.93, 5.9)
        text(sl, 0.5, yb + 0.05, 12.3, 0.7, ["The stations were fixed before this test: they are the eight of the forecast check shown earlier. In each pair, left: the version that is run; right: with partner stations. "
                                             "Each line joins the forecasts issued 1, 3 or 6 h before the hour they are valid for, a forecast from every hour."], size=11.5)
    if (T / "stations_wide_1.png").exists():
        sl = new("The example of the idea: Lake Charles with the tide gauge at Calcasieu Pass as partner")
        yb = picture(sl, T / "stations_wide_1.png", 0.3, 0.9, 12.7, 5.85)
        text(sl, 0.5, yb + 0.05, 12.3, 0.7, ["15 to 17 November. Lake Charles: 6.6 to 4.6 cm at 6 h. Mississippi River at Baton Rouge, with no tide and a small daily change: the two models are alike. Left: the version that is run. Right: with partner stations."], size=11.5)
    if (T / "stations_wide_4.png").exists():
        sl = new("Where partner stations do not help: two stations picked to show it")
        yb = picture(sl, T / "stations_wide_4.png", 0.3, 0.9, 12.7, 5.85)
        text(sl, 0.5, yb + 0.05, 12.3, 0.7, ["These two were chosen as counter-examples; they are not typical. Buffalo Bayou: the rise of more than 1 m in 6 h is late in both models (rainfall forecast). Comite River: both forecast a rise "
                                             "that did not come. The left column, the version that is run, has the same errors: they do not come from the partner stations."], size=11.5)

    # ---- 11 the jagged lines
    if (T / "blend_rmse.csv").exists():
        bl = pd.read_csv(T / "blend_rmse.csv"); bl = bl[bl.subset == "all forecast times"]
        cell = lambda m, meth, h: (lambda z: r2(z.rmse_cm.iloc[0]) if len(z) and pd.notna(z.rmse_cm.iloc[0]) else "-")(bl[(bl.model == m) & (bl.method == meth) & (bl.lead == h)])
        sl = new("The lead-time lines are jagged because every point is a separate forecast; averaging neighbouring forecasts does not help")
        cols = [(0.5, 7.2, L), (7.8, 0.8, R), (8.7, 0.8, R), (9.6, 0.8, R), (10.5, 0.8, R)]
        meths = [("new", "The newest forecast alone"), ("mean2", "Mean with the forecast for the same hour issued 1 h earlier"),
                 ("anchor2", "The same, the older forecast first moved to the newest observation"), ("change2", "Newest observation + mean of the changes forecast at the last two forecast times")]
        rows = []
        for m, name in (("run", "The version that is run"), ("partners", "With partner stations")):
            for meth, lab in meths:
                rows.append([(name + ":  " if meth == "new" else "     ") + lab] + [cell(m, meth, h) for h in (1, 3, 5, 6)])
        y = table(sl, 1.25, cols, [f"RMSE (cm), a forecast from every hour, 418 stations, {int(bl.n.max()):,} forecasts per lead", "1 h", "3 h", "5 h", "6 h"], rows, size=12.5, step=0.33)
        text(sl, 0.5, y + 0.3, 12.3, 2.6, [
            "On the 6 h line every point comes from a different forecast time, each with its own error; joined, they are not smooth. The jags are about 2 cm at a quiet river and grow with the lead time.",
            "",
            "-  If the jags were independent errors, averaging neighbouring forecasts would lower the RMSE. Every way of combining is worse than the newest forecast alone, at every lead, for both models.",
            "-  The newest hour of observations is worth more than the smoothing. The forecasts are not combined and the lines in the figures are not smoothed.",
        ], size=BODY)

    # ---- 12 the run in real time (added when it has been scored)
    lv = T / "live_summary.csv"
    if lv.exists():
        z = pd.read_csv(lv)
        sl = new("A run in real time: forecast time 17 November 18 UTC, run at 18:31 and 19:05 UTC, scored six hours later")
        cols = [(0.5, 6.6, L), (7.2, 0.9, R), (8.2, 0.8, R), (9.1, 0.8, R), (10.0, 0.8, R)]
        y = table(sl, 1.05, cols, ["RMSE (cm), the same stations in every row", "forecasts", "1 h", "3 h", "6 h"],
                  [[r.label, f"{int(r.n):,}", f"{r.rmse_1h_cm:.2f}", f"{r.rmse_3h_cm:.2f}", f"{r.rmse_6h_cm:.2f}"] for r in z.itertuples()], size=12.5, step=0.33)
        note = T / "live_note.txt"
        if note.exists():
            text(sl, 0.5, y + 0.3, 12.3, 3.0, note.read_text(encoding="utf-8").strip().split("\n"), size=BODY)

    # ---- 13 where things stand
    sl = new("Where things stand")
    text(sl, 0.5, 1.05, 12.3, 6.2, [
        "Running:  scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models. Started by hand, not connected to the group's website.",
        "",
        f"Tested and ready, not switched on:  partner stations. {run['h6']:.2f} to {par['h6']:.2f} cm at 6 h in the test years, about 10% at stations with tide; the forecast script supports them and gave the same direction on live data.",
        "",
        "Not adopted:  partners chosen by distance;  a reservoir as a cut in the river network;  HRRR rainfall as two totals;  a starting state of its own for every station;  "
        "combining neighbouring forecasts;  ConvLSTM (stations are not a grid).",
        "",
        "Open:",
        "-  The rainfall forecast is the largest lever: a radar-based nowcast for hours 1-2, several HRRR cycles for hours 3-6.",
        "-  A partner station without data for more than 3 h.",
        "-  The hurricane numbers rest on two storms.",
        "-  Whether to switch the version that is run to the one with partner stations." + ("" if lv.exists() else "  The run in real time of 17 November 18 UTC is being scored."),
        "",
        "Useful beyond this model:  every station classed by its measured tide (config/station_behaviour.csv), and the stations upstream and downstream of every USGS station "
        "on the river network (config/station_river_network.csv).",
    ], size=BODY)

    # ---- backup: every partner link
    sl = new("Backup: every partner link")
    yb = picture(sl, F / "partner_map_wide.png", 0.3, 0.9, 12.7, 6.0)
    text(sl, 0.5, yb + 0.02, 12.3, 0.6, [
        "Grey lines: a station with tide may also take a station downstream on its river, because the tide comes up the river (30 links). Green dots: weakly tidal stations, where the tide explains 5 to 20% of the 6 h change; "
        "they choose partners like tidal stations but are not offered to others as a tidal partner."], size=11.5)

    prs.save(a.out)
    print(f"-> {a.out}: {len(prs.slides)} slides")


if __name__ == "__main__":
    main()
