"""Constants for Delhi NCR stations, CPCB AQI calculation, and physical validation ranges."""

from typing import Any

# Delhi NCR Monitoring Stations (Selection of high-impact reference stations across NCR)
DELHI_STATIONS: dict[str, dict[str, Any]] = {
    "DL001": {
        "name": "Anand Vihar, Delhi - DPCC",
        "latitude": 28.6473,
        "longitude": 77.3158,
        "cpcb_id": "site_115",
        "zone": "East Delhi",
    },
    "DL002": {
        "name": "Punjabi Bagh, Delhi - DPCC",
        "latitude": 28.6740,
        "longitude": 77.1310,
        "cpcb_id": "site_118",
        "zone": "West Delhi",
    },
    "DL003": {
        "name": "R K Puram, Delhi - DPCC",
        "latitude": 28.5632,
        "longitude": 77.1869,
        "cpcb_id": "site_119",
        "zone": "South Delhi",
    },
    "DL004": {
        "name": "ITO, Delhi - CPCB",
        "latitude": 28.6286,
        "longitude": 77.2410,
        "cpcb_id": "site_103",
        "zone": "Central Delhi",
    },
    "DL005": {
        "name": "Dwarka-Sector 8, Delhi - DPCC",
        "latitude": 28.5710,
        "longitude": 77.0667,
        "cpcb_id": "site_122",
        "zone": "South West Delhi",
    },
    "DL006": {
        "name": "Jahangirpuri, Delhi - DPCC",
        "latitude": 28.7328,
        "longitude": 77.1706,
        "cpcb_id": "site_114",
        "zone": "North Delhi",
    },
    "DL007": {
        "name": "Bawana, Delhi - DPCC",
        "latitude": 28.7762,
        "longitude": 77.0511,
        "cpcb_id": "site_113",
        "zone": "North West Delhi",
    },
    "DL008": {
        "name": "Wazirpur, Delhi - DPCC",
        "latitude": 28.6998,
        "longitude": 77.1654,
        "cpcb_id": "site_125",
        "zone": "North West Delhi",
    },
}

# CPCB IND-AQI Categories and color representations
CPCB_AQI_CATEGORIES = [
    {"category": "Good", "min": 0, "max": 50, "color": "#009966"},
    {"category": "Satisfactory", "min": 51, "max": 100, "color": "#FFDE33"},
    {"category": "Moderate", "min": 101, "max": 200, "color": "#FF9933"},
    {"category": "Poor", "min": 201, "max": 300, "color": "#CC0033"},
    {"category": "Very Poor", "min": 301, "max": 400, "color": "#660099"},
    {"category": "Severe", "min": 401, "max": 500, "color": "#7E0023"},
]

# Breakpoints for Sub-index calculation (CPCB standard guidelines)
# [B_low, B_high, I_low, I_high]
CPCB_BREAKPOINTS = {
    "pm25": [
        (0.0, 30.0, 0, 50),
        (30.1, 60.0, 51, 100),
        (60.1, 90.0, 101, 200),
        (90.1, 120.0, 201, 300),
        (120.1, 250.0, 301, 400),
        (250.1, 500.0, 401, 500),
    ],
    "pm10": [
        (0.0, 50.0, 0, 50),
        (50.1, 100.0, 51, 100),
        (100.1, 250.0, 101, 200),
        (250.1, 350.0, 201, 300),
        (350.1, 430.0, 301, 400),
        (430.1, 600.0, 401, 500),
    ],
    "no2": [
        (0.0, 40.0, 0, 50),
        (40.1, 80.0, 51, 100),
        (80.1, 180.0, 101, 200),
        (180.1, 280.0, 201, 300),
        (280.1, 400.0, 301, 400),
        (400.1, 800.0, 401, 500),
    ],
    "so2": [
        (0.0, 40.0, 0, 50),
        (40.1, 80.0, 51, 100),
        (80.1, 380.0, 101, 200),
        (380.1, 800.0, 201, 300),
        (800.1, 1600.0, 301, 400),
        (1600.1, 2400.0, 401, 500),
    ],
    "co": [
        (0.0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200),
        (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
        (34.1, 50.0, 401, 500),
    ],
    "o3": [
        (0.0, 50.0, 0, 50),
        (50.1, 100.0, 51, 100),
        (100.1, 168.0, 101, 200),
        (168.1, 208.0, 201, 300),
        (208.1, 748.0, 301, 400),
        (748.1, 1000.0, 401, 500),
    ],
}

# Physical bounds for observation plausibility checks
PHYSICAL_BOUNDS = {
    "pm25": (0.0, 1500.0),  # ug/m3
    "pm10": (0.0, 2500.0),  # ug/m3
    "o3": (0.0, 1200.0),  # ug/m3
    "no2": (0.0, 1000.0),  # ug/m3
    "so2": (0.0, 1000.0),  # ug/m3
    "co": (0.0, 100.0),  # mg/m3
    "temperature_2m": (-5.0, 55.0),  # deg C
    "relative_humidity_2m": (0.0, 100.0),  # %
    "surface_pressure": (850.0, 1100.0),  # hPa
    "wind_speed_10m": (0.0, 50.0),  # m/s
    "wind_direction_10m": (0.0, 360.0),  # degrees
    "boundary_layer_height": (10.0, 6000.0),  # meters
    "precipitation": (0.0, 300.0),  # mm
}

DEFAULT_HORIZONS_HOURS = [6, 12, 24, 48, 72]
