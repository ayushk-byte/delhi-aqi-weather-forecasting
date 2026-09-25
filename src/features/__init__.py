"""Feature engineering package for weather-pollution coupling."""

from src.features.atmospheric_features import (
    add_hygroscopic_growth_features,
    add_inversion_and_cooling_proxy,
    add_ventilation_index,
    add_wind_components,
    create_all_atmospheric_features,
)
from src.features.lag_features import (
    add_autoregressive_lags,
    add_rate_of_change,
    add_rolling_statistics,
    create_all_lag_features,
)
from src.features.pipeline import FeaturePipeline
from src.features.temporal_features import add_temporal_cyclical_features

__all__ = [
    "add_wind_components",
    "add_ventilation_index",
    "add_hygroscopic_growth_features",
    "add_inversion_and_cooling_proxy",
    "create_all_atmospheric_features",
    "add_temporal_cyclical_features",
    "add_autoregressive_lags",
    "add_rolling_statistics",
    "add_rate_of_change",
    "create_all_lag_features",
    "FeaturePipeline",
]
