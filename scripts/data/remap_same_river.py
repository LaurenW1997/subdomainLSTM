"""Re-map the discharge input of river-chain stations to the SAME-RIVER UPSTREAM gauge
(deliverable 07, step 1). The HUC8 rule in station_discharge_map.csv gave most river stations
a gauge that lies downstream of them (Burkeville -> Ruliff, Goodrich -> Romayor, Town Bluff ->
Saltwater Barrier, Addicks outflow -> Piney Point, ...), which carries no lead information.

For every chain below, station i gets station i-1 as its gauge; the first element may be a
"head" gauge that is not a water-level station of ours (reservoir outflow, upstream river gauge).
Gauges missing from config/discharge_gauges.csv are added with site metadata from the USGS
site service (and their 00060 IV availability is checked). Stations outside the chains keep
their mapping. Writes both config files in place and prints the changes.

Usage: python scripts/data/remap_same_river.py [--dry-run]
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
CFG = REPO / "config"
SITE = "https://waterservices.usgs.gov/nwis/site/"

# downstream order; first element may be a head gauge (not necessarily one of our stations)
CHAINS = {
    "Sabine (Toledo Bend release)":       ["08025360", "08026000", "08028500", "08030500"],
    "Neches (Sam Rayburn / Town Bluff)":  ["08033000", "08033500", "08040600", "08041000", "08041780"],
    "Trinity (Lake Livingston release)":  ["08065350", "08066000", "08066250", "08066500", "08067000", "08067100", "08067250"],
    "W Fk San Jacinto (Lake Conroe)":     ["08067548", "08067650", "08068000", "08068090"],
    "Buffalo Bayou (Barker release)":     ["08072500", "08073500", "08073600", "08073700", "08074000"],
    "Langham Ck (Addicks release)":       ["08073000", "08073100"],
    "Brazos":                             ["08098290", "08098450", "08108700", "08110200", "08111500", "08111850", "08114000", "08114100", "08116650", "08116850", "08079120"],
    "Colorado (TX)":                      ["08160400", "08161000", "08162000", "08162500", "08162501"],
    "Guadalupe":                          ["08173900", "08175800", "08176500"],
    "Mississippi":                        ["07373420", "07374000", "07374525"],
    "Atchafalaya (Old River outflow)":    ["07381482", "07381490", "07381515", "07381600"],
    "Amite":                              ["07377300", "07377000", "07378500", "07380120"],
    "Comite":                             ["07377500", "07377750", "07377870", "07378000", "07378050"],
    "Pearl (main stem)":                  ["02489000", "02489500", "02490193", "02490200"],
}
# stations that get a specific upstream gauge without being part of a linear chain
EXTRA = {
    "02492100": "02489500", "02492519": "02489500", "02492600": "02489500", "02492511": "02489500",   # Pearl locks / lower Pearl <- Bogalusa
    "02492700": "02492600",                                                                            # Pearl at I-10 <- Pearl River, LA
}


def usgs_sites(ids: list[str]) -> pd.DataFrame:
    r = requests.get(SITE, params={"format": "rdb", "sites": ",".join(ids), "siteOutput": "expanded", "siteStatus": "all"}, timeout=120)
    r.raise_for_status()
    lines = [l for l in r.text.splitlines() if not l.startswith("#")]
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[2:])), sep="\t", dtype=str)
    return df.set_index("site_no")


def usgs_q_catalog(ids: list[str]) -> pd.DataFrame:
    r = requests.get(SITE, params={"format": "rdb", "sites": ",".join(ids), "seriesCatalogOutput": "true", "parameterCd": "00060", "siteStatus": "all"}, timeout=120)
    r.raise_for_status()
    lines = [l for l in r.text.splitlines() if not l.startswith("#")]
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[2:])), sep="\t", dtype=str)
    df = df[(df.parm_cd == "00060") & (df.data_type_cd.isin(["iv", "uv"]))]
    return df.groupby("site_no").agg(iv_begin=("begin_date", "min"), iv_end=("end_date", "max"), n=("count_nu", lambda s: pd.to_numeric(s, errors="coerce").sum()))


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    m = pd.read_csv(CFG / "station_discharge_map.csv", dtype=str)
    g = pd.read_csv(CFG / "discharge_gauges.csv", dtype=str)
    census = pd.read_csv(CFG / "stations_census.csv", dtype={"station_id": str}).drop_duplicates("station_id").set_index("station_id")
    st_ids = set(m.station_id)

    # 00060 IV availability of every chain member first: a station whose immediate upstream
    # neighbour has no discharge record takes the nearest member further upstream that has one
    all_ids = sorted({x for c in CHAINS.values() for x in c} | set(EXTRA.values()))
    cat = usgs_q_catalog(all_ids)
    has_q = set(cat.index)
    new_map: dict[str, str] = {}
    for name, chain in CHAINS.items():
        print("\n## " + name)
        for i, sid in enumerate(chain):
            tag = "station" if sid in st_ids else "head gauge only"
            lat = census.lat.get(sid, float("nan")) if sid in census.index else float("nan")
            print(f"   {i}: {sid} {tag:16s} lat {lat}  Q:{'yes' if sid in has_q else 'NO'}")
            if i > 0 and sid in st_ids:
                up = [x for x in chain[:i] if x in has_q]
                if up:
                    new_map[sid] = up[-1]
                else:
                    print(f"      ! no upstream member with discharge for {sid}; mapping unchanged")
    new_map.update({k: v for k, v in EXTRA.items() if k in st_ids and v in has_q})

    gauges_needed = sorted(set(new_map.values()))
    missing = [x for x in gauges_needed if x not in set(g.gauge_id)]
    print(f"\n{len(new_map)} stations re-mapped; {len(gauges_needed)} distinct upstream gauges, {len(missing)} not yet in discharge_gauges.csv: {missing}")

    print("00060 IV availability of the gauges used:")
    print(cat.loc[gauges_needed].to_string())

    if missing:
        info = usgs_sites(missing)
        rows = []
        for gid in missing:
            s = info.loc[gid]
            dom = ""
            for d, (x0, x1, y0, y1) in {"Louisiana100m": (-94.11, -88.39, 28.74, 31.14), "Texas100m": (-99.03, -95.24, 25.85, 29.13), "Galveston100m": (-96.71, -94.04, 28.74, 31.16)}.items():
                if x0 <= float(s.dec_long_va) <= x1 and y0 <= float(s.dec_lat_va) <= y1:
                    dom = (dom + "|" if dom else "") + d
            rows.append({"gauge_id": gid, "gauge_name": s.station_nm, "lat": s.dec_lat_va, "lon": s.dec_long_va, "huc8": s.huc_cd,
                         "drain_area_mi2": s.get("drain_area_va", ""), "iv_begin": cat.loc[gid, "iv_begin"], "domain": dom or "upstream_of_domain"})
        g = pd.concat([g, pd.DataFrame(rows)], ignore_index=True)
        print("\nadded gauges:"); print(pd.DataFrame(rows)[["gauge_id", "gauge_name", "huc8", "drain_area_mi2", "iv_begin", "domain"]].to_string(index=False))

    gname = g.set_index("gauge_id").gauge_name
    changed = []
    for i, row in m.iterrows():
        sid = row.station_id
        if sid in new_map and new_map[sid] != row.gauge_id:
            changed.append((sid, row["name"], row.gauge_id, new_map[sid], gname.get(new_map[sid], "")))
            m.loc[i, ["gauge_id", "gauge_name", "assignment"]] = [new_map[sid], gname.get(new_map[sid], ""), "same_river_upstream"]
    print(f"\n{len(changed)} mappings changed:")
    for c in changed:
        print(f"   {c[0]} {c[1][:45]:45s}  {c[2]} -> {c[3]} {c[4]}")
    if a.dry_run:
        print("dry run: nothing written"); return
    m.to_csv(CFG / "station_discharge_map.csv", index=False)
    g.to_csv(CFG / "discharge_gauges.csv", index=False)
    print("wrote", CFG / "station_discharge_map.csv", "and", CFG / "discharge_gauges.csv", f"({len(g)} gauges)")


if __name__ == "__main__":
    main()
