"""
Figure 3: projected wind and wave exposure across four major shipping corridors.

(a) The fixed 2021 traffic footprint of each corridor on the 1 deg grid, shaded
    by within-corridor traffic intensity.
(b) Per corridor: annual exposure days over 2030-2100 (one tick per model-year,
    bold marker at the SSP mean) and service-life exposure by delivery cohort
    (Methods Eq 9).

Inputs   data_public/density_corridor_month.parquet
         data_public/exposure_fixed_annual.csv
Run      python code/fig3_corridor_exposure.py
"""
import sys
from pathlib import Path

# pyarrow must be imported before cartopy: cartopy pulls in GEOS/PROJ shared
# libraries that shadow one of pyarrow's, and the parquet engine then fails to
# load. Importing it first pins the working copy.
import pyarrow  # noqa: F401

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg
from service_life_exposure import cohort_sum, load_fixed          # noqa: E402

CORRIDOR_COLOR = {"NE_ASIA_LALB": "#e08a3c", "SG_RT": "#2f8f6f",
                  "RT_NY": "#c964a0", "NE_ASIA_SG": "#4a9fd8"}
CORRIDOR_SUB = {"NE_ASIA_LALB": "Yangtze River Delta–\nLos Angeles / Long Beach",
                "SG_RT": "Rotterdam–\nSingapore",
                "RT_NY": "Rotterdam–\nNew York",
                "NE_ASIA_SG": "Yangtze River Delta–\nSingapore"}
ROW_ORDER = ["NE_ASIA_LALB", "SG_RT", "RT_NY", "NE_ASIA_SG"]
SSP_COLOR = {"SSP1-2.6": "#3b8fc4", "SSP2-4.5": "#e8912a", "SSP5-8.5": "#d4483b"}
DELIVERY_YEARS = list(range(2030, 2071, 10))
INK, INK_MUTED = "#1a1a19", "#8a8a80"
DPI = 500


# --------------------------------------------------------------------------
# panel a
# --------------------------------------------------------------------------
def corridor_footprints():
    """Annual weight per cell = the 12 monthly weights summed within a corridor."""
    d = pd.read_parquet(cfg.DENSITY_CORRIDOR)
    ann = (d.groupby(["corridor", "lon_bin", "lat_bin"], as_index=False)["w_month"]
             .sum().rename(columns={"w_month": "w_annual"}))
    # lon_bin is 0-360; shift to -180..180 for plotting
    ann["lon"] = np.where(ann["lon_bin"] >= 180, ann["lon_bin"] - 360, ann["lon_bin"])
    return ann


def panel_a(ax, ann):
    ax.set_extent([-180, 180, -20, 70], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="#e9e9e6", edgecolor="none", zorder=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.3, edgecolor="#b8b8b2", zorder=2)

    for c in ROW_ORDER:
        sub = ann[ann["corridor"] == c]
        base = CORRIDOR_COLOR[c]
        cmap = LinearSegmentedColormap.from_list(c, ["#ffffff", base])
        # rank-based shading: absolute weights span orders of magnitude, so a
        # linear scale would render everything but the busiest cells invisible
        r = sub["w_annual"].rank(pct=True)
        ax.scatter(sub["lon"], sub["lat_bin"], s=3.2, marker="s",
                   c=cmap(0.25 + 0.75 * r), transform=ccrs.PlateCarree(),
                   linewidths=0, zorder=3)

    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="#d5d5d0", alpha=0.8)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = gl.ylabel_style = dict(size=8, color=INK_MUTED)

    handles = [Line2D([], [], marker="s", ls="none", ms=7,
                      color=CORRIDOR_COLOR[c], label=cfg.CORRIDOR_LABEL[c])
               for c in ROW_ORDER]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(1.005, 0.0),
              fontsize=9, frameon=False, borderaxespad=0, handletextpad=0.6)


# --------------------------------------------------------------------------
# panel b
# --------------------------------------------------------------------------
def rug(ax, sub, corridor):
    """One tick per model-year value, bold marker and label at each SSP mean."""
    for k, ssp in enumerate(cfg.SSPS):
        v = sub.loc[sub["ssp"] == ssp, "E_annual"].to_numpy()
        if not v.size:
            continue
        y = 2 - k
        ax.vlines(v, y - 0.32, y + 0.32, color=SSP_COLOR[ssp], lw=0.35, alpha=0.5)
        m = v.mean()
        ax.vlines(m, y - 0.45, y + 0.45, color=SSP_COLOR[ssp], lw=2.4, zorder=3)
        ax.annotate(f"{m:.2f}", (m, y - 0.5), textcoords="offset points",
                    xytext=(0, -2), ha="center", va="top", fontsize=7.5,
                    color=SSP_COLOR[ssp], zorder=4)
    ax.set_ylim(-0.9, 2.9)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=7.5)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(INK_MUTED)


def cohorts(ax, sub):
    """Service-life exposure by delivery year, ensemble mean across models."""
    for ssp in cfg.SSPS:
        rows = []
        for model, g in sub[sub["ssp"] == ssp].groupby("model"):
            s = g.set_index("year")["E_annual"].sort_index()
            rows.append([cohort_sum(s, y0) for y0 in DELIVERY_YEARS])
        if not rows:
            continue
        m = np.nanmean(np.array(rows, dtype=float), axis=0)
        ax.plot(DELIVERY_YEARS, m, color=SSP_COLOR[ssp], lw=1.5, marker="o", ms=4)
        for x, y in zip(DELIVERY_YEARS, m):
            ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=7,
                        color=SSP_COLOR[ssp])
    ax.set_xticks(DELIVERY_YEARS)
    ax.tick_params(labelsize=7.5)
    ax.grid(axis="y", color=INK_MUTED, alpha=0.22, lw=0.5)
    ax.set_axisbelow(True)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["bottom", "left"]:
        ax.spines[sp].set_color(INK_MUTED)


def main():
    df = load_fixed()
    corr = df[(df["scale"] == "corridor") & (df["year"].between(2030, 2100))]

    fig = plt.figure(figsize=(15, 15), dpi=DPI)
    gs = fig.add_gridspec(5, 4, height_ratios=[2.5, 1, 1, 1, 1],
                          hspace=0.42, wspace=0.28,
                          left=0.13, right=0.94, top=0.96, bottom=0.05)

    panel_a(fig.add_subplot(gs[0, :], projection=ccrs.PlateCarree()),
            corridor_footprints())

    col_titles = ["Annual wind\nexposure days", "Annual wave\nexposure days",
                  "Service-life wind\nexposure days", "Service-life wave\nexposure days"]
    for i, c in enumerate(ROW_ORDER):
        for j, (var, kind) in enumerate([("wind", "rug"), ("wave", "rug"),
                                         ("wind", "cohort"), ("wave", "cohort")]):
            ax = fig.add_subplot(gs[i + 1, j])
            sub = corr[(corr["unit"] == c) & (corr["var"] == var)]
            rug(ax, sub, c) if kind == "rug" else cohorts(ax, sub)
            if i == 0:
                ax.set_title(col_titles[j], fontsize=9, color=INK, pad=8)
            if i == len(ROW_ORDER) - 1 and kind == "cohort":
                ax.set_xlabel("Ship delivery year", fontsize=8.5, color=INK)
            if j == 0:
                ax.text(-0.30, 0.5, cfg.CORRIDOR_LABEL[c], transform=ax.transAxes,
                        ha="right", va="center", fontsize=10, color=INK,
                        fontweight="bold")
                ax.text(-0.30, 0.16, CORRIDOR_SUB[c], transform=ax.transAxes,
                        ha="right", va="center", fontsize=7, color=INK_MUTED)
                ax.scatter([-0.36], [0.5], s=90, marker="s",
                           color=CORRIDOR_COLOR[c], transform=ax.transAxes,
                           clip_on=False)

    fig.legend(handles=[Line2D([], [], color=SSP_COLOR[s], lw=2, label=s)
                        for s in cfg.SSPS],
               loc="lower center", ncol=3, fontsize=9.5, frameon=False,
               bbox_to_anchor=(0.53, 0.005))
    fig.text(0.02, 0.965, "a", fontsize=15, fontweight="bold", color=INK)
    fig.text(0.02, 0.70, "b", fontsize=15, fontweight="bold", color=INK)

    print(corr.groupby(["unit", "var", "ssp"])["E_annual"].mean()
              .unstack().round(2).to_string())
    plt.show()


if __name__ == "__main__":
    main()
