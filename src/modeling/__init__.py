"""Modeling package for baseline and weather-coupled multi-horizon forecasting."""

from src.modeling.base import BaseForecaster
from src.modeling.baselines import PersistenceForecaster, SeasonalDiurnalLagForecaster
from src.modeling.coupled_model import WeatherCoupledForecaster
from src.modeling.metrics import evaluate_predictions, regression_metrics
from src.modeling.registry import ModelRegistry
from src.modeling.trainer import ModelTrainer

__all__ = [
    "BaseForecaster",
    "PersistenceForecaster",
    "SeasonalDiurnalLagForecaster",
    "WeatherCoupledForecaster",
    "regression_metrics",
    "evaluate_predictions",
    "ModelRegistry",
    "ModelTrainer",
]
