"""The four findings, each as a function that returns plain numbers and tables.

1. trend       How much cleaner the air has become citywide since 2009.
2. smoke_2023  How far summer 2023 broke from that trend, and whether it hit every neighborhood.
3. sources     Which local emission sources track neighborhood pollution levels.
4. burden      Whether the most polluted neighborhoods carry the most health burden.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import data as d

FIRST_YEAR = 2009
SMOKE_YEAR = 2023
SOURCE_YEAR = "2019"                       # latest year with traffic AND boiler data
HEALTH_PERIOD = "2017-2019"                # latest health-impact estimates
HEALTH_EXPOSURE_YEARS = ["2017", "2018", "2019"]


def pct_change(old: float, new: float) -> float:
    return (new / old - 1) * 100


# 1. Long-term trend -----------------------------------------------------------

def trend(df: pd.DataFrame) -> dict:
    """Citywide annual PM2.5 and NO2, and summer ozone, from 2009 to the latest year."""
    pm = d.citywide_series(df, d.PM25, "Annual mean")
    no2 = d.citywide_series(df, d.NO2, "Annual mean")
    ozone = d.citywide_series(df, d.OZONE, "Summer mean")
    low_year = int(pm.idxmin())
    last = int(pm.index.max())
    return {
        "pm25": pm, "no2": no2, "ozone": ozone,
        "first_year": FIRST_YEAR, "last_year": last, "pm25_low_year": low_year,
        "pm25_first": pm[FIRST_YEAR], "pm25_low": pm[low_year], "pm25_last": pm[last],
        "pm25_drop_to_low_pct": pct_change(pm[FIRST_YEAR], pm[low_year]),
        "pm25_drop_to_last_pct": pct_change(pm[FIRST_YEAR], pm[last]),
        "no2_first": no2[FIRST_YEAR], "no2_last": no2[last],
        "no2_drop_pct": pct_change(no2[FIRST_YEAR], no2[last]),
        "ozone_2010": ozone[2010], "ozone_last": ozone[last],
    }


# 2. The 2023 smoke season -----------------------------------------------------

def smoke_2023(df: pd.DataFrame) -> dict:
    """Compare summer 2023 PM2.5 with the 2009-2022 summer trend and with summer 2022.

    The expected 2023 value is a straight-line fit to summers 2009-2022. Summer means
    are seasonal averages, so this shows the season as a whole, not single smoke days.
    """
    summer = d.citywide_series(df, d.PM25, "Summer mean")
    base = summer[summer.index < SMOKE_YEAR]
    slope, intercept = np.polyfit(base.index, base.values, 1)
    expected = slope * SMOKE_YEAR + intercept
    actual = summer[SMOKE_YEAR]

    s22 = d.by_neighborhood(df, d.PM25, measure="Summer mean", period=str(SMOKE_YEAR - 1))
    s23 = d.by_neighborhood(df, d.PM25, measure="Summer mean", period=str(SMOKE_YEAR))
    change = ((s23 / s22 - 1) * 100).rename("summer_change_pct").dropna()

    return {
        "summer": summer, "trend_slope": slope, "trend_intercept": intercept,
        "expected": expected, "actual": actual,
        "above_trend_pct": pct_change(expected, actual),
        "vs_prior_summer_pct": pct_change(summer[SMOKE_YEAR - 1], actual),
        "highest_summer_since": int(summer[(summer.index < SMOKE_YEAR)
                                           & (summer >= actual)].index.max())
        if (summer[summer.index < SMOKE_YEAR] >= actual).any() else None,
        "neighborhood_change": change.sort_values(),
        "n_neighborhoods": int(change.size),
        "n_rose": int((change > 0).sum()),
        "change_min": change.min(), "change_median": change.median(),
        "change_max": change.max(),
    }


# 3. Local sources -------------------------------------------------------------

SOURCES = {
    "Traffic (all vehicles)": d.TRAFFIC,
    "Traffic (cars)": d.TRAFFIC_CARS,
    "Traffic (trucks)": d.TRAFFIC_TRUCKS,
    "Building boilers (PM2.5)": d.BOILER_PM25,
    "Building boilers (NOx)": d.BOILER_NOX,
}


def correlate(x: pd.Series, y: pd.Series) -> dict:
    pair = pd.concat([x, y], axis=1, join="inner").dropna()
    r, p = stats.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
    rho, _ = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    return {"n": len(pair), "r": r, "p": p, "spearman": rho}


def sources(df: pd.DataFrame, year: str = SOURCE_YEAR) -> dict:
    """Correlate each source with PM2.5 and NO2 across the 42 neighborhoods, same year."""
    pollutants = {
        "PM2.5": d.by_neighborhood(df, d.PM25, measure="Annual mean", period=year),
        "NO2": d.by_neighborhood(df, d.NO2, measure="Annual mean", period=year),
    }
    src = {label: d.by_neighborhood(df, name, period=year) for label, name in SOURCES.items()}
    rows = []
    for pol_label, pol in pollutants.items():
        for src_label, s in src.items():
            rows.append({"pollutant": pol_label, "source": src_label, **correlate(s, pol)})
    table = pd.DataFrame(rows)
    traffic_vs_boilers = correlate(src["Traffic (all vehicles)"],
                                   src["Building boilers (PM2.5)"])
    return {"year": year, "table": table, "pollutants": pollutants, "sources": src,
            "traffic_vs_boilers_r": traffic_vs_boilers["r"]}


# 4. Health burden -------------------------------------------------------------

def burden(df: pd.DataFrame) -> dict:
    """Set neighborhood PM2.5 against the estimated health harm attributed to it.

    Exposure is the 2017-2019 average annual PM2.5, matching the 2017-2019
    health estimates. The health indicators are the city's own estimates of
    visits and deaths caused by PM2.5 at each neighborhood's levels.
    """
    exposure = d.by_neighborhood(df, d.PM25, measure="Annual mean",
                                 periods=HEALTH_EXPOSURE_YEARS).rename("pm25")
    child_ed = d.by_neighborhood(df, d.ASTHMA_ED_PM25, measure_contains="under age 18",
                                 period=HEALTH_PERIOD).rename("child_asthma_ed")
    deaths = d.by_neighborhood(df, d.DEATHS_PM25, period=HEALTH_PERIOD).rename("deaths")
    table = pd.concat([exposure, child_ed, deaths], axis=1).dropna()
    return {
        "table": table,
        "exposure_ratio": table["pm25"].max() / table["pm25"].min(),
        "child_ed_ratio": table["child_asthma_ed"].max() / table["child_asthma_ed"].min(),
        "pm_vs_child_ed": correlate(table["pm25"], table["child_asthma_ed"]),
        "pm_vs_deaths": correlate(table["pm25"], table["deaths"]),
        "top_child_ed": table.sort_values("child_asthma_ed", ascending=False).head(5),
        "bottom_child_ed": table.sort_values("child_asthma_ed").head(3),
    }


def run_all(df: pd.DataFrame) -> dict:
    return {"trend": trend(df), "smoke": smoke_2023(df),
            "sources": sources(df), "burden": burden(df)}
