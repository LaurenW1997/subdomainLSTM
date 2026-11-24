"""Francine case, open boundary, step 2: a ROMS boundary file from HYCOM, in the layout of the file the Ida run read.

The Ida run took its open boundary (free surface, barotropic and 3-D velocity, temperature, salinity on the southern, western
and eastern edge; the northern edge is closed) from a 1 km model of the Gulf, every 6 hours. Here the same variables are made
from the global HYCOM analysis (ESPC-D-V02, 1/12 degree): free surface every hour (it carries the tide), the 3-D fields every
3 hours, interpolated in time to the hours.
    horizontal  bilinear on the HYCOM grid; cells HYCOM has no water in are first given the value of the nearest cell with water
    vertical    from the 40 HYCOM depths to the 8 layers of the model (Vtransform 2, Vstretching 4, theta_s 5, theta_b 0.4, Tcline 100 m);
                below the deepest HYCOM value the deepest value is kept
    ubar, vbar  thickness-weighted mean of the layers
    level       one constant --shift is added to the free surface, the same on all edges (see level_shift.py)
    land points of the edges (mask 0): zero, as in the Ida file
The grid has no rotation (angle 0), so u is eastward and v northward.
Input : --hycom DIR (ssh_*.nc, u3z_*.nc, v3z_*.nc, t3z_*.nc, s3z_*.nc of hycom_fetch.sh), --edges NPZ (coordinates, depth and mask of the
        edges of the model grid and the attributes of the Ida file), --start, --end
Output: --out FILE (NetCDF, variables as in the Ida file), --out with .txt: a summary
Usage : python make_boundary_hycom.py --hycom DIR --edges FILE --shift -0.05 --start "2024-08-14 00:00" --end "2024-09-19 00:00" --out FILE
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd

N, THETA_S, THETA_B, TCLINE = 8, 5.0, 0.4, 100.0
EDGES = ("south", "west", "east")


def load(folder: str, name: str, var: str):
    """All blocks of one variable in one array [time, (depth,) lat, lon], times as hours since 1970, duplicates at block joins dropped."""
    parts = []; times = []; depth = None
    for f in sorted(glob.glob(f"{folder}/{name}_*.nc")):
        d = nc.Dataset(f); t = d["time"]; tt = nc.num2date(t[:], t.units, only_use_cftime_datetimes=False); v = d[var]; v.set_auto_maskandscale(True)
        parts.append(np.ma.filled(v[:].astype(np.float32), np.nan)); times.append(pd.DatetimeIndex(tt)); lat = np.array(d["lat"][:], "f8"); lon = np.array(d["lon"][:], "f8"); depth = np.array(d["depth"][:], "f8") if "depth" in d.variables else None; d.close()
    t = times[0].append(times[1:]) if len(times) > 1 else times[0]; a = np.concatenate(parts); keep = ~t.duplicated(); order = np.argsort(t[keep])
    return a[keep][order], t[keep][order], lat, np.where(lon > 180, lon - 360, lon), depth


def nearest_fill_index(valid: np.ndarray, lat, lon) -> np.ndarray:
    """For every cell of a layer the flat index of the nearest cell with water (itself where it has water)."""
    ny, nx = valid.shape; idx = np.arange(ny * nx).reshape(ny, nx)
    if valid.all() or not valid.any():
        return idx
    LO, LA = np.meshgrid(lon, lat); x = (LO * np.cos(np.deg2rad(29.5))).ravel(); y = LA.ravel(); v = np.where(valid.ravel())[0]; m = np.where(~valid.ravel())[0]
    d2 = (x[m][:, None] - x[v][None, :]) ** 2 + (y[m][:, None] - y[v][None, :]) ** 2; out = idx.ravel().copy(); out[m] = v[d2.argmin(1)]
    return out.reshape(ny, nx)


def bilinear(lat, lon, plat, plon):
    fy = (plat - lat[0]) / (lat[1] - lat[0]); fx = (plon - lon[0]) / (lon[1] - lon[0]); j = np.clip(np.floor(fy).astype(int), 0, len(lat) - 2); i = np.clip(np.floor(fx).astype(int), 0, len(lon) - 2)
    return j, i, np.clip(fy - j, 0, 1), np.clip(fx - i, 0, 1)


def apply(field2d, w):
    j, i, wy, wx = w
    return (1 - wy) * ((1 - wx) * field2d[..., j, i] + wx * field2d[..., j, i + 1]) + wy * ((1 - wx) * field2d[..., j + 1, i] + wx * field2d[..., j + 1, i + 1])


def layers(h: np.ndarray):
    """Depth of the layer centres (positive down) and layer thickness [N, points] for zeta = 0."""
    def stretch(s):
        c = (1 - np.cosh(THETA_S * s)) / (np.cosh(THETA_S) - 1); return (np.exp(THETA_B * c) - 1) / (1 - np.exp(-THETA_B))
    sr = (np.arange(1, N + 1) - N - 0.5) / N; sw = (np.arange(0, N + 1) - N) / N; h = np.maximum(h, 0.1)
    zr = h[None, :] * (TCLINE * sr[:, None] + h[None, :] * stretch(sr)[:, None]) / (TCLINE + h[None, :]); zw = h[None, :] * (TCLINE * sw[:, None] + h[None, :] * stretch(sw)[:, None]) / (TCLINE + h[None, :])
    return -zr, np.diff(zw, axis=0)


def vertical(prof, depth, zc):
    """Profiles [time, depth, points] to the layers: [time, N, points]. Linear in depth; outside the HYCOM depths the end value."""
    k = np.clip(np.searchsorted(depth, zc) - 1, 0, len(depth) - 2); w = np.clip((zc - depth[k]) / (depth[k + 1] - depth[k]), 0, 1); p = np.arange(zc.shape[1])[None, :]
    return (1 - w)[None] * prof[:, k, p] + w[None] * prof[:, k + 1, p]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--hycom", required=True); ap.add_argument("--edges", required=True); ap.add_argument("--shift", type=float, required=True)
    ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", required=True); a = ap.parse_args(); assert not Path(a.out).exists(), f"{a.out} exists"
    E = np.load(a.edges); attrs = json.loads(str(E["ida_attrs"])); hours = pd.date_range(a.start, a.end, freq="h"); L = []
    ssh, ts, lat, lon, _ = load(a.hycom, "ssh", "surf_el"); assert ts[0] <= hours[0] and ts[-1] >= hours[-1], f"HYCOM surface elevation covers {ts[0]} .. {ts[-1]}"
    fill2 = nearest_fill_index(np.isfinite(ssh).mean(0) > 0.5, lat, lon); ssh = ssh.reshape(len(ssh), -1)[:, fill2.ravel()].reshape(ssh.shape); ssh = ssh[ts.get_indexer(hours)]; assert np.isfinite(ssh).all()
    F = {}
    for name, var in (("u3z", "water_u"), ("v3z", "water_v"), ("t3z", "water_temp"), ("s3z", "salinity")):
        x, t3, la3, lo3, depth = load(a.hycom, name, var); assert np.allclose(la3, lat) and np.allclose(lo3, lon); assert t3[0] <= hours[0] and t3[-1] >= hours[-1], f"{name} covers {t3[0]} .. {t3[-1]}"
        for k in range(1, x.shape[1]):                                     # below the bottom: the value above
            bad = ~np.isfinite(x[:, k]); x[:, k][bad] = x[:, k - 1][bad]
        fi = nearest_fill_index(np.isfinite(x[:, 0]).mean(0) > 0.5, lat, lon); x = x.reshape(x.shape[0], x.shape[1], -1)[:, :, fi.ravel()].reshape(x.shape); assert np.isfinite(x).all(), name
        F[var] = (x, t3, depth); L.append(f"{name}: {len(t3)} times {t3[0]} .. {t3[-1]}, step {np.unique(np.diff(t3.values).astype('timedelta64[h]').astype(int)).tolist()} h, {len(depth)} depths to {depth[-1]:.0f} m")
    th = (hours - pd.Timestamp("1970-01-01")) / pd.Timedelta(hours=1)

    def in_time(var, w):
        """3-hourly profiles at the points of w, linear in time to the hours: [hours, depth, points]."""
        x, t3, _ = F[var]; p = apply(x, w); t3h = ((t3 - pd.Timestamp("1970-01-01")) / pd.Timedelta(hours=1)).to_numpy(); k = np.clip(np.searchsorted(t3h, th.to_numpy(), side="right") - 1, 0, len(t3h) - 2)
        f = ((th.to_numpy() - t3h[k]) / (t3h[k + 1] - t3h[k]))[:, None, None]; return (1 - f) * p[k] + f * p[k + 1]

    o = nc.Dataset(a.out, "w", format="NETCDF4_CLASSIC"); dims = {"xi_rho": 5510, "xi_u": 5509, "xi_v": 5510, "eta_rho": 1837, "eta_u": 1837, "eta_v": 1836, "s_rho": N}
    for k, n in dims.items():
        o.createDimension(k, n)
    o.createDimension("time", None); tv = o.createVariable("ocean_time", "f8", ("time",))
    for k, v in attrs["ocean_time"].items():
        if k not in ("dims", "dtype"):
            tv.setncattr(k, v)
    tv[:] = ((hours - pd.Timestamp("1858-11-17")) / pd.Timedelta(days=1)).to_numpy()
    o.type = "ROMS bry conditions from HYCOM ESPC-D-V02 (global 1/12 degree analysis)"; o.history = f"make_boundary_hycom.py; free surface every hour, 3-D fields every 3 h interpolated to the hours; {a.shift:+.3f} m added to the free surface"

    def put(name, data):
        v = o.createVariable(name, "f8", tuple(attrs[name]["dims"]))
        for k, x in attrs[name].items():
            if k not in ("dims", "dtype"):
                v.setncattr(k, x)
        v[:] = data
    depth = F["water_u"][2]
    for e in EDGES:
        h_r = E[f"h_{e}"]; h_in = E["h_south_row1"] if e == "south" else E["h_west_col1"] if e == "west" else E["h_east_col2"]
        pts = {"rho": (E[f"lat_rho_{e}"], E[f"lon_rho_{e}"], E[f"mask_rho_{e}"] > 0.5, h_r), "u": (E[f"lat_u_{e}"], E[f"lon_u_{e}"], E[f"mask_u_{e}"] > 0.5, 0.5 * (h_r[:-1] + h_r[1:]) if e == "south" else 0.5 * (h_r + h_in)),
               "v": (E[f"lat_v_{e}"], E[f"lon_v_{e}"], E[f"mask_v_{e}"] > 0.5, 0.5 * (h_r + h_in) if e == "south" else 0.5 * (h_r[:-1] + h_r[1:]))}
        la, lo, m, h = pts["rho"]; w = bilinear(lat, lon, la, lo); z = apply(ssh, w) + a.shift; z[:, ~m] = 0.0; put(f"zeta_{e}", z)
        zc, _ = layers(h)
        for var, nm in (("water_temp", "temp"), ("salinity", "salt")):
            x = vertical(in_time(var, w), depth, zc); x[:, :, ~m] = 0.0; put(f"{nm}_{e}", x)
            if nm == "temp":
                L.append(f"{e}: {int(m.sum())} ocean points of {len(m)}; zeta mean {z[:, m].mean():+.3f} m, std in time {z[:, m].std(0).mean():.3f} m, range {z[:, m].min():+.2f} .. {z[:, m].max():+.2f}; temperature {x[:, :, m].min():.1f} .. {x[:, :, m].max():.1f} C")
            else:
                L.append(f"   salinity {x[:, :, m].min():.1f} .. {x[:, :, m].max():.1f}")
        for var, nm, pk in (("water_u", "u", "u"), ("water_v", "v", "v")):
            la, lo, m, h = pts[pk]; w = bilinear(lat, lon, la, lo); zc, hz = layers(h); x = vertical(in_time(var, w), depth, zc); x[:, :, ~m] = 0.0; put(f"{nm}_{e}", x)
            bar = (x * hz[None]).sum(1) / hz.sum(0)[None]; put(f"{nm}bar_{e}", bar); L.append(f"   {nm}bar {bar[:, m].min():+.2f} .. {bar[:, m].max():+.2f} m/s, std {bar[:, m].std():.3f}")
    o.close(); L = [f"{len(hours)} hours {hours[0]} .. {hours[-1]}; HYCOM grid {len(lat)} x {len(lon)}, {lat[1] - lat[0]:.3f} x {lon[1] - lon[0]:.3f} degrees; shift {a.shift:+.3f} m"] + L
    Path(a.out).with_suffix(".txt").write_text(chr(10).join(L), encoding="utf-8"); print(chr(10).join(L)); print("->", a.out)


if __name__ == "__main__":
    main()
