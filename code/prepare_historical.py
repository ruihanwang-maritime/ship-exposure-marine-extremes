"""
Assemble the historical (1980-2024) products behind Figure 1.

Sources are the pre-computed derived files under
`paper code/figure1_source/data/`, themselves regenerated from ERA5 and the
2021 AIS footprint by `regenerate_derived_data.py`. Nothing here carries vessel
counts: the grid-cell trend fields are pure ERA5, and the exposure fields are
traffic-weighted shares.

Outputs (data_public/)
    historical_gridcell_trend.npz    Fig 1a: OLS slope and p-value per cell
    historical_exposure_share.npz    Fig 1c: each cell's % of global exposure
    historical_annual.csv            Fig 1d: annual ECDs (Eq 5) and exposure (Eq 4)
    historical_month.csv             Fig 1e: monthly exposure, per year

Run:  python code/prepare_historical.py

Requires the licensed source data; its outputs are already in data_public/,
so this script does not need to be run to reproduce the paper.
"""
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

SRC = cfg.FIG1_SRC
Y0, Y1 = cfg.HIST_YEARS


def grid_fields():
    """Trend maps pass through unchanged; exposure maps become percentage shares."""
    shutil.copyfile(SRC / "gridcell_trend_1980_2024.npz",
                    cfg.PUBLIC / "historical_gridcell_trend.npz")
    print(f"    -> historical_gridcell_trend.npz")

    z = np.load(SRC / "ais_exposure_hotspot_1980_2024.npz")
    out = {"lat": z["lat"], "lon": z["lon"]}
    for var in ["wind", "wave"]:
        m = z[f"exposure_{var}_map"]
        out[f"share_{var}"] = 100 * m / np.nansum(m)
    np.savez_compressed(cfg.PUBLIC / "historical_exposure_share.npz", **out)
    print(f"    -> historical_exposure_share.npz  "
          f"(wind max {np.nanmax(out['share_wind']):.3f} %, "
          f"wave max {np.nanmax(out['share_wave']):.3f} %)")


def monthly_exposure():
    """Global traffic-weighted exposure days, one file per variable and year."""
    specs = [("wave", "monthly_historical_wave", r"monthly_exposure_global_(\d{4})\.parquet"),
             ("wind", "monthly_historical_wind", r"monthly_exposure_wind_global_(\d{4})\.parquet")]
    rows = []
    for var, folder, pat in specs:
        for f in sorted((SRC / folder).glob("*.parquet")):
            m = re.fullmatch(pat, f.name)
            if not m:
                continue                      # regional files, not used by Fig 1
            x = pd.read_parquet(f)[["month", "exposure_days"]]
            x["year"], x["var"] = int(m.group(1)), var
            rows.append(x)
    d = pd.concat(rows, ignore_index=True)
    return d[d["year"].between(Y0, Y1)][["var", "year", "month", "exposure_days"]]


def annual_ecd():
    """Annual extreme-condition days: threshold-exceeding ocean grid-cell days."""
    wave = (pd.read_csv(SRC / "global_ocean_df_year_wave.csv")
              [["year", "extreme_gridcell_days"]].assign(var="wave"))
    wind = (pd.read_csv(SRC / "global_ocean_df_month.csv")
              .groupby("year", as_index=False)["extreme_gridcell_days"].sum()
              .assign(var="wind"))
    d = pd.concat([wave, wind], ignore_index=True).rename(
        columns={"extreme_gridcell_days": "ecd"})
    return d[d["year"].between(Y0, Y1)][["var", "year", "ecd"]]


def main():
    cfg.require_raw(SRC)
    cfg.ensure_dirs()
    grid_fields()

    mon = monthly_exposure()
    mon.to_csv(cfg.PUBLIC / "historical_month.csv", index=False)
    print(f"    -> historical_month.csv  ({len(mon):,} rows)")

    ann = (mon.groupby(["var", "year"], as_index=False)["exposure_days"].sum()
              .merge(annual_ecd(), on=["var", "year"], how="outer")
              .sort_values(["var", "year"]))
    ann.to_csv(cfg.PUBLIC / "historical_annual.csv", index=False)
    print(f"    -> historical_annual.csv  ({len(ann):,} rows)")

    # Fig 1d quotes OLS trends and their two-sided p-values; print them as a check
    print(f"\n    OLS trends over {Y0}-{Y1}:")
    for var in ["wave", "wind"]:
        s = ann[ann["var"] == var].dropna(subset=["ecd"])
        r = stats.linregress(s["year"], s["ecd"])
        e = ann[ann["var"] == var].dropna(subset=["exposure_days"])
        re_ = stats.linregress(e["year"], e["exposure_days"])
        print(f"        {var}: ECD slope {r.slope:8.1f} cell-days/yr  p = {r.pvalue:.4f}   |   "
              f"exposure slope {re_.slope:+.5f} days/yr  p = {re_.pvalue:.3f}")
        print(f"             exposure range {e['exposure_days'].min():.2f}"
              f"-{e['exposure_days'].max():.2f} days/yr")


if __name__ == "__main__":
    main()
