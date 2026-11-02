"""All Plotly figures. Design rules: zero-based axes, minimal gridlines, direct labels,
plain-language titles (Tufte: high data-to-ink ratio) and colour-blind-safe palette option."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ..aqi import CATEGORIES, EDGES, SEASON_COLORS, colors, colorscale
from ..config import METRICS, PRETTY

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
INK = "#1f3b57"
GREY = "#9aa5b1"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _style(fig, height=380, title=None):
    fig.update_layout(
        template="plotly_white", height=height, font=dict(family=FONT, size=12),
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)) if title else None,
        margin=dict(l=10, r=10, t=55 if title else 20, b=10),
        legend=dict(orientation="h", y=-0.18), hoverlabel=dict(font_size=12),
    )
    return fig


def empty_fig(msg="No data for this selection", height=300):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=GREY))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, height)


def _seq(palette):
    return "YlOrRd" if palette == "standard" else "Viridis_r"


# ---------------------------------------------------------------- overview
def india_map(latest, palette):
    d = latest.dropna(subset=["aqi"]).copy()
    if d.empty:
        return empty_fig("No AQI data available")
    d["size"] = d["aqi"].clip(lower=40)
    fig = px.scatter_map(
        d, lat="lat", lon="lon", color="aqi", size="size", size_max=22, hover_name="city",
        hover_data={"state": True, "aqi": ":.0f", "category": True, "pm2_5": ":.0f",
                    "lat": False, "lon": False, "size": False},
        color_continuous_scale=colorscale(palette), range_color=(0, 500),
        map_style="carto-positron", zoom=3.4, center=dict(lat=22.5, lon=80),
        labels={"aqi": "AQI", "pm2_5": "PM2.5"},
    )
    fig.update_layout(coloraxis_colorbar=dict(title="AQI", thickness=12, len=0.7))
    return _style(fig, 470, "Where the air is worst today")


def ranking_bar(latest, palette, n=10):
    d = latest.dropna(subset=["aqi"]).nlargest(n, "aqi").sort_values("aqi")
    if d.empty:
        return empty_fig()
    d["category"] = d["category"].astype(str)
    fig = px.bar(d, x="aqi", y="city", color="category", orientation="h", text="aqi",
                 color_discrete_map=colors(palette), category_orders={"category": CATEGORIES})
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, xaxis_visible=False)
    return _style(fig, 470, f"Top {n} most polluted cities")


# ---------------------------------------------------------------- explorer
def trend_chart(df, metric, palette, city):
    if df.dropna(subset=[metric]).empty:
        return empty_fig()
    fig = go.Figure()
    if metric == "aqi":
        ymax = max(float(df["aqi"].max()) * 1.08, 110)
        for i, cat in enumerate(CATEGORIES):
            if EDGES[i] >= ymax:
                break
            fig.add_hrect(y0=EDGES[i], y1=min(EDGES[i + 1], ymax), fillcolor=colors(palette)[cat],
                          opacity=0.14, line_width=0, annotation_text=cat,
                          annotation_position="top left", annotation_font=dict(size=10, color=GREY))
    fig.add_scatter(x=df["date"], y=df[metric], mode="lines", name="Daily",
                    line=dict(width=1, color=GREY))
    fig.add_scatter(x=df["date"], y=df[metric].rolling(7, min_periods=4).mean(), mode="lines",
                    name="7-day average", line=dict(width=3, color=INK))
    fig.update_yaxes(rangemode="tozero", title=METRICS[metric])
    return _style(fig, 380, f"{city}: {METRICS[metric]} over time (axis starts at zero)")


def hourly_chart(h, city):
    d = h[h["city"] == city].sort_values("time").tail(24 * 7)
    if d.dropna(subset=["pm2_5"]).empty:
        return empty_fig("No hourly data")
    fig = px.line(d, x="time", y="pm2_5", labels={"pm2_5": "PM2.5 (µg/m³)", "time": ""})
    fig.update_traces(line=dict(color=INK, width=2))
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, 300, f"{city}: hourly PM2.5, last 7 days (note the daily rhythm)")


def monthly_box(df, metric):
    d = df.dropna(subset=[metric]).copy()
    if d.empty:
        return empty_fig()
    d["mon"] = pd.Categorical(d["date"].dt.strftime("%b"), MONTHS, ordered=True)
    fig = px.box(d, x="mon", y=metric, points=False, color_discrete_sequence=[INK],
                 category_orders={"mon": MONTHS}, labels={metric: METRICS[metric], "mon": ""})
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, 300, "Seasonality: spread of daily values by month")


# ---------------------------------------------------------------- compare
def city_month_heatmap(daily, cities, metric, palette):
    d = daily[daily["city"].isin(cities)]
    piv = d.pivot_table(index="city", columns="month", values=metric, aggfunc="mean")
    if piv.empty:
        return empty_fig("Select at least one city")
    piv = piv.loc[piv.mean(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(piv, aspect="auto", text_auto=".0f", color_continuous_scale=_seq(palette),
                    labels=dict(color=METRICS[metric], x="", y=""))
    fig.update_xaxes(side="top")
    return _style(fig, 90 + 38 * len(piv), f"Monthly average {METRICS[metric]}: darker = worse")


def distribution_box(daily, cities, metric, palette):
    d = daily[daily["city"].isin(cities)].dropna(subset=[metric])
    if d.empty:
        return empty_fig("Select at least one city")
    order = d.groupby("city")[metric].median().sort_values(ascending=False).index.tolist()
    fig = px.box(d, x="city", y=metric, points=False, category_orders={"city": order},
                 color_discrete_sequence=[INK], labels={metric: METRICS[metric], "city": ""})
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, 360, "Distribution of daily values (box = middle 50%, line = median)")


def small_multiples(daily, cities, metric, palette):
    d = daily[daily["city"].isin(cities)].dropna(subset=[metric])
    if d.empty:
        return empty_fig("Select at least one city")
    wk = d.groupby(["city", pd.Grouper(key="date", freq="W")])[metric].mean().reset_index()
    rows = int(np.ceil(wk["city"].nunique() / 3))
    fig = px.line(wk, x="date", y=metric, facet_col="city", facet_col_wrap=3, height=170 * rows + 80,
                  category_orders={"city": cities}, color_discrete_sequence=[INK],
                  labels={metric: "", "date": ""})
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, 170 * rows + 80, "Same scale, side by side: weekly averages")


# ---------------------------------------------------------------- drivers
def corr_heatmap(df, palette):
    cols = [c for c in ["pm2_5", "pm10", "no2", "so2", "o3", "co", "temp", "humidity", "wind"] if c in df]
    corr = df[cols].corr().rename(index=PRETTY, columns=PRETTY)
    fig = px.imshow(corr, zmin=-1, zmax=1, text_auto=".2f",
                    color_continuous_scale="RdBu_r" if palette == "standard" else "PuOr_r")
    return _style(fig, 430, "What moves together? (correlation, -1 to +1)")


def scatter_wind(df, palette):
    d = df.dropna(subset=["wind", "pm2_5"])
    if len(d) < 10:
        return empty_fig()
    fig = px.scatter(d, x="wind", y="pm2_5", color="season", opacity=0.6,
                     color_discrete_map=SEASON_COLORS[palette],
                     labels={"wind": "Wind speed (km/h)", "pm2_5": "PM2.5 (µg/m³)", "season": ""})
    m, c = np.polyfit(d["wind"], d["pm2_5"], 1)
    xs = np.array([d["wind"].min(), d["wind"].max()])
    fig.add_scatter(x=xs, y=m * xs + c, mode="lines", line=dict(color="black", dash="dash"), name="Trend")
    r = d["wind"].corr(d["pm2_5"])
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, 430, f"Wind vs PM2.5 (r = {r:.2f}): stronger wind, cleaner air")


def bubble(daily, palette):
    g = daily.groupby("city").agg(temp=("temp", "mean"), pm25=("pm2_5", "mean"), aqi=("aqi", "mean"),
                                  poor=("aqi", lambda s: 100 * (s > 200).sum() / max(s.notna().sum(), 1)))
    g = g.reset_index()
    g["size"] = g["poor"].clip(lower=2)
    g["label"] = np.where(g["pm25"].rank(ascending=False) <= 6, g["city"], "")
    fig = px.scatter(g, x="temp", y="pm25", size="size", size_max=38, color="aqi", text="label",
                     hover_name="city", color_continuous_scale=colorscale(palette), range_color=(0, 400),
                     hover_data={"size": False, "label": False, "poor": ":.0f", "aqi": ":.0f"},
                     labels={"temp": "Average temperature (°C)", "pm25": "Average PM2.5 (µg/m³)",
                             "aqi": "Avg AQI", "poor": "% days Poor or worse"})
    fig.update_traces(textposition="top center")
    fig.update_yaxes(rangemode="tozero")
    return _style(fig, 430, "Every city: climate vs pollution (bubble size = share of Poor-or-worse days)")


def pair_plot(df, palette):
    d = df.dropna(subset=["pm2_5", "no2", "o3", "wind", "temp"])
    if len(d) < 10:
        return empty_fig()
    d = d.sample(min(len(d), 400), random_state=1)
    fig = px.scatter_matrix(d, dimensions=["pm2_5", "no2", "o3", "wind", "temp"], color="season", opacity=0.5,
                            color_discrete_map=SEASON_COLORS[palette], labels=PRETTY)
    fig.update_traces(diagonal_visible=False, showupperhalf=False, marker=dict(size=3))
    return _style(fig, 620, "Pair plot: all relationships at a glance")


# ---------------------------------------------------------------- story
def change_bar(chg, palette):
    if chg is None or chg.empty:
        return empty_fig("Need at least 60 days of data for a comparison")
    worse, better = ("#d1495b", "#2a9d8f") if palette == "standard" else ("#D55E00", "#0072B2")
    d = pd.concat([chg.nlargest(8, "delta"), chg.nsmallest(8, "delta")]).drop_duplicates("city")
    d = d.sort_values("delta")
    d["dir"] = np.where(d["delta"] > 0, "Got worse", "Improved")
    fig = px.bar(d, x="delta", y="city", orientation="h", color="dir", text="delta",
                 color_discrete_map={"Got worse": worse, "Improved": better},
                 labels={"delta": "Change in average AQI", "city": "", "dir": ""})
    fig.update_traces(texttemplate="%{text:+.0f}", textposition="outside", cliponaxis=False)
    return _style(fig, 480, "Change in average AQI: last 30 days vs the 30 before")
