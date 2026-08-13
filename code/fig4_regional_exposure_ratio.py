"""
Figure 4a-c: projected regional changes in wind and wave exposure.

x = late-century / recent-future wind exposure ratio (Methods Eq 13),
y = the same for waves. Ratios are formed per model first and then averaged
over the five-model CMIP6 ensemble; wave ratios come from the single
continuous wave projection. Bubble area encodes 2021 basin traffic volume;
corridors use a fixed marker size.

Inputs   data_public/exposure_annual.csv, data_public/basin_traffic_2021.csv
Run      python code/fig4_regional_exposure_ratio.py
"""
import colorsys
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

sys.path.append(str(Path(__file__).resolve().parent))
import config as cfg

# --------------------------------------------------------------------------
# palette: ocean families share a colour, marginal seas get their own
# --------------------------------------------------------------------------
REGION_COLOR = {
    "NAO": ("#ad2c71", "Atlantic Ocean"), "EAO": ("#ad2c71", "Atlantic Ocean"),
    "SAO": ("#ad2c71", "Atlantic Ocean"),
    "NPO": ("#3a9e8f", "Pacific Ocean"), "EPO": ("#3a9e8f", "Pacific Ocean"),
    "SPO": ("#3a9e8f", "Pacific Ocean"),
    "ARS": ("#e8a838", "Indian Ocean"), "BOB": ("#e8a838", "Indian Ocean"),
    "EIO": ("#e8a838", "Indian Ocean"), "SIO": ("#e8a838", "Indian Ocean"),
    "CAR": ("#c5e07b", "Caribbean"), "MED": ("#2083ed", "Mediterranean"),
    "SEA": ("#5aaa5a", "Southeast Asia"), "SOO": ("#6aaed6", "Southern Ocean"),
}
CORRIDOR_COLOR = "#272ea6"
INK, INK_MUTED, SURFACE = "#1a1a19", "#8a8a80", "#ffffff"

FIGSIZE, DPI = (12.5, 8.5), 500
S_MIN, S_MAX, S_CORR = 90, 1100, 340      # bubble areas (pt^2)
PAD = 0.05                                 # axis padding as a fraction of range
EDGE_LW = 1.6
FS = dict(axis=19, tick=17, label=15, legend=14, legtitle=14, quad=13, title=20)

# label placement: side is left/right of the bubble centre, dx/dy in points
LABEL_SIDE = {"BOB": "left", "MED": "left", "NAO": "left", "NPO": "left",
              "SIO": "left", "SOO": "left", "RT-SG": "left"}
DECLUTTER_ITERS, LEADER_MIN = 60, 10


def dark_edge(hex_color, factor=0.55):
    """Same hue, lower lightness - keeps bubble edges legible without white halos."""
    h = hex_color.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return "#" + "".join(f"{round(v*255):02x}"
                         for v in colorsys.hls_to_rgb(hh, ll * factor, ss))


def size_scale(v, vmin, vmax):
    """Bubble area proportional to traffic, so radius scales with sqrt."""
    t = (np.sqrt(v) - np.sqrt(vmin)) / (np.sqrt(vmax) - np.sqrt(vmin))
    return S_MIN + np.clip(t, 0, 1) * (S_MAX - S_MIN)


def nice_size_ticks(vmin, vmax, n=4):
    out = []
    for v in np.linspace(np.sqrt(vmin), np.sqrt(vmax), n) ** 2:
        step = 10 ** np.floor(np.log10(v))
        out.append(float(np.clip(round(v / step) * step, vmin, vmax)))
    return sorted(set(out))


def fmt_traffic(v):
    if v >= 1e6:
        return f"{v/1e6:.1f}M"
    if v >= 1e3:
        return f"{v/1e3:.1f}k" if v < 1e4 else f"{v/1e3:.0f}k"
    return f"{v:.0f}"


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def build():
    a = pd.read_csv(cfg.PUBLIC / "exposure_annual.csv")

    # period mean per model, then the two-period ratio, then the ensemble mean
    pm = (a.groupby(["kind", "unit", "var", "model", "ssp", "period"], as_index=False)
            .agg(E=("E_annual", "mean"), cov=("traffic_coverage", "mean")))
    w = pm.pivot_table(index=["kind", "unit", "var", "model", "ssp"],
                       columns="period", values="E").reset_index()
    w["ratio"] = w[cfg.PERIOD_LATE] / w[cfg.PERIOD_RECENT]

    r = w.groupby(["kind", "unit", "var", "ssp"], as_index=False)["ratio"].mean()
    cov = pm.groupby(["kind", "unit", "var", "ssp"], as_index=False)["cov"].min()
    r = r.merge(cov, on=["kind", "unit", "var", "ssp"])

    d = r.pivot_table(index=["kind", "unit", "ssp"], columns="var",
                      values=["ratio", "cov"]).reset_index()
    d.columns = ["kind", "unit", "ssp", "cov_wave", "cov_wind", "r_wave", "r_wind"]

    t = (pd.read_csv(cfg.BASIN_TRAFFIC_PUBLIC)
           .rename(columns={"basin": "unit", "unique_mmsi": "ship_traffic"}))
    t["kind"] = "basin"
    d = d.merge(t[["unit", "kind", "ship_traffic"]], on=["kind", "unit"], how="left")

    d["name"] = np.where(d["kind"] == "corridor",
                         d["unit"].map(cfg.CORRIDOR_LABEL).fillna(d["unit"]),
                         d["unit"])
    return d


# --------------------------------------------------------------------------
# labelling: anchor on the bubble centre, then resolve overlaps vertically
# --------------------------------------------------------------------------
def annotate_all(fig, ax, items):
    items = sorted(items, key=lambda t: -t[2])          # place large bubbles first
    anns, offs = [], []
    effects = [pe.withStroke(linewidth=2.6, foreground=SURFACE)]

    for x, y, _s, name in items:
        right = LABEL_SIDE.get(name, "right") == "right"
        t = ax.annotate(name, (x, y), textcoords="offset points", xytext=(0, 0),
                        ha="left" if right else "right", va="center",
                        fontsize=FS["label"], color=INK, zorder=6,
                        path_effects=effects,
                        arrowprops=dict(arrowstyle="-", lw=0.7, color=INK_MUTED,
                                        shrinkA=0, shrinkB=1))
        t.arrow_patch.set_visible(False)
        anns.append(t)
        offs.append([0, 0])

    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    px2pt = 72.0 / fig.dpi
    axbb = ax.get_window_extent(rend)
    n = len(anns)

    def nudge(i, delta):
        offs[i][1] += delta
        anns[i].xyann = tuple(offs[i])
        return anns[i].get_window_extent(rend)

    for _ in range(DECLUTTER_ITERS):
        boxes = [t.get_window_extent(rend) for t in anns]
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                a, b = boxes[i], boxes[j]
                if not a.overlaps(b):
                    continue
                ov = min(a.y1, b.y1) - max(a.y0, b.y0)
                if ov <= 0:
                    continue
                step = (ov / 2 + 1) * px2pt
                up = 1 if a.y0 + a.y1 >= b.y0 + b.y1 else -1
                boxes[i] = nudge(i, up * step)
                boxes[j] = nudge(j, -up * step)
                moved = True
        for i in range(n):                              # keep labels inside the axes
            bb = boxes[i]
            if bb.y1 > axbb.y1:
                boxes[i] = nudge(i, -(bb.y1 - axbb.y1) * px2pt)
            elif bb.y0 < axbb.y0:
                boxes[i] = nudge(i, (axbb.y0 - bb.y0) * px2pt)
        if not moved:
            break

    for t, (_, oy) in zip(anns, offs):                  # leader line only if displaced
        if abs(oy) >= LEADER_MIN:
            t.arrow_patch.set_visible(True)


# --------------------------------------------------------------------------
# one panel per SSP
# --------------------------------------------------------------------------
def plot_one(d, ssp, bmin, bmax):
    sub = d[d["ssp"] == ssp]
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)

    xlo, xhi = min(sub["r_wind"].min(), 1.0), max(sub["r_wind"].max(), 1.0)
    ylo, yhi = min(sub["r_wave"].min(), 1.0), max(sub["r_wave"].max(), 1.0)
    xp, yp = (xhi - xlo) * PAD, (yhi - ylo) * PAD
    ax.set_xlim(xlo - xp, xhi + xp)
    ax.set_ylim(ylo - yp, yhi + yp)

    ax.axhline(1, color=INK_MUTED, lw=1.0, ls="--", alpha=0.7, zorder=1)
    ax.axvline(1, color=INK_MUTED, lw=1.0, ls="--", alpha=0.7, zorder=1)

    items = []
    for _, row in sub.iterrows():
        is_cor = row["kind"] == "corridor"
        color = CORRIDOR_COLOR if is_cor else REGION_COLOR.get(row["unit"],
                                                               ("#999999",))[0]
        s = S_CORR if is_cor else float(size_scale(row["ship_traffic"], bmin, bmax))
        ax.scatter(row["r_wind"], row["r_wave"], s=s, marker="D" if is_cor else "o",
                   facecolor=color, alpha=0.85, edgecolor=dark_edge(color),
                   linewidths=EDGE_LW, zorder=3)
        items.append((row["r_wind"], row["r_wave"], s, row["name"]))

    ax.set_title(ssp, fontsize=FS["title"], color=INK, pad=12)
    ax.set_xlabel("Late century / recent future wind exposure",
                  fontsize=FS["axis"], color=INK)
    ax.set_ylabel("Late century / recent future wave exposure",
                  fontsize=FS["axis"], color=INK)
    ax.tick_params(labelsize=FS["tick"], colors=INK)
    for sp in ax.spines.values():
        sp.set_color(INK_MUTED)
        sp.set_linewidth(0.9)

    for fx, fy, ha, va, txt in [
            (0.985, 0.985, "right", "top", "wind ↑ wave ↑"),
            (0.015, 0.985, "left", "top", "wind ↓ wave ↑"),
            (0.015, 0.015, "left", "bottom", "wind ↓ wave ↓"),
            (0.985, 0.015, "right", "bottom", "wind ↑ wave ↓")]:
        ax.text(fx, fy, txt, transform=ax.transAxes, fontsize=FS["quad"],
                color=INK, ha=ha, va=va, zorder=1)

    annotate_all(fig, ax, items)

    seen = {}
    for u, (c, lbl) in REGION_COLOR.items():
        if u in set(d["unit"]) and lbl not in seen:
            seen[lbl] = mpatches.Patch(facecolor=c, label=lbl, linewidth=1.0,
                                       edgecolor=dark_edge(c))
    seen["Corridor"] = mpatches.Patch(facecolor=CORRIDOR_COLOR, label="Corridor",
                                      linewidth=1.0,
                                      edgecolor=dark_edge(CORRIDOR_COLOR))
    ax.add_artist(ax.legend(handles=list(seen.values()), title="Basin / Corridor",
                            loc="upper left", bbox_to_anchor=(1.02, 1.02),
                            fontsize=FS["legend"], title_fontsize=FS["legtitle"],
                            frameon=False, borderaxespad=0))

    h = [Line2D([], [], marker="o", ls="none",
                ms=np.sqrt(size_scale(v, bmin, bmax)), mfc="#9a9a92", alpha=0.85,
                mec=dark_edge("#9a9a92"), mew=1.2, label=fmt_traffic(v))
         for v in nice_size_ticks(bmin, bmax)]
    ax.legend(handles=h, title="2021 AIS traffic volume\n(unique vessels)",
              loc="upper left", bbox_to_anchor=(1.02, 0.5), fontsize=FS["legend"],
              title_fontsize=FS["legtitle"], frameon=False, labelspacing=2,
              borderaxespad=0)

    fig.subplots_adjust(left=0.10, right=0.76, bottom=0.10, top=0.93)
    return fig


def main():
    d = build()
    print(d[["ssp", "kind", "unit", "r_wind", "r_wave", "ship_traffic"]]
          .round(3).sort_values(["ssp", "r_wind"]).to_string(index=False))

    vb = d.loc[d["kind"] == "basin", "ship_traffic"]
    bmin, bmax = vb.min(), vb.max()          # one bubble scale shared by all panels
    print(f"\nbubble scale: {bmin:,.0f} - {bmax:,.0f} unique vessels "
          f"({bmax/bmin:.1f}x)")

    for ssp in cfg.SSPS:
        plot_one(d, ssp, bmin, bmax)
    plt.show()


if __name__ == "__main__":
    main()
