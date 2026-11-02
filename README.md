# AirSense India

A live air-quality intelligence dashboard for 35 Indian cities: CPCB-style AQI, city drill-downs,
city comparisons, pollution drivers, health advice and an auto-generated data story.

Built with Python, Pandas, Plotly and Dash, backed by SQLite, with an automated ETL pipeline, tests, CI and Docker.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m airsense.etl.pipeline --days 365    # live data (needs internet); falls back to demo data if offline
# python -m airsense.etl.pipeline --demo      # force synthetic demo data (works offline)

python -m airsense.dashboard.app              # open http://localhost:8050
```
If you skip the ETL step, the app creates demo data on first start and shows a yellow **DEMO DATA** badge.
Run the tests with `pip install -r requirements-dev.txt && pytest -q`.

## Architecture

```
Open-Meteo (CAMS air quality + weather)
        |  etl/fetch.py            hourly data for 35 cities
        v
etl/clean.py   validity limits, spike filter, short-gap interpolation, CO unit fix
        v
aqi.py         CPCB sub-indices -> AQI, category, dominant pollutant
        v
data/airsense.db (SQLite: cities, daily, hourly, meta)
        v
dashboard/     Dash app: overview, explorer, compare, drivers, story, about
```
GitHub Actions refreshes the database daily (`update-data.yml`) and runs the tests on every push (`ci.yml`).

## Deploy

- **Render:** push to GitHub, then New > Blueprint (uses `render.yaml` and the `Dockerfile`).
- **Hugging Face Spaces:** create a Docker Space, push the repo, set the app port to 8050.
- **Any server:** `docker build -t airsense . && docker run -p 8050:8050 airsense`

For the daily refresh to reach your host, let the Action commit `data/airsense.db` and enable auto-deploy on push.

## Syllabus mapping

| Topic | Where |
|---|---|
| Gestalt, pre-attentive attributes, Tufte | Size and colour encode AQI on the map; zero-based axes; minimal gridlines; direct labels (`charts.py`) |
| Data types, preprocessing | `etl/clean.py`: limits, spikes, interpolation, aggregation; daily needs 16 valid hours |
| Heatmaps, box plots, bubble, pair plot | Compare and "What drives it" tabs |
| Plotly and Dash, sliders, dropdowns, tooltips | Every tab; time-window RangeSlider in the explorer |
| Geospatial | Map of city AQI (`px.scatter_map`) |
| Data storytelling, BAN | "Your city" card with the big AQI number; auto-written Data story tab |
| Colour blindness, accessibility | Colour-blind-safe switch (viridis / Okabe-Ito) across every chart |
| Ethics | About & ethics tab: limitations, honest-axes policy, correlation vs causation |

## Data honesty

Live values come from the **CAMS atmospheric model** via Open-Meteo, not from individual CPCB monitoring stations.
They are estimates for a ~11 km grid cell and can differ from official station AQI. The app says so on its About page.
If you later add CPCB or OpenAQ station data, add a new fetcher in `etl/` that returns the same columns
(`city, time, pm2_5, pm10, no2, so2, o3, co, temp, humidity, wind`).

## Ideas to extend

Next-day AQI forecast (Prophet or gradient boosting), GeoJSON state choropleth, PDF report export,
OpenAQ station overlay, e-mail alerts when a city crosses AQI 300.
