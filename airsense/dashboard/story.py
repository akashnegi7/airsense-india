"""Auto-generated data story: every sentence is computed from the data, none is hard-coded."""
import pandas as pd

from ..aqi import category_of
from ..config import DIWALI, POLLUTANTS

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def build_story(daily, latest_date):
    pts, chg = [], None
    last = latest_date
    cur = daily[(daily["date"] > last - pd.Timedelta(days=30)) & (daily["date"] <= last)]
    prev = daily[(daily["date"] > last - pd.Timedelta(days=60)) & (daily["date"] <= last - pd.Timedelta(days=30))]
    now = cur.groupby("city")["aqi"].mean()
    headline = "Not enough data yet to tell a story."

    if now.notna().any():
        worst, best = now.idxmax(), now.idxmin()
        headline = (f"{worst} had the worst air over the last 30 days "
                    f"(average AQI {now[worst]:.0f}, {category_of(now[worst])}).")
        pts.append(f"{best} was the cleanest at an average AQI of {now[best]:.0f} ({category_of(now[best])}).")
        n_bad = int((now > 200).sum())
        pts.append(f"{n_bad} of {now.notna().sum()} cities averaged 'Poor' or worse (AQI above 200).")

    before = prev.groupby("city")["aqi"].mean()
    both = pd.DataFrame({"now": now, "before": before}).dropna()
    if len(both) >= 3:
        both["delta"] = both["now"] - both["before"]
        chg = both.reset_index()
        up = int((both["delta"] > 0).sum())
        pts.insert(0, f"{up} of {len(both)} cities got worse compared with the previous 30 days; "
                      f"the national average moved from AQI {both['before'].mean():.0f} to {both['now'].mean():.0f}.")
        w, b = both["delta"].idxmax(), both["delta"].idxmin()
        pts.append(f"Biggest deterioration: {w} ({both.loc[w, 'delta']:+.0f} AQI points). "
                   f"Biggest improvement: {b} ({both.loc[b, 'delta']:+.0f}).")

    pm = daily.groupby(daily["date"].dt.month)["pm2_5"].mean()
    if daily["month"].nunique() >= 8 and len(pm) >= 8:
        hi, lo = pm.idxmax(), pm.idxmin()
        pts.append(f"Seasonality: national PM2.5 peaks in {MONTH_NAMES[hi - 1]} ({pm[hi]:.0f} µg/m³) and is lowest in "
                   f"{MONTH_NAMES[lo - 1]} ({pm[lo]:.0f} µg/m³), about {pm[hi] / pm[lo]:.1f}x higher.")

    dom = daily["dominant"].value_counts(normalize=True)
    if len(dom):
        pts.append(f"{POLLUTANTS.get(dom.index[0], dom.index[0])} was the pollutant driving the AQI on "
                   f"{100 * dom.iloc[0]:.0f}% of all city-days.")

    for d in sorted(DIWALI, reverse=True):
        d = pd.Timestamp(d)
        if d - pd.Timedelta(days=3) >= daily["date"].min() and d + pd.Timedelta(days=2) <= last:
            b = daily[(daily["date"] >= d - pd.Timedelta(days=3)) & (daily["date"] < d)]["pm2_5"].mean()
            a = daily[(daily["date"] > d) & (daily["date"] <= d + pd.Timedelta(days=2))]["pm2_5"].mean()
            if pd.notna(a) and pd.notna(b) and b > 0:
                pts.append(f"Around Diwali ({d:%d %b %Y}), average PM2.5 was {100 * (a / b - 1):+.0f}% in the two days after "
                           f"versus the three days before. Fireworks coincide with this change, but weather matters too: "
                           f"treat it as a correlation, not proof.")
                break
    return {"headline": headline, "points": pts, "changes": chg}
