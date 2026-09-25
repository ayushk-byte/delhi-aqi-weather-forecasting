"""Abstract Base Class for multi-horizon air quality forecasters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class BaseForecaster(ABC):
    """Abstract interface for multi-horizon air pollution forecasting models."""

    def __init__(
        self,
        name: str,
        target_pollutant: str = "pm25",
        horizons_hours: list[int] | None = None,
    ) -> None:
        self.name = name
        self.target_pollutant = target_pollutant
        self.horizons_hours = horizons_hours or [6, 12, 24, 48]
        self.feature_columns: list[str] = []
        self.is_fitted: bool = False

    @abstractmethod
    def fit(self, X: pd.DataFrame, y_dict: dict[int, pd.Series]) -> "BaseForecaster":
        """Train models for all configured horizons.

        Args:
            X: Predictor feature matrix.
            y_dict: Mapping of forecast horizon (hours) to target Series.
        """

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> dict[int, np.ndarray]:
        """Generate forecasts for each configured horizon.

        Args:
            X: Predictor feature matrix.

        Returns:
            Dictionary mapping horizon (hours) -> predicted concentration array.
        """

    @abstractmethod
    def save(self, directory: Path) -> Path:
        """Persist model artifacts to disk and return destination path."""

    @classmethod
    @abstractmethod
    def load(cls, directory: Path) -> "BaseForecaster":
        """Load forecaster artifact from disk."""

    def get_metadata(self) -> dict[str, Any]:
        """Return forecaster metadata and parameters."""
        return {
            "name": self.name,
            "target_pollutant": self.target_pollutant,
            "horizons_hours": self.horizons_hours,
            "num_features": len(self.feature_columns),
            "is_fitted": self.is_fitted,
        }
