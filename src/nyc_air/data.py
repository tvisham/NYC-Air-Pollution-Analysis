"""Loading and selecting from the NYC air quality dataset.

The dataset (NYC Open Data "Air Quality", id c3uy-2p5r) is a long table: one row per
indicator x geography x time period. Each indicator is published at several
geography levels at once (citywide, borough, UHF34, UHF42, community district), so
any comparison has to pick ONE level. Mixing levels in a single table counts the
same area several times and distorts correlations.

This project uses two levels:
  * "Citywide" for trends over time
  * "UHF42" (42 United Hospital Fund neighborhoods) for comparisons between places
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "air_quality.csv"
GEOJSON_PATH = DATA_DIR / "uhf42.geojson"

# Indicator names exactly as they appear in the dataset.
PM25 = "Fine particles (PM 2.5)"
NO2 = "Nitrogen dioxide (NO2)"
OZONE = "Ozone (O3)"
TRAFFIC = "Traffic density"
TRAFFIC_TRUCKS = "Traffic density (trucks)"
TRAFFIC_CARS = "Traffic density (cars)"
BOILER_PM25 = "Boiler emissions (PM2.5)"
BOILER_NOX = "Boiler emissions (NOx)"
ASTHMA_ED_PM25 = "Asthma emergency department visits due to PM2.5"
DEATHS_PM25 = "Deaths due to PM2.5"

CITYWIDE = "Citywide"
NEIGHBORHOOD = "UHF42"


def load_air_quality(path: str | Path = CSV_PATH) -> pd.DataFrame:
    """Read the CSV and tidy the columns used in the analysis.

    Adds:
      year      first year of the period as an int ("2017-2019" -> 2017)
      geo_id    neighborhood code as an int, for joining to the boundary file
    """
    df = pd.read_csv(path)
    df = df.rename(columns={"Geo Type Name": "geo_type", "Geo Join ID": "geo_id",
                            "Geo Place Name": "place", "Time Period": "period",
                            "Data Value": "value", "Name": "indicator",
                            "Measure": "measure", "Measure Info": "unit"})
    df["period"] = df["period"].astype(str)
    df["year"] = df["period"].str.extract(r"(\d{4})", expand=False).astype(int)
    df["geo_id"] = pd.to_numeric(df["geo_id"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def select(df: pd.DataFrame, indicator: str, geo_type: str, *,
           measure: str | None = None, measure_contains: str | None = None,
           period: str | None = None) -> pd.DataFrame:
    """Filter to one indicator at one geography level (and optionally one measure/period)."""
    out = df[(df["indicator"] == indicator) & (df["geo_type"] == geo_type)]
    if measure is not None:
        out = out[out["measure"] == measure]
    if measure_contains is not None:
        out = out[out["measure"].str.contains(measure_contains, case=False, regex=False)]
    if period is not None:
        out = out[out["period"] == period]
    if out.empty:
        raise ValueError(f"No rows for {indicator!r} at {geo_type!r} "
                         f"(measure={measure or measure_contains}, period={period})")
    return out


def by_neighborhood(df: pd.DataFrame, indicator: str, *, measure: str | None = None,
                    measure_contains: str | None = None,
                    period: str | None = None,
                    periods: list[str] | None = None) -> pd.Series:
    """One value per UHF42 neighborhood, indexed by neighborhood name.

    Pass `periods` to average several periods (e.g. three years of PM2.5).
    """
    if periods is not None:
        parts = [select(df, indicator, NEIGHBORHOOD, measure=measure,
                        measure_contains=measure_contains, period=p) for p in periods]
        rows = pd.concat(parts)
    else:
        rows = select(df, indicator, NEIGHBORHOOD, measure=measure,
                      measure_contains=measure_contains, period=period)
    s = rows.groupby("place")["value"].mean()
    s.name = indicator
    return s


def citywide_series(df: pd.DataFrame, indicator: str, measure: str) -> pd.Series:
    """Citywide values indexed by year."""
    rows = select(df, indicator, CITYWIDE, measure=measure)
    s = rows.set_index("year")["value"].sort_index()
    s.name = f"{indicator} ({measure})"
    return s


def neighborhood_ids(df: pd.DataFrame) -> pd.Series:
    """Map neighborhood name -> UHF42 code, for joining to the boundary file."""
    rows = df[df["geo_type"] == NEIGHBORHOOD][["place", "geo_id"]].drop_duplicates()
    return rows.set_index("place")["geo_id"].astype(int)


def load_neighborhoods(path: str | Path = GEOJSON_PATH) -> list[dict]:
    """Read UHF42 boundaries as a list of {"id", "name", "borough", "polygons"}.

    `polygons` is a list of exterior rings, each a list of (lon, lat) pairs.
    Reading GeoJSON directly keeps the project free of geopandas, which is
    hard to install on some systems.
    """
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    out = []
    for feat in gj["features"]:
        props = feat["properties"]
        code = int(props["GEOCODE"])
        if code == 0:  # unassigned area (parks, water) in the source file
            continue
        geom = feat["geometry"]
        rings = ([geom["coordinates"][0]] if geom["type"] == "Polygon"
                 else [poly[0] for poly in geom["coordinates"]])
        out.append({"id": code, "name": props["GEONAME"],
                    "borough": props["BOROUGH"], "polygons": rings})
    return out
