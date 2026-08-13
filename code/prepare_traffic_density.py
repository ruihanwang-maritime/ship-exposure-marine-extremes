"""
Build the public, non-identifying shipping-density products (Methods Eq 1-2, 13).

The 2021 AIS records are licensed from MarineTraffic and cannot be redistributed.
Everything downstream of this script therefore consumes normalised *shares* only:
absolute vessel counts and vessel identities never leave this step.

Inputs  (restricted)
    df_flow_core99.parquet          daily unique cargo vessels per 1 deg cell,
                                    already restricted to the 99 % traffic footprint
    traffic_month_basin.parquet     same counts split by AR6 basin
    traffic_month_corridor.parquet  same counts split by corridor
    basin_unique_mmsi_2021.csv      unique MMSI per basin (aggregate)

Outputs (public, written to data_public/)
    footprint_global.parquet        Eq 1: C_ij as a share of global annual traffic
    density_global_month.parquet    Eq 2: W_ij,m, sums to 1 within each month
    density_basin_month.parquet     Eq 13: weights renormalised within each basin
    density_corridor_month.parquet  Eq 13: weights renormalised within each corridor
    basin_traffic_2021.csv          per-basin aggregate vessel counts (Fig 4 bubbles)

Run:  python code/prepare_traffic_density.py

Requires the licensed source data; its outputs are already in data_public/,
so this script does not need to be run to reproduce the paper.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

GRID = ["lon_bin", "lat_bin"]


def _check(df, group, col, what):
    """Weights must sum to exactly 1 within each normalisation group."""
    s = df.groupby(group)[col].sum()
    off = (s - 1.0).abs().max()
    status = "ok" if off < 1e-9 else "FAIL"
    print(f"    [{status}] {what}: {len(s)} groups, max |sum-1| = {off:.2e}")
    return off < 1e-9


def build_footprint_and_global():
    """Eq 1 and Eq 2, both derived from the daily footprint counts."""
    print("[1/4] global footprint and monthly density")
    f = pd.read_parquet(cfg.AIS_FOOTPRINT_99)
    f["month"] = f["valid_time"].dt.month
    print(f"    source: {len(f):,} cell-days, {f['valid_time'].nunique()} days")

    # Eq 1: C_ij = sum_d N_ij,d, published as a share of the global annual total
    c = f.groupby(GRID, as_index=False)["ship_traffic"].sum()
    total = c["ship_traffic"].sum()
    c["share"] = c["ship_traffic"] / total
    c = c.sort_values("share", ascending=False).reset_index(drop=True)
    c["cum_share"] = c["share"].cumsum()          # Fig 1b 0-95 / 95-99 / 99-100 bands
    c = c[GRID + ["share", "cum_share"]]
    print(f"    footprint: {len(c):,} cells; top 95 % held by "
          f"{(c['cum_share'] <= 0.95).sum():,} cells")

    # Eq 2: W_ij,m normalised over the footprint within each calendar month
    m = f.groupby(["month"] + GRID, as_index=False)["ship_traffic"].sum()
    m["w_month"] = m["ship_traffic"] / m.groupby("month")["ship_traffic"].transform("sum")
    m = m[["month"] + GRID + ["w_month"]].sort_values(["month"] + GRID)
    _check(m, "month", "w_month", "global W_ij,m")

    c.to_parquet(cfg.FOOTPRINT_PUBLIC, index=False)
    m.to_parquet(cfg.DENSITY_GLOBAL, index=False)
    print(f"    -> {cfg.FOOTPRINT_PUBLIC.name}  ({len(c):,} rows)")
    print(f"    -> {cfg.DENSITY_GLOBAL.name}  ({len(m):,} rows)")
    return c


def build_regional(src, unit_col, out_path, label):
    """Eq 13: the same weights renormalised within one basin / corridor."""
    print(f"[{label}] {unit_col} monthly density")
    d = pd.read_parquet(src)

    # recompute rather than trust the stored w_month, so the published file is
    # self-consistent with Eq 2 applied within the unit
    d["w_month"] = (d["ship_traffic"]
                    / d.groupby([unit_col, "month"])["ship_traffic"].transform("sum"))
    out = (d[[unit_col, "month"] + GRID + ["w_month"]]
           .sort_values([unit_col, "month"] + GRID)
           .reset_index(drop=True))
    _check(out, [unit_col, "month"], "w_month", f"{unit_col} W_ij,m")

    out.to_parquet(out_path, index=False)
    print(f"    -> {out_path.name}  ({len(out):,} rows, "
          f"{out[unit_col].nunique()} {unit_col}s)")
    return out


def build_basin_traffic(footprint):
    """Per-basin aggregate vessel counts used for the Fig 4 bubble scale.

    Unique-MMSI totals per basin are aggregate statistics, not vessel-level
    records, so they are publishable; the accompanying share column lets the
    figure be redrawn on a purely relative scale if preferred.
    """
    print("[4/4] basin aggregate traffic")
    t = pd.read_csv(cfg.BASIN_MMSI)
    b = pd.read_parquet(cfg.TRAF_BASIN)
    vd = (b.groupby("basin", as_index=False)["ship_traffic"].sum()
            .rename(columns={"ship_traffic": "vessel_days"}))
    t = t.merge(vd, on="basin")
    t["vessel_days_share"] = t["vessel_days"] / t["vessel_days"].sum()
    t = t[["basin", "unique_mmsi", "vessel_days_share"]].sort_values("basin")
    t.to_csv(cfg.BASIN_TRAFFIC_PUBLIC, index=False)
    print(f"    -> {cfg.BASIN_TRAFFIC_PUBLIC.name}  ({len(t)} basins)")
    return t


def main():
    cfg.require_raw(cfg.AIS_FOOTPRINT_99, cfg.TRAF_BASIN, cfg.TRAF_CORRIDOR, cfg.BASIN_MMSI)
    cfg.ensure_dirs()
    footprint = build_footprint_and_global()
    build_regional(cfg.TRAF_BASIN, "basin", cfg.DENSITY_BASIN, "2/4")
    build_regional(cfg.TRAF_CORRIDOR, "corridor", cfg.DENSITY_CORRIDOR, "3/4")
    build_basin_traffic(footprint)

    print("\nPublic products written to", cfg.PUBLIC)
    for p in sorted(cfg.PUBLIC.iterdir()):
        print(f"    {p.name:<34} {p.stat().st_size/1e6:7.2f} MB")


if __name__ == "__main__":
    main()
