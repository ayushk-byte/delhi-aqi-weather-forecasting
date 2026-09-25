"""Unit tests for data validation, sanity bounds, and stuck sensor detection."""

import numpy as np
import pandas as pd

from src.validation.quality_checks import (
    clean_dataset,
    detect_stuck_sensors,
    validate_physical_bounds,
)


def test_validate_physical_bounds() -> None:
    df = pd.DataFrame(
        {
            "station_id": ["DL001", "DL001", "DL001"],
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC"),
            "pm25": [120.0, -5.0, 2500.0],  # -5.0 and 2500.0 violate bounds [0, 1500]
            "temperature_2m": [22.0, 23.5, 75.0],  # 75.0 violates bound [-5, 55]
        }
    )

    cleaned_df, anomalies = validate_physical_bounds(df)

    assert anomalies == 3
    assert cleaned_df.loc[0, "pm25"] == 120.0
    assert np.isnan(cleaned_df.loc[1, "pm25"])
    assert np.isnan(cleaned_df.loc[2, "pm25"])
    assert np.isnan(cleaned_df.loc[2, "temperature_2m"])


def test_detect_stuck_sensors() -> None:
    # Create 8 consecutive hours where DL001 has constant 185.0
    times = pd.date_range("2026-01-01", periods=8, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "station_id": ["DL001"] * 8,
            "timestamp": times,
            "pm25": [185.0] * 8,
        }
    )

    cleaned_df, stuck_count = detect_stuck_sensors(df, columns=["pm25"], min_consecutive_hours=6)

    assert stuck_count >= 6
    # Stuck points should be converted to NaN
    assert np.isnan(cleaned_df["pm25"].iloc[-1])


def test_normal_fluctuation_not_flagged_as_stuck() -> None:
    times = pd.date_range("2026-01-01", periods=8, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "station_id": ["DL001"] * 8,
            "timestamp": times,
            "pm25": [120.0, 122.0, 121.5, 125.0, 128.0, 130.0, 129.5, 131.0],
        }
    )

    cleaned_df, stuck_count = detect_stuck_sensors(df, columns=["pm25"], min_consecutive_hours=6)

    assert stuck_count == 0
    assert cleaned_df["pm25"].notna().all()


def test_clean_dataset_end_to_end() -> None:
    df = pd.DataFrame(
        {
            "station_id": ["DL001", "DL001"],
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="1h", tz="UTC"),
            "pm25": [110.0, -10.0],
            "pm10": [200.0, 220.0],
        }
    )

    cleaned_df, report = clean_dataset(df)

    assert report.total_rows == 2
    assert report.out_of_bounds_anomalies == 1
    assert report.passed_sanity is True
    assert cleaned_df.loc[0, "pm25"] == 110.0
    assert np.isnan(cleaned_df.loc[1, "pm25"])
