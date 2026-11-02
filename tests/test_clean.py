import numpy as np
import pandas as pd

from airsense.etl.clean import clean_hourly, to_daily


def make(n=48, **over):
    t = pd.date_range("2026-01-01", periods=n, freq="h")
    df = pd.DataFrame({"city": "X", "time": t, "pm2_5": 50.0, "pm10": 90.0, "no2": 20.0, "so2": 5.0,
                       "o3": 30.0, "co": 500.0, "temp": 20.0, "humidity": 50.0, "wind": 5.0})
    for k, v in over.items():
        df[k] = v
    return df


def test_removes_sentinels_and_impossible_values():
    df = make()
    df.loc[10, "pm2_5"] = -999
    df.loc[20, "temp"] = 400
    out = clean_hourly(df)
    assert out["pm2_5"].min() >= 0 and out["temp"].max() <= 55


def test_drops_duplicates():
    df = pd.concat([make(), make()])
    assert len(clean_hourly(df)) == 48


def test_interpolates_short_gaps_only():
    df = make()
    df.loc[5:7, "no2"] = np.nan        # 3h gap: filled
    df.loc[20:30, "no2"] = np.nan      # 11h gap: left missing
    out = clean_hourly(df)
    assert out.loc[5:7, "no2"].notna().all()
    assert out.loc[20:30, "no2"].isna().all()


def test_spike_filter_and_co_conversion():
    df = make()
    df.loc[12, "pm2_5"] = 900          # 18x local median and > 300
    out = clean_hourly(df)
    assert out.loc[12, "pm2_5"] < 100  # removed then interpolated
    assert abs(out["co"].iloc[0] - 0.5) < 1e-9  # 500 ug/m3 -> 0.5 mg/m3


def test_daily_requires_16_valid_hours():
    df = make(n=24)
    df.loc[:10, "pm2_5"] = np.nan      # only 13 valid hours
    d = to_daily(clean_hourly(df, max_gap_hours=0))
    assert len(d) == 1 and np.isnan(d.loc[0, "pm2_5"])


def test_daily_full_day_gives_aqi():
    d = to_daily(clean_hourly(make(n=24)))
    assert d.loc[0, "aqi"] == 90 and d.loc[0, "dominant"] == "pm10" and d.loc[0, "category"] == "Satisfactory"
