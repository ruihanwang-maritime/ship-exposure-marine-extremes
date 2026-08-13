"""
Figure 2: projected global shipping exposure under three SSPs.

(a) Annual wind-exposure days in the recent future (2030-2054) versus the late
    century (2076-2100), one row per CMIP6 model plus the ensemble mean.
(b) Service-life exposure by delivery cohort (Methods Eq 9), wind with the
    inter-model SD, wave from the single continuous projection.

Inputs   data_public/exposure_fixed_annual.csv
Run      python code/fig2_global_projection.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg
from service_life_exposure import load_fixed, service_life          # noqa: E402

SSP_COLOR = {"SSP1-2.6": "#3b8fc4", "SSP2-4.5": "#e8912a", "SSP5-8.5": "#d4483b"}
MODEL_LABEL = {"access_cm2": "ACCESS-CM2", "cmcc_cm2_sr5": "CMCC-CM2",
               "ipsl_cm6a_lr": "IPSL-CM6A", "mpi_esm1_2_lr": "MPI-ESM1",
               "mri_esm2_0": "MRI-ESM2"}
MODEL_ORDER = list(MODEL_LABEL)
INK, INK_MUTED = "#1a1a19", "#8a8a80"
DPI = 500


def period_means(df):
    """Per-model annual wind exposure averaged over each of the two windows."""
    g = df[(df["scale"] == "global") & (df["var"] == "wind")]
    lo, hi = cfg.PERIOD_RECENT.split("-"), cfg.PERIOD_LATE.split("-")
    recent = g[g["year"].between(int(lo[0]), int(lo[1]))]
    late = g[g["year"].between(int(hi[0]), int(hi[1]))]
    out = (recent.groupby(["model", "ssp"], as_index=False)["E_annual"].mean()
                 .rename(columns={"E_annual": "recent"})
           .merge(late.groupby(["model", "ssp"], as_index=False)["E_annual"].mean()
                      .rename(columns={"E_annual": "late"}), on=["model", "ssp"]))
    return out


def panel_a(fig, gs, pm):
    """One column per SSP: dumbbell per model, ensemble mean below the divider."""
    axes = []
    for j, ssp in enumerate(cfg.SSPS):
        ax = fig.add_subplot(gs[0, j])
        sub = pm[pm["ssp"] == ssp].set_index("model")
        color = SSP_COLOR[ssp]

        def dumbbell(r, l, y, ms, lw, fmt, fs):
            """Endpoints label outwards, so near-identical values never collide."""
            ax.plot([r, l], [y, y], color=color, lw=lw, zorder=1)
            ax.scatter([r], [y], s=ms, facecolor="white", edgecolor=color,
                       lw=lw * 1.1, zorder=2)
            ax.scatter([l], [y], s=ms, color=color, zorder=2)
            for v, other in ((r, l), (l, r)):
                out = -1 if v <= other else 1
                ax.annotate(format(v, fmt), (v, y), xytext=(6 * out, -11),
                            textcoords="offset points", fontsize=fs,
                            ha="right" if out < 0 else "left", color=INK)

        for i, m in enumerate(MODEL_ORDER):
            dumbbell(sub.loc[m, "recent"], sub.loc[m, "late"],
                     len(MODEL_ORDER) - i, 55, 1.6, ".2f", 7.5)

        r, l = sub["recent"].mean(), sub["late"].mean()
        dumbbell(r, l, -0.5, 170, 3.0, ".3f", 8)
        ax.annotate(f"{100*(l/r-1):+.2f}%", ((r + l) / 2, -0.5), xytext=(0, 11),
                    fontsize=8.5, textcoords="offset points", ha="center",
                    color=INK)
        ax.axhline(0.35, color=INK_MUTED, lw=0.7, ls=":")

        ax.set_title(ssp, fontsize=11, color=INK, pad=16)
        ax.set_ylim(-1.5, len(MODEL_ORDER) + 0.8)
        ax.set_yticks(list(range(1, len(MODEL_ORDER) + 1)) + [-0.5])
        ax.set_yticklabels([MODEL_LABEL[m] for m in MODEL_ORDER][::-1]
                           + ["Ensemble mean"], fontsize=8.5)
        if j:
            ax.set_yticklabels([])
        ax.tick_params(axis="x", labelsize=8)
        for sp in ["top", "right", "left"]:
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(INK_MUTED)
        axes.append(ax)

    lo = min(a.get_xlim()[0] for a in axes)
    hi = max(a.get_xlim()[1] for a in axes)
    for a in axes:
        a.set_xlim(lo, hi)
    axes[0].set_xlabel("Annual wind exposure (days)", fontsize=9.5, color=INK)
    return axes


def panel_b(fig, gs, ens):
    """Service-life exposure by delivery cohort; wind carries inter-model SD."""
    for j, var in enumerate(["wind", "wave"]):
        ax = fig.add_subplot(gs[1, j])
        sub = ens[ens["var"] == var]
        # stagger the three scenarios horizontally so labels and error bars
        # stay readable where the lines nearly coincide
        for k, ssp in enumerate(cfg.SSPS):
            s = sub[sub["ssp"] == ssp].sort_values("delivery_year")
            if s.empty:
                continue
            dx = (k - 1) * (1.4 if var == "wind" else 0.0)
            x = s["delivery_year"] + dx
            ax.plot(x, s["L_mean"], color=SSP_COLOR[ssp], lw=1.8, marker="o",
                    ms=5, label=ssp, zorder=2)
            if var == "wind" and s["L_sd"].notna().any():
                ax.errorbar(x, s["L_mean"], yerr=s["L_sd"], fmt="none",
                            ecolor=SSP_COLOR[ssp], elinewidth=1.1, capsize=3,
                            alpha=0.75, zorder=1)
            side = 1 if k != 2 else -1          # SSP5-8.5 labels sit below its line
            for xi, yi in zip(x, s["L_mean"]):
                ax.annotate(f"{yi:.1f}", (xi, yi), xytext=(0, 9 * side),
                            textcoords="offset points", fontsize=7.5,
                            ha="center", va="bottom" if side > 0 else "top",
                            color=SSP_COLOR[ssp])

        ax.set_xlabel("Ship delivery year", fontsize=9.5, color=INK)
        ax.set_ylabel(f"Service-life {var} exposure (days)", fontsize=9.5, color=INK)
        ax.set_xticks(sorted(sub["delivery_year"].unique()))
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", color=INK_MUTED, alpha=0.25, lw=0.6)
        ax.set_axisbelow(True)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        for sp in ["bottom", "left"]:
            ax.spines[sp].set_color(INK_MUTED)
        if j == 0:
            ax.legend(fontsize=8.5, frameon=False, loc="best")


def main():
    df = load_fixed()
    pm = period_means(df)
    _, ens = service_life(df)

    fig = plt.figure(figsize=(12.5, 10), dpi=DPI)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1], hspace=0.34, wspace=0.22)
    panel_a(fig, gs, pm)
    panel_b(fig, gs, ens)
    fig.text(0.02, 0.965, "a", fontsize=15, fontweight="bold", color=INK)
    fig.text(0.02, 0.46, "b", fontsize=15, fontweight="bold", color=INK)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.94, bottom=0.07)

    print(pm.pivot(index="model", columns="ssp",
                   values=["recent", "late"]).round(3).to_string())
    plt.show()


if __name__ == "__main__":
    main()
