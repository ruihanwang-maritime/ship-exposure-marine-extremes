"""
Table 1: associations between extreme marine weather and accident consequences
(Methods Eq 10-12).

Serious-accident classification is modelled with logistic regression and
reported as odds ratios and average marginal effects; human casualty intensity
is modelled with OLS and reported as marginal changes. Both adjust for log
gross tonnage, vessel age, calendar-month fixed effects and ocean-basin fixed
effects, with HC1 robust standard errors. Models are estimated separately under
the P95 and P99 threshold definitions; the reference category is accident days
on which neither wind nor wave exceeds the relevant threshold.

Input   config.RESTRICTED / accident_panel.parquet  (licensed, not redistributed)
Output  data_public/table1_accident_models.csv  (model summaries only)

Run:  python code/accident_models.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

PANEL = cfg.RESTRICTED / "accident_panel.parquet"
OUT = cfg.PUBLIC / "table1_accident_models.csv"

CATS = ["wind_only", "wave_only", "compound"]
REF = "non_extreme"
LABEL = {"wind_only": "Wind-only extremes", "wave_only": "Wave-only extremes",
         "compound": "Compound extremes"}
COVARIATES = "logGT + Age + C(month) + C(basin)"


def _as_cat(values):
    return pd.Categorical(values, categories=[REF] + CATS)


def fit(df, cat_col):
    """Logit for serious classification, OLS for HCI, on the same design."""
    d = df.copy()
    d["cat"] = _as_cat(d[cat_col])

    logit = smf.logit(f"serious ~ C(cat) + {COVARIATES}",
                      data=d).fit(disp=False, cov_type="HC1")
    # dummy=True gives the discrete 0->1 change in predicted probability, which
    # is what the Methods define an AME to be; the default treats the category
    # dummies as continuous and reports a derivative instead. The two agree to
    # within 0.7 percentage points here, but only the former matches the text.
    ame = logit.get_margeff(at="overall", dummy=True).summary_frame()
    ols = smf.ols(f"HCI ~ C(cat) + {COVARIATES}", data=d).fit(cov_type="HC1")

    rows = []
    for c in CATS:
        key = f"C(cat)[T.{c}]"
        b, se = logit.params[key], logit.bse[key]
        lo, hi = logit.conf_int().loc[key]
        rows.append(dict(
            category=LABEL[c],
            n=int((d["cat"] == c).sum()),
            odds_ratio=np.exp(b),
            or_lo=np.exp(lo), or_hi=np.exp(hi),
            or_p=logit.pvalues[key],
            # AMEs are reported in percentage points
            ame_pp=100 * ame.loc[key, "dy/dx"],
            ame_lo=100 * ame.loc[key, "Conf. Int. Low"],
            ame_hi=100 * ame.loc[key, "Cont. Int. Hi."],
            ame_p=ame.loc[key, "Pr(>|z|)"],
            hci=ols.params[key],
            hci_lo=ols.conf_int().loc[key, 0],
            hci_hi=ols.conf_int().loc[key, 1],
            hci_p=ols.pvalues[key],
            # cross-check: average predicted-probability difference when every
            # accident is placed in category c versus the reference
            ame_counterfactual=100 * (
                logit.predict(d.assign(cat=_as_cat([c] * len(d))))
                - logit.predict(d.assign(cat=_as_cat([REF] * len(d))))).mean(),
        ))
        _ = se
    return pd.DataFrame(rows), logit, ols


def stars(p):
    """*** p < 0.001, ** p < 0.01, * p < 0.05."""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def render(tab):
    """Print Table 1 in the manuscript's layout: estimate, stars, 95 % CI below."""
    w = (28, 20, 22, 22)
    head = ("Extreme-weather category", "Odds ratio",
            "AME (percentage points)", "AME (HCI units acc.⁻¹)")
    rule = "-" * (sum(w) + 3)
    print(f"\n{'':<{w[0]}} {'Accident severity':<{w[1]+w[2]+1}} Casualty magnitude")
    print("  ".join(h.ljust(x) for h, x in zip(head, w)))
    print(rule)

    for cat in [LABEL[c] for c in CATS]:
        print(f"{cat}")
        for _, r in tab[tab["category"] == cat].iterrows():
            est = (f"{r['odds_ratio']:.2f}{stars(r['or_p'])}",
                   f"{r['ame_pp']:.2f}{stars(r['ame_p'])}",
                   f"{r['hci']:.2f}{stars(r['hci_p'])}")
            ci = (f"[{r['or_lo']:.2f}, {r['or_hi']:.2f}]",
                  f"[{r['ame_lo']:.2f}, {r['ame_hi']:.2f}]",
                  f"[{r['hci_lo']:.2f}, {r['hci_hi']:.2f}]")
            lab = f"  {r['threshold']}  (n = {int(r['n']):,})"
            print(f"{lab:<{w[0]}}  " + "  ".join(e.ljust(x) for e, x in zip(est, w[1:])))
            print(f"{'':<{w[0]}}  " + "  ".join(c.ljust(x) for c, x in zip(ci, w[1:])))
        print()
    print(rule)


def main():
    if not PANEL.exists():
        raise SystemExit(
            f"\nThe accident panel is not present:\n    {PANEL}\n"
            "\nIt holds row-level licensed accident records and is therefore "
            "kept outside\nthis repository. Rebuild it with "
            "prepare_accident_panel.py if you hold the\n"
            "Lloyd's List Intelligence licence.\n"
            "\nThe fitted results this script produces are already provided "
            "in\n    data_public/table1_accident_models.csv\n")
    df = pd.read_parquet(PANEL)
    out = []
    for q, tag in [("p95", "Extreme"), ("p99", "Severe extreme")]:
        t, logit, ols = fit(df, f"cat_{q}")
        t.insert(0, "threshold", tag)
        t["n_obs"] = int(logit.nobs)
        t["n_reference"] = int((df[f"cat_{q}"] == REF).sum())
        t["pseudo_r2"] = logit.prsquared
        t["ols_r2"] = ols.rsquared
        out.append(t)

    tab = pd.concat(out, ignore_index=True)
    render(tab)

    n = int(tab["n_obs"].iloc[0])
    print(f"N = {n:,} open-ocean accidents. Reference category: accident days on "
          f"which neither\nwind nor wave exceeds the relevant threshold "
          f"({int(tab.loc[0, 'n_reference']):,} under P95, "
          f"{int(tab.loc[3, 'n_reference']):,} under P99).")
    print("Severity by logistic regression, casualty magnitude by OLS; both adjust "
          "for log gross\ntonnage, vessel age, calendar-month and ocean-basin fixed "
          "effects, HC1 robust errors.")
    print(f"Logit pseudo-R² {tab['pseudo_r2'].iloc[0]:.3f} / "
          f"{tab['pseudo_r2'].iloc[3]:.3f};  OLS R² "
          f"{tab['ols_r2'].iloc[0]:.4f} / {tab['ols_r2'].iloc[3]:.4f}.")
    print("*** p < 0.001, ** p < 0.01, * p < 0.05.")
    gap = (tab["ame_pp"] - tab["ame_counterfactual"]).abs().max()
    print(f"AMEs are discrete 0->1 changes; the full-counterfactual check agrees "
          f"to within {gap:.2f} pp.")

    cfg.ensure_dirs()
    tab.to_csv(OUT, index=False)
    print(f"\n    -> {OUT.name}")


if __name__ == "__main__":
    main()
