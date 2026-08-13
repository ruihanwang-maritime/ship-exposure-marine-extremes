"""
Strip absolute traffic volumes out of the exposure tables (Methods Eq 3-4, 13).

exposure_annual.csv / exposure_month.csv carry a T_annual / T_monthly column
holding the summed AIS vessel counts behind each traffic-weighted mean. The
exposure days themselves (E) are already weighted averages and disclose no
counts, so only the T columns are dropped.

Run:  python code/prepare_exposure_projected.py

Requires the licensed source data; its outputs are already in data_public/,
so this script does not need to be run to reproduce the paper.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

DROP = ["T_annual", "T_monthly"]


def sanitise(src, dst):
    df = pd.read_csv(src, encoding="utf-8-sig")
    dropped = [c for c in DROP if c in df.columns]
    df = df.drop(columns=dropped)
    # the annual table doubles as figure source data, so keep it readable;
    # the monthly table is 12x larger and only ever read programmatically
    if dst.suffix == ".parquet":
        df.to_parquet(dst, index=False)
    else:
        df.to_csv(dst, index=False)
    print(f"    {src.name} -> {dst.name}")
    print(f"        {len(df):,} rows, dropped {dropped or 'nothing'}, "
          f"{dst.stat().st_size/1e6:.2f} MB")
    return df


def main():
    cfg.require_raw(cfg.EXPOSURE_ANNUAL, cfg.EXPOSURE_MONTH)
    cfg.ensure_dirs()
    print("[1/2] annual exposure")
    a = sanitise(cfg.EXPOSURE_ANNUAL, cfg.PUBLIC / "exposure_annual.csv")
    print("[2/2] monthly exposure")
    sanitise(cfg.EXPOSURE_MONTH, cfg.PUBLIC / "exposure_month.parquet")

    print("\n    coverage:", ", ".join(
        f"{k}={v}" for k, v in [
            ("kinds", a["kind"].nunique()), ("units", a["unit"].nunique()),
            ("vars", a["var"].nunique()), ("models", a["model"].nunique()),
            ("ssps", a["ssp"].nunique()), ("years", a["year"].nunique())]))


if __name__ == "__main__":
    main()
