"""Model Training & Benchmarking Harness with Time-Series Cross-Validation."""

from typing import Any

import numpy as np
import pandas as pd

from src.core.logging import get_logger
from src.modeling.base import BaseForecaster
from src.modeling.baselines import PersistenceForecaster, SeasonalDiurnalLagForecaster
from src.modeling.coupled_model import WeatherCoupledForecaster
from src.modeling.metrics import evaluate_predictions
from src.modeling.registry import ModelRegistry

logger = get_logger(__name__)


class ModelTrainer:
    """Trains, compares, and registers multiple forecasting models without data leakage."""

    def __init__(
        self,
        target_pollutant: str = "pm25",
        horizons_hours: list[int] | None = None,
        train_test_split_ratio: float = 0.8,
        registry: ModelRegistry | None = None,
    ) -> None:
        self.target_pollutant = target_pollutant
        self.horizons_hours = horizons_hours or [6, 12, 24, 48]
        self.split_ratio = train_test_split_ratio
        self.registry = registry or ModelRegistry()

    def train_and_evaluate_all(
        self,
        df_features: pd.DataFrame,
        feature_columns: list[str],
    ) -> dict[str, Any]:
        """Execute chronological train-test split, fit all models, and compare metrics.

        Models compared:
        1. Persistence Baseline
        2. Seasonal Diurnal Baseline
        3. Weather-Coupled LightGBM
        """
        logger.info(
            f"Starting benchmarking for pollutant '{self.target_pollutant}' across horizons {self.horizons_hours}..."
        )

        # 1. Chronological Split (Strictly order-preserving)
        df_sorted = df_features.sort_values(by="timestamp").reset_index(drop=True)
        split_idx = int(len(df_sorted) * self.split_ratio)

        train_df = df_sorted.iloc[:split_idx].copy().reset_index(drop=True)
        test_df = df_sorted.iloc[split_idx:].copy().reset_index(drop=True)

        logger.info(
            f"Chronological split: {len(train_df)} train samples, {len(test_df)} test samples."
        )

        X_train = train_df[feature_columns]
        X_test = test_df[feature_columns]

        # Extract target series for each horizon
        y_train_dict: dict[int, pd.Series] = {}
        y_test_dict: dict[int, pd.Series] = {}

        for h in self.horizons_hours:
            target_col = f"target_{self.target_pollutant}_lead_{h}h"
            if target_col in train_df.columns and target_col in test_df.columns:
                y_train_dict[h] = train_df[target_col]
                y_test_dict[h] = test_df[target_col]

        # 2. Instantiate candidates
        candidates: list[BaseForecaster] = [
            PersistenceForecaster(
                target_pollutant=self.target_pollutant,
                horizons_hours=self.horizons_hours,
            ),
            SeasonalDiurnalLagForecaster(
                target_pollutant=self.target_pollutant,
                horizons_hours=self.horizons_hours,
            ),
            WeatherCoupledForecaster(
                target_pollutant=self.target_pollutant,
                horizons_hours=self.horizons_hours,
            ),
        ]

        # 3. Train and benchmark each model
        results_by_model: dict[str, dict[str, Any]] = {}
        model_instances: dict[str, BaseForecaster] = {}
        overall_scores: dict[str, float] = {}

        for model in candidates:
            logger.info(f"Training {model.name}...")
            model.fit(X_train, y_train_dict)
            model_instances[model.name] = model

            # Predict on test set
            preds = model.predict(X_test)

            horizon_metrics: dict[int, dict[str, float]] = {}
            mae_list: list[float] = []

            for h in self.horizons_hours:
                if h in y_test_dict and h in preds:
                    y_true = y_test_dict[h]
                    y_pred = preds[h]
                    metrics = evaluate_predictions(y_true, y_pred, pollutant=self.target_pollutant)
                    horizon_metrics[h] = metrics
                    mae_list.append(metrics["mae"])

            avg_mae = float(np.mean(mae_list)) if mae_list else float("inf")
            overall_scores[model.name] = avg_mae
            results_by_model[model.name] = {
                "average_mae": round(avg_mae, 2),
                "by_horizon": horizon_metrics,
            }
            logger.info(f"{model.name} completed. Average Test MAE: {avg_mae:.2f}")

        # 4. Determine champion (model with lowest average MAE)
        champion_name = min(overall_scores, key=lambda k: overall_scores[k])
        logger.info(
            f"Champion model selected: {champion_name} (Lowest MAE: {overall_scores[champion_name]:.2f})"
        )

        # 5. Register models in the local registry
        for model_name, model in model_instances.items():
            is_champ = model_name == champion_name
            self.registry.register_model(
                forecaster=model,
                metrics=results_by_model[model_name],
                is_champion=is_champ,
            )

        report = {
            "target_pollutant": self.target_pollutant,
            "horizons_hours": self.horizons_hours,
            "champion_model": champion_name,
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "leaderboard": results_by_model,
        }
        return report
