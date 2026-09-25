"""Evaluation metrics for continuous pollutant predictions and CPCB categorical classification."""

import numpy as np
import pandas as pd

from src.preprocessing.aqi_calculator import calculate_sub_index, get_aqi_category


def regression_metrics(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
) -> dict[str, float]:
    """Calculate standard regression metrics: MAE, RMSE, R2, MBE."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    # Filter out NaNs if any
    valid_mask = (~np.isnan(yt)) & (~np.isnan(yp))
    if not np.any(valid_mask):
        return {"mae": 0.0, "rmse": 0.0, "r2": 0.0, "mbe": 0.0}

    yt = yt[valid_mask]
    yp = yp[valid_mask]

    errors = yp - yt
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    mbe = float(np.mean(errors))

    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    ss_res = np.sum(errors**2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-8 else 0.0

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "mbe": round(mbe, 2),
    }


def categorical_aqi_metrics(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    pollutant: str = "pm25",
) -> dict[str, float]:
    """Evaluate accuracy of converting continuous forecasts into CPCB AQI categories."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    valid_mask = (~np.isnan(yt)) & (~np.isnan(yp))
    if not np.any(valid_mask):
        return {"category_accuracy": 0.0, "severe_recall": 0.0}

    yt = yt[valid_mask]
    yp = yp[valid_mask]

    categories_ordered = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    cat_to_idx = {c: i for i, c in enumerate(categories_ordered)}

    cat_true = [get_aqi_category(calculate_sub_index(pollutant, val)) for val in yt]
    cat_pred = [get_aqi_category(calculate_sub_index(pollutant, val)) for val in yp]

    exact_matches = sum(1 for t, p in zip(cat_true, cat_pred) if t == p)
    total = len(cat_true)
    exact_acc = float(exact_matches / total) if total > 0 else 0.0

    # Within 1 bucket accuracy
    within_one = 0
    for t, p in zip(cat_true, cat_pred):
        if t in cat_to_idx and p in cat_to_idx:
            if abs(cat_to_idx[t] - cat_to_idx[p]) <= 1:
                within_one += 1
    within_one_acc = float(within_one / total) if total > 0 else 0.0

    # Severe recall
    severe_true_count = sum(1 for t in cat_true if t == "Severe")
    severe_pred_count = sum(
        1 for t, p in zip(cat_true, cat_pred) if t == "Severe" and p == "Severe"
    )
    severe_recall = float(severe_pred_count / severe_true_count) if severe_true_count > 0 else 1.0

    return {
        "category_accuracy": round(exact_acc, 4),
        "within_one_bucket_acc": round(within_one_acc, 4),
        "severe_recall": round(severe_recall, 4),
    }


def evaluate_predictions(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    pollutant: str = "pm25",
) -> dict[str, float]:
    """Combined continuous and categorical evaluation metrics."""
    metrics = regression_metrics(y_true, y_pred)
    cat_metrics = categorical_aqi_metrics(y_true, y_pred, pollutant=pollutant)
    metrics.update(cat_metrics)
    return metrics
