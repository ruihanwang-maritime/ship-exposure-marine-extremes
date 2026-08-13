"""
Build the accident modelling table (Methods, "Accident records and accident-day
weather matching").

Open-ocean accidents are those assigned to an IPCC AR6 ocean basin; coastal and
unassigned records are excluded. Accident-day wind and wave are compared with
basin- and month-specific P95 / P99 thresholds computed from ERA5 over
2002-2022, and each accident is placed in exactly one of four mutually
exclusive categories:

    wind-only   wind exceeds, wave does not
    wave-only   wave exceeds, wind does not
    compound    both exceed on the same day in the same cell
    non-extreme neither exceeds  (reference category)

Outcomes: a binary serious-accident indicator taken from the source records,
and human casualty intensity HCI = fatalities + missing + 0.1 x injuries (Eq 11).

The output is written outside this repository (config.RESTRICTED) because it is
row-level licensed accident data. Only the fitted model summaries in
data_public/ are shareable.

Run:  python code/prepare_accident_panel.py

Requires the licensed source data; its outputs are already in data_public/,
so this script does not need to be run to reproduce the paper.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

# The source CSV was written through a non-raw Windows path, so "\200" became
# a literal \x80 byte in the filename. Kept verbatim so the file is findable.
ACCIDENT_CSV = cfg.RAW / "maritime accident\x802_2022_accident_wind_wave.csv"

# The 1 deg, land-masked threshold set - the same one the Fig 4 exposure
# analysis uses, as the Methods state. An older pooled set exists under
# weather_wind_combine/month_threshold/ and was used by the exploratory
# notebooks; it disagrees sharply in marginal seas (MED, SEA, ARO).
WIND_THR = cfg.THR_DIR / "AR6_basin_month_wind_1deg_2002_2022.csv"
WAVE_THR = cfg.THR_DIR / "AR6_basin_month_wave_1deg_2002_2022.csv"

OUT = cfg.RESTRICTED / "accident_panel.parquet"

COASTAL = "COAST/OTHER"
KEEP = ["year", "month", "basin", "GT", "Age", "logGT", "serious", "HCI",
        "wind_speed10", "wave_height", "wave_observed",
        "cat_p95", "cat_p99", "wind_ext_p95", "wind_ext_p99",
        "wave_ext_p95", "wave_ext_p99"]


def categorise(wind_ext, wave_ext):
    """Four mutually exclusive accident-day weather categories."""
    return np.select(
        [wind_ext & ~wave_ext, wave_ext & ~wind_ext, wind_ext & wave_ext],
        ["wind_only", "wave_only", "compound"],
        default="non_extreme")


def main():
    cfg.require_raw(ACCIDENT_CSV, WIND_THR, WAVE_THR)
    cfg.ensure_dirs()
    d = pd.read_csv(ACCIDENT_CSV, low_memory=False)
    print(f"    source records: {len(d):,}")

    d = d.rename(columns={"ar6_ocean_abbrev": "basin"})
    d = d[d["basin"] != COASTAL].copy()
    print(f"    open-ocean (AR6 basin assigned): {len(d):,}")

    # thresholds: basin x calendar month, ERA5 2002-2022
    def thresholds(path, var):
        t = pd.read_csv(path).rename(columns={"region_abbr": "basin",
                                              "P95": f"{var}_p95",
                                              "P99": f"{var}_p99"})
        return t[["basin", "month", f"{var}_p95", f"{var}_p99"]]

    d = d.merge(thresholds(WIND_THR, "wind"), on=["basin", "month"], how="left") \
         .merge(thresholds(WAVE_THR, "wave"), on=["basin", "month"], how="left")

    # An accident-day wave value is missing wherever the wave product has no
    # cell at the reported location. Those days cannot exceed the wave
    # threshold, so they fall in the wind-only or non-extreme categories;
    # `wave_observed` marks them for the sensitivity check in accident_models.
    d["wave_observed"] = d["wave_height"].notna()
    for q in ["p95", "p99"]:
        d[f"wind_ext_{q}"] = (d["wind_speed10"] >= d[f"wind_{q}"]).fillna(False)
        d[f"wave_ext_{q}"] = (d["wave_height"] >= d[f"wave_{q}"]).fillna(False)
        d[f"cat_{q}"] = categorise(d[f"wind_ext_{q}"], d[f"wave_ext_{q}"])

    # outcomes
    d["serious"] = (d["Serious Indicator"].astype(str).str.lower()
                    .isin(["true", "1", "yes"]).astype(int))
    cas = d[["No. Dead", "No. Missing", "No. Injured"]].fillna(0)
    d["HCI"] = cas["No. Dead"] + cas["No. Missing"] + 0.1 * cas["No. Injured"]

    # covariates
    d["Age"] = pd.to_numeric(d["Age"], errors="coerce")
    d["GT"] = pd.to_numeric(d["GT"], errors="coerce")
    d["logGT"] = np.log(d["GT"].where(d["GT"] > 0))

    n0 = len(d)
    d = d.dropna(subset=["wind_speed10", "logGT", "Age", "wind_p95", "wave_p95"])
    print(f"    complete cases for the models: {len(d):,} "
          f"({n0 - len(d):,} dropped for missing wind, tonnage or age); "
          f"{int((~d['wave_observed']).sum()):,} of these lack an accident-day "
          f"wave value")

    out = d[KEEP].reset_index(drop=True)
    out.to_parquet(OUT, index=False)
    print(f"    -> {OUT}")

    for q in ["p95", "p99"]:
        n = out[f"cat_{q}"].value_counts()
        sr = out.groupby(f"cat_{q}")["serious"].mean().mul(100).round(2)
        print(f"\n    {q.upper()} categories:")
        for k in ["non_extreme", "wind_only", "wave_only", "compound"]:
            print(f"        {k:<12} n={n.get(k, 0):>6,}   serious={sr.get(k, float('nan')):>6.2f}%")


if __name__ == "__main__":
    main()
