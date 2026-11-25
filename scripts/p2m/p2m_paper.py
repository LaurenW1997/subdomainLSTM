"""Flood map: the mapping model of Bao et al. (2025, npj Natural Hazards), implemented as the paper describes it.

For every cell of the prediction area an own model, input = water level at control points, output = water depth of the cell,
fitted on the output of the numerical model:
  Type 1   the cell is flooded in every training hour               Model-1  linear regression on the whole series
  Type 2   dry in normal conditions, flooded at times               the best of three, by five-fold cross-validation (CV):
             Model-2  linear regression on the flooded hours only
             Model-3  hurdle: logistic regression says flooded or not; if flooded, Model-2 gives the depth
             Model-4  Tobit (regression for data cut off at zero)
           A fold counts if it holds flooded and dry hours. With two or more such folds the model with the lowest mean RMSE over
           them is taken. With fewer, the cell is a low-flood-risk location and gets no model (as in the paper).
  prediction area: the region the control points surround (--area).
What had to be decided for Louisiana (the paper has 8 control points, 432 km2 and 1,440 training hours):
  - every cell uses its --k nearest control points (default 8), so that the regressions stay determined with 30 control points;
  - 'flooded' means deeper than --wet m (default 0.05): the land model keeps films of rain water on most cells, which would
    otherwise make nearly every cell 'flooded at times'. Depths up to --wet count as 0;
  - the folds are consecutive fifths of every run (no shuffling), as a flood is a block of consecutive hours;
  - the regressions carry a very small ridge term for numerical stability only; the logistic regression has the usual L2 term (C = 1);
  - --noise (default 0 = as the paper): with a value above 0 the regressions take the inputs to carry an error of that size. The
    paper feeds the mapping with forecasts at 8 control points; here the 8 nearest of 30 often rise and fall together, and
    without this term they get large weights of opposite sign that turn a small mismatch of the inputs into metres.
Commands:
  fit      --train-runs RUN ...   ->  --out DIR/model.npz, fit_summary.txt
  apply    --model FILE --inputs NPY/NPZ[:key] [T, control points] [--truth-run RUN] [--hours-mask ...]  ->  peak field, metrics, series at --cells
Input : --ida DIR, --sums DIR (sums_<run>.npz with the control-point series X, xref.npy, controls_used.csv), --area NPZ (area [lat, lon])
Usage : python p2m_paper.py fit --ida DIR --sums DIR --area FILE --train-runs Exp1_fully_coupled --out DIR
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_fit import Reader, grid  # noqa: E402

KX, KY = np.cos(np.deg2rad(29.7)) * 111.2, 111.2
MODELS = {1: "Model-1 linear, whole series", 2: "Model-2 linear, flooded hours", 3: "Model-3 hurdle", 4: "Model-4 Tobit"}
THR = (0.1, 0.3, 0.5, 1.0, 2.0)


def load_depth(ida: Path, run: str, h, roms, jj, ii) -> np.ndarray:
    """Depth of the chosen cells for every hour of a run [T, N], gaps of the archive filled as mapping_fit.Reader does."""
    rd = Reader(ida, run, h, roms); add = np.where(roms[jj, ii], h[jj, ii], 0).astype(np.float32); out = np.empty((rd.T, len(jj)), np.float32)
    for k0 in range(0, rd.T, 24):
        y = rd.block(k0, min(k0 + 24, rd.T)); out[k0:k0 + y.shape[0]] = np.maximum(y[:, jj, ii] + add[None, :], 0)
    return out


def controls(sums: Path):
    c = pd.read_csv(sums / "controls_used.csv", dtype={"station_id": str}); used = c.used.to_numpy(bool) if "used" in c.columns else np.ones(len(c), bool)
    return c, used


def lin_wet(Xd, Yt, W, ridge, noise=0.0):
    """Least squares on the flooded hours of every cell: Xd [T, q], Yt [T, n], W [T, n] -> [n, q]. noise: assumed error of the inputs (m)."""
    T, q = Xd.shape; Z = (Xd[:, :, None] * Xd[:, None, :]).reshape(T, q * q); Wf = W.to(Xd.dtype)
    A = (Wf.T @ Z).reshape(-1, q, q).double(); cnt = Wf.sum(0).double()
    D = torch.eye(q, dtype=torch.float64); D[0, 0] = 0.0
    A = A + (ridge * (cnt + 1.0))[:, None, None] * torch.eye(q, dtype=torch.float64)[None] + (noise ** 2 * cnt)[:, None, None] * D[None]
    b = ((Yt * Wf).T @ Xd).double()
    return torch.linalg.solve(A, b[..., None])[..., 0].to(Xd.dtype)


def logit(Xs, W, C=1.0, iters=12):
    """Logistic regression per cell with an L2 term (not on the constant): Xs [T, q] standardised with a column of ones, W [T, n] -> [n, q]."""
    T, q = Xs.shape; n = W.shape[1]; Z = (Xs[:, :, None] * Xs[:, None, :]).reshape(T, q * q); y = W.to(Xs.dtype); g = torch.zeros(n, q, dtype=torch.float64)
    pen = torch.ones(q, dtype=torch.float64) / C; pen[0] = 1e-6
    for _ in range(iters):
        p = torch.sigmoid((Xs @ g.to(Xs.dtype).T).clamp(-30, 30)); grad = ((y - p).T @ Xs).double() - g * pen[None, :]
        H = ((p * (1 - p)).T @ Z).reshape(n, q, q).double() + torch.diag(pen)[None]
        g = g + torch.linalg.solve(H, grad[..., None])[..., 0].clamp(-5, 5)
    return g.to(Xs.dtype)


def proj(Xd, noise=0.0):
    """The matrix that turns a series into regression coefficients; with noise > 0 the inputs are taken to carry an error of that size (ridge)."""
    X = Xd.double(); q = X.shape[1]; D = torch.eye(q, dtype=torch.float64); D[0, 0] = 0.0
    return (torch.linalg.solve(X.T @ X + len(X) * noise ** 2 * D + 1e-9 * torch.eye(q, dtype=torch.float64), X.T)).to(Xd.dtype)


def tobit(Xd, Y, W, cut, iters=40, noise=0.0):
    """Tobit by EM: the hours not flooded are known only to lie at or below `cut`. Xd [T, q], Y [T, n], W [T, n] -> coefficients [n, q]."""
    P = proj(Xd, noise); Yc = torch.where(W, Y, torch.full_like(Y, cut)); b = (P @ Yc).T; mu = Xd @ b.T
    s = ((Yc - mu) ** 2).mean(0).sqrt().clamp_min(0.02); nd = torch.distributions.Normal(0.0, 1.0)
    for _ in range(iters):
        mu = Xd @ b.T; al = ((cut - mu) / s[None, :]).clamp(-8, 8); lam = torch.exp(nd.log_prob(al) - torch.special.log_ndtr(al))       # pdf / cdf
        e = mu - s[None, :] * lam; var = (s[None, :] ** 2) * (1 - al * lam - lam ** 2).clamp_min(0)
        Ycomp = torch.where(W, Y, e); b = (P @ Ycomp).T; mu2 = Xd @ b.T
        s = (torch.where(W, (Y - mu2) ** 2, var + (e - mu2) ** 2)).mean(0).sqrt().clamp_min(0.02)
    return b


def predict(model: dict, Xin: np.ndarray, sel: np.ndarray) -> np.ndarray:
    """Depth [T, len(sel)] of the cells `sel` (indices into the cells of the model) for the control-point series Xin [T, P]; NaN where the cell has no model."""
    cols = model["cols"][sel]; mdl = model["model"][sel]; out = np.full((Xin.shape[0], len(sel)), np.nan, np.float32)
    Xs_all = (Xin - model["xmean"][None, :]) / model["xstd"][None, :]
    key = np.ascontiguousarray(cols).view([("", cols.dtype)] * cols.shape[1]).ravel(); _, inv = np.unique(key, return_inverse=True)
    for gk in np.unique(inv):
        m = np.where((inv == gk) & (mdl > 0))[0]
        if len(m) == 0:
            continue
        c = cols[m[0]]; Xd = np.concatenate([np.ones((len(Xin), 1)), Xin[:, c]], 1).astype(np.float32); Xs = np.concatenate([np.ones((len(Xin), 1)), Xs_all[:, c]], 1).astype(np.float32)
        lin = np.maximum(Xd @ model["coef_linear"][sel[m]].T, 0); tb = np.maximum(Xd @ model["coef_tobit"][sel[m]].T, 0); fl = (Xs @ model["coef_logit"][sel[m]].T) > 0
        k = mdl[m]; out[:, m] = np.where(k[None, :] == 4, tb, np.where(k[None, :] == 3, np.where(fl, lin, 0), lin))
    return out


def cmd_fit(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); assert not (out / "model.npz").exists(), f"{out} has a model already"
    t00 = time.time(); ida, sums = Path(a.ida), Path(a.sums); h, roms, lat, lon = grid(ida); NY, NX = h.shape
    area = np.load(a.area)["area"]; jj, ii = np.where(area); N = len(jj); c, used = controls(sums); P = int(used.sum())
    Xr = [np.load(sums / f"sums_{r}.npz")["X"][:, used] for r in a.train_runs]                                  # --hours DIR: hours_<run>.npy says which hours of a run are used (all, if there is no such file)
    keep = [np.load(Path(a.hours) / f"hours_{r}.npy").astype(bool) if a.hours and (Path(a.hours) / f"hours_{r}.npy").exists() else np.ones(len(x), bool) for r, x in zip(a.train_runs, Xr)]
    assert all(len(k) == len(x) and k.sum() >= a.folds for k, x in zip(keep, Xr)), "an hours file does not fit its run or leaves fewer hours than folds"
    X = np.concatenate([x[k] for x, k in zip(Xr, keep)]).astype(np.float64)
    Y = np.concatenate([load_depth(ida, r, h, roms, jj, ii)[k] for r, k in zip(a.train_runs, keep)]); T = len(X); assert Y.shape[0] == T
    fold = np.concatenate([np.minimum(np.arange(n) * a.folds // n, a.folds - 1) for n in [int(k.sum()) for k in keep]])
    print(f"{N} cells in the prediction area, {P} control points, {T} training hours of {len(a.train_runs)} run(s); loaded in {time.time() - t00:.0f} s", flush=True)
    clat, clon = c.lat.to_numpy(float)[used], c.lon.to_numpy(float)[used]; cols = np.zeros((N, a.k), np.int16)
    for s0 in range(0, N, 500000):                                         # the k nearest control points of every cell
        d2 = ((lon[ii[s0:s0 + 500000]][:, None] - clon[None, :]) * KX) ** 2 + ((lat[jj[s0:s0 + 500000]][:, None] - clat[None, :]) * KY) ** 2
        cols[s0:s0 + 500000] = np.sort(np.argsort(d2, 1)[:, :a.k], 1)
    xmean, xstd = X.mean(0), X.std(0); q = a.k + 1
    typ = np.zeros(N, np.int8); mdl = np.zeros(N, np.int8); cv = np.full((N, 3), np.nan, np.float32); nval = np.zeros(N, np.int8)
    B1 = np.zeros((N, q), np.float32); BL = np.zeros((N, q), np.float32); BT = np.zeros((N, q), np.float32)
    key = np.ascontiguousarray(cols).view([("", cols.dtype)] * a.k).ravel(); _, inv = np.unique(key, return_inverse=True); ng = int(inv.max()) + 1; order = np.argsort(inv, kind="stable"); bounds = np.searchsorted(inv[order], np.arange(ng + 1))
    print(f"{ng} groups of cells with the same {a.k} control points", flush=True); torch.set_num_threads(a.threads); ft = torch.from_numpy(fold)
    for gk in range(ng):
        cells = order[bounds[gk]:bounds[gk + 1]]; cc = cols[cells[0]]
        Xd = torch.from_numpy(np.concatenate([np.ones((T, 1)), X[:, cc]], 1).astype(np.float32)); Xs = torch.from_numpy(np.concatenate([np.ones((T, 1)), (X[:, cc] - xmean[cc]) / xstd[cc]], 1).astype(np.float32))
        Pinv = proj(Xd, a.noise)
        for s0 in range(0, len(cells), a.chunk):
            cs = cells[s0:s0 + a.chunk]; Yg = torch.from_numpy(Y[:, cs]); W = Yg > a.wet; Yt = torch.where(W, Yg, torch.zeros_like(Yg))
            alw = W.all(0).numpy(); nev = (~W.any(0)).numpy(); some = ~alw & ~nev
            if alw.any():                                                 # Type 1: Model-1
                B1[cs[alw]] = (Pinv @ Yg[:, torch.from_numpy(alw)]).T.numpy(); typ[cs[alw]] = 1; mdl[cs[alw]] = 1
            typ[cs[nev]] = 4
            if not some.any():
                continue
            sm = torch.from_numpy(some); Ws, Ys = W[:, sm], Yt[:, sm]; n = int(some.sum())
            valid = torch.stack([Ws[ft == f].any(0) & (~Ws[ft == f]).any(0) for f in range(a.folds)]); nv = valid.sum(0); el = nv >= 2
            idx_some = cs[some]; nval[idx_some] = nv.numpy(); typ[idx_some] = np.where(el.numpy(), 2, 3)
            if not el.any():
                continue
            We, Ye = Ws[:, el], Ys[:, el]; ve = valid[:, el].float(); sse = torch.zeros(3, int(el.sum()))
            for f in range(a.folds):
                tr, te = ft != f, ft == f
                b2 = lin_wet(Xd[tr], Ye[tr], We[tr], a.ridge, a.noise); g3 = logit(Xs[tr], We[tr]); b4 = tobit(Xd[tr], Ye[tr], We[tr], a.wet, noise=a.noise)
                p2 = (Xd[te] @ b2.T).clamp_min(0); p3 = torch.where((Xs[te] @ g3.T) > 0, p2, torch.zeros_like(p2)); p4 = (Xd[te] @ b4.T).clamp_min(0)
                for k_, p in enumerate((p2, p3, p4)):
                    sse[k_] += ve[f] * ((p - Ye[te]) ** 2).mean(0).sqrt()
            cvr = (sse / ve.sum(0)[None, :]).T.numpy(); ide = idx_some[el.numpy()]; cv[ide] = cvr; mdl[ide] = 2 + np.nanargmin(cvr, 1)
            B1[ide] = lin_wet(Xd, Ye, We, a.ridge, a.noise).numpy(); BL[ide] = logit(Xs, We).numpy(); BT[ide] = tobit(Xd, Ye, We, a.wet, noise=a.noise).numpy()
        if gk % 25 == 0:
            print(f"  group {gk + 1} of {ng}, {time.time() - t00:.0f} s", flush=True)
    np.savez_compressed(out / "model.npz", jj=jj.astype(np.int32), ii=ii.astype(np.int32), type=typ, model=mdl, cv_rmse=cv, valid_folds=nval, cols=cols, coef_linear=B1, coef_logit=BL, coef_tobit=BT, xmean=xmean, xstd=xstd,
                        used=used, train_runs=np.array(a.train_runs), wet=a.wet, k=a.k, noise=a.noise)
    land = np.load(a.land)["dmax_no_storm"][jj, ii] <= 0.1 if a.land else np.ones(N, bool); km = lambda m: f"{int(m.sum()) / 100:,.0f} km2"
    runs_txt = ", ".join(a.train_runs) if len(a.train_runs) <= 14 else ", ".join(a.train_runs[:12]) + f", ... ({len(a.train_runs)} runs, listed in model.npz)"
    L = [f"training: {runs_txt} ({T} hours" + (f", hours chosen by {a.hours}" if a.hours else "") + f"); prediction area {km(np.ones(N, bool))}; every cell uses its {a.k} nearest of {P} control points; flooded = deeper than {a.wet} m; assumed error of the inputs {a.noise} m",
         f"Type 1 (flooded in every hour, Model-1): {km(typ == 1)}",
         f"Type 2 with a model: {km(typ == 2)} - " + "; ".join(f"{MODELS[k]} {km(mdl == k)} ({100 * (mdl == k).sum() / max((typ == 2).sum(), 1):.0f}%)" for k in (2, 3, 4)),
         f"low flood risk (flooded at times, fewer than two folds with flooded and dry hours; no model): {km(typ == 3)}", f"never flooded in the training hours (no model): {km(typ == 4)}",
         f"on land (dry in the run without a hurricane, {km(land)}): Type 1 {km(land & (typ == 1))}, Type 2 with a model {km(land & (typ == 2))}, low flood risk {km(land & (typ == 3))}, never flooded {km(land & (typ == 4))}",
         "cross-validation RMSE of the Type 2 cells (m), median: " + ", ".join(f"{MODELS[k + 2]} {np.nanmedian(cv[typ == 2, k]):.3f}" for k in range(3)) + f"; of the model chosen {np.nanmedian(np.nanmin(cv[typ == 2], 1)):.3f}"]
    (out / "fit_summary.txt").write_text(chr(10).join(L), encoding="utf-8"); print(chr(10).join(L)); print(f"-> {out}, {time.time() - t00:.0f} s")


def cmd_apply(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); tag = a.tag; assert not (out / f"metrics_{tag}.csv").exists() and not (out / f"peak_{tag}.npz").exists(), f"{tag} exists in {out}"
    t00 = time.time(); z = np.load(a.model); model = {k: z[k] for k in z.files}; jj, ii = model["jj"], model["ii"]; N = len(jj); used = model["used"]
    f, _, key = a.inputs.partition(":"); Xin = np.load(f)[key] if key else np.load(f); Xin = np.asarray(Xin, np.float64)[:, used]
    hours = np.ones(len(Xin), bool)
    if a.hours:
        hz = np.load(a.hours.split(":")[0]); hours = np.asarray(hz[a.hours.split(":")[1]], bool)
    ida = Path(a.ida); h, roms, lat, lon = grid(ida); NY, NX = h.shape; has = model["model"] > 0; t2 = model["type"] == 2
    truth = load_depth(ida, a.truth_run, h, roms, jj, ii) if a.truth_run else None
    peak = np.full(N, np.nan, np.float32); pt = np.full(N, np.nan, np.float32); acc = {g: np.zeros(5) for g in ("all cells with a model", "Type 2 cells")}; series = {}
    cells = pd.read_csv(a.cells) if a.cells else None                      # sites: the land cells around them that have a model
    for s0 in range(0, N, a.chunk):
        sel = np.arange(s0, min(s0 + a.chunk, N)); p = predict(model, Xin, sel); peak[sel] = np.nanmax(np.where(hours[:, None], p, np.nan), 0) if hours.any() else np.nan
        if truth is not None:
            y = np.where(truth[:, sel] > float(model["wet"]), truth[:, sel], 0); pt[sel] = y[hours].max(0)
            for g, m in (("all cells with a model", has[sel]), ("Type 2 cells", t2[sel])):
                if m.any():
                    d = (p[:, m] - y[:, m])[hours]; yy = y[:, m][hours]; acc[g] += np.array([d.size, (d.astype(np.float64) ** 2).sum(), yy.sum(dtype=np.float64), (yy.astype(np.float64) ** 2).sum(), 0])
    np.savez_compressed(out / f"peak_{tag}.npz", jj=jj, ii=ii, peak=peak, **({"peak_truth": pt} if truth is not None else {}))
    rows = []
    if truth is not None:
        for g, m in (("all cells with a model", has), ("Type 2 cells", t2)):
            n, sse, sy, syy, _ = acc[g]; var = syy - sy ** 2 / n; r = {"cells": g, "area_km2": m.sum() / 100, "hours": int(hours.sum()), "nse": 1 - sse / var, "rmse_m": np.sqrt(sse / n),
                                                                     "peak_mean_numerical_model_m": float(np.nanmean(pt[m])), "peak_mean_p2m_m": float(np.nanmean(peak[m]))}
            for t in THR:
                A, Bm = pt[m] > t, peak[m] > t; r[f"flooded_above_{t}m_numerical_model_km2"] = A.sum() / 100; r[f"flooded_above_{t}m_p2m_km2"] = Bm.sum() / 100; r[f"csi_{t}m"] = (A & Bm).sum() / max((A | Bm).sum(), 1)
            rows.append(r)
        pd.DataFrame(rows).to_csv(out / f"metrics_{tag}.csv", index=False); pd.set_option("display.width", 250); print(pd.DataFrame(rows).round(3).T.to_string())
    if cells is not None:
        cellid = {(int(j), int(i)): k for k, (j, i) in enumerate(zip(jj, ii))}; land = np.load(a.land)["dmax_no_storm"] <= 0.1; R = a.radius; ser = {}; info = []
        for s in cells.itertuples():
            j, i = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin()); near = [(jx, ix) for jx in range(j - R, j + R + 1) for ix in range(i - R, i + R + 1) if 0 <= jx < NY and 0 <= ix < NX and np.hypot(jx - j, ix - i) <= R + 0.5 and land[jx, ix]]
            ids = np.array([cellid[k] for k in near if k in cellid], int); w = ids[has[ids]] if len(ids) else ids
            info.append({"station": s.station, "land_cells": len(near), "in_prediction_area": len(ids), "with_a_model": len(w), "low_flood_risk": int((model["type"][ids] == 3).sum()) if len(ids) else 0, "never_flooded": int((model["type"][ids] == 4).sum()) if len(ids) else 0})
            if len(w):
                ser[s.station] = np.nanmedian(predict(model, Xin, w), 1).astype(np.float32)
        np.savez_compressed(out / f"sites_{tag}.npz", **ser); pd.DataFrame(info).to_csv(out / f"sites_{tag}.csv", index=False)
        print(f"sites: {len(info)}; with land cells that have a model: {len(ser)}")
    print(f"-> {out} [{tag}], {time.time() - t00:.0f} s")


def main() -> None:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit"); f.add_argument("--ida", required=True); f.add_argument("--sums", required=True); f.add_argument("--area", required=True); f.add_argument("--train-runs", nargs="+", required=True); f.add_argument("--out", required=True)
    f.add_argument("--land", help="eval_<run>.npz of mapping_fit.py (dmax_no_storm), for the summary by land"); f.add_argument("--k", type=int, default=8); f.add_argument("--wet", type=float, default=0.05); f.add_argument("--folds", type=int, default=5)
    f.add_argument("--noise", type=float, default=0.0, help="assumed error of the inputs (m): 0 = the regressions of the paper; 0.12 = what the inputs differ by when observations or forecasts are fed in")
    f.add_argument("--ridge", type=float, default=1e-6); f.add_argument("--chunk", type=int, default=40000); f.add_argument("--threads", type=int, default=32)
    f.add_argument("--hours", help="DIR with hours_<run>.npy (boolean, one value per hour of the run): only these hours of that run are used, e.g. to leave out hours in which the output of a run is incomplete")
    p = sub.add_parser("apply"); p.add_argument("--ida", required=True); p.add_argument("--model", required=True); p.add_argument("--inputs", required=True, help="NPY, or NPZ:key, [T, control points of the sums]"); p.add_argument("--out", required=True); p.add_argument("--tag", required=True)
    p.add_argument("--truth-run"); p.add_argument("--hours", help="NPZ:key of a boolean mask of the hours that count"); p.add_argument("--cells", help="CSV station, lat, lon: series at the land cells around these sites"); p.add_argument("--land")
    p.add_argument("--radius", type=int, default=3); p.add_argument("--chunk", type=int, default=200000)
    a = ap.parse_args(); (cmd_fit if a.cmd == "fit" else cmd_apply)(a)


if __name__ == "__main__":
    main()
