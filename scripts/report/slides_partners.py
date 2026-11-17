"""Slides on the work after the group meeting of 13 November 2026, added to the deck that is arranged by hand.

Opens deliverables/17_versions/version_comparison.pptx as it was saved, leaves every existing slide as it is, and puts the
new slides before "Where things stand": the evaluation with five seeds, the rainfall of the next 6 h in two parts, the
partner stations (map, results, late data), the check of the station types, and a summary. Slides added by an earlier run
of this script are replaced (they carry the name "after_meeting"), so it can be run again when a new result is in.
Same style as slides_versions.py: white background, black Times New Roman, no page numbers.
Input : runs/protocol_<group>/protocol_station.csv, config/station_behaviour.csv, config/station_partners_*.csv,
        deliverables/31_partner_map.png
Usage : python slides_partners.py [--deck FILE --out FILE]     (default: the deck is updated in place)
"""
from __future__ import annotations

import argparse
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.enum.text import PP_ALIGN

from slides_figures import picture, text
from slides_versions import hilite

REPO = Path(__file__).resolve().parents[2]
F = REPO / "deliverables" / "17_versions"
K = ["source", "station_id"]
L, R = PP_ALIGN.LEFT, PP_ALIGN.RIGHT
TAG = "after_meeting"
TYPES = [("tide gauge", "Tide gauges"), ("estuary / tidal channel", "Estuaries"), ("lake", "Lakes"), ("river / canal", "Rivers"), ("urban creek (Houston)", "Urban creeks")]
RUN = "Scaling + gap filling + HRRR rainfall, trained with missing hours, mean of 5 models"


def load(name: str) -> pd.DataFrame | None:
    f = REPO / "runs" / f"protocol_{name}" / "protocol_station.csv"
    if not f.exists():
        return None
    x = pd.read_csv(f, dtype={"station_id": str})
    return x[x.n_6h >= 720]


def pool(x: pd.DataFrame, col: str, n: str = "n_6h") -> float:
    w = x[n].to_numpy(float); v = np.nan_to_num(x[col].to_numpy(float))
    return float(np.sqrt((w * v ** 2).sum() / max(w.sum(), 1)))


def q(X: pd.DataFrame) -> dict:
    """Quantities of the mean of the members, and the range of the single members for the 6 h RMSE and the hurricanes."""
    x = X[X.model == "mean"]; mem = [m for m in X.model.unique() if m != "mean"]
    d = {"h1": pool(x, "rmse_1h_cm"), "h3": pool(x, "rmse_3h_cm"), "h6": pool(x, "rmse_6h_cm"), "event": pool(x, "rmse_event_6h_cm", "n_event"),
         "rise": pool(x, "rmse_rise_6h_cm", "n_rise"), "fall": pool(x, "rmse_fall_6h_cm", "n_fall"), "storm": pool(x, "rmse_storm_6h_cm", "n_storm"),
         "lag": float(x.lag_h[x.n_timing >= 10].mean()), "share": float(np.nansum(x.n_timing * x.rise_fc_cm) / np.nansum(x.n_timing * x.rise_obs_cm)),
         "h6_single": [pool(X[X.model == m], "rmse_6h_cm") for m in mem], "storm_single": [pool(X[X.model == m], "rmse_storm_6h_cm", "n_storm") for m in mem],
         "lag_single": [float(X[X.model == m].lag_h[X[X.model == m].n_timing >= 10].mean()) for m in mem]}
    for t, _ in TYPES:
        y = x[x.type == t]
        d[t] = pool(y, "rmse_6h_cm"); d[t + "|med"] = float(y.rmse_6h_cm.median()); d[t + "|event"] = pool(y, "rmse_event_6h_cm", "n_event")
        d[t + "|storm"] = pool(y, "rmse_storm_6h_cm", "n_storm"); d[t + "|lag"] = float(y.lag_h[y.n_timing >= 10].mean()); d[t + "|n"] = len(y)
    return d


def against(X: pd.DataFrame, REF: pd.DataFrame) -> dict:
    """Station by station against the reference group: better / worse by more than 0.5 cm, and stations where every single
    member is worse than every single member of the reference."""
    a = REF[REF.model == "mean"].set_index(K).rmse_6h_cm; b = X[X.model == "mean"].set_index(K).rmse_6h_cm.reindex(a.index)
    mem = lambda Z: Z[Z.model != "mean"].set_index(K + ["model"]).rmse_6h_cm.unstack("model").reindex(a.index)
    ma, mb = mem(REF), mem(X)
    return {"better": int((b - a < -0.5).sum()), "worse": int((b - a > 0.5).sum()), "clear_worse": int((mb.min(1) > ma.max(1)).sum()), "clear_better": int((mb.max(1) < ma.min(1)).sum())}


def table(sl, y, cols, head, rows, size=11, hl=None, step=0.29):
    """Text-box table: cols = [(x, width, align)], rows = lists of cells (a cell may be a list of lines); hl = index of the highlighted row."""
    for (x, w, al), h in zip(cols, head):
        text(sl, x, y, w, 0.3, h, size=size, bold=True, align=al)
    y += step + 0.17 * any(isinstance(h, list) for h in head)
    for i, r in enumerate(rows):
        two = any(isinstance(c, list) for c in r)
        if i == hl:
            hilite(sl, cols[0][0] - 0.08, y - 0.01, cols[-1][0] + cols[-1][1] - cols[0][0] + 0.16, step - 0.02 + 0.17 * two)
        for (x, w, al), c in zip(cols, r):
            text(sl, x, y, w, 0.3, c, size=size, bold=i == hl, align=al)
        y += step + 0.17 * two
    return y


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--deck", default=str(F / "version_comparison.pptx")); ap.add_argument("--out")
    a = ap.parse_args()
    src = Path(a.deck); dst = Path(a.out) if a.out else src
    prs = Presentation(str(src)); blank = prs.slide_layouts[6]
    ids = prs.slides._sldIdLst
    for el in list(ids):                                    # slides of an earlier run of this script
        if prs.part.related_part(el.rId).slide.name == TAG:
            prs.part.drop_rel(el.rId); ids.remove(el)
    n_before = len(ids); new_els = []

    def new(title):
        sl = prs.slides.add_slide(blank); sl._element.cSld.set("name", TAG); new_els.append(ids[-1])
        text(sl, 0.5, 0.3, 12.3, 0.5, title, size=17, bold=True)
        return sl

    G = {k: load(k) for k in ["hrrr_total", "split_none", "split_early", "split_late", "split_both", "partners4", "partners4_river50", "partners4_river50_lateaug",
                              "partners4_network_lateaug", "partners4_behaviour_lateaug"]}
    Q = {k: q(v) for k, v in G.items() if v is not None}
    run = Q["hrrr_total"]; n_st = int((G["hrrr_total"].model == "mean").sum())

    # ---- 1 how versions are compared
    sl = new("After the group meeting: every version is trained five times, and four numbers are reported besides the average")
    cols = [(0.5, 4.0, L), (4.5, 1.3, R), (5.9, 1.7, R)]
    y = table(sl, 1.0, cols, [RUN.split(", trained")[0] + ",", "mean of 5", "single models"], [], size=11)
    text(sl, 0.5, 1.17, 4.0, 0.3, "trained with missing hours  (the version that is run)", size=11, bold=True)
    rng = lambda v, f="{:.2f}": f"{f.format(min(v))} to {f.format(max(v))}"
    rows = [["All forecasts, 1 / 3 / 6 h ahead (cm)", f"{run['h1']:.2f} / {run['h3']:.2f} / {run['h6']:.2f}", "6 h: " + rng(run["h6_single"])],
            ["Largest 1% of the 6 h changes, 6 h (cm)", f"{run['event']:.1f}", ""], ["    of these: rises", f"{run['rise']:.1f}", ""], ["    of these: falls", f"{run['fall']:.1f}", ""],
            ["Hurricane periods, 6 h (cm)", f"{run['storm']:.1f}", rng(run["storm_single"], "{:.1f}")], ["Lag of the forecast on the rises (h)", f"{run['lag']:.2f}", rng(run["lag_single"])],
            ["Share of the observed rise that is forecast", f"{run['share']:.2f}", ""]]
    y = 1.55
    for r in rows:
        for (x, w, al), c in zip(cols, r):
            text(sl, x, y, w, 0.3, c, size=11, align=al)
        y += 0.29
    cols2 = [(8.0, 1.5, L), (9.4, 0.7, R), (10.1, 1.0, R), (11.1, 0.9, R), (12.0, 0.8, R)]
    table(sl, 1.0, cols2, ["By station type", "stations", ["largest 1%,", "6 h (cm)"], ["hurricanes,", "6 h (cm)"], ["lag on the", "rises (h)"]],
          [[lab, f"{run[t + '|n']}", f"{run[t + '|event']:.1f}", f"{run[t + '|storm']:.1f}", f"{run[t + '|lag']:.1f}"] for t, lab in TYPES], size=11)
    text(sl, 0.5, 3.85, 12.3, 3.4, [
        "Why. Another random seed alone moves the 6 h RMSE over all stations by about 0.04 cm and single stations in a hurricane by a factor of two. From now on every setting is trained with five seeds, "
        "and the mean of five models is compared with the mean of five models on the same forecasts. A difference counts only if it is larger than the differences between single models.",
        "",
        f"Same test period (2024-2025), forecasts at 00, 06, 12 and 18 UTC, {n_st} stations with real-time data. Next to the RMSE over all forecasts:",
        "Largest 1% of the 6 h changes: the forecasts whose observed 6 h change is above the 99% quantile of that station in the training period, rises and falls separately.",
        "Hurricane periods: Beryl in the Texas and Galveston domains, Francine in the Louisiana domain.",
        "Lag on the rises: the shift in time (0 to 8 h) that brings the 6 h forecast closest to the observation on the rises. 0 h = the forecast rises with the observation, 6 h = it only repeats the last level.",
        "Share of the rise: forecast 6 h rise divided by observed 6 h rise on the same forecasts.",
        "",
        f"What these numbers show for the version that is run: the error sits in the rises ({run['rise']:.0f} cm against {run['fall']:.0f} cm on the falls), the model forecasts {100 * run['share']:.0f}% of an observed rise "
        f"and is {run['lag']:.1f} h late on average, {run['urban creek (Houston)|lag']:.1f} h at urban creeks. Averaging five models does not change the lag.",
    ], size=11.5)

    # ---- 2 rainfall in two parts
    sp = [Q[k] for k in ("split_none", "split_early", "split_late", "split_both")]
    sl = new("Rainfall of the next 6 hours in two parts: how much of the error comes from hours 1-2 and from hours 3-6")
    cols = [(0.5, 3.4, L), (3.9, 0.9, R), (4.8, 0.9, R), (5.7, 0.9, R), (6.8, 1.3, R), (8.2, 1.3, R), (9.6, 1.2, R), (10.9, 1.7, R)]
    labs = ["HRRR forecast / HRRR forecast", "Observed / HRRR forecast", "HRRR forecast / observed", "Observed / observed"]
    y = table(sl, 1.0, cols, [["Rainfall of hours 1-2 /", "rainfall of hours 3-6"], ["1 h", "(cm)"], ["3 h", "(cm)"], ["6 h", "(cm)"], ["largest 1%,", "6 h (cm)"], ["hurricanes,", "6 h (cm)"],
                              ["lag on the", "rises (h)"], ["share of the", "rise forecast"]],
              [[lab, f"{s['h1']:.2f}", f"{s['h3']:.2f}", f"{s['h6']:.2f}", f"{s['event']:.1f}", f"{s['storm']:.1f}", f"{s['lag']:.2f}", f"{s['share']:.2f}"] for lab, s in zip(labs, sp)], size=11.5, step=0.31)
    gap = lambda k: sp[0][k] - sp[3][k]
    fr = lambda k, i: 100 * (sp[0][k] - sp[i][k]) / gap(k)
    uc = "urban creek (Houston)"
    text(sl, 0.5, y + 0.25, 12.3, 4.2, [
        "What was done. The version that is run gets the HRRR rainfall of the next 6 h as one total. Here it is given as two totals, hours 1-2 and hours 3-6, and each part comes either from the HRRR forecast or from the "
        "observed rainfall. Observed rainfall of the future is not available in real time: this measures how much a perfect rainfall forecast for that part would be worth. Four combinations, five seeds each, 20 trainings.",
        "",
        f"The distance between forecast and observed rainfall is {gap('h6'):.2f} cm at 6 h. Hours 1-2 account for {fr('h6', 1):.0f}% of it, hours 3-6 for {fr('h6', 2):.0f}%; the two gains add up.",
        f"A perfect rainfall forecast for hours 1-2 alone (what a radar-based nowcast can aim at) gives nearly the whole gain at 3 h ({sp[0]['h3']:.2f} to {sp[1]['h3']:.2f} cm) but less than half at 6 h.",
        f"In the hurricanes the later hours matter most: {sp[0]['storm']:.1f} to {sp[2]['storm']:.1f} cm with observed rainfall in hours 3-6, {fr('storm', 2):.0f}% of the distance.",
        f"The lag comes largely from the rainfall forecast: {sp[0]['lag']:.2f} to {sp[3]['lag']:.2f} h over all stations, {sp[0][uc + '|lag']:.1f} to {sp[3][uc + '|lag']:.1f} h at urban creeks. "
        "At urban creeks the lag is a rainfall problem, not a model problem.",
        f"What remains with perfect rainfall: {sp[3]['lag']:.2f} h of lag, {sp[3]['event']:.1f} cm on the largest changes, {100 * sp[3]['share']:.0f}% of the rise forecast. Tide gauges and lakes do not depend on rainfall "
        f"({sp[0]['tide gauge']:.2f} to {sp[3]['tide gauge']:.2f} cm and {sp[0]['lake']:.2f} to {sp[3]['lake']:.2f} cm).",
        "",
        f"Conclusion: the largest remaining error is the rainfall forecast, {sp[0]['h6']:.2f} against {sp[3]['h6']:.2f} cm, with the model unchanged. Giving HRRR as two totals instead of one is worth 0.04 cm and was not adopted.",
    ], size=11.5)

    # ---- 3 partner stations: what they are
    beh = pd.read_csv(REPO / "config" / "station_behaviour.csv", dtype={"station_id": str}); rt = beh[beh.source != "CRMS"]
    nb = rt.behaviour.value_counts()
    sl = new("Partner stations: the water level of other stations as input")
    text(sl, 0.5, 1.0, 12.3, 6.2, [
        "Idea. At some stations the next change shows first somewhere else: the tide and a surge reach the coast before the inner bay, and a flood wave reaches the gauge upstream before the one downstream. "
        "Each station is given the water level of the past 72 h at up to four such partner stations as extra input. It is still one LSTM for all stations, and no new data source is needed: "
        "the partners are stations of the same real-time feed.",
        "",
        "Example. Lake Charles lies 52 km inland of Calcasieu Pass. With the water level at Calcasieu Pass as input, its 6 h RMSE falls from 5.4 to 3.5 cm.",
        "",
        "How the partners of a station are chosen (training period only):",
        f"1.  Each station is classed by its own water level: tidal if the tide explains at least 20% of its 6 h change ({int(nb.get('tidal', 0))} stations with real-time data), "
        f"weakly tidal from 5% ({int(nb.get('weakly tidal', 0))}), no tide below that ({int(nb.get('no tide', 0))}).",
        "2.  A station without tide may take partners only from upstream on its river network. The network comes from the USGS river network data: real flow connections, not distance and not station names.",
        "3.  A station with tide may take the stations on its river network, upstream and downstream, and within 150 km any station that is tidal itself.",
        "4.  Among those, the station that explains most of the next 6 h change beyond the station's own history is picked, then the next one, up to four. A pick must explain at least 1%.",
        "",
        "Late data. In real time the newest hours of a partner may not have arrived. In training, the newest 1-3 h of each partner are removed in a quarter of the cases, so the model learns to cope with it.",
        "",
        "The rules in points 1 to 3 are the result of four rounds (next slides): partners by correlation and distance, then rivers and creeks only within 50 km, then only on the same river network, "
        "then by measured tide and upstream direction.",
    ], size=12)

    sl = new("Partner stations on the map: down the rivers inland, along the coast for the tidal stations")
    yb = picture(sl, F / "partner_map_wide.png", 0.3, 0.9, 12.7, 6.0)
    text(sl, 0.5, yb + 0.02, 12.3, 0.6, [
        f"The {len(rt)} stations with real-time data. Most hollow dots are inland gauges with no gauge upstream of them; they have no partner and are forecast as before. "
        "CRMS stations are used for training only and are not drawn."], size=11)

    # ---- 4 partner stations: results
    ref = G["hrrr_total"]
    rounds = [("hrrr_total", [RUN.split(", mean")[0] + ",", "mean of 5 models: no partner stations  (the version that is run)"]),
              ("partners4", "+ partners: any station within 150 km"),
              ("partners4_river50", "+ partners: rivers and creeks only within 50 km"),
              ("partners4_river50_lateaug", ["+ partners: rivers and creeks only within 50 km,", "trained with the newest hours of the partners missing"]),
              ("partners4_network_lateaug", ["+ partners: rivers and creeks only on the same river network,", "trained with the newest hours of the partners missing"]),
              ("partners4_behaviour_lateaug", ["+ partners by measured tide and upstream direction,", "trained with the newest hours of the partners missing"])]
    rounds = [(k, lab) for k, lab in rounds if k in Q]
    sl = new("Partner stations: results")
    cols = [(0.5, 4.6, L), (5.1, 0.7, R), (5.85, 0.8, R), (6.7, 0.9, R), (7.6, 0.7, R), (8.4, 0.75, R), (9.15, 0.8, R), (9.95, 0.7, R), (10.65, 0.75, R), (11.45, 1.4, R)]
    rows = []
    for k, lab in rounds:
        s = Q[k]; ag = against(G[k], ref) if k != "hrrr_total" else None
        rows.append([lab, f"{s['h6']:.2f}", f"{s['event']:.1f}", f"{s['storm']:.1f}", f"{s['lag']:.2f}", f"{s['tide gauge']:.2f}", f"{s['estuary / tidal channel']:.2f}", f"{s['river / canal']:.2f}",
                     f"{s['urban creek (Houston)']:.2f}", f"{ag['better']} / {ag['worse']}  ({ag['clear_worse']})" if ag else ""])
    y = table(sl, 1.0, cols, ["6 h RMSE (cm), all five-model means", ["all", "forecasts"], ["largest", "1%"], ["hurri-", "canes"], ["lag", "(h)"], ["tide", "gauges"], ["estu-", "aries"], "rivers",
                              ["urban", "creeks"], ["better / worse", "(clearly worse)"]], rows, size=10.5, hl=0, step=0.3)
    best_k = rounds[-1][0]; b = Q[best_k]; bag = against(G[best_k], ref)
    net = Q.get("partners4_network_lateaug", b)
    pending = "partners4_behaviour_lateaug" not in Q
    text(sl, 0.5, y + 0.2, 12.3, 3.4, [
        f"Every row is the first row plus partner-station input, five seeds each, {n_st} stations, the same forecasts. Station columns: pooled over all forecasts of that type. Last column: stations better / worse than the "
        "version that is run by more than 0.5 cm at 6 h; in brackets the stations where all five single models are worse than all five of the version that is run.",
        "",
        f"With partners chosen by river network: {run['h6']:.2f} to {net['h6']:.2f} cm at 6 h ({100 * (net['h6'] / run['h6'] - 1):+.1f}%), hurricanes {run['storm']:.1f} to {net['storm']:.1f} cm, "
        f"lag {run['lag']:.2f} to {net['lag']:.2f} h. All outside the differences between seeds.",
        f"Who gains: tidally influenced stations, about 10% (tide gauges {run['tide gauge']:.2f} to {net['tide gauge']:.2f} cm, estuaries {run['estuary / tidal channel']:.2f} to {net['estuary / tidal channel']:.2f} cm), "
        "and river stations with a gauge upstream on the same river.",
        "What did not work: choosing partners by correlation and distance alone. Creeks 60-150 km apart are related only through the weather that passes over both; that timing does not hold in other years, "
        "and 24 stations became clearly worse. Each tightening of the rule (50 km, then the river network) removed part of them.",
        f"Urban creeks gain little ({run['urban creek (Houston)']:.2f} to {net['urban creek (Houston)']:.2f} cm): neighbouring creeks rise together, none of them earlier. What they lack is the rainfall of the next hours.",
        ("The round with partners by measured tide and upstream direction (next slides) is being trained; its row will be added." if pending else
         f"Last row, partners by measured tide and upstream direction: {b['h6']:.2f} cm at 6 h ({100 * (b['h6'] / run['h6'] - 1):+.1f}%), {bag['better']} stations better and {bag['worse']} worse by more than 0.5 cm. "
         f"Against the river-network round the {net['h6'] - b['h6']:.2f} cm are within the differences between seeds; what the rule changes is that it needs fewer partners "
         "(157 instead of 86 stations without partner, at no cost) and no longer depends on the registered station types."),
        "",
        "The version that is run has not been changed.",
    ], size=11.5)

    # ---- 5 late partner data
    late = [("No partner stations  (the version that is run)", "hrrr_total", None, "hrrr_total_ownlate1"),
            (["Partners (rivers and creeks within 50 km),", "trained with complete partner data"], "partners4_river50", "partners4_river50_late{}", "partners4_river50_ownlate1_late1"),
            (["Partners by river network, trained with", "the newest hours of the partners missing"], "partners4_network_lateaug", "partners4_network_lateaug_late{}", "partners4_network_lateaug_ownlate1_late1"),
            (["Partners by measured tide and upstream direction,", "trained with the newest hours of the partners missing"], "partners4_behaviour_lateaug", "partners4_behaviour_lateaug_late{}",
             "partners4_behaviour_lateaug_ownlate1_late1")]
    h6 = lambda name: (lambda X: pool(X[X.model == "mean"], "rmse_6h_cm") if X is not None else None)(load(name))
    tg = lambda name: (lambda X: pool(X[(X.model == "mean") & (X.type == "tide gauge")], "rmse_6h_cm") if X is not None else None)(load(name))
    sl = new("Partner data that arrive late: trained for it, the gain survives a delay of one to two hours")
    cols = [(0.5, 4.4, L), (5.0, 1.0, R), (6.1, 1.1, R), (7.3, 1.1, R), (8.5, 1.1, R), (9.7, 1.1, R), (11.0, 1.8, R)]
    rows, vals = [], {}
    for lab, on, pat, both in late:
        if h6(on) is None:
            continue
        v = [h6(on)] + [h6(on) if pat is None else h6(pat.format(k)) for k in (1, 2, 3, 6)] + [h6(both)]
        vals[on] = v; rows.append([lab] + [f"{x:.2f}" if x is not None else "" for x in v])
    y = table(sl, 1.0, cols, ["6 h RMSE over all forecasts (cm)", "on time", ["partners", "1 h late"], ["partners", "2 h late"], ["partners", "3 h late"], ["partners", "6 h late"],
                              ["station and partners", "both 1 h late"]], rows, size=11.5, hl=0, step=0.31)
    a_, c_, n_ = vals["hrrr_total"], vals["partners4_river50"], vals["partners4_network_lateaug"]
    text(sl, 0.5, y + 0.25, 12.3, 3.6, [
        "The numbers on the previous slide assume that the partners have reported up to the forecast time. In real time their newest hours may be missing. Here the newest 1, 2, 3 or 6 h of every partner are removed "
        "from the input, exactly as the forecast script would see them; the station itself is on time, except in the last column.",
        "",
        f"Trained with complete partner data, the model relies on the partners and is caught out: {c_[0]:.2f} cm on time, {c_[1]:.2f} cm with the partners 1 h late - already worse than without partners ({a_[0]:.2f} cm) - "
        f"and {c_[3]:.2f} cm at 3 h. Tide gauges: {tg('partners4_river50'):.2f} to {tg('partners4_river50_late3'):.2f} cm at 3 h, against {tg('hrrr_total'):.2f} cm without partners. The stations that gain most lose most.",
        f"Trained with the newest 1-3 h of each partner removed in a quarter of the cases: nothing is lost on time, and the error grows slowly: {n_[1]:.2f}, {n_[2]:.2f} and {n_[3]:.2f} cm with the partners 1, 2 and 3 h late. "
        f"Better than without partners up to 2 h, level at 3 h, worse at 6 h ({n_[4]:.2f} cm; a delay that long was not in the training).",
        f"Closest to real time, station and partners both 1 h late: {a_[5]:.2f} to {n_[5]:.2f} cm ({100 * (n_[5] / a_[5] - 1):+.1f}%). Half of the USGS gauges have the reading of the hour after 32 minutes, nine in ten after 57 minutes.",
        "",
        "The partners by measured tide and upstream direction behave like the partners by river network when the data are late (last row).",
        "Open: a partner without data for more than 3 h. Either train with longer gaps, or fall back to the version without partners for those stations.",
    ], size=11.5)

    # ---- 6 station types checked
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    x = rt.merge(g[K + ["type"]], on=K, suffixes=("", "_g"))
    ct = pd.crosstab(x.type, x.behaviour).reindex(columns=["tidal", "weakly tidal", "no tide"]).fillna(0).astype(int)
    pm = pd.read_csv(REPO / "config" / "station_partners_network.csv", dtype=str).fillna("")
    pm = pm[pm.source != "CRMS"]
    used = lambda nm: int(sum(pm[f"p{j}_name"].str.contains(nm, regex=False).sum() for j in range(1, 5)))
    share = lambda nm: float(rt[rt.name.str.contains(nm, regex=False)].tide_share_6h.iloc[0])
    sl = new("Station types checked against the water level itself: some types are wrong, and direction matters")
    cols = [(0.5, 2.3, L), (2.8, 0.8, R), (3.6, 1.0, R), (4.6, 0.9, R)]
    order = [("tide gauge", "Tide gauge"), ("estuary / tidal channel", "Estuary / tidal channel"), ("lake", "Lake"), ("marsh", "Marsh"), ("river / canal", "River"), ("urban creek (Houston)", "Urban creek")]
    y1 = table(sl, 1.0, cols, [["Type as registered", "(stations with real-time data)"], [" ", "tidal"], ["weakly", "tidal"], [" ", "no tide"]],
               [[lab] + [f"{int(ct.loc[t, c])}" for c in ct.columns] for t, lab in order if t in ct.index], size=11)
    cols = [(6.0, 4.0, L), (10.0, 1.2, R), (11.3, 1.5, R)]
    ex = [("Y-Pipeline Cnl", "Y-Pipeline Canal, New Orleans East  (marsh)"), ("Lake Pelba", "Lake Pelba at I-10  (lake)"), ("Buffalo Bayou at Houston", "Buffalo Bayou at Houston  (estuary)")]
    y2 = table(sl, 1.0, cols, [["Registered as a tidal type,", "almost no tide in the data"], ["tide share of", "the 6 h change"], ["chosen as partner", "by ... stations"]],
               [[lab, f"{share(nm):.2f}", f"{used(nm)}"] for nm, lab in ex], size=11)
    cols = [(6.0, 4.0, L), (10.0, 1.2, R), (11.3, 1.5, R)]
    y2 = table(sl, y2 + 0.2, cols, [["River stations without tide, by their partners", "(change against the version that is run)"], ["validation", "year 2023"], ["test years", "2024-2025"]],
               [["No partner upstream  (150 stations)", "-1.0%", "0.0%"], ["One partner upstream  (54)", "-4.8%", "-3.4%"], ["Two partners upstream  (25)", "-8.2%", "-7.1%"],
                ["Partners downstream only  (39)", "-0.6%", "-0.1%"]], size=11)
    n_wrong = int(((x.type.isin(["tide gauge", "estuary / tidal channel", "lake", "marsh"])) & (x.behaviour != "tidal")).sum())
    n_tidal_river = int(((x.type.isin(["river / canal", "urban creek (Houston)"])) & (x.behaviour == "tidal")).sum())
    text(sl, 0.5, max(y1, y2) + 0.25, 12.3, 3.2, [
        "Question: with partners chosen by river network, 8 stations were still clearly worse. Are stations in the wrong class? The station types used so far are the site types registered by USGS, not what the water level does. "
        "Check: the share of the 6 h change that a harmonic tide fit explains, from the training period of every station, next to the public NHDPlus river-segment data.",
        "",
        f"{n_wrong} stations registered as a tidal type have no or only weak tide; as 'tidal' stations they could be chosen as partner by any station within 150 km. "
        "Of the 15 stations that became worse, 8 had chosen one of them (six the Y-Pipeline Canal, a canal behind the levee; two Buffalo Bayou at Houston, an urban flood channel).",
        f"{n_tidal_river} stations registered as rivers are tidal (Barataria Pass at Grand Isle: tide share 0.90). No harm, but information that was not used. The tidal flag of NHDPlus is not reliable either "
        "(49 of 148 flagged stations have no tide), so the class is taken from the water level.",
        "Direction matters more than the class: a river station without tide gains only from partners upstream. A flood wave comes down the river; a gauge downstream says nothing about it. Same result in the validation year and in the test years.",
        "Reservoirs: public waterbody data give the lakes and reservoirs between every pair of stations. Partners behind a reservoir still help at most stations; only the gauge directly below the Lake Livingston dam got worse. "
        "No general rule; single stations like that one are found with the validation year.",
    ], size=11)

    # ---- the forecast script with partner stations, tested on past forecast times from the live services
    T = REPO / "deliverables" / "33_partner_live_test"
    if (T / "verification_summary.csv").exists():
        v = pd.read_csv(T / "verification_summary.csv")
        g_ = lambda by, grp, model: v[(v.group_by == by) & (v.group.astype(str) == grp) & (v.model == model)].iloc[0]
        f3 = lambda r: [f"{r.rmse_1h_cm:.2f}", f"{r.rmse_3h_cm:.2f}", f"{r.rmse_6h_cm:.2f}"]
        A, B, AL, BL = (g_("all", "all", m) for m in ("no partners", "partners", "no partners, USGS 1 h late", "partners, USGS 1 h late"))
        sl = new("Partner stations in the forecast script: ten past forecast times from the live data services")
        cols = [(0.5, 5.2, L), (5.8, 0.8, R), (6.7, 0.8, R), (7.6, 0.8, R)]
        y = table(sl, 1.0, cols, [f"RMSE (cm), {int(A.n):,} forecasts at 418 stations", "1 h", "3 h", "6 h"],
                  [["Data complete: no partner stations  (the version that is run)"] + f3(A), ["Data complete: with partner stations"] + f3(B),
                   ["Newest hour of every USGS gauge removed: no partner stations"] + f3(AL), ["Newest hour of every USGS gauge removed: with partner stations"] + f3(BL)], size=11.5, hl=0, step=0.31)
        cols2 = [(9.0, 1.6, L), (10.4, 1.2, R), (11.6, 1.2, R)]
        table(sl, 1.0, cols2, [["6 h RMSE (cm),", "data complete"], ["no partner", "stations"], ["with partner", "stations"]],
              [[lab, f"{g_('behaviour', k, 'no partners').rmse_6h_cm:.2f}", f"{g_('behaviour', k, 'partners').rmse_6h_cm:.2f}"] for k, lab in (("tidal", "Tidal"), ("weakly tidal", "Weakly tidal"), ("no tide", "No tide"))], size=11.5, step=0.31)
        hr = pd.read_csv(T / "hourly_rmse.csv").pivot(index="lead", columns="model", values="rmse_cm") if (T / "hourly_rmse.csv").exists() else None
        text(sl, 0.5, y + 0.3, 12.3, 4.2, [
            "What was done. The forecast script now builds the partner inputs from the same live readings. It was run for the forecast times 15 November 00 UTC to 17 November 06 UTC 2026, every 6 hours, with the five models of the "
            "last row of the results slide and with the version that is run. Six hours later the observations were fetched and both were scored on the same forecasts.",
            "",
            f"Result: {A.rmse_6h_cm:.2f} to {B.rmse_6h_cm:.2f} cm at 6 h ({100 * (B.rmse_6h_cm / A.rmse_6h_cm - 1):+.1f}%), {A.rmse_3h_cm:.2f} to {B.rmse_3h_cm:.2f} cm at 3 h. In the test years the same comparison gives 8.42 to 8.03 cm. "
            "The gain is again at the stations with tide.",
            "",
            "Data hygiene, checked item by item:",
            "-  The period is outside everything used before: training 2010-2022, validation 2023, test 2024-2025; partners and tide classes come from the training period only.",
            "-  Both models read the same saved water levels and discharge: no difference in any of 10,100 station rows.",
            "-  No input later than the forecast time: newest reading 55 min after the hour at most (used up to 29 min); wind and rainfall forecasts from HRRR cycles issued at or before the forecast time.",
            "-  The forecast script fills an old gap differently from the training arrays (it cannot reach back further than 24 h). Measured on the test years: no change (8.03 and 8.03 cm).",
            "-  Run afterwards, the services return complete data. In real time part of the USGS readings of the newest hour have not arrived: with that hour removed at every USGS gauge the gain remains "
            f"({AL.rmse_6h_cm:.2f} to {BL.rmse_6h_cm:.2f} cm).",
            "",
            "What it is not: independent evidence of accuracy. Two and a half days, one rain event at Houston (15 November 18 UTC, creeks rose by more than 1 m in 6 h; neither model forecast it). "
            "It shows that the whole chain works on live data and that the direction agrees with the test years."
            + (f" With a forecast from every hour instead of every 6 h (next slides): {hr.loc[6, 'run']:.2f} to {hr.loc[6, 'partners']:.2f} cm at 6 h." if hr is not None else ""),
        ], size=11.5)
        for n_, cap in enumerate(["Mississippi River at Baton Rouge: the two models are alike. Lake Charles: the 6 h line follows the tide more closely with partner stations (the tide gauge at Calcasieu Pass, 52 km seaward).",
                                  "Vermilion Bay and Sims Bayou: without partner stations the 6 h forecast overshoots on 16 November; with them it stays closer to the observation.",
                                  "Atchafalaya River at Butte La Rose: a rise forecast on 16 November that did not happen is largely gone with partner stations. Spring Creek: the rise is forecast with both.",
                                  "Buffalo Bayou at Piney Point: the rise of more than 1 m in 6 h is late in both models - the rainfall forecast, not the partner stations. Comite River: both forecast a rise that did not come."], 1):
            f_ = T / f"stations_wide_{n_}.png"
            if not f_.exists():
                continue
            sl = new(f"The same test, a forecast from every hour: stations ({n_} of 4)")
            yb = picture(sl, f_, 0.3, 0.9, 12.7, 5.85)
            text(sl, 0.5, yb + 0.05, 12.3, 0.7, [cap + "  Left: the version that is run. Right: with partner stations. Each line joins the forecasts issued 1, 3 or 6 h before the hour they are valid for."], size=11)

    # ---- 7 summary
    sl = new("After the group meeting: what was added, and what is open")
    text(sl, 0.5, 1.0, 12.3, 6.2, [
        "The model is still the same LSTM. Everything that helped added information; nothing that changed the model itself helped.",
        "",
        f"1.  Five models with different random seeds, averaged: 8.66 to {run['h6']:.2f} cm at 6 h. This is the version that is run. A starting state of its own for every station in the LSTM: no change.",
        "2.  A way to compare versions that is not fooled by the seed: five seeds each, the largest changes, the hurricanes, the lag.",
        f"3.  Where the remaining error is: with observed instead of HRRR rainfall for the next 6 h the same model reaches {sp[3]['h6']:.2f} instead of {sp[0]['h6']:.2f} cm, and the lag falls from {sp[0]['lag']:.1f} to {sp[3]['lag']:.1f} h. "
        "The rainfall forecast is the largest lever, in the hurricanes mainly hours 3-6.",
        f"4.  Partner stations: {run['h6']:.2f} to {b['h6']:.2f} cm at 6 h, about 10% at stations with tide; trained so that late partner data do not hurt for one to two hours.",
        "5.  Two tables that are useful beyond this model: every station classed by its measured tide (config/station_behaviour.csv), and the stations upstream and downstream of every USGS station on the river network, "
        "with the lakes and reservoirs between them (config/station_river_network.csv, config/station_reservoirs_between.csv).",
        "",
        "Not adopted: partners chosen by distance; a reservoir as a cut in the river network; HRRR rainfall as two totals; ConvLSTM (stations are not a grid, and the literature shows no gain over a multi-station LSTM "
        "for station forecasts at these lead times).",
        "",
        "Open:",
        "-  Partner-station input is in the forecast script and was tested on past forecast times, not yet in real time. It has not replaced the version that is run, which is started by hand and not connected to the group's website.",
        "-  A partner without data for more than 3 h.",
        "-  The hurricane numbers rest on two storms.",
        "-  The rainfall forecast: a radar-based nowcast for hours 1-2, several HRRR cycles for hours 3-6.",
    ], size=12)

    # put the new slides before "Where things stand"
    def title_of(el):
        s_ = prs.part.related_part(el.rId).slide
        t_ = [sh.text_frame.text for sh in s_.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
        return t_[0] if t_ else ""
    anchor = next((el for el in ids if el not in new_els and title_of(el).startswith("Where things stand")), None)
    for el in new_els:
        ids.remove(el)
    at = list(ids).index(anchor) if anchor is not None else len(ids)
    for k, el in enumerate(new_els):
        ids.insert(at + k, el)
    prs.part.rename_slide_parts([el.rId for el in ids])      # python-pptx numbers the slide files only when the deck is opened: after replacing slides two would share a name
    try:
        prs.save(str(dst)); out = dst
    except PermissionError:
        out = F / f"version_comparison_{datetime.date.today():%Y%m%d}.pptx"; prs.save(str(out))
    print(f"-> {out}: {n_before} slides kept, {len(new_els)} added at position {at + 1}" + ("  (the round by measured tide is not in yet)" if pending else ""))


if __name__ == "__main__":
    main()
