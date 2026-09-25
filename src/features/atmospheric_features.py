"""Domain-specific atmospheric physics and dispersion feature engineering for Delhi NCR."""

import numpy as np
import pandas as pd


def add_wind_components(
    df: pd.DataFrame,
    speed_col: str = "wind_speed_10m",
    dir_col: str = "wind_direction_10m",
) -> pd.DataFrame:
    """Compute meteorological zonal (u) and meridional (v) wind vector components.

    Convention:
        u: East-West component (+u = wind blowing towards East)
        v: North-South component (+v = wind blowing towards North)
    """
    res = df.copy()
    if speed_col in res.columns and dir_col in res.columns:
        rad = np.radians(res[dir_col])
        res["wind_u"] = -res[speed_col] * np.sin(rad)
        res["wind_v"] = -res[speed_col] * np.cos(rad)
    return res


def add_ventilation_index(
    df: pd.DataFrame,
    speed_col: str = "wind_speed_10m",
    pblh_col: str = "boundary_layer_height",
) -> pd.DataFrame:
    """Compute Atmospheric Ventilation Index (VI = Wind Speed * Boundary Layer Height).

    In atmospheric dispersion, VI is the primary measure of the atmosphere's capacity
    to transport and dilute pollutants.
    Values < 2000 m^2/s in Delhi indicate extreme stagnation and trapping.
    """
    res = df.copy()
    if speed_col in res.columns and pblh_col in res.columns:
        res["ventilation_index"] = res[speed_col] * res[pblh_col]
        # Low ventilation stagnation indicator (< 2000 m^2/s)
        res["is_stagnation_ventilation"] = (res["ventilation_index"] < 2000.0).astype(int)
    return res


def add_hygroscopic_growth_features(
    df: pd.DataFrame,
    rh_col: str = "relative_humidity_2m",
    temp_col: str = "temperature_2m",
    dew_col: str = "dew_point_2m",
) -> pd.DataFrame:
    """Compute aerosol hygroscopic growth proxy and dew point depression (fog/smog indicator)."""
    res = df.copy()

    # Dew point depression: T - T_dew. Values < 2.5 C indicate near saturation / fog
    if temp_col in res.columns and dew_col in res.columns:
        res["dew_point_depression"] = res[temp_col] - res[dew_col]
        res["is_fog_risk"] = (res["dew_point_depression"] <= 2.5).astype(int)

    # Hygroscopic particulate growth is highly non-linear above 70% RH
    if rh_col in res.columns:
        res["rh_excess_70"] = np.maximum(0.0, res[rh_col] - 70.0)
        res["is_high_humidity"] = (res[rh_col] >= 80.0).astype(int)

    return res


def add_inversion_and_cooling_proxy(
    df: pd.DataFrame,
    temp_col: str = "temperature_2m",
    pblh_col: str = "boundary_layer_height",
    station_col: str = "station_id",
) -> pd.DataFrame:
    """Compute proxy for nocturnal temperature inversion and vertical boundary layer compression.

    During Delhi winter evenings, radiative surface cooling creates surface-based inversions
    that crush the boundary layer to < 150m, triggering pollution spikes.
    """
    res = df.copy()
    if temp_col in res.columns and station_col in res.columns:
        # 1-hour and 3-hour temperature trend
        res["temp_delta_1h"] = res.groupby(station_col)[temp_col].diff(1)
        res["temp_delta_3h"] = res.groupby(station_col)[temp_col].diff(3)

    if pblh_col in res.columns:
        # Extreme shallow nocturnal boundary layer indicator (< 250m)
        res["is_shallow_pbl"] = (res[pblh_col] < 250.0).astype(int)

    return res


def create_all_atmospheric_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all domain-specific atmospheric and dispersion feature transformations."""
    df_feat = add_wind_components(df)
    df_feat = add_ventilation_index(df_feat)
    df_feat = add_hygroscopic_growth_features(df_feat)
    df_feat = add_inversion_and_cooling_proxy(df_feat)
    return df_feat
