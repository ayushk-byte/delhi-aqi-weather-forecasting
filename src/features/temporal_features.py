"""Temporal and calendar cyclical feature engineering."""

import numpy as np
import pandas as pd


def add_temporal_cyclical_features(
    df: pd.DataFrame, timestamp_col: str = "timestamp"
) -> pd.DataFrame:
    """Extract diurnal, weekly, and annual cyclical features from observation timestamps."""
    res = df.copy()

    if timestamp_col not in res.columns:
        return res

    ts = pd.to_datetime(res[timestamp_col], utc=True)

    # Convert to Indian Standard Time (IST = UTC + 5:30) for accurate diurnal local cycle
    ist_ts = ts.dt.tz_convert("Asia/Kolkata") if ts.dt.tz else ts

    # 1. Diurnal cycle (24-hour periodicity)
    hour = ist_ts.dt.hour + (ist_ts.dt.minute / 60.0)
    res["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
    res["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)

    # 2. Day of week & weekend flag
    res["day_of_week"] = ist_ts.dt.dayofweek
    res["is_weekend"] = (res["day_of_week"] >= 5).astype(int)

    # 3. Annual cycle (365.25 days)
    day_of_year = ist_ts.dt.dayofyear
    res["dayofyear_sin"] = np.sin(2.0 * np.pi * day_of_year / 365.25)
    res["dayofyear_cos"] = np.cos(2.0 * np.pi * day_of_year / 365.25)

    # 4. Delhi Winter Pollution Season indicator (October to February: peak stubble & winter inversion)
    month = ist_ts.dt.month
    res["is_winter_pollution_season"] = month.isin([10, 11, 12, 1, 2]).astype(int)

    # 5. Rush Hour Flags (Morning traffic 8-11, Evening traffic 18-22 IST)
    res["is_morning_rush"] = hour.between(8, 11).astype(int)
    res["is_evening_rush"] = hour.between(18, 22).astype(int)

    return res
