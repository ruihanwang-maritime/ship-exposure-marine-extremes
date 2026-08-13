"""
Service-life exposure by delivery cohort (Methods Eq 9).

A vessel entering service in year y0 accumulates the annual traffic-weighted
exposure days of years y0 .. y0+24:

    L(y0) = sum_{t=y0}^{y0+24} A_t

Wind is the five-model CMIP6 ensemble (mean and inter-model SD are formed
after each model's own cohort sum); wave comes from the single continuous
projection, so no inter-model spread exists.

Used by fig2 (global) and fig3 (corridor).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg


def load_fixed():
    return pd.read_csv(cfg.PUBLIC / "exposure_fixed_annual.csv")


def cohort_sum(series_by_year, y0, span=cfg.SERVICE_LIFE):
    """Sum a year-indexed series over [y0, y0+span-1]; NaN if the window is short."""
    w = series_by_year.reindex(range(y0, y0 + span))
    return w.sum() if w.notna().all() else float("nan")


def service_life(df, scale="global", unit="global", delivery_years=None):
    """Per-model cohort sums, then the ensemble summary for each var/ssp/cohort."""
    delivery_years = delivery_years or list(range(2030, 2071, 10))
    sub = df[(df["scale"] == scale) & (df["unit"] == unit)]

    rows = []
    for (var, model, ssp), g in sub.groupby(["var", "model", "ssp"]):
        s = g.set_index("year")["E_annual"].sort_index()
        for y0 in delivery_years:
            rows.append(dict(var=var, model=model, ssp=ssp, delivery_year=y0,
                             L=cohort_sum(s, y0)))
    per_model = pd.DataFrame(rows).dropna(subset=["L"])

    ens = (per_model.groupby(["var", "ssp", "delivery_year"], as_index=False)
                    .agg(L_mean=("L", "mean"), L_sd=("L", "std"),
                         n_models=("L", "size")))
    return per_model, ens


def main():
    df = load_fixed()
    per_model, ens = service_life(df)

    out = cfg.PUBLIC / "service_life_global.csv"
    ens.to_csv(out, index=False)
    print(f"    -> {out.name}")
    for var in ["wind", "wave"]:
        p = (ens[ens["var"] == var]
             .pivot(index="ssp", columns="delivery_year", values="L_mean").round(1))
        print(f"\n  {var} service-life exposure days ({cfg.SERVICE_LIFE}-yr):")
        print(p.to_string())

    per_model.to_csv(cfg.PUBLIC / "service_life_global_per_model.csv", index=False)
    print(f"\n    -> service_life_global_per_model.csv")


if __name__ == "__main__":
    main()
