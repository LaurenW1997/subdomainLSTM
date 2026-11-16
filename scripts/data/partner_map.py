"""Partner stations: for every station, the other stations whose recent water level says most about its next 6 hours.

For a station A and a candidate B (a station with real-time data within --max-km), over the hours of the TRAINING period:
  own      linear fit of A's change over the next 6 h on A's own recent changes (last 1, 3, 6 h, and the 6 h changes half a day
           and a day earlier at the same phase, a stand-in for the tide the model reads from its 72 h of input)
  with B   the same fit with B's changes over the last 1, 3, 6 h added
  gain     share of the variance left by "own" that B explains
Partners are picked one after another (the next one is the candidate that adds most to the ones already picked), up to --k,
as long as the gain of the pick is at least --min-gain. CRMS stations are not used as partners (no real-time data) but get
partners themselves (they are in the training).
--max-km-river: a candidate that is a river or creek (any type other than tide gauge, estuary / tidal channel, lake, marsh)
is used only within this distance. Far-away creeks are related to a station only through the weather passing over both,
and that timing does not carry over to other years (deliverables/27_partner_stations.md).
--network FILE (config/station_river_network.csv from river_network.py): a candidate that is a river or creek is used only
when it lies downstream or upstream of the station along the river network, or within --near-km of it (default 0 = never);
--max-km-river then no longer applies to the river and creek stations of that table. Tide gauges, estuaries, lakes, marsh
and stations that are not in the table keep the distance rule.
--min-gain-unlinked: at those river and creek stations a partner that is not on the same network (a tide gauge, estuary or
lake station) must explain at least this share instead of --min-gain. Without the far creeks many inland stations would
otherwise fill their four places with distant tidal stations that explain 1-3 %; in the round with the 50 km rule such
partners brought nothing in the test years.
Output: config/station_partners.csv   source, station_id, name, type, n_partners, own_r2, r2_with_partners,
                                      p<j>_source, p<j>_station_id, p<j>_name, p<j>_type, p<j>_km, p<j>_gain   (j = 1 .. k)
Usage : python partner_map.py --dataset DATA/dataset_v6 [--out FILE --k 4 --max-km 150 --max-km-river 50 --min-gain 0.01 --workers 32]
"""
from __future__ import annotations

import argparse
import json
import re
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
H = 6
G = {}
TIDAL = {"tide gauge", "estuary / tidal channel", "lake", "marsh"}


def km(lat, lon, la, lo):
    p = np.pi / 180
    a = np.sin((la - lat) * p / 2) ** 2 + np.cos(lat * p) * np.cos(la * p) * np.sin((lo - lon) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


def r2(X, y):
    X = np.column_stack([X, np.ones(len(y))])
    w = np.linalg.lstsq(X, y, rcond=None)[0]
    return 1 - ((y - X @ w) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-12)


def feats(j, t):            # changes of station j over the last 1, 3, 6 h before the hours t
    x = G["x"]
    return np.stack([x[j, t] - x[j, t - L] for L in (1, 3, 6)], 1)


def one(s):
    x, t, a = G["x"], G["t"], G["a"]
    y = x[s, t + H] - x[s, t]
    own = np.column_stack([feats(s, t), x[s, t - 6] - x[s, t - 12], x[s, t - 19] - x[s, t - 25]])
    ok = np.isfinite(y) & np.isfinite(own).all(1)
    d = km(G["lat"][s], G["lon"][s], G["lat"][G["cand"]], G["lon"][G["cand"]])
    lim = np.where(G["tidal"][G["cand"]], a.max_km, min(a.max_km, a.max_km_river))
    keep = d <= lim
    if G["link"] is not None and G["in_net"][s]:      # rivers and creeks: only along the network (or very near)
        keep = np.where(G["tidal"][G["cand"]], keep, (d <= a.max_km) & (G["link"][s][G["cand"]] | (d <= a.near_km)))
    cand = [int(j) for j in G["cand"][keep] if j != s]
    dist = {int(j): float(dd) for j, dd in zip(G["cand"], d)}
    F = {j: feats(j, t) for j in cand}
    V = {j: np.isfinite(F[j]).all(1) for j in cand}
    picked, gains, base, r_own, r_full = [], [], own, np.nan, np.nan
    if ok.sum() >= a.min_n:
        r_own = r_full = r2(own[ok], y[ok])
    for _ in range(a.k):
        best = (0.0, None)
        for j in cand:
            if j in picked:
                continue
            need = a.min_gain_unlinked if (G["link"] is not None and G["in_net"][s] and not G["link"][s][j]) else a.min_gain
            m = ok & V[j]
            if m.sum() < a.min_n:
                continue
            r0 = r2(base[m], y[m]); r1 = r2(np.column_stack([base[m], F[j][m]]), y[m])
            g = (r1 - r0) / max(1 - r0, 1e-9)
            if g > best[0] and g >= need:
                best = (g, j, r1)
        if best[1] is None:
            break
        picked.append(best[1]); gains.append(best[0]); r_full = best[2]
        ok = ok & V[best[1]]; base = np.column_stack([base, F[best[1]]])
    return s, picked, gains, [dist[j] for j in picked], r_own, r_full


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True); ap.add_argument("--out", default=str(REPO / "config" / "station_partners.csv"))
    ap.add_argument("--k", type=int, default=4); ap.add_argument("--max-km", type=float, default=150.0); ap.add_argument("--max-km-river", type=float, default=1e9); ap.add_argument("--min-gain", type=float, default=0.01)
    ap.add_argument("--network"); ap.add_argument("--near-km", type=float, default=0.0); ap.add_argument("--min-gain-unlinked", type=float, default=0.03)
    ap.add_argument("--min-n", type=int, default=2000); ap.add_argument("--stride", type=int, default=5); ap.add_argument("--workers", type=int, default=32)
    a = ap.parse_args()
    d = Path(a.dataset)
    st = pd.read_csv(d / "stations.csv", index_col="row", dtype={"station_id": str}).reset_index(drop=True)
    meta = json.loads((d / "meta.json").read_text())
    time = pd.to_datetime(np.load(d / "time.npy"))
    t_end = int(np.searchsorted(time.values, np.datetime64(meta["train_end"])))
    v = np.load(d / "values.npy", mmap_mode="r")[:, :t_end]
    x = ((np.asarray(v) - st.mean_m.to_numpy(np.float32)[:, None]) / st.std_m.to_numpy(np.float32)[:, None]).astype(np.float32)
    g = pd.read_csv(REPO / "config" / "station_groups.csv", dtype={"station_id": str})
    typ = st[["source", "station_id"]].astype(str).merge(g[["source", "station_id", "type"]], on=["source", "station_id"], how="left").type.fillna("other").to_numpy()
    G.update(x=x, t=np.arange(25, t_end - H, a.stride), a=a, lat=st.lat.to_numpy(float), lon=st.lon.to_numpy(float), cand=np.where((st.source != "CRMS").to_numpy())[0], tidal=np.isin(typ, list(TIDAL)))
    G.update(link=None, in_net=None)
    if a.network:
        net = pd.read_csv(a.network, dtype=str).fillna("")
        row = {(x, y): k for k, (x, y) in enumerate(zip(st.source.astype(str), st.station_id.astype(str)))}
        link = np.zeros((len(st), len(st)), bool); in_net = np.zeros(len(st), bool)
        for r in net.itertuples():
            k = row.get((r.source, r.station_id))
            if k is None:
                continue
            in_net[k] = typ[k] not in TIDAL          # the rule is for river and creek stations; the others keep the distance rule
            for j in re.findall(r"(\S+) \(", r.down + " | " + r.up):
                if (r.source, j) in row:
                    link[k, row[(r.source, j)]] = link[row[(r.source, j)], k] = True
        G.update(link=link, in_net=in_net)
    with Pool(a.workers) as pool:                       # fork: the workers share x
        res = pool.map(one, range(len(st)), chunksize=4)
    rows = []
    for s, picked, gains, dist, r_own, r_full in res:
        r = {"source": st.source[s], "station_id": st.station_id[s], "name": st.name[s], "type": typ[s], "n_partners": len(picked),
             "own_r2": round(float(r_own), 4), "r2_with_partners": round(float(r_full), 4)}
        for j in range(a.k):
            has = j < len(picked); p = picked[j] if has else None
            r.update({f"p{j + 1}_source": st.source[p] if has else "", f"p{j + 1}_station_id": st.station_id[p] if has else "", f"p{j + 1}_name": st.name[p] if has else "",
                      f"p{j + 1}_type": typ[p] if has else "", f"p{j + 1}_km": round(dist[j], 1) if has else "", f"p{j + 1}_gain": round(float(gains[j]), 4) if has else ""})
        rows.append(r)
    m = pd.DataFrame(rows); m.to_csv(a.out, index=False)
    rt = m[m.source != "CRMS"]
    print(f"{len(m)} stations; with real-time data {len(rt)}: partners 0 / 1 / 2 / 3 / 4 at {[int((rt.n_partners == i).sum()) for i in range(a.k + 1)]} stations")
    print("type                      n   with a partner | median share of the remaining variance explained by all partners | first partner: median km, other type")
    for t, x_ in rt.groupby("type"):
        w = x_[x_.n_partners > 0]
        gain = ((w.r2_with_partners - w.own_r2) / (1 - w.own_r2)).median() if len(w) else np.nan
        print(f"  {t:24s} {len(x_):4d}   {len(w):4d}           | {gain:.3f}                                                              | "
              f"{pd.to_numeric(w.p1_km).median():.0f} km, {float((w.p1_type != w.type).mean()) if len(w) else np.nan:.2f}")
    print("->", a.out)


if __name__ == "__main__":
    main()
