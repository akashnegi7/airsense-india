"""Live ingestion from the free, key-less Open-Meteo APIs (CAMS air quality + weather)."""
import logging
import time
from datetime import date, timedelta

import pandas as pd
import requests

from ..config import CITIES

log = logging.getLogger(__name__)
AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"
WX_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
AQ_VARS = {"pm2_5": "pm2_5", "pm10": "pm10", "nitrogen_dioxide": "no2",
           "sulphur_dioxide": "so2", "ozone": "o3", "carbon_monoxide": "co"}
WX_VARS = {"temperature_2m": "temp", "relative_humidity_2m": "humidity", "wind_speed_10m": "wind"}
TZ = "Asia/Kolkata"


def _get(url, params, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            log.warning("Retry %s for %s: %s", attempt + 1, url, exc)
            time.sleep(2 ** attempt)


def _frame(payload, mapping):
    h = payload["hourly"]
    df = pd.DataFrame({"time": pd.to_datetime(h["time"])})
    for api_name, name in mapping.items():
        df[name] = h.get(api_name)
    return df


def _weather(lat, lon, start, end):
    """Recent days from the forecast API (past_days <= 92), older days from the archive API."""
    recent_start = max(start, end - timedelta(days=92))
    p = dict(latitude=lat, longitude=lon, hourly=",".join(WX_VARS), timezone=TZ,
             past_days=(end - recent_start).days, forecast_days=1)
    parts = [_frame(_get(WX_URL, p), WX_VARS)]
    if start < recent_start:
        p = dict(latitude=lat, longitude=lon, hourly=",".join(WX_VARS), timezone=TZ,
                 start_date=start.isoformat(), end_date=(recent_start - timedelta(days=1)).isoformat())
        parts.append(_frame(_get(WX_ARCHIVE, p), WX_VARS))
    return pd.concat(parts).drop_duplicates("time")


def fetch_city(name, lat, lon, days=365):
    end = date.today()
    start = end - timedelta(days=days)
    aq = _frame(_get(AQ_URL, dict(latitude=lat, longitude=lon, hourly=",".join(AQ_VARS), timezone=TZ,
                                  start_date=start.isoformat(), end_date=end.isoformat())), AQ_VARS)
    df = aq.merge(_weather(lat, lon, start, end), on="time", how="left")
    df.insert(0, "city", name)
    return df[df["time"] <= pd.Timestamp.now()]


def fetch_all(days=365, cities=CITIES, pause=0.3):
    frames, failed = [], []
    for r in cities.itertuples():
        try:
            frames.append(fetch_city(r.city, r.lat, r.lon, days))
            log.info("Fetched %s", r.city)
        except Exception as exc:  # keep going; one bad city should not kill the run
            failed.append(r.city)
            log.warning("Failed %s: %s", r.city, exc)
        time.sleep(pause)
    if len(frames) < len(cities) / 2:
        raise RuntimeError(f"Live fetch failed for {len(failed)} of {len(cities)} cities")
    return pd.concat(frames, ignore_index=True)
