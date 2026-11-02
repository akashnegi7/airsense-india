"""Data access layer: loads the SQLite database once and exposes typed DataFrames."""
import sqlite3
from functools import lru_cache
from typing import NamedTuple

import pandas as pd

from .aqi import CATEGORIES
from .config import DB_PATH, DEMO_DAYS

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Summer", 4: "Summer", 5: "Summer",
           6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon", 10: "Post-monsoon", 11: "Post-monsoon"}


class Data(NamedTuple):
    daily: pd.DataFrame
    hourly: pd.DataFrame
    cities: pd.DataFrame
    meta: dict
    latest_date: pd.Timestamp
    latest: pd.DataFrame


def ensure():
    """Create a demo database on first run so the app never starts empty."""
    if not DB_PATH.exists():
        from .etl import pipeline
        pipeline.run(demo=True, days=DEMO_DAYS)


@lru_cache(maxsize=1)
def load() -> Data:
    ensure()
    con = sqlite3.connect(DB_PATH)
    try:
        daily = pd.read_sql("SELECT * FROM daily", con, parse_dates=["date"])
        hourly = pd.read_sql("SELECT * FROM hourly", con, parse_dates=["time"])
        cities = pd.read_sql("SELECT * FROM cities", con)
        meta = dict(pd.read_sql("SELECT key, value FROM meta", con).values)
    finally:
        con.close()
    daily["category"] = pd.Categorical(daily["category"], CATEGORIES, ordered=True)
    daily["month"] = daily["date"].dt.strftime("%Y-%m")
    daily["season"] = daily["date"].dt.month.map(SEASONS)
    coverage = daily.groupby("date")["aqi"].count()
    ok = coverage[coverage >= len(cities) * 0.5]
    latest_date = ok.index.max() if len(ok) else daily["date"].max()
    latest = daily[daily["date"] == latest_date].merge(cities, on="city")
    return Data(daily, hourly, cities, meta, latest_date, latest)
