"""Baseline models: Persistence heuristic and 24-hour Diurnal Seasonal Lag forecasters."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.logging import get_logger
from src.modeling.base import BaseForecaster

logger = get_logger(__name__)


class PersistenceForecaster(BaseForecaster):
    """Persistence heuristic: assumes pollutant concentration remains constant over all forecast horizons.

    y_hat(t + h) = y(t)
    """

    def __init__(
        self,
        target_pollutant: str = "pm25",
        horizons_hours: list[int] | None = None,
    ) -> None:
        super().__init__(
            name="persistence_baseline",
            target_pollutant=target_pollutant,
            horizons_hours=horizons_hours,
        )

    def fit(self, X: pd.DataFrame, y_dict: dict[int, pd.Series]) -> "PersistenceForecaster":
        """No training parameters required for persistence; records feature columns."""
        self.feature_columns = list(X.columns)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> dict[int, np.ndarray]:
        """Predict current pollutant value across all horizons."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted. Call fit() first.")

        # Locate latest pollutant column
        if self.target_pollutant in X.columns:
            base_values = X[self.target_pollutant].to_numpy(dtype=float)
        elif f"{self.target_pollutant}_lag_1h" in X.columns:
            base_values = X[f"{self.target_pollutant}_lag_1h"].to_numpy(dtype=float)
        else:
            # Fallback to zeros if column missing
            base_values = np.zeros(len(X))

        # Replace any residual NaNs with median
        if np.isnan(base_values).any():
            valid = base_values[~np.isnan(base_values)]
            med = float(np.median(valid)) if len(valid) > 0 else 100.0
            base_values = np.nan_to_num(base_values, nan=med)

        predictions: dict[int, np.ndarray] = {}
        for h in self.horizons_hours:
            predictions[h] = np.copy(base_values)

        return predictions

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        meta = self.get_metadata()
        meta_file = directory / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return directory

    @classmethod
    def load(cls, directory: Path) -> "PersistenceForecaster":
        meta_file = directory / "metadata.json"
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
        forecaster = cls(
            target_pollutant=meta["target_pollutant"],
            horizons_hours=meta["horizons_hours"],
        )
        forecaster.is_fitted = meta.get("is_fitted", True)
        return forecaster


class SeasonalDiurnalLagForecaster(BaseForecaster):
    """Seasonal heuristic: uses the 24-hour lag reflecting the strong diurnal traffic/inversion cycle in Delhi.

    y_hat(t + h) = y(t - 24 + (h % 24))
    """

    def __init__(
        self,
        target_pollutant: str = "pm25",
        horizons_hours: list[int] | None = None,
    ) -> None:
        super().__init__(
            name="seasonal_diurnal_baseline",
            target_pollutant=target_pollutant,
            horizons_hours=horizons_hours,
        )

    def fit(self, X: pd.DataFrame, y_dict: dict[int, pd.Series]) -> "SeasonalDiurnalLagForecaster":
        self.feature_columns = list(X.columns)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> dict[int, np.ndarray]:
        if not self.is_fitted:
            raise ValueError("Model is not fitted. Call fit() first.")

        lag24_col = f"{self.target_pollutant}_lag_24h"
        lag1_col = f"{self.target_pollutant}_lag_1h"

        if lag24_col in X.columns:
            lag24_vals = X[lag24_col].to_numpy(dtype=float)
        elif self.target_pollutant in X.columns:
            lag24_vals = X[self.target_pollutant].to_numpy(dtype=float)
        else:
            lag24_vals = np.zeros(len(X))

        # Fallback for remaining NaNs
        if np.isnan(lag24_vals).any():
            if lag1_col in X.columns:
                lag1_vals = X[lag1_col].to_numpy(dtype=float)
                nan_mask = np.isnan(lag24_vals)
                lag24_vals[nan_mask] = lag1_vals[nan_mask]

            valid = lag24_vals[~np.isnan(lag24_vals)]
            med = float(np.median(valid)) if len(valid) > 0 else 100.0
            lag24_vals = np.nan_to_num(lag24_vals, nan=med)

        predictions: dict[int, np.ndarray] = {}
        for h in self.horizons_hours:
            # 24-hour cycle matches directly for 24h & 48h; for intermediate horizons, uses lag24
            predictions[h] = np.copy(lag24_vals)

        return predictions

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        meta = self.get_metadata()
        meta_file = directory / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return directory

    @classmethod
    def load(cls, directory: Path) -> "SeasonalDiurnalLagForecaster":
        meta_file = directory / "metadata.json"
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
        forecaster = cls(
            target_pollutant=meta["target_pollutant"],
            horizons_hours=meta["horizons_hours"],
        )
        forecaster.is_fitted = meta.get("is_fitted", True)
        return forecaster
