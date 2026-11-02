"""ETL entry point:  python -m airsense.etl.pipeline [--demo] [--days 365]"""
import argparse
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..config import CITIES, DB_PATH, DEMO_DAYS
from . import fetch, synthetic
from .clean import clean_hourly, to_daily

log = logging.getLogger(__name__)
HOURLY_KEEP_DAYS = 21


def build(raw, source, db_path=DB_PATH):
    hourly = clean_hourly(raw)
    report = hourly.attrs.get("report", {})
    daily = to_daily(hourly)
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    recent = hourly[hourly["time"] >= hourly["time"].max() - pd.Timedelta(days=HOURLY_KEEP_DAYS)].copy()
    recent["time"] = recent["time"].dt.strftime("%Y-%m-%d %H:%M")

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    meta = {"source": source, "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "rows_hourly": str(len(hourly)), **{k: str(v) for k, v in report.items()}}
    con = sqlite3.connect(tmp)
    try:
        CITIES.to_sql("cities", con, index=False)
        daily.to_sql("daily", con, index=False)
        recent.to_sql("hourly", con, index=False)
        pd.DataFrame(list(meta.items()), columns=["key", "value"]).to_sql("meta", con, index=False)
        con.execute("CREATE INDEX idx_daily ON daily(city, date)")
        con.commit()
    finally:
        con.close()
    os.replace(tmp, db_path)
    log.info("Wrote %s (%s, %d daily rows)", db_path, source, len(daily))
    return db_path


def run(demo=False, days=365, db_path=DB_PATH):
    if demo:
        return build(synthetic.generate(DEMO_DAYS if days is None else days), "demo", db_path)
    try:
        raw = fetch.fetch_all(days)
        return build(raw, "open-meteo", db_path)
    except Exception as exc:
        log.warning("Live ingestion failed: %s", exc)
        if Path(db_path).exists():
            log.warning("Keeping the existing database.")
            return Path(db_path)
        log.warning("No database yet - falling back to DEMO data.")
        return build(synthetic.generate(DEMO_DAYS), "demo", db_path)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="AirSense ETL")
    ap.add_argument("--demo", action="store_true", help="generate synthetic demo data (offline)")
    ap.add_argument("--days", type=int, default=365, help="days of history to ingest")
    ap.add_argument("--db", default=str(DB_PATH))
    a = ap.parse_args()
    run(demo=a.demo, days=a.days, db_path=a.db)


if __name__ == "__main__":
    main()
