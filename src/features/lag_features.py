"""Autoregressive lag features and rolling window aggregates per station."""

import pandas as pd


def add_autoregressive_lags(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    lags: list[int] | None = None,
    station_col: str = "station_id",
) -> pd.DataFrame:
    """Create lagged features for specified columns grouped by station.

    Default lags: [1, 2, 3, 6, 12, 24] hours.
    """
    res = df.copy()
    target_cols = columns or ["pm25", "pm10", "no2", "wind_speed_10m", "temperature_2m"]
    lag_list = lags or [1, 2, 3, 6, 12, 24]

    for col in target_cols:
        if col not in res.columns:
            continue
        for lag in lag_list:
            res[f"{col}_lag_{lag}h"] = res.groupby(station_col)[col].shift(lag)

    return res


def add_rolling_statistics(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    windows: list[int] | None = None,
    station_col: str = "station_id",
) -> pd.DataFrame:
    """Compute rolling window mean, std, min, max per station.

    Default windows: [6, 12, 24] hours.
    Uses closed='left' logic (shifted by 1) to prevent target leakage if applied to pollutants.
    """
    res = df.copy()
    target_cols = columns or ["pm25", "pm10", "wind_speed_10m"]
    window_list = windows or [6, 12, 24]

    for col in target_cols:
        if col not in res.columns:
            continue
        for w in window_list:
            # Shift by 1 first so the current observation t is not included in the historical window
            shifted = res.groupby(station_col)[col].shift(1)
            grouped_shifted = shifted.groupby(res[station_col])

            res[f"{col}_roll_mean_{w}h"] = grouped_shifted.transform(
                lambda s: s.rolling(w, min_periods=max(1, w // 3)).mean()
            )
            res[f"{col}_roll_std_{w}h"] = grouped_shifted.transform(
                lambda s: s.rolling(w, min_periods=max(1, w // 3)).std()
            )
            res[f"{col}_roll_max_{w}h"] = grouped_shifted.transform(
                lambda s: s.rolling(w, min_periods=max(1, w // 3)).max()
            )
            res[f"{col}_roll_min_{w}h"] = grouped_shifted.transform(
                lambda s: s.rolling(w, min_periods=max(1, w // 3)).min()
            )

    return res


def add_rate_of_change(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    station_col: str = "station_id",
) -> pd.DataFrame:
    """Compute 1-hour and 6-hour rate of change / momentum for pollutants."""
    res = df.copy()
    target_cols = columns or ["pm25", "pm10"]

    for col in target_cols:
        if col in res.columns:
            res[f"{col}_diff_1h"] = res.groupby(station_col)[col].diff(1)
            res[f"{col}_diff_6h"] = res.groupby(station_col)[col].diff(6)

    return res


def create_all_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply complete lag, rolling statistics, and momentum feature pipeline."""
    df_lags = add_autoregressive_lags(df)
    df_lags = add_rolling_statistics(df_lags)
    df_lags = add_rate_of_change(df_lags)
    return df_lags
