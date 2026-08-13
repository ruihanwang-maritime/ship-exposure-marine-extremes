"""
Collect the fixed-threshold exposure series into one tidy public table.

Figures 1-3 use the fixed physical thresholds (U10 >= 17.2 m/s, SWH >= 6 m),
whereas Figure 4 and the accident analysis use basin- and month-specific P99
thresholds. The two pipelines are kept in separate files so the distinction
stays explicit:

    exposure_annual.csv        P99 thresholds, two 25-year windows, basin+corridor
    exposure_fixed_annual.csv  fixed thresholds, continuous 2015-2100, global+corridor

Exposure days are traffic-weighted means (Eq 4) and carry no vessel counts,
so these series are publishable as they stand.

Run:  python code/prepare_exposure_fixed.py

Requires the licensed source data; its outputs are already in data_public/,
so this script does not need to be run to reproduce the paper.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

NC = cfg.RAW / "new_climate"
GLOBAL_WIND = NC / "wind_exposure_results"                  # {model}_exposure.csv
GLOBAL_WAVE = NC / "wave" / "masnum" / "exposure_results"

# Two archived copies of the global wave series exist. They are identical in
# all 75 years and all three SSPs except SSP1-2.6 in 2055, where the earlier
# per-SSP files (wave_exposure_ssp{X}.csv) read 2.1637 and this later combined
# file reads 1.1637 - a difference of exactly 1.0 day. Because an annual figure
# is a traffic-weighted mean over months whose weights each sum to one, a
# discrepancy of exactly 1.0 is one whole month counted as extreme everywhere,
# i.e. the earlier files carry the bug. This file reproduces the published
# Fig 2b cohorts, so it is the authoritative source.
GLOBAL_WAVE_FILE = GLOBAL_WAVE / "wave_system_exposure_masnum_6m.csv"
CORR_WIND = NC / "wind" / "corridor"                        # corridor_{c}_thresh17p2.csv
CORR_WAVE = NC / "wave" / "masnum" / "corridor"             # corridor_{c}_thresh6m_masnum.csv

WAVE_MODEL = "masnum"           # the single continuous wave projection product
COLS = ["scale", "unit", "var", "model", "ssp", "year", "E_annual"]


def _melt(df, id_col="year", var_name="ssp"):
    return df.melt(id_vars=id_col, var_name=var_name, value_name="E_annual")


def global_wind():
    out = []
    for f in sorted(GLOBAL_WIND.glob("*_exposure.csv")):
        model = f.stem.replace("_exposure", "")
        d = _melt(pd.read_csv(f))
        d["scale"], d["unit"], d["var"], d["model"] = "global", "global", "wind", model
        out.append(d)
    return pd.concat(out, ignore_index=True)


def global_wave():
    d = _melt(pd.read_csv(GLOBAL_WAVE_FILE))
    d["scale"], d["unit"], d["var"], d["model"] = "global", "global", "wave", WAVE_MODEL
    return d[COLS]


def corridor_wind():
    out = []
    for c in cfg.CORRIDORS:
        d = _melt(pd.read_csv(CORR_WIND / f"corridor_{c}_thresh17p2.csv"),
                  var_name="model_ssp")
        # columns are "{model}__{ssp}"
        d[["model", "ssp"]] = d["model_ssp"].str.split("__", expand=True)
        d["scale"], d["unit"], d["var"] = "corridor", c, "wind"
        out.append(d[COLS])
    return pd.concat(out, ignore_index=True)


def corridor_wave():
    out = []
    for c in cfg.CORRIDORS:
        d = _melt(pd.read_csv(CORR_WAVE / f"corridor_{c}_thresh6m_masnum.csv"))
        d["scale"], d["unit"], d["var"], d["model"] = "corridor", c, "wave", WAVE_MODEL
        out.append(d[COLS])
    return pd.concat(out, ignore_index=True)


def main():
    cfg.require_raw(GLOBAL_WIND, GLOBAL_WAVE_FILE, CORR_WIND, CORR_WAVE)
    cfg.ensure_dirs()
    parts = {"global wind": global_wind(), "global wave": global_wave(),
             "corridor wind": corridor_wind(), "corridor wave": corridor_wave()}
    for k, v in parts.items():
        print(f"    {k:<16} {len(v):>6,} rows  "
              f"years {v['year'].min()}-{v['year'].max()}  "
              f"models {v['model'].nunique()}  ssps {v['ssp'].nunique()}")

    df = (pd.concat(parts.values(), ignore_index=True)[COLS]
            .dropna(subset=["E_annual"])
            .sort_values(["scale", "unit", "var", "model", "ssp", "year"])
            .reset_index(drop=True))

    out = cfg.PUBLIC / "exposure_fixed_annual.csv"
    df.to_csv(out, index=False)
    print(f"\n    -> {out.name}  ({len(df):,} rows, {out.stat().st_size/1e6:.2f} MB)")

    # service-life cohorts (Eq 9) need 25 continuous years from the delivery year
    for scale in ["global", "corridor"]:
        yr = df.loc[df["scale"] == scale, "year"]
        last = yr.max() - cfg.SERVICE_LIFE + 1
        print(f"    {scale}: years {yr.min()}-{yr.max()}, "
              f"delivery cohorts computable up to {last}")


if __name__ == "__main__":
    main()
