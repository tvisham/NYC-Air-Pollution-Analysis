"""Checks that the data loads as expected and the findings hold.

    pytest
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nyc_air import analysis, data  # noqa: E402


@pytest.fixture(scope="module")
def df():
    return data.load_air_quality()


def test_columns_and_levels(df):
    assert {"indicator", "geo_type", "place", "period", "year", "value"} <= set(df.columns)
    assert {"Citywide", "UHF42"} <= set(df["geo_type"])


def test_42_neighborhoods_match_boundaries(df):
    ids = set(data.neighborhood_ids(df))
    hoods = {h["id"] for h in data.load_neighborhoods()}
    assert len(ids) == 42
    assert ids == hoods


def test_select_rejects_missing_combination(df):
    with pytest.raises(ValueError):
        data.select(df, data.PM25, data.CITYWIDE, measure="No such measure")


def test_trend_falls(df):
    t = analysis.trend(df)
    assert t["pm25_low"] < t["pm25_first"]
    assert t["no2_last"] < t["no2_first"]


def test_summer_2023_above_trend_everywhere(df):
    s = analysis.smoke_2023(df)
    assert s["actual"] > s["expected"]
    assert s["n_neighborhoods"] == 42
    assert s["n_rose"] == 42


def test_source_correlations_use_one_level(df):
    src = analysis.sources(df)
    assert (src["table"]["n"] == 42).all()
    assert (src["table"]["r"] > 0).all()


def test_burden_table_complete(df):
    b = analysis.burden(df)
    assert len(b["table"]) == 42
    assert b["child_ed_ratio"] > b["exposure_ratio"]
