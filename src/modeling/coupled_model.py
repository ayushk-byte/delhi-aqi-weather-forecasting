"""Weather-Aware Coupled Air Quality Forecaster using multi-horizon LightGBM Regressors."""

import json
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from src.core.logging import get_logger
from src.modeling.base import BaseForecaster

logger = get_logger(__name__)


class WeatherCoupledForecaster(BaseForecaster):
    """Coupled forecaster training specialized gradient-boosted trees per horizon."""

    def __init__(
        self,
        target_pollutant: str = "pm25",
        horizons_hours: list[int] | None = None,
        model_params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            name="weather_coupled_lightgbm",
            target_pollutant=target_pollutant,
            horizons_hours=horizons_hours,
        )
        self.model_params = model_params or {
            "objective": "regression_l1",  # L1 loss (MAE) robust to extreme smoke spikes
            "n_estimators": 120,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 6,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "random_state": 42,
            "verbose": -1,
            "n_jobs": -1,
        }
        self.models: dict[int, lgb.LGBMRegressor] = {}
        self.feature_importances: dict[int, dict[str, float]] = {}

    def fit(self, X: pd.DataFrame, y_dict: dict[int, pd.Series]) -> "WeatherCoupledForecaster":
        """Train an independent LightGBM regressor for each horizon."""
        self.feature_columns = list(X.columns)
        logger.info(
            f"Fitting {self.name} on {len(X)} samples with {len(self.feature_columns)} features..."
        )

        for h in self.horizons_hours:
            if h not in y_dict:
                logger.warning(f"Target for horizon +{h}h not found in y_dict. Skipping.")
                continue

            y = y_dict[h]
            # Filter non-null pairs
            valid_idx = y.notna() & (~X.isna().all(axis=1))
            X_clean = X.loc[valid_idx]
            y_clean = y.loc[valid_idx]

            if len(X_clean) < 10:
                logger.error(f"Insufficient training samples ({len(X_clean)}) for horizon +{h}h.")
                continue

            regressor = lgb.LGBMRegressor(**self.model_params)
            regressor.fit(X_clean, y_clean)
            self.models[h] = regressor

            # Compute normalized feature importance
            importances = regressor.feature_importances_
            total_imp = np.sum(importances)
            if total_imp > 0:
                imp_dict = {
                    col: round(float(imp / total_imp), 4)
                    for col, imp in zip(self.feature_columns, importances)
                }
            else:
                imp_dict = {col: 0.0 for col in self.feature_columns}

            # Top features for this horizon
            sorted_imp = dict(sorted(imp_dict.items(), key=lambda item: item[1], reverse=True)[:10])
            self.feature_importances[h] = sorted_imp
            logger.info(f"Fitted horizon +{h}h. Top feature: {list(sorted_imp.keys())[:3]}")

        self.is_fitted = len(self.models) > 0
        return self

    def predict(self, X: pd.DataFrame) -> dict[int, np.ndarray]:
        """Generate forecasts per horizon, clamped to non-negative physical values."""
        if not self.is_fitted:
            raise ValueError("Forecaster is not fitted yet. Call fit() first.")

        # Ensure all training feature columns are present without DataFrame fragmentation
        col_data = {}
        for col in self.feature_columns:
            if col in X.columns:
                col_data[col] = X[col]
            else:
                col_data[col] = np.nan
        X_aligned = pd.DataFrame(col_data, index=X.index)

        predictions: dict[int, np.ndarray] = {}
        for h in self.horizons_hours:
            if h in self.models:
                raw_pred = self.models[h].predict(X_aligned)
                # Physical concentration constraint: >= 0.0
                predictions[h] = np.maximum(0.0, np.round(raw_pred, 2))
            else:
                predictions[h] = np.zeros(len(X))

        return predictions

    def save(self, directory: Path) -> Path:
        """Persist model binaries and metadata JSON."""
        directory.mkdir(parents=True, exist_ok=True)

        for h, model in self.models.items():
            model_path = directory / f"model_lead_{h}h.joblib"
            joblib.dump(model, model_path)

        meta = self.get_metadata()
        meta["model_params"] = self.model_params
        meta["feature_columns"] = self.feature_columns
        meta["feature_importances"] = self.feature_importances

        with open(directory / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Model {self.name} saved to {directory}")
        return directory

    @classmethod
    def load(cls, directory: Path) -> "WeatherCoupledForecaster":
        """Load forecaster and all horizon models from directory."""
        meta_path = directory / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Model metadata not found at {meta_path}")

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        forecaster = cls(
            target_pollutant=meta["target_pollutant"],
            horizons_hours=meta["horizons_hours"],
            model_params=meta.get("model_params"),
        )
        forecaster.feature_columns = meta.get("feature_columns", [])
        forecaster.feature_importances = {
            int(k): v for k, v in meta.get("feature_importances", {}).items()
        }

        for h in forecaster.horizons_hours:
            model_path = directory / f"model_lead_{h}h.joblib"
            if model_path.exists():
                forecaster.models[h] = joblib.load(model_path)

        forecaster.is_fitted = len(forecaster.models) > 0
        return forecaster
