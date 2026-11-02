"""Data cleaning: validity limits, spike removal, short-gap interpolation, daily aggregation."""
import numpy as np
import pandas as pd

from ..aqi import add_aqi

# Physically plausible limits. CO is supplied in ug/m3 and converted to mg/m3 at the end.
LIMITS = {
    "pm2_5": (0, 1000), "pm10": (0, 2000), "no2": (0, 1000), "so2": (0, 2000),
    "o3": (0, 1000), "co": (0, 50000),
    "temp": (-20, 55), "humidity": (0, 100), "wind": (0, 200),
}
MIN_HOURS = 16  # CPCB: a 24h average needs >=16 valid hourly values


def _fill_short_gaps(s, limit):
    """Linearly interpolate only gaps no longer than `limit` hours (long gaps stay missing)."""
    isna = s.isna()
    run_id = (isna != isna.shift()).cumsum()
    run_len = isna.groupby(run_id).transform("sum")
    filled = s.interpolate(limit_area="inside")
    return s.where(~(isna & (run_len <= limit)), filled)


def clean_hourly(raw, max_gap_hours=6):
    """Clean raw hourly data (columns: city, time, pollutants, weather; CO in ug/m3).

    Steps: dedupe -> numeric coercion -> limit check -> spike filter -> short-gap
    interpolation -> CO unit conversion. Counts are stored in ``df.attrs['report']``.
    """
    df = raw.copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df.drop_duplicates(["city", "time"]).sort_values(["city", "time"]).reset_index(drop=True)
    cols = [c for c in LIMITS if c in df]
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    valid_before = int(df[cols].notna().sum().sum())

    for c in cols:
        lo, hi = LIMITS[c]
        df.loc[(df[c] < lo) | (df[c] > hi), c] = np.nan

    for c in ("pm2_5", "pm10"):  # isolated spikes far above the local rolling median
        if c in df:
            med = df.groupby("city")[c].transform(lambda s: s.rolling(25, center=True, min_periods=5).median())
            df.loc[(df[c] > 8 * med) & (df[c] > 300), c] = np.nan

    valid_mid = int(df[cols].notna().sum().sum())
    for c in cols:
        df[c] = df.groupby("city")[c].transform(lambda s: _fill_short_gaps(s, max_gap_hours))
    valid_after = int(df[cols].notna().sum().sum())

    if "co" in df:
        df["co"] = df["co"] / 1000.0  # ug/m3 -> mg/m3
    df.attrs["report"] = {
        "invalid_removed": valid_before - valid_mid,
        "gaps_filled": valid_after - valid_mid,
        "missing_pct_after": round(100 * (1 - valid_after / max(df[cols].size, 1)), 2),
    }
    return df


def to_daily(hourly):
    """Aggregate cleaned hourly data to daily CPCB-style values and compute AQI."""
    h = hourly.sort_values(["city", "time"]).copy()
    for c in ("o3", "co"):  # CPCB uses the max 8-hour rolling mean for O3 and CO
        h[c + "_8h"] = h.groupby("city")[c].transform(lambda s: s.rolling(8, min_periods=6).mean())
    h["date"] = h["time"].dt.floor("D")
    g = h.groupby(["city", "date"])
    mean_cols = ["pm2_5", "pm10", "no2", "so2"]
    out = g[mean_cols + ["temp", "humidity", "wind"]].mean()
    counts = g[mean_cols].count()
    out[mean_cols] = out[mean_cols].where(counts >= MIN_HOURS)
    out["o3"] = g["o3_8h"].max()
    out["co"] = g["co_8h"].max()
    return add_aqi(out.reset_index())
