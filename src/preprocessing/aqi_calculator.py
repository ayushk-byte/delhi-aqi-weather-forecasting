"""Official CPCB Indian National Air Quality Index (IND-AQI) Calculator.

Implements standard piecewise linear interpolation for sub-indices,
minimum pollutant requirements (>=3 pollutants with at least one PM),
composite AQI computation, and category classification.
"""

import numpy as np
import pandas as pd

from src.core.constants import CPCB_AQI_CATEGORIES, CPCB_BREAKPOINTS


def calculate_sub_index(pollutant: str, concentration: float | None) -> float | None:
    """Calculate the CPCB sub-index for a single pollutant concentration using piecewise interpolation.

    Formula:
        Ip = I_low + ((I_high - I_low) / (B_high - B_low)) * (Cp - B_low)
    """
    if concentration is None or np.isnan(concentration) or concentration < 0:
        return None

    param = pollutant.lower().replace(".", "")
    if param not in CPCB_BREAKPOINTS:
        return None

    breakpoints = CPCB_BREAKPOINTS[param]

    for b_low, b_high, i_low, i_high in breakpoints:
        if b_low <= concentration <= b_high:
            sub_index = i_low + ((i_high - i_low) / (b_high - b_low)) * (concentration - b_low)
            return round(sub_index, 1)

    # If concentration exceeds highest breakpoint, extrapolate linearly from top bucket
    b_low, b_high, i_low, i_high = breakpoints[-1]
    if concentration > b_high:
        extrapolated = i_high + ((i_high - i_low) / (b_high - b_low)) * (concentration - b_high)
        return round(extrapolated, 1)

    return None


def get_aqi_category(aqi_value: float | None) -> str | None:
    """Return the CPCB qualitative category for a numeric AQI value."""
    if aqi_value is None or np.isnan(aqi_value):
        return None

    val = round(aqi_value)
    for cat in CPCB_AQI_CATEGORIES:
        if cat["min"] <= val <= cat["max"]:
            return cat["category"]

    if val > 500:
        return "Severe"
    return "Good"


def calculate_aqi(
    pollutants: dict[str, float | None],
    strict_cpcb_rule: bool = True,
) -> tuple[float | None, str | None, str | None]:
    """Calculate composite AQI, dominant pollutant, and category.

    Args:
        pollutants: Mapping of pollutant names ('pm25', 'pm10', 'no2', 'so2', 'co') to values.
        strict_cpcb_rule: If True, requires >= 3 valid sub-indices with at least PM2.5 or PM10.
                         If False, computes composite max from available sub-indices.

    Returns:
        tuple of (composite_aqi, dominant_pollutant, aqi_category)
    """
    sub_indices: dict[str, float] = {}

    for pol, val in pollutants.items():
        sub_idx = calculate_sub_index(pol, val)
        if sub_idx is not None:
            sub_indices[pol.lower().replace(".", "")] = sub_idx

    if not sub_indices:
        return None, None, None

    # Check CPCB criteria: at least 3 pollutants with at least one PM
    if strict_cpcb_rule:
        has_pm = "pm25" in sub_indices or "pm10" in sub_indices
        has_enough = len(sub_indices) >= 3
        if not (has_pm and has_enough):
            # In real-time edge cases, if we don't have 3 gases but have PM, fall back to max PM
            if has_pm:
                pm_dominant = (
                    "pm25" if sub_indices.get("pm25", 0) >= sub_indices.get("pm10", 0) else "pm10"
                )
                aqi_val = sub_indices[pm_dominant]
                return aqi_val, pm_dominant, get_aqi_category(aqi_val)
            return None, None, None

    dominant_pollutant = max(sub_indices, key=lambda k: sub_indices[k])
    composite_aqi = sub_indices[dominant_pollutant]
    category = get_aqi_category(composite_aqi)

    return composite_aqi, dominant_pollutant, category


def calculate_aqi_dataframe(df: pd.DataFrame, strict_cpcb_rule: bool = False) -> pd.DataFrame:
    """Vectorized calculation adding sub-indices, 'cpcb_aqi', and 'aqi_category' to a DataFrame."""
    res = df.copy()

    # Calculate sub-indices
    for pol in ["pm25", "pm10", "no2", "so2", "co"]:
        if pol in res.columns:
            res[f"sub_index_{pol}"] = res[pol].apply(lambda x: calculate_sub_index(pol, x))

    sub_cols = [c for c in res.columns if c.startswith("sub_index_")]

    if sub_cols:
        res["cpcb_aqi"] = res[sub_cols].max(axis=1)
        res["aqi_category"] = res["cpcb_aqi"].apply(get_aqi_category)

    return res
