"""AirSense India - Dash application.   Run:  python -m airsense.dashboard.app"""
import os

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dcc, html

from .. import aqi as A
from .. import db
from ..config import METRICS, POLLUTANTS
from . import charts as C
from .story import build_story

D = db.load()
CITY_LIST = sorted(D.cities["city"])
METRIC_OPTS = [{"label": v, "value": k} for k, v in METRICS.items()]
DATES = sorted(D.daily["date"].unique())
N = len(DATES)
STEP = max(1, N // 6)
MARKS = {i: pd.Timestamp(DATES[i]).strftime("%b %y") for i in range(0, N, STEP)}
DEFAULT_COMPARE = [c for c in ["Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru", "Lucknow"] if c in CITY_LIST]
IS_DEMO = D.meta.get("source") == "demo"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], title="AirSense India",
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server  # for gunicorn


def pal(cb):
    return "safe" if cb else "standard"


def kpi(title, value, sub=""):
    return dbc.Card(dbc.CardBody([html.Div(title, className="text-muted small"),
                                  html.Div(value, className="fs-3 fw-bold"),
                                  html.Div(sub, className="small text-muted")]), className="shadow-sm h-100")


def legend(p):
    cols = A.colors(p)
    return html.Div([html.Span(f"{c}  {r}", style={
        "background": cols[c], "color": A.text_on(cols[c]), "padding": "3px 12px", "borderRadius": "14px",
        "marginRight": "6px", "marginBottom": "4px", "fontSize": "0.8rem", "display": "inline-block"})
        for c, r in zip(A.CATEGORIES, A.RANGE_LABELS)])


def hint(text):
    return html.P(text, className="text-muted small mb-2")


def source_badge():
    if IS_DEMO:
        return dbc.Badge("DEMO DATA (synthetic) - run the live pipeline", color="warning", text_color="dark")
    return dbc.Badge(f"Live data · updated {D.meta.get('updated_at', '?')}", color="success")


# ------------------------------------------------------------------ layout
overview = dbc.Container([
    hint("Pick your city for a plain-language health summary, then explore the national picture below."),
    dbc.Row([dbc.Col([html.Label("Check your city", className="fw-semibold"),
                      dcc.Dropdown(CITY_LIST, "Delhi" if "Delhi" in CITY_LIST else CITY_LIST[0], id="ov-city", clearable=False)],
                     md=3, className="mb-3"),
             dbc.Col(html.Div(id="ov-ban"), md=9, className="mb-3")]),
    dbc.Row(id="ov-kpis", className="g-3 mb-3"),
    dbc.Row([dbc.Col(dcc.Graph(id="ov-map", config={"displayModeBar": False}), lg=8),
             dbc.Col(dcc.Graph(id="ov-rank", config={"displayModeBar": False}), lg=4)]),
    html.Div(id="ov-legend", className="mt-2"),
], fluid=True, className="pt-3")

explorer = dbc.Container([
    hint("Choose a city and a measure, then drag the slider to zoom into a period."),
    dbc.Row([dbc.Col([html.Label("City", className="fw-semibold"),
                      dcc.Dropdown(CITY_LIST, "Delhi" if "Delhi" in CITY_LIST else CITY_LIST[0], id="ex-city", clearable=False)], md=3),
             dbc.Col([html.Label("Measure", className="fw-semibold"),
                      dcc.Dropdown(METRIC_OPTS, "aqi", id="ex-metric", clearable=False)], md=3),
             dbc.Col([html.Label("Time window", className="fw-semibold"),
                      dcc.RangeSlider(0, N - 1, 1, value=[max(0, N - 180), N - 1], marks=MARKS, id="ex-range",
                                      allowCross=False), html.Div(id="ex-label", className="small text-muted")], md=6)],
            className="mb-3 g-3"),
    dcc.Graph(id="ex-trend", config={"displayModeBar": False}),
    dbc.Row([dbc.Col(dcc.Graph(id="ex-hourly", config={"displayModeBar": False}), lg=7),
             dbc.Col(dcc.Graph(id="ex-box", config={"displayModeBar": False}), lg=5)]),
    dbc.Button("Download this view as CSV", id="ex-dl-btn", color="secondary", outline=True, size="sm"),
    dcc.Download(id="ex-dl"),
], fluid=True, className="pt-3")

compare = dbc.Container([
    hint("Select several cities to compare them on the same scale."),
    dbc.Row([dbc.Col([html.Label("Cities", className="fw-semibold"),
                      dcc.Dropdown(CITY_LIST, DEFAULT_COMPARE, multi=True, id="cp-cities")], md=8),
             dbc.Col([html.Label("Measure", className="fw-semibold"),
                      dcc.Dropdown(METRIC_OPTS, "pm2_5", id="cp-metric", clearable=False)], md=4)],
            className="mb-3 g-3"),
    dcc.Graph(id="cp-heat", config={"displayModeBar": False}),
    dcc.Graph(id="cp-box", config={"displayModeBar": False}),
    dcc.Graph(id="cp-small", config={"displayModeBar": False}),
], fluid=True, className="pt-3")

drivers = dbc.Container([
    hint("What explains the pollution? Explore how pollutants and weather relate in one city."),
    dbc.Row([dbc.Col([html.Label("City", className="fw-semibold"),
                      dcc.Dropdown(CITY_LIST, "Delhi" if "Delhi" in CITY_LIST else CITY_LIST[0], id="dr-city", clearable=False)], md=3)],
            className="mb-3"),
    dbc.Row([dbc.Col(dcc.Graph(id="dr-corr", config={"displayModeBar": False}), lg=6),
             dbc.Col(dcc.Graph(id="dr-wind", config={"displayModeBar": False}), lg=6)]),
    dcc.Graph(id="dr-bubble", config={"displayModeBar": False}),
    dcc.Graph(id="dr-pair", config={"displayModeBar": False}),
], fluid=True, className="pt-3")

story = dbc.Container([html.Div(id="st-text"), dcc.Graph(id="st-chart", config={"displayModeBar": False})],
                      fluid=True, className="pt-3")

ABOUT = f"""
### How AirSense India works
**Data source.** `{D.meta.get('source', 'unknown')}`. Live mode uses the free Open-Meteo APIs, which serve the
**CAMS atmospheric model** (satellite and ground observations assimilated into a model) on a ~11 km grid. Weather comes from Open-Meteo too.

**Pipeline.** Ingest hourly data → drop duplicates → remove impossible values and spikes → interpolate gaps of 6 hours or less →
aggregate to daily values (a daily mean needs ≥16 valid hours, as CPCB requires) → compute the CPCB AQI.
Last run: values removed as invalid: **{D.meta.get('invalid_removed', '?')}**, short gaps filled: **{D.meta.get('gaps_filled', '?')}**,
missing after cleaning: **{D.meta.get('missing_pct_after', '?')}%**. Updated: {D.meta.get('updated_at', '?')}.

**AQI.** The Indian National AQI (CPCB): the highest of the pollutant sub-indices (PM2.5, PM10, NO₂, SO₂, O₃, CO),
valid only when at least 3 pollutants including PM2.5 or PM10 are available.

### Limitations (please read)
- Values are **model estimates for a city-centre grid cell**, not readings from a single CPCB monitoring station.
  They can differ from official station AQI, especially near roads, industry or construction.
- Neighbourhood-level variation is invisible at this resolution.
- Short gaps are interpolated; long gaps are left missing rather than guessed.
- Correlations (e.g. fireworks, wind) show association, not proof of cause.
- This is information, not medical advice. Consult a doctor for health concerns.

### Honest-visualization policy
Bar and area measures start at zero; the same colour scale is used everywhere; missing data is shown as missing;
the colour-blind-safe palette (top-right switch) is applied to every chart.
"""
about = dbc.Container(dcc.Markdown(ABOUT), fluid=True, className="pt-3", style={"maxWidth": "900px"})

navbar = dbc.Navbar(dbc.Container([
    html.Div([html.Span("AirSense India", className="navbar-brand mb-0 h4 fw-bold"),
              html.Span("  real-time air quality intelligence", className="text-light small d-none d-md-inline")]),
    html.Div([source_badge(), dbc.Switch(id="cb-switch", label="Colour-blind safe", value=False,
                                         className="d-inline-block ms-3 text-white")], className="d-flex align-items-center"),
], fluid=True), color="primary", dark=True)

app.layout = html.Div([
    navbar,
    dbc.Tabs([dbc.Tab(overview, label="Overview", tab_id="t1"), dbc.Tab(explorer, label="City explorer", tab_id="t2"),
              dbc.Tab(compare, label="Compare", tab_id="t3"), dbc.Tab(drivers, label="What drives it", tab_id="t4"),
              dbc.Tab(story, label="Data story", tab_id="t5"), dbc.Tab(about, label="About & ethics", tab_id="t6")],
             active_tab="t1", className="px-3 pt-2"),
])


# ------------------------------------------------------------------ callbacks
def _ban(city, p):
    row = D.latest[D.latest["city"] == city]
    if row.empty or pd.isna(row.iloc[0]["aqi"]):
        return dbc.Alert("No reliable reading for this city on the latest day.", color="secondary")
    r = row.iloc[0]
    cat, col = str(r["category"]), A.colors(p)[str(r["category"])]
    adv = A.ADVICE[cat]
    big = html.Div([html.Div("AQI", className="small"),
                    html.Div(f"{r['aqi']:.0f}", style={"fontSize": "4.2rem", "fontWeight": 800, "lineHeight": 1}),
                    html.Div(cat, className="fs-5 fw-semibold")],
                   className="text-center p-3 rounded", style={"background": col, "color": A.text_on(col)})
    detail = [html.H5(f"{city}: {adv['headline']}"),
              html.P(f"Main pollutant: {POLLUTANTS.get(r['dominant'], r['dominant'])} · as of {D.latest_date:%d %b %Y}",
                     className="text-muted small"),
              html.Ul([html.Li([html.B("Everyone: "), adv["general"]]),
                       html.Li([html.B("Sensitive groups: "), adv["sensitive"]]),
                       html.Li([html.B("Exercise: "), adv["exercise"]])], className="mb-0")]
    return dbc.Card(dbc.CardBody(dbc.Row([dbc.Col(big, md=4, xs=12, className="mb-2"), dbc.Col(detail, md=8, xs=12)],
                                         align="center")), className="shadow-sm")


@app.callback(Output("ov-ban", "children"), Output("ov-kpis", "children"), Output("ov-map", "figure"),
              Output("ov-rank", "figure"), Output("ov-legend", "children"),
              Input("ov-city", "value"), Input("cb-switch", "value"))
def update_overview(city, cb):
    p, lt = pal(cb), D.latest.dropna(subset=["aqi"])
    if lt.empty:
        return _ban(city, p), [], C.empty_fig(), C.empty_fig(), legend(p)
    worst, best = lt.loc[lt["aqi"].idxmax()], lt.loc[lt["aqi"].idxmin()]
    avg = lt["aqi"].mean()
    kpis = [dbc.Col(kpi("National average AQI", f"{avg:.0f}", A.category_of(avg)), md=3, xs=6),
            dbc.Col(kpi("Most polluted", worst["city"], f"AQI {worst['aqi']:.0f}"), md=3, xs=6),
            dbc.Col(kpi("Cleanest", best["city"], f"AQI {best['aqi']:.0f}"), md=3, xs=6),
            dbc.Col(kpi("Cities Poor or worse", f"{int((lt['aqi'] > 200).sum())} of {len(lt)}", "AQI above 200"), md=3, xs=6)]
    return _ban(city, p), kpis, C.india_map(D.latest, p), C.ranking_bar(D.latest, p), legend(p)


def _window(rng):
    lo, hi = rng
    return pd.Timestamp(DATES[lo]), pd.Timestamp(DATES[hi])


def _city_slice(city, rng):
    d0, d1 = _window(rng)
    df = D.daily[(D.daily["city"] == city) & (D.daily["date"] >= d0) & (D.daily["date"] <= d1)].sort_values("date")
    return df, d0, d1


@app.callback(Output("ex-label", "children"), Output("ex-trend", "figure"), Output("ex-hourly", "figure"),
              Output("ex-box", "figure"), Input("ex-city", "value"), Input("ex-metric", "value"),
              Input("ex-range", "value"), Input("cb-switch", "value"))
def update_explorer(city, metric, rng, cb):
    df, d0, d1 = _city_slice(city, rng)
    label = f"Showing {d0:%d %b %Y} to {d1:%d %b %Y} ({(d1 - d0).days + 1} days)"
    return label, C.trend_chart(df, metric, pal(cb), city), C.hourly_chart(D.hourly, city), C.monthly_box(df, metric)


@app.callback(Output("ex-dl", "data"), Input("ex-dl-btn", "n_clicks"), State("ex-city", "value"),
              State("ex-range", "value"), prevent_initial_call=True)
def download(_, city, rng):
    df, *_ = _city_slice(city, rng)
    return dcc.send_data_frame(df.drop(columns=["month", "season"]).to_csv, f"airsense_{city.lower()}.csv", index=False)


@app.callback(Output("cp-heat", "figure"), Output("cp-box", "figure"), Output("cp-small", "figure"),
              Input("cp-cities", "value"), Input("cp-metric", "value"), Input("cb-switch", "value"))
def update_compare(cities, metric, cb):
    cities, p = cities or [], pal(cb)
    return (C.city_month_heatmap(D.daily, cities, metric, p), C.distribution_box(D.daily, cities, metric, p),
            C.small_multiples(D.daily, cities, metric, p))


@app.callback(Output("dr-corr", "figure"), Output("dr-wind", "figure"), Output("dr-bubble", "figure"),
              Output("dr-pair", "figure"), Input("dr-city", "value"), Input("cb-switch", "value"))
def update_drivers(city, cb):
    p, df = pal(cb), D.daily[D.daily["city"] == city]
    return C.corr_heatmap(df, p), C.scatter_wind(df, p), C.bubble(D.daily, p), C.pair_plot(df, p)


@app.callback(Output("st-text", "children"), Output("st-chart", "figure"), Input("cb-switch", "value"))
def update_story(cb):
    s = build_story(D.daily, D.latest_date)
    text = dbc.Card(dbc.CardBody([html.H4(s["headline"], className="mb-3"),
                                  html.Ul([html.Li(x, className="mb-2") for x in s["points"]]),
                                  html.P("Generated automatically from the latest data; every number above is computed, not typed.",
                                         className="text-muted small mb-0")]), className="shadow-sm mb-3")
    return text, C.change_bar(s["changes"], pal(cb))


if __name__ == "__main__":
    app.run(debug=os.getenv("DEBUG") == "1", host="0.0.0.0", port=int(os.getenv("PORT", "8050")))
