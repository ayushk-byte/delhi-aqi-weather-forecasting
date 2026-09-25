"""Spatial forecasting: Hotspot detection and 2D grid IDW interpolation across Delhi NCR."""

from typing import Any

import numpy as np

from src.core.config import get_settings
from src.preprocessing.aqi_calculator import get_aqi_category
from src.preprocessing.spatial_alignment import haversine_distance_km


def detect_hotspots(
    station_predictions: list[dict[str, Any]],
    horizon_hours: int = 24,
    excess_threshold_std: float = 0.5,
) -> list[dict[str, Any]]:
    """Identify spatial pollution hotspots comparing locations across the Delhi NCR region.

    A location is flagged as a Hotspot if:
    1. Its forecasted AQI is >= regional_mean + excess_threshold_std * regional_std, OR
    2. Its forecasted AQI enters 'Very Poor' (>= 301) or 'Severe' (>= 401).
    """
    if not station_predictions:
        return []

    # Extract AQI values for requested horizon
    station_points = []
    aqi_values = []

    for stn in station_predictions:
        st_id = stn.get("station_id")
        name = stn.get("station_name", st_id)
        lat = stn.get("latitude")
        lon = stn.get("longitude")

        # Find forecast for horizon
        horizons = stn.get("horizons", [])
        h_match = next((h for h in horizons if h.get("horizon_hours") == horizon_hours), None)
        if not h_match and horizons:
            h_match = horizons[0]

        if h_match:
            aqi = float(h_match.get("predicted_aqi", 0))
            pm25 = float(h_match.get("predicted_pm25", 0))
            category = h_match.get("aqi_category", get_aqi_category(aqi))

            station_points.append(
                {
                    "station_id": st_id,
                    "station_name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "predicted_aqi": aqi,
                    "predicted_pm25": pm25,
                    "aqi_category": category,
                }
            )
            aqi_values.append(aqi)

    if not aqi_values:
        return []

    reg_mean = float(np.mean(aqi_values))
    reg_std = float(np.std(aqi_values))
    threshold_aqi = max(reg_mean + excess_threshold_std * reg_std, 250.0)

    hotspots = []
    for pt in station_points:
        aqi = pt["predicted_aqi"]
        is_hotspot = (aqi >= threshold_aqi) or (aqi >= 320.0)

        if is_hotspot:
            excess = round(aqi - reg_mean, 1)
            if aqi >= 401:
                severity = "Critical / Severe"
            elif aqi >= 301:
                severity = "High Hotspot"
            else:
                severity = "Moderate Hotspot"

            hotspots.append(
                {
                    "station_id": pt["station_id"],
                    "station_name": pt["station_name"],
                    "latitude": pt["latitude"],
                    "longitude": pt["longitude"],
                    "predicted_aqi": round(aqi),
                    "predicted_pm25": round(pt["predicted_pm25"], 1),
                    "aqi_category": pt["aqi_category"],
                    "excess_above_regional_mean": excess,
                    "severity": severity,
                    "horizon_hours": horizon_hours,
                }
            )

    # Sort descending by predicted AQI
    return sorted(hotspots, key=lambda x: x["predicted_aqi"], reverse=True)


def generate_spatial_grid(
    station_predictions: list[dict[str, Any]],
    horizon_hours: int = 24,
    grid_steps: int = 15,
) -> list[dict[str, Any]]:
    """Interpolate discrete station forecasts into a continuous 2D spatial grid over Delhi NCR via IDW.

    Fulfills Section 11: Grid/location representation & spatial interpolation.
    """
    settings = get_settings()
    bbox = settings.bounding_box

    # Extract station points
    pts = []
    for stn in station_predictions:
        lat = stn.get("latitude")
        lon = stn.get("longitude")
        horizons = stn.get("horizons", [])
        h_match = next((h for h in horizons if h.get("horizon_hours") == horizon_hours), None)
        if h_match and lat is not None and lon is not None:
            pts.append(
                (
                    lat,
                    lon,
                    float(h_match.get("predicted_aqi", 100)),
                    float(h_match.get("predicted_pm25", 50)),
                )
            )

    if not pts:
        return []

    lats = np.linspace(bbox.min_lat, bbox.max_lat, grid_steps)
    lons = np.linspace(bbox.min_lon, bbox.max_lon, grid_steps)

    grid_cells = []
    p = 2.0  # IDW power

    for lat_c in lats:
        for lon_c in lons:
            weights = []
            aqi_vals = []
            pm25_vals = []

            for st_lat, st_lon, aqi, pm25 in pts:
                dist = haversine_distance_km(lat_c, lon_c, st_lat, st_lon)
                if dist < 0.05:  # Co-located
                    weights = [1.0]
                    aqi_vals = [aqi]
                    pm25_vals = [pm25]
                    break
                w = 1.0 / (dist**p)
                weights.append(w)
                aqi_vals.append(aqi)
                pm25_vals.append(pm25)

            sum_w = sum(weights)
            interp_aqi = round(sum(w * a for w, a in zip(weights, aqi_vals)) / sum_w)
            interp_pm25 = round(sum(w * p for w, p in zip(weights, pm25_vals)) / sum_w, 1)

            grid_cells.append(
                {
                    "latitude": round(float(lat_c), 4),
                    "longitude": round(float(lon_c), 4),
                    "predicted_aqi": interp_aqi,
                    "predicted_pm25": interp_pm25,
                    "aqi_category": get_aqi_category(interp_aqi),
                    "horizon_hours": horizon_hours,
                }
            )

    return grid_cells
