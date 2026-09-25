"""Uncertainty estimation and prediction interval engine for multi-horizon forecasts."""

import numpy as np


def compute_forecast_uncertainty(
    predicted_val: float,
    horizon_hours: int,
    confidence_level: float = 0.80,
    historical_rmse: float = 18.0,
) -> dict[str, float]:
    """Calculate lower/upper uncertainty bands and a defensible confidence score.

    Forecast uncertainty naturally increases with forecast lead time:
    sigma(h) = base_rmse * sqrt(1 + 0.025 * h)
    """
    # Horizon uncertainty expansion factor
    expansion = np.sqrt(1.0 + 0.03 * horizon_hours)
    sigma = historical_rmse * expansion

    # z-score for normal distribution (80% CI -> z=1.28; 90% CI -> z=1.645)
    z = 1.28 if confidence_level <= 0.80 else 1.645
    half_width = z * sigma

    lower_bound = max(0.0, round(predicted_val - half_width, 1))
    upper_bound = round(predicted_val + half_width, 1)

    # Confidence score (decreases slightly as horizon expands)
    confidence_pct = max(50.0, min(95.0, round(92.0 - 0.3 * horizon_hours, 1)))

    return {
        "predicted_value": round(predicted_val, 1),
        "uncertainty_lower": lower_bound,
        "uncertainty_upper": upper_bound,
        "uncertainty_half_width": round(half_width, 1),
        "confidence_score_pct": confidence_pct,
    }
