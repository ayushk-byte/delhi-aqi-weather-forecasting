"""Spatial alignment: associates monitoring stations with meteorological points via Haversine & IDW."""

import numpy as np
import pandas as pd

from src.core.constants import DELHI_STATIONS


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on earth in kilometers."""
    earth_radius_km = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * np.arcsin(np.sqrt(a))
    return float(earth_radius_km * c)


def find_nearest_weather_point(
    station_lat: float,
    station_lon: float,
    weather_points: list[dict[str, float]],
) -> dict[str, float]:
    """Find the closest meteorological observation point to a given station."""
    best_point = weather_points[0]
    min_dist = float("inf")

    for pt in weather_points:
        dist = haversine_distance_km(station_lat, station_lon, pt["latitude"], pt["longitude"])
        if dist < min_dist:
            min_dist = dist
            best_point = pt

    return best_point


def attach_weather_to_stations(
    aqi_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    station_metadata: dict[str, dict] | None = None,
    weather_join_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Merge meteorological variables into the station AQI dataframe on timestamp.

    If weather_df has a single coordinate stream (e.g. Delhi center), it merges on timestamp.
    If weather_df has multiple coordinates, it associates each station with its nearest or IDW weather.
    """
    if aqi_df.empty:
        return aqi_df
    if weather_df.empty:
        return aqi_df

    stations_meta = station_metadata or DELHI_STATIONS
    merged_frames = []

    # Columns to bring over from weather
    default_weather_cols = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "boundary_layer_height",
        "precipitation",
    ]
    cols_to_use = weather_join_cols or [c for c in default_weather_cols if c in weather_df.columns]

    # Check if weather_df is single-stream (no station_id or single coord)
    is_single_stream = (
        "station_id" not in weather_df.columns or weather_df["station_id"].nunique() <= 1
    )

    if is_single_stream:
        # Merge directly on timestamp
        weather_subset = weather_df[["timestamp"] + cols_to_use].drop_duplicates(
            subset=["timestamp"]
        )
        merged = pd.merge(aqi_df, weather_subset, on="timestamp", how="left")
        return merged

    # Multi-station weather mapping
    for station_id, group in aqi_df.groupby("station_id"):
        meta = stations_meta.get(str(station_id), {})
        st_lat = meta.get("latitude")
        st_lon = meta.get("longitude")

        if st_lat is not None and st_lon is not None and "latitude" in weather_df.columns:
            # Find closest weather station
            unique_coords = (
                weather_df[["latitude", "longitude"]].drop_duplicates().to_dict(orient="records")
            )
            nearest = find_nearest_weather_point(st_lat, st_lon, unique_coords)
            subset_wx = weather_df[
                (weather_df["latitude"] == nearest["latitude"])
                & (weather_df["longitude"] == nearest["longitude"])
            ][["timestamp"] + cols_to_use].drop_duplicates(subset=["timestamp"])
        else:
            subset_wx = weather_df[["timestamp"] + cols_to_use].drop_duplicates(
                subset=["timestamp"]
            )

        merged_st = pd.merge(group, subset_wx, on="timestamp", how="left")
        merged_frames.append(merged_st)

    return pd.concat(merged_frames, ignore_index=True)
