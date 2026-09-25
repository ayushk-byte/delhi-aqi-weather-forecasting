"""Unit tests for ModelTrainer benchmarking harness."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.modeling.registry import ModelRegistry
from src.modeling.trainer import ModelTrainer


def test_model_trainer_benchmarking(tmp_path: Path) -> None:
    # Build 80 synthetic samples
    np.random.seed(42)
    n = 80
    times = pd.date_range("2026-01-01 00:00", periods=n, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": times,
            "station_id": ["DL001"] * n,
            "pm25": np.random.uniform(80, 200, n),
            "pm25_lag_1h": np.random.uniform(80, 200, n),
            "pm25_lag_24h": np.random.uniform(80, 200, n),
            "wind_speed_10m": np.random.uniform(1, 8, n),
            "ventilation_index": np.random.uniform(500, 4000, n),
            "target_pm25_lead_6h": np.random.uniform(80, 200, n),
            "target_pm25_lead_24h": np.random.uniform(80, 200, n),
        }
    )

    feature_cols = [
        "pm25",
        "pm25_lag_1h",
        "pm25_lag_24h",
        "wind_speed_10m",
        "ventilation_index",
    ]

    registry = ModelRegistry(registry_dir=tmp_path / "registry")
    trainer = ModelTrainer(
        target_pollutant="pm25",
        horizons_hours=[6, 24],
        train_test_split_ratio=0.75,
        registry=registry,
    )

    report = trainer.train_and_evaluate_all(df, feature_cols)

    assert "champion_model" in report
    assert report["champion_model"] in [
        "persistence_baseline",
        "seasonal_diurnal_baseline",
        "weather_coupled_lightgbm",
    ]
    assert "leaderboard" in report
    assert len(report["leaderboard"]) == 3
    for model_name, metrics in report["leaderboard"].items():
        assert "average_mae" in metrics
        assert "by_horizon" in metrics
        assert 6 in metrics["by_horizon"]
        assert 24 in metrics["by_horizon"]
