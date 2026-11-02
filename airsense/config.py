"""Central configuration: paths, monitored cities and pollutant metadata."""
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("AIRSENSE_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "airsense.db"
DEMO_DAYS = int(os.getenv("AIRSENSE_DEMO_DAYS", "730"))

_CITY_ROWS = [
    ("Delhi", "Delhi", 28.61, 77.21), ("Gurugram", "Haryana", 28.46, 77.03),
    ("Rewari", "Haryana", 28.20, 76.62), ("Faridabad", "Haryana", 28.41, 77.31),
    ("Noida", "Uttar Pradesh", 28.54, 77.39), ("Lucknow", "Uttar Pradesh", 26.85, 80.95),
    ("Kanpur", "Uttar Pradesh", 26.45, 80.35), ("Agra", "Uttar Pradesh", 27.18, 78.01),
    ("Varanasi", "Uttar Pradesh", 25.32, 82.97), ("Patna", "Bihar", 25.59, 85.14),
    ("Chandigarh", "Chandigarh", 30.73, 76.78), ("Ludhiana", "Punjab", 30.90, 75.86),
    ("Amritsar", "Punjab", 31.63, 74.87), ("Dehradun", "Uttarakhand", 30.32, 78.03),
    ("Srinagar", "Jammu & Kashmir", 34.08, 74.80), ("Jaipur", "Rajasthan", 26.91, 75.79),
    ("Jodhpur", "Rajasthan", 26.24, 73.02), ("Ahmedabad", "Gujarat", 23.02, 72.57),
    ("Surat", "Gujarat", 21.17, 72.83), ("Mumbai", "Maharashtra", 19.08, 72.88),
    ("Pune", "Maharashtra", 18.52, 73.86), ("Nagpur", "Maharashtra", 21.15, 79.09),
    ("Bhopal", "Madhya Pradesh", 23.26, 77.41), ("Indore", "Madhya Pradesh", 22.72, 75.86),
    ("Raipur", "Chhattisgarh", 21.25, 81.63), ("Ranchi", "Jharkhand", 23.34, 85.31),
    ("Kolkata", "West Bengal", 22.57, 88.36), ("Bhubaneswar", "Odisha", 20.30, 85.82),
    ("Guwahati", "Assam", 26.14, 91.74), ("Hyderabad", "Telangana", 17.39, 78.49),
    ("Visakhapatnam", "Andhra Pradesh", 17.69, 83.22), ("Bengaluru", "Karnataka", 12.97, 77.59),
    ("Chennai", "Tamil Nadu", 13.08, 80.27), ("Coimbatore", "Tamil Nadu", 11.02, 76.96),
    ("Kochi", "Kerala", 9.93, 76.27), ("Thiruvananthapuram", "Kerala", 8.52, 76.94),
]
CITIES = pd.DataFrame(_CITY_ROWS, columns=["city", "state", "lat", "lon"])

POLLUTANTS = {"pm2_5": "PM2.5", "pm10": "PM10", "no2": "NO₂", "o3": "O₃", "so2": "SO₂", "co": "CO"}
UNITS = {"pm2_5": "µg/m³", "pm10": "µg/m³", "no2": "µg/m³", "o3": "µg/m³", "so2": "µg/m³", "co": "mg/m³"}
METRICS = {"aqi": "AQI (overall)", **{k: f"{v} ({UNITS[k]})" for k, v in POLLUTANTS.items()}}
WEATHER = {"temp": "Temperature", "humidity": "Humidity", "wind": "Wind speed"}
PRETTY = {**POLLUTANTS, **WEATHER}

# Approximate Diwali dates (fireworks effect analysis)
DIWALI = ["2024-11-01", "2025-10-20", "2026-11-08"]
