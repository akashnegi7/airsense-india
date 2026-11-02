"""Realistic synthetic hourly data so the app always works offline (clearly labelled DEMO).

Encodes known patterns: winter peak in the Indo-Gangetic Plain, monsoon wash-out,
Diwali spike, wind dispersion - plus injected defects (gaps, sentinels, spikes)
so the cleaning pipeline has real work to do.
"""
import numpy as np
import pandas as pd

from ..config import CITIES, DIWALI

IGP = {"Delhi", "Haryana", "Punjab", "Uttar Pradesh", "Bihar", "Chandigarh"}
CENTRAL = {"Rajasthan", "Madhya Pradesh", "Gujarat", "Maharashtra", "Chhattisgarh",
           "Jharkhand", "West Bengal", "Odisha", "Assam"}


def generate(days=730, seed=42, cities=CITIES):
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.now().floor("h")
    idx = pd.date_range(end - pd.Timedelta(days=days), end, freq="h")
    n = len(idx)
    doy, hour = idx.dayofyear.to_numpy(), idx.hour.to_numpy()
    day_no = (idx.normalize() - idx[0].normalize()).days.to_numpy()
    nd = int(day_no.max()) + 1
    winter = 0.5 * (1 + np.cos(2 * np.pi * (doy - 10) / 365))
    monsoon = np.exp(-(((doy - 210) / 40.0) ** 2))
    diwali = np.zeros(n)
    for d in DIWALI:
        t = (idx.normalize() - pd.Timestamp(d)).days.to_numpy()
        diwali += np.where((t >= 0) & (t <= 3), np.exp(-t / 1.5), 0)
    diurnal = 1 + 0.25 * np.cos(2 * np.pi * (hour - 9) / 24) + 0.2 * np.cos(2 * np.pi * (hour - 21) / 24)

    frames = []
    for r in cities.itertuples():
        if r.state in IGP:
            base, amp, fw = 45, 105, 0.9
        elif r.state in CENTRAL:
            base, amp, fw = 28, 42, 0.4
        else:
            base, amp, fw = 17, 18, 0.2
        mult = rng.uniform(0.8, 1.25)
        ar, e = np.zeros(nd), rng.normal(0, 0.25, nd)
        for i in range(1, nd):
            ar[i] = 0.7 * ar[i - 1] + e[i]
        wind_day = rng.gamma(4, 2.2, nd)
        wind = wind_day[day_no] * (1 + 0.2 * np.sin(2 * np.pi * (hour - 14) / 24)) * (1 + 0.5 * monsoon)
        wind = np.clip(wind + rng.normal(0, 0.8, n), 0.3, None)
        pm25 = ((base + amp * winter) * (1 - 0.65 * monsoon) * mult * diurnal * np.exp(ar[day_no])
                * np.exp(-0.04 * (wind - 8)) * (1 + fw * diwali) * rng.lognormal(0, 0.08, n))
        pm10 = pm25 * rng.uniform(1.5, 1.9) * rng.lognormal(0, 0.1, n)
        no2 = (12 + 0.22 * pm25) * rng.lognormal(0, 0.15, n)
        so2 = (5 + 0.04 * pm25) * rng.lognormal(0, 0.2, n)
        o3 = (25 + 45 * np.clip(np.cos(2 * np.pi * (hour - 14) / 24), 0, None) * (1 - 0.4 * winter)) * rng.lognormal(0, 0.15, n)
        co = (350 + 7 * pm25) * rng.lognormal(0, 0.15, n)  # ug/m3 (cleaned to mg/m3 later)
        lat = r.lat
        temp = (33 - 0.35 * (lat - 8)) + (3 + 0.35 * (lat - 8)) * np.cos(2 * np.pi * (doy - 160) / 365) \
            + 5 * np.cos(2 * np.pi * (hour - 15) / 24) + rng.normal(0, 1, n)
        hum = np.clip(55 + 30 * monsoon - 0.8 * (temp - 25) + rng.normal(0, 8, n), 15, 100)

        df = pd.DataFrame({"city": r.city, "time": idx, "pm2_5": pm25, "pm10": pm10, "no2": no2,
                           "so2": so2, "o3": o3, "co": co, "temp": temp, "humidity": hum, "wind": wind})
        pol = ["pm2_5", "pm10", "no2", "so2", "o3", "co"]
        for c in pol:
            df.loc[rng.random(n) < 0.02, c] = np.nan            # random sensor dropouts
            df.loc[rng.random(n) < 0.001, c] = -999             # sentinel values
        spikes = rng.random(n) < 0.0007
        df.loc[spikes, ["pm2_5", "pm10"]] *= 9                  # electrical spikes
        if rng.random() < 0.15:                                 # occasional multi-day outage
            i0 = int(rng.integers(0, max(n - 96, 1)))
            df.loc[df.index[i0:i0 + 72], pol] = np.nan
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
