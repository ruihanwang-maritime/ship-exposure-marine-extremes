"""
Extended Data Figure 3: projected annual global shipping exposure, 2030-2100.

Upper panel, wind: faint dotted lines are the individual CMIP6 models, solid
lines the five-model ensemble mean smoothed with a 5-year rolling window.
Lower panel, wave: the single continuous projection product, so the spread
shown is temporal variability rather than inter-model uncertainty.

Inputs   data_public/exposure_fixed_annual.csv
Run      python code/ed_fig3_annual_projection.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

SSP_COLOR = {"SSP1-2.6": "#3b8fc4", "SSP2-4.5": "#e8912a", "SSP5-8.5": "#d4483b"}
INK, INK_MUTED = "#1a1a19", "#8a8a80"
YEARS = (2030, 2100)
ROLL = 5
DPI = 400


def main():
    d = pd.read_csv(cfg.PUBLIC / "exposure_fixed_annual.csv")
    d = d[(d["scale"] == "global") & (d["year"].between(*YEARS))]

    fig, axes = plt.subplots(2, 1, figsize=(9, 7.5), dpi=DPI, sharex=True)
    for ax, var in zip(axes, ["wind", "wave"]):
        sub = d[d["var"] == var]
        for ssp in cfg.SSPS:
            s = sub[sub["ssp"] == ssp]
            c = SSP_COLOR[ssp]
            # ensemble-mean annual value, then its 5-year rolling mean; the
            # wave product has a single model, so the mean is a pass-through
            m = (s.groupby("year", as_index=False)["E_annual"].mean()
                  .sort_values("year"))
            ax.plot(m["year"], m["E_annual"], ls=":", lw=0.7, color=c,
                    alpha=0.55, zorder=1)
            ax.scatter(m["year"], m["E_annual"], s=6, color=c, alpha=0.55,
                       linewidths=0, zorder=2)
            ax.plot(m["year"], m["E_annual"].rolling(ROLL, center=True).mean(),
                    lw=2.0, color=c, zorder=3)

        ax.set_ylabel(f"Annual {var} exposure days", fontsize=11, color=INK)
        ax.tick_params(labelsize=9.5, colors=INK)
        ax.grid(color=INK_MUTED, alpha=0.2, lw=0.5, ls=":")
        ax.set_axisbelow(True)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        for sp in ["bottom", "left"]:
            ax.spines[sp].set_color(INK_MUTED)

    axes[1].set_xlabel("Year", fontsize=11, color=INK)
    handles = [Line2D([], [], color=SSP_COLOR[s], lw=2, label=s) for s in cfg.SSPS]
    handles += [Line2D([], [], color=INK_MUTED, lw=0.8, ls=":", marker="o", ms=3,
                       label="Annual exposure days"),
                Line2D([], [], color=INK_MUTED, lw=2, label=f"{ROLL}-year rolling mean")]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 0.005))
    fig.subplots_adjust(left=0.10, right=0.97, top=0.97, bottom=0.12, hspace=0.10)

    for var in ["wind", "wave"]:
        s = d[d["var"] == var].groupby("ssp")["E_annual"]
        print(f"  {var}: " + "   ".join(
            f"{k} {v.mean():.3f}"
            for k, v in s))
    plt.show()


if __name__ == "__main__":
    main()
