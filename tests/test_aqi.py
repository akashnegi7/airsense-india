import numpy as np
import pandas as pd

from airsense import aqi


def test_sub_index_breakpoints():
    assert aqi.sub_index("pm2_5", 30) == 50
    assert aqi.sub_index("pm2_5", 60) == 100
    assert aqi.sub_index("pm2_5", 90) == 200
    assert aqi.sub_index("pm10", 250) == 200


def test_sub_index_clamps_and_keeps_nan():
    assert aqi.sub_index("pm2_5", -5) == 0
    assert aqi.sub_index("pm2_5", 9999) == 500
    assert np.isnan(aqi.sub_index("pm2_5", np.nan))


def test_category_boundaries():
    s = pd.Series([0, 50, 51, 100, 200, 201, 300, 400, 401])
    assert aqi.categorize(s).astype(str).tolist() == [
        "Good", "Good", "Satisfactory", "Satisfactory", "Moderate", "Poor", "Poor", "Very Poor", "Severe"]


def test_aqi_is_max_of_subindices_and_names_dominant():
    df = pd.DataFrame({"pm2_5": [90.0], "pm10": [50.0], "no2": [20.0], "so2": [5.0], "o3": [30.0], "co": [0.5]})
    out = aqi.add_aqi(df)
    assert out.loc[0, "aqi"] == 200 and out.loc[0, "dominant"] == "pm2_5"
    assert out.loc[0, "category"] == "Moderate"


def test_aqi_needs_three_pollutants_including_pm():
    two = pd.DataFrame({"pm2_5": [90.0], "pm10": [np.nan], "no2": [20.0], "so2": [np.nan], "o3": [np.nan], "co": [np.nan]})
    assert np.isnan(aqi.add_aqi(two).loc[0, "aqi"])
    no_pm = pd.DataFrame({"pm2_5": [np.nan], "pm10": [np.nan], "no2": [20.0], "so2": [5.0], "o3": [30.0], "co": [0.5]})
    assert np.isnan(aqi.add_aqi(no_pm).loc[0, "aqi"])


def test_palettes_cover_every_category():
    for p in aqi.PALETTES:
        assert set(aqi.colors(p)) == set(aqi.CATEGORIES)
