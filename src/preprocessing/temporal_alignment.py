"""Temporal alignment and hourly regularization for unevenly sampled sensor feeds."""

import pandas as pd

from src.core.logging import get_logger

logger = get_logger(__name__)


def align_hourly_timeseries(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    station_col: str = "station_id",
    max_ffill_hours: int = 2,
    numeric_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Regularize raw timeseries to clean 1-hour intervals per monitoring station.

    Steps:
    1. Parse and round timestamps to nearest hour.
    2. Group by station and take hourly average if duplicate readings exist in the same hour.
    3. Reindex to a complete continuous hourly DatetimeIndex.
    4. Bounded forward-fill up to `max_ffill_hours` to handle isolated transient dropouts.
    """
    if df.empty:
        return df

    df_work = df.copy()

    # Ensure datetime type
    if not pd.api.types.is_datetime64_any_dtype(df_work[timestamp_col]):
        df_work[timestamp_col] = pd.to_datetime(df_work[timestamp_col], utc=True)

    # Floor or round to nearest hour
    df_work["hourly_dt"] = df_work[timestamp_col].dt.round("1h")

    target_cols = numeric_cols or [
        c
        for c in df_work.columns
        if c not in (timestamp_col, station_col, "hourly_dt", "provider", "raw_payload")
        and pd.api.types.is_numeric_dtype(df_work[c])
    ]

    aligned_frames = []

    for station_id, group in df_work.groupby(station_col):
        # Average readings within the same hour
        hourly_agg = group.groupby("hourly_dt")[target_cols].mean()

        if hourly_agg.empty:
            continue

        min_time = hourly_agg.index.min()
        max_time = hourly_agg.index.max()

        # Build complete continuous hourly grid
        full_idx = pd.date_range(start=min_time, end=max_time, freq="1h", name=timestamp_col)
        reindexed = hourly_agg.reindex(full_idx)

        # Bounded forward fill for transient gaps
        if max_ffill_hours > 0:
            reindexed = reindexed.ffill(limit=max_ffill_hours)

        reindexed[station_col] = station_id
        reindexed = reindexed.reset_index()
        aligned_frames.append(reindexed)

    if not aligned_frames:
        return pd.DataFrame()

    aligned_df = pd.concat(aligned_frames, ignore_index=True)
    aligned_df = aligned_df.sort_values(by=[station_col, timestamp_col]).reset_index(drop=True)

    return aligned_df
