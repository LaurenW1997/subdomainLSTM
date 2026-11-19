"""Flood map, step 6: the whole chain against observations - forecasts of the water-level model at the control points,
through the mapping model, compared with what was observed at the valid time, for a storm neither model has seen.

For every valid hour v and every lead h the inputs of the mapping model are
    lead 0      the observations of the control points at v (the mapping model alone)
    lead 1..6   the forecasts issued at v - h for v
moved to the level of the numerical model with the offset of each station from the calm days of the hindcast (observed_inputs.py).
A control point without a forecast at an issue time is filled with its expectation given the others.
Compared with the observations at v:
    control point, left out       its level from the inputs of the other control points (as observed_inputs.py)
    check station                 passes the control-point check, never an input: the full mapping model at its cell
    other gauge                   has a cell that is always water but the hindcast does not follow its observations there
For reference the direct forecast of the water-level model at the same station and lead is scored too (what one has where a gauge exists).
Input : --fc NPZ of forecast_inputs.py, --fit DIR of mapping_fit.py (--sums-dir if the sums are elsewhere), --offsets stations.csv of observed_inputs.py,
        --cells CSV of control_cells.py, --ida DIR, --cache hindcast float32, --dataset DIR, --table config/operational_stations_grid_datum.csv
Output: --out DIR: stations.csv (one row per station and lead), summary.csv (per group and lead), series.npz, summary.txt,
        inputs.npz (the inputs of the mapping model per lead, [valid hours, control points])
Usage : python forecast_map_check.py --fc FILE --fit DIR --offsets FILE --cells FILE --ida DIR --cache FILE --dataset DIR --table FILE --out DIR
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import grid, training  # noqa: E402
from observed_inputs import cell_wse, conditional  # noqa: E402

LEADS = [0, 1, 2, 3, 4, 5, 6]


def rmse(e) -> float:
    e = e[np.isfinite(e)]
    return float(np.sqrt((e ** 2).mean())) if len(e) >= 12 else np.nan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fc", required=True); ap.add_argument("--fit", required=True); ap.add_argument("--sums-dir"); ap.add_argument("--offsets", required=True); ap.add_argument("--cells", required=True)
    ap.add_argument("--ida", required=True); ap.add_argument("--cache", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--table", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--train-runs", nargs="+"); ap.add_argument("--holdout", default="Exp1_fully_coupled"); ap.add_argument("--noise", type=float, default=0.12); ap.add_argument("--calm-hours", type=int, default=72)
    ap.add_argument("--storm", nargs=2, default=["2024-09-10 00:00", "2024-09-14 00:00"], help="the days around the landfall, scored apart")
    a = ap.parse_args()
    ida, fit, out = Path(a.ida), Path(a.fit), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    assert not (out / "stations.csv").exists(), f"{out} has results already"
    sd = Path(a.sums_dir) if a.sums_dir else fit
    h, roms, lat, lon = grid(ida); NX = h.shape[1]

    z = np.load(a.fc); F, O = z["forecast"].astype(np.float64), z["observed"].astype(np.float64); valid = pd.DatetimeIndex(z["valid"]); T = F.shape[0]; H = F.shape[1]
    col = {(s, i): k for k, (s, i) in enumerate(zip(z["source"], z["station_id"]))}
    V = np.arange(H, T)                                                    # valid hours that every lead reaches
    tv = valid[V]; storm = np.asarray((tv >= a.storm[0]) & (tv < a.storm[1]))
    tab = pd.read_csv(a.table, dtype=str, keep_default_na=False); tab = tab[tab.domain == "Louisiana100m_full"]
    add = {(r.source, r.station_id): float(r.to_navd88_add_m) for r in tab.itertuples() if r.to_navd88_add_m != ""}

    def level(key, lead):
        """Level of one station at the valid hours V as known `lead` hours before (lead 0: observed), in NAVD88 where the datum is known."""
        k = col[key]
        return (O[V, k] if lead == 0 else F[V - lead, lead - 1, k]) + add.get(key, 0.0)

    c = pd.read_csv(fit / "controls_used.csv", dtype={"station_id": str}); P = len(c); used = c.used.to_numpy(bool); xref = np.load(sd / "xref.npy")
    of = pd.read_csv(a.offsets, dtype={"station_id": str}); off_of = {(r.source, r.station_id): float(r.offset_m) for r in of.itertuples()}
    keys = [(r.source, r.station_id) for r in c.itertuples()]; off = np.array([off_of.get(k, np.nan) for k in keys]); assert np.isfinite(off[used]).all()

    train, name = training(a); n = 0; Sx = np.zeros(P); Sxx = np.zeros((P, P))
    for r in train:
        s_ = np.load(sd / f"sums_{r}.npz"); n += int(s_["n"]); Sx += s_["Sx"]; Sxx += s_["Sxx"]
    xm = Sx / n; C = Sxx - n * np.outer(xm, xm); lam = n * a.noise ** 2

    # inputs per lead, on the level of the numerical model, minus the reference level of the sums
    X = {}; Xf = {}; filled = {}
    for L in LEADS:
        x = np.stack([level(k, L) for k in keys], 1) + off[None, :] - xref[None, :]; x[:, ~used] = np.nan; X[L] = x
        xf = x.copy(); xf[:, ~used] = xm[None, ~used]; miss = ~np.isfinite(xf); filled[L] = int(miss[:, used].sum())
        for s in np.where(miss.any(0))[0]:
            use = used.copy(); use[s] = False
            xf[miss[:, s], s] = conditional(C, xm, lam, x[miss[:, s]], use, C[:, [s]], xm[[s]])[:, 0]
        assert np.isfinite(xf).all(), f"lead {L}: an hour with fewer than five control points"; Xf[L] = xf
    np.savez(out / "inputs.npz", times=np.array(tv.strftime("%Y-%m-%d %H:%M"), dtype=str), storm=storm, **{f"lead{L}": Xf[L] for L in LEADS})      # for forecast_map_fields.py

    recs = []; ser = {"times": np.array(tv.strftime("%Y-%m-%d %H:%M"), dtype=str)}

    def score(group, r, key, o_obs, pred, offset):
        """o_obs: observed at V (station datum + NAVD88 shift); pred[L]: mapping on the model level; offset: model minus observed."""
        sid = key[1]; ser[f"obs_{sid}"] = o_obs.astype(np.float32)
        for L in LEADS:
            p = pred[L] - offset; e = p - o_obs; ser[f"map{L}_{sid}"] = p.astype(np.float32)
            rec = {"group": group, "source": key[0], "station_id": sid, "name": r["name"], "lat": r.lat, "lon": r.lon, "cell_model": r.best_model, "lead_h": L, "hours": int(np.isfinite(e).sum()),
                   "rmse_mapping_m": rmse(e), "bias_mapping_m": float(np.nanmean(e)) if np.isfinite(e).any() else np.nan, "rmse_mapping_bias_removed_m": rmse(e - np.nanmean(e)) if np.isfinite(e).any() else np.nan,
                   "rmse_mapping_storm_m": rmse(e[storm]), "peak_observed_m": float(np.nanmax(o_obs)) if np.isfinite(o_obs).any() else np.nan, "peak_mapping_m": float(np.nanmax(np.where(np.isfinite(o_obs), p, np.nan))) if np.isfinite(o_obs).any() else np.nan}
            if L > 0:                                                     # the direct forecast of the water-level model at this station
                d = level(key, L) - o_obs; ser[f"fc{L}_{sid}"] = (level(key, L)).astype(np.float32)
                rec.update({"rmse_direct_forecast_m": rmse(d), "rmse_direct_forecast_storm_m": rmse(d[storm])})
            recs.append(rec)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for s in np.where(used)[0]:                                       # control points, each left out in turn
            use = used.copy(); use[s] = False
            pred = {L: conditional(C, xm, lam, X[L], use, C[:, [s]], xm[[s]])[:, 0] + xref[s] for L in LEADS}
            score("control point, left out", c.iloc[s], keys[s], level(keys[s], 0), pred, off[s])

        al = pd.read_csv(a.cells, dtype={"station_id": str}); al = al[(al.obs_hours >= 200) & (al.best_j >= 0) & ~al.station_id.isin(c.station_id)].reset_index(drop=True)
        amp = (al.best_std_ratio >= 0.5) & (al.best_std_ratio <= 2.0)
        al["group"] = np.where((al.best_r >= 0.8) & amp, "check station, never an input", "other gauge, the hindcast does not follow its observations")
        # offsets of these stations from the calm days of the hindcast, as observed_inputs.py
        d = netCDF4.Dataset(ida / f"water_level_{a.holdout}.nc"); ti = pd.DatetimeIndex(netCDF4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)); d.close()
        wl = np.load(a.cache, mmap_mode="r"); TI = wl.shape[0]
        st = pd.read_csv(Path(a.dataset) / "stations.csv", dtype={"station_id": str}); tm = pd.DatetimeIndex(np.load(Path(a.dataset) / "time.npy"))
        vals = np.load(Path(a.dataset) / "values.npy", mmap_mode="r"); row = {(s, i): k for k, (s, i) in enumerate(zip(st.source, st.station_id))}; i0 = int(tm.get_indexer([ti[0]])[0])
        B = np.load(fit / f"coef_{name}.npy", mmap_mode="r"); ym = np.load(fit / f"fitmeta_{name}.npz")["ym"]
        for r in al.itertuples():
            key = (r.source, r.station_id); j, i = int(r.best_j), int(r.best_i)
            if key not in col:
                continue
            ob = np.asarray(vals[row[key], i0:i0 + TI], np.float64) + add.get(key, 0.0); dif = cell_wse(wl, j, i, h, roms) - ob
            o_ = off_of.get(key, np.nan)
            if not np.isfinite(o_):
                o_ = np.nanmedian(dif[:a.calm_hours]) if np.isfinite(dif[:a.calm_hours]).sum() >= 24 else np.nanmedian(dif)
            if not np.isfinite(o_):
                continue
            idx = j * NX + i; b = np.asarray(B[:, idx], np.float64); pred = {}
            for L in LEADS:
                y = (Xf[L] - xm[None, :]) @ b + float(ym[idx]); pred[L] = y if roms[j, i] else np.maximum(y, 0) - float(h[j, i])
            score(r.group, pd.Series(r._asdict()), key, level(key, 0), pred, o_)

    t = pd.DataFrame(recs); t.to_csv(out / "stations.csv", index=False); np.savez_compressed(out / "series.npz", **ser)
    rows = []
    for (g, L), x in t.groupby(["group", "lead_h"], sort=False):
        x = x.dropna(subset=["rmse_mapping_m"]); w = x.hours.to_numpy(float)
        pool = lambda cc: float(np.sqrt(np.nansum(w * x[cc].to_numpy() ** 2) / w[np.isfinite(x[cc].to_numpy())].sum())) if cc in x and np.isfinite(x[cc].to_numpy()).any() else np.nan
        rows.append({"group": g, "lead_h": L, "stations": len(x), "rmse_mapping_median_m": x.rmse_mapping_m.median(), "rmse_mapping_pooled_m": pool("rmse_mapping_m"),
                     "rmse_mapping_storm_median_m": x.rmse_mapping_storm_m.median(), "rmse_mapping_bias_removed_median_m": x.rmse_mapping_bias_removed_m.median(), "bias_mapping_median_m": x.bias_mapping_m.median(),
                     "peak_error_mean_m": (x.peak_mapping_m - x.peak_observed_m).mean(), "peak_error_rms_m": float(np.sqrt(((x.peak_mapping_m - x.peak_observed_m) ** 2).mean())),
                     "rmse_direct_forecast_median_m": x.rmse_direct_forecast_m.median() if L > 0 else np.nan, "rmse_direct_forecast_storm_median_m": x.rmse_direct_forecast_storm_m.median() if L > 0 else np.nan})
    sm_ = pd.DataFrame(rows); sm_.to_csv(out / "summary.csv", index=False)
    lines = [f"{int(used.sum())} control points; valid hours {tv[0]} .. {tv[-1]} ({len(V)}), days around the landfall {a.storm[0]} .. {a.storm[1]} ({int(storm.sum())} hours); mapping model fitted on {len(train)} runs",
             "control-point hours without a forecast, filled from the others: " + ", ".join(f"lead {L}: {filled[L]}" for L in LEADS) + f" of {len(V) * int(used.sum())}"]
    pd.set_option("display.width", 250); lines.append(sm_.round(3).to_string(index=False))
    (out / "summary.txt").write_text(chr(10).join(lines), encoding="utf-8"); print(chr(10).join(lines)); print("->", out)


if __name__ == "__main__":
    main()
