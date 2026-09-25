"""Data quality checks and sanitation logic for sensor observations."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.constants import PHYSICAL_BOUNDS
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DataQualityReport:
    """Detailed summary of data quality assessment."""

    total_rows: int
    out_of_bounds_anomalies: int
    stuck_sensor_anomalies: int
    missingness_by_column: dict[str, float]
    passed_sanity: bool


def validate_physical_bounds(
    df: pd.DataFrame, bounds: dict[str, tuple[float, float]] | None = None
) -> tuple[pd.DataFrame, int]:
    """Clamp or invalidate values that violate physical laws or instrument limits.

    Replaces out-of-bounds readings with NaN and counts total replacements.
    """
    df_clean = df.copy()
    check_bounds = bounds or PHYSICAL_BOUNDS
    anomalies_count = 0

    for col, (min_val, max_val) in check_bounds.items():
        if col in df_clean.columns:
            # Mask out-of-bounds values (including negative values)
            invalid_mask = (df_clean[col] < min_val) | (df_clean[col] > max_val)
            col_anomalies = int(invalid_mask.sum())
            if col_anomalies > 0:
                anomalies_count += col_anomalies
                logger.warning(
                    f"Column '{col}' has {col_anomalies} readings outside [{min_val}, {max_val}]. Setting to NaN."
                )
                df_clean.loc[invalid_mask, col] = np.nan

    return df_clean, anomalies_count


def detect_stuck_sensors(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    station_col: str = "station_id",
    min_consecutive_hours: int = 6,
) -> tuple[pd.DataFrame, int]:
    """Detect and mask flatline / stuck sensor readings.

    In continuous monitoring stations, sensor hardware or telemetry loops often freeze
    and report the exact identical floating value for many consecutive hours.
    """
    df_clean = df.copy()
    target_cols = columns or ["pm25", "pm10", "no2", "so2", "co"]
    total_stuck_points = 0

    if station_col not in df_clean.columns or "timestamp" not in df_clean.columns:
        return df_clean, 0

    # Ensure sorting for accurate sequential comparison
    df_clean = df_clean.sort_values(by=[station_col, "timestamp"]).reset_index(drop=True)

    for col in target_cols:
        if col not in df_clean.columns:
            continue

        for _, group in df_clean.groupby(station_col):
            series = group[col]
            # Identify where values don't change
            is_same = (series == series.shift(1)) & series.notna()

            # Group consecutive True runs
            run_ids = (~is_same).cumsum()
            run_lengths = is_same.groupby(run_ids).transform("sum") + 1

            # Flag runs reaching or exceeding threshold
            stuck_mask = is_same & (run_lengths >= min_consecutive_hours)
            stuck_indices = group.index[stuck_mask]

            if len(stuck_indices) > 0:
                total_stuck_points += len(stuck_indices)
                df_clean.loc[stuck_indices, col] = np.nan

    if total_stuck_points > 0:
        logger.warning(
            f"Detected and masked {total_stuck_points} stuck sensor data points (>= {min_consecutive_hours} consecutive hours flatline)."
        )

    return df_clean, total_stuck_points


def check_missingness_rate(
    df: pd.DataFrame, critical_columns: list[str] | None = None
) -> dict[str, float]:
    """Calculate percentage of missing values per column."""
    cols = critical_columns or [c for c in df.columns if c not in ("station_id", "timestamp")]
    rates = {}
    total_rows = len(df)
    if total_rows == 0:
        return {c: 1.0 for c in cols}

    for col in cols:
        if col in df.columns:
            rates[col] = round(float(df[col].isna().sum()) / total_rows, 4)
    return rates


def clean_dataset(
    df: pd.DataFrame,
    station_col: str = "station_id",
    min_consecutive_hours: int = 6,
    max_missing_ratio: float = 0.8,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Execute end-to-end data cleaning and return cleaned DataFrame with quality report."""
    if df.empty:
        return df, DataQualityReport(
            total_rows=0,
            out_of_bounds_anomalies=0,
            stuck_sensor_anomalies=0,
            missingness_by_column={},
            passed_sanity=False,
        )

    # 1. Physical bounds sanitization
    df_bounds, bounds_anomalies = validate_physical_bounds(df)

    # 2. Stuck sensor detection
    df_stuck, stuck_anomalies = detect_stuck_sensors(
        df_bounds, station_col=station_col, min_consecutive_hours=min_consecutive_hours
    )

    # 3. Missingness check
    missing_rates = check_missingness_rate(df_stuck)
    pm25_missing = missing_rates.get("pm25", 0.0)
    passed = pm25_missing <= max_missing_ratio

    report = DataQualityReport(
        total_rows=len(df),
        out_of_bounds_anomalies=bounds_anomalies,
        stuck_sensor_anomalies=stuck_anomalies,
        missingness_by_column=missing_rates,
        passed_sanity=passed,
    )

    return df_stuck, report
