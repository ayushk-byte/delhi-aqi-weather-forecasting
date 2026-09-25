"""Unit tests for continuous and categorical evaluation metrics."""

import numpy as np

from src.modeling.metrics import categorical_aqi_metrics, evaluate_predictions, regression_metrics


def test_regression_metrics() -> None:
    y_true = np.array([100.0, 150.0, 200.0, 250.0])
    y_pred = np.array([110.0, 140.0, 210.0, 240.0])  # errors: +10, -10, +10, -10

    metrics = regression_metrics(y_true, y_pred)

    assert metrics["mae"] == 10.0
    assert metrics["rmse"] == 10.0
    assert metrics["mbe"] == 0.0
    assert metrics["r2"] > 0.90


def test_categorical_aqi_metrics() -> None:
    # 20 ug/m3 PM2.5 = Good, 260 ug/m3 PM2.5 = Severe
    y_true = np.array([20.0, 260.0])
    y_pred = np.array([22.0, 280.0])  # Both in same respective category

    cat_metrics = categorical_aqi_metrics(y_true, y_pred, pollutant="pm25")

    assert cat_metrics["category_accuracy"] == 1.0
    assert cat_metrics["within_one_bucket_acc"] == 1.0
    assert cat_metrics["severe_recall"] == 1.0


def test_evaluate_predictions_combined() -> None:
    y_true = np.array([50.0, 100.0, 300.0])
    y_pred = np.array([55.0, 95.0, 310.0])

    combined = evaluate_predictions(y_true, y_pred, pollutant="pm25")

    assert "mae" in combined
    assert "rmse" in combined
    assert "r2" in combined
    assert "category_accuracy" in combined
    assert "severe_recall" in combined
