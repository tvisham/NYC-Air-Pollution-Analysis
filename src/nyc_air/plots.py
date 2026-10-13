"""One figure per finding, in a single consistent style.

Maps are drawn with plain matplotlib from the GeoJSON rings (see data.load_neighborhoods),
so no GIS libraries are needed.
"""

from __future__ import annotations

import math

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize

# Palette -------------------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
NO_DATA = "#d9d8d4"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
TREND = "#8a8984"

BLUES = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
ORANGES = LinearSegmentedColormap.from_list(
    "seq_orange", ["#fde3d6", "#f8bfa3", "#f39a72", "#eb6834", "#c94f1f", "#9c3b14", "#6e290d"])

NYC_LAT = 40.7  # for an equal-area-ish aspect ratio on lon/lat maps


def use_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
        "axes.edgecolor": GRID, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlepad": 10, "legend.frameon": False,
        "savefig.dpi": 200, "savefig.bbox": "tight",
    })


def _title(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.suptitle(title, x=0.01, ha="left", fontsize=14, fontweight="bold", y=1.0)
    fig.text(0.01, 0.955, subtitle, ha="left", va="top", fontsize=10.5, color=INK_2)


def _source_note(fig: plt.Figure, text: str = "Source: NYC Open Data, Air Quality (NYC DOHMH)") -> None:
    fig.text(0.01, 0.005, text, ha="left", va="bottom", fontsize=8.5, color=INK_2)


# Finding 1 + 2: trend and the 2023 break --------------------------------------

def trend_chart(trend: dict, smoke: dict) -> plt.Figure:
    pm, summer = trend["pm25"], smoke["summer"]
    fig, ax = plt.subplots(figsize=(9, 5))

    years = np.arange(summer.index.min(), 2024)
    fit = smoke["trend_slope"] * years + smoke["trend_intercept"]
    ax.plot(years, fit, color=TREND, lw=1.4, ls=(0, (4, 3)), zorder=1,
            label="Summer trend, 2009–2022")

    ax.plot(summer.index, summer.values, color=ORANGE, lw=2, marker="o", ms=4.5,
            mec=SURFACE, mew=1.2, zorder=3, label="Summer average")
    ax.plot(pm.index, pm.values, color=BLUE, lw=2, marker="o", ms=4.5,
            mec=SURFACE, mew=1.2, zorder=3, label="Annual average")

    y23 = smoke["actual"]
    ax.annotate(f"Summer 2023: {y23:.1f}\n{smoke['above_trend_pct']:.0f}% above trend",
                xy=(2023, y23), xytext=(2019.6, 10.6), fontsize=9.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
    ax.annotate(f"{trend['pm25_low_year']} low: {trend['pm25_low']:.1f}",
                xy=(trend["pm25_low_year"], trend["pm25_low"]),
                xytext=(2019.2, 4.9), fontsize=9.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
    ax.annotate(f"{trend['first_year']}: {trend['pm25_first']:.1f}",
                xy=(trend["first_year"], trend["pm25_first"]), xytext=(2009.6, 7.6),
                fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))

    ax.set_ylim(4, 13)
    ax.set_xlim(2008.5, 2024.6)
    ax.set_xticks(range(2009, 2025, 3))
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.legend(loc="upper right", ncols=3, bbox_to_anchor=(1, 1.02), fontsize=9.5)
    _title(fig, f"NYC's fine-particle pollution fell {abs(trend['pm25_drop_to_low_pct']):.0f}%, "
                "then summer 2023 broke the trend",
           "Citywide PM2.5, 2009–2024. June 2023 brought heavy smoke from Canadian wildfires.")
    fig.subplots_adjust(top=0.86, bottom=0.12)
    _source_note(fig)
    return fig


# Maps ---------------------------------------------------------------------------

def _draw_map(ax: plt.Axes, hoods: list[dict], ids: pd.Series, values: pd.Series,
              cmap, label: str, fmt: str = "{x:.0f}") -> None:
    """Fill each neighborhood by `values` (indexed by neighborhood name)."""
    value_by_id = {int(ids[name]): v for name, v in values.items() if name in ids.index}
    norm = Normalize(vmin=float(values.min()), vmax=float(values.max()))
    polys, colors = [], []
    for h in hoods:
        v = value_by_id.get(h["id"])
        for ring in h["polygons"]:
            polys.append(np.asarray(ring)[:, :2])
            colors.append(cmap(norm(v)) if v is not None else NO_DATA)
    ax.add_collection(PolyCollection(polys, facecolors=colors, edgecolors=SURFACE,
                                     linewidths=0.6))
    ax.autoscale_view()
    ax.set_aspect(1 / math.cos(math.radians(NYC_LAT)))
    ax.axis("off")
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    cb = plt.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.045, pad=0.02,
                      shrink=0.8, format=mpl.ticker.StrMethodFormatter(fmt))
    cb.outline.set_visible(False)
    cb.set_label(label, color=INK_2, fontsize=9.5)
    cb.ax.tick_params(colors=INK_2, labelsize=9, length=0)


def _label_places(ax, hoods, ids, names, short=None, offsets=None):
    """Name a few neighborhoods. `offsets` (lon, lat deltas) moves a label off the
    map with a leader line so labels never sit on top of each other."""
    short, offsets = short or {}, offsets or {}
    by_id = {h["id"]: h for h in hoods}
    for name in names:
        h = by_id.get(int(ids[name]))
        if h is None:
            continue
        ring = np.asarray(max(h["polygons"], key=len))[:, :2]
        xy = (ring[:, 0].min() + ring[:, 0].max()) / 2, (ring[:, 1].min() + ring[:, 1].max()) / 2
        text = short.get(name, name)
        if name in offsets:
            dx, dy = offsets[name]
            ax.annotate(text, xy=xy, xytext=(xy[0] + dx, xy[1] + dy), fontsize=8.5, color=INK,
                        ha="right" if dx < 0 else "left", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
        else:
            ax.text(*xy, text, fontsize=8.5, color=INK, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none", alpha=0.85))


def smoke_map(smoke: dict, hoods: list[dict], ids: pd.Series) -> plt.Figure:
    change = smoke["neighborhood_change"]
    fig, ax = plt.subplots(figsize=(7.2, 7.6))
    _draw_map(ax, hoods, ids, change, BLUES, "Change in summer PM2.5, 2022 → 2023", "+{x:.0f}%")
    lo, hi = change.idxmin(), change.idxmax()
    _label_places(ax, hoods, ids, [lo, hi], offsets={lo: (-0.09, 0.02), hi: (0.02, -0.05)})
    _title(fig, f"Summer 2023 was worse in all {smoke['n_neighborhoods']} neighborhoods",
           f"Rise ranged from +{smoke['change_min']:.0f}% ({lo}) "
           f"to +{smoke['change_max']:.0f}% ({hi})")
    fig.subplots_adjust(top=0.9, bottom=0.1)
    _source_note(fig, "Source: NYC Open Data, Air Quality (NYC DOHMH). "
                      "Boundaries: NYC DOHMH EHDP, UHF42 neighborhoods.")
    return fig


# Finding 3: sources ----------------------------------------------------------------

def sources_chart(src: dict) -> plt.Figure:
    pm = src["pollutants"]["PM2.5"]
    panels = [("Traffic (all vehicles)", "Traffic density\n(million vehicle-miles per sq mi)"),
              ("Building boilers (PM2.5)", "Boiler PM2.5 emissions\n(tons per sq km)")]
    table = src["table"].set_index(["pollutant", "source"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    for ax, (key, xlabel) in zip(axes, panels):
        x = src["sources"][key]
        pair = pd.concat([x.rename("x"), pm.rename("y")], axis=1).dropna()
        b, a = np.polyfit(pair.x, pair.y, 1)
        xs = np.linspace(pair.x.min(), pair.x.max(), 50)
        ax.plot(xs, a + b * xs, color=TREND, lw=1.4, ls=(0, (4, 3)), zorder=1)
        ax.scatter(pair.x, pair.y, s=42, color=BLUE, edgecolor=SURFACE, linewidth=1.2, zorder=3)
        r = table.loc[("PM2.5", key), "r"]
        ax.set_title(f"{key.split(' (')[0]}: r = {r:.2f}", fontsize=11.5)
        ax.set_xlabel(xlabel)
        # ring the two most polluted neighborhoods and explain them in one note
        top2 = pair.y.nlargest(2).index
        ax.scatter(pair.x[top2], pair.y[top2], s=130, facecolor="none",
                   edgecolor=INK_2, linewidth=1, zorder=4)
    axes[0].set_ylabel(f"Annual PM2.5, {src['year']} (µg/m³)")
    top2 = pm.nlargest(2).index
    axes[0].text(0.98, 0.04, "Circled, both in\nMidtown Manhattan:\n" + "\n".join(top2),
                 transform=axes[0].transAxes, ha="right", va="bottom", fontsize=8.5, color=INK_2)
    _title(fig, "Pollution is highest where traffic and building heating are densest",
           f"Each dot is one of 42 neighborhoods, {src['year']}. Traffic and boiler emissions "
           f"are themselves correlated (r = {src['traffic_vs_boilers_r']:.2f}).")
    fig.subplots_adjust(top=0.8, bottom=0.2, wspace=0.08)
    _source_note(fig)
    return fig


# Finding 4: burden ---------------------------------------------------------------

def burden_maps(burden: dict, hoods: list[dict], ids: pd.Series) -> plt.Figure:
    t = burden["table"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 6.2))
    _draw_map(axes[0], hoods, ids, t["pm25"], BLUES,
              "Average PM2.5, 2017–2019 (µg/m³)", "{x:.1f}")
    axes[0].set_title("Exposure", fontsize=12)
    _draw_map(axes[1], hoods, ids, t["child_asthma_ed"], ORANGES,
              "Child asthma ER visits caused by PM2.5\n(per 100,000 children per year)", "{x:.0f}")
    axes[1].set_title("Harm", fontsize=12)
    top = burden["top_child_ed"].index[:2].tolist()
    _label_places(axes[1], hoods, ids, top, offsets={top[0]: (-0.12, 0.0), top[1]: (0.12, -0.03)})
    _title(fig, "The neighborhoods hurt most are not the most polluted",
           f"PM2.5 varies {burden['exposure_ratio']:.1f}× across neighborhoods; "
           f"PM2.5-caused child asthma ER visits vary {burden['child_ed_ratio']:.0f}×")
    fig.subplots_adjust(top=0.84, bottom=0.13, wspace=0.05)
    _source_note(fig, "Source: NYC Open Data, Air Quality (NYC DOHMH). "
                      "Boundaries: NYC DOHMH EHDP, UHF42 neighborhoods.")
    return fig
