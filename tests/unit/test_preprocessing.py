"""Unit tests for CPCB AQI calculator, temporal and spatial alignment."""

from datetime import datetime, timezone

import pandas as pd

from src.preprocessing.aqi_calculator import (
    calculate_aqi,
    calculate_sub_index,
    get_aqi_category,
)
from src.preprocessing.harmonizer import DataHarmonizer
from src.preprocessing.spatial_alignment import (
    haversine_distance_km,
)
from src.preprocessing.temporal_alignment import align_hourly_timeseries


def test_calculate_sub_index_pm25() -> None:
    # Good range: 0-30 -> 0-50
    assert calculate_sub_index("pm25", 15.0) == 25.0
    # Boundary: 30 -> 50
    assert calculate_sub_index("pm25", 30.0) == 50.0
    # Moderate range: 60.1-90 -> 101-200
    sub_idx = calculate_sub_index("pm25", 75.0)
    assert sub_idx is not None and 140 <= sub_idx <= 160
    # Invalid / None
    assert calculate_sub_index("pm25", None) is None
    assert calculate_sub_index("pm25", -5.0) is None


def test_calculate_aqi_and_categories() -> None:
    # Good air quality
    aqi_val, dominant, cat = calculate_aqi(
        {"pm25": 20.0, "pm10": 40.0, "no2": 25.0}, strict_cpcb_rule=True
    )
    assert aqi_val is not None
    assert cat == "Good"

    # Severe air quality in Delhi winter
    aqi_severe, dominant, cat_severe = calculate_aqi(
        {"pm25": 350.0, "pm10": 480.0, "no2": 95.0}, strict_cpcb_rule=True
    )
    assert aqi_severe is not None and aqi_severe >= 400
    assert cat_severe == "Severe"


def test_get_aqi_category_breakpoints() -> None:
    assert get_aqi_category(45) == "Good"
    assert get_aqi_category(80) == "Satisfactory"
    assert get_aqi_category(150) == "Moderate"
    assert get_aqi_category(250) == "Poor"
    assert get_aqi_category(350) == "Very Poor"
    assert get_aqi_category(450) == "Severe"


def test_haversine_distance() -> None:
    # Distance between Anand Vihar (28.6473, 77.3158) and ITO (28.6286, 77.2410) ~7.5 km
    dist = haversine_distance_km(28.6473, 77.3158, 28.6286, 77.2410)
    assert 6.0 <= dist <= 10.0


def test_temporal_alignment_regularization() -> None:
    # Unaligned timestamps at 10:04 and 11:58
    df = pd.DataFrame(
        {
            "station_id": ["DL001", "DL001"],
            "timestamp": [
                datetime(2026, 1, 1, 10, 4, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
            ],
            "pm25": [100.0, 140.0],
        }
    )

    aligned = align_hourly_timeseries(df, max_ffill_hours=1)
    assert len(aligned) == 3  # 10:00, 11:00 (forward filled), 12:00
    assert aligned["timestamp"].iloc[0].minute == 0
    assert aligned.loc[aligned["timestamp"].dt.hour == 11, "pm25"].iloc[0] == 100.0


def test_attach_weather_and_harmonizer(tmp_path) -> None:
    aqi_df = pd.DataFrame(
        {
            "station_id": ["DL001", "DL001"],
            "timestamp": pd.date_range("2026-01-01 10:00", periods=2, freq="1h", tz="UTC"),
            "pm25": [120.0, 130.0],
            "pm10": [200.0, 210.0],
            "no2": [40.0, 45.0],
        }
    )

    wx_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01 10:00", periods=2, freq="1h", tz="UTC"),
            "temperature_2m": [22.0, 24.0],
            "relative_humidity_2m": [60.0, 55.0],
            "wind_speed_10m": [3.0, 3.5],
            "wind_direction_10m": [300.0, 310.0],
            "boundary_layer_height": [800.0, 1000.0],
        }
    )

    harmonizer = DataHarmonizer(output_dir=tmp_path)
    result = harmonizer.harmonize(aqi_df, wx_df, save_parquet=True)

    assert not result.empty
    assert "temperature_2m" in result.columns
    assert "cpcb_aqi" in result.columns
    assert "aqi_category" in result.columns
    assert (tmp_path / "aligned_observations.parquet").exists()
