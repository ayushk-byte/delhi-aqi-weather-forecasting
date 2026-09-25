"""Unit tests for Persistence, Seasonal Diurnal, and WeatherCoupled forecasters."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.modeling.baselines import PersistenceForecaster, SeasonalDiurnalLagForecaster
from src.modeling.coupled_model import WeatherCoupledForecaster


def test_persistence_forecaster(tmp_path: Path) -> None:
    X = pd.DataFrame({"pm25": [120.0, 150.0, 180.0]})
    y_dict = {6: pd.Series([130.0, 160.0, 190.0]), 24: pd.Series([140.0, 170.0, 200.0])}

    model = PersistenceForecaster(target_pollutant="pm25", horizons_hours=[6, 24])
    model.fit(X, y_dict)

    preds = model.predict(X)
    assert 6 in preds and 24 in preds
    assert np.array_equal(preds[6], np.array([120.0, 150.0, 180.0]))
    assert np.array_equal(preds[24], np.array([120.0, 150.0, 180.0]))

    # Test serialization
    saved_dir = model.save(tmp_path / "persistence")
    loaded = PersistenceForecaster.load(saved_dir)
    assert loaded.is_fitted is True
    loaded_preds = loaded.predict(X)
    assert np.array_equal(loaded_preds[6], preds[6])


def test_seasonal_diurnal_forecaster(tmp_path: Path) -> None:
    X = pd.DataFrame(
        {
            "pm25": [100.0, 120.0],
            "pm25_lag_24h": [95.0, 115.0],
        }
    )
    y_dict = {24: pd.Series([98.0, 118.0])}

    model = SeasonalDiurnalLagForecaster(target_pollutant="pm25", horizons_hours=[24])
    model.fit(X, y_dict)

    preds = model.predict(X)
    assert 24 in preds
    assert np.array_equal(preds[24], np.array([95.0, 115.0]))

    # Serialization
    saved_dir = model.save(tmp_path / "seasonal")
    loaded = SeasonalDiurnalLagForecaster.load(saved_dir)
    assert loaded.is_fitted is True


def test_weather_coupled_forecaster(tmp_path: Path) -> None:
    # 50 samples for quick LightGBM test
    np.random.seed(42)
    n = 60
    X = pd.DataFrame(
        {
            "pm25_lag_1h": np.random.uniform(50, 200, n),
            "wind_speed_10m": np.random.uniform(1, 10, n),
            "wind_u": np.random.uniform(-5, 5, n),
            "ventilation_index": np.random.uniform(500, 5000, n),
            "temperature_2m": np.random.uniform(15, 35, n),
        }
    )
    # Synthetic target correlated with lag and inversely with wind
    y6 = X["pm25_lag_1h"] * 0.9 - X["wind_speed_10m"] * 2.0 + np.random.normal(0, 5, n)
    y24 = X["pm25_lag_1h"] * 0.8 - X["wind_speed_10m"] * 3.0 + np.random.normal(0, 10, n)

    y_dict = {6: pd.Series(y6), 24: pd.Series(y24)}

    model = WeatherCoupledForecaster(
        target_pollutant="pm25",
        horizons_hours=[6, 24],
        model_params={"n_estimators": 20, "verbose": -1, "random_state": 42},
    )
    model.fit(X, y_dict)

    assert model.is_fitted is True
    assert 6 in model.feature_importances
    assert 24 in model.feature_importances

    # Predict
    preds = model.predict(X)
    assert 6 in preds and 24 in preds
    assert len(preds[6]) == n
    assert (preds[6] >= 0.0).all()  # non-negative physical constraint

    # Serialization
    saved_dir = model.save(tmp_path / "coupled_lgb")
    loaded = WeatherCoupledForecaster.load(saved_dir)
    assert loaded.is_fitted is True

    loaded_preds = loaded.predict(X)
    assert np.allclose(loaded_preds[6], preds[6], atol=1e-2)
