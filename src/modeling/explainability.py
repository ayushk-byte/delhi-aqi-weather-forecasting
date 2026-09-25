"""Explainable AI (XAI) engine: computes model-derived factor contributions and human-readable explanations."""

from typing import Any

import numpy as np
import pandas as pd

from src.core.constants import DELHI_STATIONS
from src.core.logging import get_logger

logger = get_logger(__name__)

# Feature category classification for domain explainability
METEOROLOGICAL_KEYWORDS = {
    "wind",
    "temp",
    "ventilation",
    "humidity",
    "rh",
    "boundary_layer",
    "pressure",
    "fog",
    "pbl",
    "inversion",
    "cooling",
}
POLLUTION_KEYWORDS = {"pm25", "pm10", "no2", "so2", "co", "o3", "sub_index", "lag"}
TEMPORAL_KEYWORDS = {"hour", "day", "week", "month", "season", "rush", "year"}


def categorize_feature(feature_name: str) -> str:
    """Classify a feature name into Meteorological, Pollution, Temporal, or Other."""
    lower = feature_name.lower()
    if any(k in lower for k in METEOROLOGICAL_KEYWORDS):
        return "Meteorological"
    elif any(k in lower for k in POLLUTION_KEYWORDS):
        return "Pollution Trend"
    elif any(k in lower for k in TEMPORAL_KEYWORDS):
        return "Temporal / Seasonal"
    return "Other"


class ForecastExplainer:
    """Computes feature attribution and synthesizes human-readable explanations answering 'Why is AQI expected to change?'."""

    def __init__(self) -> None:
        pass

    def explain_forecast(
        self,
        station_id: str,
        horizon_hours: int,
        predicted_aqi: float,
        current_aqi: float | None,
        feature_row: pd.Series,
        feature_importances: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Derive explanation contributions for a specific prediction."""
        st_meta = DELHI_STATIONS.get(station_id, {})
        station_name = st_meta.get("name", f"Station {station_id}")

        importances = feature_importances or {}
        if not importances:
            # Fallback uniform importances over present numeric features
            importances = {
                col: 1.0
                for col in feature_row.index
                if pd.api.types.is_numeric_dtype(type(feature_row[col]))
            }

        # Calculate category weights
        category_weights = {
            "Meteorological": 0.0,
            "Pollution Trend": 0.0,
            "Temporal / Seasonal": 0.0,
            "Other": 0.0,
        }

        detailed_features = []
        for feat_name, imp in importances.items():
            if feat_name in feature_row:
                cat = categorize_feature(feat_name)
                val = feature_row[feat_name]
                category_weights[cat] += float(imp)
                detailed_features.append(
                    {
                        "feature": feat_name,
                        "category": cat,
                        "importance_weight": round(float(imp), 4),
                        "value": round(float(val), 2)
                        if isinstance(val, (int, float)) and not np.isnan(val)
                        else None,
                    }
                )

        # Normalize category percentage contributions
        total_weight = sum(category_weights.values())
        if total_weight > 0:
            category_contributions = {
                cat: round((w / total_weight) * 100.0, 1) for cat, w in category_weights.items()
            }
        else:
            category_contributions = {cat: 25.0 for cat in category_weights}

        # Determine direction of change
        curr = current_aqi or predicted_aqi
        delta_aqi = round(predicted_aqi - curr, 1)

        if delta_aqi > 15:
            trend = "Deteriorating (Rising AQI)"
            trend_verb = "increase"
        elif delta_aqi < -15:
            trend = "Improving (Declining AQI)"
            trend_verb = "decrease"
        else:
            trend = "Stable"
            trend_verb = "remain relatively steady"

        # Generate human-readable explanation grounded in model feature values
        explanation_text = self._build_natural_explanation(
            station_name=station_name,
            horizon_hours=horizon_hours,
            predicted_aqi=predicted_aqi,
            current_aqi=curr,
            delta_aqi=delta_aqi,
            trend=trend,
            trend_verb=trend_verb,
            feature_row=feature_row,
            category_contributions=category_contributions,
        )

        return {
            "station_id": station_id,
            "station_name": station_name,
            "horizon_hours": horizon_hours,
            "predicted_aqi": round(predicted_aqi),
            "current_aqi": round(curr),
            "delta_aqi": delta_aqi,
            "trend": trend,
            "human_readable_explanation": explanation_text,
            "category_contributions": category_contributions,
            "top_contributing_features": sorted(
                detailed_features, key=lambda x: x["importance_weight"], reverse=True
            )[:8],
        }

    def _build_natural_explanation(
        self,
        station_name: str,
        horizon_hours: int,
        predicted_aqi: float,
        current_aqi: float,
        delta_aqi: float,
        trend: str,
        trend_verb: str,
        feature_row: pd.Series,
        category_contributions: dict[str, float],
    ) -> str:
        """Synthesize a model-grounded narrative explanation based on actual atmospheric features."""
        sentences = [
            f"Over the next +{horizon_hours} hours at {station_name.split(',')[0]}, air quality is forecast to {trend_verb} "
            f"from {round(current_aqi)} to {round(predicted_aqi)} (trend: {trend})."
        ]

        # Check atmospheric factors
        meteo_notes = []
        if "ventilation_index" in feature_row and pd.notna(feature_row["ventilation_index"]):
            vi = feature_row["ventilation_index"]
            if vi < 2000:
                meteo_notes.append(
                    f"atmospheric ventilation is critically suppressed (VI: {round(vi)} m²/s), severely restricting pollutant dispersion"
                )
            elif vi > 4000:
                meteo_notes.append(
                    f"strong ventilation (VI: {round(vi)} m²/s) facilitates vertical mixing and dilution"
                )

        if "wind_speed_10m" in feature_row and pd.notna(feature_row["wind_speed_10m"]):
            ws = feature_row["wind_speed_10m"]
            if ws < 2.0:
                meteo_notes.append(f"calm surface winds ({ws:.1f} m/s) prevent horizontal clearing")
            elif ws >= 5.0:
                meteo_notes.append(f"moderate wind transport ({ws:.1f} m/s) aids dispersal")

        if "relative_humidity_2m" in feature_row and pd.notna(feature_row["relative_humidity_2m"]):
            rh = feature_row["relative_humidity_2m"]
            if rh >= 75.0:
                meteo_notes.append(
                    f"elevated humidity ({round(rh)}%) promotes secondary particulate condensation and hygroscopic particle growth"
                )

        if "is_shallow_pbl" in feature_row and feature_row["is_shallow_pbl"] == 1:
            meteo_notes.append(
                "a shallow nocturnal boundary layer compresses pollutants close to breathing level"
            )

        # Assemble meteorological summary
        if meteo_notes:
            sentences.append("Meteorological drivers: " + "; ".join(meteo_notes) + ".")

        # Pollution driver
        met_share = category_contributions.get("Meteorological", 40.0)
        pol_share = category_contributions.get("Pollution Trend", 40.0)
        sentences.append(
            f"Model factor breakdown indicates {met_share}% attribution to meteorological dispersion conditions "
            f"and {pol_share}% to antecedent local particulate accumulation."
        )

        return " ".join(sentences)
