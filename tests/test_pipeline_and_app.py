import sqlite3

from airsense.etl import pipeline


def test_demo_pipeline_builds_database(tmp_path):
    db = pipeline.run(demo=True, days=40, db_path=tmp_path / "t.db")
    con = sqlite3.connect(db)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"cities", "daily", "hourly", "meta"} <= tables
    assert con.execute("SELECT COUNT(*) FROM daily WHERE aqi IS NOT NULL").fetchone()[0] > 1000
    assert dict(con.execute("SELECT key, value FROM meta").fetchall())["source"] == "demo"


def test_live_failure_falls_back_to_demo(tmp_path, monkeypatch):
    from airsense.etl import fetch
    monkeypatch.setattr(fetch, "fetch_all", lambda days: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(pipeline, "DEMO_DAYS", 30)
    db = pipeline.run(demo=False, db_path=tmp_path / "fb.db")
    assert db.exists()


def test_every_dashboard_callback_runs_for_both_palettes():
    from airsense.dashboard import app as a
    for cb in (False, True):
        ban, kpis, fmap, rank, leg = a.update_overview("Delhi", cb)
        assert len(kpis) == 4 and fmap.data and rank.data
        label, trend, hourly, box = a.update_explorer("Mumbai", "aqi", [0, a.N - 1], cb)
        assert "days" in label and trend.data and hourly.data and box.data
        for fig in a.update_compare(a.DEFAULT_COMPARE, "pm2_5", cb):
            assert fig.data
        for fig in a.update_drivers("Kolkata", cb):
            assert fig.data
        text, chart = a.update_story(cb)
        assert text is not None and chart is not None


def test_compare_with_no_city_selected_is_graceful():
    from airsense.dashboard import app as a
    figs = a.update_compare([], "aqi", False)
    assert len(figs) == 3


def test_story_is_data_driven():
    from airsense import db
    from airsense.dashboard.story import build_story
    d = db.load()
    s = build_story(d.daily, d.latest_date)
    assert "AQI" in s["headline"] and len(s["points"]) >= 3
