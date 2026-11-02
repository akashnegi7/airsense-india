"""CPCB (India) National AQI computation, categories, palettes and health advice."""
import numpy as np
import pandas as pd

CATEGORIES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
EDGES = [0, 50, 100, 200, 300, 400, 500]
RANGE_LABELS = ["0-50", "51-100", "101-200", "201-300", "301-400", "401-500"]

# Concentration breakpoints matching the AQI band edges above (CPCB, 2014).
# PM/NO2/SO2/O3 in ug/m3, CO in mg/m3.
BREAKPOINTS = {
    "pm2_5": [0, 30, 60, 90, 120, 250, 380],
    "pm10": [0, 50, 100, 250, 350, 430, 510],
    "no2": [0, 40, 80, 180, 280, 400, 520],
    "o3": [0, 50, 100, 168, 208, 748, 1000],
    "so2": [0, 40, 80, 380, 800, 1600, 2000],
    "co": [0, 1, 2, 10, 17, 34, 50],
}

PALETTES = {
    "standard": ["#00a651", "#8dc63f", "#f2c500", "#f7941d", "#e53935", "#8b0000"],
    # viridis-based, safe for the common forms of colour blindness
    "safe": ["#fde725", "#7ad151", "#22a884", "#2a788e", "#414487", "#440154"],
}
SEASON_COLORS = {
    "standard": {"Winter": "#1f77b4", "Summer": "#ff7f0e", "Monsoon": "#2ca02c", "Post-monsoon": "#9467bd"},
    "safe": {"Winter": "#0072B2", "Summer": "#E69F00", "Monsoon": "#009E73", "Post-monsoon": "#CC79A7"},
}


def colors(palette="standard"):
    return dict(zip(CATEGORIES, PALETTES[palette]))


def colorscale(palette="standard"):
    c = PALETTES[palette]
    stops = [0.0, 0.1, 0.3, 0.5, 0.7, 1.0]  # fraction of a 0-500 axis
    return [[s, col] for s, col in zip(stops, c)]


def text_on(hex_color):
    """Black or white text, whichever is more readable on the colour."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#ffffff"


def sub_index(pollutant, conc):
    """Linear-interpolated CPCB sub-index; NaN stays NaN, values clamp to 0-500."""
    return np.interp(np.asarray(conc, dtype=float), BREAKPOINTS[pollutant], EDGES)


def categorize(aqi):
    return pd.cut(aqi, bins=[-1, 50, 100, 200, 300, 400, np.inf], labels=CATEGORIES)


def category_of(value):
    if value is None or pd.isna(value):
        return None
    return str(categorize(pd.Series([value])).iloc[0])


def add_aqi(df):
    """Add aqi, category and dominant-pollutant columns.

    CPCB rule: an AQI is valid only if at least 3 pollutants are available,
    one of which must be PM2.5 or PM10. AQI = max of the sub-indices.
    """
    subs = pd.DataFrame({p: sub_index(p, df[p]) for p in BREAKPOINTS if p in df}, index=df.index)
    valid = (subs.notna().sum(axis=1) >= 3) & subs[["pm2_5", "pm10"]].notna().any(axis=1)
    out = df.copy()
    out["aqi"] = subs.max(axis=1).where(valid).round()
    out["dominant"] = subs.fillna(-1).idxmax(axis=1).where(valid)
    out["category"] = categorize(out["aqi"]).astype(object).where(valid)
    return out


ADVICE = {
    "Good": dict(headline="Air quality is good", general="Enjoy your normal outdoor activities.",
                 sensitive="No special precautions needed.", exercise="A great day for outdoor exercise."),
    "Satisfactory": dict(headline="Air quality is acceptable", general="Fine for most people.",
                         sensitive="Unusually sensitive people may notice minor breathing discomfort.",
                         exercise="Outdoor exercise is fine; ease off if you feel irritation."),
    "Moderate": dict(headline="Air quality is moderate", general="Most people are fine; limit long, heavy exertion outside.",
                     sensitive="People with asthma, lung or heart disease: keep medication handy and reduce time outdoors.",
                     exercise="Prefer lighter workouts or shift to cleaner hours (afternoon is usually better)."),
    "Poor": dict(headline="Air quality is poor", general="Prolonged exposure can cause discomfort; cut down on long outdoor stays.",
                 sensitive="Children, older adults and people with respiratory or heart conditions should stay indoors where possible.",
                 exercise="Move workouts indoors. Consider an N95/FFP2 mask if you must be outside."),
    "Very Poor": dict(headline="Air quality is very poor", general="Avoid outdoor activity where you can; keep windows closed.",
                      sensitive="Stay indoors, use an air purifier if available, and follow your doctor's advice.",
                      exercise="Skip outdoor exercise. Wear an N95/FFP2 mask outdoors."),
    "Severe": dict(headline="Air quality is severe (health emergency level)", general="Everyone should avoid outdoor exertion and stay indoors.",
                   sensitive="High risk: stay indoors, use purifiers, and seek medical help if symptoms worsen.",
                   exercise="No outdoor exercise. Wear an N95/FFP2 mask for any essential trip."),
}
