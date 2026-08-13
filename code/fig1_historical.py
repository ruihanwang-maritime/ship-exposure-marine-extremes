"""
Figure 1: historical evolution (1980-2024) of extreme marine weather and ship
exposure across the global shipping system.

(a) Grid-cell trends in annual extreme-wave and extreme-wind days.
(b) 2021 AIS shipping activity, grouped by cumulative traffic contribution.
(c) Each grid cell's share of global traffic-weighted exposure.
(d) Globally aggregated annual ECDs (Eq 5) and exposure days (Eq 4), with OLS
    trends (Eq 8) and 5-year rolling means.
(e) Monthly climatology of ship exposure.

Inputs   data_public/historical_gridcell_trend.npz
         data_public/historical_exposure_share.npz
         data_public/historical_annual.csv, historical_month.csv
         data_public/footprint_global.parquet
Run      python code/fig1_historical.py
"""
import sys
from pathlib import Path

# pyarrow before cartopy - see the note in fig3
import pyarrow  # noqa: F401

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

INK, INK_MUTED = "#1a1a19", "#8a8a80"
VAR_COLOR = {"wave": "#2c6fad", "wind": "#3f7d4e"}
TREND_LIM = {"wave": 2.0, "wind": 0.8}          # days per decade, symmetric
SHARE_LIM = {"wave": 0.04, "wind": 0.05}        # % of global exposure
# cumulative-traffic bands, densest first
BANDS = [(0.00, 0.95, "#e07b1f", "0–95% (high)"),
         (0.95, 0.99, "#f2c795", "95–99% (medium)"),
         (0.99, 1.01, "#c3d3de", "99–100% (low)")]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DPI = 400


def _basemap(ax):
    ax.add_feature(cfeature.LAND, facecolor="#dededa", edgecolor="none", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.25, edgecolor="#9a9a94", zorder=3)
    ax.gridlines(linewidth=0.25, color="#c9c9c4", alpha=0.7)
    ax.set_global()
    ax.spines["geo"].set_edgecolor(INK_MUTED)
    ax.spines["geo"].set_linewidth(0.6)


def panel_a(fig, gs):
    """Grid-cell OLS trend in annual extreme days; slopes are stored per decade."""
    z = np.load(cfg.PUBLIC / "historical_gridcell_trend.npz")
    lon2d, lat2d = np.meshgrid(z["lon"], z["lat"])
    for i, var in enumerate(["wave", "wind"]):
        ax = fig.add_subplot(gs[i, 0], projection=ccrs.Robinson())
        _basemap(ax)
        v = TREND_LIM[var]
        m = ax.pcolormesh(lon2d, lat2d, z[f"slope_{var}"], cmap="RdBu_r",
                          vmin=-v, vmax=v, shading="auto",
                          transform=ccrs.PlateCarree(), zorder=1)
        ax.set_title(f"Extreme-{var} trend", fontsize=8.5, color=INK, pad=4)
        if i == 0:
            ax.text(-0.06, 1.18, "a", transform=ax.transAxes, fontsize=13,
                    fontweight="bold", color=INK)
        cb = fig.colorbar(m, ax=ax, orientation="horizontal", pad=0.04,
                          fraction=0.045, extend="both",
                          ticks=[-v, -v / 4, 0, v / 4, v])
        cb.ax.tick_params(labelsize=6.5, colors=INK)
        cb.set_label("Days decade⁻¹", fontsize=7, color=INK)
        cb.outline.set_linewidth(0.4)


def panel_b(fig, gs):
    """2021 footprint, coloured by which cumulative-traffic band a cell falls in."""
    f = pd.read_parquet(cfg.FOOTPRINT_PUBLIC)
    ax = fig.add_subplot(gs[2, 0], projection=ccrs.Robinson())
    _basemap(ax)
    lon = np.where(f["lon_bin"] >= 180, f["lon_bin"] - 360, f["lon_bin"])
    for lo, hi, col, _ in BANDS:
        m = (f["cum_share"] > lo) & (f["cum_share"] <= hi)
        ax.scatter(lon[m.to_numpy()], f.loc[m, "lat_bin"], s=0.9, marker="s",
                   color=col, transform=ccrs.PlateCarree(), linewidths=0, zorder=1)
    ax.set_title("Ship-traffic density", fontsize=8.5, color=INK, pad=4)
    ax.text(-0.06, 1.18, "b", transform=ax.transAxes, fontsize=13,
            fontweight="bold", color=INK)
    ax.legend(handles=[Patch(facecolor=c, label=l) for *_, c, l in BANDS],
              title="Cumulative ship traffic", loc="lower center",
              bbox_to_anchor=(0.5, -0.22), ncol=1, fontsize=6.5,
              title_fontsize=7, frameon=False, handlelength=1.1)


def panel_c(fig, gs):
    """Each cell's contribution to global traffic-weighted exposure."""
    z = np.load(cfg.PUBLIC / "historical_exposure_share.npz")
    lon2d, lat2d = np.meshgrid(z["lon"], z["lat"])
    for i, var in enumerate(["wave", "wind"]):
        ax = fig.add_subplot(gs[i, 1], projection=ccrs.Robinson())
        _basemap(ax)
        hi = SHARE_LIM[var]
        levels = np.linspace(0, hi, 9)
        cmap = LinearSegmentedColormap.from_list(
            var, ["#ffffff", VAR_COLOR[var], "#0d2f1c" if var == "wind" else "#08306b"])
        data = np.where(z[f"share_{var}"] > 0, z[f"share_{var}"], np.nan)
        m = ax.pcolormesh(lon2d, lat2d, data, cmap=cmap,
                          norm=BoundaryNorm(levels, cmap.N, extend="max"),
                          shading="auto", transform=ccrs.PlateCarree(), zorder=1)
        thr = "SWH ≥ 6.0 m" if var == "wave" else "U₁₀ ≥ 17.2 m s⁻¹"
        ax.set_title(f"Traffic-weighted {var} exposure ({thr})",
                     fontsize=8.5, color=INK, pad=4)
        if i == 0:
            ax.text(-0.06, 1.18, "c", transform=ax.transAxes, fontsize=13,
                    fontweight="bold", color=INK)
        cb = fig.colorbar(m, ax=ax, orientation="horizontal", pad=0.04,
                          fraction=0.045, extend="max",
                          ticks=levels[::2])
        cb.ax.tick_params(labelsize=6.5, colors=INK)
        cb.set_label("Share of global exposure (%)", fontsize=7, color=INK)
        cb.outline.set_linewidth(0.4)


def _series(ax, x, y, color, ylabel, note=None):
    """Annual values, OLS trend and 5-year rolling mean on one axis."""
    r = stats.linregress(x, y)
    ax.scatter(x, y, s=7, color="#a9a9a2", zorder=2, label="Annual values")
    ax.plot(x, r.intercept + r.slope * np.asarray(x), ls="--", lw=1.0,
            color=INK, zorder=3, label="Linear trend")
    ax.plot(x, pd.Series(y).rolling(5, center=True).mean(), lw=1.6, color=color,
            zorder=4, label="5-yr rolling mean")
    ax.set_ylabel(ylabel, fontsize=7, color=INK)
    ax.tick_params(labelsize=6.5, colors=INK)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["bottom", "left"]:
        ax.spines[sp].set_color(INK_MUTED)
    if note:
        ax.text(0.98, 0.94, note, transform=ax.transAxes, ha="right", va="top",
                fontsize=6.5, color=INK_MUTED, style="italic")
    ax.text(0.02, 0.94, f"$p$ = {r.pvalue:.4f}" if r.pvalue < 0.05
            else f"$p$ > 0.05", transform=ax.transAxes, ha="left", va="top",
            fontsize=6.5, color=INK_MUTED, style="italic")
    return r


def panel_d(fig, gs):
    a = pd.read_csv(cfg.PUBLIC / "historical_annual.csv")
    for j, var in enumerate(["wave", "wind"]):
        s = a[a["var"] == var].sort_values("year")
        ax = fig.add_subplot(gs[3, j])
        _series(ax, s["year"], s["ecd"] / 1e3, VAR_COLOR[var],
                "ECDs (×10³ grid-cell days)")
        raw = stats.linregress(s["year"], s["ecd"])
        ax.set_title("Global ocean", fontsize=7.5, color=INK, pad=3, loc="left")
        if j == 0:
            ax.text(-0.13, 1.20, "d", transform=ax.transAxes, fontsize=13,
                    fontweight="bold", color=INK)
        ax.text(0.98, 0.06, f"slope = {raw.slope:.1f} grid-cell days yr⁻¹",
                transform=ax.transAxes, ha="right", fontsize=6.5,
                color=INK_MUTED, style="italic")

        ax = fig.add_subplot(gs[4, j])
        _series(ax, s["year"], s["exposure_days"], VAR_COLOR[var],
                "Exposure (days)")
        ax.set_title("Shipping system", fontsize=7.5, color=INK, pad=3, loc="left")
        ax.set_xlabel("Year", fontsize=7, color=INK)
        if j == 0:
            ax.legend(fontsize=6, frameon=False, loc="lower left", ncol=3,
                      bbox_to_anchor=(0.0, -0.55))


def panel_e(fig, gs):
    """Monthly climatology, drawn as an annotated one-row heatmap per variable."""
    m = pd.read_csv(cfg.PUBLIC / "historical_month.csv")
    clim = (m.groupby(["var", "month"])["exposure_days"].mean()
             .unstack("month").reindex(columns=range(1, 13)))
    for j, var in enumerate(["wave", "wind"]):
        ax = fig.add_subplot(gs[5, j])
        v = clim.loc[var].to_numpy()[None, :]
        cmap = LinearSegmentedColormap.from_list(
            var, ["#ffffff", VAR_COLOR[var]])
        ax.imshow(v, cmap=cmap, aspect="auto", vmin=0, vmax=v.max() * 1.05)
        for k, val in enumerate(v[0]):
            ax.text(k, 0, f"{val:.2f}", ha="center", va="center", fontsize=6.5,
                    color=INK)
        ax.set_xticks(range(12))
        ax.set_xticklabels(MONTHS, fontsize=6.5, color=INK)
        ax.set_yticks([])
        ax.set_title(f"{var.capitalize()} exposure (days month⁻¹)",
                     fontsize=7.5, color=INK, pad=4, loc="left")
        if j == 0:
            ax.text(-0.13, 1.55, "e", transform=ax.transAxes, fontsize=13,
                    fontweight="bold", color=INK)
        for sp in ax.spines.values():
            sp.set_visible(False)


def main():
    fig = plt.figure(figsize=(11, 14), dpi=DPI)
    gs = fig.add_gridspec(6, 2, height_ratios=[1.5, 1.5, 1.5, 1, 1, 0.4],
                          hspace=0.55, wspace=0.18,
                          left=0.07, right=0.97, top=0.965, bottom=0.045)
    panel_a(fig, gs)
    panel_b(fig, gs)
    panel_c(fig, gs)
    panel_d(fig, gs)
    panel_e(fig, gs)
    a = pd.read_csv(cfg.PUBLIC / "historical_annual.csv")
    for var in ["wave", "wind"]:
        s = a[a["var"] == var]
        r = stats.linregress(s["year"], s["ecd"])
        print(f"  {var}: ECD slope {r.slope:7.1f} cell-days/yr, p = {r.pvalue:.4f}; "
              f"exposure {s['exposure_days'].min():.2f}-{s['exposure_days'].max():.2f} days/yr")
    plt.show()


if __name__ == "__main__":
    main()
